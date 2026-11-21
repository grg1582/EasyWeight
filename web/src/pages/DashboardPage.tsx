import { useState } from "react";
import { Link } from "react-router-dom";

import { useDevices, useStats, useWorkouts } from "../api/queries";
import { DailyRepsChart, ExerciseBars } from "../components/charts";
import { EmptyState, ErrorNote, PageHeader, Spinner, StatTile } from "../components/ui";
import { WorkoutList } from "../components/WorkoutList";
import { EXERCISE_ORDER, fillDays, formatNumber } from "../lib/format";

const RANGES = [7, 30, 90] as const;

function RangePicker({ days, onChange }: { days: number; onChange: (days: number) => void }) {
  return (
    <div role="group" aria-label="Time range" className="flex rounded-lg border border-line bg-surface p-0.5">
      {RANGES.map((d) => (
        <button
          key={d}
          type="button"
          aria-pressed={d === days}
          onClick={() => onChange(d)}
          className={`rounded-md px-3 py-1 text-sm font-medium ${
            d === days ? "bg-accent/10 text-accent" : "text-muted hover:text-ink"
          }`}
        >
          {d} days
        </button>
      ))}
    </div>
  );
}

export function DashboardPage() {
  const [days, setDays] = useState<number>(30);
  const stats = useStats(days);
  const recent = useWorkouts(0, undefined, 5);
  const devices = useDevices();

  const header = (
    <PageHeader
      title="Dashboard"
      subtitle={`Your training over the last ${days} days`}
      actions={<RangePicker days={days} onChange={setDays} />}
    />
  );

  if (stats.isPending || devices.isPending) return <>{header}<Spinner /></>;
  if (stats.isError) return <>{header}<ErrorNote error={stats.error} onRetry={() => void stats.refetch()} /></>;

  if (devices.data?.length === 0) {
    return (
      <>
        {header}
        <EmptyState title="Connect your first mirror">
          <p>Workouts appear here once a mirror sends them.</p>
          <Link to="/mirrors" className="btn-primary mt-4">
            Add a mirror
          </Link>
        </EmptyState>
      </>
    );
  }

  const s = stats.data;
  const totalReps = s.per_exercise.reduce((sum, e) => sum + e.reps, 0);
  const totalSets = s.per_exercise.reduce((sum, e) => sum + e.sets, 0);
  const daily = fillDays(s.per_day, days);
  const activeDays = s.per_day.filter((d) => d.reps > 0).length;
  const exercises = [...s.per_exercise].sort(
    (a, b) => EXERCISE_ORDER.indexOf(a.exercise) - EXERCISE_ORDER.indexOf(b.exercise),
  );

  return (
    <>
      {header}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatTile label="Workouts" value={formatNumber(s.workouts)} />
        <StatTile label="Reps" value={formatNumber(totalReps)} />
        <StatTile label="Sets" value={formatNumber(totalSets)} />
        <StatTile
          label="Active days"
          value={`${activeDays}`}
          hint={`of ${days}`}
        />
      </div>

      {s.workouts === 0 ? (
        <div className="mt-6">
          <EmptyState title={`No workouts in the last ${days} days`}>
            Step in front of your mirror and start a set. It shows up here within seconds.
          </EmptyState>
        </div>
      ) : (
        <div className="mt-6 grid gap-6 lg:grid-cols-3">
          <section className="card p-5 lg:col-span-2">
            <h2 className="font-semibold">Reps per day</h2>
            <p className="mb-4 text-sm text-muted">All exercises together</p>
            <DailyRepsChart data={daily} />
          </section>
          <section className="card p-5">
            <h2 className="font-semibold">By exercise</h2>
            <p className="mb-5 text-sm text-muted">Reps and sets</p>
            <ExerciseBars data={exercises} />
          </section>
        </div>
      )}

      <section className="mt-8">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="font-semibold">Recent workouts</h2>
          <Link to="/workouts" className="text-sm font-medium text-accent">
            See all
          </Link>
        </div>
        {recent.isPending ? (
          <Spinner />
        ) : recent.isError ? (
          <ErrorNote error={recent.error} onRetry={() => void recent.refetch()} />
        ) : recent.data.items.length === 0 ? (
          <EmptyState title="No workouts yet" />
        ) : (
          <WorkoutList workouts={recent.data.items} />
        )}
      </section>
    </>
  );
}
