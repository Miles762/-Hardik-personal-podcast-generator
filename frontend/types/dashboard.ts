// Mirrors app/schemas/dashboard.py (PRD 6, 11.6).
// The seeded concept was removed; every value is real, so no source field.

export interface Tile {
  label: string;
  value: number;
  unit: string;
}

export interface NameValue {
  name: string;
  value: number;
}

export interface DashboardResponse {
  product: Tile[];
  user: Tile[];
  operational: Tile[];
  top_interests: NameValue[];
  voice_distribution: NameValue[];
}
