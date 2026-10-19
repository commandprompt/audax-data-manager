import { flushPromises, mount, enableAutoUnmount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import ERDTab from "@src/components/ERDTab.vue";
import Controls from "@src/erd_plugins/Controls.vue";
import axios from "axios";
import { handleError } from "@src/logging/utils";
import { capture } from "@src/erd_plugins/screenshot";

vi.mock("@src/logging/utils", () => ({
  handleError: vi.fn(),
}));

vi.mock("@src/erd_plugins/screenshot", () => ({
  capture: vi.fn(() => Promise.resolve("data:image/png;base64,")),
}));

enableAutoUnmount(afterEach);

// VueFlow relies on browser APIs (ResizeObserver, layout measurements, ...)
// that aren't meaningful in jsdom/happy-dom, so it is replaced with a small
// stub that mimics the subset of its instance API ERDTab.vue relies on
// through `this.$refs.vueFlow`. Its internal state is exposed as plain
// component data so tests can set it up and inspect it directly.
function createVueFlowStub() {
  const spies = {
    zoomIn: vi.fn(),
    zoomOut: vi.fn(),
    fitView: vi.fn(),
    setViewport: vi.fn(),
    updateNode: vi.fn(),
  };

  const component = {
    name: "VueFlow",
    template: "<div><slot /></div>",
    data() {
      return {
        internalNodes: [],
        internalEdges: [],
        internalViewport: null,
      };
    },
    computed: {
      nodes() {
        return this.internalNodes;
      },
    },
    methods: {
      zoomIn(...args) {
        return spies.zoomIn(...args);
      },
      zoomOut(...args) {
        return spies.zoomOut(...args);
      },
      fitView(...args) {
        return spies.fitView(...args);
      },
      setViewport(...args) {
        return spies.setViewport(...args);
      },
      updateNode(...args) {
        return spies.updateNode(...args);
      },
      toObject() {
        return {
          nodes: this.internalNodes,
          edges: this.internalEdges,
          viewport: this.internalViewport || { x: 0, y: 0, zoom: 1 },
        };
      },
      findEdge(id) {
        return this.internalEdges.find((edge) => edge.id === id);
      },
      findNode(id) {
        return this.internalNodes.find((node) => node.id === id);
      },
    },
  };

  return { component, spies };
}

describe("ERDTab.vue", () => {
  let wrapper;
  let vueFlowSpies;

  const initialProps = {
    schema: "public",
    workspaceId: "workspace-id",
    tabId: "tab-id",
    databaseIndex: 0,
    databaseName: "test_db",
  };

  const noLayoutResponse = {
    data: {
      nodes: [
        {
          id: "table1",
          label: "Table1",
          columns: [
            {
              name: "id",
              type: "integer",
              cgid: null,
              is_pk: true,
              is_fk: false,
            },
            {
              name: "name",
              type: "character varying",
              cgid: null,
              is_pk: false,
              is_fk: false,
            },
          ],
        },
        {
          id: "table2",
          label: "Table2",
          columns: [
            {
              name: "id",
              type: "integer",
              cgid: null,
              is_pk: true,
              is_fk: false,
            },
            {
              name: "table1_id",
              type: "integer",
              cgid: "fk1",
              is_pk: false,
              is_fk: true,
            },
          ],
        },
      ],
      edges: [
        {
          from: "table2",
          from_col: "table1_id",
          to: "table1",
          to_col: "id",
          label: "",
          cgid: "fk1",
        },
      ],
    },
  };

  const mountComponent = (options = {}) => {
    const { component: VueFlowStub, spies } = createVueFlowStub();
    vueFlowSpies = spies;

    return mount(ERDTab, {
      props: initialProps,
      global: {
        stubs: {
          VueFlow: VueFlowStub,
          Background: true,
          ErdRelationEdge: true,
        },
      },
      ...options,
    });
  };

  const vueFlow = () => wrapper.vm.$refs.vueFlow;

  beforeEach(() => {
    vi.clearAllMocks();
    axios.post.mockResolvedValue(noLayoutResponse);
    wrapper = mountComponent();
  });

  describe("rendering", () => {
    it("renders the controls and the vue-flow graph", () => {
      expect(wrapper.exists()).toBe(true);
      expect(wrapper.findComponent(Controls).exists()).toBe(true);
    });

    it("triggers a screenshot download when the screenshot button is clicked", async () => {
      const doScreenshotSpy = vi
        .spyOn(wrapper.vm, "doScreenshot")
        .mockImplementation(() => {});
      // Force a re-render so the template re-binds its click handler to the
      // spy (Vue caches the bare-identifier handler reference per render).
      wrapper.vm.$forceUpdate();
      await wrapper.vm.$nextTick();

      await wrapper
        .find('button[title="Download a screenshot"]')
        .trigger("click");

      expect(doScreenshotSpy).toHaveBeenCalledTimes(1);
    });

    it("resets the layout when the reset button is clicked", async () => {
      const resetSpy = vi
        .spyOn(wrapper.vm, "resetToDefault")
        .mockImplementation(() => {});
      wrapper.vm.$forceUpdate();
      await wrapper.vm.$nextTick();

      await wrapper.find('button[title="Reset to default"]').trigger("click");

      expect(resetSpy).toHaveBeenCalledTimes(1);
    });

    it("toggles fullscreen when the fullscreen button is clicked", async () => {
      const toggleSpy = vi
        .spyOn(wrapper.vm, "toggleFullScreen")
        .mockImplementation(() => {});
      wrapper.vm.$forceUpdate();
      await wrapper.vm.$nextTick();

      await wrapper.find('button[title="Fullscreen"]').trigger("click");

      expect(toggleSpy).toHaveBeenCalledTimes(1);
    });

    it("delegates zoom in/out clicks to the vue-flow instance", async () => {
      await wrapper.find('button[title="Zoom In"]').trigger("click");
      expect(vueFlowSpies.zoomIn).toHaveBeenCalledTimes(1);

      await wrapper.find('button[title="Zoom Out"]').trigger("click");
      expect(vueFlowSpies.zoomOut).toHaveBeenCalledTimes(1);
    });

    it("passes the capturingScreenshot state down to Controls", async () => {
      expect(wrapper.findComponent(Controls).props("capturingScreenshot")).toBe(
        false,
      );

      wrapper.vm.capturingScreenshot = true;
      await wrapper.vm.$nextTick();

      expect(wrapper.findComponent(Controls).props("capturingScreenshot")).toBe(
        true,
      );
    });
  });

  describe("loadSchemaGraph (mounted behavior)", () => {
    it("requests the schema graph with the expected payload", async () => {
      await flushPromises();

      expect(axios.post).toHaveBeenCalledWith("/draw_graph/", {
        database_index: initialProps.databaseIndex,
        workspace_id: initialProps.workspaceId,
        schema: initialProps.schema,
      });
    });

    it("builds table and column nodes and edges when no saved layout exists", async () => {
      await flushPromises();

      expect(wrapper.vm.jsonLayout).toBe(false);

      const tableNodes = wrapper.vm.nodes.filter(
        (node) => node.type === "table",
      );
      const columnNodes = wrapper.vm.nodes.filter(
        (node) => node.type === "column",
      );

      expect(tableNodes).toHaveLength(2);
      expect(tableNodes.map((node) => node.id)).toEqual(["table1", "table2"]);
      expect(tableNodes[0].data.label).toBe("Table1");

      expect(columnNodes).toHaveLength(4);
      const nameColumn = columnNodes.find((node) => node.id === "table1_name");
      expect(nameColumn.parentNode).toBe("table1");
      expect(nameColumn.data.type).toBe("varchar");

      // Only the last column of each table gets extra spacing below it.
      expect(columnNodes.find((node) => node.id === "table1_id").data.is_last).toBe(
        false,
      );
      expect(nameColumn.data.is_last).toBe(true);
      expect(
        columnNodes.find((node) => node.id === "table2_id").data.is_last,
      ).toBe(false);
      expect(
        columnNodes.find((node) => node.id === "table2_table1_id").data
          .is_last,
      ).toBe(true);

      expect(wrapper.vm.edges).toEqual([
        {
          id: "table2_table1_id-table1_id",
          source: "table2_table1_id",
          target: "table1_id",
          sourceHandle: "source-right",
          targetHandle: "target-left",
          label: "",
          cgid: "fk1",
          type: "bezierOrSmoothstep",
          pathOptions: { offset: 30 },
          markerEnd: "erd-one-only",
          markerStart: "erd-one-many",
          data: {
            cgid: "fk1",
            sourceTableId: "table2",
            targetTableId: "table1",
          },
        },
      ]);
    });

    it("restores a saved layout and merges new nodes/edges when the backend returns one", async () => {
      wrapper.unmount();

      const layoutResponse = {
        data: {
          layout: { nodes: [], edges: [], viewport: { x: 0, y: 0, zoom: 1 } },
          new_nodes: [{ id: "table3", label: "Table3", columns: [] }],
          new_edges: [],
        },
      };
      axios.post.mockResolvedValueOnce(layoutResponse);

      wrapper = mountComponent();
      const restoreSpy = vi.spyOn(wrapper.vm, "restoreVueFlowLayout");

      await flushPromises();

      expect(restoreSpy).toHaveBeenCalledWith(
        layoutResponse.data.layout,
        layoutResponse.data.new_nodes,
        layoutResponse.data.new_edges,
      );
      expect(wrapper.vm.jsonLayout).toBe(true);
    });

    it("calls handleError when the request fails", async () => {
      wrapper.unmount();
      const error = new Error("network error");
      axios.post.mockRejectedValueOnce(error);

      wrapper = mountComponent();
      await flushPromises();

      expect(handleError).toHaveBeenCalledWith(error);
    });
  });

  describe("shortDataType", () => {
    it("maps known postgresql type names to their short form", () => {
      expect(wrapper.vm.shortDataType("character varying")).toBe("varchar");
      expect(wrapper.vm.shortDataType("timestamp with time zone")).toBe(
        "timestamptz",
      );
      expect(wrapper.vm.shortDataType("timestamp without time zone")).toBe(
        "timestamp",
      );
      expect(wrapper.vm.shortDataType("time without time zone")).toBe("time");
      expect(wrapper.vm.shortDataType("time with time zone")).toBe("timetz");
      expect(wrapper.vm.shortDataType("character")).toBe("char");
      expect(wrapper.vm.shortDataType("boolean")).toBe("bool");
    });

    it("returns the original type name when there is no mapping", () => {
      expect(wrapper.vm.shortDataType("integer")).toBe("integer");
    });
  });

  describe("node/edge factories", () => {
    it("createTableNode builds a table node", () => {
      const node = wrapper.vm.createTableNode(
        { id: "table1", label: "Table1" },
        { x: 10, y: 20 },
      );

      expect(node).toEqual({
        id: "table1",
        type: "table",
        position: { x: 10, y: 20 },
        data: { label: "Table1" },
      });
    });

    it("createColumnNode builds a column node positioned below the table header", () => {
      const node = wrapper.vm.createColumnNode(
        { id: "table1" },
        {
          name: "email",
          type: "character varying",
          cgid: "cg1",
          is_pk: false,
          is_fk: true,
        },
        1,
      );

      expect(node.id).toBe("table1_email");
      expect(node.type).toBe("column");
      expect(node.parentNode).toBe("table1");
      expect(node.draggable).toBe(false);
      expect(node.data).toEqual({
        label: "email",
        type: "varchar",
        cgid: "cg1",
        is_pk: false,
        is_fk: true,
        is_highlighted: false,
        is_last: false,
      });
    });

    it("createColumnNode defaults is_last to false when not passed", () => {
      const node = wrapper.vm.createColumnNode(
        { id: "table1" },
        { name: "id", type: "integer", cgid: null, is_pk: true, is_fk: false },
        0,
      );

      expect(node.data.is_last).toBe(false);
    });

    it("createColumnNode marks the column as last when isLast is passed", () => {
      const node = wrapper.vm.createColumnNode(
        { id: "table1" },
        { name: "id", type: "integer", cgid: null, is_pk: true, is_fk: false },
        0,
        true,
      );

      expect(node.data.is_last).toBe(true);
    });

    it("createEdge builds an edge with markers and handles", () => {
      const edge = wrapper.vm.createEdge({
        from: "table2",
        from_col: "table1_id",
        to: "table1",
        to_col: "id",
        from_cols: ["table1_id"],
        to_cols: ["id"],
        label: "fk",
        cgid: "fk1",
      });

      expect(edge.id).toBe("table2_table1_id-table1_id");
      expect(edge.source).toBe("table2_table1_id");
      expect(edge.target).toBe("table1_id");
      expect(edge.markerEnd).toBe("erd-one-only");
      expect(edge.markerStart).toBe("erd-one-many");
      expect(edge.data).toEqual({
        cgid: "fk1",
        sourceTableId: "table2",
        targetTableId: "table1",
        sourceColumns: ["table1_id"],
        targetColumns: ["id"],
      });
    });
  });

  describe("restoreVueFlowLayout", () => {
    const savedViewport = { x: 5, y: 5, zoom: 2 };

    it("keeps saved nodes/edges and restores the saved viewport", async () => {
      const layoutData = {
        nodes: [{ id: "table1", type: "table", position: { x: 0, y: 0 } }],
        edges: [{ id: "e1", cgid: "fk1", source: "a", target: "b" }],
        viewport: savedViewport,
      };

      wrapper.vm.restoreVueFlowLayout(layoutData, [], []);
      await flushPromises();

      expect(wrapper.vm.nodes).toEqual(layoutData.nodes);
      expect(wrapper.vm.edges).toEqual(layoutData.edges);
      expect(vueFlowSpies.setViewport).toHaveBeenCalledWith(savedViewport);
      expect(vueFlowSpies.fitView).not.toHaveBeenCalled();
    });

    it("fits the view when there is no saved viewport", async () => {
      wrapper.vm.restoreVueFlowLayout({ nodes: [], edges: [] }, [], []);
      await flushPromises();

      expect(vueFlowSpies.fitView).toHaveBeenCalledWith({ padding: 0.2 });
      expect(vueFlowSpies.setViewport).not.toHaveBeenCalled();
    });

    it("adds brand new tables together with their columns", async () => {
      const newTable = {
        id: "table_new",
        label: "NewTable",
        columns: [
          { name: "id", type: "integer" },
          { name: "name", type: "character varying" },
        ],
      };

      wrapper.vm.restoreVueFlowLayout({ nodes: [], edges: [] }, [newTable], []);
      await flushPromises();

      const tableNode = wrapper.vm.nodes.find(
        (node) => node.id === "table_new",
      );
      const columnNode = wrapper.vm.nodes.find(
        (node) => node.id === "table_new_id",
      );
      const lastColumnNode = wrapper.vm.nodes.find(
        (node) => node.id === "table_new_name",
      );

      expect(tableNode).toMatchObject({ id: "table_new", type: "table" });
      expect(columnNode).toMatchObject({
        id: "table_new_id",
        type: "column",
        parentNode: "table_new",
      });
      expect(columnNode.data.is_last).toBe(false);
      expect(lastColumnNode.data.is_last).toBe(true);
    });

    it("rebuilds columns and updates the label for an existing table with new columns", async () => {
      const layoutData = {
        nodes: [
          { id: "table1", type: "table", position: { x: 0, y: 0 } },
          {
            id: "table1_old_col",
            type: "column",
            parentNode: "table1",
            position: { x: 0, y: 0 },
          },
        ],
        edges: [],
      };

      const changedTable = {
        id: "table1",
        label: "Table1Renamed",
        columns: [{ name: "new_col", type: "integer" }],
      };

      wrapper.vm.restoreVueFlowLayout(layoutData, [changedTable], []);
      await flushPromises();

      expect(
        wrapper.vm.nodes.find((node) => node.id === "table1_old_col"),
      ).toBeUndefined();

      const tableNode = wrapper.vm.nodes.find((node) => node.id === "table1");
      expect(tableNode.data.label).toBe("Table1Renamed");

      const newColumnNode = wrapper.vm.nodes.find(
        (node) => node.id === "table1_new_col",
      );
      expect(newColumnNode).toMatchObject({
        id: "table1_new_col",
        parentNode: "table1",
      });
    });

    it("only appends edges that are not already part of the saved layout", async () => {
      const layoutData = {
        nodes: [],
        // Deduplication is keyed by the edge id vue-flow uses
        // (`${source}-${target}`), not by cgid.
        edges: [
          {
            id: "a_col_a-b_col_b",
            cgid: "existing-cgid",
            source: "a_col_a",
            target: "b_col_b",
          },
        ],
      };

      const newEdges = [
        {
          from: "a",
          from_col: "col_a",
          to: "b",
          to_col: "col_b",
          cgid: "existing-cgid",
        },
        {
          from: "c",
          from_col: "col_c",
          to: "d",
          to_col: "col_d",
          cgid: "brand-new-cgid",
        },
      ];

      wrapper.vm.restoreVueFlowLayout(layoutData, [], newEdges);
      await flushPromises();

      expect(wrapper.vm.edges).toHaveLength(2);
      expect(wrapper.vm.edges.map((edge) => edge.cgid)).toEqual([
        "existing-cgid",
        "brand-new-cgid",
      ]);
    });
  });

  describe("saveGraphState", () => {
    it("posts the vue-flow layout to the backend", async () => {
      vueFlow().internalNodes = [{ id: "table1", type: "table" }];
      vueFlow().internalEdges = [];
      vueFlow().internalViewport = { x: 1, y: 2, zoom: 1 };
      axios.post.mockResolvedValueOnce({ data: { status: "saved" } });

      wrapper.vm.saveGraphState();
      await flushPromises();

      expect(axios.post).toHaveBeenCalledWith("/save_graph_state/", {
        workspace_id: initialProps.workspaceId,
        schema: initialProps.schema,
        database_name: initialProps.databaseName,
        database_index: initialProps.databaseIndex,
        layout: {
          nodes: [{ id: "table1", type: "table" }],
          edges: [],
          viewport: { x: 1, y: 2, zoom: 1 },
        },
      });
    });

    it("calls handleError when saving the layout fails", async () => {
      const error = new Error("save failed");
      axios.post.mockRejectedValueOnce(error);

      wrapper.vm.saveGraphState();
      await flushPromises();

      expect(handleError).toHaveBeenCalledWith(error);
    });
  });

  describe("toggleFullScreen", () => {
    it("toggles the fullscreen class and flag", () => {
      expect(wrapper.vm.inFullscreen).toBe(false);

      wrapper.vm.toggleFullScreen();

      expect(wrapper.vm.inFullscreen).toBe(true);
      expect(
        wrapper.vm.$refs.erdContainer.classList.contains(
          "omnidb__panel-view--full",
        ),
      ).toBe(true);

      wrapper.vm.toggleFullScreen();

      expect(wrapper.vm.inFullscreen).toBe(false);
      expect(
        wrapper.vm.$refs.erdContainer.classList.contains(
          "omnidb__panel-view--full",
        ),
      ).toBe(false);
    });
  });

  describe("selection", () => {
    const columnA = {
      id: "table1_id",
      type: "column",
      parentNode: "table1",
      data: { is_highlighted: false },
    };
    const columnB = {
      id: "table1_name",
      type: "column",
      parentNode: "table1",
      data: { is_highlighted: false },
    };
    const columnC = {
      id: "table2_id",
      type: "column",
      parentNode: "table2",
      data: { is_highlighted: false },
    };
    const columnD = {
      id: "table2_table1_id",
      type: "column",
      parentNode: "table2",
      data: { is_highlighted: false },
    };
    const tableNode1 = { id: "table1", type: "table", data: {} };
    const tableNode2 = { id: "table2", type: "table", data: {} };
    const tableNode3 = { id: "table3", type: "table", data: {} };
    const columnE = {
      id: "table3_id",
      type: "column",
      parentNode: "table3",
      data: { is_highlighted: false },
    };
    const edge1 = {
      id: "table2_table1_id-table1_id",
      source: "table2_table1_id",
      target: "table1_id",
      data: {},
    };

    beforeEach(() => {
      wrapper.vm.nodes = [
        tableNode1,
        { ...columnA, data: { ...columnA.data } },
        { ...columnB, data: { ...columnB.data } },
        tableNode2,
        { ...columnC, data: { ...columnC.data } },
        { ...columnD, data: { ...columnD.data } },
        tableNode3,
        { ...columnE, data: { ...columnE.data } },
      ];
      wrapper.vm.edges = [edge1];
    });

    it("clearErdSelection resets edge selection and column highlighting", () => {
      vueFlow().internalEdges = [{ ...edge1, selected: true, zIndex: 2 }];
      wrapper.vm.nodes[1].data.is_highlighted = true;

      wrapper.vm.clearErdSelection();

      const storedEdge = vueFlow().findEdge(edge1.id);
      expect(storedEdge.selected).toBe(false);
      expect(storedEdge.zIndex).toBe(1);
      expect(wrapper.vm.nodes[1].data.is_highlighted).toBe(false);
    });

    it("onEdgeClick clears the current selection and selects the clicked edge", () => {
      const clearSpy = vi
        .spyOn(wrapper.vm, "clearErdSelection")
        .mockImplementation(() => {});
      const selectSpy = vi
        .spyOn(wrapper.vm, "selectErdEdges")
        .mockImplementation(() => {});

      wrapper.vm.onEdgeClick({ edge: edge1 });

      expect(clearSpy).toHaveBeenCalledTimes(1);
      expect(selectSpy).toHaveBeenCalledWith([edge1]);
    });

    it("onNodeClick selects related edges for every column of a clicked table", () => {
      const selectSpy = vi
        .spyOn(wrapper.vm, "selectErdEdges")
        .mockImplementation(() => {});

      wrapper.vm.onNodeClick({ node: tableNode1 });

      expect(vueFlowSpies.updateNode).toHaveBeenCalledWith("table1_id", {
        selected: true,
      });
      expect(vueFlowSpies.updateNode).toHaveBeenCalledWith("table1_name", {
        selected: true,
      });
      expect(selectSpy).toHaveBeenCalledWith([edge1]);
    });

    it("onNodeClick clears the selection when a clicked table has no related edges", () => {
      const clearSpy = vi
        .spyOn(wrapper.vm, "clearErdSelection")
        .mockImplementation(() => {});

      wrapper.vm.onNodeClick({ node: tableNode3 });

      expect(clearSpy).toHaveBeenCalledTimes(1);
    });

    it("onNodeClick selects related edges when a column is clicked", () => {
      const selectSpy = vi
        .spyOn(wrapper.vm, "selectErdEdges")
        .mockImplementation(() => {});

      wrapper.vm.onNodeClick({ node: columnD });

      expect(selectSpy).toHaveBeenCalledWith([edge1]);
    });

    it("onNodeClick clears the selection when a clicked column has no related edges", () => {
      const clearSpy = vi
        .spyOn(wrapper.vm, "clearErdSelection")
        .mockImplementation(() => {});

      wrapper.vm.onNodeClick({ node: columnC });

      expect(clearSpy).toHaveBeenCalledTimes(1);
    });

    describe("composite foreign key", () => {
      // table2 (a, b) references table1 (id, name); the edge connects only a -> id
      const compositeEdge = {
        id: "table2_a-table1_id",
        source: "table2_a",
        target: "table1_id",
        data: {
          sourceTableId: "table2",
          targetTableId: "table1",
          sourceColumns: ["a", "b"],
          targetColumns: ["id", "name"],
        },
      };
      const compositeNodes = [
        { id: "table1_id", type: "column", parentNode: "table1", data: { is_highlighted: false } },
        { id: "table1_name", type: "column", parentNode: "table1", data: { is_highlighted: false } },
        { id: "table1_other", type: "column", parentNode: "table1", data: { is_highlighted: false } },
        { id: "table2_a", type: "column", parentNode: "table2", data: { is_highlighted: false } },
        { id: "table2_b", type: "column", parentNode: "table2", data: { is_highlighted: false } },
      ];

      beforeEach(() => {
        wrapper.vm.nodes = compositeNodes.map((node) => ({ ...node, data: { ...node.data } }));
        wrapper.vm.edges = [compositeEdge];
      });

      it("onNodeClick selects the edge when a column that is not an edge end is clicked", () => {
        const selectSpy = vi
          .spyOn(wrapper.vm, "selectErdEdges")
          .mockImplementation(() => {});

        wrapper.vm.onNodeClick({ node: { id: "table2_b", type: "column" } });
        wrapper.vm.onNodeClick({ node: { id: "table1_name", type: "column" } });

        expect(selectSpy).toHaveBeenNthCalledWith(1, [compositeEdge]);
        expect(selectSpy).toHaveBeenNthCalledWith(2, [compositeEdge]);
      });

      it("selectErdEdges highlights all columns of the foreign key", () => {
        vueFlow().internalEdges = [{ ...compositeEdge, selected: false, zIndex: 1 }];
        vueFlow().internalNodes = wrapper.vm.nodes;

        wrapper.vm.selectErdEdges([compositeEdge]);

        const highlighted = vueFlow()
          .internalNodes.filter((node) => node.data.is_highlighted)
          .map((node) => node.id);
        expect(highlighted).toEqual(["table1_id", "table1_name", "table2_a", "table2_b"]);
      });
    });

    it("selectErdEdges marks the given edges as selected and highlights their columns only", () => {
      const secondEdge = {
        id: "other-edge",
        source: "table2_id",
        target: "unrelated",
      };
      wrapper.vm.edges = [edge1, secondEdge];

      vueFlow().internalEdges = [
        { ...edge1, selected: false, zIndex: 1 },
        { ...secondEdge, selected: false, zIndex: 1 },
      ];
      vueFlow().internalNodes = wrapper.vm.nodes;

      wrapper.vm.selectErdEdges([edge1]);

      const storedEdge1 = vueFlow().findEdge(edge1.id);
      const storedEdge2 = vueFlow().findEdge(secondEdge.id);
      expect(storedEdge1.selected).toBe(true);
      expect(storedEdge1.zIndex).toBe(2);
      expect(storedEdge2.selected).toBe(false);

      expect(vueFlow().findNode("table1_id").data.is_highlighted).toBe(true);
      expect(vueFlow().findNode("table2_table1_id").data.is_highlighted).toBe(
        true,
      );
      expect(vueFlow().findNode("table1_name").data.is_highlighted).toBe(false);
      expect(vueFlow().findNode("table2_id").data.is_highlighted).toBe(false);
    });
  });

  describe("edge routing geometry", () => {
    it("getTableBounds computes the bounding box from position and dimensions", () => {
      const bounds = wrapper.vm.getTableBounds({
        dimensions: { width: 100, height: 50 },
        position: { x: 20, y: 30 },
      });

      expect(bounds).toEqual({ left: 20, right: 120, top: 30, bottom: 80 });
    });

    it("getTableBounds defaults position to the origin when missing", () => {
      const bounds = wrapper.vm.getTableBounds({
        dimensions: { width: 10, height: 10 },
      });

      expect(bounds).toEqual({ left: 0, right: 10, top: 0, bottom: 10 });
    });

    const sourceTable = {
      id: "sourceTable",
      dimensions: { width: 100, height: 100 },
      position: { x: 0, y: 0 },
    };
    const sourceColumn = { id: "sourceColumn", parentNode: "sourceTable" };

    it("routes source-right/target-left when the target table is to the right", () => {
      const targetTable = {
        id: "targetTable",
        dimensions: { width: 100, height: 100 },
        position: { x: 300, y: 0 },
      };
      const targetColumn = { id: "targetColumn", parentNode: "targetTable" };

      const route = wrapper.vm.getBestHorizontalRoute(
        { source: "sourceColumn", target: "targetColumn" },
        [sourceTable, sourceColumn, targetTable, targetColumn],
      );

      expect(route).toEqual({
        sourceHandle: "source-right",
        targetHandle: "target-left",
      });
    });

    it("routes source-left/target-right when the target table is to the left", () => {
      const targetTable = {
        id: "targetTable",
        dimensions: { width: 100, height: 100 },
        position: { x: -300, y: 0 },
      };
      const targetColumn = { id: "targetColumn", parentNode: "targetTable" };

      const route = wrapper.vm.getBestHorizontalRoute(
        { source: "sourceColumn", target: "targetColumn" },
        [sourceTable, sourceColumn, targetTable, targetColumn],
      );

      expect(route).toEqual({
        sourceHandle: "source-left",
        targetHandle: "target-right",
      });
    });

    it("returns null when both columns belong to the same table", () => {
      const otherColumn = { id: "otherColumn", parentNode: "sourceTable" };

      const route = wrapper.vm.getBestHorizontalRoute(
        { source: "sourceColumn", target: "otherColumn" },
        [sourceTable, sourceColumn, otherColumn],
      );

      expect(route).toBeNull();
    });

    it("rerouteEdgesByTableDistance updates handles for edges whose route changed", () => {
      const targetTable = {
        id: "targetTable",
        dimensions: { width: 100, height: 100 },
        position: { x: 300, y: 0 },
      };
      const targetColumn = { id: "targetColumn", parentNode: "targetTable" };
      const edge = {
        id: "edge1",
        source: "sourceColumn",
        target: "targetColumn",
        sourceHandle: "source-left",
        targetHandle: "target-right",
      };

      wrapper.vm.edges = [edge];
      vueFlow().internalEdges = [{ ...edge }];
      vueFlow().internalNodes = [
        sourceTable,
        sourceColumn,
        targetTable,
        targetColumn,
      ];

      wrapper.vm.rerouteEdgesByTableDistance();

      const storedEdge = vueFlow().findEdge("edge1");
      expect(storedEdge.sourceHandle).toBe("source-right");
      expect(storedEdge.targetHandle).toBe("target-left");
    });
  });

  describe("onNodeDragStop / scheduleRerouteEdges", () => {
    let rafSpy;
    let cafSpy;

    beforeEach(() => {
      let rafId = 0;
      rafSpy = vi.fn(() => ++rafId);
      cafSpy = vi.fn();
      vi.stubGlobal("requestAnimationFrame", rafSpy);
      vi.stubGlobal("cancelAnimationFrame", cafSpy);
    });

    it("onNodeDragStop reroutes edges and persists the layout", () => {
      const rerouteSpy = vi
        .spyOn(wrapper.vm, "rerouteEdgesByTableDistance")
        .mockImplementation(() => {});
      const saveSpy = vi
        .spyOn(wrapper.vm, "saveGraphState")
        .mockImplementation(() => {});

      wrapper.vm.onNodeDragStop();

      expect(rerouteSpy).toHaveBeenCalledTimes(1);
      expect(saveSpy).toHaveBeenCalledTimes(1);
    });

    it("schedules a single reroute via requestAnimationFrame", () => {
      const rerouteSpy = vi
        .spyOn(wrapper.vm, "rerouteEdgesByTableDistance")
        .mockImplementation(() => {});

      wrapper.vm.scheduleRerouteEdges();

      expect(rafSpy).toHaveBeenCalledTimes(1);
      expect(wrapper.vm.rerouteFrame).toBe(1);

      const scheduledCallback = rafSpy.mock.calls[0][0];
      scheduledCallback();

      expect(rerouteSpy).toHaveBeenCalledTimes(1);
      expect(wrapper.vm.rerouteFrame).toBeNull();
    });

    it("cancels a pending frame when scheduled again before it fires", () => {
      vi.spyOn(wrapper.vm, "rerouteEdgesByTableDistance").mockImplementation(
        () => {},
      );

      wrapper.vm.scheduleRerouteEdges();
      const firstFrameId = wrapper.vm.rerouteFrame;
      wrapper.vm.scheduleRerouteEdges();

      expect(cafSpy).toHaveBeenCalledWith(firstFrameId);
      expect(rafSpy).toHaveBeenCalledTimes(2);
    });
  });

  describe("applyGroupedZIndexes", () => {
    it("assigns increasing z-indexes per table and offsets its columns above it", () => {
      const table1 = { id: "table1", type: "table" };
      const column1 = { id: "table1_id", type: "column", parentNode: "table1" };
      const table2 = { id: "table2", type: "table" };
      const column2 = { id: "table2_id", type: "column", parentNode: "table2" };

      wrapper.vm.nodes = [table1, column1, table2, column2];

      wrapper.vm.applyGroupedZIndexes();

      expect(vueFlowSpies.updateNode).toHaveBeenCalledWith("table1", {
        zIndex: 10,
      });
      expect(vueFlowSpies.updateNode).toHaveBeenCalledWith("table1_id", {
        zIndex: 11,
      });
      expect(vueFlowSpies.updateNode).toHaveBeenCalledWith("table2", {
        zIndex: 20,
      });
      expect(vueFlowSpies.updateNode).toHaveBeenCalledWith("table2_id", {
        zIndex: 21,
      });
    });
  });

  describe("onNodesInitialized / resetToDefault", () => {
    const layoutedTableNode = {
      id: "table1",
      type: "table",
      position: { x: 0, y: 0 },
    };
    const internalTableNode = {
      id: "table1",
      type: "table",
      dimensions: { width: 100, height: 80 },
    };

    it("computes the layout, fits the view and reroutes/z-indexes when there is no saved layout", async () => {
      wrapper.vm.jsonLayout = false;
      wrapper.vm.nodes = [layoutedTableNode];
      vueFlow().internalNodes = [internalTableNode];

      const rerouteSpy = vi
        .spyOn(wrapper.vm, "rerouteEdgesByTableDistance")
        .mockImplementation(() => {});
      const applySpy = vi
        .spyOn(wrapper.vm, "applyGroupedZIndexes")
        .mockImplementation(() => {});

      wrapper.vm.onNodesInitialized();
      await flushPromises();

      expect(wrapper.vm.nodes[0].position).toEqual({ x: 50, y: 50 });
      expect(vueFlowSpies.fitView).toHaveBeenCalledTimes(1);
      expect(rerouteSpy).toHaveBeenCalledTimes(1);
      expect(applySpy).toHaveBeenCalledTimes(1);
    });

    it("skips the layout computation and just reroutes/z-indexes when restoring a saved layout", async () => {
      wrapper.vm.jsonLayout = true;
      wrapper.vm.nodes = [layoutedTableNode];

      const rerouteSpy = vi
        .spyOn(wrapper.vm, "rerouteEdgesByTableDistance")
        .mockImplementation(() => {});
      const applySpy = vi
        .spyOn(wrapper.vm, "applyGroupedZIndexes")
        .mockImplementation(() => {});

      wrapper.vm.onNodesInitialized();
      await flushPromises();

      expect(vueFlowSpies.fitView).not.toHaveBeenCalled();
      expect(rerouteSpy).toHaveBeenCalledTimes(1);
      expect(applySpy).toHaveBeenCalledTimes(1);
    });

    it("resetToDefault relayouts, reroutes, fits the view and persists the new state", async () => {
      wrapper.vm.nodes = [layoutedTableNode];
      vueFlow().internalNodes = [internalTableNode];

      const rerouteSpy = vi
        .spyOn(wrapper.vm, "rerouteEdgesByTableDistance")
        .mockImplementation(() => {});
      const applySpy = vi
        .spyOn(wrapper.vm, "applyGroupedZIndexes")
        .mockImplementation(() => {});
      const saveSpy = vi
        .spyOn(wrapper.vm, "saveGraphState")
        .mockImplementation(() => {});

      wrapper.vm.resetToDefault();
      await flushPromises();

      expect(wrapper.vm.nodes[0].position).toEqual({ x: 50, y: 50 });
      expect(applySpy).toHaveBeenCalledTimes(1);
      expect(rerouteSpy).toHaveBeenCalledTimes(1);
      expect(vueFlowSpies.fitView).toHaveBeenCalledTimes(1);
      expect(saveSpy).toHaveBeenCalledTimes(1);
    });
  });

  describe("doScreenshot", () => {
    let rafSpy;

    beforeEach(() => {
      rafSpy = vi.fn();
      vi.stubGlobal("requestAnimationFrame", rafSpy);
    });

    // Runs the two nested requestAnimationFrame callbacks scheduled by
    // doScreenshot, in the order they were most recently queued.
    const runScheduledFrames = () => {
      const firstFrame = rafSpy.mock.calls[rafSpy.mock.calls.length - 1][0];
      firstFrame();
      const secondFrame = rafSpy.mock.calls[rafSpy.mock.calls.length - 1][0];
      secondFrame();
    };

    it("marks capturingScreenshot while capturing and clears it once the capture resolves", async () => {
      expect(wrapper.vm.capturingScreenshot).toBe(false);

      wrapper.vm.doScreenshot();

      expect(wrapper.vm.capturingScreenshot).toBe(true);
      expect(rafSpy).toHaveBeenCalledTimes(1);

      runScheduledFrames();

      expect(capture).toHaveBeenCalledWith(wrapper.vm.$refs.vueFlowWrap, {
        shouldDownload: true,
      });

      await flushPromises();

      expect(wrapper.vm.capturingScreenshot).toBe(false);
    });

    it("ignores a screenshot click while a capture is already in progress", () => {
      wrapper.vm.doScreenshot();
      expect(rafSpy).toHaveBeenCalledTimes(1);

      wrapper.vm.doScreenshot();

      expect(rafSpy).toHaveBeenCalledTimes(1);
    });

    it("allows starting a new capture again once the previous one finished", async () => {
      wrapper.vm.doScreenshot();
      runScheduledFrames();
      await flushPromises();

      expect(wrapper.vm.capturingScreenshot).toBe(false);

      wrapper.vm.doScreenshot();

      expect(wrapper.vm.capturingScreenshot).toBe(true);
      expect(rafSpy).toHaveBeenCalledTimes(3);
    });
  });
});
