"use client";

import { Clock, Headphones, Sparkles } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { formatDuration } from "@/lib/utils";
import type { EpisodeSummary } from "@/types/domain";

// Quick Stats (PRD 10): episodes generated, total length, top interest.
// "Top interest" reflects the user's CURRENT saved preference (interests[0]),
// not past-episode history — it's forward-looking, matching Settings.
export function QuickStats({
  episodes,
  favoriteCategory,
}: {
  episodes: EpisodeSummary[];
  favoriteCategory: string;
}) {
  const ready = episodes.filter((e) => e.status === "ready");
  const totalSec = ready.reduce((acc, e) => acc + (e.duration_sec ?? 0), 0);

  const stats: {
    label: string;
    value: string;
    icon: LucideIcon;
    hint?: string;
  }[] = [
    { label: "Episodes", value: String(ready.length), icon: Headphones },
    { label: "Total length", value: formatDuration(totalSec), icon: Clock },
    {
      label: "Top interest",
      value: favoriteCategory || "—",
      icon: Sparkles,
      hint: "From your settings",
    },
  ];

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
      {stats.map((s) => {
        const Icon = s.icon;
        return (
          <Card
            key={s.label}
            className="group relative overflow-hidden transition-all duration-300 hover:-translate-y-0.5 hover:shadow-2xl hover:ring-1 hover:ring-primary/40"
          >
            {/* Soft accent glow that intensifies on hover. */}
            <div
              aria-hidden
              className="pointer-events-none absolute -right-6 -top-6 h-24 w-24 rounded-full bg-primary/10 blur-2xl transition-opacity duration-300 group-hover:bg-primary/25"
            />
            <CardContent className="relative flex items-start justify-between p-5 pt-5">
              <div className="min-w-0">
                <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                  {s.label}
                </p>
                <p className="mt-1.5 truncate text-2xl font-semibold capitalize tracking-tight">
                  {s.value}
                </p>
                {s.hint ? (
                  <p className="mt-0.5 text-[11px] text-muted-foreground/70">{s.hint}</p>
                ) : null}
              </div>
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary transition-colors duration-300 group-hover:bg-primary/20">
                <Icon size={18} />
              </span>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
