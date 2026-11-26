import { AlertCircle, ArrowDownRight, ArrowUpRight, type LucideIcon } from "lucide-react";
import { type ReactNode, useEffect } from "react";

import type { Exercise } from "../api/types";
import { EXERCISES } from "../lib/format";

/** The browser tab's title: "Dashboard · EasyWeight" */
export function usePageTitle(title: string) {
  useEffect(() => {
    document.title = title ? `${title} · EasyWeight` : "EasyWeight";
  }, [title]);
}

export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: string;
  subtitle?: ReactNode;
  actions?: ReactNode;
}) {
  usePageTitle(title);
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4 sm:mb-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-muted sm:text-base">{subtitle}</p>}
      </div>
      {actions}
    </div>
  );
}

/** Up or down from the previous period: "↗ 12% vs previous 30 days" */
export function Trend({ change, label }: { change: number; label: string }) {
  const up = change >= 0;
  const Icon = up ? ArrowUpRight : ArrowDownRight;
  return (
    <div className="mt-2 flex flex-wrap items-center gap-x-1.5 text-xs">
      <span className={`pill px-1.5 ${up ? "bg-success/10 text-success" : "bg-ink/5 text-muted"}`}>
        <Icon aria-hidden className="h-3 w-3" strokeWidth={2.5} />
        {Math.abs(Math.round(change * 100))}%
        <span className="sr-only">{up ? "up" : "down"}</span>
      </span>
      <span className="text-faint">{label}</span>
    </div>
  );
}

/** A number with a label: "Reps · 1,284". The first one on a page can stand out */
export function StatTile({
  label,
  value,
  hint,
  icon: Icon,
  trend,
  primary = false,
}: {
  label: string;
  value: string;
  hint?: string;
  icon?: LucideIcon;
  trend?: ReactNode;
  primary?: boolean;
}) {
  return (
    <div className={`card p-4 sm:p-5 ${primary ? "ring-1 ring-inset ring-accent/25" : ""}`}>
      <div className="flex items-center gap-2 text-sm font-medium text-muted">
        {Icon && (
          <Icon aria-hidden className={`h-4 w-4 ${primary ? "text-accent" : "text-faint"}`} />
        )}
        {label}
      </div>
      <div className="tabular mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">{value}</div>
      {hint && <div className="mt-1 text-xs text-faint">{hint}</div>}
      {trend}
    </div>
  );
}

/** The exercise's name with its color as a dot beside it (never color alone) */
export function ExerciseTag({ exercise }: { exercise: Exercise }) {
  const { name, color } = EXERCISES[exercise];
  return (
    <span className="inline-flex items-center gap-1.5 whitespace-nowrap">
      <span
        aria-hidden
        className="inline-block h-2 w-2 rounded-full"
        style={{ backgroundColor: color }}
      />
      {name}
    </span>
  );
}

export function Spinner({ label = "Loading" }: { label?: string }) {
  return (
    <div role="status" className="flex items-center gap-2 py-10 text-sm text-muted">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-line border-t-accent motion-reduce:animate-[spin_1.5s_linear_infinite]" />
      {label}…
    </div>
  );
}

/** A gray block in the shape of what's loading, so the page doesn't jump */
export function Skeleton({ className = "" }: { className?: string }) {
  return <div aria-hidden className={`rounded-md bg-ink/[0.06] motion-safe:animate-pulse ${className}`} />;
}

export function ErrorNote({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const message = error instanceof Error ? error.message : "Something went wrong";
  return (
    <div
      role="alert"
      className="card flex flex-wrap items-center justify-between gap-3 border-danger/30 p-4"
    >
      <span className="flex items-center gap-2 text-sm text-danger">
        <AlertCircle aria-hidden className="h-4 w-4 shrink-0" />
        {message}
      </span>
      {onRetry && (
        <button type="button" className="btn-ghost" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  );
}

export function EmptyState({
  title,
  icon: Icon,
  children,
}: {
  title: string;
  icon?: LucideIcon;
  children?: ReactNode;
}) {
  return (
    <div className="card px-6 py-12 text-center">
      {Icon && (
        <span className="icon-chip mx-auto mb-4 h-11 w-11 rounded-xl">
          <Icon aria-hidden className="h-5 w-5" />
        </span>
      )}
      <h2 className="text-base font-semibold">{title}</h2>
      {children && <div className="mx-auto mt-2 max-w-md text-sm text-muted">{children}</div>}
    </div>
  );
}
