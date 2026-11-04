import { describe, it, expect } from "vitest";
import ErdRelationEdge from "@src/erd_plugins/ErdRelationEdge.vue";

const scopeMarker = (ctx, marker) =>
  ErdRelationEdge.methods.scopeMarker.call(ctx, marker);

describe("ErdRelationEdge.scopeMarker", () => {
  it("scopes the marker id to the tab", () => {
    expect(scopeMarker({ tabId: "t1", selected: false }, "url(#erd-one-many)")).toBe(
      "url(#erd-one-many-t1)",
    );
  });

  it("uses the selected marker set when the edge is selected", () => {
    expect(scopeMarker({ tabId: "t1", selected: true }, "url(#erd-zero-one)")).toBe(
      "url(#erd-zero-one-selected-t1)",
    );
  });

  it("leaves the marker alone without a tab id", () => {
    expect(scopeMarker({ tabId: undefined, selected: true }, "url(#erd-one-only)")).toBe(
      "url(#erd-one-only)",
    );
  });

  it("passes non-string markers through", () => {
    const marker = { type: "arrow" };
    expect(scopeMarker({ tabId: "t1", selected: true }, marker)).toBe(marker);
    expect(scopeMarker({ tabId: "t1", selected: false }, undefined)).toBeUndefined();
  });

  it("declares the selected prop that vue-flow passes to edges", () => {
    expect(ErdRelationEdge.props.selected).toEqual({ type: Boolean, default: false });
  });
});
