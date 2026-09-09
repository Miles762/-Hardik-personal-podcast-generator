"use client";

import { Sparkles } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { QuickStats } from "@/components/dashboard/QuickStats";
import { StoryList } from "@/components/dashboard/StoryList";
import { AudioPlayer } from "@/components/player/AudioPlayer";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState, ErrorState, Skeleton } from "@/components/ui/misc";
import {
  useEpisode,
  useEpisodeStatus,
  useEpisodes,
  useGenerate,
  usePreferences,
} from "@/hooks/usePodcast";
import { cn, formatDate, formatRelative } from "@/lib/utils";

export function Dashboard() {
  const prefs = usePreferences();
  const episodes = useEpisodes();
  const generate = useGenerate();

  // Track the in-flight episode so we can poll its status.
  const [activeId, setActiveId] = useState<number | null>(null);

  // Multiple episodes per day are allowed; show the most recent one. The list
  // is ordered newest first by the backend.
  const latestEpisode = episodes.data?.[0] ?? null;

  const focusId = activeId ?? latestEpisode?.id ?? null;
  const inFlight =
    (focusId != null &&
      (latestEpisode?.status === "pending" || latestEpisode?.status === "generating")) ||
    activeId != null;

  const status = useEpisodeStatus(focusId, inFlight);
  const detail = useEpisode(focusId);

  // When polling reports done, refresh lists + detail and stop tracking.
  useEffect(() => {
    const s = status.data?.status;
    if (s === "ready" || s === "failed") {
      void episodes.refetch();
      void detail.refetch();
      setActiveId(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status.data?.status]);

  async function onGenerate() {
    try {
      const res = await generate.mutateAsync();
      setActiveId(res.episode_id);
    } catch {
      // Surfaced below via generate.isError (e.g. 409 while one is in flight).
    }
    void episodes.refetch();
  }

  const generating = inFlight || generate.isPending;
  const currentStage = status.data?.stages?.filter((s) => s.status !== "done").at(-1)?.stage;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-2 pt-1">
        <div className="inline-flex w-fit items-center gap-1.5 rounded-full border border-border/60 bg-secondary/40 px-2.5 py-1 text-[11px] font-medium text-muted-foreground">
          <span className="h-1.5 w-1.5 rounded-full bg-primary" />
          Today&apos;s briefing
        </div>
        <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
          {prefs.data ? (
            <>
              Hey{" "}
              <span className="bg-gradient-to-r from-primary via-violet-400 to-primary bg-clip-text text-transparent">
                {prefs.data.name}
              </span>
            </>
          ) : (
            "Your daily briefing"
          )}
        </h1>
        <p className="text-muted-foreground">
          A fresh, personalized podcast from today&apos;s news.
        </p>
      </div>

      <Card className="relative overflow-hidden">
        {/* Ambient accent behind the hero card. */}
        <div
          aria-hidden
          className="pointer-events-none absolute -right-10 -top-10 h-40 w-40 rounded-full bg-primary/15 blur-3xl"
        />
        <CardHeader className="relative flex-row items-center justify-between">
          <CardTitle>Latest Podcast</CardTitle>
          {/* Single button: every click creates a new episode (multiple per day). */}
          <Button
            onClick={() => onGenerate()}
            disabled={generating}
            className="shadow-lg shadow-primary/20 transition-transform hover:scale-[1.03] active:scale-95"
          >
            <Sparkles size={16} className={generating ? "animate-pulse" : ""} />
            {generating ? "Generating..." : "Generate"}
          </Button>
        </CardHeader>
        <CardContent className="relative">
          {generate.isError && !generating ? (
            <div className="mb-4">
              <ErrorState
                message={
                  generate.error instanceof Error
                    ? generate.error.message
                    : "Could not start generation. Please try again."
                }
              />
            </div>
          ) : null}
          {generating ? (
            <div className="flex flex-col gap-3">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <span className="h-2 w-2 animate-pulse rounded-full bg-primary" />
                {currentStage ? `Working: ${currentStage.replace("_", " ")}` : "Starting up..."}
              </div>
              <Skeleton className="h-12 w-full" />
            </div>
          ) : detail.data?.status === "ready" && detail.data.audio_url ? (
            <div className="flex flex-col gap-4">
              <AudioPlayer
                episodeId={detail.data.id}
                audioUrl={detail.data.audio_url}
                title={detail.data.title ?? "Your episode"}
                durationSec={detail.data.duration_sec}
              />
              <p className="text-xs text-muted-foreground">
                Generated {formatRelative(detail.data.generated_at)}
              </p>
            </div>
          ) : detail.data?.status === "failed" ? (
            <ErrorState message={`Generation failed: ${detail.data.error ?? "unknown error"}`} />
          ) : (
            <EmptyState
              title="No episode yet today"
              hint="Hit Generate to create your personalized podcast."
            />
          )}
        </CardContent>
      </Card>

      {prefs.data ? (
        <QuickStats
          episodes={episodes.data ?? []}
          favoriteCategory={prefs.data.interests[0] ?? ""}
        />
      ) : null}

      {detail.data?.stories?.length ? <StoryList stories={detail.data.stories} /> : null}

      <Card>
        <CardHeader className="flex-row items-center justify-between">
          <CardTitle>Recent Episodes</CardTitle>
          <Link href="/history" className="text-sm text-primary hover:underline">
            View all
          </Link>
        </CardHeader>
        <CardContent className="flex flex-col gap-2">
          {episodes.isLoading ? (
            <Skeleton className="h-16 w-full" />
          ) : episodes.data && episodes.data.length > 0 ? (
            episodes.data.slice(0, 4).map((e) => (
              <div
                key={e.id}
                className="flex items-center justify-between rounded-md border border-border/70 px-3 py-2.5 transition-colors hover:border-primary/30 hover:bg-secondary/40"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">{e.title ?? "Untitled"}</p>
                  <p className="text-xs text-muted-foreground">{formatDate(e.episode_date)}</p>
                </div>
                <span
                  className={cn(
                    "ml-3 shrink-0 rounded-full px-2 py-0.5 text-[11px] font-medium capitalize",
                    e.status === "ready"
                      ? "bg-emerald-500/15 text-emerald-400"
                      : e.status === "failed"
                        ? "bg-destructive/15 text-destructive-foreground"
                        : "bg-primary/15 text-primary",
                  )}
                >
                  {e.status}
                </span>
              </div>
            ))
          ) : (
            <EmptyState title="No episodes yet" />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
