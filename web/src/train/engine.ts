// Feeds one video frame's pose landmarks into a Workout: a port of
// device/easyweight/engine.py. Every exercise in exercises.ts is watched all
// the time, on each side it counts.

import {
  AWAY_RESET_SECONDS,
  BLOCK_AFTER_REP_SECONDS,
  MAX_REST_SECONDS,
  MIN_VISIBILITY,
  REGAIN_VISIBILITY,
  SIDES,
  type CounterSide,
  type Exercise,
  type Side,
} from "./config";
import { Workout } from "./counter";
import { EXERCISES, sidesOf, type Condition, type Measure } from "./exercises";
import { measure, measureIds, mouthDistance, visibility, type Landmark } from "./geometry";

const ALL = Object.keys(EXERCISES) as Exercise[];
/** The order counters are fed in a frame: arm by arm, then the whole body ones */
const ORDER: [Exercise, CounterSide][] = [
  ...SIDES.flatMap((side) =>
    ALL.filter((e) => EXERCISES[e].sides === "each").map((e): [Exercise, CounterSide] => [e, side]),
  ),
  ...ALL.filter((e) => EXERCISES[e].sides === "both").map((e): [Exercise, CounterSide] => [e, "both"]),
];

/** Whether a reading meets a condition's min and max. unseen when it's null */
function passes(value: number | null, condition: Condition, unseen: boolean): boolean {
  if (value === null) return unseen;
  return (condition.min ?? -Infinity) <= value && value <= (condition.max ?? Infinity);
}

export class Engine {
  workout = new Workout();
  lastSeen: number | null = null; // time someone was last in front of the camera
  /** Per landmark: seen well enough, with hysteresis */
  visible: boolean[] = [];

  /** A landmark is lost below MIN_VISIBILITY and found again only at
   * REGAIN_VISIBILITY, so one hovering around the line doesn't come and go */
  private see(landmarks: Landmark[] | null) {
    if (!landmarks) {
      this.visible = [];
      return;
    }
    const before = this.visible;
    this.visible = landmarks.map((lm, i) => {
      const v = lm.visibility;
      return v == null || v >= REGAIN_VISIBILITY || ((before[i] ?? false) && v >= MIN_VISIBILITY);
    });
  }

  /** A measure on the given sides. With two: the average when they're within
   * agree of each other, otherwise the better seen side */
  private read(lm: Landmark[], m: Measure, sides: Side[], width: number, height: number, agree: number | null = null) {
    const values: [number, number][] = [];
    for (const side of sides) {
      const value = measure(lm, m, side, width, height, this.visible);
      if (value !== null) values.push([value, visibility(lm, measureIds(m, side))]);
    }
    if (!values.length) return null;
    if (values.length === 2 && agree !== null && Math.abs(values[0]![0] - values[1]![0]) <= agree) {
      return (values[0]![0] + values[1]![0]) / 2;
    }
    return values.reduce((best, v) => (v[1] > best[1] ? v : best))[0];
  }

  /** The exercises that don't count now, because a squat is under way */
  private blocked(now: number): Set<Exercise> {
    const blocked = new Set<Exercise>();
    for (const exercise of ALL) {
      const spec = EXERCISES[exercise];
      for (const side of sidesOf(exercise)) {
        const counter = this.workout.counters[exercise][side]!;
        if (!(spec.blocks.length && counter.visible && counter.progress() > 0)) continue;
        const justDone = counter.repAt !== null && now - counter.repAt < BLOCK_AFTER_REP_SECONDS;
        if (counter.stage === "down" || justDone) for (const e of spec.blocks) blocked.add(e);
      }
    }
    return blocked;
  }

  /** Process one frame: landmarks (33, or null when nobody is seen), the frame
   * size in pixels and the time in seconds. Returns true when a rep was counted */
  step(landmarks: Landmark[] | null, width: number, height: number, now: number): boolean {
    const workout = this.workout;
    this.lastSeen ??= now;
    this.see(landmarks);
    let counted = false;
    const blocked = this.blocked(now);

    for (const [exercise, side] of ORDER) {
      const spec = EXERCISES[exercise];
      const counter = workout.counters[exercise][side]!;
      if (!landmarks) {
        counter.update(null, null, true, now);
        continue;
      }
      const sides: Side[] = side === "both" ? SIDES : [side];
      const reading = this.read(landmarks, spec.measure, sides, width, height, spec.agree);
      const formOk =
        !blocked.has(exercise) &&
        spec.form.every((f) => passes(this.read(landmarks, f.measure, sides, width, height), f, f.unseen ?? false));
      const check = spec.check;
      const checkOk = check === null || passes(this.read(landmarks, check.measure, sides, width, height), check, true);
      const mouth =
        side !== "both" && reading !== null ? mouthDistance(landmarks, side, width, height, this.visible) : null;
      if (counter.update(reading, mouth, formOk, now, checkOk) && workout.addRep(now, exercise, counter)) {
        counted = true;
      }
    }
    if (workout.checkPending(now)) counted = true;

    // Nobody in front of the camera for a while, or a rest that went on too long
    if (landmarks) this.lastSeen = now;
    else if (now - this.lastSeen > AWAY_RESET_SECONDS) workout.reset();
    if (workout.resting(now) && workout.restTime(now) > MAX_REST_SECONDS) workout.reset();
    return counted;
  }

  reset() {
    this.workout.reset();
  }
}
