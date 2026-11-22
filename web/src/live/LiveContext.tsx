import { useQueryClient } from "@tanstack/react-query";
import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from "react";

import type { Exercise } from "../train/config";
import { connectLive, type LiveDevice, type LiveMessage, type LiveStatus } from "./connection";

/** What a device is doing right now */
export interface Activity {
  device: LiveDevice;
  exercise: Exercise | null;
  set: number;
  reps: number;
  resting: boolean;
  lastSeen: number; // Date.now() of its last event
}

interface Live {
  status: LiveStatus;
  activity: Activity[];
}

const LiveContext = createContext<Live>({ status: "offline", activity: [] });

// A device that sent nothing for this long isn't shown as training any more
// (a mirror that lost power never sends workout_ended)
export const QUIET_MS = 3 * 60_000;

export function applyMessage(
  activity: Record<string, Activity>,
  message: LiveMessage,
  now: number,
): Record<string, Activity> {
  const { device } = message;
  let current: Activity | null = activity[device.id] ?? null;
  for (const event of message.events) {
    if (event.type === "workout_ended") {
      current = null;
      continue;
    }
    current ??= { device, exercise: null, set: 0, reps: 0, resting: false, lastSeen: now };
    if (event.type === "set_started") {
      current = { ...current, exercise: event.data.exercise, set: event.data.set_number, reps: 0, resting: false };
    } else if (event.type === "rep") {
      current = { ...current, reps: Math.max(current.reps, event.data.count), resting: false };
    } else if (event.type === "set_ended") {
      current = { ...current, reps: event.data.reps, resting: true };
    }
    current = { ...current, device, lastSeen: now };
  }
  const next = { ...activity };
  if (current) next[device.id] = current;
  else delete next[device.id];
  return next;
}

/** Keeps the live connection open while signed in. New events refresh the
 * workouts and stats on screen, and show who is training right now */
export function LiveProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<LiveStatus>("connecting");
  const [activity, setActivity] = useState<Record<string, Activity>>({});
  const refresh = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  useEffect(() => {
    const stop = connectLive((message) => {
      setActivity((current) => applyMessage(current, message, Date.now()));
      // One refresh for a burst of events, not one per rep
      clearTimeout(refresh.current);
      refresh.current = setTimeout(() => {
        for (const key of ["workouts", "workout", "stats", "devices"]) {
          void queryClient.invalidateQueries({ queryKey: [key] });
        }
      }, 400);
    }, setStatus);
    return () => {
      stop();
      clearTimeout(refresh.current);
    };
  }, [queryClient]);

  // Forget devices that went quiet
  useEffect(() => {
    const timer = setInterval(() => {
      setActivity((current) => {
        const now = Date.now();
        const kept = Object.entries(current).filter(([, a]) => now - a.lastSeen < QUIET_MS);
        return kept.length === Object.keys(current).length ? current : Object.fromEntries(kept);
      });
    }, 15_000);
    return () => clearInterval(timer);
  }, []);

  return (
    <LiveContext.Provider value={{ status, activity: Object.values(activity) }}>
      {children}
    </LiveContext.Provider>
  );
}

export const useLive = () => useContext(LiveContext);
