import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import { describe, it, expect } from "vitest";
import SchemaEditorColumnList from "@src/components/SchemaEditorColumnList.vue";
import SearchableDropdown from "@src/components/SearchableDropdown.vue";
import { operationModes } from "@src/constants";

const column = (overrides = {}) => ({
  dataType: "integer",
  name: "id",
  defaultValue: null,
  nullable: false,
  isPK: false,
  comment: null,
  editable: true,
  is_dirty: false,
  deleted: false,
  ...overrides,
});

const mountList = (props = {}) =>
  mount(SchemaEditorColumnList, {
    props: {
      initialColumns: [
        column({ name: "id", isPK: true }),
        column({ name: "email", dataType: "text" }),
      ],
      dataTypes: ["integer", "text"],
      mode: operationModes.CREATE,
      ...props,
    },
    global: { stubs: { SearchableDropdown: true } },
  });

const NAME_INPUT = 'input[placeholder="column name..."]';
const rows = (wrapper) => wrapper.findAll(".schema-editor__column");
const columnNames = (wrapper) =>
  rows(wrapper).map((row) => row.find(NAME_INPUT).element.value);
const button = (row, title) => row.find(`button[title="${title}"]`);
const addColumn = (wrapper) =>
  wrapper
    .findAll("button")
    .find((btn) => btn.text() === "Add Column")
    .trigger("click");
const lastEmitted = (wrapper) => wrapper.emitted("columns:changed").at(-1)[0];

describe("SchemaEditorColumnList.vue", () => {
  describe("rendering", () => {
    it("shows a row for each column", () => {
      const wrapper = mountList();

      expect(columnNames(wrapper)).toEqual(["id", "email"]);
    });

    it("shows the comment column only when the columns are commentable", () => {
      const withoutComments = mountList();
      const withComments = mountList({ commentable: true });

      expect(withoutComments.find(".schema-editor__header").text()).not.toContain("Comment");
      expect(withoutComments.find('input[placeholder="column comment..."]').exists()).toBe(false);
      expect(withComments.find(".schema-editor__header").text()).toContain("Comment");
      expect(withComments.find('input[placeholder="column comment..."]').exists()).toBe(true);
    });

    it("marks the columns that are deleted, new or changed", () => {
      const wrapper = mountList({
        initialColumns: [
          column({ name: "a", deleted: true }),
          column({ name: "b", new: true }),
          column({ name: "c", is_dirty: true }),
          column({ name: "d" }),
        ],
      });

      const [deleted, added, changed, unchanged] = rows(wrapper);
      expect(deleted.classes()).toContain("schema-editor__column-deleted");
      expect(added.classes()).toContain("schema-editor__column-new");
      expect(changed.classes()).toContain("schema-editor__column-dirty");
      expect(unchanged.classes()).not.toContain("schema-editor__column-deleted");
      expect(unchanged.classes()).not.toContain("schema-editor__column-new");
      expect(unchanged.classes()).not.toContain("schema-editor__column-dirty");
    });

    it("tells apart a default that is not set from an empty default", () => {
      const wrapper = mountList({
        initialColumns: [
          column({ name: "a", defaultValue: null }),
          column({ name: "b", defaultValue: "" }),
        ],
      });

      const [notSet, empty] = rows(wrapper).map((row) =>
        row.find('input[type="text"]:not([placeholder="column name..."])')
      );
      expect(notSet.attributes("placeholder")).toBe("not set");
      expect(empty.attributes("placeholder")).toBe("empty");
    });

    it("does not let the user edit the type, default and nullable of a column that is not editable", () => {
      const wrapper = mountList({
        initialColumns: [column({ editable: false })],
      });

      const row = rows(wrapper)[0];
      expect(row.findComponent(SearchableDropdown).props("disabled")).toBe(true);
      expect(row.find('input[placeholder="not set"]').attributes("disabled")).toBeDefined();
      expect(row.findAll('input[type="checkbox"]')[0].attributes("disabled")).toBeDefined();
    });

    it("does not let the user make a primary key column nullable", () => {
      const wrapper = mountList({
        initialColumns: [column({ isPK: true }), column({ name: "email" })],
      });

      const [primaryKey, other] = rows(wrapper).map(
        (row) => row.findAll('input[type="checkbox"]')[0]
      );
      expect(primaryKey.attributes("disabled")).toBeDefined();
      expect(other.attributes("disabled")).toBeUndefined();
    });

    it("does not let the user make a nullable column a primary key", () => {
      const wrapper = mountList({
        initialColumns: [column({ nullable: true }), column({ name: "email" })],
      });

      const [nullable, other] = rows(wrapper).map(
        (row) => row.findAll('input[type="checkbox"]')[1]
      );
      expect(nullable.attributes("disabled")).toBeDefined();
      expect(other.attributes("disabled")).toBeUndefined();
    });

    it("does not let the user change the primary key of an existing table", () => {
      const wrapper = mountList({ mode: operationModes.UPDATE });

      rows(wrapper).forEach((row) => {
        expect(
          row.findAll('input[type="checkbox"]')[1].attributes("disabled")
        ).toBeDefined();
      });
    });
  });

  describe("editing", () => {
    it("emits the columns with the new name", async () => {
      const wrapper = mountList();

      await rows(wrapper)[1].find(NAME_INPUT).setValue("mail");

      expect(lastEmitted(wrapper).map((col) => col.name)).toEqual(["id", "mail"]);
    });

    it("emits the columns with the type chosen in the dropdown", async () => {
      const wrapper = mountList();

      rows(wrapper)[0]
        .findComponent(SearchableDropdown)
        .vm.$emit("update:modelValue", "text");
      await nextTick();

      expect(lastEmitted(wrapper)[0].dataType).toBe("text");
    });

    it("emits the columns with the nullable setting the user chose", async () => {
      const wrapper = mountList();

      await rows(wrapper)[1]
        .findAll('input[type="checkbox"]')[0]
        .setValue(true);

      expect(lastEmitted(wrapper)[1].nullable).toBe(true);
    });

    it("emits the columns with the new comment", async () => {
      const wrapper = mountList({ commentable: true });

      await rows(wrapper)[0]
        .find('input[placeholder="column comment..."]')
        .setValue("Row identifier");

      expect(lastEmitted(wrapper)[0].comment).toBe("Row identifier");
    });

    it("sets the default back to not set when the input is emptied", async () => {
      const wrapper = mountList();
      const input = rows(wrapper)[0].find('input[placeholder="not set"]');

      await input.setValue("5");
      expect(lastEmitted(wrapper)[0].defaultValue).toBe("5");

      await input.setValue("");
      expect(lastEmitted(wrapper)[0].defaultValue).toBeNull();
    });

    it("does not change the initial columns", async () => {
      const initialColumns = [column({ name: "id" })];
      const wrapper = mountList({ initialColumns });

      await rows(wrapper)[0].find(NAME_INPUT).setValue("renamed");

      expect(initialColumns[0].name).toBe("id");
    });

    it("shows and emits the new columns when the initial columns change", async () => {
      const wrapper = mountList();

      await wrapper.setProps({
        initialColumns: [column({ name: "title" })],
      });

      expect(columnNames(wrapper)).toEqual(["title"]);
      expect(lastEmitted(wrapper).map((col) => col.name)).toEqual(["title"]);
    });
  });

  describe("adding a column", () => {
    it("adds a column with a name based on the number of columns", async () => {
      const wrapper = mountList();

      await addColumn(wrapper);

      expect(columnNames(wrapper)).toEqual(["id", "email", "column_2"]);
      expect(lastEmitted(wrapper)[2]).toMatchObject({
        name: "column_2",
        dataType: "integer",
        defaultValue: null,
        nullable: false,
        isPK: false,
        editable: true,
      });
    });

    it.each([
      ["a new table", operationModes.CREATE, false],
      ["an existing table", operationModes.UPDATE, true],
    ])("marks the column as new only for %s", async (_, mode, isNew) => {
      const wrapper = mountList({ mode });

      await addColumn(wrapper);

      expect(lastEmitted(wrapper)[2].new).toBe(isNew);
    });
  });

  describe("removing a column", () => {
    it("removes the column from a new table", async () => {
      const wrapper = mountList();

      await button(rows(wrapper)[0], "Remove column").trigger("click");

      expect(columnNames(wrapper)).toEqual(["email"]);
    });

    it("marks an existing column as deleted instead of removing it", async () => {
      const wrapper = mountList({ mode: operationModes.UPDATE });

      await button(rows(wrapper)[0], "Remove column").trigger("click");

      expect(columnNames(wrapper)).toEqual(["id", "email"]);
      expect(lastEmitted(wrapper)[0].deleted).toBe(true);
      expect(rows(wrapper)[0].classes()).toContain("schema-editor__column-deleted");
      expect(button(rows(wrapper)[0], "Remove column").exists()).toBe(false);
    });

    it("removes a column that was added to an existing table", async () => {
      const wrapper = mountList({ mode: operationModes.UPDATE });
      await addColumn(wrapper);

      await button(rows(wrapper)[2], "Remove column").trigger("click");

      expect(columnNames(wrapper)).toEqual(["id", "email"]);
    });
  });

  describe("reverting a column", () => {
    it("does not offer to revert a column that is not changed", () => {
      const wrapper = mountList({ mode: operationModes.UPDATE });

      expect(button(rows(wrapper)[0], "Revert").exists()).toBe(false);
    });

    it("restores a deleted column", async () => {
      const wrapper = mountList({ mode: operationModes.UPDATE });
      await button(rows(wrapper)[0], "Remove column").trigger("click");

      await button(rows(wrapper)[0], "Revert").trigger("click");

      expect(lastEmitted(wrapper)[0].deleted).toBe(false);
      expect(rows(wrapper)[0].classes()).not.toContain("schema-editor__column-deleted");
    });

    it("restores the initial values of a changed column", async () => {
      const wrapper = mountList({ mode: operationModes.UPDATE });
      await rows(wrapper)[0].find(NAME_INPUT).setValue("renamed");
      // The schema editor flags the changed columns it receives
      lastEmitted(wrapper)[0].is_dirty = true;
      await nextTick();

      await button(rows(wrapper)[0], "Revert").trigger("click");

      expect(columnNames(wrapper)).toEqual(["id", "email"]);
      expect(button(rows(wrapper)[0], "Revert").exists()).toBe(false);
    });
  });

  describe("moving a column", () => {
    it("moves a column up", async () => {
      const wrapper = mountList();

      await button(rows(wrapper)[1], "Move column up").trigger("click");

      expect(columnNames(wrapper)).toEqual(["email", "id"]);
      expect(lastEmitted(wrapper).map((col) => col.name)).toEqual(["email", "id"]);
    });

    it("moves a column down", async () => {
      const wrapper = mountList();

      await button(rows(wrapper)[0], "Move column down").trigger("click");

      expect(columnNames(wrapper)).toEqual(["email", "id"]);
    });

    describe("at the edge of the list", () => {
      const threeColumns = () =>
        mountList({
          initialColumns: [
            column({ name: "id" }),
            column({ name: "email" }),
            column({ name: "name" }),
          ],
        });

      it("keeps the first column in place when it is moved up", async () => {
        const wrapper = threeColumns();

        await button(rows(wrapper)[0], "Move column up").trigger("click");

        expect(columnNames(wrapper)).toEqual(["id", "email", "name"]);
      });

      it("keeps the last column in place when it is moved down", async () => {
        const wrapper = threeColumns();

        await button(rows(wrapper)[2], "Move column down").trigger("click");

        expect(columnNames(wrapper)).toEqual(["id", "email", "name"]);
      });
    });

    describe("in an existing table", () => {
      it("lets the user move only the columns that were added", async () => {
        const wrapper = mountList({ mode: operationModes.UPDATE });
        await addColumn(wrapper);

        const [id, email, added] = rows(wrapper);
        expect(button(id, "Move column up").exists()).toBe(false);
        expect(button(email, "Move column down").exists()).toBe(false);
        expect(button(added, "Move column up").exists()).toBe(true);
        expect(button(added, "Move column down").exists()).toBe(true);
      });

      it("does not move an added column above the existing columns", async () => {
        const wrapper = mountList({ mode: operationModes.UPDATE });
        await addColumn(wrapper);

        await button(rows(wrapper)[2], "Move column up").trigger("click");

        expect(columnNames(wrapper)).toEqual(["id", "email", "column_2"]);
      });

      it("moves an added column above another added column", async () => {
        const wrapper = mountList({ mode: operationModes.UPDATE });
        await addColumn(wrapper);
        await addColumn(wrapper);

        await button(rows(wrapper)[3], "Move column up").trigger("click");

        expect(columnNames(wrapper)).toEqual([
          "id",
          "email",
          "column_3",
          "column_2",
        ]);
      });
    });
  });

  describe("primary keys", () => {
    const pkCheckbox = (wrapper, index) =>
      rows(wrapper)[index].findAll('input[type="checkbox"]')[1];

    it("emits the initial primary key as not primary when another primary key is chosen", async () => {
      const wrapper = mountList();

      await pkCheckbox(wrapper, 1).setValue(true);

      const [id, email] = lastEmitted(wrapper);
      expect(id.isPK).toBe(false);
      expect(email.isPK).toBe(true);
    });

    it("keeps the initial primary key when multiple primary keys are allowed", async () => {
      const wrapper = mountList({ multiPKeys: true });

      await pkCheckbox(wrapper, 1).setValue(true);

      const [id, email] = lastEmitted(wrapper);
      expect(id.isPK).toBe(true);
      expect(email.isPK).toBe(true);
    });
  });
});
