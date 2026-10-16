import { mount, flushPromises } from "@vue/test-utils";
import ExtensionModal from "@src/components/ExtensionModal.vue";
import PreviewBox from "@src/components/PreviewBox.vue";
import { Modal } from "bootstrap";
import axios from "axios";
import { vi, describe, it, expect, afterEach, beforeEach } from "vitest";
import { operationModes } from "@src/constants";
import { handleError } from "@src/logging/utils";
import { mockErrorResponse } from "../helpers/fixtures.js";

vi.mock("@src/logging/utils", () => ({
  handleError: vi.fn(),
}));

vi.mock("bootstrap", () => ({
  Modal: vi.fn(function () {
    return { show: vi.fn(), hide: vi.fn() };
  }),
}));

const mountComponent = (props = {}) => {
  return mount(ExtensionModal, {
    props: {
      mode: operationModes.CREATE,
      treeNode: { title: "test_extension" },
      workspaceId: "workspace123",
      databaseIndex: 1,
      ...props,
    },
    shallow: true,
  });
};

describe("ExtensionModal.vue", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    axios.post
      .mockResolvedValue({ data: [] })
      .mockResolvedValueOnce({
        data: { available_extensions: [{ name: "hstore" }] },
      })
      .mockResolvedValueOnce({ data: [] });
  });
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renders the modal with correct title for CREATE mode", () => {
    const wrapper = mountComponent();
    expect(wrapper.find(".modal-title").text()).toBe("Create Extension");
  });

  it("renders the modal with correct title for UPDATE mode", async () => {
    axios.post.mockResolvedValueOnce({ data: { name: "hstore" } });
    const wrapper = mountComponent({
      mode: operationModes.UPDATE,
      treeNode: { title: "hstore" },
    });
    await flushPromises();
    expect(wrapper.find(".modal-title").text()).toBe("hstore");
  });

  it("renders the form inputs", () => {
    const wrapper = mountComponent();
    expect(wrapper.find("#extensionName").exists()).toBe(true);
    expect(wrapper.find("#extensionComment").exists()).toBe(true);
    expect(wrapper.find("#extensionSchema").exists()).toBe(true);
    expect(wrapper.find("#extensionVersions").exists()).toBe(true);
  });

  it("disables schema selection if requiredSchema is set", async () => {
    const wrapper = mountComponent();
    await wrapper.setData({
      selectedExtension: { name: "hstore", required_schema: "public" },
    });
    expect(
      wrapper.find("#extensionSchema").attributes("disabled")
    ).toBeDefined();
  });

  it("updates selectedExtension when selecting an extension", async () => {
    const wrapper = mountComponent();
    await flushPromises();

    const selectEl = wrapper.find("#extensionName").element;
    selectEl.selectedIndex = 1;
    selectEl.dispatchEvent(new Event("change"));

    expect(wrapper.vm.selectedExtension).toStrictEqual({ name: "hstore" });
  });

  it("disables save button when no changes are made", async () => {
    axios.post.mockResolvedValueOnce({ data: { name: "hstore" } });
    const wrapper = mountComponent({ mode: operationModes.UPDATE });

    expect(
      wrapper.find("button.btn-primary").attributes("disabled")
    ).toBeDefined();
  });

  it("enables save button when valid extension is selected", async () => {
    const wrapper = mountComponent();
    await wrapper.setData({
      selectedExtension: { name: "hstore" },
    });
    expect(
      wrapper.find("button.btn-primary").attributes("disabled")
    ).toBeUndefined();
  });

  it("calls getAvailableExtensions and getSchemas on mount", async () => {
    const wrapper = mountComponent();
    expect(axios.post).toHaveBeenCalledWith(
      "/get_available_extensions_postgresql/",
      expect.any(Object)
    );
    expect(axios.post).toHaveBeenCalledWith(
      "/get_schemas_postgresql/",
      expect.any(Object)
    );
  });

  it("handles API error in getSchemas and getAvailableExtensions", async () => {
    const errorResponse = mockErrorResponse("Response error");
    vi.resetAllMocks();
    axios.post.mockRejectedValue(errorResponse);
    const wrapper = mountComponent();
    await flushPromises();

    expect(axios.post).toHaveBeenCalledWith(
      "/get_available_extensions_postgresql/",
      expect.any(Object)
    );
    expect(axios.post).toHaveBeenCalledWith(
      "/get_schemas_postgresql/",
      expect.any(Object)
    );

    expect(handleError).toHaveBeenCalledWith(errorResponse);
  });

  it("displays generated SQL in PreviewBox", async () => {
    const wrapper = mountComponent();
    await wrapper.setData({
      selectedExtension: { name: "hstore" },
    });
    expect(wrapper.findComponent(PreviewBox).props("editorText")).toContain(
      "CREATE EXTENSION hstore"
    );
  });

  it("calls saveExtension on save button click", async () => {
    const wrapper = mountComponent();
    const saveExtensionSpy = vi.spyOn(wrapper.vm, "saveExtension");
    await wrapper.setData({
      selectedExtension: { name: "hstore" },
    });
    await wrapper
      .find('[data-testid="save-extension-button"]')
      .trigger("click");
    expect(saveExtensionSpy).toHaveBeenCalled();
  });

  it("calls axios.post when saving extension", async () => {
    axios.post.mockResolvedValueOnce({ data: {} });
    const wrapper = mountComponent();
    await wrapper.setData({ selectedExtension: { name: "hstore" } });
    await wrapper
      .find('[data-testid="save-extension-button"]')
      .trigger("click");
    expect(axios.post).toHaveBeenCalledWith(
      "/execute_query/",
      expect.any(Object)
    );
  });

  it("closes modal after successful save", async () => {
    const wrapper = mountComponent();
    await wrapper.setData({ selectedExtension: { name: "hstore" } });
    await wrapper
      .find('[data-testid="save-extension-button"]')
      .trigger("click");
    expect(Modal).toHaveBeenCalled();
    expect(wrapper.vm.modalInstance.hide).toHaveBeenCalled();
  });

  it("handles API errors gracefully", async () => {
    axios.post.mockRejectedValueOnce(mockErrorResponse("Error occurred"));
    const wrapper = mountComponent();
    const saveExtensionSpy = vi.spyOn(wrapper.vm, "saveExtension");
    await wrapper.setData({ selectedExtension: { name: "hstore" } });
    await wrapper
      .find('[data-testid="save-extension-button"]')
      .trigger("click");
    expect(saveExtensionSpy).toHaveBeenCalled();
  });
});
