import { mount } from "@vue/test-utils";
import mixin from "../../src/mixins/file_input_mixin";
import {
  describe,
  test,
  expect,
  vi,
  beforeEach,
  afterEach,
  beforeAll,
} from "vitest";
import { showToast } from "@src/notification_control";
import { maxFileSizeInKB, maxFileSizeInMB } from "../../src/constants";
import { useTabsStore } from "../../src/stores/tabs";

vi.mock("@src/notification_control", () => ({
  showToast: vi.fn(),
}));

describe("File Input Mixin", () => {
  let wrapper, tabsStore, snippetTab;

  beforeAll(() => {
    tabsStore = useTabsStore();
    const snippetPanel = tabsStore.addTab({ name: "Snippets" });
    snippetTab = tabsStore.addTab({
      parentId: snippetPanel.id,
      name: "SnippetTab",
    });
    tabsStore.selectTab(snippetTab);
  });

  beforeEach(() => {
    vi.unstubAllGlobals();
    wrapper = mount({
      mixins: [mixin],
      template: `<div></div>`,
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });
  test("handles valid file type", () => {
    const fileReaderSpy = vi
      .spyOn(FileReader.prototype, "readAsText")
      .mockImplementation(() => null);

    const fileMock = new File(["content"], "example.sql", {
      type: "application/sql",
    });

    const eventMock = { target: { files: [fileMock] } };

    wrapper.vm.handleFileInputChange(eventMock);

    expect(fileReaderSpy).toHaveBeenCalledWith(eventMock.target.files[0]);
  });

  test("handles invalid file type", () => {
    const fileMock = new File(["content"], "example.jpg", {
      type: "image/jpeg",
    });
    const eventMock = { target: { files: [fileMock] } };
    wrapper.vm.handleFileInputChange(eventMock);
    expect(showToast).toHaveBeenCalledWith(
      "error",
      "File with type 'image/jpeg' is not supported."
    );
  });

  test("handles file size within limit", () => {
    const fileReaderSpy = vi
      .spyOn(FileReader.prototype, "readAsText")
      .mockImplementation(() => null);
    const fileMock = new File(["content"], "example.txt", {
      type: "text/plain",
    });
    Object.defineProperty(fileMock, "size", { value: 1024 }); // 1KB
    const eventMock = { target: { files: [fileMock] } };
    wrapper.vm.handleFileInputChange(eventMock);

    expect(fileReaderSpy).toHaveBeenCalledWith(eventMock.target.files[0]);
    expect(fileReaderSpy).toBeCalledTimes(1);
  });

  test("handles file size exceeds limit", () => {
    const fileMock = new File(["content"], "example.txt", {
      type: "text/plain",
    });
    Object.defineProperty(fileMock, "size", { value: maxFileSizeInKB + 1024 });
    const eventMock = { target: { files: [fileMock] } };
    wrapper.vm.handleFileInputChange(eventMock);
    expect(showToast).toHaveBeenCalledWith(
      "error",
      `Please select a file that is ${maxFileSizeInMB}MB or less.`
    );
  });

  test("handles exceptions", () => {
    const preventDefault = vi.fn();
    const stopPropagation = vi.fn();
    const error = new Error("An error occurred");
    const FileReader = vi.fn(function () {
      return {
        readAsText: vi.fn(() => {
          throw error;
        }),
      };
    });
    vi.stubGlobal("FileReader", FileReader);

    const fileMock = new File(["content"], "example.txt", {
      type: "text/plain",
    });
    const eventMock = {
      target: { files: [fileMock] },
      preventDefault,
      stopPropagation,
    };
    wrapper.vm.handleFileInputChange(eventMock);

    expect(showToast).toHaveBeenCalledWith("error", error);
    expect(preventDefault).toHaveBeenCalled();
    expect(stopPropagation).toHaveBeenCalled();
  });

  test("changes tab title on file change", () => {
    wrapper.unmount();

    wrapper = mount({
      name: "SnippetTab",
      mixins: [mixin],
      template: `<div></div>`,
    });

    const fileMock = new File(["content"], "example.sql", {
      type: "application/sql",
    });

    const eventMock = { target: { files: [fileMock] } };

    wrapper.vm.handleFileInputChange(eventMock);

    expect(snippetTab.name).toEqual(fileMock.name);
  });
});
