// Angles and distances measured from pose landmarks: a port of
// device/easyweight/geometry.py. Positions are turned into pixels first, so
// angles aren't squashed by the frame's shape.
//
// Functions that check visibility take `visible`: for each landmark, whether
// it is seen well enough (the engine keeps it, with hysteresis). Without it, a
// landmark is seen when its visibility is at least MIN_VISIBILITY.

import {
  ARMS,
  HIPS,
  LANDMARKS,
  MIN_VISIBILITY,
  MOUTH,
  SHOULDERS,
  TORSO_WIDTH_RATIO,
  type Joint,
  type Side,
} from "./config";
import type { Measure } from "./exercises";

export interface Landmark {
  x: number; // 0-1, a fraction of the frame
  y: number;
  visibility?: number | null;
}

type Point = [number, number];
export type Visible = boolean[] | null;

const toDegrees = (radians: number) => (radians * 180) / Math.PI;

/** Angle ABC in degrees, measured at point b */
export function angleAt(a: Point, b: Point, c: Point): number | null {
  const v1: Point = [a[0] - b[0], a[1] - b[1]];
  const v2: Point = [c[0] - b[0], c[1] - b[1]];
  const n1 = Math.hypot(...v1);
  const n2 = Math.hypot(...v2);
  if (n1 === 0 || n2 === 0) return null;
  const cos = (v1[0] * v2[0] + v1[1] * v2[1]) / (n1 * n2);
  return toDegrees(Math.acos(Math.max(-1, Math.min(1, cos))));
}

/** Landmark i. MediaPipe always gives all 33, so a missing one is a bug */
function landmark(lm: Landmark[], i: number): Landmark {
  const p = lm[i];
  if (!p) throw new Error(`Landmark ${i} is missing: expected 33, got ${lm.length}`);
  return p;
}

function seen(lm: Landmark[], i: number, visible: Visible): boolean {
  if (visible) return visible[i] ?? false;
  const v = landmark(lm, i).visibility;
  return v == null || v >= MIN_VISIBILITY;
}

/** How surely MediaPipe sees the least visible of these (1 when unknown) */
export function visibility(lm: Landmark[], ids: number[]): number {
  return Math.min(...ids.map((i) => landmark(lm, i).visibility ?? 1));
}

/** Pixel positions of these landmarks, or null if one of them can't be seen well */
function points(lm: Landmark[], ids: number[], width: number, height: number, visible: Visible): Point[] | null {
  const out: Point[] = [];
  for (const i of ids) {
    if (!seen(lm, i, visible)) return null;
    out.push(pixel(lm, i, width, height));
  }
  return out;
}

function pixel(lm: Landmark[], i: number, width: number, height: number): Point {
  const p = landmark(lm, i);
  return [p.x * width, p.y * height];
}

const dist = (a: Point, b: Point) => Math.hypot(a[0] - b[0], a[1] - b[1]);

function middle(ps: Point[]): Point {
  let x = 0;
  let y = 0;
  for (const p of ps) {
    x += p[0];
    y += p[1];
  }
  return [x / ps.length, y / ps.length];
}

export function shoulderWidth(lm: Landmark[], width: number, height: number): number {
  return dist(pixel(lm, SHOULDERS[0], width, height), pixel(lm, SHOULDERS[1], width, height));
}

/** [middle of the shoulders, middle of the hips], from the ones that are seen */
function torsoEnds(lm: Landmark[], width: number, height: number, visible: Visible): [Point, Point] | null {
  const shoulders = SHOULDERS.filter((i) => seen(lm, i, visible)).map((i) => pixel(lm, i, width, height));
  const hips = HIPS.filter((i) => seen(lm, i, visible)).map((i) => pixel(lm, i, width, height));
  if (!shoulders.length || !hips.length) return null;
  return [middle(shoulders), middle(hips)];
}

/** The length heights and distances are measured in: the shoulder width, but
 * at least TORSO_WIDTH_RATIO times the torso when the hips are seen (turned
 * sideways the shoulders get close together in the picture) */
export function bodyWidth(lm: Landmark[], width: number, height: number, visible: Visible = null): number {
  let shoulders = shoulderWidth(lm, width, height);
  const torso = torsoEnds(lm, width, height, visible);
  if (torso) shoulders = Math.max(shoulders, TORSO_WIDTH_RATIO * dist(torso[0], torso[1]));
  return shoulders;
}

/** How far the torso leans from upright: 0 = standing, 90 = lying down */
export function torsoAngle(lm: Landmark[], width: number, height: number, visible: Visible = null): number | null {
  const ends = torsoEnds(lm, width, height, visible);
  if (!ends) return null;
  const [s, [hx, hy]] = ends;
  return angleAt([hx, hy - 100], [hx, hy], s);
}

/** The landmarks a measure looks at */
export function measureIds(m: Measure, side: Side): number[] {
  if (m.kind === "torso") return [...SHOULDERS, ...HIPS];
  return m.points.map((n: Joint) => LANDMARKS[side][n]);
}

/** One measure (see exercises.ts) of one side, or null if it can't be seen */
export function measure(
  lm: Landmark[],
  m: Measure,
  side: Side,
  width: number,
  height: number,
  visible: Visible = null,
): number | null {
  if (m.kind === "torso") return torsoAngle(lm, width, height, visible);
  const p = points(lm, measureIds(m, side), width, height, visible);
  if (!p) return null;
  switch (m.kind) {
    case "angle":
      return angleAt(p[0]!, p[1]!, p[2]!);
    case "from_vertical": {
      const [ax, ay] = p[0]!;
      return angleAt([ax, ay + 100], [ax, ay], p[1]!);
    }
    case "height": {
      const unit = bodyWidth(lm, width, height, visible);
      return unit ? (p[1]![1] - p[0]![1]) / unit : null;
    }
  }
}

/** How far the wrist is from the mouth, in body widths */
export function mouthDistance(lm: Landmark[], side: Side, width: number, height: number, visible: Visible = null) {
  const left = pixel(lm, MOUTH[0], width, height);
  const right = pixel(lm, MOUTH[1], width, height);
  const mouth: Point = [(left[0] + right[0]) / 2, (left[1] + right[1]) / 2];
  const scale = bodyWidth(lm, width, height, visible);
  if (scale === 0) return null;
  return dist(pixel(lm, ARMS[side][2], width, height), mouth) / scale;
}
