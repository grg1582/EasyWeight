import { describe, expect, it } from "vitest";

import { fillDays, formatAgo, formatDuration, plural, secondsBetween } from "./format";

describe("fillDays", () => {
  it("lists every day, with 0 for days without reps", () => {
    const today = new Date("2026-11-21T10:00:00Z");
    const days = fillDays([{ date: "2026-11-19", reps: 12 }, { date: "2026-11-21", reps: 5 }], 4, today);
    expect(days).toEqual([
      { date: "2026-11-18", reps: 0 },
      { date: "2026-11-19", reps: 12 },
      { date: "2026-11-20", reps: 0 },
      { date: "2026-11-21", reps: 5 },
    ]);
  });

  it("crosses month ends", () => {
    const days = fillDays([], 3, new Date("2026-12-01T23:30:00Z"));
    expect(days.map((d) => d.date)).toEqual(["2026-11-29", "2026-11-30", "2026-12-01"]);
  });
});

describe("formatting", () => {
  it("formats durations", () => {
    expect(formatDuration(42)).toBe("42s");
    expect(formatDuration(12 * 60 + 10)).toBe("12 min");
    expect(formatDuration(65 * 60)).toBe("1 h 05 min");
  });

  it("measures workouts that ended, and not open ones", () => {
    expect(secondsBetween("2026-11-21T14:00:00Z", "2026-11-21T14:02:30Z")).toBe(150);
    expect(secondsBetween("2026-11-21T14:00:00Z", null)).toBeNull();
  });

  it("says how long ago", () => {
    const now = new Date("2026-11-21T12:00:00Z");
    expect(formatAgo("2026-11-21T11:59:30Z", now)).toBe("just now");
    expect(formatAgo("2026-11-21T11:15:00Z", now)).toBe("45 min ago");
    expect(formatAgo("2026-11-20T09:00:00Z", now)).toBe("yesterday");
    expect(formatAgo("2026-11-11T12:00:00Z", now)).toBe("10 days ago");
  });

  it("pluralizes", () => {
    expect(plural(1, "rep")).toBe("1 rep");
    expect(plural(1200, "rep")).toBe("1,200 reps");
  });
});
