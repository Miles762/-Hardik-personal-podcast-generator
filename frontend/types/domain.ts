// Domain types mirroring the FastAPI Pydantic contract (PRD 6).
// Phase 7/8 adds an openapi-typescript build step to generate these from
// /openapi.json; until then they are hand-authored to match the backend.

export type Voice = "rachel" | "adam" | "bella" | "antoni";
export type Tone = "calm" | "energetic" | "professional" | "witty";
export type Length = "short" | "medium" | "long";
export type EpisodeStatus = "pending" | "generating" | "ready" | "failed";

export interface Preference {
  name: string;
  interests: string[];
  voice: Voice;
  tone: Tone;
  podcast_length: Length;
  schedule: string | null;
}

export type PreferenceUpdate = Partial<Preference>;

export interface NewsItem {
  title: string;
  source: string;
  url: string;
  published_at: string;
  summary: string;
  score: number;
}

export interface NewsResponse {
  items: NewsItem[];
  cached: boolean;
}

export interface Story {
  headline: string;
  summary: string | null;
  source: string;
  url: string;
  published_at: string | null;
  score: number | null;
  importance: number | null;
}

export interface EpisodeSummary {
  id: number;
  episode_date: string;
  title: string | null;
  status: EpisodeStatus;
  duration_sec: number | null;
  audio_url: string | null;
  created_at: string;
  generated_at: string | null;
}

export interface EpisodeDetail extends EpisodeSummary {
  script: string | null;
  error: string | null;
  stories: Story[];
}

export interface GenerateResponse {
  episode_id: number;
  status: EpisodeStatus;
  created: boolean;
}

export interface StageStatus {
  stage: string;
  status: string;
  error: string | null;
}

export interface EpisodeStatusResponse {
  episode_id: number;
  status: EpisodeStatus;
  error: string | null;
  stages: StageStatus[];
}
