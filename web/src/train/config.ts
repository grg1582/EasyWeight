// Tuning constants, the same as device/easyweight/config.py. Keep the two in
// step: parity.json holds the Python values, and counter.test.ts fails if
// these differ (and if the counting differs).

export const CURL_DOWN_ANGLE = 150; // elbow angle that counts as "arm straight"
export const CURL_UP_ANGLE = 50; // elbow angle that counts as "fully curled"
export const RAISE_DOWN_ANGLE = 30; // shoulder angle (0 = arm hanging) that counts as "arm down"
export const RAISE_UP_ANGLE = 75; // shoulder angle that counts as "arm raised"
export const RAISE_MIN_ELBOW = 120; // a lateral raise keeps the elbow at least this straight
export const RAISE_MAX_ANGLE = 140; // and stays below this shoulder angle, so a press can't count
export const PRESS_DOWN_HEIGHT = 0.5; // wrist height above the shoulder (body widths): at the shoulders
export const PRESS_UP_HEIGHT = 1.0; // wrist height above the shoulder: pressed overhead
export const SQUAT_DOWN_HEIGHT = 0.8; // hip height above the knee (body widths): standing (about 1.1 straight)
export const SQUAT_UP_HEIGHT = 0.4; // and at the bottom (0 = thighs level with the knees)
export const PUSHUP_DOWN_ANGLE = 145; // elbow angle: arms straight in a push-up
export const PUSHUP_UP_ANGLE = 105; // elbow angle: at the bottom (smoothing takes a few degrees off)

export const MIN_VISIBILITY = 0.5; // a landmark seen less surely than this is lost...
export const REGAIN_VISIBILITY = 0.6; // ...and only found again once seen this surely
export const SMOOTHING = 0.4; // 0-1 at 30 frames a second: lower = steadier but slower to react
export const SMOOTHING_FPS = 30; // the frame rate SMOOTHING is for
export const MAX_GAP_SECONDS = 0.5; // a limb out of sight longer than this starts its smoothing over
export const SET_IDLE_SECONDS = 8; // no new rep for this long = the set is over and rest starts
export const MAX_REST_SECONDS = 180; // resting longer than this resets the count
export const AWAY_RESET_SECONDS = 10; // reset the count after nobody has been seen this long
export const DRINK_DISTANCE = 0.52; // a lift during rest closer than this to the mouth is drinking
export const UPRIGHT_MAX_TORSO = 45; // arm exercises count only this close to upright (or hips unseen)
export const SQUAT_MAX_TORSO = 60; // a squat may lean forward this much at the bottom
export const PUSHUP_MIN_TORSO = 50; // a push-up: the torso at least this far from upright (lying down)
export const TORSO_WIDTH_RATIO = 0.75; // shoulder width is about this times the shoulder to hip length
export const BLOCK_AFTER_REP_SECONDS = 2; // after a squat's bottom, the arms don't count for this long

export type Side = "left" | "right";
/** A counter's side: an arm, or the whole body */
export type CounterSide = Side | "both";
export type Exercise = "curl" | "raise" | "press" | "squat" | "pushup";
export type Joint = "shoulder" | "elbow" | "wrist" | "hip" | "knee" | "ankle";

// MediaPipe landmark numbers (the person's own left/right)
export const LANDMARKS: Record<Side, Record<Joint, number>> = {
  left: { shoulder: 11, elbow: 13, wrist: 15, hip: 23, knee: 25, ankle: 27 },
  right: { shoulder: 12, elbow: 14, wrist: 16, hip: 24, knee: 26, ankle: 28 },
};
export const ARMS: Record<Side, [number, number, number]> = {
  left: [11, 13, 15],
  right: [12, 14, 16],
};
export const SIDES: Side[] = ["left", "right"];
export const SHOULDERS: [number, number] = [11, 12];
export const HIPS: [number, number] = [23, 24];
export const MOUTH: [number, number] = [9, 10];
