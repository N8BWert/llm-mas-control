import { useSignal } from "@preact/signals";
import { api } from "../api/socket";
import { llm } from "../state/store";
import type { LlmLogEntry } from "../types";

const STATUS_LABEL = { idle: "Idle", planning: "Planning…", error: "Error", paused: "Paused" };
const LOG_LABEL: Record<LlmLogEntry["role"], string> = {
  operator: "You",
  llm: "LLM",
  action: "Command",
  error: "Rejected",
  system: "System",
};

export function StrategyPanel() {
  const draft = useSignal("");
  const snapshot = llm.value;

  const submit = (event?: Event) => {
    event?.preventDefault();
    const text = draft.value.trim();
    if (!text) return;
    api.strategy(text);
    draft.value = "";
  };

  return (
    <section class="panel strategy">
      <h3>
        Strategy
        {snapshot && <span class={`chip llm-${snapshot.status}`}>{STATUS_LABEL[snapshot.status]}</span>}
      </h3>
      <form onSubmit={submit}>
        <textarea
          rows={3}
          placeholder="Tell the robots what to do, e.g. “Two robots mine stone, the rest guard the supply drop.”"
          value={draft.value}
          onInput={(e) => (draft.value = e.currentTarget.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) submit(e);
          }}
        />
        <button type="submit" class="small" disabled={!draft.value.trim()}>
          Send strategy <kbd>⌘↵</kbd>
        </button>
      </form>
      {snapshot?.strategy && (
        <p class="small">
          <span class="muted">Current: </span>
          {snapshot.strategy}
        </p>
      )}
      {snapshot?.paused && <p class="small warn">Planning paused. Send a strategy to resume.</p>}
      {snapshot?.error && <p class="small bad">{snapshot.error}</p>}
      <ul class="llm-log small">
        {[...(snapshot?.log ?? [])].reverse().map((entry, index) => (
          <li key={`${entry.t}-${index}`} class={`log-${entry.role}`}>
            <span class="log-role">{LOG_LABEL[entry.role]}</span> {entry.text}
          </li>
        ))}
      </ul>
      {snapshot && <p class="muted tiny">Model: {snapshot.model}</p>}
    </section>
  );
}
