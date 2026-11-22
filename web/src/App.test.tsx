import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";
import { clearTokens } from "./api/client";
import { AuthProvider } from "./auth/AuthContext";
import { fakeApi, signedIn, tokens } from "./test/fakeApi";
import { FakeWebSocket } from "./test/fakeSocket";

afterEach(() => {
  clearTokens();
  vi.unstubAllGlobals();
});

function renderApp(path = "/") {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[path]}>
        <AuthProvider>
          <App />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const today = new Date().toISOString().slice(0, 10);
const workout = {
  id: "w1",
  device_id: "d1",
  started_at: new Date(Date.now() - 3600_000).toISOString(),
  ended_at: new Date(Date.now() - 3000_000).toISOString(),
  total_sets: 3,
  total_reps: 24,
  exercises: ["curl", "press"],
};

const authed =
  (body: unknown) =>
  (init: { headers?: HeadersInit }) =>
    signedIn(init) ? { body } : { status: 401, body: { detail: "Not signed in" } };

function backend(devices: unknown[] = [{ id: "d1", name: "Home mirror", created_at: today, last_seen_at: null }]) {
  return fakeApi({
    "POST /auth/login": (init) =>
      String(init.body).includes("password=right+password")
        ? { body: tokens() }
        : { status: 401, body: { detail: "Wrong email or password" } },
    "POST /auth/demo": () => ({ body: tokens() }),
    "GET /users/me": authed({ id: "u1", email: "roy@example.com", created_at: today, is_demo: false }),
    "GET /devices": authed(devices),
    "GET /stats": authed({
      days: 30,
      workouts: 1,
      per_exercise: [
        { exercise: "curl", sets: 2, reps: 18 },
        { exercise: "press", sets: 1, reps: 6 },
      ],
      per_day: [{ date: today, reps: 24 }],
    }),
    "GET /workouts": authed({ items: [workout], total: 1 }),
  });
}

async function signIn(password = "right password") {
  const user = userEvent.setup();
  await user.type(await screen.findByLabelText("Email"), "roy@example.com");
  await user.type(screen.getByLabelText("Password"), password);
  await user.click(screen.getByRole("button", { name: "Sign in" }));
  return user;
}

describe("the dashboard app", () => {
  it("asks to sign in first", async () => {
    backend();
    renderApp("/workouts");
    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
  });

  it("shows the server's answer to a wrong password", async () => {
    backend();
    renderApp();
    await signIn("wrong password");
    expect(await screen.findByRole("alert")).toHaveTextContent("Wrong email or password");
  });

  it("opens on the Train page after signing in", async () => {
    backend();
    renderApp();
    await signIn();
    expect(await screen.findByRole("heading", { name: "Train" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Start camera" })).toBeInTheDocument();
    const nav = screen.getAllByRole("link").map((link) => link.textContent);
    expect(nav.slice(0, 4)).toEqual(["Train", "Dashboard", "Workouts", "Mirrors"]);
  });

  it("shows stats and recent workouts on the dashboard", async () => {
    backend();
    renderApp();
    await signIn();
    await userEvent.setup().click(await screen.findByRole("link", { name: "Dashboard" }));
    expect(await screen.findByRole("heading", { name: "Dashboard" })).toBeInTheDocument();
    expect(await screen.findByText("roy@example.com")).toBeInTheDocument();

    const reps = screen.getByText("Reps", { selector: "div" }).parentElement!;
    expect(within(reps).getByText("24")).toBeInTheDocument();
    const byExercise = screen.getByRole("list", { name: "Reps by exercise" });
    expect(within(byExercise).getByText("Bicep curl")).toBeInTheDocument();
    expect(within(byExercise).getByText("Overhead press")).toBeInTheDocument();

    const row = screen.getByRole("link", { name: /\w{3}, \w{3} \d+/ }).closest("tr")!;
    expect(within(row).getByText("24")).toBeInTheDocument();
    expect(row).toHaveTextContent("10 min");
  });

  it("shows a mirror's set as it happens, and refreshes the workouts", async () => {
    const api = backend();
    renderApp();
    await signIn();
    await userEvent.setup().click(await screen.findByRole("link", { name: "Dashboard" }));
    expect(await screen.findByRole("heading", { name: "Dashboard" })).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Training now" })).not.toBeInTheDocument();

    const socket = await waitFor(() => FakeWebSocket.last!);
    act(() => {
      socket.open();
      socket.receive({ type: "ready" });
    });
    expect(await screen.findByText("Live")).toBeInTheDocument();
    const workoutsBefore = api.calls.filter((c) => c.path === "/workouts").length;

    const at = new Date().toISOString();
    act(() =>
      socket.receive({
        type: "events",
        device: { id: "d1", name: "Home mirror", kind: "mirror" },
        events: [
          { id: "e1", type: "set_started", at, data: { workout_id: "w2", set_id: "s", exercise: "press", set_number: 3 } },
          { id: "e2", type: "rep", at, data: { set_id: "s", side: "left", count: 1, top: 1.2 } },
          { id: "e3", type: "rep", at, data: { set_id: "s", side: "left", count: 2, top: 1.1 } },
        ],
      }),
    );
    const now = await screen.findByRole("region", { name: "Training now" });
    expect(now).toHaveTextContent("Home mirror");
    expect(now).toHaveTextContent("Overhead press");
    expect(now).toHaveTextContent("Set 3 · 2 reps");
    await waitFor(() =>
      expect(api.calls.filter((c) => c.path === "/workouts").length).toBeGreaterThan(workoutsBefore),
    );
  });

  it("connects a mirror from its QR code link, signing in on the way", async () => {
    const api = backend();
    const routes = api.fetchMock.getMockImplementation()!;
    api.fetchMock.mockImplementation(async (input, init) =>
      String(input).endsWith("/pairing/K7QM3XPA/claim")
        ? new Response(
            JSON.stringify({
              status: "paired",
              expires_at: today,
              device: { id: "d2", name: JSON.parse(String(init!.body)).name, kind: "mirror", created_at: today, last_seen_at: null },
            }),
            { status: 201 },
          )
        : routes(input, init),
    );
    renderApp("/pair/k7qm3xpa");
    const user = await signIn();
    const form = await screen.findByRole("region", { name: "Connect a mirror" });
    expect(form).toHaveTextContent("K7QM-3XPA");
    await user.type(within(form).getByLabelText("Name (optional)"), "Hallway");
    await user.click(within(form).getByRole("button", { name: "Connect mirror" }));
    expect(await screen.findByText("“Hallway” is connected")).toBeInTheDocument();
  });

  it("points a new user to adding a mirror", async () => {
    backend([]);
    renderApp();
    await signIn();
    await userEvent.setup().click(await screen.findByRole("link", { name: "Dashboard" }));
    expect(await screen.findByText("Connect your first mirror")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Add a mirror" })).toHaveAttribute("href", "/mirrors");
  });

  it("opens the demo without an account, and says it's a demo", async () => {
    const api = backend();
    const routes = api.fetchMock.getMockImplementation()!;
    api.fetchMock.mockImplementation(async (input, init) =>
      String(input).endsWith("/users/me")
        ? new Response(JSON.stringify({ id: "demo", email: "demo@easyweight.dev", is_demo: true }))
        : routes(input, init),
    );
    renderApp();
    await userEvent.setup().click(await screen.findByRole("button", { name: "Try the demo" }));
    expect(await screen.findByText(/looking at a demo/)).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Train" })).toBeInTheDocument();
    expect(screen.getByText(/reps are counted but not saved/)).toBeInTheDocument();
  });

  it("stays signed in after a reload, using the stored refresh token", async () => {
    localStorage.setItem("easyweight.refreshToken", "refresh-0");
    const api = backend();
    const routes = api.fetchMock.getMockImplementation()!;
    api.fetchMock.mockImplementation(async (input, init) =>
      String(input).endsWith("/auth/refresh")
        ? new Response(JSON.stringify(tokens(5)), { status: 200 })
        : routes(input, init),
    );
    renderApp("/dashboard");
    expect(await screen.findByRole("heading", { name: "Dashboard" })).toBeInTheDocument();
  });
});
