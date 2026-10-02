import { useEffect, useRef, useState } from "preact/hooks";
import { game, notices, notify } from "../state/store";

const FLASH_MS = 900;

// Flashes the screen edge whenever a new violation is counted, and shows all
// notices (violations, warnings, server errors) as toasts.
export function ViolationFlash() {
  const previous = useRef<Map<string, number> | null>(null);
  const [flash, setFlash] = useState(0);
  const view = game.value;
  const key = (view?.constraint_statuses ?? []).map((s) => `${s.constraint_id}:${s.violation_count}`).join("|");

  useEffect(() => {
    if (!view) return;
    const counts = new Map(view.constraint_statuses.map((s) => [s.constraint_id, s.violation_count]));
    let fresh = false;
    if (previous.current) {
      for (const status of view.constraint_statuses) {
        const added = status.violation_count - (previous.current.get(status.constraint_id) ?? 0);
        if (added > 0) {
          const constraint = view.active_constraints.find((c) => c.id === status.constraint_id);
          notify(`Violation: ${constraint?.label ?? status.constraint_id} (−${(constraint?.penalty ?? 0) * added} pts)`, "violation");
          fresh = true;
        }
      }
    }
    previous.current = counts;
    if (fresh) setFlash((n) => n + 1);
  }, [key]);

  useEffect(() => {
    if (!flash) return;
    const timer = setTimeout(() => setFlash(0), FLASH_MS);
    return () => clearTimeout(timer);
  }, [flash]);

  return (
    <>
      {flash > 0 && <div class="violation-flash" key={flash} />}
      <div class="toasts">
        {notices.value.map((notice) => (
          <div class={`toast ${notice.kind}`} key={notice.id}>
            {notice.text}
          </div>
        ))}
      </div>
    </>
  );
}
