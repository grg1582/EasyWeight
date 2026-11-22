import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { fakeApi } from "../test/fakeApi";
import { framesOf } from "../train/parity";
import type { PoseDetector } from "../train/pose";
import { TrainPage, type TrainDeps } from "./TrainPage";

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
    const current = screen.getByRole("region", { name: "Current set" });
    expect(within(current).getAllByText("Bicep curl")).toHaveLength(2); // the set, and the list
    expect(within(current).getByRole("list", { name: "Sets" })).toHaveTextContent("Set 1Bicep curl10 reps");

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
