import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { defineComponent, shallowReactive } from "vue";
import axios from "axios";
import ContextMenu from "@imengyu/vue3-context-menu";
import mixin from "@src/mixins/power_tree";
import { emitter } from "@src/emitter";
import { logger } from "@src/logging/logger_setup";
import { axiosHooks } from "@src/logging/service";
import { handleError } from "@src/logging/utils";
import { flashHighlight } from "@src/utils";
import {
  connectionsStore,
  settingsStore,
} from "@src/stores/stores_initializer";

vi.mock("@src/stores/stores_initializer", () => ({
  tabsStore: {
    selectedPrimaryTab: { metaData: { selectedDatabase: "db1" } },
  },
  settingsStore: { scrollTree: false },
  connectionsStore: { queueChangeActiveDatabaseThreadSafe: vi.fn() },
}));

vi.mock("@src/logging/logger_setup", () => ({ logger: { name: "logger" } }));

vi.mock("@src/logging/service", () => ({ axiosHooks: vi.fn() }));

vi.mock("@src/logging/utils", () => ({ handleError: vi.fn() }));

vi.mock("@src/utils", () => ({ flashHighlight: vi.fn() }));

vi.mock("@imengyu/vue3-context-menu", () => ({
  default: { showContextMenu: vi.fn() },
}));

const workspaceId = "ws-1";
const databaseIndex = 3;

const makeNode = (path, overrides = {}) => ({
  path,
  title: `node-${path.join("-")}`,
  level: path.length,
  isLeaf: false,
  isExpanded: false,
  isVisible: true,
  children: [],
  data: {},
  ...overrides,
});

// A stand-in for PowerTree: a component with the same methods and a $el.
function createFakeTree() {
  const state = shallowReactive({ selected: [] });
  const api = {
    select: vi.fn(),
    getSelected: vi.fn(() => state.selected),
    getNode: vi.fn(),
    getFirstNode: vi.fn(),
    getLastNode: vi.fn(),
    getNextNode: vi.fn(),
    getPrevNode: vi.fn(),
    updateNode: vi.fn(),
    insert: vi.fn(),
    remove: vi.fn(),
  };
  const component = defineComponent({
    template: '<div class="fake-tree"></div>',
    methods: api,
  });
  return { state, api, component };
}

describe("power_tree mixin", () => {
  let wrapper, tree, apiClient, getProperties, refreshTree;

  const mountHost = ({ contextMenu = {} } = {}) =>
    mount(
      {
        mixins: [mixin],
        components: { Tree: tree.component },
        props: { workspaceId: String, databaseIndex: Number },
        template: `<div class="tree-container">
          <div :id="workspaceId + '_tree'"><Tree ref="tree" /></div>
        </div>`,
        data: () => ({ contextMenu }),
        methods: { getProperties, refreshTree },
      },
      {
        props: { workspaceId, databaseIndex },
        attachTo: document.body,
      },
    );

  const treeEl = () => wrapper.vm.$refs.tree.$el;

  const container = () => treeEl().parentElement;

  const select = (node) => {
    tree.state.selected = node ? [node] : [];
  };

  // Adds the DOM that PowerTree renders for a node.
  const addNodeEl = (path, { top = 100, height = 20 } = {}) => {
    const el = document.createElement("div");
    el.setAttribute("path", JSON.stringify(path));
    el.innerHTML =
      '<div class="vue-power-tree-row"></div><div class="vue-power-tree-title"></div>';
    treeEl().appendChild(el);
    const rect = { top, height, left: 10, width: 200 };
    vi.spyOn(el, "getBoundingClientRect").mockReturnValue(rect);
    vi.spyOn(
      el.querySelector(".vue-power-tree-row"),
      "getBoundingClientRect",
    ).mockReturnValue(rect);
    vi.spyOn(
      el.querySelector(".vue-power-tree-title"),
      "getBoundingClientRect",
    ).mockReturnValue(rect);
    return el;
  };

  const rowOf = (el) => el.querySelector(".vue-power-tree-row");

  const setContainerMetrics = ({
    scrollTop = 0,
    scrollHeight = 2000,
    clientHeight = 400,
    top = 0,
  } = {}) => {
    const el = container();
    Object.defineProperty(el, "scrollTop", {
      value: scrollTop,
      configurable: true,
    });
    Object.defineProperty(el, "scrollHeight", {
      value: scrollHeight,
      configurable: true,
    });
    Object.defineProperty(el, "clientHeight", {
      value: clientHeight,
      configurable: true,
    });
    vi.spyOn(el, "getBoundingClientRect").mockReturnValue({ top });
    el.scrollTo = vi.fn();
  };

  beforeEach(() => {
    vi.clearAllMocks();
    settingsStore.scrollTree = false;
    tree = createFakeTree();
    getProperties = vi.fn();
    refreshTree = vi.fn();
    apiClient = { post: vi.fn() };
    axios.create.mockReturnValue(apiClient);
  });

  afterEach(() => {
    vi.useRealTimers();
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  describe("setup", () => {
    beforeEach(() => {
      wrapper = mountHost();
    });

    it("creates an api client with the logging hooks", () => {
      expect(wrapper.vm.api).toBe(apiClient);
      expect(axiosHooks).toHaveBeenCalledWith(logger, apiClient);
    });

    it("adds the database index and the workspace id to api requests", () => {
      const [config] = axios.create.mock.calls[0];
      const [addIds] = config.transformRequest;

      expect(addIds({ query: "select 1" })).toEqual({
        query: "select 1",
        database_index: databaseIndex,
        workspace_id: workspaceId,
      });
    });

    it("blocks the browser context menu on the tree", () => {
      const event = new MouseEvent("contextmenu", {
        bubbles: true,
        cancelable: true,
      });

      document.getElementById(`${workspaceId}_tree`).dispatchEvent(event);

      expect(event.defaultPrevented).toBe(true);
    });

  });

  describe("emitter events", () => {
    beforeEach(() => {
      wrapper = mountHost();
    });

    it("refreshes a node with force on refreshNode", () => {
      const node = makeNode([0, 1]);

      emitter.emit(`refreshNode_${workspaceId}`, { node });

      expect(refreshTree).toHaveBeenCalledWith(node, true);
    });

    it("removes a node on removeNode", () => {
      const node = makeNode([0, 1]);

      emitter.emit(`removeNode_${workspaceId}`, { node });

      expect(tree.api.remove).toHaveBeenCalledWith([node.path]);
    });

    it("refreshes the nodes of a type on refreshTreeRecursive", () => {
      wrapper.vm.refreshTreeRecursive = vi.fn();

      emitter.emit(`refreshTreeRecursive_${workspaceId}`, "schema_list");

      expect(wrapper.vm.refreshTreeRecursive).toHaveBeenCalledWith(
        "schema_list",
      );
    });

    it("focuses the tree and highlights it on focusTree", () => {
      const focus = vi.spyOn(treeEl(), "focus");

      emitter.emit(`focusTree_${workspaceId}`);

      expect(focus).toHaveBeenCalled();
      expect(flashHighlight).toHaveBeenCalledWith(wrapper.element);
    });

    it("removes its handlers when it unmounts", () => {
      wrapper.unmount();
      wrapper = null;

      expect(emitter.all.get(`refreshNode_${workspaceId}`)).toBeUndefined();
      expect(emitter.all.get(`removeNode_${workspaceId}`)).toBeUndefined();
      expect(
        emitter.all.get(`refreshTreeRecursive_${workspaceId}`),
      ).toBeUndefined();
      expect(emitter.all.get(`focusTree_${workspaceId}`)).toBeUndefined();
    });
  });

  describe("selected node", () => {
    it("tells the parent to clear its tabs when no node is selected", async () => {
      select(makeNode([0, 1]));
      wrapper = mountHost();

      select(null);
      await wrapper.vm.$nextTick();

      expect(wrapper.emitted("clearTabs")).toHaveLength(1);
    });

    it("keeps the tabs when another node is selected", async () => {
      select(makeNode([0, 1]));
      wrapper = mountHost();

      select(makeNode([0, 2]));
      await wrapper.vm.$nextTick();

      expect(wrapper.emitted("clearTabs")).toBeUndefined();
    });

  });

  describe("clicking and toggling", () => {
    const server = makeNode([0], { title: "Server" });

    beforeEach(() => {
      tree.api.getFirstNode.mockReturnValue(server);
      wrapper = mountHost();
    });

    it("gets the properties of a clicked node", () => {
      const node = makeNode([0, 1]);

      wrapper.vm.onClickHandler(node);

      expect(getProperties).toHaveBeenCalledWith(node);
    });

    it("does not get properties in the snippets tree", () => {
      tree.api.getFirstNode.mockReturnValue(
        makeNode([0], { title: "Snippets" }),
      );

      wrapper.vm.onClickHandler(makeNode([0, 1]));

      expect(getProperties).not.toHaveBeenCalled();
    });

    it("selects the node when it toggles", () => {
      const node = makeNode([0, 1]);

      wrapper.vm.onToggle(node);

      expect(tree.api.select).toHaveBeenCalledWith(node.path);
    });

    it("gets the properties 200 ms after the toggle", () => {
      vi.useFakeTimers();
      const node = makeNode([0, 1]);

      wrapper.vm.onToggle(node);
      vi.advanceTimersByTime(199);
      expect(getProperties).not.toHaveBeenCalled();

      vi.advanceTimersByTime(1);
      expect(getProperties).toHaveBeenCalledWith(node);
    });

    it("does not get properties on toggle in the snippets tree", () => {
      vi.useFakeTimers();
      tree.api.getFirstNode.mockReturnValue(
        makeNode([0], { title: "Snippets" }),
      );

      wrapper.vm.onToggle(makeNode([0, 1]));
      vi.advanceTimersByTime(200);

      expect(getProperties).not.toHaveBeenCalled();
    });

    it("refreshes a collapsed node when it toggles", () => {
      const node = makeNode([0, 1], { isExpanded: false });

      wrapper.vm.onToggle(node);

      expect(refreshTree).toHaveBeenCalledWith(node);
    });

    it("does not refresh an expanded node when it toggles", () => {
      wrapper.vm.onToggle(makeNode([0, 1], { isExpanded: true }));

      expect(refreshTree).not.toHaveBeenCalled();
    });

    it("scrolls the toggled node into view when scrollTree is on", async () => {
      settingsStore.scrollTree = true;
      wrapper.vm.scrollIntoViewIfPossible = vi.fn();
      const node = makeNode([0, 1]);

      wrapper.vm.onToggle(node);
      await wrapper.vm.$nextTick();

      expect(wrapper.vm.scrollIntoViewIfPossible).toHaveBeenCalledWith(node);
    });

    it("does not scroll the toggled node when scrollTree is off", async () => {
      wrapper.vm.scrollIntoViewIfPossible = vi.fn();

      wrapper.vm.onToggle(makeNode([0, 1]));
      await wrapper.vm.$nextTick();

      expect(wrapper.vm.scrollIntoViewIfPossible).not.toHaveBeenCalled();
    });

    it("ignores a double click on a leaf", () => {
      wrapper.vm.doubleClickNode(makeNode([0, 1], { isLeaf: true }));

      expect(tree.api.select).not.toHaveBeenCalled();
      expect(tree.api.updateNode).not.toHaveBeenCalled();
    });

    it("toggles and expands a node on double click", () => {
      const node = makeNode([0, 1]);

      wrapper.vm.doubleClickNode(node);

      expect(tree.api.select).toHaveBeenCalledWith(node.path);
      expect(refreshTree).toHaveBeenCalledWith(node);
      expect(tree.api.updateNode).toHaveBeenCalledWith(node.path, {
        isExpanded: true,
      });
    });
  });

  describe("clicks on the tree", () => {
    const node = makeNode([0, 1]);
    const event = { target: document.createElement("span") };

    beforeEach(() => {
      tree.api.getFirstNode.mockReturnValue(makeNode([0], { title: "Server" }));
      wrapper = mountHost();
    });

    // Finding the node from the click is up to the tree, so it is stubbed.
    const clickOn = (resolvedNode) => {
      wrapper.vm.resolveNodeFromEvent = vi.fn().mockReturnValue(resolvedNode);
    };

    it("selects the clicked node and gets its properties", () => {
      clickOn(node);

      wrapper.vm.handleLeftSideClick(event);

      expect(wrapper.vm.resolveNodeFromEvent).toHaveBeenCalledWith(event);
      expect(tree.api.select).toHaveBeenCalledWith(node.path);
      expect(getProperties).toHaveBeenCalledWith(node);
    });

    it("does nothing when the click is not on a node", () => {
      clickOn(undefined);

      wrapper.vm.handleLeftSideClick(event);

      expect(tree.api.select).not.toHaveBeenCalled();
      expect(getProperties).not.toHaveBeenCalled();
    });

    it("toggles the node on a double click", () => {
      clickOn(node);

      wrapper.vm.handleLeftSideDblClick(event);

      expect(tree.api.updateNode).toHaveBeenCalledWith(node.path, {
        isExpanded: true,
      });
    });

    it("does nothing when the double click is not on a node", () => {
      clickOn(undefined);

      wrapper.vm.handleLeftSideDblClick(event);

      expect(tree.api.updateNode).not.toHaveBeenCalled();
    });
  });

  describe("context menu", () => {
    const items = [{ label: "Refresh" }];
    const event = () => ({ x: 10, y: 20, preventDefault: vi.fn() });

    beforeEach(() => {
      wrapper = mountHost({ contextMenu: { cm_table: items } });
    });

    it("shows the menu of the node type at the pointer", () => {
      wrapper.vm.showContextMenu(
        makeNode([0, 1], { data: { contextMenu: "cm_table" } }),
        event(),
      );

      expect(ContextMenu.showContextMenu).toHaveBeenCalledWith(
        expect.objectContaining({ x: 10, y: 20, items }),
      );
      expect(wrapper.vm.treeContextMenuOpen).toBe(true);
    });

    it("marks the menu as closed when it closes", () => {
      wrapper.vm.showContextMenu(
        makeNode([0, 1], { data: { contextMenu: "cm_table" } }),
        event(),
      );

      ContextMenu.showContextMenu.mock.calls[0][0].onClose();

      expect(wrapper.vm.treeContextMenuOpen).toBe(false);
    });

    it("selects the node and shows its menu on a right click", () => {
      const node = makeNode([0, 1], { data: { contextMenu: "cm_table" } });
      const e = event();

      wrapper.vm.onContextMenu(node, e);

      expect(tree.api.select).toHaveBeenCalledWith(node.path);
      expect(e.preventDefault).toHaveBeenCalled();
      expect(ContextMenu.showContextMenu).toHaveBeenCalled();
    });

    it("shows no menu for a node without a context menu", () => {
      const e = event();

      wrapper.vm.onContextMenu(makeNode([0, 1]), e);

      expect(e.preventDefault).toHaveBeenCalled();
      expect(ContextMenu.showContextMenu).not.toHaveBeenCalled();
    });
  });

  describe("tree helpers", () => {
    const node = makeNode([0, 1, 2], { children: [makeNode([0, 1, 2, 0])] });

    beforeEach(() => {
      wrapper = mountHost();
    });

    it("inserts a spinner node inside a node", () => {
      wrapper.vm.insertSpinnerNode(node);

      expect(tree.api.insert).toHaveBeenCalledWith(
        { node, placement: "inside" },
        {
          title: "",
          isLeaf: true,
          isExpanded: false,
          isDraggable: false,
          data: { icon: "node-spin" },
        },
      );
    });

    it("inserts a node that is not a leaf by default", () => {
      wrapper.vm.insertNode(node, "users", { type: "table" });

      expect(tree.api.insert).toHaveBeenCalledWith(
        { node, placement: "inside" },
        {
          title: "users",
          isLeaf: false,
          isExpanded: false,
          isDraggable: false,
          data: { type: "table" },
        },
      );
    });

    it("inserts a leaf node when asked to", () => {
      wrapper.vm.insertNode(node, "id", { type: "column" }, true);

      expect(tree.api.insert.mock.calls[0][1].isLeaf).toBe(true);
    });

    it("gets the parent of a node from its path", () => {
      const parent = makeNode([0, 1]);
      tree.api.getNode.mockReturnValue(parent);

      expect(wrapper.vm.getParentNode(node)).toBe(parent);
      expect(tree.api.getNode).toHaveBeenCalledWith([0, 1]);
    });

    it("gets the parent one level up by default", () => {
      const parent = makeNode([0, 1]);
      tree.api.getNode.mockReturnValue(parent);

      expect(wrapper.vm.getParentNodeDeep(node)).toBe(parent);
    });

    it("gets the node itself when the depth is zero", () => {
      expect(wrapper.vm.getParentNodeDeep(node, 0)).toBe(node);
      expect(tree.api.getNode).not.toHaveBeenCalled();
    });

    it("climbs as many levels as the depth", () => {
      const byPath = { "[0,1]": makeNode([0, 1]), "[0]": makeNode([0]) };
      tree.api.getNode.mockImplementation(
        (path) => byPath[JSON.stringify(path)],
      );

      expect(wrapper.vm.getParentNodeDeep(node, 2)).toBe(byPath["[0]"]);
    });

    it("gets the first child of the current version of a node", () => {
      const current = makeNode([0, 1, 2], {
        children: [makeNode([0, 1, 2, 0])],
      });
      tree.api.getNode.mockReturnValue(current);

      expect(wrapper.vm.getFirstChildNode(node)).toBe(current.children[0]);
      expect(tree.api.getNode).toHaveBeenCalledWith(node.path);
    });

    it("expands and force refreshes the selected node on refreshNode", () => {
      select(node);

      wrapper.vm.refreshNode();

      expect(tree.api.updateNode).toHaveBeenCalledWith(node.path, {
        isExpanded: true,
      });
      expect(refreshTree).toHaveBeenCalledWith(node, true);
    });

    it("gives the context menu a Refresh item that runs refreshNode", () => {
      select(node);

      wrapper.vm.cmRefreshObject.onClick();

      expect(refreshTree).toHaveBeenCalledWith(node, true);
    });
  });

  describe("formatTitle", () => {
    beforeEach(() => {
      wrapper = mountHost();
    });

    it("shows the title alone when the node has no unique value", () => {
      expect(wrapper.vm.formatTitle({ title: "users", data: {} })).toBe(
        "users",
      );
    });

    it("adds the unique value after the title", () => {
      expect(
        wrapper.vm.formatTitle({ title: "users", data: { unique: "UQ" } }),
      ).toBe("users (UQ)");
    });

    it("adds a unique value of zero", () => {
      expect(
        wrapper.vm.formatTitle({ title: "users", data: { unique: 0 } }),
      ).toBe("users (0)");
    });
  });

  describe("nodeOpenError", () => {
    const node = makeNode([0, 1]);

    beforeEach(() => {
      wrapper = mountHost();
    });

    it("asks for the password when the password timed out", () => {
      const emit = vi.spyOn(emitter, "emit");
      const error = {
        response: {
          data: {
            password_timeout: true,
            data: "Password expired",
            kind: "database",
          },
        },
      };

      wrapper.vm.nodeOpenError(error, node);

      expect(emit).toHaveBeenCalledWith("show_password_prompt", {
        databaseIndex,
        successCallback: expect.any(Function),
        message: "Password expired",
        kind: "database",
      });
      expect(handleError).not.toHaveBeenCalled();
    });

    it("changes the active database and refreshes the node after the password", () => {
      const emit = vi.spyOn(emitter, "emit");
      select(node);
      wrapper.vm.nodeOpenError(
        {
          response: { data: { password_timeout: true, data: "x", kind: "k" } },
        },
        node,
      );

      emit.mock.calls
        .find(([name]) => name === "show_password_prompt")[1]
        .successCallback();

      expect(
        connectionsStore.queueChangeActiveDatabaseThreadSafe,
      ).toHaveBeenCalledWith({
        database_index: databaseIndex,
        workspace_id: workspaceId,
        database: "db1",
      });
      expect(refreshTree).toHaveBeenCalledWith(node, true);
    });

    it("removes the children and reports any other error", () => {
      const error = new Error("boom");

      wrapper.vm.nodeOpenError(error, node);

      expect(tree.api.updateNode).toHaveBeenCalledWith(node.path, {
        children: [],
      });
      expect(handleError).toHaveBeenCalledWith(error);
    });
  });

  describe("goToNodeAndSelect", () => {
    it("selects the node, scrolls to it, and gets its properties", () => {
      tree.api.getFirstNode.mockReturnValue(makeNode([0], { title: "Server" }));
      wrapper = mountHost();
      const node = makeNode([0, 1]);
      const row = rowOf(addNodeEl(node.path));
      row.scrollIntoView = vi.fn();

      wrapper.vm.goToNodeAndSelect(node);

      expect(tree.api.select).toHaveBeenCalledWith(node.path);
      expect(row.scrollIntoView).toHaveBeenCalledWith({
        block: "start",
        inline: "start",
        behavior: "smooth",
      });
      expect(getProperties).toHaveBeenCalledWith(node);
    });
  });

  describe("scrollIntoViewIfPossible", () => {
    const node = makeNode([0, 1]);

    beforeEach(() => {
      wrapper = mountHost();
      setContainerMetrics({
        scrollTop: 0,
        scrollHeight: 1000,
        clientHeight: 300,
      });
    });

    it("scrolls the node to the top when there is room to scroll", () => {
      const row = rowOf(addNodeEl(node.path, { top: 100 }));
      row.scrollIntoView = vi.fn();

      wrapper.vm.scrollIntoViewIfPossible(node);

      expect(row.scrollIntoView).toHaveBeenCalledWith({
        block: "start",
        inline: "start",
        behavior: "smooth",
      });
    });

    it("does not scroll when the node is too low to reach the top", () => {
      const row = rowOf(addNodeEl(node.path, { top: 900 }));
      row.scrollIntoView = vi.fn();

      wrapper.vm.scrollIntoViewIfPossible(node);

      expect(row.scrollIntoView).not.toHaveBeenCalled();
    });
  });

  describe("shouldUpdateNode", () => {
    const now = new Date("2026-01-01T00:01:00.000Z");

    beforeEach(() => {
      vi.useFakeTimers();
      vi.setSystemTime(now);
      wrapper = mountHost();
    });

    it("updates a node that was never updated", () => {
      const node = makeNode([0, 1], { data: { type: "table" } });

      expect(wrapper.vm.shouldUpdateNode(node)).toBe(true);
      expect(tree.api.updateNode).toHaveBeenCalledWith(node.path, {
        data: { type: "table", last_update: now.toISOString() },
      });
    });

    it("skips a node that was updated less than a minute ago", () => {
      const node = makeNode([0, 1], {
        data: { last_update: "2026-01-01T00:00:30.000Z" },
      });

      expect(wrapper.vm.shouldUpdateNode(node)).toBe(false);
      expect(tree.api.updateNode).not.toHaveBeenCalled();
    });

    it("updates a node that was updated a minute ago or more", () => {
      const node = makeNode([0, 1], {
        data: { last_update: "2026-01-01T00:00:00.000Z" },
      });

      expect(wrapper.vm.shouldUpdateNode(node)).toBe(true);
    });

    it("updates a recent node when forced", () => {
      const node = makeNode([0, 1], {
        data: { last_update: "2026-01-01T00:00:59.000Z" },
      });

      expect(wrapper.vm.shouldUpdateNode(node, true)).toBe(true);
      expect(tree.api.updateNode).toHaveBeenCalled();
    });
  });

  describe("expandAndRefreshIfNeeded", () => {
    beforeEach(() => {
      tree.api.getFirstNode.mockReturnValue(makeNode([0], { title: "Server" }));
      refreshTree = vi.fn(() => Promise.resolve());
      wrapper = mountHost();
    });

    it("refreshes a node without children and then expands it", async () => {
      const node = makeNode([0, 1], { children: [] });

      await wrapper.vm.expandAndRefreshIfNeeded(node);

      expect(refreshTree).toHaveBeenCalledWith(node, true);
      expect(refreshTree.mock.invocationCallOrder[0]).toBeLessThan(
        tree.api.updateNode.mock.invocationCallOrder[0],
      );
      expect(tree.api.updateNode).toHaveBeenCalledWith(node.path, {
        isExpanded: true,
      });
    });

    it("expands a node that has children and gets its properties", async () => {
      const node = makeNode([0, 1], { children: [makeNode([0, 1, 0])] });

      await wrapper.vm.expandAndRefreshIfNeeded(node);

      expect(refreshTree).not.toHaveBeenCalled();
      expect(tree.api.updateNode).toHaveBeenCalledWith(node.path, {
        isExpanded: true,
      });
      expect(getProperties).toHaveBeenCalledWith(node);
    });
  });

  describe("getNodeDatabase", () => {
    const database = makeNode([0, 0], {
      title: "db1",
      data: { type: "database" },
    });
    const group = makeNode([0, 0, 0], { data: { type: "schema_list" } });
    const table = makeNode([0, 0, 0, 0], { data: { type: "table" } });
    const server = makeNode([0], { data: { type: "server" } });
    const byPath = {};

    beforeEach(() => {
      [server, database, group, table].forEach((n) => {
        byPath[JSON.stringify(n.path)] = n;
      });
      tree.api.getNode.mockImplementation(
        (path) => byPath[JSON.stringify(path)],
      );
      wrapper = mountHost();
    });

    it("returns the title of a database node", () => {
      expect(wrapper.vm.getNodeDatabase(database)).toBe("db1");
    });

    it("returns the database that holds a nested node", () => {
      expect(wrapper.vm.getNodeDatabase(table)).toBe("db1");
    });

    it("returns null for a node outside any database", () => {
      expect(wrapper.vm.getNodeDatabase(server)).toBeNull();
    });

    it("returns null when no ancestor is a database", () => {
      const other = makeNode([0, 5], { data: { type: "role_list" } });
      byPath["[0,5]"] = other;

      expect(wrapper.vm.getNodeDatabase(other)).toBeNull();
    });
  });

  describe("refreshTreeRecursive", () => {
    let nodes;

    // server > database_list > (db1, db2) > schema_list / extension_list
    const buildTree = () => {
      const schemas1 = makeNode([0, 0, 0, 0], {
        data: { type: "schema_list" },
      });
      const schemas2 = makeNode([0, 0, 1, 0], {
        data: { type: "schema_list" },
      });
      const ext1 = makeNode([0, 0, 0, 1], { data: { type: "extension_list" } });
      const ext2 = makeNode([0, 0, 1, 1], { data: { type: "extension_list" } });
      const db1 = makeNode([0, 0, 0], {
        title: "db1",
        data: { type: "database" },
        children: [schemas1, ext1],
      });
      const db2 = makeNode([0, 0, 1], {
        title: "db2",
        data: { type: "database" },
        children: [schemas2, ext2],
      });
      const dbList = makeNode([0, 0], {
        data: { type: "database_list" },
        children: [db1, db2],
      });
      const server = makeNode([0], {
        data: { type: "server" },
        children: [dbList],
      });
      nodes = { server, dbList, db1, db2, schemas1, schemas2, ext1, ext2 };
      const byPath = {};
      Object.values(nodes).forEach((n) => {
        byPath[JSON.stringify(n.path)] = n;
      });
      tree.api.getFirstNode.mockReturnValue(server);
      tree.api.getNode.mockImplementation(
        (path) => byPath[JSON.stringify(path)],
      );
    };

    beforeEach(() => {
      buildTree();
      wrapper = mountHost();
    });

    it("refreshes and expands the nodes of the type in the selected database", () => {
      wrapper.vm.refreshTreeRecursive("schema_list");

      expect(refreshTree).toHaveBeenCalledTimes(1);
      expect(refreshTree).toHaveBeenCalledWith(nodes.schemas1, true);
      expect(tree.api.updateNode).toHaveBeenCalledWith(nodes.schemas1.path, {
        isExpanded: true,
      });
    });

    it("leaves the other databases alone", () => {
      wrapper.vm.refreshTreeRecursive("schema_list");

      expect(refreshTree).not.toHaveBeenCalledWith(nodes.schemas2, true);
    });

    it("follows the database selected in the tree", () => {
      wrapper.vm.selectedDatabase = "db2";

      wrapper.vm.refreshTreeRecursive("schema_list");

      expect(refreshTree).toHaveBeenCalledWith(nodes.schemas2, true);
      expect(refreshTree).not.toHaveBeenCalledWith(nodes.schemas1, true);
    });

    it("refreshes the database first and its extensions after 200 ms", () => {
      vi.useFakeTimers();

      wrapper.vm.refreshTreeRecursive("extension_list");

      expect(refreshTree).toHaveBeenCalledTimes(1);
      expect(refreshTree).toHaveBeenCalledWith(nodes.db1, true);

      vi.advanceTimersByTime(200);

      expect(refreshTree).toHaveBeenCalledWith(nodes.ext1, true);
      expect(tree.api.updateNode).toHaveBeenCalledWith(nodes.ext1.path, {
        isExpanded: true,
      });
      expect(refreshTree).not.toHaveBeenCalledWith(nodes.ext2, true);
    });

    it("does nothing when the tree has no node of the type", () => {
      wrapper.vm.refreshTreeRecursive("view_list");

      expect(refreshTree).not.toHaveBeenCalled();
    });
  });

  describe("keyboard navigation", () => {
    let selected;

    const pressKey = (code, init = {}) => {
      const event = new KeyboardEvent("keydown", {
        code,
        bubbles: true,
        cancelable: true,
        ...init,
      });
      document.getElementById(`${workspaceId}_tree`).dispatchEvent(event);
      return event;
    };

    beforeEach(() => {
      selected = makeNode([0, 1], {
        level: 2,
        data: { contextMenu: "cm_table" },
      });
      select(selected);
      tree.api.getFirstNode.mockReturnValue(makeNode([0], { title: "Server" }));
      wrapper = mountHost({
        contextMenu: { cm_table: [{ label: "Refresh" }] },
      });
      setContainerMetrics();
    });

    it("ignores keys while a context menu is open", () => {
      wrapper.vm.treeContextMenuOpen = true;

      const event = pressKey("ArrowDown");

      expect(tree.api.getNextNode).not.toHaveBeenCalled();
      expect(event.defaultPrevented).toBe(false);
    });

    it("ignores keys that it does not handle", () => {
      const event = pressKey("KeyA");

      expect(event.defaultPrevented).toBe(false);
      expect(tree.api.select).not.toHaveBeenCalled();
    });

    // Navigation must skip the nodes that are not visible.
    const expectVisibleOnly = (isVisible) => {
      expect(isVisible({ isVisible: true })).toBe(true);
      expect(isVisible({ isVisible: false })).toBe(false);
    };

    describe("moving the selection", () => {
      const next = makeNode([0, 2]);

      beforeEach(() => {
        addNodeEl(next.path);
      });

      it("selects the next visible node on ArrowDown", () => {
        tree.api.getNextNode.mockReturnValue(next);

        const event = pressKey("ArrowDown");

        const [path, isVisible] = tree.api.getNextNode.mock.calls[0];
        expect(path).toEqual(selected.path);
        expectVisibleOnly(isVisible);
        expect(event.defaultPrevented).toBe(true);
        expect(tree.api.select).toHaveBeenCalledWith(next.path);
        expect(getProperties).toHaveBeenCalledWith(next);
      });

      it("selects the previous visible node on ArrowUp", () => {
        tree.api.getPrevNode.mockReturnValue(next);

        const event = pressKey("ArrowUp");

        const [path, isVisible] = tree.api.getPrevNode.mock.calls[0];
        expect(path).toEqual(selected.path);
        expectVisibleOnly(isVisible);
        expect(event.defaultPrevented).toBe(true);
        expect(tree.api.select).toHaveBeenCalledWith(next.path);
        expect(getProperties).toHaveBeenCalledWith(next);
      });

      it("keeps the selection when there is no node to move to", () => {
        tree.api.getNextNode.mockReturnValue(undefined);

        pressKey("ArrowDown");

        expect(tree.api.select).not.toHaveBeenCalled();
        expect(getProperties).not.toHaveBeenCalled();
      });

      it("jumps to the first node on Home without getting properties", () => {
        const first = makeNode([0]);
        tree.api.getFirstNode.mockReturnValue(first);

        pressKey("Home");

        expect(tree.api.select).toHaveBeenCalledWith(first.path);
        expect(getProperties).not.toHaveBeenCalled();
      });

      it("jumps to the last node on End", () => {
        const last = makeNode([0, 9], { isVisible: true });
        tree.api.getLastNode.mockReturnValue(last);

        pressKey("End");

        expect(tree.api.select).toHaveBeenCalledWith(last.path);
      });

      it("jumps to the last visible node on End when the last node is hidden", () => {
        const hidden = makeNode([0, 9], { isVisible: false });
        const visible = makeNode([0, 8], { isVisible: true });
        tree.api.getLastNode.mockReturnValue(hidden);
        tree.api.getPrevNode.mockReturnValue(visible);

        pressKey("End");

        const [path, isVisible] = tree.api.getPrevNode.mock.calls[0];
        expect(path).toEqual(hidden.path);
        expectVisibleOnly(isVisible);
        expect(tree.api.select).toHaveBeenCalledWith(visible.path);
      });

      it("moves down one page on PageDown and stops at the last node", () => {
        const [n1, n2, n3] = [
          makeNode([0, 3]),
          makeNode([0, 4]),
          makeNode([0, 5]),
        ];
        addNodeEl(n3.path);
        tree.api.getNextNode
          .mockReturnValueOnce(n1)
          .mockReturnValueOnce(n2)
          .mockReturnValueOnce(n3)
          .mockReturnValue(undefined);

        const event = pressKey("PageDown");

        expect(event.defaultPrevented).toBe(true);
        expectVisibleOnly(tree.api.getNextNode.mock.calls[0][1]);
        expect(tree.api.select).toHaveBeenCalledWith(n3.path);
      });

      it("moves up one page on PageUp and stops at the first node", () => {
        const [n1, n2] = [makeNode([0, 3]), makeNode([0, 4])];
        addNodeEl(n2.path);
        tree.api.getPrevNode
          .mockReturnValueOnce(n1)
          .mockReturnValueOnce(n2)
          .mockReturnValue(undefined);

        const event = pressKey("PageUp");

        expect(event.defaultPrevented).toBe(true);
        expectVisibleOnly(tree.api.getPrevNode.mock.calls[0][1]);
        expect(tree.api.select).toHaveBeenCalledWith(n2.path);
      });

      it("sizes a page by the height of the selected node", () => {
        const nodeEl = addNodeEl(selected.path);
        Object.defineProperty(nodeEl, "offsetHeight", { value: 200 });
        tree.api.getNextNode.mockImplementation((path) => makeNode([0, 2]));

        pressKey("PageDown");

        // 400 px container / 200 px node = 2 steps.
        expect(tree.api.getNextNode).toHaveBeenCalledTimes(2);
      });
    });

    describe("expanding and collapsing", () => {
      it("does nothing on ArrowRight for a leaf", () => {
        select(makeNode([0, 1], { isLeaf: true }));

        pressKey("ArrowRight");

        expect(tree.api.updateNode).not.toHaveBeenCalled();
        expect(tree.api.select).not.toHaveBeenCalled();
      });

      it("opens a collapsed node on ArrowRight", () => {
        pressKey("ArrowRight");

        expect(refreshTree).toHaveBeenCalledWith(selected);
        expect(tree.api.updateNode).toHaveBeenCalledWith(selected.path, {
          isExpanded: true,
        });
      });

      it("moves to the next node on ArrowRight when already open", () => {
        const next = makeNode([0, 1, 0]);
        addNodeEl(next.path);
        select(makeNode([0, 1], { isExpanded: true }));
        tree.api.getNextNode.mockReturnValue(next);

        pressKey("ArrowRight");

        expectVisibleOnly(tree.api.getNextNode.mock.calls[0][1]);
        expect(tree.api.select).toHaveBeenCalledWith(next.path);
      });

      it("does nothing on ArrowLeft at the first level", () => {
        select(makeNode([0], { level: 1 }));

        pressKey("ArrowLeft");

        expect(tree.api.select).not.toHaveBeenCalled();
        expect(tree.api.updateNode).not.toHaveBeenCalled();
      });

      it("moves to the parent on ArrowLeft for a collapsed node", () => {
        const parent = makeNode([0], { level: 1 });
        addNodeEl(parent.path);
        tree.api.getPrevNode.mockReturnValue(parent);

        pressKey("ArrowLeft");

        const [, isParent] = tree.api.getPrevNode.mock.calls[0];
        expect(isParent({ level: 1 })).toBe(true);
        expect(isParent({ level: 2 })).toBe(false);
        expect(tree.api.select).toHaveBeenCalledWith(parent.path);
      });

      it("moves to the parent on ArrowLeft for a leaf", () => {
        const parent = makeNode([0], { level: 1 });
        addNodeEl(parent.path);
        select(makeNode([0, 1], { level: 2, isLeaf: true, isExpanded: true }));
        tree.api.getPrevNode.mockReturnValue(parent);

        pressKey("ArrowLeft");

        expect(tree.api.select).toHaveBeenCalledWith(parent.path);
      });

      it("collapses an open node on ArrowLeft", () => {
        select(makeNode([0, 1], { level: 2, isExpanded: true }));

        pressKey("ArrowLeft");

        expect(tree.api.updateNode).toHaveBeenCalledWith([0, 1], {
          isExpanded: false,
        });
        expect(tree.api.select).not.toHaveBeenCalled();
      });

      it.each(["Enter", "Space"])("toggles the node on %s", (code) => {
        const event = pressKey(code);

        expect(event.defaultPrevented).toBe(true);
        expect(refreshTree).toHaveBeenCalledWith(selected);
        expect(tree.api.updateNode).toHaveBeenCalledWith(selected.path, {
          isExpanded: true,
        });
      });

      it.each(["Enter", "Space"])("leaves a leaf alone on %s", (code) => {
        select(makeNode([0, 1], { isLeaf: true }));

        const event = pressKey(code);

        expect(event.defaultPrevented).toBe(true);
        expect(tree.api.updateNode).not.toHaveBeenCalled();
      });
    });

    describe("opening the context menu", () => {
      beforeEach(() => {
        addNodeEl(selected.path, { top: 100, height: 20 });
      });

      it("opens the menu of the selected node on the ContextMenu key", () => {
        const event = pressKey("ContextMenu");

        expect(event.defaultPrevented).toBe(true);
        expect(tree.api.select).toHaveBeenCalledWith(selected.path);
        expect(ContextMenu.showContextMenu).toHaveBeenCalledWith(
          expect.objectContaining({ items: [{ label: "Refresh" }] }),
        );
      });

      it("opens the menu on Shift+F10", () => {
        const event = pressKey("F10", { shiftKey: true });

        expect(event.defaultPrevented).toBe(true);
        expect(ContextMenu.showContextMenu).toHaveBeenCalled();
      });

      it("ignores F10 without Shift", () => {
        const event = pressKey("F10");

        expect(event.defaultPrevented).toBe(false);
        expect(ContextMenu.showContextMenu).not.toHaveBeenCalled();
      });
    });

    describe("keeping the selected node in view", () => {
      const next = makeNode([0, 2]);

      beforeEach(() => {
        tree.api.getNextNode.mockReturnValue(next);
      });

      it("does not scroll when the node is in view", () => {
        addNodeEl(next.path, { top: 100, height: 20 });

        pressKey("ArrowDown");

        expect(container().scrollTo).not.toHaveBeenCalled();
      });

      it("scrolls up when the node is under the header", () => {
        addNodeEl(next.path, { top: 10, height: 20 });

        pressKey("ArrowDown");

        // nodeTop (10) is above viewTop (40), so scroll to nodeTop - 40.
        expect(container().scrollTo).toHaveBeenCalledWith({
          top: -30,
          behavior: "instant",
        });
      });

      it("scrolls down when the node is under the footer", () => {
        addNodeEl(next.path, { top: 390, height: 20 });

        pressKey("ArrowDown");

        // nodeBottom (410) is past viewBottom (370): 410 - 400 + 30.
        expect(container().scrollTo).toHaveBeenCalledWith({
          top: 40,
          behavior: "instant",
        });
      });
    });
  });
});
