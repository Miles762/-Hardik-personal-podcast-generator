"use client";

import { Download } from "lucide-react";

import { AudioPlayer } from "@/components/player/AudioPlayer";
import { Badge, EmptyState, Skeleton } from "@/components/ui/misc";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useEpisodes } from "@/hooks/usePodcast";
import { formatDate, formatDuration } from "@/lib/utils";

// Episode History (PRD 10): cards with date, title, duration, play, download.
export default function HistoryPage() {
  const episodes = useEpisodes();

  return (
    <div className="flex flex-col gap-4 pt-2">
      <h1 className="text-2xl font-semibold">Episode History</h1>

      {episodes.isLoading ? (
        <Skeleton className="h-40 w-full" />
      ) : episodes.data && episodes.data.length > 0 ? (
        episodes.data.map((e) => (
          <Card key={e.id}>
            <CardHeader className="flex-row items-start justify-between">
              <div>
                <CardTitle>{e.title ?? "Untitled episode"}</CardTitle>
                <p className="mt-1 text-sm text-muted-foreground">
                  {formatDate(e.episode_date)} · {formatDuration(e.duration_sec)}
                </p>
              </div>
              <Badge className="capitalize">{e.status}</Badge>
            </CardHeader>
            <CardContent>
              {e.status === "ready" && e.audio_url ? (
                <AudioPlayer
                  episodeId={e.id}
                  audioUrl={e.audio_url}
                  title={e.title ?? "Episode"}
                  durationSec={e.duration_sec}
                />
              ) : e.status === "failed" ? (
                <p className="text-sm text-destructive-foreground">Generation failed.</p>
              ) : (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <span className="h-2 w-2 animate-pulse rounded-full bg-primary" />
                  {e.status}...
                </div>
              )}
            </CardContent>
          </Card>
        ))
      ) : (
        <EmptyState title="No episodes yet" hint="Generate your first episode from the dashboard." />
      )}
    </div>
  );
}
