import { describe, expect, it, vi } from "vitest";

import { framesOf, parity } from "./parity";
import type { WorkoutEvent } from "./reporter";
import { TrainingSession } from "./session";

function play(session: TrainingSession, name: string, start = 0) {
  let t = start;
  for (const landmarks of framesOf(name)) {
    session.step(landmarks, parity.size, parity.size, t);
    t += 1 / parity.fps;
  }
  return t;
}

describe("TrainingSession", () => {
  it("sends every event of the workout, in order, by the end", async () => {
    const sent: WorkoutEvent[] = [];
    const session = new TrainingSession(async (events) => {
      sent.push(...events);
    });
    const t = play(session, "rest then next set");
    await session.finish(t);
    expect(sent.map((e) => e.id)).toEqual(session.events.map((e) => e.id));
    expect(sent[0]!.type).toBe("workout_started");
    expect(sent[sent.length - 1]!.type).toBe("workout_ended");
    expect(session.unsent).toBe(0);
  });

  it("sends in batches while training, not once per frame", async () => {
    const send = vi.fn(async () => {});
    const session = new TrainingSession(send);
    play(session, "curls"); // about 5 seconds
    expect(send.mock.calls.length).toBeGreaterThan(0);
    expect(send.mock.calls.length).toBeLessThanOrEqual(3);
  });

  it("keeps events after a failed send, and sends them next time", async () => {
    let fail = true;
    const sent: WorkoutEvent[] = [];
    const session = new TrainingSession(async (events) => {
      if (fail) throw new Error("offline");
      sent.push(...events);
    });
    const t = play(session, "curls");
    await session.flush();
    expect(sent).toEqual([]);
    expect(session.failedSends).toBeGreaterThan(0);
    fail = false;
    await session.finish(t);
    expect(sent.map((e) => e.id)).toEqual(session.events.map((e) => e.id));
  });

  it("counts without sending when nothing is saved (the demo)", async () => {
    const session = new TrainingSession(null);
    const t = play(session, "curls");
    await session.finish(t);
    expect(session.engine.workout.history).toEqual([{ exercise: "curl", set: 1, reps: 10 }]);
    expect(session.unsent).toBe(0);
  });
});
