"use client";

import { Download, Pause, Play } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { formatDuration } from "@/lib/utils";

// Audio player (PRD 10). Streams the MP3 from the /audio rewrite proxy so the
// element and the file are same-origin; the download button uses the same path
// so the `download` attribute works (PRD 9). Seeking relies on Range support.
// While playing it pings /progress so listening metrics are real (PRD 11.6).
export function AudioPlayer({
  episodeId,
  audioUrl,
  title,
  durationSec,
}: {
  episodeId?: number;
  audioUrl: string;
  title: string;
  durationSec: number | null;
}) {
  const ref = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);
  const [current, setCurrent] = useState(0);
  const [total, setTotal] = useState(durationSec ?? 0);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const onTime = () => setCurrent(el.currentTime);
    const onMeta = () => setTotal(el.duration || durationSec || 0);
    const onEnd = () => setPlaying(false);
    el.addEventListener("timeupdate", onTime);
    el.addEventListener("loadedmetadata", onMeta);
    el.addEventListener("ended", onEnd);
    return () => {
      el.removeEventListener("timeupdate", onTime);
      el.removeEventListener("loadedmetadata", onMeta);
      el.removeEventListener("ended", onEnd);
    };
  }, [durationSec]);

  // Ping progress every 10s while playing (real listening metrics, PRD 11.6).
  useEffect(() => {
    if (!playing || episodeId == null) return;
    const id = setInterval(() => {
      const el = ref.current;
      if (el) void api.recordProgress(episodeId, Math.floor(el.currentTime)).catch(() => {});
    }, 10_000);
    return () => clearInterval(id);
  }, [playing, episodeId]);

  function toggle() {
    const el = ref.current;
    if (!el) return;
    if (playing) el.pause();
    else void el.play();
    setPlaying(!playing);
    // Record final position on pause so partial listens count.
    if (playing && episodeId != null) {
      void api.recordProgress(episodeId, Math.floor(el.currentTime)).catch(() => {});
    }
  }

  function seek(e: React.ChangeEvent<HTMLInputElement>) {
    const el = ref.current;
    if (!el) return;
    const t = Number(e.target.value);
    el.currentTime = t;
    setCurrent(t);
  }

  const pct = total > 0 ? (current / total) * 100 : 0;

  return (
    <div className="flex flex-col gap-3">
      <audio ref={ref} src={audioUrl} preload="metadata" />
      <div className="flex items-center gap-4">
        <Button size="icon" onClick={toggle} aria-label={playing ? "Pause" : "Play"}>
          {playing ? <Pause size={18} /> : <Play size={18} />}
        </Button>
        <div className="min-w-0 flex-1">
          <p className="truncate font-medium">{title}</p>
          <p className="text-xs text-muted-foreground">
            {formatDuration(current)} / {formatDuration(total)}
          </p>
        </div>
        <a href={audioUrl} download>
          <Button variant="outline" size="icon" aria-label="Download">
            <Download size={16} />
          </Button>
        </a>
      </div>
      <input
        type="range"
        min={0}
        max={total || 0}
        value={current}
        onChange={seek}
        className="h-1.5 w-full cursor-pointer appearance-none rounded-full"
        style={{
          background: `linear-gradient(to right, hsl(var(--primary)) ${pct}%, hsl(var(--secondary)) ${pct}%)`,
        }}
        aria-label="Seek"
      />
    </div>
  );
}
