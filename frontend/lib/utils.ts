import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

// shadcn/ui class-merge helper.
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDuration(sec: number | null | undefined): string {
  if (!sec || sec <= 0) return "--:--";
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

const DATE_ONLY_RE = /^(\d{4})-(\d{2})-(\d{2})$/;

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "";
  // Date-only strings (episode_date) are calendar dates, not instants: parse
  // them as local so "2026-07-05" never renders as the previous day.
  const dateOnly = DATE_ONLY_RE.exec(iso);
  const d = dateOnly
    ? new Date(Number(dateOnly[1]), Number(dateOnly[2]) - 1, Number(dateOnly[3]))
    : new Date(iso);
  return d.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function formatRelative(iso: string | null | undefined): string {
  if (!iso) return "";
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.round(diffMs / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return formatDate(iso);
}
