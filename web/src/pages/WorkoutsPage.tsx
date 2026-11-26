import { ChevronLeft, ChevronRight, ListChecks } from "lucide-react";
import { useSearchParams } from "react-router-dom";

import { PAGE_SIZE, useDevices, useWorkouts } from "../api/queries";
import { EmptyState, ErrorNote, PageHeader, Spinner } from "../components/ui";
import { WorkoutList } from "../components/WorkoutList";

export function WorkoutsPage() {
  // Page and mirror live in the address (?page=2&mirror=...), so the back
  // button and shared links keep them
  const [params, setParams] = useSearchParams();
  const page = Math.max(0, Number(params.get("page") ?? 1) - 1);
  const deviceId = params.get("mirror") ?? undefined;
  const workouts = useWorkouts(page, deviceId);
  const devices = useDevices();

  function update(changes: Record<string, string | undefined>) {
    const next = new URLSearchParams(params);
    for (const [key, value] of Object.entries(changes)) {
      if (value) next.set(key, value);
      else next.delete(key);
    }
    setParams(next);
  }

  const total = workouts.data?.total ?? 0;
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <>
      <PageHeader
        title="Workouts"
        subtitle={workouts.data ? `${total} ${total === 1 ? "workout" : "workouts"}` : undefined}
        actions={
          (devices.data?.length ?? 0) > 1 && (
            <select
              aria-label="Mirror"
              className="input w-auto"
              value={deviceId ?? ""}
              onChange={(e) => update({ mirror: e.target.value || undefined, page: undefined })}
            >
              <option value="">All mirrors</option>
              {devices.data?.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </select>
          )
        }
      />
      {workouts.isPending ? (
        <Spinner />
      ) : workouts.isError ? (
        <ErrorNote error={workouts.error} onRetry={() => void workouts.refetch()} />
      ) : workouts.data.items.length === 0 ? (
        <EmptyState title="No workouts yet" icon={ListChecks}>
          Workouts appear here as soon as a mirror sends them.
        </EmptyState>
      ) : (
        <>
          <WorkoutList workouts={workouts.data.items} />
          {pages > 1 && (
            <nav className="mt-4 flex items-center justify-between text-sm" aria-label="Pages">
              <button
                type="button"
                className="btn-ghost"
                disabled={page === 0}
                onClick={() => update({ page: page > 1 ? String(page) : undefined })}
              >
                <ChevronLeft aria-hidden className="h-4 w-4" />
                Newer
              </button>
              <span className="text-muted">
                Page {page + 1} of {pages}
              </span>
              <button
                type="button"
                className="btn-ghost"
                disabled={page + 1 >= pages}
                onClick={() => update({ page: String(page + 2) })}
              >
                Older
                <ChevronRight aria-hidden className="h-4 w-4" />
              </button>
            </nav>
          )}
        </>
      )}
    </>
  );
}
