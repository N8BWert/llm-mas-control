import { effect } from "@preact/signals";
import { useEffect, useRef } from "preact/hooks";
import { MapView } from "../map/MapView";
import { attachTools } from "../map/tools";
import { game, offendingRobots, selection } from "../state/store";

export function MapPanel() {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const map = new MapView(ref.current!);
    const detachTools = attachTools(map);
    const stopRendering = effect(() => {
      const view = game.value;
      if (view) map.render({ view, selected: selection.value, offending: offendingRobots.value });
    });
    return () => {
      stopRendering();
      detachTools();
      map.destroy();
    };
  }, []);

  return <div class="map" ref={ref} />;
}
