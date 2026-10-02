// Draws constraint zones per kind and live state, and computes the per-robot
// countdown rings (timed-entry dwell, activity interval).

import Konva from "konva";
import { ConstraintState, constraintKind, constraintZones, type Constraint, type ConstraintStatus, type GameView, type Zone } from "../types";
import { COLORS } from "../theme";
import type { WorldTransform } from "./geometry";

let hatchCanvas: HTMLCanvasElement | null = null;

function hatchPattern(): HTMLImageElement {
  if (!hatchCanvas) {
    hatchCanvas = document.createElement("canvas");
    hatchCanvas.width = hatchCanvas.height = 10;
    const ctx = hatchCanvas.getContext("2d")!;
    ctx.strokeStyle = "rgba(239,68,68,0.55)";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(0, 10);
    ctx.lineTo(10, 0);
    ctx.moveTo(-5, 5);
    ctx.lineTo(5, -5);
    ctx.moveTo(5, 15);
    ctx.lineTo(15, 5);
    ctx.stroke();
  }
  return hatchCanvas as unknown as HTMLImageElement;
}

function zoneShape(zone: Zone, t: WorldTransform, attrs: Konva.ShapeConfig): Konva.Shape | null {
  if (zone.rect) {
    const r = zone.rect;
    const topLeft = t.toScreen({ x: r.x_min, y: r.y_max });
    return new Konva.Rect({ ...attrs, ...topLeft, width: t.length(r.x_max - r.x_min), height: t.length(r.y_max - r.y_min) });
  }
  if (zone.circle) {
    const c = zone.circle;
    return new Konva.Circle({ ...attrs, ...t.toScreen(c), radius: t.length(c.radius) });
  }
  return null;
}

function zoneLabelPosition(zone: Zone, t: WorldTransform) {
  if (zone.rect) return t.toScreen({ x: zone.rect.x_min, y: zone.rect.y_max });
  const c = zone.circle!;
  const s = t.toScreen(c);
  return { x: s.x - t.length(c.radius), y: s.y - t.length(c.radius) };
}

function stateColor(status: ConstraintStatus | undefined, okColor: string): string {
  if (status?.state === ConstraintState.VIOLATED) return COLORS.violation;
  if (status?.state === ConstraintState.WARNING) return COLORS.warning;
  return okColor;
}

function zoneStyle(constraint: Constraint, status: ConstraintStatus | undefined): Konva.ShapeConfig | null {
  const violated = status?.state === ConstraintState.VIOLATED;
  switch (constraintKind(constraint)) {
    case "restricted_zone":
      return {
        fillPatternImage: hatchPattern(),
        fillPatternRepeat: "repeat",
        stroke: COLORS.restricted,
        strokeWidth: violated ? 3 : 1.5,
        opacity: violated ? 1 : 0.85,
      };
    case "occupation_zone":
      return { stroke: stateColor(status, COLORS.ok), strokeWidth: 2.5, dash: [8, 5], fill: "rgba(34,197,94,0.06)" };
    case "timed_entry_zone":
      return { stroke: violated ? COLORS.violation : COLORS.timed, strokeWidth: violated ? 3 : 1.5, fill: "rgba(245,158,11,0.16)" };
    case "activity_interval":
      return { stroke: COLORS.base, strokeWidth: 2, dash: [3, 4], fill: "rgba(56,189,248,0.08)" };
    default:
      return null;
  }
}

export function drawConstraintZones(layer: Konva.Layer, view: GameView, t: WorldTransform) {
  const statuses = new Map(view.constraint_statuses.map((s) => [s.constraint_id, s]));
  for (const constraint of view.active_constraints) {
    const status = statuses.get(constraint.id);
    const style = zoneStyle(constraint, status);
    if (!style) continue;
    constraintZones(constraint).forEach((zone, index) => {
      const shape = zoneShape(zone, t, style);
      if (!shape) return;
      layer.add(shape);
      let text = constraint.activity_interval ? "Base (refuel)" : constraint.label;
      if (constraint.occupation_zone) {
        text += `  ${status?.zone_counts[index] ?? 0}/${constraint.occupation_zone.min_robots} robots`;
      }
      const at = zoneLabelPosition(zone, t);
      layer.add(new Konva.Text({ x: at.x + 2, y: at.y - 14, text, fontSize: 11, fill: (style.stroke as string) ?? "#fff" }));
    });
  }
  layer.draw();
}

export interface Ring {
  fraction: number;
  color: string;
}

export function robotConstraintRings(view: GameView): Map<number, Ring[]> {
  const rings = new Map<number, Ring[]>();
  const statuses = new Map(view.constraint_statuses.map((s) => [s.constraint_id, s]));
  for (const constraint of view.active_constraints) {
    const status = statuses.get(constraint.id);
    if (!status) continue;
    const max = constraint.timed_entry_zone?.max_dwell_s ?? constraint.activity_interval?.max_active_s;
    if (!max) continue;
    const color = constraint.timed_entry_zone ? COLORS.timed : COLORS.base;
    for (const [id, seconds] of Object.entries(status.timers)) {
      if (seconds >= max) continue;
      const list = rings.get(Number(id)) ?? [];
      list.push({ fraction: seconds / max, color: seconds / max < 0.25 ? COLORS.violation : color });
      rings.set(Number(id), list);
    }
  }
  return rings;
}
