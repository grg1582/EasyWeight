import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { fakeApi } from "../test/fakeApi";
import { framesOf } from "../train/parity";
import type { PoseDetector } from "../train/pose";
import { restClock, TrainPage, type TrainDeps } from "./TrainPage";

const auth = vi.hoisted(() => ({ isDemo: false }));
vi.mock("../auth/AuthContext", () => ({
  useAuth: () => ({ user: { id: "u1", email: "roy@example.com", is_demo: auth.isDemo } }),
}));

// jsdom has no camera or video decoding: each read of currentTime is a new frame
let frameTime = 0;
beforeEach(() => {
  frameTime = 0;
  auth.isDemo = false;
  const video = HTMLVideoElement.prototype;
  Object.defineProperty(video, "readyState", { configurable: true, get: () => 4 });
  Object.defineProperty(video, "videoWidth", { configurable: true, get: () => 1000 });
  Object.defineProperty(video, "videoHeight", { configurable: true, get: () => 1000 });
  Object.defineProperty(video, "currentTime", { configurable: true, get: () => ++frameTime });
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(null);
  vi.stubGlobal("requestAnimationFrame", (cb: FrameRequestCallback) =>
    setTimeout(() => cb(performance.now()), 0) as unknown as number,
  );
  vi.stubGlobal("cancelAnimationFrame", (id: number) => clearTimeout(id));
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

/** A detector that plays back the synthetic "curls" session: 10 curls */
function fakes(overrides: Partial<TrainDeps> = {}) {
  const frames = framesOf("curls");
  let i = 0;
  const detector: PoseDetector = { detect: () => frames[i++] ?? frames[frames.length - 1]!, close: vi.fn() };
  const track = { stop: vi.fn() };
  const deps: TrainDeps = {
    loadDetector: vi.fn(async () => detector),
    openCamera: vi.fn(async () => ({ getTracks: () => [track] }) as unknown as MediaStream),
    ...overrides,
  };
  return { deps, detector, track };
}

function renderPage(deps: TrainDeps) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <TrainPage deps={deps} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("TrainPage", () => {
  it("counts reps from the camera and saves the workout", async () => {
    const { calls } = fakeApi({ "POST /events/browser": () => ({ body: { applied: 1 } }) });
    const { deps, detector, track } = fakes();
    renderPage(deps);
    expect(screen.getByText(/Your video stays on your device/)).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Start camera" }));
    await waitFor(() => expect(screen.getByLabelText("Reps")).toHaveTextContent("10"), {
      timeout: 5000,
    });
    // On the camera view, as on the mirror: the exercise, the count and the set
    const stage = screen.getByRole("region", { name: "Camera view" });
    expect(within(stage).getByText("Bicep curl")).toBeInTheDocument();
    expect(within(stage).getByText("SET 1")).toBeInTheDocument();
    const session = screen.getByRole("region", { name: "This session" });
    expect(within(session).getByRole("list", { name: "Sets" })).toHaveTextContent("Set 1Bicep curl10 reps");

    await userEvent.click(screen.getByRole("button", { name: "Stop" }));
    const summary = await screen.findByRole("region", { name: "Summary" });
    expect(within(summary).getByText("10 reps in 1 set")).toBeInTheDocument();
    expect(await within(summary).findByText(/Saved/)).toBeInTheDocument();
    expect(track.stop).toHaveBeenCalled();
    expect(detector.close).toHaveBeenCalled();

    const sent = calls
      .filter((c) => c.path === "/events/browser")
      .flatMap((c) => JSON.parse(c.body!).events as { type: string }[]);
    expect(sent[0]!.type).toBe("workout_started");
    expect(sent.filter((e) => e.type === "rep")).toHaveLength(20); // both arms, 10 each
    expect(sent[sent.length - 1]!.type).toBe("workout_ended");
  });

  it("counts but doesn't save in the demo", async () => {
    auth.isDemo = true;
    const { calls } = fakeApi({});
    const { deps } = fakes();
    renderPage(deps);
    expect(screen.getByText(/reps are counted but not saved/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Start camera" }));
    await waitFor(() => expect(screen.getByLabelText("Reps")).toHaveTextContent("10"), {
      timeout: 5000,
    });
    await userEvent.click(screen.getByRole("button", { name: "Stop" }));
    expect(await screen.findByText(/nothing was saved/)).toBeInTheDocument();
    expect(calls.filter((c) => c.path === "/events/browser")).toEqual([]);
  });

  it("shows the rest time after 8 seconds without a rep, like the mirror", async () => {
    fakeApi({ "POST /events/browser": () => ({ body: { applied: 1 } }) });
    const realNow = performance.now.bind(performance);
    let later = 0;
    vi.spyOn(performance, "now").mockImplementation(() => realNow() + later);
    renderPage(fakes().deps);
    await userEvent.click(screen.getByRole("button", { name: "Start camera" }));
    await waitFor(() => expect(screen.getByLabelText("Reps")).toHaveTextContent("10"), {
      timeout: 5000,
    });
    expect(screen.queryByRole("timer")).not.toBeInTheDocument();

    later = 65_000; // a minute after the last rep
    const timer = await screen.findByRole("timer", { name: "Rest time" });
    expect(timer.textContent).toMatch(/^1:0[5-6]$/);
    expect(screen.getByText("REST · SET 1 DONE")).toBeInTheDocument();
    expect(screen.queryByLabelText("Reps")).not.toBeInTheDocument();
  });

  it("goes full screen, and back", async () => {
    fakeApi({});
    renderPage(fakes().deps);
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Start camera" }));
    const stage = await screen.findByRole("region", { name: "Camera view" });
    expect(stage).not.toHaveClass("fixed");

    // jsdom can't go full screen, like Safari on iPhone: the view fills the window
    await user.click(screen.getByRole("button", { name: "Full screen" }));
    expect(stage).toHaveClass("fixed", "inset-0");
    expect(screen.getByRole("button", { name: "Stop" })).toBeInTheDocument();
    await user.keyboard("{Escape}");
    expect(stage).not.toHaveClass("fixed");
    expect(screen.getByRole("button", { name: "Full screen" })).toBeInTheDocument();
  });

  it("writes the rest time like the mirror", () => {
    expect(restClock(0)).toBe("0:00");
    expect(restClock(9.7)).toBe("0:09");
    expect(restClock(125)).toBe("2:05");
  });

  it("explains a blocked camera and lets you try again", async () => {
    fakeApi({});
    const blocked = new DOMException("Permission denied", "NotAllowedError");
    const { deps, detector } = fakes({ openCamera: vi.fn(async () => Promise.reject(blocked)) });
    renderPage(deps);
    await userEvent.click(screen.getByRole("button", { name: "Start camera" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/camera is blocked/);
    expect(detector.close).toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
  });
});
