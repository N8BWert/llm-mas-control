// Konva stage for the map. Rendering only: pointer input is forwarded to
// handlers (see tools.ts) in both world and screen coordinates.
//
// Layers, bottom to top: terrain, constraint zones, intents (paths and
// destinations), entities (robots, enemies, objectives), interaction
// (selection box, path drafts and previews).

import Konva from "konva";
import type { GameView, Vec } from "../types";
import { COLORS, ITEM_COLORS, TILE_COLORS, healthColor, roleColor } from "../theme";
import { WorldTransform, commandTarget } from "./geometry";
import { drawConstraintZones, robotConstraintRings } from "./constraintLayer";

export const ROBOT_RADIUS_M = 0.055;
export const ENEMY_RADIUS_M = 0.2;

export interface MapPointer {
  world: Vec;
  screen: Vec;
  button: number;
  shift: boolean;
  additive: boolean;
}

export interface PointerHandlers {
  down?(pointer: MapPointer): void;
  move?(pointer: MapPointer): void;
  up?(pointer: MapPointer): void;
  leave?(): void;
}

export interface Overlay {
  selectionBox?: [Vec, Vec];
  path?: { points: Vec[]; bad: boolean };
  previews?: { from: Vec; to: Vec; bad: boolean }[];
}

export interface RenderInput {
  view: GameView;
  selected: ReadonlySet<number>;
  offending: ReadonlySet<number>;
}

export class MapView {
  readonly stage: Konva.Stage;
  transform: WorldTransform | null = null;
  handlers: PointerHandlers = {};

  private readonly terrain = new Konva.Layer({ listening: false });
  private readonly zones = new Konva.Layer({ listening: false });
  private readonly intents = new Konva.Layer({ listening: false });
  private readonly entities = new Konva.Layer({ listening: false });
  private readonly interaction = new Konva.Layer({ listening: false });
  private readonly resizeObserver: ResizeObserver;
  private terrainKey = "";
  private last: RenderInput | null = null;
  private overlay: Overlay = {};

  constructor(private readonly container: HTMLDivElement) {
    this.stage = new Konva.Stage({
      container,
      width: container.clientWidth,
      height: container.clientHeight,
    });
    this.stage.add(this.terrain, this.zones, this.intents, this.entities, this.interaction);
    this.resizeObserver = new ResizeObserver(() => this.resize());
    this.resizeObserver.observe(container);
    container.addEventListener("contextmenu", (e) => e.preventDefault());
    this.stage.on("pointerdown", (e) => this.forward("down", e.evt));
    this.stage.on("pointermove", (e) => this.forward("move", e.evt));
    this.stage.on("pointerup", (e) => this.forward("up", e.evt));
    this.stage.on("pointerleave", () => this.handlers.leave?.());
  }

  destroy() {
    this.resizeObserver.disconnect();
    this.stage.destroy();
  }

  private forward(kind: "down" | "move" | "up", evt: PointerEvent) {
    const screen = this.stage.getPointerPosition();
    if (!screen || !this.transform) return;
    this.handlers[kind]?.({
      world: this.transform.toWorld(screen),
      screen,
      button: evt.button,
      shift: evt.shiftKey,
      additive: evt.shiftKey || evt.ctrlKey || evt.metaKey,
    });
  }

  private resize() {
    this.stage.size({ width: this.container.clientWidth, height: this.container.clientHeight });
    this.terrainKey = "";
    if (this.last) this.render(this.last);
  }

  robotRadius(): number {
    return Math.max(this.transform?.length(ROBOT_RADIUS_M) ?? 8, 7);
  }

  render(input: RenderInput) {
    this.last = input;
    const { view } = input;
    const width = this.stage.width();
    const height = this.stage.height();
    if (width === 0 || height === 0) return;
    this.transform = new WorldTransform(view.arena, width, height);

    const key = `${width}x${height}:${view.width}x${view.height}:${view.tiles.join("")}`;
    if (key !== this.terrainKey) {
      this.terrainKey = key;
      this.drawTerrain(view);
    }
    this.zones.destroyChildren();
    drawConstraintZones(this.zones, view, this.transform);
    this.drawIntents(input);
    this.drawEntities(input);
    this.drawOverlay();
  }

  setOverlay(overlay: Overlay) {
    this.overlay = overlay;
    this.drawOverlay();
  }

  private drawTerrain(view: GameView) {
    const t = this.transform!;
    this.terrain.destroyChildren();
    const a = view.arena;
    const topLeft = t.toScreen({ x: a.x_min, y: a.y_max });
    const size = { w: t.length(a.x_max - a.x_min), h: t.length(a.y_max - a.y_min) };
    this.terrain.add(new Konva.Rect({ ...topLeft, width: size.w, height: size.h, fill: TILE_COLORS[0] }));
    const tw = size.w / view.width;
    const th = size.h / view.height;
    for (let i = 0; i < view.width; i++) {
      for (let j = 0; j < view.height; j++) {
        const state = view.tiles[i * view.height + j];
        if (!state) continue;
        this.terrain.add(
          new Konva.Rect({
            x: topLeft.x + i * tw,
            y: topLeft.y + (view.height - 1 - j) * th,
            width: tw,
            height: th,
            fill: TILE_COLORS[state] ?? TILE_COLORS[0],
          }),
        );
      }
    }
    for (let i = 1; i < view.width; i++) {
      const x = topLeft.x + i * tw;
      this.terrain.add(new Konva.Line({ points: [x, topLeft.y, x, topLeft.y + size.h], stroke: COLORS.grid }));
    }
    for (let j = 1; j < view.height; j++) {
      const y = topLeft.y + j * th;
      this.terrain.add(new Konva.Line({ points: [topLeft.x, y, topLeft.x + size.w, y], stroke: COLORS.grid }));
    }
    this.terrain.draw();
  }

  private drawIntents({ view, selected }: RenderInput) {
    const t = this.transform!;
    this.intents.destroyChildren();
    for (const agent of view.agent_states) {
      const waypoints = agent.plan.map((command) => commandTarget(view, command));
      if (!waypoints.length && agent.busy && agent.has_target && agent.target) waypoints.push(agent.target);
      if (!waypoints.length) continue;
      const opacity = selected.has(agent.id) ? 1 : 0.45;
      const points = [agent.position, ...waypoints].flatMap((p) => {
        const s = t.toScreen(p);
        return [s.x, s.y];
      });
      this.intents.add(new Konva.Line({ points, stroke: COLORS.path, strokeWidth: 1.5, dash: [6, 4], opacity }));
      waypoints.forEach((p, index) => {
        const s = t.toScreen(p);
        const last = index === waypoints.length - 1;
        this.intents.add(
          last
            ? new Konva.Text({ x: s.x - 5, y: s.y - 7, text: "✕", fontSize: 13, fill: COLORS.path, opacity })
            : new Konva.Circle({ x: s.x, y: s.y, radius: 3, fill: COLORS.path, opacity }),
        );
      });
    }
    this.intents.draw();
  }

  private drawEntities({ view, selected, offending }: RenderInput) {
    const t = this.transform!;
    const r = this.robotRadius();
    this.entities.destroyChildren();

    for (const objective of view.objectives) {
      const s = t.toScreen(objective.position);
      this.entities.add(
        new Konva.Star({ ...s, numPoints: 5, innerRadius: 5, outerRadius: 11, fill: COLORS.objective }),
        new Konva.Text({ x: s.x + 12, y: s.y - 6, text: objective.label, fontSize: 11, fill: COLORS.objective }),
      );
    }

    for (const enemy of view.enemies) {
      const s = t.toScreen(enemy.position);
      this.entities.add(
        new Konva.Circle({ ...s, radius: t.length(ENEMY_RADIUS_M), fill: COLORS.enemy, opacity: 0.12 }),
        new Konva.RegularPolygon({ ...s, sides: 3, radius: r + 2, fill: COLORS.enemy, stroke: "#000", strokeWidth: 1 }),
      );
    }

    const rings = robotConstraintRings(view);
    const pulse = 0.5 + 0.5 * Math.sin(Date.now() / 120);
    for (const agent of view.agent_states) {
      const s = t.toScreen(agent.position);
      const isSelected = selected.has(agent.id);
      const group = new Konva.Group({ x: s.x, y: s.y });

      if (offending.has(agent.id)) {
        group.add(new Konva.Circle({ radius: r + 9, stroke: COLORS.violation, strokeWidth: 3, opacity: 0.4 + 0.6 * pulse }));
      }
      (rings.get(agent.id) ?? []).forEach((ring, index) => {
        group.add(
          new Konva.Arc({
            innerRadius: r + 10 + index * 4,
            outerRadius: r + 12 + index * 4,
            angle: 360 * Math.max(Math.min(ring.fraction, 1), 0),
            rotation: -90,
            fill: ring.color,
          }),
        );
      });
      group.add(
        new Konva.Arc({
          innerRadius: r + 1,
          outerRadius: r + 4,
          angle: 360 * agent.health,
          rotation: -90,
          fill: healthColor(agent.health),
        }),
      );
      if (agent.action_duration > 0 && agent.action_time_remaining < agent.action_duration) {
        group.add(
          new Konva.Arc({
            innerRadius: r + 5,
            outerRadius: r + 7,
            angle: 360 * (1 - agent.action_time_remaining / agent.action_duration),
            rotation: -90,
            fill: "#e5e7eb",
          }),
        );
      }
      group.add(
        new Konva.Circle({
          radius: r,
          fill: agent.failure ? COLORS.disabled : roleColor(agent.role),
          stroke: isSelected ? COLORS.selected : "#0b1220",
          strokeWidth: isSelected ? 3 : 1.5,
        }),
        new Konva.Text({
          x: -r,
          y: -6,
          width: 2 * r,
          align: "center",
          text: agent.failure ? "✕" : String(agent.id),
          fontSize: 11,
          fontStyle: "bold",
          fill: "#0b1220",
        }),
      );
      if (agent.carrying) {
        group.add(new Konva.Circle({ x: r * 0.8, y: -r * 0.8, radius: 4, fill: ITEM_COLORS[agent.carrying] ?? "#fff", stroke: "#000", strokeWidth: 1 }));
      }
      if (offending.has(agent.id)) {
        group.add(
          new Konva.Circle({ x: -r * 0.9, y: -r * 0.9, radius: 6, fill: COLORS.violation }),
          new Konva.Text({ x: -r * 0.9 - 3, y: -r * 0.9 - 5, text: "!", fontSize: 11, fontStyle: "bold", fill: "#fff" }),
        );
      }
      this.entities.add(group);
    }
    this.entities.draw();
  }

  private drawOverlay() {
    const t = this.transform;
    this.interaction.destroyChildren();
    if (!t) return;
    const { selectionBox, path, previews } = this.overlay;
    if (selectionBox) {
      const [a, b] = selectionBox;
      this.interaction.add(
        new Konva.Rect({
          x: Math.min(a.x, b.x),
          y: Math.min(a.y, b.y),
          width: Math.abs(a.x - b.x),
          height: Math.abs(a.y - b.y),
          fill: "rgba(147,197,253,0.12)",
          stroke: "#93c5fd",
          dash: [4, 3],
        }),
      );
    }
    for (const preview of previews ?? []) {
      const a = t.toScreen(preview.from);
      const b = t.toScreen(preview.to);
      this.interaction.add(
        new Konva.Arrow({
          points: [a.x, a.y, b.x, b.y],
          stroke: preview.bad ? COLORS.pathBad : COLORS.path,
          fill: preview.bad ? COLORS.pathBad : COLORS.path,
          strokeWidth: 1.5,
          pointerLength: 7,
          pointerWidth: 6,
          dash: [5, 4],
        }),
      );
    }
    if (path && path.points.length > 1) {
      this.interaction.add(
        new Konva.Line({
          points: path.points.flatMap((p) => {
            const s = t.toScreen(p);
            return [s.x, s.y];
          }),
          stroke: path.bad ? COLORS.pathBad : "#e0f2fe",
          strokeWidth: 2.5,
          lineCap: "round",
          lineJoin: "round",
        }),
      );
    }
    this.interaction.draw();
  }
}
