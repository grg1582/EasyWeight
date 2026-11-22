// Feeds one video frame's pose landmarks into a Workout: a port of
// device/easyweight/engine.py.

import {
  AWAY_RESET_SECONDS,
  MAX_REST_SECONDS,
  RAISE_MAX_ANGLE,
  RAISE_MIN_ELBOW,
  SIDES,
  type Exercise,
} from "./config";
import { Workout } from "./counter";
import { elbowAngle, jointHeight, mouthDistance, shoulderAngle, type Landmark } from "./geometry";

export class Engine {
  workout = new Workout();
  lastSeen: number | null = null; // time someone was last in front of the camera

  /** Process one frame: landmarks (33, or null when nobody is seen), the frame
   * size in pixels and the time in seconds. Returns true when a rep was counted */
  step(landmarks: Landmark[] | null, width: number, height: number, now: number): boolean {
    const workout = this.workout;
    this.lastSeen ??= now;
    let counted = false;

    for (const side of SIDES) {
      const lm = landmarks;
      const elbow = lm ? elbowAngle(lm, side, width, height) : null;
      const shoulder = lm ? shoulderAngle(lm, side, width, height) : null;
      const wrist = lm ? jointHeight(lm, side, 2, width, height) : null;
      const mouth = lm && elbow !== null ? mouthDistance(lm, side, width, height) : null;
      const raiseOk =
        elbow !== null && elbow > RAISE_MIN_ELBOW && shoulder !== null && shoulder < RAISE_MAX_ANGLE;
      const readings: [Exercise, number | null, boolean][] = [
        ["curl", elbow, true],
        ["raise", shoulder, raiseOk],
        ["press", wrist, true],
      ];
      for (const [exercise, angle, formOk] of readings) {
        const counter = workout.counters[exercise][side];
        if (counter.update(angle, mouth, formOk) && workout.addRep(now, exercise, counter)) {
          counted = true;
        }
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
