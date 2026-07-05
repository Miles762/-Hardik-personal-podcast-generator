"use client";

import { Card, CardContent } from "@/components/ui/card";
import type { Tile } from "@/types/dashboard";

// Stat tile (a hero number, per dataviz: the job is "single headline" -> not a
// chart). Every value is real captured data.
function formatValue(t: Tile): string {
  if (t.unit === "USD") {
    // Small costs (multi-stage LLM is cents) need more precision than 2 dp, or
    // a real $0.0036 would render as "$0.00" and look like zero.
    if (t.value > 0 && t.value < 0.01) return `$${t.value.toFixed(4)}`;
    return `$${t.value.toFixed(2)}`;
  }
  if (t.unit === "%") return `${t.value.toFixed(0)}%`;
  if (t.unit === "s") return `${t.value.toFixed(0)}s`;
  if (t.unit === "min") return `${t.value} min`;
  return String(t.value);
}

export function MetricTile({ tile }: { tile: Tile }) {
  return (
    <Card>
      <CardContent className="p-4 pt-4">
        <p className="text-xs uppercase tracking-wide text-muted-foreground">
          {tile.label}
        </p>
        <p className="mt-2 text-2xl font-semibold tabular-nums">{formatValue(tile)}</p>
      </CardContent>
    </Card>
  );
}
