import { useQueryClient } from "@tanstack/react-query";
import { type RefObject, useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { ExerciseTag, PageHeader, Spinner } from "../components/ui";
import { EXERCISES, formatNumber } from "../lib/format";
import { ARMS, SHOULDERS, SIDES, type Exercise } from "../train/config";
import type { Summary } from "../train/coach";
import type { SetEntry } from "../train/counter";
import type { Landmark } from "../train/geometry";
import { loadPoseDetector, type PoseDetector } from "../train/pose";
import type { WorkoutEvent } from "../train/reporter";
import { TrainingSession } from "../train/session";

/** What the page needs from the outside world. Tests pass fakes */
export interface TrainDeps {
  loadDetector: () => Promise<PoseDetector>;
  openCamera: () => Promise<MediaStream>;
}

const realDeps: TrainDeps = {
  loadDetector: loadPoseDetector,
  openCamera: async () => {
    if (!navigator.mediaDevices?.getUserMedia) {
      throw new Error(
        "This browser can't use the camera here. Open the site over https, in a recent browser.",
      );
    }
    return navigator.mediaDevices.getUserMedia({
      video: { facingMode: "user", width: { ideal: 1280 }, height: { ideal: 720 } },
      audio: false,
    });
  },
};

const sendEvents = (events: WorkoutEvent[]) =>
  api<unknown>("/events/browser", { method: "POST", json: { events } }).then(() => undefined);

/** What the screen shows, taken from the session a few times a second */
interface View {
  seen: boolean; // someone is in front of the camera
  exercise: Exercise | null;
  set: number;
  reps: number;
  resting: number | null; // seconds of rest, or null while training
  flash: boolean; // a rep was just counted: the count lights up green, as on the mirror
  cue: string | null; // feedback on the reps, like "Curl all the way up"
  summary: Summary | null; // during the rest: how the set went, and what to do next
  progress: [number, number]; // left and right arm: 0 = down, 1 = up
  history: SetEntry[];
  unsent: number;
  failedSends: number;
}

const FLASH_SECONDS = 0.35; // as long as the mirror's

function snapshot(session: TrainingSession, seen: boolean, now: number): View {
  const workout = session.engine.workout;
  const [left, right] = workout.arms();
  const resting = workout.resting(now);
  return {
    seen,
    exercise: workout.exercise,
    set: workout.set,
    reps: workout.exercise ? workout.setReps() : 0,
    resting: resting ? workout.restTime(now) : null,
    flash: !resting && workout.lastRep !== null && now - workout.lastRep < FLASH_SECONDS,
    cue: resting ? null : session.coach.text(now),
    summary: resting ? session.coach.summary(workout) : null,
    progress: [left.progress(), right.progress()],
    history: workout.history.map((entry) => ({ ...entry })),
    unsent: session.unsent,
    failedSends: session.failedSends,
  };
}

function cameraError(error: unknown): string {
  if (error instanceof DOMException) {
    if (error.name === "NotAllowedError") {
      return "The camera is blocked. Allow it in your browser (the camera icon in the address bar), then try again.";
    }
    if (error.name === "NotFoundError") return "No camera was found on this device.";
    if (error.name === "NotReadableError") {
      return "The camera is busy. Close other apps or tabs that use it, then try again.";
    }
  }
  return error instanceof Error ? error.message : "Couldn't start the camera.";
}

/** The arms (what the counting looks at) on top of the video */
function drawArms(canvas: HTMLCanvasElement, landmarks: Landmark[] | null, width: number, height: number) {
  if (canvas.width !== width) canvas.width = width;
  if (canvas.height !== height) canvas.height = height;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  ctx.clearRect(0, 0, width, height);
  if (!landmarks) return;
  const at = (i: number) => {
    const point = landmarks[i]!;
    return [point.x * width, point.y * height] as const;
  };
  const scale = Math.max(2, width / 320);
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  const line = (ids: number[]) => {
    ctx.beginPath();
    ids.forEach((i, k) => (k ? ctx.lineTo(...at(i)) : ctx.moveTo(...at(i))));
    ctx.strokeStyle = "rgba(0, 0, 0, 0.45)";
    ctx.lineWidth = scale * 2.6;
    ctx.stroke();
    ctx.strokeStyle = "#ffffff";
    ctx.lineWidth = scale * 1.4;
    ctx.stroke();
  };
  line([...SHOULDERS]);
  for (const side of SIDES) line(ARMS[side]);
  for (const i of [...ARMS.left, ...ARMS.right]) {
    ctx.beginPath();
    ctx.arc(...at(i), scale * 3, 0, Math.PI * 2);
    ctx.fillStyle = "#2a78d6";
    ctx.fill();
    ctx.lineWidth = scale;
    ctx.strokeStyle = "#ffffff";
    ctx.stroke();
  }
}

function ArmMeter({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-center gap-3 text-sm">
      <span className="w-10 text-muted">{label}</span>
      <div
        className="h-2 flex-1 rounded-full bg-line"
        role="meter"
        aria-label={`${label} arm`}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(value * 100)}
      >
        <div
          className="h-2 rounded-full bg-accent transition-[width] duration-100"
          style={{ width: `${Math.round(value * 100)}%` }}
        />
      </div>
    </div>
  );
}

function SetList({ history }: { history: SetEntry[] }) {
  if (!history.length) return <p className="text-sm text-muted">No sets yet.</p>;
  return (
    <ol className="divide-y divide-line" aria-label="Sets">
      {history.map((entry, k) => (
        <li key={k} className="flex items-center justify-between py-2 text-sm">
          <span className="flex items-center gap-3">
            <span className="w-12 text-muted">Set {entry.set}</span>
            <ExerciseTag exercise={entry.exercise} />
          </span>
          <span className="font-semibold tabular-nums">
            {entry.reps} {entry.reps === 1 ? "rep" : "reps"}
          </span>
        </li>
      ))}
    </ol>
  );
}

/** A hint while there's nothing to count yet */
function status(view: View): string | null {
  if (!view.seen) return "Step into view: head to waist, both arms";
  if (!view.exercise) return "Ready: start your first rep";
  return null;
}

const pad = (n: number) => String(n).padStart(2, "0");

/** Seconds as the mirror shows them: 0:42, 2:05 */
export function restClock(seconds: number): string {
  const whole = Math.max(0, Math.floor(seconds));
  return `${Math.floor(whole / 60)}:${pad(whole % 60)}`;
}

/** The mirror's display on top of the camera: the time and date, the
 * exercise, and the rep count, or after 8 seconds without a rep, the rest timer */
function MirrorHud({ view }: { view: View }) {
  const now = new Date();
  return (
    <div className="mirror-text pointer-events-none absolute inset-0">
      <div className="absolute left-[3cqw] top-[4cqh]">
        <div className="mirror-clock">
          {pad(now.getHours())}:{pad(now.getMinutes())}
        </div>
        <div className="mirror-small mt-1">
          {pad(now.getDate())}/{pad(now.getMonth() + 1)}/{now.getFullYear()}
        </div>
      </div>
      <div className="mirror-label absolute right-[3cqw] top-[4cqh] font-semibold tracking-normal text-[color:var(--mirror-cyan)]">
        EasyWeight
      </div>
      {view.exercise && (
        <div className="mirror-label absolute left-1/2 top-[7cqh] -translate-x-1/2 -translate-y-1/2 whitespace-nowrap tracking-normal">
          {EXERCISES[view.exercise].name}
        </div>
      )}
      <div className="absolute left-1/2 top-[24%] -translate-x-1/2 -translate-y-1/2">
        {view.resting !== null ? (
          <span className="mirror-big text-[color:var(--mirror-cyan)]" aria-label="Rest time" role="timer">
            {restClock(view.resting)}
          </span>
        ) : (
          <span
            className={`mirror-big ${view.flash ? "text-[color:var(--mirror-green)]" : ""}`}
            aria-label="Reps"
          >
            {view.reps}
          </span>
        )}
      </div>
      <div className="mirror-label absolute left-1/2 top-[41%] -translate-x-1/2 -translate-y-1/2 whitespace-nowrap">
        {view.resting !== null ? `REST · SET ${view.set} DONE` : `SET ${view.set}`}
      </div>
      {view.cue && (
        <div
          role="status"
          className="mirror-label absolute left-1/2 top-[50%] -translate-x-1/2 -translate-y-1/2 whitespace-nowrap font-semibold tracking-normal text-[color:var(--mirror-amber)]"
        >
          {view.cue}
        </div>
      )}
      {view.summary && (
        <div
          role="status"
          aria-label="How the set went"
          className="mirror-label absolute left-1/2 top-[48%] w-[92%] -translate-x-1/2 space-y-[1.2cqh] text-center tracking-normal"
        >
          <p className="font-semibold text-white">{view.summary[0]}</p>
          <p
            className={`font-semibold ${view.summary[1].startsWith("Tip") ? "text-white" : "text-[color:var(--mirror-amber)]"}`}
          >
            {view.summary[1]}
          </p>
        </div>
      )}
    </div>
  );
}

/** Full screen for the camera view. Where a page can't go full screen
 * (Safari on iPhone), the view fills the window instead */
function useFullscreen(ref: RefObject<HTMLElement | null>) {
  const [full, setFull] = useState(false);
  const native = useRef(false);

  useEffect(() => {
    const sync = () => {
      if (native.current && !document.fullscreenElement) {
        native.current = false; // left with Esc or the browser's own button
        setFull(false);
      }
    };
    document.addEventListener("fullscreenchange", sync);
    return () => document.removeEventListener("fullscreenchange", sync);
  }, []);

  // Filling the window: Esc leaves, and the page behind doesn't scroll
  useEffect(() => {
    if (!full || native.current) return;
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && setFull(false);
    window.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [full]);

  const exit = useCallback(() => {
    if (native.current && document.fullscreenElement) void document.exitFullscreen();
    native.current = false;
    setFull(false);
  }, []);

  const enter = async () => {
    const element = ref.current;
    if (element?.requestFullscreen && document.fullscreenEnabled) {
      try {
        native.current = true;
        await element.requestFullscreen();
        setFull(true);
        return;
      } catch {
        native.current = false;
      }
    }
    setFull(true);
  };

  return { full, toggle: () => (full ? exit() : void enter()), exit };
}

type Phase =
  | { name: "intro" }
  | { name: "starting"; step: string }
  | { name: "running" }
  | { name: "done"; history: SetEntry[]; saved: boolean | null }
  | { name: "error"; message: string };

export function TrainPage({ deps = realDeps }: { deps?: TrainDeps }) {
  const { user } = useAuth();
  const saving = !user?.is_demo;
  const queryClient = useQueryClient();
  const [phase, setPhase] = useState<Phase>({ name: "intro" });
  const [view, setView] = useState<View | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const stageRef = useRef<HTMLElement>(null);
  const fullscreen = useFullscreen(stageRef);
  const live = useRef<{
    stream: MediaStream;
    detector: PoseDetector;
    session: TrainingSession;
    frame: number;
  } | null>(null);

  /** Stops the camera and the loop. Returns the session, to finish it */
  const stopCamera = useCallback(() => {
    const current = live.current;
    if (!current) return null;
    live.current = null;
    cancelAnimationFrame(current.frame);
    current.stream.getTracks().forEach((track) => track.stop());
    current.detector.close();
    return current.session;
  }, []);

  const start = async () => {
    try {
      setPhase({ name: "starting", step: "Loading the pose model" });
      const detector = await deps.loadDetector();
      setPhase({ name: "starting", step: "Waiting for the camera" });
      let stream: MediaStream;
      try {
        stream = await deps.openCamera();
      } catch (error) {
        detector.close();
        throw error;
      }
      const clock = (now: number) => new Date(performance.timeOrigin + now * 1000);
      const session = new TrainingSession(saving ? sendEvents : null, clock);
      live.current = { stream, detector, session, frame: 0 };
      setView(snapshot(session, false, performance.now() / 1000));
      setPhase({ name: "running" });
    } catch (error) {
      setPhase({ name: "error", message: cameraError(error) });
    }
  };

  // The loop: every new video frame goes through the pose model and the counter
  useEffect(() => {
    if (phase.name !== "running" || !live.current) return;
    const video = videoRef.current!;
    const canvas = canvasRef.current!;
    const { stream } = live.current;
    video.srcObject = stream;
    const playing = video.play?.() as Promise<void> | undefined; // undefined in old browsers
    playing?.catch(() => {}); // autoplay refused: muted video normally isn't
    let lastVideoTime = -1;
    let lastTimestamp = 0;
    let lastView = 0;
    const tick = () => {
      const current = live.current;
      if (!current) return;
      if (video.readyState >= 2 && video.currentTime !== lastVideoTime && video.videoWidth) {
        lastVideoTime = video.currentTime;
        const nowMs = performance.now();
        lastTimestamp = Math.max(Math.round(nowMs), lastTimestamp + 1); // must keep increasing
        const landmarks = current.detector.detect(video, lastTimestamp);
        const width = video.videoWidth;
        const height = video.videoHeight;
        const counted = current.session.step(landmarks, width, height, nowMs / 1000);
        drawArms(canvas, landmarks, width, height);
        if (counted || nowMs - lastView > 100) {
          lastView = nowMs;
          setView(snapshot(current.session, landmarks !== null, nowMs / 1000));
        }
      }
      current.frame = requestAnimationFrame(tick);
    };
    live.current.frame = requestAnimationFrame(tick);
  }, [phase.name]);

  // Leaving the page mid-workout: stop the camera, close and send the workout
  useEffect(
    () => () => {
      void stopCamera()?.finish(performance.now() / 1000);
    },
    [stopCamera],
  );

  const stop = async () => {
    const session = stopCamera();
    if (!session) return;
    fullscreen.exit();
    const history = session.engine.workout.history.map((entry) => ({ ...entry }));
    setPhase({ name: "done", history, saved: saving ? null : false });
    await session.finish(performance.now() / 1000);
    if (saving) {
      setPhase({ name: "done", history, saved: session.unsent === 0 });
      void queryClient.invalidateQueries({ queryKey: ["workouts"] });
      void queryClient.invalidateQueries({ queryKey: ["stats"] });
      void queryClient.invalidateQueries({ queryKey: ["devices"] });
    }
  };

  return (
    <>
      <PageHeader
        title="Train"
        subtitle="Count your reps with your camera, right here in the browser"
      />

      {phase.name === "intro" && (
        <div className="grid gap-6 lg:grid-cols-[1fr_20rem]">
          <section className="card p-6">
            <h2 className="text-lg font-semibold">How it works</h2>
            <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm text-muted">
              <li>Put your phone or laptop where the camera sees you from the head to the waist.</li>
              <li>
                Do <ExerciseTag exercise="curl" />, <ExerciseTag exercise="raise" /> or{" "}
                <ExerciseTag exercise="press" />. The first rep tells which one.
              </li>
              <li>Rest about 8 seconds between sets: the next rep starts the next set.</li>
              <li>Press Stop when you're done.</li>
            </ol>
            <button type="button" className="btn-primary mt-6" onClick={() => void start()}>
              Start camera
            </button>
          </section>
          <aside className="card p-5 text-sm text-muted">
            <h2 className="font-semibold text-ink">Your video stays on your device</h2>
            <p className="mt-2">
              The pose model runs in your browser. Only the reps are sent, never the picture.
            </p>
            {saving ? (
              <p className="mt-3">
                Your workout is saved to your account, under “Web browser” on the Mirrors page.
              </p>
            ) : (
              <p className="mt-3">
                This is the demo, so the reps are counted but not saved. Create an account to keep
                them.
              </p>
            )}
          </aside>
        </div>
      )}

      {phase.name === "starting" && <Spinner label={phase.step} />}

      {phase.name === "error" && (
        <div role="alert" className="card p-6">
          <p className="text-sm text-danger">{phase.message}</p>
          <button type="button" className="btn-ghost mt-4" onClick={() => void start()}>
            Try again
          </button>
        </div>
      )}

      {phase.name === "running" && view && (
        <div className="space-y-4">
          <section
            ref={stageRef}
            aria-label="Camera view"
            className={`mirror overflow-hidden bg-black ${
              fullscreen.full
                ? "fixed inset-0 z-50 h-[100dvh] w-full"
                : "relative h-[70svh] w-full rounded-xl sm:aspect-video sm:h-auto sm:max-h-[78svh]"
            }`}
          >
            {/* Mirrored, like a mirror. The landmarks are drawn on the same flip */}
            <div className="absolute inset-0 -scale-x-100">
              <video
                ref={videoRef}
                className="absolute inset-0 h-full w-full object-contain"
                playsInline
                muted
                aria-label="Camera"
              />
              <canvas
                ref={canvasRef}
                className="absolute inset-0 h-full w-full object-contain"
                aria-hidden
              />
            </div>
            {/* A shade at the top, so the text reads in a bright room */}
            <div className="pointer-events-none absolute inset-x-0 top-0 h-1/2 bg-gradient-to-b from-black/60 to-transparent" />
            <MirrorHud view={view} />
            {status(view) && (
              <div className="absolute bottom-3 left-3 max-w-[calc(100%-15rem)] rounded-lg bg-black/60 px-3 py-1.5 text-sm font-medium text-white">
                {status(view)}
              </div>
            )}
            <div className="absolute bottom-3 right-3 flex gap-2">
              <button
                type="button"
                className="btn bg-black/60 text-white hover:bg-black/75"
                onClick={fullscreen.toggle}
              >
                {fullscreen.full ? "Exit full screen" : "Full screen"}
              </button>
              <button type="button" className="btn-primary" onClick={() => void stop()}>
                Stop
              </button>
            </div>
          </section>

          <section className="card grid gap-6 p-5 md:grid-cols-[16rem_1fr]" aria-label="This session">
            <div className="space-y-2">
              <h2 className="mb-3 text-sm font-semibold">Arms</h2>
              <ArmMeter label="Left" value={view.progress[0]} />
              <ArmMeter label="Right" value={view.progress[1]} />
            </div>
            <div>
              <h2 className="text-sm font-semibold">This session</h2>
              <SetList history={view.history} />
              {saving && view.failedSends > 0 && (
                <p className="mt-3 text-xs text-danger">
                  Can't reach the server. {view.unsent} updates will be sent when it's back.
                </p>
              )}
            </div>
          </section>
        </div>
      )}

      {phase.name === "done" && (
        <section className="card max-w-xl p-6" aria-label="Summary">
          <h2 className="text-lg font-semibold">
            {phase.history.length
              ? `${formatNumber(phase.history.reduce((n, s) => n + s.reps, 0))} reps in ${phase.history.length} ${phase.history.length === 1 ? "set" : "sets"}`
              : "No reps this time"}
          </h2>
          <div className="mt-3">
            <SetList history={phase.history} />
          </div>
          <p className="mt-4 text-sm text-muted">
            {!saving && "This was the demo, so nothing was saved."}
            {saving && phase.saved === null && "Saving…"}
            {saving && phase.saved === true && phase.history.length > 0 && (
              <>
                Saved. <Link className="font-medium text-accent" to="/workouts">See it in your workouts</Link>
              </>
            )}
            {saving && phase.saved === false && "Couldn't reach the server, so this workout wasn't saved."}
          </p>
          <button type="button" className="btn-ghost mt-4" onClick={() => setPhase({ name: "intro" })}>
            Train again
          </button>
        </section>
      )}
    </>
  );
}
