import { describe, expect, it } from "vitest";
import type { Agent } from "../types";
import { boxSelect, clickSelect, robotAt, robotsInBox } from "./selection";

const agent = (id: number, x: number, y: number, failure = "") => ({ id, position: { x, y }, failure }) as Agent;
const agents = [agent(0, 0, 0), agent(1, 0.5, 0.5), agent(2, 0.1, 0.1, "disabled")];

describe("clickSelect", () => {
  it("replaces the selection on a plain click", () => {
    expect([...clickSelect(new Set([1]), 0, false)]).toEqual([0]);
  });

  it("adds on an additive click", () => {
    expect([...clickSelect(new Set([1]), 0, true)].sort()).toEqual([0, 1]);
  });

  it("deselects a robot that is already selected", () => {
    expect([...clickSelect(new Set([0, 1]), 0, false)]).toEqual([1]);
  });

  it("clears on empty space unless additive", () => {
    expect(clickSelect(new Set([0]), null, false).size).toBe(0);
    expect(clickSelect(new Set([0]), null, true).size).toBe(1);
  });
});

describe("box and point picking", () => {
  it("selects robots inside the box regardless of drag direction, skipping failed robots", () => {
    expect(robotsInBox(agents, { x: 0.6, y: 0.6 }, { x: -0.1, y: -0.1 })).toEqual([0, 1]);
  });

  it("merges boxes when additive", () => {
    expect([...boxSelect(new Set([5]), [0], true)].sort()).toEqual([0, 5]);
    expect([...boxSelect(new Set([5]), [0], false)]).toEqual([0]);
  });

  it("picks the nearest selectable robot within the radius", () => {
    expect(robotAt(agents, { x: 0.08, y: 0.08 }, 0.2)).toBe(0);
    expect(robotAt(agents, { x: 1.5, y: 1.5 }, 0.2)).toBeNull();
  });
});
