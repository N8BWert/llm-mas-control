import { useEffect, useRef, useState } from "preact/hooks";
import { game } from "../state/store";

const BANNER_MS = 8000;

interface Banner {
  id: number;
  title: string;
  text: string;
}

// Announces new rounds and constraints that become active, so rule changes are never silent.
export function ConstraintBanner() {
  const view = game.value;
  const seen = useRef<Set<string> | null>(null);
  const round = useRef<number | null>(null);
  const nextId = useRef(0);
  const [banners, setBanners] = useState<Banner[]>([]);
  const ids = (view?.active_constraints ?? []).map((c) => c.id).join("|");

  useEffect(() => {
    if (!view) return;
    const fresh: Banner[] = [];
    if (round.current !== null && round.current !== view.round_index) {
      fresh.push({ id: nextId.current++, title: `Round ${view.round_index + 1}: ${view.round_name}`, text: "A new round has started." });
    }
    round.current = view.round_index;
    if (seen.current) {
      for (const constraint of view.active_constraints) {
        if (!seen.current.has(constraint.id)) {
          fresh.push({ id: nextId.current++, title: `New constraint: ${constraint.label}`, text: constraint.description });
        }
      }
    }
    seen.current = new Set(view.active_constraints.map((c) => c.id));
    if (!fresh.length) return;
    setBanners((b) => [...b, ...fresh]);
    const freshIds = new Set(fresh.map((b) => b.id));
    setTimeout(() => setBanners((b) => b.filter((banner) => !freshIds.has(banner.id))), BANNER_MS);
  }, [ids, view?.round_index]);

  if (!banners.length) return null;
  return (
    <div class="banners">
      {banners.map((banner) => (
        <div class="banner" key={banner.id} onClick={() => setBanners((b) => b.filter((x) => x.id !== banner.id))}>
          <strong>{banner.title}</strong>
          <div class="small">{banner.text}</div>
        </div>
      ))}
    </div>
  );
}
