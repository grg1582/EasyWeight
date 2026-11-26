import { ArrowRight, CalendarCheck, Dumbbell, Flame, Layers, MonitorSmartphone } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { useDevices, useStats, useWorkouts } from "../api/queries";
import type { Stats } from "../api/types";
import { DailyRepsChart, ExerciseBars } from "../components/charts";
import {
  EmptyState,
  ErrorNote,
  PageHeader,
  Skeleton,
  StatTile,
  Trend,
} from "../components/ui";
import { WorkoutList } from "../components/WorkoutList";
import { TrainingNow } from "../live/LiveViews";
import { EXERCISE_ORDER, fillDays, formatNumber } from "../lib/format";

const RANGES = [7, 30, 90] as const;

function RangePicker({ days, onChange }: { days: number; onChange: (days: number) => void }) {
  return (
    <div
      role="group"
      aria-label="Time range"
      className="flex rounded-lg border border-line bg-surface p-0.5 shadow-card"
    >
      {RANGES.map((d) => (
        <button
          key={d}
          type="button"
          aria-pressed={d === days}
          onClick={() => onChange(d)}
          className={`rounded-md px-3 py-1 text-sm font-medium transition-colors ${
            d === days ? "bg-accent/10 text-accent" : "text-muted hover:text-ink"
          }`}
        >
          {d} days
        </button>
      ))}
    </div>
  );
}

/** Reps and active days in the period before this one, from the same
 * endpoint asked for twice the days. Null until it has loaded */
function previousPeriod(double: Stats | undefined, firstDay: string) {
  if (!double) return null;
  const before = double.per_day.filter((d) => d.date < firstDay);
  return {
    reps: before.reduce((sum, d) => sum + d.reps, 0),
    activeDays: before.filter((d) => d.reps > 0).length,
  };
}

/** The change from the previous period, or nothing when there's no previous
 * period to compare with */
function change(now: number, before: number | undefined): number | null {
  return before ? (now - before) / before : null;
}

/** The dashboard's shape while it loads, so nothing jumps when it arrives */
function DashboardSkeleton() {
  return (
    <div role="status" aria-label="Loading">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {[0, 1, 2, 3].map((k) => (
          <div key={k} className="card p-4 sm:p-5">
            <Skeleton className="h-4 w-20" />
            <Skeleton className="mt-3 h-8 w-16" />
          </div>
        ))}
      </div>
      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <div className="card p-5 lg:col-span-2">
          <Skeleton className="h-5 w-32" />
          <Skeleton className="mt-6 h-64" />
        </div>
        <div className="card space-y-6 p-5">
          <Skeleton className="h-5 w-28" />
          {[0, 1, 2].map((k) => (
            <Skeleton key={k} className="h-8" />
          ))}
        </div>
      </div>
    </div>
  );
}

export function DashboardPage() {
  const [days, setDays] = useState<number>(30);
  const stats = useStats(days);
  const double = useStats(days * 2);
  const recent = useWorkouts(0, undefined, 5);
  const devices = useDevices();

  const header = (
    <PageHeader
      title="Dashboard"
      subtitle={`Your training over the last ${days} days`}
      actions={<RangePicker days={days} onChange={setDays} />}
    />
  );

  if (stats.isPending || devices.isPending) return <>{header}<DashboardSkeleton /></>;
  if (stats.isError) return <>{header}<ErrorNote error={stats.error} onRetry={() => void stats.refetch()} /></>;

  if (devices.data?.length === 0) {
    return (
      <>
        {header}
        <EmptyState title="Connect your first mirror" icon={MonitorSmartphone}>
          <p>Workouts appear here once a mirror sends them, or once you train in the browser.</p>
          <div className="mt-5 flex flex-wrap justify-center gap-2">
            <Link to="/mirrors" className="btn-primary">
              Add a mirror
            </Link>
            <Link to="/train" className="btn-ghost">
              Train in the browser
            </Link>
          </div>
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
  const previous = previousPeriod(double.data, daily[0]!.date);
  const vs = `vs previous ${days} days`;
  const repsChange = change(totalReps, previous?.reps);
  const daysChange = change(activeDays, previous?.activeDays);

  return (
    <>
      {header}
      <TrainingNow />
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatTile
          primary
          icon={Flame}
          label="Reps"
          value={formatNumber(totalReps)}
          trend={repsChange !== null && <Trend change={repsChange} label={vs} />}
        />
        <StatTile icon={Dumbbell} label="Workouts" value={formatNumber(s.workouts)} />
        <StatTile icon={Layers} label="Sets" value={formatNumber(totalSets)} />
        <StatTile
          icon={CalendarCheck}
          label="Active days"
          value={`${activeDays}`}
          hint={`of ${days}`}
          trend={daysChange !== null && <Trend change={daysChange} label={vs} />}
        />
      </div>

      {s.workouts === 0 ? (
        <div className="mt-6">
          <EmptyState title={`No workouts in the last ${days} days`} icon={Dumbbell}>
            Step in front of your mirror and start a set. It shows up here within seconds.
          </EmptyState>
        </div>
      ) : (
        <div className="mt-6 grid gap-6 lg:grid-cols-3">
          <section className="card p-5 sm:p-6 lg:col-span-2">
            <h2 className="font-semibold">{days > 30 ? "Reps per week" : "Reps per day"}</h2>
            <p className="mb-5 text-sm text-muted">All exercises together</p>
            <DailyRepsChart data={daily} weekly={days > 30} />
          </section>
          <section className="card p-5 sm:p-6">
            <h2 className="font-semibold">By exercise</h2>
            <p className="mb-6 text-sm text-muted">Reps, sets and share of all reps</p>
            <ExerciseBars data={exercises} />
          </section>
        </div>
      )}

      <section className="mt-10">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold tracking-tight">Recent workouts</h2>
          <Link to="/workouts" className="link inline-flex items-center gap-1 text-sm">
            See all
            <ArrowRight aria-hidden className="h-3.5 w-3.5" />
          </Link>
        </div>
        {recent.isPending ? (
          <div className="card space-y-4 p-5" role="status" aria-label="Loading">
            {[0, 1, 2].map((k) => (
              <Skeleton key={k} className="h-6" />
            ))}
          </div>
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
