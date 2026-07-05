// Validated dark-mode dataviz palette (see dataviz skill; validated with
// scripts/validate_palette.js --mode dark). Categorical hues in FIXED order —
// never cycled. Ink/grid follow text tokens, never a series color.

export const CATEGORICAL = [
  "#3987e5", // 1 blue
  "#199e70", // 2 aqua
  "#c98500", // 3 yellow
  "#008300", // 4 green
  "#9085e9", // 5 violet
  "#e66767", // 6 red
];

export const SERIES_BLUE = "#3987e5"; // single-series / sequential default

export const CHART_INK = {
  grid: "#2c2c2a",
  axis: "#898781",
  text: "#c3c2b7",
  surface: "#1a1a19",
};
