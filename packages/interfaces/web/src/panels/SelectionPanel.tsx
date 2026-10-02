import { api } from "../api/socket";
import { mode, selectedAgents, selection } from "../state/store";
import { describeCommand } from "./format";

export function SelectionPanel() {
  const agents = selectedAgents.value;
  const roles = new Map<string, number>();
  agents.forEach((a) => roles.set(a.role || "robot", (roles.get(a.role || "robot") ?? 0) + 1));
  const objectives = new Map<string, number>();
  agents.forEach((a) =>
    a.plan.forEach((c) => objectives.set(describeCommand(c), (objectives.get(describeCommand(c)) ?? 0) + 1)),
  );

  return (
    <section class="panel selection">
      <h3>
        Selected <span class="count">{agents.length}</span>
      </h3>
      {agents.length === 0 ? (
        <p class="muted small">Click, shift/ctrl-click or drag a box on the map to select robots.</p>
      ) : (
        <>
          <p class="small">
            {[...roles].map(([role, n]) => (
              <span class="chip" key={role}>
                {n} {role}
              </span>
            ))}
          </p>
          <div class="small">Objectives:</div>
          {objectives.size === 0 ? (
            <p class="muted small">None. Selected robots are idle.</p>
          ) : (
            <ul class="objectives small">
              {[...objectives].map(([text, n]) => (
                <li key={text}>
                  {text} <span class="muted">×{n}</span>
                </li>
              ))}
            </ul>
          )}
          <div class="row">
            {mode.value === "rts" && (
              <button class="secondary outline small" onClick={() => api.clear(selection.value)}>
                Clear commands
              </button>
            )}
            <button class="secondary outline small" onClick={() => (selection.value = new Set())}>
              Deselect
            </button>
          </div>
        </>
      )}
    </section>
  );
}
