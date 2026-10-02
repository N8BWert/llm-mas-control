import type { Agent, Command } from "../types";

export function formatTime(seconds: number): string {
  const s = Math.max(Math.ceil(seconds), 0);
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

export function actionLabel(kind: string): string {
  return kind.replace(/_/g, " ");
}

export function describeCommand(command: Pick<Command, "kind" | "target">): string {
  const [a, b] = command.target;
  const where = command.kind === "move" ? `(${a.toFixed(2)}, ${b.toFixed(2)})` : `tile (${a}, ${b})`;
  return `${actionLabel(command.kind)} ${where}`;
}

export function agentStatus(agent: Agent): string {
  if (agent.failure) return agent.failure.toUpperCase();
  if (!agent.current_action) return "idle";
  const working = agent.action_duration > 0 && agent.action_time_remaining < agent.action_duration;
  const label = actionLabel(agent.current_action);
  if (working) return `${label} · ${Math.ceil(agent.action_time_remaining)}s left`;
  return agent.current_action === "move" ? "moving" : `→ ${label}`;
}
