import { describe, it, expect } from "vitest";
import {
  truncateText,
  extractOrderByClause,
  findChild,
  findNode,
  splitStringInHalf,
  isSafeHtml,
} from "@src/utils.js";

describe("utils.js", () => {
  describe("truncateText", () => {
    it("returns an empty string for falsy text", () => {
      expect(truncateText("", 10)).toBe("");
      expect(truncateText(null, 10)).toBe("");
      expect(truncateText(undefined, 10)).toBe("");
    });

    it("returns the text unchanged when within maxLength", () => {
      expect(truncateText("short", 13)).toBe("short");
    });

    it("truncates plain text with an ellipsis when it has no slashes", () => {
      expect(truncateText("abcdefghij", 5)).toBe("ab...");
    });

    it("keeps the first and last path segments and ellipses the middle when it would overflow", () => {
      expect(truncateText("first/aaaaaaaaaa/bbbbbbbbbb/last", 10)).toBe(
        "first/.../last",
      );
    });

    it("keeps every middle segment when they all fit within maxLength", () => {
      expect(truncateText("a/bb/ccccccccccccccc", 10)).toBe(
        "a/bb//ccccccccccccccc",
      );
    });
  });

  describe("extractOrderByClause", () => {
    it("returns an empty orderByClause when there is no ORDER BY", () => {
      expect(extractOrderByClause("name = 'test'")).toEqual({
        queryFilterCleaned: "name = 'test'",
        orderByClause: "",
      });
    });

    it("extracts a trailing ORDER BY clause and cleans the remaining filter", () => {
      expect(extractOrderByClause("name = 'test' ORDER BY id DESC")).toEqual({
        queryFilterCleaned: "name = 'test'",
        orderByClause: "ORDER BY id DESC",
      });
    });

    it("matches ORDER BY case-insensitively and supports multiple columns", () => {
      expect(
        extractOrderByClause("status = 1 order by name, created_at"),
      ).toEqual({
        queryFilterCleaned: "status = 1",
        orderByClause: "ORDER BY name, created_at",
      });
    });

    it("handles an empty query filter", () => {
      expect(extractOrderByClause("")).toEqual({
        queryFilterCleaned: "",
        orderByClause: "",
      });
    });
  });

  describe("findNode", () => {
    const tree = {
      title: "root",
      children: [
        {
          title: "folder",
          children: [{ title: "leaf", children: [] }],
        },
        { title: "sibling", children: [] },
      ],
    };

    it("returns the node itself when it matches the predicate", () => {
      expect(findNode(tree, (n) => n.title === "root")).toBe(tree);
    });

    it("finds a deeply nested node matching the predicate", () => {
      const found = findNode(tree, (n) => n.title === "leaf");
      expect(found?.title).toBe("leaf");
    });

    it("returns null when no node matches", () => {
      expect(findNode(tree, (n) => n.title === "missing")).toBeNull();
    });

    it("handles nodes without a children array", () => {
      expect(
        findNode({ title: "lonely" }, (n) => n.title === "lonely"),
      ).toEqual({ title: "lonely" });
    });
  });

  describe("findChild", () => {
    it("returns the first direct child matching the given type", () => {
      const node = {
        children: [{ data: { type: "folder" } }, { data: { type: "table" } }],
      };

      expect(findChild(node, "table")).toBe(node.children[1]);
    });

    it("returns undefined when no direct child matches", () => {
      const node = { children: [{ data: { type: "folder" } }] };

      expect(findChild(node, "table")).toBeUndefined();
    });

    it("returns undefined when the node has no children", () => {
      expect(findChild({}, "table")).toBeUndefined();
    });
  });

  describe("splitStringInHalf", () => {
    it("splits an even-length string evenly", () => {
      expect(splitStringInHalf("abcd")).toEqual(["ab", "cd"]);
    });

    it("gives the extra character to the first half for odd-length strings", () => {
      expect(splitStringInHalf("abcde")).toEqual(["abc", "de"]);
    });

    it("handles an empty string", () => {
      expect(splitStringInHalf("")).toEqual(["", ""]);
    });
  });

  describe("isSafeHtml", () => {
    it("accepts plain text", () => {
      expect(isSafeHtml("Just a message.")).toBe(true);
      expect(isSafeHtml("")).toBe(true);
    });

    it("accepts the allowed tags", () => {
      expect(
        isSafeHtml(
          "<b>b</b><strong>strong</strong><i>i</i><em>em</em><mark>mark</mark>" +
            "<small>small</small><del>del</del><ins>ins</ins><sub>sub</sub><sup>sup</sup><br>"
        )
      ).toBe(true);
    });

    it("rejects tags that are not allowed", () => {
      expect(isSafeHtml("<script>alert(1)</script>")).toBe(false);
      expect(isSafeHtml("<div>text</div>")).toBe(false);
      expect(isSafeHtml("<iframe src='x'></iframe>")).toBe(false);
      expect(isSafeHtml("<img src=x onerror=alert(1)>")).toBe(false);
    });

    it("rejects tags that have attributes", () => {
      expect(isSafeHtml('<b onclick="alert(1)">text</b>')).toBe(false);
      expect(isSafeHtml('<b class="x">text</b>')).toBe(false);
    });

    it("rejects links", () => {
      expect(isSafeHtml('<a href="https://example.com">link</a>')).toBe(false);
      expect(isSafeHtml('<a href="javascript:alert(1)">link</a>')).toBe(false);
    });

    it("rejects an unsafe tag that is nested in an allowed tag", () => {
      expect(isSafeHtml("<b>text<script>alert(1)</script></b>")).toBe(false);
    });
  });
});
