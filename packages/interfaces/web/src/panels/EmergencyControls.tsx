import { api } from "../api/socket";

export function EmergencyControls() {
  return (
    <div class="emergency">
      <button class="danger" title="Stop all robots (X)" onClick={() => api.emergency("stop")}>
        ■ Stop all
      </button>
      <button class="warning" title="All robots return to the castle (R)" onClick={() => api.emergency("retreat")}>
        ⟲ Retreat
      </button>
    </div>
  );
}
