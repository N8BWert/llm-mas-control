// Map interaction controller. Selection works in both modes; commands only
// in RTS mode.
//
// Select tool: click / shift|ctrl-click / drag a box; click a selected robot to deselect.
// Move tool:   click to send selected robots to a waypoint (shift appends).
// Path tool:   drag to draw a path; robots follow it as a chain of waypoints.
// Action tool: click a tile to perform that action there (robots navigate themselves).
// Right-click: smart command for the clicked tile (quarry -> mine, castle -> drop, ...).

import { effect } from "@preact/signals";
import { api } from "../api/socket";
import { disallowedFor, game, mode, notify, selectedAgents, selection, tool } from "../state/store";
import { TileState, type GameView, type Vec } from "../types";
import { pathCrossesZones, restrictedZones, tileAt, tileCenter, tileStateAt } from "./geometry";
import type { MapView, Overlay } from "./MapView";
import { boxSelect, clickSelect, robotAt, robotsInBox } from "./selection";

const DRAG_PX = 5;
const PATH_STEP_M = 0.08;

const SMART_ACTIONS: Record<number, string> = {
  [TileState.QUARRY]: "mine",
  [TileState.FARM]: "farm",
  [TileState.APPLE]: "pick_up",
  [TileState.CASTLE]: "drop",
};

export function smartAction(view: GameView, world: Vec): { kind: string; target: [number, number] } {
  const tile = tileAt(view, world);
  const kind = tile ? SMART_ACTIONS[tileStateAt(view, tile[0], tile[1])] : undefined;
  return kind && tile ? { kind, target: tile } : { kind: "move", target: [world.x, world.y] };
}

const canCommand = () => mode.value === "rts" && selection.value.size > 0;

// Sends a command to the selection, warning if a role restriction forbids it for some robots.
function commandSelection(kind: string, target: [number, number], append: boolean) {
  const blocked = disallowedFor(game.value, kind, selectedAgents.value);
  if (blocked.length) {
    notify(`Role restriction: robot(s) ${blocked.map((a) => a.id).join(", ")} may not ${kind.replace(/_/g, " ")}`);
  }
  api.command(selection.value, kind, target, append);
}

export function attachTools(map: MapView): () => void {
  let downScreen: Vec | null = null;
  let downWorld: Vec | null = null;
  let currentScreen: Vec | null = null;
  let dragging = false;
  let drawing: Vec[] | null = null;
  let hover: Vec | null = null;

  function previewsTo(view: GameView, to: Vec): Overlay["previews"] {
    const zones = restrictedZones(view);
    return selectedAgents.value.map((agent) => ({
      from: agent.position,
      to,
      bad: pathCrossesZones([agent.position, to], zones),
    }));
  }

  function hoverTarget(view: GameView, at: Vec): Vec | null {
    const t = tool.value;
    if (t === "move") return at;
    if (typeof t === "object") {
      const tile = tileAt(view, at);
      return tile ? tileCenter(view, tile[0], tile[1]) : null;
    }
    return null;
  }

  function refreshOverlay() {
    const view = game.value;
    if (!view) return;
    const overlay: Overlay = {};
    if (dragging && downScreen && currentScreen) overlay.selectionBox = [downScreen, currentScreen];
    if (drawing) {
      const zones = restrictedZones(view);
      const lead = selectedAgents.value.some((a) => pathCrossesZones([a.position, drawing![0]], zones));
      overlay.path = { points: drawing, bad: lead || pathCrossesZones(drawing, zones) };
    } else if (hover && canCommand()) {
      const target = hoverTarget(view, hover);
      if (target) overlay.previews = previewsTo(view, target);
    }
    map.setOverlay(overlay);
  }

  function finishPath(append: boolean) {
    const points = drawing ?? [];
    points.forEach((p, index) => api.command(selection.value, "move", [p.x, p.y], append || index > 0));
  }

  function selectAt(world: Vec, additive: boolean) {
    const view = game.value;
    if (!view || !map.transform) return;
    const radius = (map.robotRadius() * 1.5) / map.transform.scale;
    selection.value = clickSelect(selection.value, robotAt(view.agent_states, world, radius), additive);
  }

  map.handlers = {
    down(p) {
      const view = game.value;
      if (!view) return;
      if (p.button === 2) {
        if (canCommand()) {
          const { kind, target } = smartAction(view, p.world);
          commandSelection(kind, target, p.shift);
        }
        return;
      }
      if (p.button !== 0) return;
      const t = tool.value;
      if (t === "select" || !canCommand()) {
        downScreen = currentScreen = p.screen;
        downWorld = p.world;
        dragging = false;
      } else if (t === "move") {
        api.command(selection.value, "move", [p.world.x, p.world.y], p.shift);
      } else if (t === "path") {
        drawing = [p.world];
      } else {
        const tile = tileAt(view, p.world);
        if (tile) commandSelection(t.action, tile, p.shift);
      }
    },
    move(p) {
      hover = p.world;
      currentScreen = p.screen;
      if (downScreen && Math.hypot(p.screen.x - downScreen.x, p.screen.y - downScreen.y) > DRAG_PX) dragging = true;
      if (drawing) {
        const last = drawing[drawing.length - 1];
        if (Math.hypot(p.world.x - last.x, p.world.y - last.y) >= PATH_STEP_M) drawing.push(p.world);
      }
      refreshOverlay();
    },
    up(p) {
      const view = game.value;
      if (drawing) {
        drawing.push(p.world);
        finishPath(p.shift);
        drawing = null;
      } else if (downScreen && downWorld && view) {
        if (dragging) {
          selection.value = boxSelect(selection.value, robotsInBox(view.agent_states, downWorld, p.world), p.additive);
        } else {
          selectAt(p.world, p.additive);
        }
      }
      downScreen = downWorld = null;
      dragging = false;
      refreshOverlay();
    },
    leave() {
      hover = null;
      refreshOverlay();
    },
  };

  const stopEffect = effect(() => {
    const t = tool.value;
    map.stage.container().style.cursor = t === "select" ? "default" : "crosshair";
    refreshOverlay();
  });

  return () => {
    stopEffect();
    map.handlers = {};
  };
}
