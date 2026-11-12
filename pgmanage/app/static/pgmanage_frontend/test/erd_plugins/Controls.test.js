import { mount } from "@vue/test-utils";
import { describe, it, expect } from "vitest";
import Controls from "@src/erd_plugins/Controls.vue";

describe("Controls.vue", () => {
  const schemas = [
    { name: "public", name_raw: "public" },
    { name: "Sales", name_raw: '"Sales"' },
  ];

  const mountComponent = (props = {}) => {
    return mount(Controls, { props });
  };

  const checkbox = (wrapper, index) =>
    wrapper.findAll(".erd-schemas input[type=checkbox]")[index];

  it("does not render the schema picker without schemas", () => {
    const wrapper = mountComponent();

    expect(wrapper.find('button[title="Schemas"]').exists()).toBe(false);
  });

  it("renders a checkbox for each schema and checks the selected ones", () => {
    const wrapper = mountComponent({ schemas, selectedSchemas: ["public"] });

    expect(wrapper.find('button[title="Schemas"]').exists()).toBe(true);
    expect(wrapper.findAll(".erd-schemas label").map((l) => l.text())).toEqual([
      "public",
      "Sales",
    ]);
    expect(checkbox(wrapper, 0).element.checked).toBe(true);
    expect(checkbox(wrapper, 1).element.checked).toBe(false);
  });

  it("emits the selection with the checked schema added", async () => {
    const wrapper = mountComponent({ schemas, selectedSchemas: ["public"] });

    await checkbox(wrapper, 1).setValue(true);

    expect(wrapper.emitted("change-schemas")).toEqual([[["public", '"Sales"']]]);
  });

  it("emits the selection with the unchecked schema removed", async () => {
    const wrapper = mountComponent({
      schemas,
      selectedSchemas: ["public", '"Sales"'],
    });

    await checkbox(wrapper, 0).setValue(false);

    expect(wrapper.emitted("change-schemas")).toEqual([[['"Sales"']]]);
  });

  it("emits all schemas on select all and none on clear", async () => {
    const wrapper = mountComponent({ schemas, selectedSchemas: [] });
    const [selectAll, clear] = wrapper.findAll(".erd-schemas .btn-link");

    await selectAll.trigger("click");
    await clear.trigger("click");

    expect(wrapper.emitted("change-schemas")).toEqual([
      [["public", '"Sales"']],
      [[]],
    ]);
  });

  it("disables the schema picker while loading", () => {
    const wrapper = mountComponent({
      schemas,
      selectedSchemas: [],
      loading: true,
    });

    expect(checkbox(wrapper, 0).element.disabled).toBe(true);
    expect(
      wrapper.findAll(".erd-schemas .btn-link").every((b) => b.element.disabled),
    ).toBe(true);
    expect(wrapper.find('button[title="Schemas"] .fa-spinner').exists()).toBe(
      true,
    );
  });
});
