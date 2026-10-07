// Pure selection logic shared by the map and the robot list.

import type { Agent, Vec } from "../types";

// Clicking a selected robot deselects it; shift/ctrl adds to the selection;
// clicking empty space clears it (unless additive).
export function clickSelect(selection: ReadonlySet<number>, id: number | null, additive: boolean): Set<number> {
  if (id === null) return additive ? new Set(selection) : new Set();
  if (selection.has(id)) {
    const next = new Set(selection);
    next.delete(id);
    return next;
  }
  return additive ? new Set([...selection, id]) : new Set([id]);
}

export function boxSelect(selection: ReadonlySet<number>, ids: number[], additive: boolean): Set<number> {
  return additive ? new Set([...selection, ...ids]) : new Set(ids);
}

export function selectable(agents: Agent[]): Agent[] {
  return agents.filter((agent) => !agent.failure);
}

export function robotsInBox(agents: Agent[], a: Vec, b: Vec): number[] {
  const [x0, x1] = [Math.min(a.x, b.x), Math.max(a.x, b.x)];
  const [y0, y1] = [Math.min(a.y, b.y), Math.max(a.y, b.y)];
  return selectable(agents)
    .filter((agent) => agent.position.x >= x0 && agent.position.x <= x1 && agent.position.y >= y0 && agent.position.y <= y1)
    .map((agent) => agent.id);
}

export function robotAt(agents: Agent[], p: Vec, radius: number): number | null {
  let best: number | null = null;
  let bestDistance = radius;
  for (const agent of selectable(agents)) {
    const distance = Math.hypot(agent.position.x - p.x, agent.position.y - p.y);
    if (distance <= bestDistance) {
      best = agent.id;
      bestDistance = distance;
    }
  }
  return best;
}
