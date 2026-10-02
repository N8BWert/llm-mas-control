import { game, statusById } from "../state/store";
import { ConstraintState, type Constraint, type ConstraintStatus } from "../types";

const STATE_LABEL = ["OK", "Warning", "Violated"];
const STATE_CLASS = ["ok", "warn", "bad"];
const TIMERS_SHOWN = 3;

function details(constraint: Constraint, status: ConstraintStatus | undefined, elapsed: number) {
  const lines: string[] = [];
  if (constraint.occupation_zone && status) {
    const min = constraint.occupation_zone.min_robots;
    lines.push(`Robots in zone: ${status.zone_counts.map((n) => `${n}/${min}`).join(", ")}`);
    const graceLeft = constraint.active_from_s + constraint.occupation_zone.grace_s - elapsed;
    if (graceLeft > 0) lines.push(`Grace period: ${Math.ceil(graceLeft)}s to get in position`);
  }
  const limit = constraint.activity_interval?.max_active_s ?? Infinity;
  const timers = Object.entries(status?.timers ?? {})
    .filter(([, s]) => s < limit)
    .sort((a, b) => a[1] - b[1]);
  if (timers.length) {
    const label = constraint.activity_interval ? "until refuel" : "time left inside";
    const shown = timers.slice(0, TIMERS_SHOWN).map(([id, s]) => `Robot ${id}: ${Math.ceil(s)}s ${label}`);
    lines.push(shown.join(" · ") + (timers.length > TIMERS_SHOWN ? " …" : ""));
  }
  if (constraint.role_restriction) {
    const allowed = new Set(constraint.role_restriction.allowed_roles);
    const others = (game.value?.agent_states ?? []).filter((a) => !a.failure && !allowed.has(a.role));
    if (others.length) lines.push(`Not allowed: robot ${others.map((a) => a.id).join(", ")}`);
  }
  if (status?.offending_robot_ids.length) {
    lines.push(`In violation: robot ${status.offending_robot_ids.join(", ")}`);
  }
  if (constraint.active_until_s > 0) {
    lines.push(`Ends in ${Math.max(Math.ceil(constraint.active_until_s - elapsed), 0)}s`);
  }
  return lines;
}

export function ConstraintPanel() {
  const view = game.value;
  const constraints = view?.active_constraints ?? [];
  return (
    <section class="panel constraints">
      <h3>Constraints</h3>
      {constraints.length === 0 && <p class="muted small">No active constraints.</p>}
      {constraints.map((constraint) => {
        const status = statusById.value.get(constraint.id);
        const state = status?.state ?? ConstraintState.OK;
        return (
          <article key={constraint.id} class={`constraint ${STATE_CLASS[state]}`}>
            <div class="constraint-head">
              <strong>{constraint.label}</strong>
              <span class="chip">{constraint.difficulty}</span>
              <span class={`badge ${STATE_CLASS[state]}`}>{STATE_LABEL[state]}</span>
            </div>
            <p class="small">{constraint.description}</p>
            {details(constraint, status, view!.elapsed_s).map((line) => (
              <div class="small" key={line}>
                {line}
              </div>
            ))}
            <div class="small muted">
              {status?.violation_count ?? 0} violation(s) · −{status?.points_lost ?? 0} pts · {constraint.penalty} pts each
            </div>
          </article>
        );
      })}
    </section>
  );
}
