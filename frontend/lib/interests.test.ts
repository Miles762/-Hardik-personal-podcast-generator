import { describe, expect, it } from "vitest";

import { MAX_INTERESTS, addInterest, normalizeInterest } from "@/lib/interests";

describe("normalizeInterest", () => {
  it("trims and collapses whitespace", () => {
    expect(normalizeInterest("  formula   1  ")).toBe("formula 1");
  });
  it("returns empty string for blank input", () => {
    expect(normalizeInterest("   ")).toBe("");
  });
  it("caps length at 100 characters", () => {
    expect(normalizeInterest("x".repeat(150))).toHaveLength(100);
  });
});

describe("addInterest", () => {
  it("appends a new interest", () => {
    expect(addInterest(["space"], "climate")).toEqual(["space", "climate"]);
  });
  it("ignores case-insensitive duplicates", () => {
    expect(addInterest(["AI"], "ai")).toEqual(["AI"]);
  });
  it("ignores empty input", () => {
    expect(addInterest(["space"], "  ")).toEqual(["space"]);
  });
  it("does not grow past the maximum", () => {
    const full = Array.from({ length: MAX_INTERESTS }, (_, i) => `t${i}`);
    expect(addInterest(full, "one more")).toEqual(full);
  });
});
