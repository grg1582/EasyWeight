import { ExerciseTag } from "../components/ui";
import { useLive } from "./LiveContext";

/** A small dot in the header: are updates coming in live? */
export function LiveBadge() {
  const { status } = useLive();
  const live = status === "live";
  return (
    <span
      className="inline-flex items-center gap-1.5 text-xs font-medium text-muted"
      title={live ? "New workouts show up as they happen" : "Reconnecting to live updates"}
    >
      <span className={`h-2 w-2 rounded-full ${live ? "bg-success" : "bg-faint"}`} aria-hidden />
      {live ? "Live" : "Offline"}
    </span>
  );
}

/** "Training now": what each mirror (or browser) is doing, as it happens */
export function TrainingNow() {
  const { activity } = useLive();
  if (!activity.length) return null;
  return (
    <section className="card mb-6 border-success/30 p-5" aria-label="Training now">
      <h2 className="flex items-center gap-2 font-semibold">
        <span className="relative flex h-2.5 w-2.5" aria-hidden>
          <span className="absolute inline-flex h-full w-full rounded-full bg-success opacity-60 motion-safe:animate-ping" />
          <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-success" />
        </span>
        Training now
      </h2>
      <ul className="mt-3 divide-y divide-line">
        {activity.map((a) => (
          <li key={a.device.id} className="flex flex-wrap items-center justify-between gap-2 py-2 text-sm">
            <span className="flex items-center gap-3">
              <span className="font-medium">{a.device.name}</span>
              {a.exercise && <ExerciseTag exercise={a.exercise} />}
            </span>
            <span className="tabular-nums text-muted">
              {!a.exercise
                ? "Starting"
                : a.resting
                  ? `Resting after set ${a.set} (${a.reps} ${a.reps === 1 ? "rep" : "reps"})`
                  : `Set ${a.set} · `}
              {a.exercise && !a.resting && (
                <span className="font-semibold text-ink">
                  {a.reps} {a.reps === 1 ? "rep" : "reps"}
                </span>
              )}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
