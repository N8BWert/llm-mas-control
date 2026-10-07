// The single WebSocket to the backend. partysocket reconnects automatically,
// so the UI recovers if the backend restarts.

import ReconnectingWebSocket from "partysocket/ws";
import { batch } from "@preact/signals";
import type { ClientMessage, ServerMessage } from "../types";
import { config, connected, game, hasUrlMode, llm, mode, notify, queue, selection } from "../state/store";

let socket: ReconnectingWebSocket | null = null;

export function connect() {
  const protocol = location.protocol === "https:" ? "wss" : "ws";
  socket = new ReconnectingWebSocket(`${protocol}://${location.host}/ws`);
  socket.addEventListener("open", () => (connected.value = true));
  socket.addEventListener("close", () => (connected.value = false));
  socket.addEventListener("message", (event) => handle(JSON.parse(event.data as string) as ServerMessage));

  fetch("/api/config")
    .then((response) => response.json())
    .then((data) => {
      config.value = data;
      if (!hasUrlMode) mode.value = data.mode;
    })
    .catch(() => undefined);
}

function handle(message: ServerMessage) {
  switch (message.type) {
    case "state":
      batch(() => {
        game.value = message.data;
        pruneSelection();
      });
      break;
    case "queue":
      queue.value = message.data;
      break;
    case "llm":
      llm.value = message.data;
      break;
    case "error":
      notify(message.data.message, "error", 6000);
      break;
  }
}

// Disabled robots can't take commands, so drop them from the selection.
function pruneSelection() {
  const usable = new Set((game.value?.agent_states ?? []).filter((a) => !a.failure).map((a) => a.id));
  const sel = selection.value;
  if ([...sel].some((id) => !usable.has(id))) {
    selection.value = new Set([...sel].filter((id) => usable.has(id)));
  }
}

export function send(message: ClientMessage) {
  socket?.send(JSON.stringify(message));
}

export const api = {
  command(robotIds: Iterable<number>, kind: string, target: [number, number], append = false) {
    const robot_ids = [...robotIds];
    if (robot_ids.length) send({ type: "command", robot_ids, action: { kind, target }, append });
  },
  emergency(kind: "stop" | "retreat") {
    send({ type: "emergency", kind });
  },
  strategy(text: string) {
    send({ type: "strategy", text });
  },
  clear(robotIds?: Iterable<number>) {
    send({ type: "clear", robot_ids: robotIds ? [...robotIds] : undefined });
  },
  async restart() {
    await fetch("/api/restart", { method: "POST" });
  },
};
