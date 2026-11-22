// Turns what the Workout does into events for the backend: a port of
// device/easyweight/reporter.py. It compares the Workout with the last frame
// after every step, so the counting logic doesn't know the backend exists.

import { SIDES, type Exercise, type Side } from "./config";
import type { SetEntry, Workout } from "./counter";

export type WorkoutEvent =
  | { id: string; type: "workout_started"; at: string; data: { workout_id: string } }
  | {
      id: string;
      type: "set_started";
      at: string;
      data: { workout_id: string; set_id: string; exercise: Exercise; set_number: number };
    }
  | {
      id: string;
      type: "rep";
      at: string;
      data: { set_id: string; side: Side; count: number; top: number | null };
    }
  | { id: string; type: "set_ended"; at: string; data: { set_id: string; reps: number } }
  | { id: string; type: "workout_ended"; at: string; data: { workout_id: string } };

type EventType = WorkoutEvent["type"];
type DataOf<T extends EventType> = Extract<WorkoutEvent, { type: T }>["data"];

export class Reporter {
  workoutId: string | null = null;
  setId: string | null = null;
  private entry: SetEntry | null = null;
  private historyLength = 0;
  private sideReps: Record<Side, number> = { left: 0, right: 0 };
  private setOpen = false;
  private lastReps = 0;

  /** clock(now) turns the step's time into a real date. newId makes event ids */
  constructor(
    private readonly clock: (now: number) => Date = (now) => new Date(now * 1000),
    private readonly newId: () => string = () => crypto.randomUUID(),
  ) {}

  /** Call after every Engine.step. Returns the new events (often none) */
  observe(workout: Workout, now: number): WorkoutEvent[] {
    const events: WorkoutEvent[] = [];
    const at = this.clock(now).toISOString();
    const emit = <T extends EventType>(type: T, data: DataOf<T>) => {
      events.push({ id: this.newId(), type, at, data } as WorkoutEvent);
    };

    const history = workout.history;
    if (workout.exercise === null) {
      // reset, or nothing has happened yet
      if (this.workoutId !== null) {
        if (this.setOpen) emit("set_ended", { set_id: this.setId!, reps: this.lastReps });
        emit("workout_ended", { workout_id: this.workoutId });
        this.workoutId = this.setId = null;
        this.setOpen = false;
      }
      this.historyLength = history.length;
      return events;
    }

    const newSet = history.length > this.historyLength;
    if (newSet || history[history.length - 1] !== this.entry) {
      if (this.workoutId === null) {
        this.workoutId = this.newId();
        emit("workout_started", { workout_id: this.workoutId });
      }
      if (newSet || this.setId === null) this.setId = this.newId();
      const entry = history[history.length - 1]!;
      emit("set_started", {
        workout_id: this.workoutId,
        set_id: this.setId,
        exercise: entry.exercise,
        set_number: entry.set,
      });
      this.entry = entry;
      this.historyLength = history.length;
      this.sideReps = { left: 0, right: 0 };
      this.setOpen = true;
    }

    for (const side of SIDES) {
      const counter = workout.counters[workout.exercise][side];
      while (this.sideReps[side] < counter.reps) {
        this.sideReps[side] += 1;
        const top = counter.angle === null ? null : Math.round(counter.angle * 1000) / 1000;
        emit("rep", { set_id: this.setId!, side, count: this.sideReps[side], top });
      }
    }
    this.lastReps = workout.setReps();

    if (this.setOpen && workout.resting(now)) {
      emit("set_ended", { set_id: this.setId!, reps: this.lastReps });
      this.setOpen = false;
    }
    return events;
  }

  /** The events that close the workout now (the person pressed Stop) */
  finish(now: number): WorkoutEvent[] {
    const at = this.clock(now).toISOString();
    const events: WorkoutEvent[] = [];
    if (this.workoutId === null) return events;
    if (this.setOpen) {
      events.push({ id: this.newId(), type: "set_ended", at, data: { set_id: this.setId!, reps: this.lastReps } });
    }
    events.push({ id: this.newId(), type: "workout_ended", at, data: { workout_id: this.workoutId } });
    this.workoutId = this.setId = null;
    this.setOpen = false;
    return events;
  }
}
