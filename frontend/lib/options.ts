import type { Length, Tone, Voice } from "@/types/domain";

export const INTEREST_OPTIONS = [
  "technology",
  "space",
  "science",
  "world news",
  "business",
  "sports",
  "politics",
  "health",
  "entertainment",
  "climate",
];

export const VOICE_OPTIONS: { value: Voice; label: string }[] = [
  { value: "rachel", label: "Rachel — warm, natural" },
  { value: "adam", label: "Adam — deep, steady" },
  { value: "bella", label: "Bella — bright, friendly" },
  { value: "antoni", label: "Antoni — calm, measured" },
];

export const TONE_OPTIONS: { value: Tone; label: string }[] = [
  { value: "professional", label: "Professional" },
  { value: "calm", label: "Calm" },
  { value: "energetic", label: "Energetic" },
  { value: "witty", label: "Witty" },
];

export const LENGTH_OPTIONS: { value: Length; label: string }[] = [
  { value: "short", label: "Short — about 3 min" },
  { value: "medium", label: "Medium — about 6 min" },
  { value: "long", label: "Long — about 10 min" },
];
