// Global keyboard shortcuts. tinykeys ignores key presses inside form fields,
// so typing a strategy never triggers them.

import { tinykeys } from "tinykeys";
import { api } from "./api/socket";
import { ACTION_TOOLS } from "./panels/CommandBar";
import { game, mode, selection, tool, type Tool } from "./state/store";
import { selectable } from "./map/selection";

function rtsTool(t: Tool) {
  return () => {
    if (mode.value === "rts") tool.value = t;
  };
}

export function bindHotkeys(): () => void {
  const actionKeys = Object.fromEntries(ACTION_TOOLS.map((action, i) => [String(i + 1), rtsTool({ action })]));
  return tinykeys(window, {
    Escape: () => {
      if (tool.value === "select") selection.value = new Set();
      else tool.value = "select";
    },
    w: rtsTool("move"),
    p: rtsTool("path"),
    ...actionKeys,
    "$mod+a": (event) => {
      event.preventDefault();
      selection.value = new Set(selectable(game.value?.agent_states ?? []).map((a) => a.id));
    },
    x: () => api.emergency("stop"),
    r: () => api.emergency("retreat"),
  });
}
