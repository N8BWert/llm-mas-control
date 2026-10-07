// World/screen transforms, tile math and display-only zone hit tests.
// The engine is the authority on constraints; these only drive previews.

import type { Command, GameView, Rect, Vec, Zone } from "../types";

// World coordinates are meters with y up; screen coordinates are pixels with y down.
export class WorldTransform {
  readonly scale: number;
  private readonly offsetX: number;
  private readonly offsetY: number;

  constructor(
    readonly arena: Rect,
    widthPx: number,
    heightPx: number,
    padding = 12,
  ) {
    const w = arena.x_max - arena.x_min;
    const h = arena.y_max - arena.y_min;
    this.scale = Math.max(Math.min((widthPx - 2 * padding) / w, (heightPx - 2 * padding) / h), 1);
    this.offsetX = (widthPx - w * this.scale) / 2;
    this.offsetY = (heightPx - h * this.scale) / 2;
  }

  toScreen(p: Vec): Vec {
    return {
      x: this.offsetX + (p.x - this.arena.x_min) * this.scale,
      y: this.offsetY + (this.arena.y_max - p.y) * this.scale,
    };
  }

  toWorld(p: Vec): Vec {
    return {
      x: this.arena.x_min + (p.x - this.offsetX) / this.scale,
      y: this.arena.y_max - (p.y - this.offsetY) / this.scale,
    };
  }

  length(meters: number): number {
    return meters * this.scale;
  }
}

export function tileSize(view: GameView): Vec {
  const a = view.arena;
  return { x: (a.x_max - a.x_min) / view.width, y: (a.y_max - a.y_min) / view.height };
}

export function tileCenter(view: GameView, i: number, j: number): Vec {
  const size = tileSize(view);
  return { x: view.arena.x_min + (i + 0.5) * size.x, y: view.arena.y_min + (j + 0.5) * size.y };
}

export function tileAt(view: GameView, p: Vec): [number, number] | null {
  const size = tileSize(view);
  const i = Math.floor((p.x - view.arena.x_min) / size.x);
  const j = Math.floor((p.y - view.arena.y_min) / size.y);
  if (i < 0 || j < 0 || i >= view.width || j >= view.height) return null;
  return [i, j];
}

// Tiles are the row-major flattening of a (width, height) grid.
export function tileStateAt(view: GameView, i: number, j: number): number {
  return view.tiles[i * view.height + j] ?? 0;
}

export function commandTarget(view: GameView, command: Pick<Command, "kind" | "target">): Vec {
  const [a, b] = command.target;
  return command.kind === "move" ? { x: a, y: b } : tileCenter(view, a, b);
}

export function zoneContains(zone: Zone, p: Vec): boolean {
  if (zone.rect) {
    const r = zone.rect;
    return p.x >= r.x_min && p.x <= r.x_max && p.y >= r.y_min && p.y <= r.y_max;
  }
  if (zone.circle) {
    const c = zone.circle;
    return Math.hypot(p.x - c.x, p.y - c.y) <= c.radius;
  }
  return false;
}

// Liang-Barsky clipping: does segment a-b touch the rectangle?
function segmentHitsRect(a: Vec, b: Vec, r: Rect): boolean {
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  let t0 = 0;
  let t1 = 1;
  const edges: [number, number][] = [
    [-dx, a.x - r.x_min],
    [dx, r.x_max - a.x],
    [-dy, a.y - r.y_min],
    [dy, r.y_max - a.y],
  ];
  for (const [p, q] of edges) {
    if (p === 0) {
      if (q < 0) return false;
    } else {
      const t = q / p;
      if (p < 0) t0 = Math.max(t0, t);
      else t1 = Math.min(t1, t);
      if (t0 > t1) return false;
    }
  }
  return true;
}

function segmentHitsCircle(a: Vec, b: Vec, c: { x: number; y: number; radius: number }): boolean {
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const len2 = dx * dx + dy * dy;
  const t = len2 === 0 ? 0 : Math.max(0, Math.min(1, ((c.x - a.x) * dx + (c.y - a.y) * dy) / len2));
  return Math.hypot(a.x + t * dx - c.x, a.y + t * dy - c.y) <= c.radius;
}

export function segmentHitsZone(a: Vec, b: Vec, zone: Zone): boolean {
  if (zone.rect) return segmentHitsRect(a, b, zone.rect);
  if (zone.circle) return segmentHitsCircle(a, b, zone.circle);
  return false;
}

export function pathCrossesZones(points: Vec[], zones: Zone[]): boolean {
  if (points.length === 1) return zones.some((zone) => zoneContains(zone, points[0]));
  for (let k = 1; k < points.length; k++) {
    if (zones.some((zone) => segmentHitsZone(points[k - 1], points[k], zone))) return true;
  }
  return false;
}

export function restrictedZones(view: GameView | null): Zone[] {
  return (view?.active_constraints ?? []).flatMap((c) => c.restricted_zone?.zones ?? []);
}
