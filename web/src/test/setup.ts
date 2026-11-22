import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

import { FakeWebSocket } from "./fakeSocket";

afterEach(() => {
  cleanup();
  localStorage.clear();
  FakeWebSocket.all = [];
});

// The live updates connect over a WebSocket. Tests drive a fake one
globalThis.WebSocket = FakeWebSocket as unknown as typeof WebSocket;

// jsdom has no layout, which Recharts' ResponsiveContainer listens to
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver ??= ResizeObserverStub as unknown as typeof ResizeObserver;
