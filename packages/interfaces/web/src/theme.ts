import { TileState } from "./types";

// All friendly robots are blue; roles are different shades of blue.
const ROLE_SHADES: Record<string, string> = {
  worker: "#60a5fa",
  builder: "#2563eb",
  scout: "#bfdbfe",
  miner: "#1e40af",
};
const FALLBACK_SHADES = ["#3b82f6", "#93c5fd", "#1d4ed8", "#dbeafe"];

export function roleColor(role: string): string {
  if (ROLE_SHADES[role]) return ROLE_SHADES[role];
  let hash = 0;
  for (const ch of role) hash = (hash * 31 + ch.charCodeAt(0)) | 0;
  return FALLBACK_SHADES[Math.abs(hash) % FALLBACK_SHADES.length];
}

export const TILE_COLORS: Record<number, string> = {
  [TileState.EMPTY]: "#1c2420",
  [TileState.CASTLE]: "#8b5cf6",
  [TileState.FARM]: "#4d7c0f",
  [TileState.QUARRY]: "#78716c",
  [TileState.WATER]: "#155e75",
  [TileState.APPLE]: "#db2777",
  [TileState.OBSCURED]: "#0b0b0b",
};

export const TILE_NAMES: Record<number, string> = {
  [TileState.EMPTY]: "Empty",
  [TileState.CASTLE]: "Castle",
  [TileState.FARM]: "Farm",
  [TileState.QUARRY]: "Quarry",
  [TileState.WATER]: "Water",
  [TileState.APPLE]: "Apple",
  [TileState.OBSCURED]: "Obscured",
};

export const ITEM_COLORS: Record<string, string> = {
  stone: "#d6d3d1",
  food: "#a3e635",
  apple: "#f472b6",
};

export const COLORS = {
  background: "#111714",
  grid: "rgba(255,255,255,0.04)",
  enemy: "#ef4444",
  objective: "#facc15",
  selected: "#ffffff",
  violation: "#ff3b30",
  warning: "#f59e0b",
  ok: "#22c55e",
  restricted: "#ef4444",
  timed: "#f59e0b",
  base: "#38bdf8",
  path: "rgba(147,197,253,0.8)",
  pathBad: "#ff3b30",
  disabled: "#4b5563",
};

export function healthColor(health: number): string {
  if (health > 0.6) return COLORS.ok;
  if (health > 0.3) return COLORS.warning;
  return COLORS.violation;
}
