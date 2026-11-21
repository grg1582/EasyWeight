import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { Exercise } from "../api/types";
import { EXERCISES, formatNumber, shortDay } from "../lib/format";
import { ExerciseTag } from "./ui";

interface DayPoint {
  date: string;
  reps: number;
}

function DayTooltip({ active, payload }: { active?: boolean; payload?: { payload: DayPoint }[] }) {
  const point = payload?.[0]?.payload;
  if (!active || !point) return null;
  return (
    <div className="card px-3 py-2 text-sm shadow-sm">
      <div className="font-semibold">{formatNumber(point.reps)} reps</div>
      <div className="text-muted">{shortDay(point.date)}</div>
    </div>
  );
}

/** Reps per day as columns. One series, so no legend: the title says what it is */
export function DailyRepsChart({ data }: { data: DayPoint[] }) {
  return (
    <div className="h-64" data-testid="daily-chart">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
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
          <Tooltip content={<DayTooltip />} cursor={{ fill: "rgb(var(--ink) / 0.05)" }} />
          <Bar
            dataKey="reps"
            fill="var(--ex-curl)"
            radius={[4, 4, 0, 0]}
            maxBarSize={24}
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
  return (
    <ul className="space-y-4" aria-label="Reps by exercise">
      {data.map((d) => (
        <li key={d.exercise}>
          <div className="mb-1.5 flex items-baseline justify-between gap-3 text-sm">
            <ExerciseTag exercise={d.exercise} />
            <span className="tabular text-muted">
              <span className="font-semibold text-ink">{formatNumber(d.reps)}</span> reps ·{" "}
              {d.sets} {d.sets === 1 ? "set" : "sets"}
            </span>
          </div>
          <div className="h-2.5 rounded-full bg-ink/5">
            <div
              className="h-full rounded-full"
              style={{
                width: `${(d.reps / max) * 100}%`,
                backgroundColor: EXERCISES[d.exercise].color,
              }}
            />
          </div>
        </li>
      ))}
    </ul>
  );
}
