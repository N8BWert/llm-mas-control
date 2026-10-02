import { disallowedFor, game, selectedAgents, selection, tool, type Tool } from "../state/store";
import { actionLabel } from "./format";

const BASE_TOOLS: { tool: Tool; label: string; key: string }[] = [
  { tool: "select", label: "Select", key: "Esc" },
  { tool: "move", label: "Waypoint", key: "W" },
  { tool: "path", label: "Draw path", key: "P" },
];

export const ACTION_TOOLS = ["mine", "farm", "pick_up", "drop", "build_farm", "build_quarry", "build_house"];

function isActive(t: Tool): boolean {
  const current = tool.value;
  if (typeof t === "object" && typeof current === "object") return t.action === current.action;
  return t === current;
}

export function CommandBar() {
  const hasSelection = selection.value.size > 0;
  return (
    <div class="command-bar">
      {BASE_TOOLS.map(({ tool: t, label, key }) => (
        <button key={label} class={`tool ${isActive(t) ? "active" : ""}`} onClick={() => (tool.value = t)} title={key}>
          {label} <kbd>{key}</kbd>
        </button>
      ))}
      <span class="divider" />
      {ACTION_TOOLS.map((action, index) => {
        const blocked = disallowedFor(game.value, action, selectedAgents.value);
        const title = blocked.length
          ? `Role restriction: robot(s) ${blocked.map((a) => a.id).join(", ")} may not ${actionLabel(action)}`
          : `${actionLabel(action)} (${index + 1})`;
        return (
          <button
            key={action}
            class={`tool ${isActive({ action }) ? "active" : ""} ${blocked.length ? "restricted" : ""}`}
            onClick={() => (tool.value = { action })}
            title={title}
          >
            {actionLabel(action)} <kbd>{index + 1}</kbd>
          </button>
        );
      })}
      <span class="hint">
        {hasSelection
          ? "Right-click: smart command · Shift: add to queue"
          : "Select robots to give commands"}
      </span>
    </div>
  );
}
