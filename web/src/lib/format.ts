import type { Exercise } from "../api/types";

export const EXERCISES: Record<Exercise, { name: string; color: string }> = {
  curl: { name: "Bicep curl", color: "var(--ex-curl)" },
  raise: { name: "Lateral raise", color: "var(--ex-raise)" },
  press: { name: "Overhead press", color: "var(--ex-press)" },
};

export const EXERCISE_ORDER: Exercise[] = ["curl", "raise", "press"];

const number = new Intl.NumberFormat("en-US");

export function formatNumber(n: number): string {
  return number.format(n);
}

/** "Sat, Nov 21" (with the year when it isn't this year) */
export function formatDate(iso: string, now = new Date()): string {
  const date = new Date(iso);
  return date.toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    year: date.getFullYear() === now.getFullYear() ? undefined : "numeric",
  });
}

/** "16:25" in the viewer's time zone */
export function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
}

/** "45s", "12 min", "1 h 05 min" */
export function formatDuration(seconds: number): string {
  if (seconds < 60) return `${Math.max(0, Math.round(seconds))}s`;
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes} min`;
  return `${Math.floor(minutes / 60)} h ${String(minutes % 60).padStart(2, "0")} min`;
}

export function secondsBetween(start: string, end: string | null): number | null {
  if (!end) return null;
  return (new Date(end).getTime() - new Date(start).getTime()) / 1000;
}

/** "just now", "5 min ago", "3 h ago", "2 days ago" */
export function formatAgo(iso: string, now = new Date()): string {
  const seconds = (now.getTime() - new Date(iso).getTime()) / 1000;
  if (seconds < 60) return "just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)} min ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)} h ago`;
  const days = Math.floor(seconds / 86400);
  return days === 1 ? "yesterday" : `${days} days ago`;
}

/** The backend only lists days that had reps. A time axis needs every day,
 * so the missing ones are filled in with 0 (dates are UTC, like the backend's) */
export function fillDays(
  perDay: { date: string; reps: number }[],
  days: number,
  today = new Date(),
): { date: string; reps: number }[] {
  const reps = new Map(perDay.map((d) => [d.date, d.reps]));
  const end = Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate());
  return Array.from({ length: days }, (_, i) => {
    const date = new Date(end - (days - 1 - i) * 86400000).toISOString().slice(0, 10);
    return { date, reps: reps.get(date) ?? 0 };
  });
}

/** "Nov 21" from "2026-11-21" */
export function shortDay(date: string): string {
  return new Date(`${date}T00:00:00Z`).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  });
}

/** "1 rep", "12 reps" */
export function plural(n: number, word: string): string {
  return `${formatNumber(n)} ${n === 1 ? word : `${word}s`}`;
}
