import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { Exercise } from "../api/types";
import { EXERCISES, formatNumber, plural, shortDay } from "../lib/format";
import { ExerciseTag } from "./ui";

interface DayPoint {
  date: string;
  reps: number;
}

/** Days into weeks, counted back from the last day, so the last bar is this
 * week. Each week is named by its first day */
export function toWeeks(days: DayPoint[]): DayPoint[] {
  const weeks: DayPoint[] = [];
  for (let end = days.length; end > 0; end -= 7) {
    const week = days.slice(Math.max(0, end - 7), end);
    weeks.unshift({ date: week[0]!.date, reps: week.reduce((sum, d) => sum + d.reps, 0) });
  }
  return weeks;
}

function RepsTooltip({
  active,
  payload,
  weekly,
}: {
  active?: boolean;
  payload?: { payload: DayPoint }[];
  weekly: boolean;
}) {
  const point = payload?.[0]?.payload;
  if (!active || !point) return null;
  return (
    <div className="card px-3 py-2 text-sm shadow-card-hover">
      <div className="font-semibold tabular-nums">{plural(point.reps, "rep")}</div>
      <div className="text-muted">
        {weekly ? `Week of ${shortDay(point.date)}` : shortDay(point.date)}
      </div>
    </div>
  );
}

/** Reps per day (or per week, for long ranges) as columns. One series, in a
 * neutral color, so no legend: the title says what it is */
export function DailyRepsChart({ data, weekly = false }: { data: DayPoint[]; weekly?: boolean }) {
  const points = weekly ? toWeeks(data) : data;
  return (
    <div className="h-64 sm:h-72" data-testid="daily-chart">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={points} margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
          <CartesianGrid vertical={false} stroke="var(--grid)" />
          <XAxis
            dataKey="date"
            tickFormatter={shortDay}
            tick={{ fill: "rgb(var(--faint))", fontSize: 12 }}
            tickLine={false}
            axisLine={{ stroke: "var(--axis)" }}
            minTickGap={24}
          />
          <YAxis
            allowDecimals={false}
            tick={{ fill: "rgb(var(--faint))", fontSize: 12 }}
            tickLine={false}
            axisLine={false}
            width={48}
          />
          <Tooltip
            content={<RepsTooltip weekly={weekly} />}
            cursor={{ fill: "rgb(var(--ink) / 0.05)", radius: 4 }}
          />
          <Bar
            dataKey="reps"
            fill="var(--chart-total)"
            radius={[4, 4, 0, 0]}
            maxBarSize={weekly ? 40 : 24}
            isAnimationActive={false}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

/** Reps per exercise as horizontal bars, with the name and value written out */
export function ExerciseBars({
  data,
}: {
  data: { exercise: Exercise; sets: number; reps: number }[];
}) {
  const max = Math.max(1, ...data.map((d) => d.reps));
  const total = data.reduce((sum, d) => sum + d.reps, 0) || 1;
  return (
    <ul className="space-y-5" aria-label="Reps by exercise">
      {data.map((d) => (
        <li key={d.exercise}>
          <div className="mb-2 flex items-baseline justify-between gap-3 text-sm">
            <span className="font-medium">
              <ExerciseTag exercise={d.exercise} />
            </span>
            <span className="tabular text-muted">
              <span className="font-semibold text-ink">{formatNumber(d.reps)}</span> reps ·{" "}
              {d.sets} {d.sets === 1 ? "set" : "sets"}
            </span>
          </div>
          <div className="flex items-center gap-3">
            <div className="h-2.5 flex-1 rounded-full bg-ink/5">
              <div
                className="h-full rounded-full transition-[width] duration-500 ease-out"
                style={{
                  width: `${(d.reps / max) * 100}%`,
                  backgroundColor: EXERCISES[d.exercise].color,
                }}
              />
            </div>
            <span className="tabular w-9 text-right text-xs text-faint">
              {Math.round((d.reps / total) * 100)}%
            </span>
          </div>
        </li>
      ))}
    </ul>
  );
}
