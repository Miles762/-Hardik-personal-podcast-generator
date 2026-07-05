// Typed API client. All requests go through the Next /api rewrite proxy to
// FastAPI, so the browser stays same-origin (PRD 9). No business logic here —
// just typed fetch + a consistent error envelope (PRD 6).

import type { DashboardResponse } from "@/types/dashboard";
import type {
  EpisodeDetail,
  EpisodeStatusResponse,
  EpisodeSummary,
  GenerateResponse,
  NewsResponse,
  Preference,
  PreferenceUpdate,
} from "@/types/domain";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    let message = res.statusText;
    try {
      const body = await res.json();
      message = body?.error?.message ?? body?.detail ?? message;
    } catch {
      // non-JSON error body; keep statusText
    }
    throw new ApiError(res.status, message);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  getPreferences: () => request<Preference>("/preferences"),
  updatePreferences: (body: PreferenceUpdate) =>
    request<Preference>("/preferences", { method: "PATCH", body: JSON.stringify(body) }),

  getNews: () => request<NewsResponse>("/news"),

  generate: () => request<GenerateResponse>("/generate", { method: "POST" }),

  listEpisodes: () => request<EpisodeSummary[]>("/episodes"),
  getEpisode: (id: number) => request<EpisodeDetail>(`/episodes/${id}`),
  getEpisodeStatus: (id: number) =>
    request<EpisodeStatusResponse>(`/episodes/${id}/status`),
  recordProgress: (id: number, positionSec: number) =>
    request<void>(`/episodes/${id}/progress`, {
      method: "POST",
      body: JSON.stringify({ position_sec: positionSec }),
    }),

  getDashboard: () => request<DashboardResponse>("/dashboard"),
};
