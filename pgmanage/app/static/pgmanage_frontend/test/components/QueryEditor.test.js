import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach } from "vitest";
import QueryEditor from "@src/components/QueryEditor.vue";
import { SQLAutocomplete } from "sql-autocomplete";
import ContextMenu from "@imengyu/vue3-context-menu";
import { format } from "sql-formatter";
import { showToast } from "@src/notification_control";
import { emitter } from "@src/emitter";
import { dbMetadataStore } from "@src/stores/stores_initializer";

vi.mock("@imengyu/vue3-context-menu", () => ({
  default: { showContextMenu: vi.fn() },
}));
vi.mock("sql-formatter", () => ({ format: vi.fn(() => "FORMATTED") }));
vi.mock("@src/ace_extras/plugins", () => ({
  setupAceDragDrop: vi.fn(),
  setupAceSelectionHighlight: vi.fn(),
}));
vi.mock("@src/notification_control", () => ({
  showToast: vi.fn(),
}));

vi.mock("@src/stores/stores_initializer", () => ({
  snippetsStore: { files: [], folders: [] },
  settingsStore: {
    editorTheme: "omnidb",
    $subscribe: vi.fn(),
  },
  dbMetadataStore: {
    fetchDbMeta: vi.fn(() => Promise.resolve()),
    getDbMeta: vi.fn(() => [
      {
        name: "public",
        tables: [
          { name: "users", columns: [{ name: "id" }, { name: "email" }] },
          { name: "orders", columns: [{ name: "id" }, { name: "user_id" }] },
        ],
        views: [],
      },
    ]),
    $onAction: vi.fn(),
  },
}));

const aceMockEditor = {
  on: vi.fn(),
  session: {
    getLength: vi.fn(() => 3),
    setMode: vi.fn(),
  },
  selection: { getRange: vi.fn(() => ({ start: { row: 5 } })) },
  setTheme: vi.fn(),
  setFontSize: vi.fn(),
  setReadOnly: vi.fn(),
  setShowPrintMargin: vi.fn(),
  setValue: vi.fn(),
  clearSelection: vi.fn(),
  gotoLine: vi.fn(),
  insert: vi.fn(),
  focus: vi.fn(),
  resize: vi.fn(),
  execCommand: vi.fn(),
  commands: { bindKey: vi.fn() },
  setOptions: vi.fn(),
  getValue: vi.fn(() => "SELECT * FROM test;"),
  getSelectedText: vi.fn(() => "SELECT 1"),
};

global.ace = { edit: vi.fn(() => aceMockEditor) };

describe("QueryEditor.vue", () => {
  let wrapper;

  beforeEach(() => {
    vi.clearAllMocks();
    wrapper = mount(QueryEditor, {
      props: {
        tabId: "tab1",
        workspaceId: "ws1",
        dialect: "postgresql",
        databaseIndex: 1,
        databaseName: "mydb",
      },
    });
  });

  it("initializes ace editor on mount", () => {
    expect(global.ace.edit).toHaveBeenCalled();
    expect(wrapper.vm.editor.setTheme).toHaveBeenCalledWith("ace/theme/omnidb");
    expect(wrapper.vm.editor).toBeDefined();
  });

  it("fetches db meta with workspace id and tab id on mount", () => {
    expect(dbMetadataStore.fetchDbMeta).toHaveBeenCalledWith(1, "ws1", "mydb", "tab1");
  });

  it("emits editorChange on content change", () => {
    const handler = wrapper.vm.editor.on.mock.calls.find(([event]) => event === "change")[1];
    handler();
    expect(wrapper.emitted("editorChange")).toBeTruthy();
  });

  it("computes autocompleteMode correctly", async () => {
    await wrapper.setProps({ tabMode: "query" });
    expect(wrapper.vm.autocompleteMode).toBe(0);
    await wrapper.setProps({ tabMode: "console" });
    expect(wrapper.vm.autocompleteMode).toBe(1);
  });

  it("readOnly watcher updates editor readonly", async () => {
    await wrapper.setProps({ readOnly: true });
    expect(wrapper.vm.editor.setReadOnly).toHaveBeenCalledWith(true);
  });

  it("autocomplete watcher updates editor options", async () => {
    await wrapper.setProps({ autocomplete: false });
    expect(wrapper.vm.editor.setOptions).toHaveBeenCalled();
  });

  it("setupEditor binds shortcuts and sets options", () => {
    wrapper.vm.setupEditor();
    expect(wrapper.vm.editor.setOptions).toHaveBeenCalledWith(
      expect.objectContaining({
        enableBasicAutocompletion: expect.any(Array),
        enableHoverLinking: true,
      })
    );
  });

  it("setupCompleter creates SQLAutocomplete when dbMeta exists", () => {
    wrapper.vm.setupCompleter();
    expect(wrapper.vm.completer).toBeInstanceOf(SQLAutocomplete);
  });

  it("getEditorContent returns full or selected content", () => {
    aceMockEditor.getSelectedText.mockReturnValueOnce("SEL");
    expect(wrapper.vm.getEditorContent(true, false)).toContain("SELECT");
    expect(wrapper.vm.getEditorContent(false, true)).toBe("SEL");
  });

  it("getQueryOffset returns current row", () => {
    expect(wrapper.vm.getQueryOffset()).toBe(5);
  });

  it("shows context menu with postgres options", () => {
    aceMockEditor.getSelectedText.mockReturnValue("SELECT 1");
    wrapper.vm.contextMenu({ x: 10, y: 20 });
    expect(ContextMenu.showContextMenu).toHaveBeenCalled();
    const call = ContextMenu.showContextMenu.mock.calls[0][0];
    expect(call.items.some((i) => i.label.includes("Explain"))).toBe(true);
  });

  it("shows context menu without selection disables items", () => {
    aceMockEditor.getSelectedText.mockReturnValue("");
    wrapper.vm.contextMenu({ x: 1, y: 2 });
    const items = ContextMenu.showContextMenu.mock.calls[0][0].items;
    expect(items[0].disabled).toBe(true);
  });

  it("calls format and sets formatted text", () => {
    format.mockReturnValue("SELECT 1;");
    wrapper.vm.indentSQL();
    expect(aceMockEditor.setValue).toHaveBeenCalledWith("SELECT 1;");
  });

  it("shows toast if too many lines", () => {
    aceMockEditor.session.getLength.mockReturnValueOnce(99999);
    wrapper.vm.indentSQL();
    expect(showToast).toHaveBeenCalled();
  });

  it("should unregister emitter events", () => {
    const emitterDeleteSpy = vi.spyOn(emitter.all, "delete");
    wrapper.unmount();
    
    expect(emitterDeleteSpy).toHaveBeenCalledWith(`${wrapper.props("tabId")}_find_replace`);
    expect(emitterDeleteSpy).toHaveBeenCalledWith(`${wrapper.props("tabId")}_indent_sql`);
    expect(emitterDeleteSpy).toHaveBeenCalledWith(`${wrapper.props("tabId")}_insert_to_editor`);
    expect(emitterDeleteSpy).toHaveBeenCalledWith(`${wrapper.props("tabId")}_copy_to_editor`);
    expect(emitterDeleteSpy).toHaveBeenCalledWith(`${wrapper.props("tabId")}_show_autocomplete_results`);
  });

  it("focus calls editor.focus", () => {
    wrapper.vm.focus();
    expect(aceMockEditor.focus).toHaveBeenCalled();
  });
  it("executes startAutocomplete when receiving show_autocomplete_results event", async () => {
    emitter.emit(`${wrapper.props("tabId")}_show_autocomplete_results`);

    expect(aceMockEditor.execCommand).toHaveBeenCalledWith("startAutocomplete");
  });

  it("sets value and resets selection on copy_to_editor event", async () => {
  emitter.emit(`${wrapper.props("tabId")}_copy_to_editor`, "SELECT 1");

  expect(aceMockEditor.setValue).toHaveBeenCalledWith("SELECT 1");
  expect(aceMockEditor.clearSelection).toHaveBeenCalled();
  expect(aceMockEditor.gotoLine).toHaveBeenCalled();
});

it("inserts text and clears selection on insert_to_editor event", async () => {
  emitter.emit(`${wrapper.props("tabId")}_insert_to_editor`, "WHERE id = 1");

  expect(aceMockEditor.insert).toHaveBeenCalledWith("WHERE id = 1");
  expect(aceMockEditor.clearSelection).toHaveBeenCalled();
});

it("calls indentSQL and formats content", async () => {
  const indentSQLSpy = vi.spyOn(wrapper.vm, "indentSQL")
  emitter.emit(`${wrapper.props("tabId")}_indent_sql`);

  expect(format).toHaveBeenCalled();
  expect(indentSQLSpy).toHaveBeenCalled();
});
it("executes find command on find_replace event", async () => {
  emitter.emit(`${wrapper.props("tabId")}_find_replace`);

  expect(aceMockEditor.execCommand).toHaveBeenCalledWith("find");
});
});
