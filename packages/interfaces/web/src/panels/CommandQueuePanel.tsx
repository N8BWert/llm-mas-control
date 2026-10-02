import { queue, selection } from "../state/store";
import type { Command } from "../types";
import { describeCommand } from "./format";

const HISTORY_SHOWN = 8;

function CommandRow({ command }: { command: Command }) {
  return (
    <li class={`queue-row status-${command.status}`} onClick={() => (selection.value = new Set([command.robot_id]))}>
      <span class="robot-tag">{command.robot_id}</span>
      <span class="queue-text">{describeCommand(command)}</span>
      <span class={`chip source-${command.source}`}>{command.source}</span>
    </li>
  );
}

function Section({ title, commands }: { title: string; commands: Command[] }) {
  return (
    <>
      <div class="queue-heading small">
        {title} <span class="muted">{commands.length}</span>
      </div>
      {commands.length === 0 ? (
        <p class="muted tiny">None</p>
      ) : (
        <ul class="queue-list">
          {commands.map((c) => (
            <CommandRow key={c.id} command={c} />
          ))}
        </ul>
      )}
    </>
  );
}

export function CommandQueuePanel() {
  const { in_progress, waiting, history } = queue.value;
  return (
    <section class="panel command-queue">
      <h3>Command queue</h3>
      <Section title="In progress" commands={in_progress} />
      <Section title="Waiting" commands={waiting} />
      <Section title="Recent" commands={history.slice(-HISTORY_SHOWN).reverse()} />
    </section>
  );
}
