import { CommandBar } from "./panels/CommandBar";
import { CommandQueuePanel } from "./panels/CommandQueuePanel";
import { ConstraintBanner } from "./panels/ConstraintBanner";
import { ConstraintPanel } from "./panels/ConstraintPanel";
import { MapPanel } from "./panels/MapPanel";
import { RobotList } from "./panels/RobotList";
import { SelectionPanel } from "./panels/SelectionPanel";
import { StatusBar } from "./panels/StatusBar";
import { StrategyPanel } from "./panels/StrategyPanel";
import { VideoPanel } from "./panels/VideoPanel";
import { ViolationFlash } from "./panels/ViolationFlash";
import { connected, mode } from "./state/store";

export function App() {
  const llmMode = mode.value === "llm";
  return (
    <div class="app">
      <StatusBar />
      <aside class="left">
        <RobotList />
        {llmMode && <CommandQueuePanel />}
      </aside>
      <main class="center">
        {!llmMode && <CommandBar />}
        <MapPanel />
        <ConstraintBanner />
        {!connected.value && (
          <div class="disconnected">
            <strong>Connection to the game server lost</strong>
            <span class="small">Reconnecting… Commands cannot be sent until the connection is back.</span>
          </div>
        )}
      </main>
      <aside class="right">
        <VideoPanel />
        {llmMode && <StrategyPanel />}
        <SelectionPanel />
        <ConstraintPanel />
      </aside>
      <ViolationFlash />
    </div>
  );
}
