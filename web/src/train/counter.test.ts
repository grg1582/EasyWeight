// The browser must count exactly like the mirror. parity.json holds sessions of
// synthetic poses and what the Python counter (device/easyweight) made of
// them: replaying the same poses here must give the same reps, sets and events.
// To refresh it after changing the counting logic: python device/tests/web_parity.py

import { describe, expect, it } from "vitest";

import { Engine } from "./engine";
import { framesOf, parity } from "./parity";
import { Reporter, type WorkoutEvent } from "./reporter";

function replay(name: string) {
  const engine = new Engine();
  let n = 0;
  const reporter = new Reporter(undefined, () => `uuid-${++n}`);
  const events: WorkoutEvent[] = [];
  const counted: number[] = [];
  let t = parity.start;
  framesOf(name).forEach((landmarks, i) => {
    if (engine.step(landmarks, parity.size, parity.size, t)) counted.push(i);
    events.push(...reporter.observe(engine.workout, t));
    t += 1 / parity.fps;
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
