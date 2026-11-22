// Angles and distances measured from pose landmarks: a port of
// device/easyweight/geometry.py. Positions are turned into pixels first, so
// angles aren't squashed by the frame's shape.

import { ARMS, MIN_VISIBILITY, MOUTH, SHOULDERS, type Side } from "./config";

export interface Landmark {
  x: number; // 0-1, a fraction of the frame
  y: number;
  visibility?: number | null;
}

type Point = [number, number];

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

/** Pixel positions of these landmarks, or null if one of them can't be seen well */
function armPoints(lm: Landmark[], ids: number[], width: number, height: number): Point[] | null {
  const points: Point[] = [];
  for (const i of ids) {
    const p = landmark(lm, i);
    if (p.visibility != null && p.visibility < MIN_VISIBILITY) return null;
    points.push([p.x * width, p.y * height]);
  }
  return points;
}

function pixel(lm: Landmark[], i: number, width: number, height: number): Point {
  const p = landmark(lm, i);
  return [p.x * width, p.y * height];
}

const dist = (a: Point, b: Point) => Math.hypot(a[0] - b[0], a[1] - b[1]);

export function shoulderWidth(lm: Landmark[], width: number, height: number): number {
  return dist(pixel(lm, SHOULDERS[0], width, height), pixel(lm, SHOULDERS[1], width, height));
}

/** Elbow angle for one arm (about 180 = straight), or null if it can't be seen */
export function elbowAngle(lm: Landmark[], side: Side, width: number, height: number) {
  const points = armPoints(lm, ARMS[side], width, height);
  return points ? angleAt(points[0]!, points[1]!, points[2]!) : null;
}

/** How far the upper arm is raised out to the side: 0 = hanging down, 90 = level */
export function shoulderAngle(lm: Landmark[], side: Side, width: number, height: number) {
  const points = armPoints(lm, ARMS[side].slice(0, 2), width, height);
  if (!points) return null;
  const [sx, sy] = points[0]!;
  return angleAt([sx, sy + 100], [sx, sy], points[1]!);
}

/** How far a joint of the arm (1 = elbow, 2 = wrist) is above the shoulder, in
 * shoulder widths (negative = below it) */
export function jointHeight(
  lm: Landmark[],
  side: Side,
  joint: 1 | 2,
  width: number,
  height: number,
) {
  const points = armPoints(lm, [ARMS[side][0], ARMS[side][joint]], width, height);
  if (!points) return null;
  const shoulders = shoulderWidth(lm, width, height);
  if (shoulders === 0) return null;
  return (points[0]![1] - points[1]![1]) / shoulders;
}

/** How far the wrist is from the mouth, in shoulder widths */
export function mouthDistance(lm: Landmark[], side: Side, width: number, height: number) {
  const left = pixel(lm, MOUTH[0], width, height);
  const right = pixel(lm, MOUTH[1], width, height);
  const mouth: Point = [(left[0] + right[0]) / 2, (left[1] + right[1]) / 2];
  const shoulders = shoulderWidth(lm, width, height);
  if (shoulders === 0) return null;
  return dist(pixel(lm, ARMS[side][2], width, height), mouth) / shoulders;
}
