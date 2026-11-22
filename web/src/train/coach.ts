// Feedback on how the reps are done. During a set, a cue under the count when
// a rep stopped halfway or the reps are too fast to control the weight. During
// the rest after it, how the set went and one thing to do on the next one. It
// only watches the Workout, and never changes what is counted.
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

/** What to do on the next set, after partial or too fast reps */
const FULL_RANGE_TEXT: Record<Exercise, string> = {
  curl: "Next set: all the way up, all the way down",
  raise: "Next set: lift to shoulder height every rep",
  press: "Next set: arms straight at the top, every rep",
};
export const SLOW_TEXT = "Next set: 2 seconds up, 2 seconds down";

/** After a clean set, a pointer on form for the next one, a different one each set */
const TIPS: Record<Exercise, readonly string[]> = {
  curl: [
    "Tip: keep your elbows pinned to your sides",
    "Tip: no swinging, keep your back still",
    "Tip: squeeze at the top, lower slowly",
  ],
  raise: [
    "Tip: lead with your elbows, not your hands",
    "Tip: stop at shoulder height",
    "Tip: keep a slight bend in your elbows",
  ],
  press: [
    "Tip: brace your core, don't arch your back",
    "Tip: press straight up, biceps by your ears",
    "Tip: lower to chin height, no lower",
  ],
};

/** The form tip for after a clean set */
export function tip(exercise: Exercise, setNumber: number): string {
  const tips = TIPS[exercise];
  return tips[(setNumber - 1) % tips.length]!;
}

/** How a set went, and what to do on the next one */
export type Summary = [done: string, advice: string];

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

  /** During the rest after a set: how it went and what to do next, or null */
  summary(workout: Workout): Summary | null {
    if (!this.exercise || this.set !== workout.set) return null;
    const reps = workout.setReps();
    const parts = [reps === 1 ? "1 rep" : `${reps} reps`];
    if (this.partial) parts.push(`${this.partial} partial`);
    if (this.fast) parts.push(`${this.fast} too fast`);
    let advice: string;
    if (this.partial && this.partial >= this.fast) advice = FULL_RANGE_TEXT[this.exercise];
    else if (this.fast) advice = SLOW_TEXT;
    else {
      parts[0] = `Clean set: ${parts[0]}`;
      advice = tip(this.exercise, this.set);
    }
    return [parts.join(" · "), advice];
  }

  private say(cue: Cue, now: number) {
    this.cue = cue;
    this.cueAt = now;
    if (cue === "partial") this.partial += 1;
    else this.fast += 1;
  }
}

const fresh = (): ArmState => ({ peak: 0, reps: 0, lastRep: null });
