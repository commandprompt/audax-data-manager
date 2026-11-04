import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import mixin from "@src/mixins/table_clipboard_copy_mixin";
import { settingsStore } from "@src/stores/stores_initializer";
import { handleError } from "@src/logging/utils";

vi.mock("@src/logging/utils", () => ({
  handleError: vi.fn(),
}));

describe("table clipboard copy mixin", () => {
  let wrapper, copied;

  // Tabulator range data: rows keyed by the index of the column
  const rows = [
    { 0: "1", 1: "alice" },
    { 0: "2", 1: "bob" },
  ];
  const columnNames = ["id", "name"];

  beforeEach(() => {
    settingsStore.$reset();
    settingsStore.csvDelimiter = ",";
    copied = undefined;

    // happy-dom has no execCommand. The fake copies the selected text, like a browser.
    document.execCommand = vi.fn(() => {
      const textArea = document.querySelector("textarea");
      copied = textArea.value.slice(
        textArea.selectionStart,
        textArea.selectionEnd
      );
      return true;
    });

    wrapper = mount({ mixins: [mixin], template: "<div></div>" });
  });

  afterEach(() => {
    wrapper.unmount();
    delete document.execCommand;
    vi.clearAllMocks();
  });

  describe("copyTableData", () => {
    describe("json", () => {
      it("copies the rows as objects with the column names as keys", () => {
        wrapper.vm.copyTableData(rows, "json", columnNames);

        expect(JSON.parse(copied)).toEqual([
          { id: "1", name: "alice" },
          { id: "2", name: "bob" },
        ]);
      });

      it("copies only the columns of the selected range", () => {
        const selectedRows = [{ 1: "alice" }, { 1: "bob" }];

        wrapper.vm.copyTableData(selectedRows, "json", columnNames);

        expect(JSON.parse(copied)).toEqual([{ name: "alice" }, { name: "bob" }]);
      });

      it("renames repeated column names so the values do not overwrite each other", () => {
        wrapper.vm.copyTableData(
          [{ 0: "1", 1: "alice", 2: "bob" }],
          "json",
          ["id", "name", "name"]
        );

        expect(JSON.parse(copied)).toEqual([
          { id: "1", name: "alice", name_2: "bob" },
        ]);
      });
    });

    describe("csv", () => {
      it("copies a header line and one line for each row", () => {
        wrapper.vm.copyTableData(rows, "csv", columnNames);

        expect(copied).toBe("id,name\n1,alice\n2,bob");
      });

      it("separates the values with the CSV delimiter from the settings", () => {
        settingsStore.csvDelimiter = ";";

        wrapper.vm.copyTableData(rows, "csv", columnNames);

        expect(copied).toBe("id;name\n1;alice\n2;bob");
      });
    });

    describe("markdown", () => {
      it("copies a table with each column as wide as its widest value", () => {
        wrapper.vm.copyTableData(rows, "markdown", columnNames);

        expect(copied).toBe(
          [
            "| id | name  |",
            "| -- | ----- |",
            "| 1  | alice |",
            "| 2  | bob   |",
          ].join("\n")
        );
      });

      it("leaves empty values blank", () => {
        wrapper.vm.copyTableData(
          [{ 0: "1", 1: null }],
          "markdown",
          columnNames
        );

        expect(copied).toBe(
          ["| id | name |", "| -- | ---- |", "| 1  |      |"].join("\n")
        );
      });
    });
  });

  describe("copyToClipboard", () => {
    it("copies the text with the browser copy command", () => {
      wrapper.vm.copyToClipboard("some text");

      expect(document.execCommand).toHaveBeenCalledWith("copy");
      expect(copied).toBe("some text");
    });

    it("removes the temporary textarea from the page", () => {
      wrapper.vm.copyToClipboard("some text");

      expect(document.querySelector("textarea")).toBeNull();
    });

    it("reports an error when the browser does not copy the text", () => {
      document.execCommand.mockReturnValue(false);

      wrapper.vm.copyToClipboard("some text");

      expect(handleError).toHaveBeenCalledWith(
        new Error("Could not copy the data to the clipboard.")
      );
      expect(document.querySelector("textarea")).toBeNull();
    });
  });
});
