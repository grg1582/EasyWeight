import { Link, useParams } from "react-router-dom";

import { ApiError } from "../api/client";
import { useDevices, useWorkout } from "../api/queries";
import { EmptyState, ErrorNote, ExerciseTag, PageHeader, Spinner, StatTile } from "../components/ui";
import { isRecent } from "../components/WorkoutList";
import {
  EXERCISES,
  formatDate,
  formatDuration,
  formatTime,
  plural,
  secondsBetween,
} from "../lib/format";

export function WorkoutPage() {
  const { id = "" } = useParams();
  const workout = useWorkout(id);
  const devices = useDevices();

  const back = (
    <Link to="/workouts" className="mb-4 inline-block text-sm text-muted hover:text-ink">
      ← All workouts
    </Link>
  );
  if (workout.isPending) return <>{back}<Spinner /></>;
  if (workout.isError) {
    return (
      <>
        {back}
        {workout.error instanceof ApiError && workout.error.status === 404 ? (
          <EmptyState title="Workout not found">It may have been removed with its mirror.</EmptyState>
        ) : (
          <ErrorNote error={workout.error} onRetry={() => void workout.refetch()} />
        )}
      </>
    );
  }

  const w = workout.data;
  const seconds = secondsBetween(w.started_at, w.ended_at);
  const mirror = devices.data?.find((d) => d.id === w.device_id)?.name;
  const maxReps = Math.max(1, ...w.sets.map((s) => s.reps));

  return (
    <>
      {back}
      <PageHeader
        title={formatDate(w.started_at)}
        subtitle={
          <>
            Started {formatTime(w.started_at)}
            {mirror && <> on {mirror}</>}
          </>
        }
      />
      <div className="grid grid-cols-3 gap-4">
        <StatTile label="Sets" value={String(w.total_sets)} />
        <StatTile label="Reps" value={String(w.total_reps)} />
        <StatTile
          label="Duration"
          value={
            seconds !== null ? formatDuration(seconds) : isRecent(w.started_at) ? "Ongoing" : "–"
          }
        />
      </div>

      <section className="card mt-6 overflow-hidden">
        <h2 className="border-b border-line px-5 py-4 font-semibold">Sets</h2>
        {w.sets.length === 0 ? (
          <p className="px-5 py-6 text-sm text-muted">No sets in this workout.</p>
        ) : (
          <ol className="divide-y divide-line">
            {w.sets.map((s, i) => {
              const length = secondsBetween(s.started_at, s.ended_at);
              const previous = w.sets[i - 1];
              const rest = previous ? secondsBetween(previous.ended_at ?? previous.started_at, s.started_at) : null;
              return (
                <li key={s.id} className="grid grid-cols-[2rem_1fr_auto] items-center gap-x-4 gap-y-2 px-5 py-3 text-sm sm:grid-cols-[2rem_12rem_1fr_8rem]">
                  <span className="tabular text-faint">{i + 1}</span>
                  <span>
                    <ExerciseTag exercise={s.exercise} />
                    <span className="ml-2 text-faint">set {s.set_number}</span>
                  </span>
                  <span className="col-span-3 col-start-2 row-start-2 flex items-center gap-3 sm:col-span-1 sm:col-start-3 sm:row-start-1">
                    <span className="h-2 flex-1 rounded-full bg-ink/5">
                      <span
                        className="block h-full rounded-full"
                        style={{
                          width: `${(s.reps / maxReps) * 100}%`,
                          backgroundColor: EXERCISES[s.exercise].color,
                        }}
                      />
                    </span>
                    <span className="tabular w-16 text-right font-semibold">{plural(s.reps, "rep")}</span>
                  </span>
                  <span className="tabular text-right text-muted">
                    {length !== null ? formatDuration(length) : "–"}
                    {rest !== null && rest > 0 && (
                      <span className="block text-xs text-faint">{formatDuration(rest)} rest before</span>
                    )}
                  </span>
                </li>
              );
            })}
          </ol>
        )}
      </section>
    </>
  );
}
