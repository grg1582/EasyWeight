// Feedback on how the reps are done, shown under the count: a rep that
// stopped halfway, or reps done too fast to control the weight. It only
// watches the Workout, and never changes what is counted.
// A port of device/easyweight/coach.py.

import { SIDES, type Exercise, type Side } from "./config";
import type { Workout } from "./counter";

/** A lift that got this far (0 = down, 1 = a counted rep) and went back down
 * without counting was a partial rep */
export const PARTIAL_FROM = 0.5;
/** Back down: the arm is this close to the start */
const DOWN = 0.05;
/** Two reps of one arm closer together than this are too fast */
export const FAST_REP_SECONDS = 0.9;
/** How long a cue stays on screen */
export const CUE_SECONDS = 2.5;

export type Cue = "partial" | "fast";

const PARTIAL_TEXT: Record<Exercise, string> = {
  curl: "Curl all the way up",
  raise: "Raise to shoulder height",
  press: "Press all the way up",
};

export function cueText(cue: Cue, exercise: Exercise): string {
  return cue === "partial" ? PARTIAL_TEXT[exercise] : "Slow down: control the weight";
}

interface ArmState {
  peak: number; // furthest through a rep since the arm was last down
  reps: number;
  lastRep: number | null;
}

export class Coach {
  private arms: Record<Side, ArmState> = { left: fresh(), right: fresh() };
  private exercise: Exercise | null = null;
  private set = 0;
  cue: Cue | null = null;
  cueAt = -Infinity;
  /** Per set: how many partial and fast reps there were */
  partial = 0;
  fast = 0;

  /** Call every frame, after the engine */
  observe(workout: Workout, now: number): void {
    if (workout.exercise !== this.exercise || workout.set !== this.set) {
      this.exercise = workout.exercise;
      this.set = workout.set;
      this.arms = { left: fresh(), right: fresh() };
      this.partial = 0;
      this.fast = 0;
    }
    if (!this.exercise || workout.resting(now)) return;
    for (const side of SIDES) {
      const counter = workout.counters[this.exercise][side];
      const arm = this.arms[side];
      if (!counter.visible) continue;
      if (counter.reps > arm.reps) {
        if (arm.lastRep !== null && now - arm.lastRep < FAST_REP_SECONDS) this.say("fast", now);
        arm.reps = counter.reps;
        arm.lastRep = now;
        arm.peak = 0; // this lift counted
        continue;
      }
      const progress = counter.progress();
      if (progress <= DOWN) {
        if (arm.peak >= PARTIAL_FROM && arm.peak < 1) this.say("partial", now);
        arm.peak = 0;
      } else if (counter.stage === "down") {
        arm.peak = Math.max(arm.peak, progress);
      }
    }
  }

  /** The text to show now, or null */
  text(now: number): string | null {
    if (!this.cue || !this.exercise || now - this.cueAt > CUE_SECONDS) return null;
    return cueText(this.cue, this.exercise);
  }

  private say(cue: Cue, now: number) {
    this.cue = cue;
    this.cueAt = now;
    if (cue === "partial") this.partial += 1;
    else this.fast += 1;
  }
}

const fresh = (): ArmState => ({ peak: 0, reps: 0, lastRep: null });
