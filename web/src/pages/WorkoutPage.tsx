import { ArrowLeft, Clock, Flame, Layers, SearchX } from "lucide-react";
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
    <Link
      to="/workouts"
      className="mb-4 inline-flex items-center gap-1.5 rounded text-sm text-muted transition-colors hover:text-ink"
    >
      <ArrowLeft aria-hidden className="h-4 w-4" />
      All workouts
    </Link>
  );
  if (workout.isPending) return <>{back}<Spinner /></>;
  if (workout.isError) {
    return (
      <>
        {back}
        {workout.error instanceof ApiError && workout.error.status === 404 ? (
          <EmptyState title="Workout not found" icon={SearchX}>
            It may have been removed with its mirror.
          </EmptyState>
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
      <div className="grid grid-cols-3 gap-3 sm:gap-4">
        <StatTile icon={Layers} label="Sets" value={String(w.total_sets)} />
        <StatTile icon={Flame} label="Reps" value={String(w.total_reps)} />
        <StatTile
          icon={Clock}
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
              const timing = (
                <>
                  {length !== null ? formatDuration(length) : "–"}
                  {rest !== null && rest > 0 && (
                    <span className="text-faint"> · {formatDuration(rest)} rest before</span>
                  )}
                </>
              );
              return (
                // Phones: the exercise and reps on one line, the bar below,
                // the timing under the name. Wider: all in one row
                <li
                  key={s.id}
                  className="grid grid-cols-[1.75rem_1fr_auto] items-center gap-x-3 gap-y-2 px-5 py-3 text-sm transition-colors hover:bg-ink/[0.02] sm:grid-cols-[2rem_12rem_1fr_5rem_11rem] sm:gap-x-4"
                >
                  <span className="tabular text-faint">{i + 1}</span>
                  <span>
                    <span className="font-medium">
                      <ExerciseTag exercise={s.exercise} />
                    </span>
                    <span className="ml-2 text-faint">set {s.set_number}</span>
                    <span className="tabular mt-0.5 block text-xs text-muted sm:hidden">{timing}</span>
                  </span>
                  <span className="col-span-2 col-start-2 row-start-2 h-2 rounded-full bg-ink/5 sm:col-span-1 sm:col-start-3 sm:row-start-1">
                    <span
                      className="block h-full rounded-full"
                      style={{
                        width: `${(s.reps / maxReps) * 100}%`,
                        backgroundColor: EXERCISES[s.exercise].color,
                      }}
                    />
                  </span>
                  <span className="tabular col-start-3 row-start-1 text-right font-semibold sm:col-start-4">
                    {plural(s.reps, "rep")}
                  </span>
                  <span className="tabular hidden text-right text-muted sm:block">
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
