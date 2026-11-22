// parity.json with its types (see counter.test.ts). Only the tests use it
import data from "./parity.json";
import type { Landmark } from "./geometry";

/** The measured landmarks of one frame: [x, y, visibility], or null = nobody */
export type Frame = [number, number, number | null][] | null;

export interface Scenario {
  frames: [number, Frame][]; // run length: [how many frames in a row, the frame]
  counted: number[]; // the frames that counted a rep
  history: { exercise: string; set: number; reps: number }[];
  events: { id: string; type: string; at: number; data: Record<string, unknown> }[];
}

interface Parity {
  size: number;
  fps: number;
  start: number;
  used: number[];
  filler: [number, number];
  scenarios: Record<string, Scenario>;
}

export const parity = data as unknown as Parity;

/** All 33 landmarks of a frame */
export function expand(frame: Frame): Landmark[] | null {
  if (frame === null) return null;
  const points: Landmark[] = Array.from({ length: 33 }, () => ({
    x: parity.filler[0],
    y: parity.filler[1],
    visibility: null,
  }));
  parity.used.forEach((index, k) => {
    const [x, y, visibility] = frame[k]!;
    points[index] = { x, y, visibility };
  });
  return points;
}

/** Every frame of a scenario, run length undone */
export function framesOf(name: string): (Landmark[] | null)[] {
  const out: (Landmark[] | null)[] = [];
  for (const [count, frame] of parity.scenarios[name]!.frames) {
    const landmarks = expand(frame);
    for (let k = 0; k < count; k++) out.push(landmarks);
  }
  return out;
}
