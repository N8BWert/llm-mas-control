// Global UI state as signals. Components read these directly; only
// api/socket.ts writes the server-driven ones.

import { computed, signal } from "@preact/signals";
import {
  ConstraintState,
  type Agent,
  type AppConfig,
  type ConstraintStatus,
  type GameView,
  type LlmSnapshot,
  type Mode,
  type QueueSnapshot,
} from "../types";

export type Tool = "select" | "move" | "path" | { action: string };

const urlMode = new URLSearchParams(location.search).get("mode");

export const config = signal<AppConfig | null>(null);
export const mode = signal<Mode>(urlMode === "llm" ? "llm" : "rts");
export const hasUrlMode = urlMode === "llm" || urlMode === "rts";

export const connected = signal(false);
export const game = signal<GameView | null>(null);
export const queue = signal<QueueSnapshot>({ in_progress: [], waiting: [], history: [] });
export const llm = signal<LlmSnapshot | null>(null);
export interface Notice {
  id: number;
  text: string;
  kind: "violation" | "warning" | "error";
}

export const notices = signal<Notice[]>([]);
let nextNoticeId = 0;

export function notify(text: string, kind: Notice["kind"] = "warning", ms = 4000) {
  const id = nextNoticeId++;
  notices.value = [...notices.value, { id, text, kind }];
  setTimeout(() => (notices.value = notices.value.filter((n) => n.id !== id)), ms);
}

export const selection = signal<ReadonlySet<number>>(new Set());
export const tool = signal<Tool>("select");

export const statusById = computed(() => {
  const map = new Map<string, ConstraintStatus>();
  for (const status of game.value?.constraint_statuses ?? []) map.set(status.constraint_id, status);
  return map;
});

export const offendingRobots = computed(() => {
  const ids = new Set<number>();
  for (const status of game.value?.constraint_statuses ?? []) {
    if (status.state === ConstraintState.VIOLATED) status.offending_robot_ids.forEach((id) => ids.add(id));
  }
  return ids;
});

export const totalViolations = computed(() =>
  (game.value?.constraint_statuses ?? []).reduce((sum, s) => sum + s.violation_count, 0),
);

export const selectedAgents = computed(() =>
  (game.value?.agent_states ?? []).filter((agent) => selection.value.has(agent.id)),
);

// Robots among `agents` whose role an active role restriction forbids from `action`.
export function disallowedFor(view: GameView | null, action: string, agents: Agent[]): Agent[] {
  const rules = (view?.active_constraints ?? [])
    .map((c) => c.role_restriction)
    .filter((r) => r?.action_kinds.includes(action));
  return agents.filter((agent) => rules.some((r) => !r!.allowed_roles.includes(agent.role)));
}
