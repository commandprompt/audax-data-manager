import { flushPromises, mount } from "@vue/test-utils";
import SettingsModal from "@src/components/SettingsModal.vue";
import { useSettingsStore } from "@src/stores/settings";
import { vi, describe, beforeEach, afterEach, it, expect } from "vitest";
import axios from "axios";
import { Tab } from "bootstrap";

vi.mock("@src/notification_control", () => {
  const showToast = vi.fn();
  return {
    showToast,
  };
});

describe("SettingsModal.vue", () => {
  let wrapper, settingsStore;

  beforeEach(() => {
    settingsStore = useSettingsStore();
    settingsStore.$reset();
    wrapper = mount(SettingsModal, {
      shallow: true,
    });
  });

  afterEach(() => {
    wrapper.unmount();
  });

  it("should render settings modal with proper tabs", () => {
    expect(wrapper.find("#settings_shortcuts-tab").exists()).toBe(true);
    expect(wrapper.find("#settings_options-tab").exists()).toBe(true);
    expect(wrapper.find("#settings_password-tab").exists()).toBe(true);
  });

  it("should show password tab only if desktopMode is false", async () => {
    settingsStore.desktopMode = false;
    await flushPromises();
    expect(wrapper.find("#settings_password-tab").exists()).toBe(true);
    settingsStore.desktopMode = true;
    await flushPromises();
    expect(wrapper.find("#settings_password-tab").exists()).toBe(false);
  });

  it("should call resetUnsavedSettings when close button is clicked", async () => {
    const resetUnsavedSettingsSpy = vi.spyOn(
      wrapper.vm,
      "resetUnsavedSettings"
    );
    await wrapper.find(".btn-close").trigger("click");
    expect(resetUnsavedSettingsSpy).toHaveBeenCalled();
  });

  it("should render encoding values and select the correct one", async () => {
    const encodingOptions = wrapper.findAll("#sel_csv_encoding option");
    const selectEl = wrapper.find("#sel_csv_encoding");
    expect(encodingOptions.length).toBe(wrapper.vm.encodingValues.length);
    expect(wrapper.vm.csvEncoding).toBe(settingsStore.csvEncoding);
    await selectEl.setValue("utf-8");
    expect(wrapper.vm.csvEncoding).toBe("utf-8");
  });

  it("should validate csv delimiter input correctly", async () => {
    const input = wrapper.find("#txt_csv_delimiter");
    await input.setValue("a");
    expect(wrapper.vm.v$.csvDelimiter.$invalid).toBe(false);

    await input.setValue("ab");
    expect(wrapper.vm.v$.csvDelimiter.$invalid).toBe(true);
  });

  it("should correctly format date preview based on selected date format", async () => {
    const dateFormatSelect = wrapper.find("#date_format");
    const preview = wrapper.find("p.fw-bold");
    const selectEl = dateFormatSelect.element;
    selectEl.selectedIndex = 1;
    selectEl.dispatchEvent(new Event("change"));
    await flushPromises();
    expect(preview.text()).toMatch(
      /^\d{2}\/\d{1,2}\/\d{4}, \d{1,2}:\d{2}:\d{2} (AM|PM)$/ // MM/D/YYYY, h:mm:ss A
    );

    selectEl.selectedIndex = 0;
    selectEl.dispatchEvent(new Event("change"));
    await flushPromises();
    expect(preview.text()).toMatch(/^\d{4}-\d{2}-\d{2}, \d{1,2}:\d{2}:\d{2}$/); // YYYY-MM-DD, HH:mm:ss

    selectEl.selectedIndex = 2;
    selectEl.dispatchEvent(new Event("change"));
    await flushPromises();
    expect(preview.text()).toMatch(
      /^[A-Za-z]{3} \d{1,2} \d{4}, \d{1,2}:\d{2}:\d{2} (AM|PM)$/ // MMM D YYYY, h:mm:ss A
    );
  });

  it("should handle the validation of PostgreSQL binary paths", async () => {
    settingsStore.binaryPaths = { "pg-16": "/usr/bin" };
    const tab = await wrapper.find("#settings-paths-tab");
    Tab.getOrCreateInstance(tab.element).show();

    await flushPromises();
    const validateBinaryPathSpy = vi.spyOn(wrapper.vm, "validateBinaryPath");
    const validateButton = wrapper.find(
      '[data-testid="validate-binary-path-button"]'
    );
    axios.post.mockResolvedValue({ data: { data: "test data" } });
    await validateButton.trigger("click");
    expect(validateBinaryPathSpy).toHaveBeenCalledWith(
      wrapper.vm.binaryPaths["pg-16"],
      "postgres",
    );
  });

  it("should handle theme changes correctly", async () => {
    await wrapper.find("#sel_theme").setValue("dark");
    expect(settingsStore.theme).toBe("dark");
    await wrapper.find("#sel_theme").setValue("light");
    expect(settingsStore.theme).toBe("light");
  });

  it("should apply font size changes correctly", async () => {
    wrapper.vm.changeInterfaceFontSize = vi.fn();
    await wrapper.find("#sel_interface_font_size").setValue("14");
    expect(settingsStore.fontSize).toBe(14);

    await wrapper.find("#sel_interface_font_size").setValue("12");

    expect(settingsStore.fontSize).toBe(12);
  });
});
