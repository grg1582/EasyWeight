import { afterEach, describe, expect, it, vi } from "vitest";

import { clearTokens, setTokens } from "../api/client";
import { fakeApi, tokens } from "../test/fakeApi";
import { FakeWebSocket } from "../test/fakeSocket";
import { connectLive, type LiveMessage } from "./connection";
import { applyMessage } from "./LiveContext";

const mirror = { id: "d1", name: "Home mirror", kind: "mirror" as const };
let n = 0;
const event = (type: string, data: object) => ({ id: `e${++n}`, type, at: "2026-11-22T18:00:00Z", data });
const message = (...events: object[]) => ({ type: "events", device: mirror, events }) as LiveMessage;

afterEach(() => {
  clearTokens();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("what a device is doing", () => {
  it("follows a set rep by rep, then the rest", () => {
    let state = applyMessage({}, message(event("workout_started", { workout_id: "w" })), 1);
    expect(state.d1).toMatchObject({ exercise: null, reps: 0 });
    state = applyMessage(
      state,
      message(
        event("set_started", { workout_id: "w", set_id: "s", exercise: "curl", set_number: 2 }),
        event("rep", { set_id: "s", side: "left", count: 1, top: 40 }),
        event("rep", { set_id: "s", side: "right", count: 1, top: 41 }),
        event("rep", { set_id: "s", side: "left", count: 2, top: 39 }),
      ),
      2,
    );
    expect(state.d1).toMatchObject({ exercise: "curl", set: 2, reps: 2, resting: false, lastSeen: 2 });
    state = applyMessage(state, message(event("set_ended", { set_id: "s", reps: 2 })), 3);
    expect(state.d1).toMatchObject({ reps: 2, resting: true });
  });

  it("forgets the device when its workout ends", () => {
    const state = applyMessage(
      {},
      message(event("workout_started", { workout_id: "w" }), event("workout_ended", { workout_id: "w" })),
      1,
    );
    expect(state).toEqual({});
  });
});

describe("the live connection", () => {
  it("signs in with the access token, then passes events on", async () => {
    setTokens(tokens(1));
    const onMessage = vi.fn();
    const onStatus = vi.fn();
    const stop = connectLive(onMessage, onStatus);
    await vi.waitFor(() => expect(FakeWebSocket.last).toBeDefined());
    const socket = FakeWebSocket.last!;
    expect(socket.url).toBe(`ws://${location.host}/api/v1/live`);
    socket.open();
    expect(JSON.parse(socket.sent[0]!)).toEqual({ token: "access-1" });
    socket.receive({ type: "ready" });
    expect(onStatus).toHaveBeenLastCalledWith("live");
    const m = message(event("workout_started", { workout_id: "w" }));
    socket.receive(m);
    expect(onMessage).toHaveBeenCalledWith(m);
    stop();
    expect(socket.closed).toBe(true);
  });

  it("gets a fresh token and reconnects when the server says the token expired", async () => {
    setTokens(tokens(1));
    localStorage.setItem("easyweight.refreshToken", "refresh-1");
    fakeApi({ "POST /auth/refresh": () => ({ body: tokens(2) }) });
    const onStatus = vi.fn();
    const stop = connectLive(vi.fn(), onStatus);
    await vi.waitFor(() => expect(FakeWebSocket.all).toHaveLength(1));
    FakeWebSocket.last!.open();
    FakeWebSocket.last!.drop(4401);
    expect(onStatus).toHaveBeenLastCalledWith("offline");
    await vi.waitFor(() => expect(FakeWebSocket.all).toHaveLength(2));
    FakeWebSocket.last!.open();
    expect(JSON.parse(FakeWebSocket.last!.sent[0]!)).toEqual({ token: "access-2" });
    stop();
  });

  it("waits longer after each failed attempt", async () => {
    setTokens(tokens(1));
    vi.useFakeTimers();
    const stop = connectLive(vi.fn(), vi.fn());
    await vi.waitFor(() => expect(FakeWebSocket.all).toHaveLength(1));
    FakeWebSocket.last!.drop();
    await vi.advanceTimersByTimeAsync(999);
    expect(FakeWebSocket.all).toHaveLength(1);
    await vi.advanceTimersByTimeAsync(1);
    expect(FakeWebSocket.all).toHaveLength(2);
    FakeWebSocket.last!.drop();
    await vi.advanceTimersByTimeAsync(1999);
    expect(FakeWebSocket.all).toHaveLength(2);
    await vi.advanceTimersByTimeAsync(1);
    expect(FakeWebSocket.all).toHaveLength(3);
    stop();
  });
});
