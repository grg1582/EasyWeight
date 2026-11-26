// The browser must count exactly like the mirror. parity.json holds sessions of
// synthetic poses and what the Python counter (device/easyweight) made of
// them: replaying the same poses here must give the same reps, sets and events.
// To refresh it after changing the counting logic: python device/tests/web_parity.py

import { describe, expect, it } from "vitest";

import * as config from "./config";
import { RepCounter, smoothingFactor, Workout } from "./counter";
import { Engine } from "./engine";
import { EXERCISES } from "./exercises";
import { framesOf, parity } from "./parity";
import { Reporter, type WorkoutEvent } from "./reporter";

function replay(name: string) {
  const engine = new Engine();
  let n = 0;
  const reporter = new Reporter(undefined, () => `uuid-${++n}`);
  const events: WorkoutEvent[] = [];
  const counted: number[] = [];
  const fps = parity.scenarios[name]!.fps;
  let t = parity.start;
  framesOf(name).forEach((landmarks, i) => {
    if (engine.step(landmarks, parity.size, parity.size, t)) counted.push(i);
    events.push(...reporter.observe(engine.workout, t));
    t += 1 / fps;
  });
  engine.reset();
  events.push(...reporter.observe(engine.workout, t));
  return { engine, events, counted };
}
/** Ids become id1, id2... in order of appearance, like the Python side did */
function relabel(events: WorkoutEvent[]) {
  const ids = new Map<string, string>();
  const label = (value: string) => {
    if (!ids.has(value)) ids.set(value, `id${ids.size + 1}`);
    return ids.get(value)!;
  };
  return events.map((event) => {
    const data: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(event.data)) {
      data[key] = key.endsWith("_id") ? label(value as string) : value;
    }
    return { id: label(event.id), type: event.type, at: Date.parse(event.at) / 1000, data };
  });
}

describe("counts the same as the mirror", () => {
  for (const [name, scenario] of Object.entries(parity.scenarios)) {
    it(name, () => {
      const { engine, events, counted } = replay(name);
      expect(engine.workout.history).toEqual(scenario.history);
      expect(counted).toEqual(scenario.counted);

      const ours = relabel(events);
      expect(ours.map(({ id, type }) => ({ id, type }))).toEqual(
        scenario.events.map(({ id, type }) => ({ id, type })),
      );
      ours.forEach((event, k) => {
        const theirs = scenario.events[k]!;
        // JavaScript dates have milliseconds, Python's microseconds
        expect(event.at).toBeCloseTo(theirs.at, 2);
        const { top, ...rest } = event.data as { top?: number | null };
        const { top: theirTop, ...theirRest } = theirs.data as { top?: number | null };
        expect(rest).toEqual(theirRest);
        if (typeof theirTop === "number") expect(top).toBeCloseTo(theirTop, 2);
        else expect(top ?? null).toEqual(theirTop ?? null);
      });
    });
  }
});

describe("tuned the same as the mirror", () => {
  it("has the same constants", () => {
    const ours = config as unknown as Record<string, unknown>;
    for (const [name, value] of Object.entries(parity.config)) expect(ours[name], name).toEqual(value);
    // and no number of its own the mirror doesn't have
    const numbers = Object.keys(ours).filter((k) => typeof ours[k] === "number");
    expect(numbers.sort()).toEqual(Object.keys(parity.config).filter((k) => k !== "LANDMARKS").sort());
  });

  it("has the same exercises", () => {
    expect(EXERCISES).toEqual(parity.exercises);
  });
});

describe("the rep counter", () => {
  const feed = (c: RepCounter, angles: number[]) => angles.filter((a) => c.update(a)).length;

  it("reacts as fast at any frame rate", () => {
    expect(smoothingFactor(1 / 30)).toBeCloseTo(0.4, 10);
    expect(smoothingFactor(2 / 30)).toBeCloseTo(1 - 0.6 ** 2, 10);
  });

  it("drops a one frame spike completely", () => {
    const c = new RepCounter(150, 50);
    feed(c, Array(10).fill(170));
    c.update(30);
    expect(c.angle).toBeCloseTo(170, 10);
  });

  it("starts its smoothing over after a long gap, keeping the rep under way", () => {
    const c = new RepCounter(150, 50);
    for (let i = 0; i < 10; i++) c.update(170, null, true, i / 30);
    c.update(100, null, true, 10 / 30 + 1);
    expect(c.angle).toBe(100);
    expect(c.stage).toBe("down");
  });
});

describe("whole body exercises", () => {
  it("have one counter, shown for both sides", () => {
    const w = new Workout();
    expect(Object.keys(w.counters.squat)).toEqual(["both"]);
    w.exercise = "squat";
    const [left, right] = w.arms();
    expect(left).toBe(w.counters.squat.both);
    expect(right).toBe(left);
  });

  it("start a squat set only on the second squat", () => {
    const w = new Workout();
    const squat = w.counters.squat.both!;
    squat.reps = 1;
    expect(w.addRep(0, "squat", squat)).toBe(false);
    expect(w.history).toEqual([]);
    squat.reps = 1;
    expect(w.addRep(3, "squat", squat)).toBe(true);
    expect(w.history).toEqual([{ exercise: "squat", set: 1, reps: 2 }]);
  });

  it("report each rep with side both", () => {
    const { events } = replay("push-ups");
    const reps = events.filter((e) => e.type === "rep");
    expect(reps).toHaveLength(10);
    expect(new Set(reps.map((e) => (e.data as { side: string }).side))).toEqual(new Set(["both"]));
  });
});

describe("finishing a workout by hand", () => {
  it("closes the open set and the workout", () => {
    const engine = new Engine();
    const reporter = new Reporter();
    let t = parity.start;
    for (const landmarks of framesOf("curls")) {
      engine.step(landmarks, parity.size, parity.size, t);
      reporter.observe(engine.workout, t);
      t += 1 / parity.fps;
    }
    const done = reporter.finish(t);
    expect(done.map((e) => e.type)).toEqual(["set_ended", "workout_ended"]);
    expect(done[0]!.data).toMatchObject({ reps: 10 });
    expect(reporter.finish(t)).toEqual([]); // nothing left to close
  });
});
