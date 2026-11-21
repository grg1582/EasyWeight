import { Link } from "react-router-dom";

import type { WorkoutSummary } from "../api/types";
import { formatDate, formatDuration, formatTime, secondsBetween } from "../lib/format";
import { ExerciseTag } from "./ui";

/** Not ended yet, and started in the last 3 hours: probably still going.
 * Older ones lost their end (the mirror was switched off mid-workout) */
export function isRecent(iso: string, now = Date.now()): boolean {
  return now - new Date(iso).getTime() < 3 * 3600 * 1000;
}

/** Workouts as a table on wide screens, and as stacked rows on phones */
export function WorkoutList({ workouts }: { workouts: WorkoutSummary[] }) {
  return (
    <div className="card overflow-hidden">
      <table className="w-full text-left text-sm">
        <thead className="hidden border-b border-line text-xs uppercase tracking-wide text-faint sm:table-header-group">
          <tr>
            <th className="px-4 py-3 font-medium">When</th>
            <th className="px-4 py-3 font-medium">Exercises</th>
            <th className="px-4 py-3 text-right font-medium">Sets</th>
            <th className="px-4 py-3 text-right font-medium">Reps</th>
            <th className="px-4 py-3 text-right font-medium">Duration</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {workouts.map((w) => {
            const seconds = secondsBetween(w.started_at, w.ended_at);
            return (
              <tr key={w.id} className="group relative hover:bg-ink/[0.03]">
                <td className="block px-4 pt-3 sm:table-cell sm:py-3">
                  <Link
                    to={`/workouts/${w.id}`}
                    className="font-medium after:absolute after:inset-0 group-hover:text-accent"
                  >
                    {formatDate(w.started_at)}
                  </Link>
                  <span className="ml-2 text-muted">{formatTime(w.started_at)}</span>
                </td>
                <td className="block px-4 py-1 sm:table-cell sm:py-3">
                  <span className="flex flex-wrap gap-x-3 gap-y-1 text-muted">
                    {w.exercises.map((e) => (
                      <ExerciseTag key={e} exercise={e} />
                    ))}
                  </span>
                </td>
                <td className="tabular inline-block px-4 pb-3 sm:table-cell sm:py-3 sm:text-right">
                  {w.total_sets}
                  <span className="text-muted sm:hidden"> {w.total_sets === 1 ? "set" : "sets"}</span>
                </td>
                <td className="tabular inline-block pb-3 sm:table-cell sm:px-4 sm:py-3 sm:text-right">
                  <span className="font-semibold">{w.total_reps}</span>
                  <span className="text-muted sm:hidden"> {w.total_reps === 1 ? "rep" : "reps"}</span>
                </td>
                <td className="tabular inline-block px-4 pb-3 text-muted sm:table-cell sm:py-3 sm:text-right">
                  {seconds !== null ? (
                    formatDuration(seconds)
                  ) : isRecent(w.started_at) ? (
                    <span className="rounded-full bg-accent/10 px-2 py-0.5 text-xs font-medium text-accent">
                      In progress
                    </span>
                  ) : (
                    "–"
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
