import { describe, expect, it } from "vitest";

import { Coach, CUE_SECONDS, SLOW_TEXT } from "./coach";
import { Workout } from "./counter";

const FPS = 30;

/** Moves the left arm's elbow through these angles (curl: 160 = straight,
 * 40 = curled), holding each for a few frames, as the engine would */
function play(workout: Workout, coach: Coach, angles: number[], start: number, hold = 6) {
  let t = start;
  const counter = workout.counters.curl.left;
  for (const angle of angles) {
    for (let i = 0; i < hold; i++) {
      if (counter.update(angle)) workout.addRep(t, "curl", counter);
      workout.checkPending(t);
      coach.observe(workout, t);
      t += 1 / FPS;
    }
  }
  return t;
}

const REP = [160, 120, 80, 40, 80, 120, 160];
const QUICK_REP = [170, 30, 30, 170, 170]; // held 3 frames each: half a second

describe("the coach", () => {
  it("says nothing about full reps at a steady pace", () => {
    const workout = new Workout();
    const coach = new Coach();
    play(workout, coach, [...REP, ...REP, ...REP], 0, 8); // about 1.9 seconds a rep
    expect(workout.setReps()).toBe(3);
    expect(coach.cue).toBeNull();
  });

  it("notices a rep that stopped halfway", () => {
    const workout = new Workout();
    const coach = new Coach();
    let t = play(workout, coach, REP, 0, 8);
    t = play(workout, coach, [160, 120, 90, 90, 120, 160], t, 8); // up to about 60%, and back
    expect(workout.setReps()).toBe(1); // not counted
    expect(coach.text(t)).toBe("Curl all the way up");
    expect(coach.partial).toBe(1);
    expect(coach.text(t + CUE_SECONDS + 0.1)).toBeNull();
  });

  it("doesn't mistake a small wobble for a partial rep", () => {
    const workout = new Workout();
    const coach = new Coach();
    const t = play(workout, coach, [...REP, 160, 140, 130, 140, 160], 0, 8);
    expect(coach.text(t)).toBeNull();
  });

  it("notices reps that are too fast", () => {
    const workout = new Workout();
    const coach = new Coach();
    const t = play(workout, coach, [...QUICK_REP, ...QUICK_REP], 0, 3);
    expect(workout.setReps()).toBe(2);
    expect(coach.text(t)).toBe("Slow down: control the weight");
    expect(coach.fast).toBe(1);
  });

  it("starts over for each set, and is quiet while resting", () => {
    const workout = new Workout();
    const coach = new Coach();
    let t = play(workout, coach, [...QUICK_REP, ...QUICK_REP], 0, 3);
    expect(coach.fast).toBe(1);
    t += 10; // a rest
    coach.observe(workout, t);
    expect(workout.resting(t)).toBe(true);
    t = play(workout, coach, [160, 120, 90, 120, 160], t, 8); // during the rest: not a rep yet
    expect(coach.partial).toBe(0);
    play(workout, coach, REP, t, 8);
    expect(workout.set).toBe(2);
    expect(coach.fast).toBe(0);
  });
});

/** Ten seconds without a rep: the set is over */
function rest(workout: Workout, coach: Coach, t: number) {
  t += 10;
  coach.observe(workout, t);
  expect(workout.resting(t)).toBe(true);
  return t;
}

describe("the coach after a set", () => {
  it("has nothing to sum up before the first rep", () => {
    expect(new Coach().summary(new Workout())).toBeNull();
  });

  it("gives a tip after a clean set", () => {
    const workout = new Workout();
    const coach = new Coach();
    rest(workout, coach, play(workout, coach, [...REP, ...REP, ...REP], 0, 8));
    expect(coach.summary(workout)).toEqual(["Clean set: 3 reps", "Tip: keep your elbows pinned to your sides"]);
  });

  it("gives a different tip each set", () => {
    const workout = new Workout();
    const coach = new Coach();
    let t = rest(workout, coach, play(workout, coach, [...REP, ...REP], 0, 8));
    t = rest(workout, coach, play(workout, coach, [...REP, ...REP], t, 8));
    expect(workout.set).toBe(2);
    expect(coach.summary(workout)).toEqual(["Clean set: 2 reps", "Tip: no swinging, keep your back still"]);
  });

  it("asks for the full range after partial reps", () => {
    const workout = new Workout();
    const coach = new Coach();
    const t = play(workout, coach, REP, 0, 8);
    rest(workout, coach, play(workout, coach, [160, 120, 90, 90, 120, 160], t, 8));
    expect(coach.summary(workout)).toEqual(["1 rep · 1 partial", "Next set: all the way up, all the way down"]);
  });

  it("asks to slow down after fast reps", () => {
    const workout = new Workout();
    const coach = new Coach();
    rest(workout, coach, play(workout, coach, [...QUICK_REP, ...QUICK_REP], 0, 3));
    expect(coach.summary(workout)).toEqual(["2 reps · 1 too fast", SLOW_TEXT]);
  });
});
