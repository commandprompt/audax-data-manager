import { setActivePinia, createPinia } from "pinia";
import { describe, it, expect, beforeEach, vi } from "vitest";
import { settingsStore } from "@src/stores/stores_initializer";
import axios from "axios";
import { showToast } from "@src/notification_control";
import moment from "moment";
import { Modal } from "bootstrap";
import { handleError } from "@src/logging/utils";

vi.mock("@src/logging/utils", () => ({
  handleError: vi.fn(),
}));

vi.mock("@src/notification_control", () => ({
  showToast: vi.fn(),
}));

vi.mock("bootstrap", () => ({
  Modal: {
    getOrCreateInstance: vi.fn(() => ({
      show: vi.fn(),
    })),
  },
  Tab: vi.fn(function () {
    return { show: vi.fn() };
  }),
}));

describe("settings store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    settingsStore.$reset();
  });

  it("initializes with default state", () => {
    const store = settingsStore;
    expect(store.desktopMode).toBe(window.gv_desktopMode);
    expect(store.fontSize).toBe("");
    expect(store.theme).toBe("");
    expect(store.editorTheme).toBe("");
    expect(store.terminalTheme).toBe("");
    expect(store.restoreTabs).toBe("");
    expect(store.scrollTree).toBe("");
    expect(store.binaryPaths).toEqual({});
    expect(store.pigzPath).toBe("");
    expect(store.csvEncoding).toBe("");
    expect(store.csvDelimiter).toBe("");
    expect(store.dateFormat).toBe("");
    expect(store.shortcuts).toEqual({});
    expect(store.currentOS).toBe("Unknown OS");
  });

  it("fetches settings and updates state", async () => {
    const store = settingsStore;
    axios.get.mockResolvedValue({
      data: {
        settings: {
          font_size: "16",
          theme: "dark",
          editor_theme: "monokai",
          restore_tabs: true,
          scroll_tree: false,
          binary_paths: { "pg-16": "/usr/bin" },
          pigz_path: "/usr/local/bin",
          csv_encoding: "UTF-8",
          csv_delimiter: ",",
          date_format: "YYYY-MM-DD",
        },
        shortcuts: { copy: "Ctrl+C" },
      },
    });

    const response = await store.getSettings();
    expect(response).toEqual({
      settings: {
        font_size: "16",
        theme: "dark",
        editor_theme: "monokai",
        restore_tabs: true,
        scroll_tree: false,
        binary_paths: { "pg-16": "/usr/bin" },
        pigz_path: "/usr/local/bin",
        csv_encoding: "UTF-8",
        csv_delimiter: ",",
        date_format: "YYYY-MM-DD",
      },
      shortcuts: { copy: "Ctrl+C" },
    });

    expect(store.fontSize).toBe("16");
    expect(store.theme).toBe("dark");
    expect(store.editorTheme).toBe("monokai");
    expect(store.restoreTabs).toBe(true);
    expect(store.scrollTree).toBe(false);
    expect(store.binaryPaths).toEqual({ "pg-16": "/usr/bin" });
    expect(store.pigzPath).toBe("/usr/local/bin");
    expect(store.csvEncoding).toBe("UTF-8");
    expect(store.csvDelimiter).toBe(",");
    expect(store.dateFormat).toBe("YYYY-MM-DD");
    expect(store.shortcuts).toEqual({ copy: "Ctrl+C" });
    expect(moment.defaultFormat).toBe("YYYY-MM-DD");
    expect(document.documentElement.style.fontSize).toBe("16px");
  });

  it("uses default date format during fetch settings", async () => {
    const store = settingsStore;
    axios.get.mockResolvedValue({
      data: {
        settings: {
          font_size: "16",
          theme: "dark",
          editor_theme: "monokai",
          restore_tabs: true,
          scroll_tree: false,
          binary_path: "/usr/bin",
          pigz_path: "/usr/local/bin",
          csv_encoding: "UTF-8",
          csv_delimiter: ",",
        },
        shortcuts: { copy: "Ctrl+C" },
      },
    });

    const response = await store.getSettings();

    expect(store.dateFormat).toBe("YYYY-MM-DD, HH:mm:ss");
    expect(moment.defaultFormat).toBe("YYYY-MM-DD, HH:mm:ss");
  });

  it("handles error in getSettings", async () => {
    const errorResponse = {
      response: {
        data: { data: "Error message" },
      },
    };
    const store = settingsStore;
    axios.get.mockRejectedValue(errorResponse);

    const response = await store.getSettings();
    expect(response.response.data.data).toBe("Error message");
    expect(handleError).toHaveBeenCalledWith(errorResponse);
  });

  it("saves settings and shows success toast", async () => {
    const store = settingsStore;
    store.fontSize = "16";
    store.theme = "dark";
    store.csvEncoding = "UTF-8";
    store.csvDelimiter = ",";
    store.binaryPath = "/usr/bin";
    store.dateFormat = "YYYY-MM-DD";
    store.pigzPath = "/usr/local/bin";
    store.restoreTabs = true;
    store.scrollTree = false;
    store.currentOS = "Linux";
    store.shortcuts = { copy: "Ctrl+C" };

    axios.post.mockResolvedValue({
      data: "Success",
    });

    const response = await store.saveSettings();
    expect(response).toBe("Success");
    expect(showToast).toHaveBeenCalledWith("success", "Configuration saved.");
    expect(moment.defaultFormat).toBe("YYYY-MM-DD");
  });

  it("handles error in saveSettings", async () => {
    const errorResponse = {
      response: {
        data: { data: "Error message" },
      },
    };
    const store = settingsStore;
    axios.post.mockRejectedValue(errorResponse);

    const response = await store.saveSettings();
    expect(response.response.data.data).toBe("Error message");
    expect(handleError).toHaveBeenCalledWith(errorResponse);
  });

  it("sets fontSize", () => {
    const store = settingsStore;
    store.setFontSize("16");
    expect(store.fontSize).toBe("16");
  });

  it("sets theme", () => {
    const store = settingsStore;
    store.setTheme("dark");
    expect(store.theme).toBe("dark");
  });

  it("sets editorTheme", () => {
    const store = settingsStore;
    store.setEditorTheme("monokai");
    expect(store.editorTheme).toBe("monokai");
  });

  it("sets terminalTheme", () => {
    const store = settingsStore;
    store.setTerminalTheme("monokai");
    expect(store.terminalTheme).toBe("monokai");
  });

  it("sets shortcuts", () => {
    const store = settingsStore;
    store.setShortcuts({ copy: "Ctrl+C" });
    expect(store.shortcuts).toEqual({ copy: "Ctrl+C" });
  });

  it("sets csvEncoding", () => {
    const store = settingsStore;
    store.setCSVEncoding("UTF-8");
    expect(store.csvEncoding).toBe("UTF-8");
  });

  it("sets csvDelimiter", () => {
    const store = settingsStore;
    store.setCSVDelimiter(",");
    expect(store.csvDelimiter).toBe(",");
  });

  it("sets binaryPaths", () => {
    const store = settingsStore;
    store.setBinaryPaths({ "pg-13": "/usr/bin" });
    expect(store.binaryPaths).toEqual({ "pg-13": "/usr/bin" });
  });

  it("sets pigzPath", () => {
    const store = settingsStore;
    store.setPigzPath("/usr/local/bin");
    expect(store.pigzPath).toBe("/usr/local/bin");
  });

  it("sets dateFormat", () => {
    const store = settingsStore;
    store.setDateFormat("YYYY-MM-DD");
    expect(store.dateFormat).toBe("YYYY-MM-DD");
  });

  it("sets restoreTabs", () => {
    const store = settingsStore;
    store.setRestoreTabs(true);
    expect(store.restoreTabs).toBe(true);
  });

  it("sets scrollTree", () => {
    const store = settingsStore;
    store.setScrollTree(false);
    expect(store.scrollTree).toBe(false);
  });

  it("shows modal", () => {
    const store = settingsStore;
    store.showModal();
    expect(Modal.getOrCreateInstance).toHaveBeenCalledWith("#modal_settings", {
      backdrop: "static",
    });
  });
});
