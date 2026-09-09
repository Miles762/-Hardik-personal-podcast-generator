"use client";

import { useState } from "react";
import { Trash2 } from "lucide-react";

import { AudioPlayer } from "@/components/player/AudioPlayer";
import { Badge, EmptyState, Skeleton } from "@/components/ui/misc";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  useClearEpisodes,
  useDeleteEpisode,
  useEpisodes,
} from "@/hooks/usePodcast";
import { formatDate, formatDuration } from "@/lib/utils";

// Episode History (PRD 10): cards with date, title, duration, play, download,
// plus per-episode delete and a clear-all control.
export default function HistoryPage() {
  const episodes = useEpisodes();
  const deleteEpisode = useDeleteEpisode();
  const clearEpisodes = useClearEpisodes();
  const [confirmingClear, setConfirmingClear] = useState(false);

  const hasEpisodes = !!episodes.data && episodes.data.length > 0;

  return (
    <div className="flex flex-col gap-4 pt-2">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Episode History</h1>
        {hasEpisodes &&
          (confirmingClear ? (
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">Delete all?</span>
              <Button
                variant="destructive"
                size="sm"
                disabled={clearEpisodes.isPending}
                onClick={() =>
                  clearEpisodes.mutate(undefined, {
                    onSettled: () => setConfirmingClear(false),
                  })
                }
              >
                {clearEpisodes.isPending ? "Clearing…" : "Yes, clear all"}
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setConfirmingClear(false)}
              >
                Cancel
              </Button>
            </div>
          ) : (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setConfirmingClear(true)}
            >
              <Trash2 className="h-4 w-4" />
              Clear all
            </Button>
          ))}
      </div>

      {episodes.isLoading ? (
        <Skeleton className="h-40 w-full" />
      ) : hasEpisodes ? (
        episodes.data.map((e) => (
          <Card key={e.id}>
            <CardHeader className="flex-row items-start justify-between">
              <div>
                <CardTitle>{e.title ?? "Untitled episode"}</CardTitle>
                <p className="mt-1 text-sm text-muted-foreground">
                  {formatDate(e.episode_date)} · {formatDuration(e.duration_sec)}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <Badge className="capitalize">{e.status}</Badge>
                <Button
                  variant="ghost"
                  size="sm"
                  aria-label="Delete episode"
                  disabled={deleteEpisode.isPending}
                  onClick={() => deleteEpisode.mutate(e.id)}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
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
