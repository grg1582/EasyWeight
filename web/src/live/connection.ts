// The live connection: a WebSocket to the API that pushes the user's new
// events (from a mirror, or from training in another tab) as they arrive.
//
// It signs in with the access token as its first message, and reconnects by
// itself: right away with a fresh token when the server says the token
// expired, otherwise after a growing wait (1, 2, 4 ... up to 30 seconds).

import { accessTokenFor } from "../api/client";
import type { CounterSide, Exercise } from "../train/config";

export interface LiveDevice {
  id: string;
  name: string;
  kind: "mirror" | "browser";
}

/** The events a device sends, as the server passes them on */
export type LiveEvent =
  | { id: string; type: "workout_started"; at: string; data: { workout_id: string } }
  | {
      id: string;
      type: "set_started";
      at: string;
      data: { workout_id: string; set_id: string; exercise: Exercise; set_number: number };
    }
  | { id: string; type: "rep"; at: string; data: { set_id: string; side: CounterSide; count: number; top: number } }
  | { id: string; type: "set_ended"; at: string; data: { set_id: string; reps: number } }
  | { id: string; type: "workout_ended"; at: string; data: { workout_id: string } };

export interface LiveMessage {
  type: "events";
  device: LiveDevice;
  events: LiveEvent[];
}

export type LiveStatus = "connecting" | "live" | "offline";

const UNAUTHORIZED = 4401;
const MAX_WAIT_MS = 30_000;

export function liveUrl(): string {
  // In production the API has its own address (the site's /api rewrite
  // doesn't carry WebSockets), set when the site is built
  const configured = import.meta.env.VITE_LIVE_URL as string | undefined;
  if (configured) return configured;
  const scheme = location.protocol === "https:" ? "wss" : "ws";
  return `${scheme}://${location.host}/api/v1/live`;
}

export function connectLive(
  onMessage: (message: LiveMessage) => void,
  onStatus: (status: LiveStatus) => void,
): () => void {
  let socket: WebSocket | null = null;
  let timer: ReturnType<typeof setTimeout> | undefined;
  let stopped = false;
  let failures = 0;
  let renew = false;

  const retry = (wait: number) => {
    if (!stopped) timer = setTimeout(() => void open(), wait);
  };

  const open = async () => {
    onStatus("connecting");
    const token = await accessTokenFor(renew);
    if (stopped) return;
    if (!token) {
      onStatus("offline");
      return; // signed out: the app goes back to the sign-in page
    }
    const ws = new WebSocket(liveUrl());
    socket = ws;
    ws.onopen = () => ws.send(JSON.stringify({ token }));
    ws.onmessage = (event) => {
      let message: { type?: string };
      try {
        message = JSON.parse(String(event.data));
      } catch {
        return;
      }
      if (message.type === "ready") {
        failures = 0;
        renew = false;
        onStatus("live");
      } else if (message.type === "events") {
        onMessage(message as LiveMessage);
      }
    };
    ws.onclose = (event) => {
      if (stopped || socket !== ws) return;
      socket = null;
      onStatus("offline");
      failures += 1;
      // A token turned away once is renewed right away. Twice in a row, wait
      renew = event.code === UNAUTHORIZED;
      retry(renew && failures === 1 ? 0 : Math.min(MAX_WAIT_MS, 1000 * 2 ** (failures - 1)));
    };
  };

  void open();
  return () => {
    stopped = true;
    clearTimeout(timer);
    socket?.close();
    socket = null;
  };
}
