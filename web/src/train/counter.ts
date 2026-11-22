// Rep and set logic: a port of device/easyweight/counter.py. It takes numbers
// and returns numbers, so it's tested without a camera or the pose model.

import {
  CURL_DOWN_ANGLE,
  CURL_UP_ANGLE,
  DRINK_DISTANCE,
  PRESS_DOWN_HEIGHT,
  PRESS_UP_HEIGHT,
  RAISE_DOWN_ANGLE,
  RAISE_UP_ANGLE,
  SET_IDLE_SECONDS,
  SIDES,
  SMOOTHING,
  type Exercise,
  type Side,
} from "./config";

/** One arm doing one exercise: the angle goes past downAngle, then past upAngle
 * = 1 rep. For a curl the elbow angle gets smaller on the way up, for a raise
 * the shoulder angle gets bigger, for a press the wrist height gets bigger */
export class ArmCounter {
  readonly sign: number; // 1 = the angle shrinks on the way up
  reps = 0;
  angle: number | null = null; // smoothed
  stage: "down" | "up" | null = null;
  visible = false;
  mouth: number | null = null;
  closest = Infinity; // closest the wrist came to the mouth since the arm was down
  top: number | null = null; // furthest up the angle got since the arm was down

  constructor(
    readonly downAngle: number,
    readonly upAngle: number,
  ) {
    this.sign = downAngle > upAngle ? 1 : -1;
  }

  /** Feed one reading (or null). Returns true when this reading completes a rep */
  update(rawAngle: number | null, mouth: number | null = null, formOk = true): boolean {
    this.visible = rawAngle !== null;
    this.mouth = mouth;
    if (rawAngle === null) return false;
    if (mouth !== null) this.closest = Math.min(this.closest, mouth);
    this.angle = this.angle === null ? rawAngle : this.angle + SMOOTHING * (rawAngle - this.angle);
    if (this.top === null || this.sign * (this.angle - this.top) < 0) this.top = this.angle;
    if (this.sign * (this.angle - this.downAngle) > 0) {
      this.stage = "down";
      this.closest = Infinity;
      this.top = null;
    } else if (this.sign * (this.angle - this.upAngle) < 0 && this.stage === "down" && formOk) {
      this.stage = "up";
      this.reps += 1;
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

type Pair = Record<Side, ArmCounter>;

const pair = (down: number, up: number): Pair => ({
  left: new ArmCounter(down, up),
  right: new ArmCounter(down, up),
});

/** Splits the reps into sets and knows which exercise each set is. See the
 * Python Workout for the full story: the first rep of a set decides the
 * exercise, no rep for SET_IDLE_SECONDS means resting, and a curl during rest
 * is held back until it's clear it isn't drinking */
export class Workout {
  readonly counters: Record<Exercise, Pair> = {
    curl: pair(CURL_DOWN_ANGLE, CURL_UP_ANGLE),
    raise: pair(RAISE_DOWN_ANGLE, RAISE_UP_ANGLE),
    press: pair(PRESS_DOWN_HEIGHT, PRESS_UP_HEIGHT),
  };
  /** Every set since the start. reset() doesn't clear it */
  readonly history: SetEntry[] = [];
  exercise: Exercise | null = null;
  set = 1;
  prevExercise: Exercise | null = null;
  prevSet = 0;
  lastRep: number | null = null;
  pending: ArmCounter | null = null;

  constructor() {
    this.reset();
  }

  /** The (left, right) counters to show: the set's exercise, or before the
   * first rep, whichever exercise the arms are further into */
  arms(): [ArmCounter, ArmCounter] {
    let chosen: Pair;
    if (this.exercise) {
      chosen = this.counters[this.exercise];
    } else {
      const score = (p: Pair) => Math.max(p.left.progress(), p.right.progress());
      chosen = Object.values(this.counters).reduce((best, p) => (score(p) > score(best) ? p : best));
    }
    return [chosen.left, chosen.right];
  }

  clearReps() {
    for (const p of Object.values(this.counters)) for (const side of SIDES) p[side].reps = 0;
  }

  setReps(): number {
    const p = this.counters[this.exercise as Exercise];
    return Math.max(p.left.reps, p.right.reps);
  }

  resting(now: number): boolean {
    return this.lastRep !== null && now - this.lastRep > SET_IDLE_SECONDS;
  }

  restTime(now: number): number {
    return now - (this.lastRep ?? now);
  }

  startSet(exercise: Exercise, counter: ArmCounter, now: number, replace = false) {
    this.set = exercise === this.prevExercise ? this.prevSet + 1 : 1;
    this.exercise = exercise;
    this.clearReps();
    counter.reps = 1;
    this.lastRep = now;
    this.pending = null;
    const entry: SetEntry = { exercise, set: this.set, reps: 1 };
    if (replace && this.history.length) this.history[this.history.length - 1] = entry;
    else this.history.push(entry);
  }

  nextSet(exercise: Exercise, counter: ArmCounter, now: number) {
    this.prevExercise = this.exercise;
    this.prevSet = this.set;
    this.startSet(exercise, counter, now);
  }

  /** Call after counter completed a rep of exercise. Returns true if it counts */
  addRep(now: number, exercise: Exercise, counter: ArmCounter): boolean {
    if (this.resting(now)) {
      if (exercise === "curl") {
        counter.reps -= 1;
        this.pending ??= counter;
        return false;
      }
      this.nextSet(exercise, counter, now);
      return true;
    }
    if (this.exercise === null) {
      this.startSet(exercise, counter, now);
      return true;
    }
    if (exercise === this.exercise) {
      this.lastRep = now;
      this.history[this.history.length - 1]!.reps = this.setReps();
      return true;
    }
    if (this.setReps() < 2 && !(this.exercise === "press" && exercise === "curl")) {
      // One rep isn't enough to be sure: the first "curl" is often picking up
      // the weights. But never from press to curl: lowering a press looks like a curl
      this.startSet(exercise, counter, now, true);
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
      this.pending = null; // drinking
      return false;
    }
    if (counter.stage === "down") {
      this.nextSet("curl", counter, now);
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
    this.pending = null;
  }
}
