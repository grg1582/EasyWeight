// Tuning constants, the same as device/easyweight/config.py. Keep the two in
// step: the parity test (counter.test.ts) replays poses the Python counter
// counted and fails if this one counts differently.

export const CURL_DOWN_ANGLE = 150; // elbow angle that counts as "arm straight"
export const CURL_UP_ANGLE = 50; // elbow angle that counts as "fully curled"
export const RAISE_DOWN_ANGLE = 30; // shoulder angle (0 = arm hanging) that counts as "arm down"
export const RAISE_UP_ANGLE = 75; // shoulder angle that counts as "arm raised"
export const RAISE_MIN_ELBOW = 120; // a lateral raise keeps the elbow at least this straight
export const RAISE_MAX_ANGLE = 140; // and stays below this shoulder angle, so a press can't count
export const PRESS_DOWN_HEIGHT = 0.5; // wrist height above the shoulder (shoulder widths): at the shoulders
export const PRESS_UP_HEIGHT = 1.0; // wrist height above the shoulder: pressed overhead
export const MIN_VISIBILITY = 0.5; // ignore an arm when MediaPipe isn't confident it can see it
export const SMOOTHING = 0.4; // 0-1: lower = steadier but slower to react
export const SET_IDLE_SECONDS = 8; // no new rep for this long = the set is over and rest starts
export const MAX_REST_SECONDS = 180; // resting longer than this resets the count
export const AWAY_RESET_SECONDS = 10; // reset the count after nobody has been seen this long
export const DRINK_DISTANCE = 0.52; // a lift during rest closer than this to the mouth is drinking

export type Side = "left" | "right";
export type Exercise = "curl" | "raise" | "press";

// MediaPipe landmark numbers: shoulder, elbow, wrist (the person's own left/right)
export const ARMS: Record<Side, [number, number, number]> = {
  left: [11, 13, 15],
  right: [12, 14, 16],
};
export const SIDES: Side[] = ["left", "right"];
export const SHOULDERS: [number, number] = [11, 12];
export const MOUTH: [number, number] = [9, 10];
