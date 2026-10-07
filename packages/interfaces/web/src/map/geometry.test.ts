import { describe, expect, it } from "vitest";
import type { GameView } from "../types";
import { WorldTransform, pathCrossesZones, tileAt, tileCenter, tileStateAt } from "./geometry";

const arena = { x_min: -1.6, y_min: -1, x_max: 1.6, y_max: 1 };
const view = { arena, width: 32, height: 20, tiles: Array(640).fill(0) } as unknown as GameView;

describe("WorldTransform", () => {
  it("round-trips points and flips y", () => {
    const t = new WorldTransform(arena, 800, 500);
    const top = t.toScreen({ x: 0, y: 1 });
    const bottom = t.toScreen({ x: 0, y: -1 });
    expect(top.y).toBeLessThan(bottom.y);
    const back = t.toWorld(t.toScreen({ x: 0.3, y: -0.7 }));
    expect(back.x).toBeCloseTo(0.3);
    expect(back.y).toBeCloseTo(-0.7);
  });
});

describe("tiles", () => {
  it("maps points to tiles and back", () => {
    expect(tileAt(view, { x: -1.55, y: -0.95 })).toEqual([0, 0]);
    expect(tileAt(view, { x: 2, y: 0 })).toBeNull();
    const c = tileCenter(view, 26, 15);
    expect(tileAt(view, c)).toEqual([26, 15]);
  });

  it("reads tile state row-major over (width, height)", () => {
    const tiles = Array(640).fill(0);
    tiles[3 * 20 + 7] = 5;
    expect(tileStateAt({ ...view, tiles } as GameView, 3, 7)).toBe(5);
  });
});

describe("pathCrossesZones", () => {
  const rect = { rect: { x_min: -0.2, y_min: -0.2, x_max: 0.2, y_max: 0.2 } };
  const circle = { circle: { x: 1, y: 0, radius: 0.1 } };

  it("detects segments crossing a rectangle without an endpoint inside", () => {
    expect(pathCrossesZones([{ x: -1, y: 0 }, { x: 1, y: 0 }], [rect])).toBe(true);
    expect(pathCrossesZones([{ x: -1, y: 0.5 }, { x: 1, y: 0.5 }], [rect])).toBe(false);
  });

  it("detects segments passing through a circle", () => {
    expect(pathCrossesZones([{ x: 1, y: -1 }, { x: 1, y: 1 }], [circle])).toBe(true);
    expect(pathCrossesZones([{ x: 0.5, y: -1 }, { x: 0.5, y: 1 }], [circle])).toBe(false);
  });

  it("checks a single point for containment", () => {
    expect(pathCrossesZones([{ x: 0, y: 0 }], [rect])).toBe(true);
  });
});
