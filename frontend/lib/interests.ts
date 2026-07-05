// Pure helpers for the interests editor. Mirrors the backend rules
// (trim/collapse whitespace, case-insensitive dedupe, 100-char cap) so a value
// the UI accepts is never rejected by the API.

export const MAX_INTEREST_LENGTH = 100;
export const MAX_INTERESTS = 20;

/** Normalize raw user input to a clean interest string ("" when unusable). */
export function normalizeInterest(raw: string): string {
  return raw.replace(/\s+/g, " ").trim().slice(0, MAX_INTEREST_LENGTH);
}

/** Add an interest, ignoring empties and case-insensitive duplicates. */
export function addInterest(list: string[], raw: string): string[] {
  const value = normalizeInterest(raw);
  if (!value || list.length >= MAX_INTERESTS) return list;
  if (list.some((x) => x.toLowerCase() === value.toLowerCase())) return list;
  return [...list, value];
}
