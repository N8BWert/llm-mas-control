import { clickSelect } from "../map/selection";
import { game, offendingRobots, selection } from "../state/store";
import { ITEM_COLORS, healthColor, roleColor } from "../theme";
import { agentStatus, describeCommand } from "./format";

export function RobotList() {
  const agents = game.value?.agent_states ?? [];
  return (
    <section class="panel robot-list">
      <h3>Robots</h3>
      <ul>
        {agents.map((agent) => {
          const next = agent.plan.find((c) => c.status === "waiting");
          const selected = selection.value.has(agent.id);
          const violating = offendingRobots.value.has(agent.id);
          return (
            <li
              key={agent.id}
              class={`${selected ? "selected" : ""} ${agent.failure ? "failed" : ""} ${violating ? "violating" : ""}`}
              onClick={(e) => {
                if (!agent.failure) selection.value = clickSelect(selection.value, agent.id, e.shiftKey || e.ctrlKey || e.metaKey);
              }}
            >
              <span class="swatch" style={{ background: agent.failure ? "#4b5563" : roleColor(agent.role) }}>
                {agent.id}
              </span>
              <div class="robot-info">
                <div class="robot-line">
                  <span class="role">{agent.role || "robot"}</span>
                  {agent.carrying && (
                    <span class="item" style={{ color: ITEM_COLORS[agent.carrying] }}>
                      ● {agent.carrying}
                    </span>
                  )}
                  {violating && <span class="badge bad">violation</span>}
                </div>
                <div class={`robot-status ${agent.failure ? "bad" : ""}`}>{agentStatus(agent)}</div>
                {next && <div class="muted small">then {describeCommand(next)}</div>}
                <div class="health" title={`Health ${Math.round(agent.health * 100)}%`}>
                  <div style={{ width: `${agent.health * 100}%`, background: healthColor(agent.health) }} />
                </div>
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
