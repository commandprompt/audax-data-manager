import { describe, it, expect, beforeEach, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { useTabsStore } from "@src/stores/tabs";
import { emitter } from "@src/emitter";
import * as worspaceModule from "@src/workspace";
import { operationModes } from "@src/constants";
import axios from "axios";

vi.mock("@src/workspace");

vi.mock("@src/stores/stores_initializer", () => {
  const connectionsStore = {
    connections: [{ id: 1, technology: "terminal" }],
    getConnection: vi.fn(() => {
      return { id: 1, technology: "terminal" };
    }),
    updateConnection: vi.fn(),
  };
  const messageModalStore = vi.fn();
  const dbMetadataStore = {
    deleteDbMeta: vi.fn(),
  };
  return { connectionsStore, messageModalStore, dbMetadataStore };
});

describe("useTabsStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    document.title = "";
  });

  it("should initialize with a unique id and empty tabs", () => {
    const store = useTabsStore();
    expect(store.id).toBeDefined();
    expect(store.tabs).toEqual([]);
    expect(store.selectedPrimaryTab).toBe("");
  });

  it("should return only selectable primary tabs", () => {
    const store = useTabsStore();

    const tab1 = store.addTab({ name: "Tab 1", selectable: true });
    const tab2 = store.addTab({ name: "Tab 2", selectable: false });
    const tab3 = store.addTab({ name: "Tab 3", selectable: true });
    const tab4 = store.addTab({ name: "Tab 4", selectable: false });

    const selectableTabs = store.selectablePrimaryTabs;

    expect(selectableTabs).toStrictEqual([tab1, tab3]);
  });

  it("should add a primary tab", () => {
    const store = useTabsStore();
    const tab = store.addTab({ name: "Primary Tab" });
    expect(store.tabs).toContainEqual(
      expect.objectContaining({ id: tab.id, name: "Primary Tab" })
    );
  });

  it("should add a secondary tab to a primary tab", () => {
    const store = useTabsStore();
    const primaryTab = store.addTab({ name: "Primary Tab" });
    const secondaryTab = store.addTab({
      name: "Secondary Tab",
      parentId: primaryTab.id,
    });

    const primaryTabWithSecondary = store.tabs.find(
      (tab) => tab.id === primaryTab.id
    );
    expect(primaryTabWithSecondary.metaData.secondaryTabs).toContainEqual(
      expect.objectContaining({ id: secondaryTab.id, name: "Secondary Tab" })
    );
  });

  it("should select a primary tab", () => {
    const store = useTabsStore();
    const tab = store.addTab({ name: "Primary Tab" });
    store.selectTab(tab);
    expect(store.selectedPrimaryTab).toEqual(tab);
  });

  it("should select a secondary tab", () => {
    const store = useTabsStore();
    const primaryTab = store.addTab({ name: "Primary Tab" });
    const secondaryTab = store.addTab({
      name: "Secondary Tab",
      parentId: primaryTab.id,
    });
    store.selectTab(secondaryTab);

    const selectedSecondaryTab = store.getSelectedSecondaryTab(primaryTab.id);

    expect(selectedSecondaryTab).toStrictEqual(secondaryTab);
  });

  it("should remove a primary tab", () => {
    const store = useTabsStore();
    const tab = store.addTab({ name: "Primary Tab" });
    store.removeTab(tab);
    expect(store.tabs).not.toContainEqual(
      expect.objectContaining({ id: tab.id })
    );
  });

  it("should remove a secondary tab", () => {
    const store = useTabsStore();
    const primaryTab = store.addTab({ name: "Primary Tab" });
    const secondaryTab = store.addTab({
      name: "Secondary Tab",
      parentId: primaryTab.id,
    });
    store.removeTab(secondaryTab);
    expect(store.tabs).not.toContainEqual(
      expect.objectContaining({ id: secondaryTab.id })
    );
  });

  it("should handle tab selection and deselection correctly", () => {
    const store = useTabsStore();
    const tab = store.addTab({ name: "Primary Tab" });
    store.selectTab(tab);
    expect(store.selectedPrimaryTab).toEqual(tab);
    store.removeTab(tab);
    expect(store.tabs).toStrictEqual([]);
  });

  it("should get secondary tabs", () => {
    const store = useTabsStore();
    const primaryTab = store.addTab({ name: "Primary Tab" });
    const secondaryTab = store.addTab({
      name: "Secondary Tab",
      parentId: primaryTab.id,
    });
    const tabs = store.getSecondaryTabs(primaryTab.id);

    expect(tabs).toStrictEqual([secondaryTab]);
  });

  it("should get secondary tabs as empty list", () => {
    const store = useTabsStore();
    const primaryTab = store.addTab({ name: "Primary Tab" });
    const secondaryTab = store.addTab({
      name: "Secondary Tab",
      parentId: primaryTab.id,
    });
    const tabs = store.getSecondaryTabs(999);

    expect(tabs).toStrictEqual([]);
  });

  it("should get primary tab by id", () => {
    const store = useTabsStore();
    const primaryTab = store.addTab({ name: "Primary Tab" });

    const tab = store.getPrimaryTabById(primaryTab.id);

    expect(tab).toStrictEqual(primaryTab);
    expect(store.getPrimaryTabById(999)).toBeUndefined();
  });

  it("should get secondary tab by id", () => {
    const store = useTabsStore();
    const primaryTab = store.addTab({ name: "Primary Tab" });
    const secondaryTab = store.addTab({
      name: "Secondary Tab",
      parentId: primaryTab.id,
    });
    const tab = store.getSecondaryTabById(secondaryTab.id, primaryTab.id);

    expect(tab).toStrictEqual(secondaryTab);
    expect(store.getSecondaryTabById(999, primaryTab.id)).toBeUndefined();
  });

  it("should create a Snippet Panel tab", () => {
    const store = useTabsStore();
    store.createSnippetPanel();
    const tab = store.tabs.find((tab) => tab.name === "Snippets");
    expect(tab).toBeTruthy();
    expect(tab.component).toBe("SnippetPanel");
  });

  it("should Snippet Panel tab clickFunction emit event", () => {
    const emitterEmitSpy = vi.spyOn(emitter, "emit");
    const store = useTabsStore();
    store.createSnippetPanel();
    const tab = store.tabs.find((tab) => tab.name === "Snippets");

    tab.clickFunction();

    expect(emitterEmitSpy).toHaveBeenCalledOnce();
    expect(emitterEmitSpy).toBeCalledWith("toggle_snippet_panel");
  });

  it("should create a Connections tab", () => {
    const store = useTabsStore();
    store.createConnectionsTab();
    const tab = store.tabs.find((tab) => tab.name === "Connections");
    expect(tab).toBeTruthy();
    expect(tab.component).toBeNull();
  });

  it("should Connections tab clickFunction trigger showMenuNewTabOuter", () => {
    const store = useTabsStore();
    store.createConnectionsTab();
    const showMenuNewTabOuterSpy = vi.spyOn(
      worspaceModule,
      "showMenuNewTabOuter"
    );
    const tab = store.tabs.find((tab) => tab.name === "Connections");
    tab.clickFunction("event");
    expect(showMenuNewTabOuterSpy).toHaveBeenCalledOnce();
  });

  it("should create a Welcome tab", () => {
    const store = useTabsStore();
    expect(document.title).toBe("");
    store.createWelcomeTab();
    const tab = store.tabs.find((tab) => tab.name === "Welcome");
    expect(tab).toBeTruthy();
    expect(tab.component).toBe("WelcomeScreen");
    expect(store.selectedPrimaryTab).toBe(tab);
  });

  it("should create and select a connection tab", async () => {
    const store = useTabsStore();
    const connectionIndex = 0;
    const workspaceTab = await store.createWorkspaceTab(connectionIndex);

    expect(workspaceTab).toBeDefined();
    expect(store.selectedPrimaryTab).toEqual(workspaceTab);
  });

  it("should create a Terminal tab", () => {
    const store = useTabsStore();
    store.createTerminalTab(0, "TestAlias", "Test Details");
    const tab = store.tabs.find((tab) => tab.name === "TestAlias");
    expect(tab).toBeTruthy();
    expect(tab.component).toBe("TerminalTab");
    expect(store.selectedPrimaryTab).toBe(tab);
  });

  describe("closeTabsForConnection", () => {
    it("closes a workspace tab referencing the deleted connection", async () => {
      axios.post.mockResolvedValue({ data: { returning_rows: [] } });
      const store = useTabsStore();
      const workspaceTab = await store.createWorkspaceTab(1);
      expect(store.tabs).toContainEqual(workspaceTab);

      store.closeTabsForConnection(1);

      expect(store.tabs).not.toContainEqual(workspaceTab);
    });

    it("closes a terminal tab referencing the deleted connection", () => {
      const store = useTabsStore();
      store.createTerminalTab(1, "TestAlias", "Test Details");
      const tab = store.tabs.find((tab) => tab.name === "TestAlias");
      expect(tab).toBeTruthy();

      store.closeTabsForConnection(1);

      expect(store.tabs.find((tab) => tab.name === "TestAlias")).toBeUndefined();
    });

    it("leaves tabs for other connections untouched", () => {
      const store = useTabsStore();
      store.createTerminalTab(1, "TestAlias", "Test Details");
      const tab = store.tabs.find((tab) => tab.name === "TestAlias");

      store.closeTabsForConnection(999);

      expect(store.tabs).toContainEqual(tab);
    });
  });

  it("should create a Console tab", () => {
    const store = useTabsStore();
    store.createConsoleTab();
    const tab = store.tabs.find((tab) => tab.name === "Console");
    expect(tab).toBeTruthy();
    expect(tab.component).toBe("ConsoleTab");
    expect(store.selectedPrimaryTab).toBe(tab);
  });

  it("should create a Query tab", () => {
    const store = useTabsStore();
    store.createQueryTab("TestQuery", 1, "TestDB", "SELECT * FROM test");
    const tab = store.tabs.find((tab) => tab.name === "TestQuery");
    expect(tab).toBeTruthy();
    expect(tab.component).toBe("QueryTab");
    expect(store.selectedPrimaryTab).toBe(tab);
  });

  it("should create a Snippet tab", () => {
    const store = useTabsStore();
    store.createSnippetPanel();
    const snippetPanel = store.tabs.find((tab) => tab.name === "Snippets");
    store.createSnippetTab(snippetPanel.id, {
      name: "Snippet 1",
      id: "snippet-id",
      text: "Snippet Text",
      id_parent: "parent-id",
    });
    const tab = store
      .getSecondaryTabs(snippetPanel.id)
      .find((tab) => tab.name === "Snippet 1");
    expect(tab).toBeTruthy();
    expect(tab.component).toBe("SnippetTab");
    expect(tab.metaData.snippetObject).toEqual({
      id: "snippet-id",
      name: "Snippet 1",
      text: "Snippet Text",
      parent: "parent-id",
      type: "snippet",
    });
    expect(store.getPrimaryTabById(snippetPanel.id).metaData.selectedTab).toBe(
      tab
    );
  });

  it("should create a Monitoring Dashboard tab", async () => {
    const store = useTabsStore();
    await store.createWorkspaceTab(0);
    store.createMonitoringDashboardTab();
    const tab = store.selectedPrimaryTab.metaData.secondaryTabs.find(
      (tab) => tab.name === "Monitoring"
    );
    expect(tab).toBeTruthy();
    expect(tab.component).toBe("MonitoringDashboard");
  });

  it("should create a Configuration tab", () => {
    const store = useTabsStore();
    store.createConfigurationTab();
    const tab = store.tabs.find((tab) => tab.name === "Configuration");
    expect(tab).toBeTruthy();
    expect(tab.component).toBe("ConfigTab");
    expect(store.selectedPrimaryTab).toBe(tab);
  });

  it("should create a Utility tab", () => {
    const store = useTabsStore();
    store.createUtilityTab(
      { title: "Test Table", data: { type: "table" } },
      "testDatabase",
      "Backup",
      "objects"
    );
    const tab = store.tabs.find(
      (tab) => tab.name === "Backup (table:Test Table)"
    );
    expect(tab).toBeTruthy();
    expect(tab.component).toBe("BackupTab");
    expect(store.selectedPrimaryTab).toBe(tab);
  });

  it("should create an ERD tab with schema arg provided", async () => {
    const store = useTabsStore();
    await store.createWorkspaceTab(0);
    store.selectedPrimaryTab.metaData.selectedDatabase = "TestDatabase";
    store.createERDTab("TestSchema");
    const tab = store.selectedPrimaryTab.metaData.secondaryTabs.find(
      (tab) => tab.name === "ERD: TestDatabase@TestSchema"
    );
    expect(tab).toBeTruthy();
    expect(tab.component).toBe("ERDTab");
  });

  it("should create an SQLite ERD tab without schema arg provided", async () => {
    const store = useTabsStore();
    await store.createWorkspaceTab(0);
    store.selectedPrimaryTab.metaData.selectedDBMS = "sqlite";
    store.selectedPrimaryTab.metaData.selectedDatabase = "/tmp/test.db";
    store.createERDTab();
    const tab = store.selectedPrimaryTab.metaData.secondaryTabs.find(
      (tab) => tab.name === "ERD"
    );
    expect(tab).toBeTruthy();
    expect(tab.component).toBe("ERDTab");
  });

  it("should create one database ERD tab per database without schema arg provided", async () => {
    const store = useTabsStore();
    await store.createWorkspaceTab(0);
    store.selectedPrimaryTab.metaData.selectedDBMS = "postgresql";
    store.selectedPrimaryTab.metaData.selectedDatabase = "TestDatabase";
    store.createERDTab();
    store.createERDTab();
    const tabs = store.selectedPrimaryTab.metaData.secondaryTabs.filter(
      (tab) => tab.name === "ERD: TestDatabase"
    );
    expect(tabs).toHaveLength(1);
    expect(tabs[0].component).toBe("ERDTab");
  });

  it("should create a Data Editor tab", () => {
    const store = useTabsStore();
    const primaryTab = store.addTab({ name: "Primary Tab" });
    store.selectTab(primaryTab);
    store.createDataEditorTab("test_table", "TestSchema");

    const tab = store
      .getSecondaryTabs(primaryTab.id)
      .find((tab) => tab.name === "Edit data: TestSchema.test_table");
    expect(tab).toBeTruthy();
    expect(tab.component).toBe("DataEditorTab");
    expect(store.getPrimaryTabById(primaryTab.id).metaData.selectedTab).toBe(
      tab
    );
  });

  it("should create a Schema Editor tab", () => {
    const store = useTabsStore();
    const primaryTab = store.addTab({ name: "Primary Tab" });
    store.selectTab(primaryTab);
    store.selectedPrimaryTab.metaData.selectedDBMS = "mysql";
    const nodeMock = {
      title: "test_table",
      data: { schema: "TestSchema", database: "TestDB" },
    };
    store.createSchemaEditorTab(
      nodeMock.title,
      nodeMock.data.database,
      operationModes.CREATE,
    );

    const tab = store.getSecondaryTabs(primaryTab.id).find((tab) => tab.name === "New Table");
    expect(tab).toBeTruthy();
    expect(tab.component).toBe("SchemaEditorTab");
  });

  it("should create a Monitoring tab", async () => {
    const store = useTabsStore();
    await store.createWorkspaceTab(0);
    store.createMonitoringTab("Backends", "SELECT * FROM backends");
    const tab = store.selectedPrimaryTab.metaData.secondaryTabs.find(
      (tab) => tab.name === "Backends"
    );
    expect(tab).toBeTruthy();
    expect(tab.component).toBe("MonitoringTab");
  });
});
