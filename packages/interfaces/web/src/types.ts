// Mirrors the backend wire format: GameState proto (via json_format with
// snake_case names) plus the command queue and LLM snapshots.

export interface Vec {
  x: number;
  y: number;
}

export type CommandStatus = "waiting" | "in_progress" | "done" | "cancelled";

export interface Command {
  id: number;
  robot_id: number;
  kind: string;
  target: [number, number];
  source: "user" | "llm" | "emergency";
  status: CommandStatus;
  created_at: number;
  started_at: number | null;
  finished_at: number | null;
}

export interface Agent {
  id: number;
  position: Vec;
  busy: boolean;
  role: string;
  health: number;
  current_action: string;
  action_time_remaining: number;
  action_duration: number;
  target?: Vec;
  has_target: boolean;
  failure: string;
  carrying: string;
  plan: Command[];
}

export interface Rect {
  x_min: number;
  y_min: number;
  x_max: number;
  y_max: number;
}

export interface Circle {
  x: number;
  y: number;
  radius: number;
}

export interface Zone {
  rect?: Rect;
  circle?: Circle;
}

export interface Entity {
  id: number;
  kind: string;
  position: Vec;
  label: string;
}

export interface Constraint {
  id: string;
  label: string;
  description: string;
  difficulty: string;
  penalty: number;
  active_from_s: number;
  active_until_s: number;
  restricted_zone?: { zones: Zone[] };
  occupation_zone?: { zones: Zone[]; min_robots: number; grace_s: number };
  timed_entry_zone?: { zones: Zone[]; max_dwell_s: number };
  activity_interval?: { max_active_s: number; base_zone?: Zone };
  role_restriction?: { action_kinds: string[]; allowed_roles: string[] };
}

export const ConstraintState = { OK: 0, WARNING: 1, VIOLATED: 2 } as const;
export type ConstraintStateValue = (typeof ConstraintState)[keyof typeof ConstraintState];

export interface ConstraintStatus {
  constraint_id: string;
  state: ConstraintStateValue;
  offending_robot_ids: number[];
  timers: Record<string, number>;
  violation_count: number;
  points_lost: number;
  zone_counts: number[];
}

export interface GameView {
  points: number;
  agent_states: Agent[];
  tiles: number[];
  width: number;
  height: number;
  time_remaining: number;
  elapsed_s: number;
  round_index: number;
  round_count: number;
  round_name: string;
  game_over: boolean;
  arena: Rect;
  enemies: Entity[];
  objectives: Entity[];
  active_constraints: Constraint[];
  constraint_statuses: ConstraintStatus[];
}

export interface QueueSnapshot {
  in_progress: Command[];
  waiting: Command[];
  history: Command[];
}

export interface LlmLogEntry {
  t: number;
  role: "operator" | "llm" | "action" | "error" | "system";
  text: string;
}

export interface LlmSnapshot {
  model: string;
  strategy: string;
  paused: boolean;
  status: "idle" | "planning" | "error" | "paused";
  error: string;
  log: LlmLogEntry[];
}

export type Mode = "rts" | "llm";

export interface AppConfig {
  mode: Mode;
  engine: "dummy" | "socket";
  video_url: string;
  llm_model: string;
  action_kinds: string[];
}

export type ServerMessage =
  | { type: "state"; data: GameView }
  | { type: "queue"; data: QueueSnapshot }
  | { type: "llm"; data: LlmSnapshot }
  | { type: "error"; data: { message: string } };

export type ClientMessage =
  | { type: "command"; robot_ids: number[]; action: { kind: string; target: [number, number] }; append: boolean }
  | { type: "emergency"; kind: "stop" | "retreat" }
  | { type: "strategy"; text: string }
  | { type: "clear"; robot_ids?: number[] };

export const TileState = {
  EMPTY: 0,
  CASTLE: 1,
  FARM: 2,
  QUARRY: 3,
  WATER: 4,
  APPLE: 5,
  OBSCURED: 6,
} as const;

export type ConstraintKind =
  | "restricted_zone"
  | "occupation_zone"
  | "timed_entry_zone"
  | "activity_interval"
  | "role_restriction";

const KINDS: ConstraintKind[] = [
  "restricted_zone",
  "occupation_zone",
  "timed_entry_zone",
  "activity_interval",
  "role_restriction",
];

export function constraintKind(constraint: Constraint): ConstraintKind | undefined {
  return KINDS.find((kind) => constraint[kind] !== undefined);
}

export function constraintZones(constraint: Constraint): Zone[] {
  return (
    constraint.restricted_zone?.zones ??
    constraint.occupation_zone?.zones ??
    constraint.timed_entry_zone?.zones ??
    (constraint.activity_interval?.base_zone ? [constraint.activity_interval.base_zone] : [])
  );
}
