// One training session on the Train page: the counting (Engine), the events
// it makes (Reporter), and sending them to the backend.
//
// Events wait in a queue and go out in batches every few seconds, and once
// more when the session ends. If a send fails (say the connection dropped)
// they stay queued and go with the next one. Sending an event twice is
// harmless: the backend answers "duplicate".

import { Coach } from "./coach";
import { Engine } from "./engine";
import type { Landmark } from "./geometry";
import { Reporter, type WorkoutEvent } from "./reporter";

export type Send = (events: WorkoutEvent[]) => Promise<void>;

const SEND_EVERY_SECONDS = 3;
const MAX_BATCH = 500; // the backend's limit per request

export class TrainingSession {
  readonly engine = new Engine();
  /** Feedback on how the reps are done */
  readonly coach = new Coach();
  readonly reporter: Reporter;
  /** Every event so far, sent or not (the summary shows what was done) */
  readonly events: WorkoutEvent[] = [];
  private queue: WorkoutEvent[] = [];
  private sending: Promise<void> | null = null;
  private lastSend = -Infinity;
  failedSends = 0;

  /** send is null when nothing is saved (the demo account) */
  constructor(
    private readonly send: Send | null,
    clock?: (now: number) => Date,
  ) {
    this.reporter = new Reporter(clock);
  }

  /** One video frame. now is in seconds. Returns true when it counted a rep */
  step(landmarks: Landmark[] | null, width: number, height: number, now: number): boolean {
    const counted = this.engine.step(landmarks, width, height, now);
    this.coach.observe(this.engine.workout, now);
    this.add(this.reporter.observe(this.engine.workout, now));
    if (now - this.lastSend >= SEND_EVERY_SECONDS) {
      this.lastSend = now;
      void this.flush();
    }
    return counted;
  }

  /** The person pressed Stop: close the workout and send everything left */
  async finish(now: number): Promise<void> {
    this.add(this.reporter.finish(now));
    await this.flush();
    await this.sending; // a send started just before may still be running
    if (this.queue.length) await this.flush(); // and whatever it left behind
  }

  get unsent(): number {
    return this.queue.length;
  }

  private add(events: WorkoutEvent[]) {
    if (!events.length) return;
    this.events.push(...events);
    if (this.send) this.queue.push(...events);
  }

  /** Send what's queued, one request at a time */
  flush(): Promise<void> {
    if (!this.send || this.sending || !this.queue.length) return this.sending ?? Promise.resolve();
    const batch = this.queue.slice(0, MAX_BATCH);
    this.sending = this.send(batch)
      .then(() => {
        this.queue = this.queue.slice(batch.length);
        this.failedSends = 0;
      })
      .catch(() => {
        this.failedSends += 1; // kept in the queue for the next try
      })
      .finally(() => {
        this.sending = null;
      });
    return this.sending;
  }
}
