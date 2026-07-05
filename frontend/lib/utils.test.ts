import { describe, expect, it } from "vitest";

import { cn, formatDate, formatDuration } from "@/lib/utils";

describe("formatDuration", () => {
  it("formats seconds as m:ss", () => {
    expect(formatDuration(0)).toBe("--:--");
    expect(formatDuration(65)).toBe("1:05");
    expect(formatDuration(600)).toBe("10:00");
  });
  it("handles null", () => {
    expect(formatDuration(null)).toBe("--:--");
  });
});

describe("formatDate", () => {
  it("renders date-only strings as the same calendar day in any timezone", () => {
    // Regression: new Date("2026-07-05") is UTC midnight, which displayed as
    // "4 Jul 2026" in timezones west of UTC.
    expect(formatDate("2026-07-05")).toContain("5");
    expect(formatDate("2026-07-05")).toContain("2026");
    // Year boundary: must not roll back into December of the previous year.
    expect(formatDate("2026-01-01")).toContain("2026");
    expect(formatDate("2026-01-01")).not.toContain("2025");
  });
  it("still formats full timestamps", () => {
    expect(formatDate("2026-07-05T12:00:00Z")).toContain("2026");
  });
  it("handles null/undefined", () => {
    expect(formatDate(null)).toBe("");
    expect(formatDate(undefined)).toBe("");
  });
});

describe("cn", () => {
  it("merges and dedupes tailwind classes", () => {
    expect(cn("px-2", "px-4")).toBe("px-4");
    expect(cn("text-sm", false && "hidden", "font-bold")).toBe("text-sm font-bold");
  });
});
