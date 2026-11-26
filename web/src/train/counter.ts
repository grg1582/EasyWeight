// Rep and set logic: a port of device/easyweight/counter.py. It takes numbers
// and returns numbers, so it's tested without a camera or the pose model.

import {
  DRINK_DISTANCE,
  MAX_GAP_SECONDS,
  SET_IDLE_SECONDS,
  SMOOTHING,
  SMOOTHING_FPS,
  type CounterSide,
  type Exercise,
} from "./config";
import { EXERCISES, sidesOf } from "./exercises";

/** How much of a new reading goes into the smoothed one, dt seconds after the
 * last: SMOOTHING at SMOOTHING_FPS, and just as quick (in seconds) at others */
export function smoothingFactor(dt: number | null): number {
  if (dt === null) return SMOOTHING;
  return 1 - (1 - SMOOTHING) ** (dt * SMOOTHING_FPS);
}

function median3([a, b, c]: number[]): number {
  return Math.max(Math.min(a!, b!), Math.min(Math.max(a!, b!), c!));
}

/** One arm (or the whole body) doing one exercise: the reading goes past
 * downAngle, then past upAngle = 1 rep. Each reading goes through a median of
 * the last 3, then smoothing that reacts as fast at any frame rate */
export class RepCounter {
  readonly sign: number; // 1 = the angle shrinks on the way up
  reps = 0;
  angle: number | null = null; // smoothed
  stage: "down" | "up" | null = null;
  visible = false;
  formOk = false; // whether the latest reading's form fit this exercise
  mouth: number | null = null;
  closest = Infinity; // closest the wrist came to the mouth since the arm was down
  top: number | null = null; // furthest up the angle got since the arm was down
  clean = true; // the form check held since the arm was down
  repClean = true; // and it held through the latest rep
  repAt: number | null = null; // when the latest rep was reached
  private recent: number[] = [];
  private lastSeen: number | null = null;

  constructor(
    readonly downAngle: number,
    readonly upAngle: number,
  ) {
    this.sign = downAngle > upAngle ? 1 : -1;
  }

  /** Feed one reading (or null), the mouth distance, whether the form fits,
   * the time in seconds and whether the form check holds. Returns true when
   * this reading completes a rep */
  update(
    rawAngle: number | null,
    mouth: number | null = null,
    formOk = true,
    now: number | null = null,
    checkOk = true,
  ): boolean {
    this.visible = rawAngle !== null;
    this.mouth = mouth;
    if (rawAngle === null) return false;
    this.formOk = formOk;
    let dt: number | null = null;
    if (now !== null && this.lastSeen !== null) {
      dt = now - this.lastSeen;
      if (dt > MAX_GAP_SECONDS) {
        // out of sight for a while: start over from here
        this.angle = null;
        this.recent = [];
        dt = null;
      }
    }
    this.lastSeen = now;
    this.recent = [...this.recent, rawAngle].slice(-3);
    const reading = this.recent.length === 3 ? median3(this.recent) : rawAngle;
    if (mouth !== null) this.closest = Math.min(this.closest, mouth);
    this.angle = this.angle === null ? reading : this.angle + smoothingFactor(dt) * (reading - this.angle);
    if (this.top === null || this.sign * (this.angle - this.top) < 0) this.top = this.angle;
    if (this.sign * (this.angle - this.downAngle) > 0) {
      this.stage = "down";
      this.closest = Infinity;
      this.top = null;
      this.clean = true;
      return false;
    }
    if (this.stage === "down" && !checkOk) this.clean = false;
    if (this.sign * (this.angle - this.upAngle) < 0 && this.stage === "down" && formOk) {
      this.stage = "up";
      this.reps += 1;
      this.repClean = this.clean;
      this.repAt = now;
      return true;
    }
    return false;
  }

  /** How far through the rep the arm is: 0 = down, 1 = all the way up */
  progress(): number {
    if (this.angle === null) return 0;
    const done = (this.downAngle - this.angle) / (this.downAngle - this.upAngle);
    return Math.min(1, Math.max(0, done));
  }
}

export interface SetEntry {
  exercise: Exercise;
  set: number;
  reps: number;
}

/** The counters of one exercise: left and right, or just both */
export type Counters = Partial<Record<CounterSide, RepCounter>>;

interface Candidate {
  exercise: Exercise;
  counter: RepCounter;
  reps: number;
  at: number;
}

/** Splits the reps into sets and knows which exercise each set is. See the
 * Python Workout for the full story: the first rep of a set decides the
 * exercise, no rep for SET_IDLE_SECONDS means resting, a curl during rest is
 * held back until it's clear it isn't drinking, and a squat set starts only on
 * its second squat */
export class Workout {
  readonly counters = Object.fromEntries(
    (Object.keys(EXERCISES) as Exercise[]).map((exercise) => {
      const spec = EXERCISES[exercise];
      const counters: Counters = {};
      for (const side of sidesOf(exercise)) counters[side] = new RepCounter(spec.down, spec.up);
      return [exercise, counters];
    }),
  ) as Record<Exercise, Counters>;
  /** Every set since the start. reset() doesn't clear it */
  readonly history: SetEntry[] = [];
  exercise: Exercise | null = null;
  set = 1;
  prevExercise: Exercise | null = null;
  prevSet = 0;
  lastRep: number | null = null;
  pending: RepCounter | null = null;
  pendingExercise: Exercise | null = null;
  candidate: Candidate | null = null;

  constructor() {
    this.reset();
  }

  /** The counters of an exercise, in order */
  countersOf(exercise: Exercise): [CounterSide, RepCounter][] {
    return sidesOf(exercise).map((side) => [side, this.counters[exercise][side]!]);
  }

  /** The (left, right) counters to show: the set's exercise, or before the
   * first rep, whichever exercise (with the right form) is further along. An
   * exercise of the whole body gives its one counter twice */
  arms(): [RepCounter, RepCounter] {
    let chosen: Exercise;
    if (this.exercise) {
      chosen = this.exercise;
    } else {
      const score = (e: Exercise) =>
        Math.max(...this.countersOf(e).map(([, c]) => (c.formOk ? c.progress() : 0)));
      const all = Object.keys(EXERCISES) as Exercise[];
      chosen = all.reduce((best, e) => (score(e) > score(best) ? e : best));
    }
    const c = this.counters[chosen];
    if (c.both) return [c.both, c.both];
    return [c.left!, c.right!];
  }

  clearReps() {
    for (const counters of Object.values(this.counters)) {
      for (const c of Object.values(counters)) c.reps = 0;
    }
  }

  setReps(): number {
    return Math.max(...this.countersOf(this.exercise as Exercise).map(([, c]) => c.reps));
  }

  resting(now: number): boolean {
    return this.lastRep !== null && now - this.lastRep > SET_IDLE_SECONDS;
  }

  restTime(now: number): number {
    return now - (this.lastRep ?? now);
  }

  startSet(exercise: Exercise, counter: RepCounter, now: number, replace = false, reps = 1) {
    this.set = exercise === this.prevExercise ? this.prevSet + 1 : 1;
    this.exercise = exercise;
    this.clearReps();
    counter.reps = reps;
    this.lastRep = now;
    this.pending = this.pendingExercise = this.candidate = null;
    const entry: SetEntry = { exercise, set: this.set, reps };
    if (replace && this.history.length) this.history[this.history.length - 1] = entry;
    else this.history.push(entry);
  }

  nextSet(exercise: Exercise, counter: RepCounter, now: number, reps = 1) {
    this.prevExercise = this.exercise;
    this.prevSet = this.set;
    this.startSet(exercise, counter, now, false, reps);
  }

  /** Whether a set of 1 rep can turn into a set of exercise */
  private canSwitch(exercise: Exercise): boolean {
    return this.setReps() < 2 && !EXERCISES[exercise].not_after.includes(this.exercise as Exercise);
  }

  /** Start a set of exercise however fits now. False if it can't */
  private begin(exercise: Exercise, counter: RepCounter, now: number, reps: number): boolean {
    if (this.resting(now)) this.nextSet(exercise, counter, now, reps);
    else if (this.exercise === null) this.startSet(exercise, counter, now, false, reps);
    else if (this.canSwitch(exercise)) this.startSet(exercise, counter, now, true, reps);
    else return false;
    return true;
  }

  /** A rep of an exercise that needs more than one rep to start a set */
  private confirm(exercise: Exercise, counter: RepCounter, now: number): boolean {
    counter.reps -= 1;
    let c = this.candidate;
    if (c !== null && c.counter === counter && now - c.at <= SET_IDLE_SECONDS) {
      c.reps += 1;
      c.at = now;
    } else {
      c = this.candidate = { exercise, counter, reps: 1, at: now };
    }
    if (c.reps < EXERCISES[exercise].confirm_reps) return false;
    this.candidate = null;
    return this.begin(exercise, counter, now, c.reps);
  }

  /** Call after counter completed a rep of exercise. Returns true if it counts */
  addRep(now: number, exercise: Exercise, counter: RepCounter): boolean {
    const spec = EXERCISES[exercise];
    const starting = this.exercise !== exercise || this.resting(now);
    if (starting && spec.confirm_reps > 1) return this.confirm(exercise, counter, now);
    if (this.resting(now)) {
      if (spec.could_be_drinking) {
        counter.reps -= 1;
        if (this.pending === null) {
          this.pending = counter;
          this.pendingExercise = exercise;
        }
        return false;
      }
      this.nextSet(exercise, counter, now);
      return true;
    }
    if (exercise === this.exercise) {
      this.lastRep = now;
      this.history[this.history.length - 1]!.reps = this.setReps();
      return true;
    }
    if (this.exercise === null || this.canSwitch(exercise)) {
      // Never from press to curl (not_after): lowering a press looks like a curl
      this.startSet(exercise, counter, now, this.exercise !== null);
      return true;
    }
    counter.reps -= 1; // not the exercise this set is doing
    return false;
  }

  /** Call every frame. True when a held back curl turned out to be a real rep */
  checkPending(now: number): boolean {
    const counter = this.pending;
    if (counter === null) return false;
    if (counter.closest < DRINK_DISTANCE) {
      this.pending = this.pendingExercise = null; // drinking
      return false;
    }
    if (counter.stage === "down") {
      this.nextSet(this.pendingExercise!, counter, now);
      return true;
    }
    return false;
  }

  reset() {
    this.clearReps();
    this.exercise = null;
    this.set = 1;
    this.prevExercise = null;
    this.prevSet = 0;
    this.lastRep = null;
    this.pending = this.pendingExercise = this.candidate = null;
  }
}
