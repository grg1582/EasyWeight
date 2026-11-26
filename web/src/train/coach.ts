// Feedback on how the reps are done. During a set, a cue under the count when
// a rep stopped halfway, its form slipped or the reps are too fast to control
// the weight. During the rest after it, how the set went and one thing to do on
// the next one. It only watches the Workout, and never changes what is counted.
// A port of device/easyweight/coach.py. The texts are in exercises.ts.

import type { CounterSide, Exercise } from "./config";
import type { Workout } from "./counter";
import { EXERCISES, sidesOf } from "./exercises";

/** A lift that got this far (0 = down, 1 = a counted rep) and went back down
 * without counting was a partial rep */
export const PARTIAL_FROM = 0.5;
/** Back down: the arm is this close to the start */
const DOWN = 0.05;
/** Two reps of one arm closer together than this are too fast */
export const FAST_REP_SECONDS = 0.9;
/** How long a cue stays on screen */
export const CUE_SECONDS = 2.5;

export type Cue = "partial" | "form" | "fast";

export const FAST_TEXT = "Slow down: control the weight";
export const SLOW_TEXT = "Next set: 2 seconds up, 2 seconds down";

/** The form tip for after a clean set */
export function tip(exercise: Exercise, setNumber: number): string {
  const tips = EXERCISES[exercise].text.tips;
  return tips[(setNumber - 1) % tips.length]!;
}

/** How a set went, and what to do on the next one */
export type Summary = [done: string, advice: string];

export function cueText(cue: Cue, exercise: Exercise): string {
  if (cue === "fast") return FAST_TEXT;
  return EXERCISES[exercise].text[cue] ?? FAST_TEXT;
}

interface ArmState {
  peak: number; // furthest through a rep since the arm was last down
  reps: number;
  lastRep: number | null;
}

export class Coach {
  private arms: Partial<Record<CounterSide, ArmState>> = {};
  private exercise: Exercise | null = null;
  private set = 0;
  cue: Cue | null = null;
  cueAt = -Infinity;
  /** Per set: how many partial, off form and fast reps there were */
  partial = 0;
  form = 0;
  fast = 0;

  /** Call every frame, after the engine */
  observe(workout: Workout, now: number): void {
    if (workout.exercise !== this.exercise || workout.set !== this.set) {
      this.exercise = workout.exercise;
      this.set = workout.set;
      this.arms = {};
      if (this.exercise) for (const side of sidesOf(this.exercise)) this.arms[side] = fresh();
      this.partial = 0;
      this.form = 0;
      this.fast = 0;
    }
    if (!this.exercise || workout.resting(now)) return;
    for (const side of sidesOf(this.exercise)) {
      const counter = workout.counters[this.exercise][side]!;
      const arm = this.arms[side]!;
      if (!counter.visible) continue;
      if (counter.reps > arm.reps) {
        if (arm.lastRep !== null && now - arm.lastRep < FAST_REP_SECONDS) this.say("fast", now);
        if (!counter.repClean) this.say("form", now);
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

  /** During the rest after a set: how it went and what to do next, or null. The
   * advice is about whatever happened most: partial reps, then form, then pace
   * on a tie */
  summary(workout: Workout): Summary | null {
    if (!this.exercise || this.set !== workout.set) return null;
    const reps = workout.setReps();
    const parts = [reps === 1 ? "1 rep" : `${reps} reps`];
    if (this.partial) parts.push(`${this.partial} partial`);
    if (this.form) parts.push(`${this.form} off form`);
    if (this.fast) parts.push(`${this.fast} too fast`);
    const text = EXERCISES[this.exercise].text;
    const most = Math.max(this.partial, this.form, this.fast);
    let advice: string;
    if (!most) {
      parts[0] = `Clean set: ${parts[0]}`;
      advice = tip(this.exercise, this.set);
    } else if (this.partial === most) advice = text.full_range;
    else if (this.form === most) advice = text.form_advice ?? SLOW_TEXT;
    else advice = SLOW_TEXT;
    return [parts.join(" · "), advice];
  }

  private say(cue: Cue, now: number) {
    this.cue = cue;
    this.cueAt = now;
    if (cue === "partial") this.partial += 1;
    else if (cue === "form") this.form += 1;
    else this.fast += 1;
  }
}

const fresh = (): ArmState => ({ peak: 0, reps: 0, lastRep: null });
