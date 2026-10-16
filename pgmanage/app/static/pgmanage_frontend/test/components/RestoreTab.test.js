import RestoreTab from "@src/components/RestoreTab.vue";
import UtilityJobs from "@src/components/UtilityJobs.vue";
import { showAlertText } from "@src/notification_control";
import { fileManagerStore } from "@src/stores/stores_initializer";
import { flushPromises, mount } from "@vue/test-utils";
import axios from "axios";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { handleError } from "@src/logging/utils";
import { mockErrorResponse } from "../helpers/fixtures.js";

vi.mock("@src/logging/utils", () => ({
  handleError: vi.fn(),
}));

vi.mock("@src/notification_control", async (importOriginal) => {
  const orig = await importOriginal();
  return { ...orig, showAlertText: vi.fn() };
});

vi.mock("@src/stores/stores_initializer", async (importOriginal) => {
  const orig = await importOriginal();
  return {
    ...orig,
    tabsStore: {
      selectedPrimaryTab: {
        metaData: {
          selectedTab: {
            id: "testTab",
          },
        },
      },
    },
  };
});

describe("RestoreTab.vue", () => {
  let wrapper;
  const props = {
    workspaceId: "testWorkspace",
    tabId: "testTab",
    databaseIndex: 1,
    restoreType: "objects",
    treeNode: {
      data: { type: "table", database: "testDB", schema: "public" },
      title: "testTable",
    },
  };

  beforeEach(() => {
    axios.post.mockResolvedValueOnce({
      data: { data: [] },
    });
    axios.get.mockResolvedValue({
      data: { data: [] },
    });
    axios.post.mockReturnValueOnce(new Promise(() => {}));
    wrapper = mount(RestoreTab, {
      props: props,
    });
  });

  it("renders correctly with required props", () => {
    expect(wrapper.exists()).toBeTruthy();

    expect(wrapper.findComponent(UtilityJobs).exists()).toBeTruthy();
    expect(wrapper.find(".backup-tab-scrollable").exists()).toBeTruthy();
  });

  it('renders the correct options for "server" restore type', async () => {
    await wrapper.setProps({ restoreType: "server" });
    expect(
      wrapper.find(`#${props.tabId}_restoreOptionsEchoQueries`).exists()
    ).toBeTruthy();
    expect(
      wrapper
        .find(`#${props.tabId}_restoreOptionsIncludeCreateDatabase`)
        .exists()
    ).toBeFalsy();
    expect(
      wrapper.find(`#${props.tabId}_restoreOptionsPreData`).exists()
    ).toBeFalsy();
    expect(wrapper.find("#restoreRoleName").exists()).toBeFalsy();
    expect(wrapper.find("#restoreNumberOfJobs").exists()).toBeFalsy();
  });

  it("renders the correct options for other restore types", async () => {
    expect(
      wrapper.find(`#${props.tabId}_restoreOptionsEchoQueries`).exists()
    ).toBeFalsy();
    expect(
      wrapper
        .find(`#${props.tabId}_restoreOptionsIncludeCreateDatabase`)
        .exists()
    ).toBeTruthy();
    expect(
      wrapper.find(`#${props.tabId}_restoreOptionsPreData`).exists()
    ).toBeTruthy();
    expect(wrapper.find("#restoreRoleName").exists()).toBeTruthy();
    expect(wrapper.find("#restoreNumberOfJobs").exists()).toBeTruthy();
  });

  it("renders the role names in a dropdown", async () => {
    await wrapper.setData({ roleNames: ["admin", "user", "guest"] });
    const roleSelect = wrapper.find("#restoreRoleName");
    expect(roleSelect.exists()).toBeTruthy();
    const options = roleSelect.findAll("option");
    expect(options).toHaveLength(4);
    expect(options.at(1).text()).toBe("admin");
    expect(options.at(2).text()).toBe("user");
    expect(options.at(3).text()).toBe("guest");
  });

  it("should render Revert Settings, Preview, and Restore buttons as disabled initially", () => {
    const revertSettingsButton = wrapper.find(
      '[data-testid="revert-settings-button"]'
    );
    const previewButton = wrapper.find('[data-testid="preview-button"]');
    const restoreButton = wrapper.find('[data-testid="restore-button"]');

    expect(revertSettingsButton.exists()).toBeTruthy();
    expect(previewButton.exists()).toBeTruthy();
    expect(restoreButton.exists()).toBeTruthy();

    expect(revertSettingsButton.classes("disabled")).toBeTruthy();
    expect(previewButton.classes("disabled")).toBeTruthy();
    expect(restoreButton.classes("disabled")).toBeTruthy();
  });

  it("enables Revert Settings when a value changes in the select element", async () => {
    const selectElement = wrapper.find("#restoreNumberOfJobs");
    const revertSettingsButton = wrapper.find(
      '[data-testid="revert-settings-button"]'
    );
    const previewButton = wrapper.find('[data-testid="preview-button"]');
    const restoreButton = wrapper.find('[data-testid="restore-button"]');

    await selectElement.setValue("2");

    expect(revertSettingsButton.classes("disabled")).toBeFalsy();
    expect(previewButton.classes("disabled")).toBeTruthy();
    expect(restoreButton.classes("disabled")).toBeTruthy();
  });

  it("enables Restore and Preview buttons when the backup file name changes", async () => {
    const previewButton = wrapper.find('[data-testid="preview-button"]');
    const restoreButton = wrapper.find('[data-testid="restore-button"]');

    await wrapper.setData({ restoreOptions: { fileName: "new_backup.sql" } });

    expect(previewButton.classes("disabled")).toBeFalsy();
    expect(restoreButton.classes("disabled")).toBeFalsy();
  });

  it("disables Revert Settings, Restore, and Preview buttons on Revert Settings click", async () => {
    const revertSettingsButton = wrapper.find(
      '[data-testid="revert-settings-button"]'
    );
    const previewButton = wrapper.find('[data-testid="preview-button"]');
    const restoreButton = wrapper.find('[data-testid="restore-button"]');

    await wrapper.setData({ restoreOptions: { fileName: "new_backup.sql" } });

    expect(revertSettingsButton.classes("disabled")).toBeFalsy();
    expect(previewButton.classes("disabled")).toBeFalsy();
    expect(restoreButton.classes("disabled")).toBeFalsy();

    await revertSettingsButton.trigger("click");

    expect(revertSettingsButton.classes("disabled")).toBeTruthy();
    expect(previewButton.classes("disabled")).toBeTruthy();
    expect(restoreButton.classes("disabled")).toBeTruthy();
  });

  it("calls getRoleNames and updates roleNames on success", async () => {
    const mockRoles = {
      data: { data: [{ name: "role1" }, { name: "role2" }] },
    };
    axios.post.mockResolvedValueOnce(mockRoles);

    await wrapper.vm.getRoleNames();
    await flushPromises();
    expect(axios.post).toHaveBeenCalledWith("/get_roles_postgresql/", {
      database_index: props.databaseIndex,
      workspace_id: props.workspaceId,
    });
    expect(wrapper.vm.roleNames).toEqual(["role1", "role2"]);
  });

  it("calls getRoleNames and shows an error toast on failure", async () => {
    const errorResponse = mockErrorResponse("Error fetching roles");
    axios.post.mockRejectedValueOnce(errorResponse);

    await wrapper.vm.getRoleNames();
    await flushPromises();

    expect(handleError).toHaveBeenCalledWith(errorResponse);
  });

  it("calls createRestore and starts a job on success", async () => {
    const mockResponse = { data: { job_id: 123, description: "Restore Job" } };
    axios.post.mockResolvedValueOnce(mockResponse);
    const startJobSpy = vi.spyOn(wrapper.vm.$refs.jobs, "startJob");

    await wrapper.vm.createRestore();
    await flushPromises();

    expect(axios.post).toHaveBeenCalledWith("/restore/", {
      database_index: props.databaseIndex,
      workspace_id: props.workspaceId,
      data: wrapper.vm.restoreOptions,
    });
    expect(startJobSpy).toHaveBeenCalledWith(123, "Restore Job");
  });

  it("calls createRestore and shows an error toast on failure", async () => {
    const errorResponse = mockErrorResponse("Error restoring backup");
    axios.post.mockRejectedValueOnce(errorResponse);

    await wrapper.vm.createRestore();
    await flushPromises();

    expect(handleError).toHaveBeenCalledWith(errorResponse);
  });

  it("updates fileName in changeFilePath", () => {
    wrapper.vm.changeFilePath("/new/path/to/file.sql");

    expect(wrapper.vm.restoreOptions.fileName).toBe("/new/path/to/file.sql");
  });

  it("calls openFileManagerModal and shows the modal", () => {
    const showModalSpy = vi.spyOn(fileManagerStore, "showModal");
    wrapper.vm.openFileManagerModal();

    expect(showModalSpy).toHaveBeenCalledWith(
      undefined,
      wrapper.vm.onFile,
      wrapper.vm.dialogType,
      "Choose a backup to restore",
    );
  });

  it("resets restoreOptions to default", () => {
    wrapper.vm.restoreOptions.fileName = "custom.sql";

    wrapper.vm.resetToDefault();

    expect(wrapper.vm.restoreOptions).toEqual(wrapper.vm.restoreOptionsDefault);
  });

  it("calls previewCommand and shows the command on success", async () => {
    const mockResponse = { data: { command: { cmd: "pg_restore command" } } };
    axios.post.mockResolvedValueOnce(mockResponse);

    await wrapper.vm.previewCommand();
    await flushPromises();

    expect(axios.post).toHaveBeenCalledWith("/restore/preview_command/", {
      database_index: props.databaseIndex,
      workspace_id: props.workspaceId,
      data: wrapper.vm.restoreOptions,
    });
    expect(showAlertText).toHaveBeenCalledWith("pg_restore command");
  });

  it("shows the previewed command via the text-safe alert, never the HTML one", async () => {
    const payload = '"><img src=x onerror=alert(1)>';
    axios.post.mockResolvedValueOnce({ data: { command: { cmd: payload } } });

    await wrapper.vm.previewCommand();
    await flushPromises();

    expect(showAlertText).toHaveBeenCalledWith(payload);
  });

  it("calls previewCommand and shows an error toast on failure", async () => {
    const errorResponse = mockErrorResponse("Error previewing command");
    axios.post.mockRejectedValueOnce(errorResponse);

    await wrapper.vm.previewCommand();
    await flushPromises();

    expect(handleError).toHaveBeenCalledWith(errorResponse);
  });

  it("changes restoreOptions.fileName on FileManager store 'changeFile' action", async () => {
    const previewButton = wrapper.find('[data-testid="preview-button"]');
    expect(previewButton.classes("disabled")).toBeTruthy();
    const file = { path: "/new/path/to/file.sql" };
    fileManagerStore.changeFile(file);

    await flushPromises();
    expect(wrapper.vm.restoreOptions.fileName).toEqual(file["path"]);
    expect(previewButton.classes("disabled")).toBeFalsy();
  });
});
