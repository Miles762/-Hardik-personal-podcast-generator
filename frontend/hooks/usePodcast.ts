"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { PreferenceUpdate } from "@/types/domain";

// Server-state hooks (PRD 10) — keep components free of fetch logic.

export const keys = {
  preferences: ["preferences"] as const,
  news: ["news"] as const,
  episodes: ["episodes"] as const,
  episode: (id: number) => ["episode", id] as const,
  status: (id: number) => ["status", id] as const,
  dashboard: ["dashboard"] as const,
};

export function useDashboard() {
  return useQuery({ queryKey: keys.dashboard, queryFn: api.getDashboard });
}

export function usePreferences() {
  return useQuery({ queryKey: keys.preferences, queryFn: api.getPreferences });
}

export function useUpdatePreferences() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: PreferenceUpdate) => api.updatePreferences(body),
    onSuccess: (data) => {
      qc.setQueryData(keys.preferences, data);
    },
  });
}

export function useNews() {
  return useQuery({ queryKey: keys.news, queryFn: api.getNews });
}

export function useEpisodes() {
  return useQuery({ queryKey: keys.episodes, queryFn: api.listEpisodes });
}

export function useEpisode(id: number | null) {
  return useQuery({
    queryKey: id ? keys.episode(id) : ["episode", "none"],
    queryFn: () => api.getEpisode(id as number),
    enabled: id != null,
  });
}

export function useGenerate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.generate(),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.episodes });
    },
  });
}

// Poll generation status while an episode is in flight.
export function useEpisodeStatus(id: number | null, active: boolean) {
  return useQuery({
    queryKey: id ? keys.status(id) : ["status", "none"],
    queryFn: () => api.getEpisodeStatus(id as number),
    enabled: id != null && active,
    refetchInterval: (query) => {
      const s = query.state.data?.status;
      return s === "ready" || s === "failed" ? false : 2500;
    },
  });
}
