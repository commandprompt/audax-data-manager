import { flushPromises, mount } from "@vue/test-utils";
import {
  beforeAll,
  afterEach,
  beforeEach,
  describe,
  expect,
  test,
  vi,
} from "vitest";
import "ace-builds";
import "ace-builds/esm-resolver";
import SnippetTab from "../../src/components/SnippetTab.vue";
import "../../src/ace_extras/themes/theme-omnidb.js";
import { emitter } from "../../src/emitter.js";

import { useSettingsStore } from "../../src/stores/settings.js";
import { useMessageModalStore } from "../../src/stores/message_modal.js";
import { useTabsStore } from "../../src/stores/tabs";
import { showToast } from "@src/notification_control";
import { maxFileSizeInKB, maxFileSizeInMB } from "../../src/constants.js";

vi.mock("@src/notification_control", () => ({
  showToast: vi.fn(),
}));

describe("SnippetTab", () => {
  let wrapper, fileMock, eventMock;
  let settingsStore, messageModalStore;
  const tabId = "uniqueTabID";

  beforeAll(() => {
    const tabsStore = useTabsStore();
    messageModalStore = useMessageModalStore();
    settingsStore = useSettingsStore();
    tabsStore.createSnippetPanel();
    settingsStore.setEditorTheme("omnidb");
  });

  beforeEach(() => {
    wrapper = mount(SnippetTab, {
      props: {
        tabId: tabId,
      },
      attachTo: document.body,
      shallow: true,
    });

    fileMock = new File(["content"], "example.txt", {
      type: "text/plain",
    });

    eventMock = new Event("drop");
  });

  afterEach(() => {
    wrapper.unmount();
  });

  test("should render SnippetTab component with expected elements", () => {
    expect(wrapper.html()).toContain("Indent");
    expect(wrapper.html()).toContain("Save");
  });

  test("should initialize Ace editor with correct configuration", () => {
    const editorInstance = wrapper.vm.editor;

    expect(editorInstance).toBeDefined();
    expect(editorInstance.getTheme()).toBe("ace/theme/omnidb");
    expect(editorInstance.session.getMode().$id).toBe("ace/mode/sql");
  });

  test("should indent SQL when 'Indent' button is clicked", async () => {
    const editorInstance = wrapper.vm.editor;
    editorInstance.setValue("SELECT * FROM table");

    await wrapper
      .find("[data-testid='snippet-tab-indent-button']")
      .trigger("click");

    expect(editorInstance.getValue()).toContain("SELECT\n  *");
  });

  test("should call openFileManagerModal when 'Open file' button is clicked", async () => {
    const openFileManagerModalSpy = vi.spyOn(
      wrapper.vm,
      "openFileManagerModal"
    );
    await wrapper
      .find("[data-testid='snippet-tab-open-file-button']")
      .trigger("click");

    expect(openFileManagerModalSpy).toHaveBeenCalledOnce();
  });

  test("should call saveFile when 'Save to File' button is clicked", async () => {
    const saveFileSpy = vi.spyOn(wrapper.vm, "saveFile");
    const editorInstance = wrapper.vm.editor;
    editorInstance.setValue("SELECT * FROM table");

    await flushPromises();

    await wrapper
      .find("[data-testid='snippet-tab-save-file-button']")
      .trigger("click");

    expect(saveFileSpy).toHaveBeenCalledOnce();
  });

  test("should call saveSnippetText method when 'Save' button is clicked", async () => {
    const saveSnippetTextMock = vi.spyOn(wrapper.vm, "saveSnippetText");

    await wrapper
      .find("[data-testid='snippet-tab-save-button']")
      .trigger("click");

    expect(saveSnippetTextMock).toHaveBeenCalled();
  });

  test("should set 'fileSaveDisabled' to false if snippet.id exists", async () => {
    expect(wrapper.vm.fileSaveDisabled).toBeTruthy();
    wrapper.unmount();

    wrapper = mount(SnippetTab, {
      props: {
        tabId: tabId,
        snippet: {
          id: 1,
        },
      },
      attachTo: document.body,
      shallow: true,
    });

    expect(wrapper.vm.fileSaveDisabled).toBeFalsy();
  });

  describe("Events", () => {
    test("should focus editor on focus event", async () => {
      const editorInstance = wrapper.vm.editor;

      emitter.emit(`${tabId}_editor_focus`);

      expect(editorInstance.isFocused()).toBeTruthy();
    });
    test("should copy snippet to editor on copy event", async () => {
      const editorInstance = wrapper.vm.editor;

      emitter.emit(`${tabId}_copy_to_editor`, "SELECT * FROM table");

      expect(editorInstance.getValue()).toEqual("SELECT * FROM table");
    });
    test("should call handleResize method on resize event", async () => {
      const handleResizeSpy = vi.spyOn(wrapper.vm, "handleResize");

      emitter.emit(`${tabId}_resize`);

      expect(handleResizeSpy).toHaveBeenCalledOnce();
    });
    test("should call handleResize on settingsStore fontsize change", async () => {
      const handleResizeSpy = vi.spyOn(wrapper.vm, "handleResize");
      const editorSetFontSizeSpy = vi.spyOn(wrapper.vm.editor, "setFontSize");
      const fontSize = 14;

      settingsStore.setFontSize(fontSize);

      expect(handleResizeSpy).toHaveBeenCalledOnce();

      expect(editorSetFontSizeSpy).toHaveBeenCalledOnce();
      expect(editorSetFontSizeSpy).toHaveBeenCalledWith(fontSize);
      expect(wrapper.vm.editor.getFontSize()).toEqual(fontSize);
    });

    test("should cleanup events on unmount", () => {
      const clearEventsSpy = vi.spyOn(wrapper.vm, "clearEvents");

      wrapper.unmount();

      expect(clearEventsSpy).toHaveBeenCalled();
    });
  });

  describe("File upload", async () => {
    test("prevents default action for dragover event", () => {
      eventMock = new Event("dragover");
      const preventDefaultSpy = vi.spyOn(eventMock, "preventDefault");

      Object.defineProperty(eventMock, "dataTransfer", {
        value: { types: ["Files"] },
      });
      wrapper.find(".snippet-editor").element.dispatchEvent(eventMock);
      expect(preventDefaultSpy).toHaveBeenCalled();
    });

    test("prevents default action and handles drop event", () => {
      const preventDefaultSpy = vi.spyOn(eventMock, "preventDefault");
      const readerMock = { readAsText: vi.fn(), result: "fileContent" };

      Object.defineProperty(eventMock, "dataTransfer", {
        value: { files: [fileMock], types: ["Files"] },
      });
      Object.defineProperty(window, "FileReader", {
        value: vi.fn(function () {
          return readerMock;
        }),
      });

      wrapper.find(".snippet-editor").element.dispatchEvent(eventMock);

      expect(preventDefaultSpy).toHaveBeenCalled();
      expect(readerMock.readAsText).toHaveBeenCalledWith(fileMock);
    });

    test("handles drop event with invalid file type", () => {
      fileMock = new File(["content"], "example.jpg", {
        type: "image/jpeg",
      });

      Object.defineProperty(eventMock, "dataTransfer", {
        value: { files: [fileMock], types: ["Files"] },
      });

      wrapper.find(".snippet-editor").element.dispatchEvent(eventMock);

      expect(showToast).toHaveBeenCalledWith(
        "error",
        "File with type 'image/jpeg' is not supported."
      );
    });

    test("handles drop event with file size exceeding the limit", () => {
      Object.defineProperty(fileMock, "size", {
        value: maxFileSizeInKB + 1024,
      });

      Object.defineProperty(eventMock, "dataTransfer", {
        value: { files: [fileMock], types: ["Files"] },
      });

      wrapper.find(".snippet-editor").element.dispatchEvent(eventMock);

      expect(showToast).toHaveBeenCalledWith(
        "error",
        `Please drop a file that is ${maxFileSizeInMB}MB or less.`
      );
    });

    test("handles drop event with more than 1 file", () => {
      Object.defineProperty(eventMock, "dataTransfer", {
        value: { files: [fileMock, fileMock], types: ["Files"] },
      });

      wrapper.find(".snippet-editor").element.dispatchEvent(eventMock);

      expect(showToast).toHaveBeenCalledWith(
        "error",
        "Only one file at a time is possible to drop"
      );
    });

    test("handles exceptions", () => {
      const preventDefault = vi.fn();
      const stopPropagation = vi.fn();
      eventMock.preventDefault = preventDefault;
      eventMock.stopPropagation = stopPropagation;
      const error = new Error("An error occurred");

      const readerMock = {
        readAsText: vi.fn(() => {
          throw error;
        }),
        result: "fileContent",
      };

      Object.defineProperty(eventMock, "dataTransfer", {
        value: { files: [fileMock], types: ["Files"] },
      });

      Object.defineProperty(window, "FileReader", {
        value: vi.fn(function () {
          return readerMock;
        }),
      });

      wrapper.find(".snippet-editor").element.dispatchEvent(eventMock);

      expect(showToast).toHaveBeenCalledWith("error", error);
      expect(preventDefault).toHaveBeenCalled();
      expect(stopPropagation).toHaveBeenCalled();
    });

    test("handles drop event when ace editor is not empty", () => {
      wrapper.vm.editor.setValue("test data");
      const messageModalSpy = vi
        .spyOn(messageModalStore, "showModal")
        .mockImplementation(() => null);

      const readerMock = { readAsText: vi.fn(), result: "fileContent" };

      Object.defineProperty(eventMock, "dataTransfer", {
        value: { files: [fileMock], types: ["Files"] },
      });
      Object.defineProperty(window, "FileReader", {
        value: vi.fn(function () {
          return readerMock;
        }),
      });

      wrapper.find(".snippet-editor").element.dispatchEvent(eventMock);

      expect(messageModalSpy).toBeCalled();
    });
  });
});
