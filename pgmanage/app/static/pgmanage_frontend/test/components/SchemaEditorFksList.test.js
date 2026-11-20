import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import { describe, it, expect } from "vitest";
import SchemaEditorFksList from "@src/components/SchemaEditorFksList.vue";
import SearchableDropdown from "@src/components/SearchableDropdown.vue";

const dbMetaData = [
  {
    name: "public",
    tables: [
      { name: "users", columns: ["id", "email"] },
      { name: "orders", columns: ["id", "user_id"] },
    ],
  },
  {
    name: "audit",
    tables: [{ name: "logs", columns: ["id", "message"] }],
  },
];

const foreignKey = (overrides = {}) => ({
  constraint_name: "orders_user_fk",
  column_name: "user_id",
  r_table_schema: "public",
  r_table_name: "users",
  r_column_name: "id",
  on_update: "NO ACTION",
  on_delete: "CASCADE",
  new: false,
  is_dirty: false,
  deleted: false,
  ...overrides,
});

const mountList = (props = {}) =>
  mount(SchemaEditorFksList, {
    props: {
      initialForeignKeys: [foreignKey()],
      columns: ["id", "user_id"],
      dbMetaData,
      ...props,
    },
    global: { stubs: { SearchableDropdown: true } },
  });

const NAME_INPUT = 'input[placeholder="foreign key name..."]';
const PLACEHOLDERS = {
  column: "column name...",
  schema: "foreign key table schema..",
  table: "foreign key table..",
  fkColumn: "foreign key column..",
  onUpdate: "on update ...",
  onDelete: "on delete ...",
};

const rows = (wrapper) => wrapper.findAll(".schema-editor__column");
const dropdown = (wrapper, rowIndex, name) =>
  rows(wrapper)[rowIndex]
    .findAllComponents(SearchableDropdown)
    .find((item) => item.props("placeholder") === PLACEHOLDERS[name]);
// Same events as the real dropdown emits when the user picks an option
const choose = async (wrapper, rowIndex, name, value) => {
  const item = dropdown(wrapper, rowIndex, name);
  item.vm.$emit("update:modelValue", value);
  item.vm.$emit("change", value);
  await nextTick();
};
const button = (row, title) => row.find(`button[title="${title}"]`);
const addForeignKey = (wrapper) =>
  wrapper
    .findAll("button")
    .find((btn) => btn.text() === "Add Foreign Key")
    .trigger("click");
const header = (wrapper) => wrapper.find(".schema-editor__header").text();
const lastEmitted = (wrapper) =>
  wrapper.emitted("foreign-keys:changed").at(-1)[0];

describe("SchemaEditorFksList.vue", () => {
  describe("rendering", () => {
    it("shows a row for each foreign key", () => {
      const wrapper = mountList({
        initialForeignKeys: [
          foreignKey(),
          foreignKey({ constraint_name: "orders_other_fk" }),
        ],
      });

      expect(
        rows(wrapper).map((row) => row.find(NAME_INPUT).element.value)
      ).toEqual(["orders_user_fk", "orders_other_fk"]);
    });

    it("shows the schema of the referenced table only when the database has schemas", () => {
      const withSchemas = mountList();
      const withoutSchemas = mountList({ hasSchema: false });

      expect(header(withSchemas)).toContain("FK Schema");
      expect(dropdown(withSchemas, 0, "schema")).toBeDefined();
      expect(header(withoutSchemas)).not.toContain("FK Schema");
      expect(dropdown(withoutSchemas, 0, "schema")).toBeUndefined();
    });

    it("shows the On Update setting only when the database supports it", () => {
      const supported = mountList();
      const unsupported = mountList({
        disabledFeatures: { constraints: { onUpdate: true } },
      });

      expect(header(supported)).toContain("On Update");
      expect(dropdown(supported, 0, "onUpdate")).toBeDefined();
      expect(header(unsupported)).not.toContain("On Update");
      expect(dropdown(unsupported, 0, "onUpdate")).toBeUndefined();
    });

    it("hides the actions when the database cannot drop a foreign key", () => {
      const wrapper = mountList({
        disabledFeatures: { dropForeignKey: true },
      });

      expect(header(wrapper)).not.toContain("Actions");
      expect(button(rows(wrapper)[0], "Remove foreign key").exists()).toBe(false);
    });

    it("hides the add button when the database cannot add a foreign key", () => {
      const wrapper = mountList({
        disabledFeatures: { addForeignKey: true },
      });

      expect(wrapper.text()).not.toContain("Add Foreign Key");
    });

    it("marks the foreign keys that are deleted or new", () => {
      const wrapper = mountList({
        initialForeignKeys: [
          foreignKey({ deleted: true }),
          foreignKey({ new: true }),
          foreignKey(),
        ],
      });

      const [deleted, added, unchanged] = rows(wrapper);
      expect(deleted.classes()).toContain("schema-editor__column-deleted");
      expect(added.classes()).toContain("schema-editor__column-new");
      expect(unchanged.classes()).not.toContain("schema-editor__column-deleted");
      expect(unchanged.classes()).not.toContain("schema-editor__column-new");
    });

    it("lets the user edit only the foreign keys that were added", async () => {
      const wrapper = mountList();
      await addForeignKey(wrapper);

      const lockedFields = (index) => [
        rows(wrapper)[index].find(NAME_INPUT).element.disabled,
        ...rows(wrapper)[index]
          .findAllComponents(SearchableDropdown)
          .map((item) => item.props("disabled")),
      ];
      expect(lockedFields(0).every(Boolean)).toBe(true);
      expect(lockedFields(1).some(Boolean)).toBe(false);
    });
  });

  describe("dropdown options", () => {
    it("offers the columns of the table that is edited", () => {
      const wrapper = mountList();

      expect(dropdown(wrapper, 0, "column").props("options")).toEqual([
        "id",
        "user_id",
      ]);
    });

    it("offers the schemas of the database", () => {
      const wrapper = mountList();

      expect(dropdown(wrapper, 0, "schema").props("options")).toEqual([
        "public",
        "audit",
      ]);
    });

    it("offers the tables of the schema of the foreign key", () => {
      const wrapper = mountList();

      expect(dropdown(wrapper, 0, "table").props("options")).toEqual([
        "users",
        "orders",
      ]);
    });

    it("offers the columns of the table of the foreign key", () => {
      const wrapper = mountList();

      expect(dropdown(wrapper, 0, "fkColumn").props("options")).toEqual([
        "id",
        "email",
      ]);
    });

    it("offers no tables and columns before a schema is chosen", async () => {
      const wrapper = mountList();
      await addForeignKey(wrapper);

      expect(dropdown(wrapper, 1, "table").props("options") ?? []).toEqual([]);
      expect(dropdown(wrapper, 1, "fkColumn").props("options") ?? []).toEqual([]);
    });

    it("takes the tables and columns from the only schema when the database has no schemas", () => {
      const wrapper = mountList({
        hasSchema: false,
        dbMetaData: [dbMetaData[0]],
        initialForeignKeys: [foreignKey({ r_table_schema: null })],
      });

      expect(dropdown(wrapper, 0, "table").props("options")).toEqual([
        "users",
        "orders",
      ]);
      expect(dropdown(wrapper, 0, "fkColumn").props("options")).toEqual([
        "id",
        "email",
      ]);
    });

    it("offers the same actions for on update and on delete", () => {
      const wrapper = mountList();
      const actions = [
        "NO ACTION",
        "SET NULL",
        "SET DEFAULT",
        "CASCADE",
        "RESTRICT",
      ];

      expect(dropdown(wrapper, 0, "onUpdate").props("options")).toEqual(actions);
      expect(dropdown(wrapper, 0, "onDelete").props("options")).toEqual(actions);
    });
  });

  describe("editing", () => {
    it("emits the foreign keys with the name typed for a new foreign key", async () => {
      const wrapper = mountList();
      await addForeignKey(wrapper);

      await rows(wrapper)[1].find(NAME_INPUT).setValue("orders_audit_fk");

      expect(lastEmitted(wrapper)[1].constraint_name).toBe("orders_audit_fk");
    });

    it("emits the foreign keys with the choices made in the dropdowns", async () => {
      const wrapper = mountList();
      await addForeignKey(wrapper);

      await choose(wrapper, 1, "column", "user_id");
      await choose(wrapper, 1, "schema", "public");
      await choose(wrapper, 1, "table", "users");
      await choose(wrapper, 1, "fkColumn", "id");
      await choose(wrapper, 1, "onUpdate", "SET NULL");
      await choose(wrapper, 1, "onDelete", "RESTRICT");

      expect(lastEmitted(wrapper)[1]).toMatchObject({
        column_name: "user_id",
        r_table_schema: "public",
        r_table_name: "users",
        r_column_name: "id",
        on_update: "SET NULL",
        on_delete: "RESTRICT",
      });
    });

    it("clears the table and the column when another schema is chosen", async () => {
      const wrapper = mountList();
      await addForeignKey(wrapper);
      await choose(wrapper, 1, "schema", "public");
      await choose(wrapper, 1, "table", "users");
      await choose(wrapper, 1, "fkColumn", "id");

      await choose(wrapper, 1, "schema", "audit");

      expect(lastEmitted(wrapper)[1]).toMatchObject({
        r_table_schema: "audit",
        r_table_name: null,
        r_column_name: null,
      });
    });

    it("clears the column when another table is chosen", async () => {
      const wrapper = mountList();
      await addForeignKey(wrapper);
      await choose(wrapper, 1, "schema", "public");
      await choose(wrapper, 1, "table", "users");
      await choose(wrapper, 1, "fkColumn", "id");

      await choose(wrapper, 1, "table", "orders");

      expect(lastEmitted(wrapper)[1]).toMatchObject({
        r_table_name: "orders",
        r_column_name: null,
      });
    });

    it("does not change the initial foreign keys", async () => {
      const initialForeignKeys = [foreignKey({ new: true })];
      const wrapper = mountList({ initialForeignKeys });

      await rows(wrapper)[0].find(NAME_INPUT).setValue("renamed");

      expect(initialForeignKeys[0].constraint_name).toBe("orders_user_fk");
    });

    it("shows and emits the new foreign keys when the initial foreign keys change", async () => {
      const wrapper = mountList();

      await wrapper.setProps({
        initialForeignKeys: [foreignKey({ constraint_name: "loaded_fk" })],
      });

      expect(rows(wrapper)[0].find(NAME_INPUT).element.value).toBe("loaded_fk");
      expect(lastEmitted(wrapper).map((fk) => fk.constraint_name)).toEqual([
        "loaded_fk",
      ]);
    });
  });

  describe("adding a foreign key", () => {
    it("adds a new foreign key with a name based on the number of foreign keys", async () => {
      const wrapper = mountList();

      await addForeignKey(wrapper);

      expect(rows(wrapper)).toHaveLength(2);
      expect(lastEmitted(wrapper)[1]).toMatchObject({
        constraint_name: "fk_1",
        column_name: null,
        r_table_name: null,
        r_column_name: null,
        on_update: "NO ACTION",
        on_delete: "NO ACTION",
        new: true,
      });
    });

    it("chooses the schema when the database has only one", async () => {
      const wrapper = mountList({ dbMetaData: [dbMetaData[1]] });

      await addForeignKey(wrapper);

      expect(lastEmitted(wrapper)[1].r_table_schema).toBe("audit");
    });

    it("leaves the schema empty when the database has several", async () => {
      const wrapper = mountList();

      await addForeignKey(wrapper);

      expect(lastEmitted(wrapper)[1].r_table_schema).toBeNull();
    });
  });

  describe("removing a foreign key", () => {
    it("removes a foreign key that was added", async () => {
      const wrapper = mountList();
      await addForeignKey(wrapper);

      await button(rows(wrapper)[1], "Remove foreign key").trigger("click");

      expect(rows(wrapper)).toHaveLength(1);
    });

    it("marks an existing foreign key as deleted instead of removing it", async () => {
      const wrapper = mountList();

      await button(rows(wrapper)[0], "Remove foreign key").trigger("click");

      expect(rows(wrapper)).toHaveLength(1);
      expect(lastEmitted(wrapper)[0].deleted).toBe(true);
      expect(rows(wrapper)[0].classes()).toContain("schema-editor__column-deleted");
      expect(button(rows(wrapper)[0], "Remove foreign key").exists()).toBe(false);
    });
  });

  describe("reverting a foreign key", () => {
    it("does not offer to revert a foreign key that is not deleted", () => {
      const wrapper = mountList();

      expect(button(rows(wrapper)[0], "Revert").exists()).toBe(false);
    });

    it("restores a deleted foreign key", async () => {
      const wrapper = mountList();
      await button(rows(wrapper)[0], "Remove foreign key").trigger("click");

      await button(rows(wrapper)[0], "Revert").trigger("click");

      expect(lastEmitted(wrapper)[0].deleted).toBe(false);
      expect(rows(wrapper)[0].classes()).not.toContain("schema-editor__column-deleted");
      expect(button(rows(wrapper)[0], "Revert").exists()).toBe(false);
    });
  });
});
