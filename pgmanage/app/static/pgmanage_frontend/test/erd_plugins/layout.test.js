import { describe, it, expect } from "vitest";
import { getLayoutedNodes } from "@src/erd_plugins/layout";

describe("getLayoutedNodes", () => {
  const tables = ["a", "b", "c", "d", "e", "f", "g"].map((id) => ({
    id,
    type: "table",
    position: { x: 0, y: 0 },
  }));
  const internal = tables.map((table, i) => ({
    id: table.id,
    type: "table",
    dimensions: { width: 301 + i, height: 197 + i * 3 },
  }));

  it("places every table on the 10px grid, independently of vue-flow's snapping", () => {
    const laid = getLayoutedNodes(tables, internal);

    laid.forEach((node) => {
      expect(node.position.x % 10).toBe(0);
      expect(node.position.y % 10).toBe(0);
    });
  });

  it("leaves non-table nodes alone", () => {
    const column = { id: "c1", type: "column", position: { x: 0, y: 47 } };
    const laid = getLayoutedNodes([...tables, column], [...internal]);

    expect(laid.find((node) => node.id === "c1")).toBe(column);
  });
});
