"use client";

import { Card, CardContent } from "@/components/ui/card";
import { formatDuration } from "@/lib/utils";
import type { EpisodeSummary } from "@/types/domain";

// Quick Stats (PRD 10): episodes generated, minutes listened, favorite category.
export function QuickStats({
  episodes,
  favoriteCategory,
}: {
  episodes: EpisodeSummary[];
  favoriteCategory: string;
}) {
  const ready = episodes.filter((e) => e.status === "ready");
  const totalSec = ready.reduce((acc, e) => acc + (e.duration_sec ?? 0), 0);

  const stats = [
    { label: "Episodes", value: String(ready.length) },
    { label: "Total length", value: formatDuration(totalSec) },
    { label: "Top interest", value: favoriteCategory || "—" },
  ];

  return (
    <div className="grid grid-cols-3 gap-3">
      {stats.map((s) => (
        <Card key={s.label}>
          <CardContent className="p-4 pt-4">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">{s.label}</p>
            <p className="mt-1 truncate text-xl font-semibold capitalize">{s.value}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
