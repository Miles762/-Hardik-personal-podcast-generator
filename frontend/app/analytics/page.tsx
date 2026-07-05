"use client";

import { InterestBar } from "@/components/analytics/InterestBar";
import { MetricTile } from "@/components/analytics/MetricTile";
import { VoiceDonut } from "@/components/analytics/VoiceDonut";
import { ErrorState, Skeleton } from "@/components/ui/misc";
import { useDashboard } from "@/hooks/usePodcast";
import type { Tile } from "@/types/dashboard";

// Internal analytics dashboard (PRD 10, 11.6). Every tile is a REAL captured
// number (job timing/statuses, play events, preferences) — nothing is seeded.
// Cost tiles were removed: without an input/output token split any single-rate
// dollar figure understates real spend (honesty rule, PRD 11.6).
export default function AnalyticsPage() {
  const dash = useDashboard();

  if (dash.isLoading) {
    return (
      <div className="grid grid-cols-2 gap-3 pt-2 md:grid-cols-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton key={i} className="h-24 w-full" />
        ))}
      </div>
    );
  }
  if (dash.isError || !dash.data) {
    return <ErrorState message="Could not load analytics." />;
  }

  const d = dash.data;
  return (
    <div className="flex flex-col gap-8 pt-2">
      <div>
        <h1 className="text-2xl font-semibold">Internal Analytics</h1>
        <p className="text-sm text-muted-foreground">
          Every metric here is captured live from real usage: latency from stage
          timing, reliability from job statuses, listening from play events, and
          user aggregates from preferences.
        </p>
      </div>

      <Section title="Operational" tiles={d.operational} />
      <Section title="Product" tiles={d.product} />
      <Section title="User" tiles={d.user} />

      <div className="grid gap-4 md:grid-cols-2">
        <InterestBar data={d.top_interests} />
        <VoiceDonut data={d.voice_distribution} />
      </div>
    </div>
  );
}

function Section({ title, tiles }: { title: string; tiles: Tile[] }) {
  return (
    <div>
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
        {title}
      </h2>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {tiles.map((t) => (
          <MetricTile key={t.label} tile={t} />
        ))}
      </div>
    </div>
  );
}
