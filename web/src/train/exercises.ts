// The exercises, as data: the same as device/easyweight/exercises.py, which
// explains each field. counter.test.ts checks the two are identical.

import * as cfg from "./config";
import type { CounterSide, Exercise, Joint } from "./config";

export type Measure =
  | { kind: "angle"; points: [Joint, Joint, Joint] }
  | { kind: "from_vertical"; points: [Joint, Joint] }
  | { kind: "height"; points: [Joint, Joint] } // in body widths
  | { kind: "torso" };

export interface Condition {
  measure: Measure;
  min?: number;
  max?: number;
  unseen?: boolean; // passes when the measure can't be seen
}

export interface ExerciseSpec {
  label: string;
  sides: "each" | "both";
  measure: Measure;
  down: number;
  up: number;
  form: Condition[];
  check: Condition | null;
  agree: number | null;
  could_be_drinking: boolean;
  confirm_reps: number;
  not_after: Exercise[];
  blocks: Exercise[];
  text: {
    partial: string;
    full_range: string;
    form: string | null;
    form_advice: string | null;
    tips: string[];
  };
}

const ARM_EXERCISES: Exercise[] = ["curl", "raise", "press"];
const TORSO: Measure = { kind: "torso" };
/** The arm exercises count only standing (or when the hips aren't seen) */
const UPRIGHT: Condition = { measure: TORSO, max: cfg.UPRIGHT_MAX_TORSO, unseen: true };

export const EXERCISES: Record<Exercise, ExerciseSpec> = {
  curl: {
    label: "BICEP CURLS",
    sides: "each",
    measure: { kind: "angle", points: ["shoulder", "elbow", "wrist"] },
    down: cfg.CURL_DOWN_ANGLE,
    up: cfg.CURL_UP_ANGLE,
    form: [UPRIGHT],
    check: null,
    agree: null,
    could_be_drinking: true,
    confirm_reps: 1,
    not_after: ["press"],
    blocks: [],
    text: {
      partial: "Curl all the way up",
      full_range: "Next set: all the way up, all the way down",
      form: null,
      form_advice: null,
      tips: [
        "Tip: keep your elbows pinned to your sides",
        "Tip: no swinging, keep your back still",
        "Tip: squeeze at the top, lower slowly",
      ],
    },
  },
  raise: {
    label: "LATERAL RAISES",
    sides: "each",
    measure: { kind: "from_vertical", points: ["shoulder", "elbow"] },
    down: cfg.RAISE_DOWN_ANGLE,
    up: cfg.RAISE_UP_ANGLE,
    form: [
      UPRIGHT,
      { measure: { kind: "angle", points: ["shoulder", "elbow", "wrist"] }, min: cfg.RAISE_MIN_ELBOW },
      { measure: { kind: "from_vertical", points: ["shoulder", "elbow"] }, max: cfg.RAISE_MAX_ANGLE },
    ],
    check: null,
    agree: null,
    could_be_drinking: false,
    confirm_reps: 1,
    not_after: [],
    blocks: [],
    text: {
      partial: "Raise to shoulder height",
      full_range: "Next set: lift to shoulder height every rep",
      form: null,
      form_advice: null,
      tips: [
        "Tip: lead with your elbows, not your hands",
        "Tip: stop at shoulder height",
        "Tip: keep a slight bend in your elbows",
      ],
    },
  },
  press: {
    label: "OVERHEAD PRESS",
    sides: "each",
    measure: { kind: "height", points: ["wrist", "shoulder"] },
    down: cfg.PRESS_DOWN_HEIGHT,
    up: cfg.PRESS_UP_HEIGHT,
    form: [UPRIGHT],
    check: null,
    agree: null,
    could_be_drinking: false,
    confirm_reps: 1,
    not_after: [],
    blocks: [],
    text: {
      partial: "Press all the way up",
      full_range: "Next set: arms straight at the top, every rep",
      form: null,
      form_advice: null,
      tips: [
        "Tip: brace your core, don't arch your back",
        "Tip: press straight up, biceps by your ears",
        "Tip: lower to chin height, no lower",
      ],
    },
  },
  squat: {
    label: "SQUATS",
    sides: "both",
    measure: { kind: "height", points: ["hip", "knee"] },
    down: cfg.SQUAT_DOWN_HEIGHT,
    up: cfg.SQUAT_UP_HEIGHT,
    form: [{ measure: TORSO, max: cfg.SQUAT_MAX_TORSO, unseen: true }],
    check: { measure: TORSO, max: 55 },
    agree: 0.3,
    could_be_drinking: false,
    confirm_reps: 2,
    not_after: [],
    blocks: ARM_EXERCISES,
    text: {
      partial: "Squat deeper: thighs to parallel",
      full_range: "Next set: thighs to parallel, every rep",
      form: "Chest up",
      form_advice: "Next set: chest up, back straight",
      tips: [
        "Tip: push your knees out over your toes",
        "Tip: keep your heels on the floor",
        "Tip: brace your core before you go down",
      ],
    },
  },
  pushup: {
    label: "PUSH-UPS",
    sides: "both",
    measure: { kind: "angle", points: ["shoulder", "elbow", "wrist"] },
    down: cfg.PUSHUP_DOWN_ANGLE,
    up: cfg.PUSHUP_UP_ANGLE,
    form: [{ measure: TORSO, min: cfg.PUSHUP_MIN_TORSO }],
    check: { measure: { kind: "angle", points: ["shoulder", "hip", "ankle"] }, min: 160 },
    agree: 25,
    could_be_drinking: false,
    confirm_reps: 1,
    not_after: [],
    blocks: [],
    text: {
      partial: "Go lower: elbows to 90°",
      full_range: "Next set: chest to the floor, every rep",
      form: "Keep your body in a straight line",
      form_advice: "Next set: squeeze your glutes, body straight",
      tips: [
        "Tip: elbows at 45°, not flared out",
        "Tip: squeeze your glutes the whole set",
        "Tip: chest to the floor, then lock out",
      ],
    },
  },
};

/** The counters an exercise has: left and right, or one for the whole body */
export function sidesOf(exercise: Exercise): CounterSide[] {
  return EXERCISES[exercise].sides === "each" ? [...cfg.SIDES] : ["both"];
}

/** Whether an exercise is counted once for the whole body (squats, push-ups) */
export const isWholeBody = (exercise: Exercise) => EXERCISES[exercise].sides === "both";
