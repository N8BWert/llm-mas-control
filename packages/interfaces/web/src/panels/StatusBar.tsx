import { api } from "../api/socket";
import { config, connected, game, mode, totalViolations } from "../state/store";
import { EmergencyControls } from "./EmergencyControls";
import { formatTime } from "./format";

export function StatusBar() {
  const view = game.value;
  const lowTime = view && view.time_remaining < 20 && !view.game_over;
  return (
    <header class="status-bar">
      <span class={`dot ${connected.value ? "on" : "off"}`} title={connected.value ? "Connected" : "Disconnected"} />
      <strong class="mode">
        {mode.value === "rts" ? "RTS" : "LLM"}
        <span class="wide-only"> interface</span>
      </strong>
      {view ? (
        <>
          <span class="stat">
            Score <b>{view.points}</b>
          </span>
          <span class={`stat ${lowTime ? "warn" : ""}`}>
            Time <b>{view.game_over ? "0:00" : formatTime(view.time_remaining)}</b>
          </span>
          <span class="stat">
            Round <b>{view.round_index + 1}/{view.round_count}</b> <span class="wide-only">{view.round_name}</span>
          </span>
          <span class="stat">
            Violations <b class={totalViolations.value ? "bad" : ""}>{totalViolations.value}</b>
          </span>
          {view.game_over && <span class="badge bad">Game over</span>}
        </>
      ) : (
        <span class="muted">Waiting for game state…</span>
      )}
      <span class="spacer" />
      {config.value?.engine === "dummy" && (
        <button
          class="secondary outline small"
          onClick={() => confirm("Restart the game from round 1?") && api.restart()}
        >
          Restart
        </button>
      )}
      <EmergencyControls />
    </header>
  );
}
