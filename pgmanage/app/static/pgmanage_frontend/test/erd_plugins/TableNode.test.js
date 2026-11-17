import { mount } from "@vue/test-utils";
import { describe, it, expect } from "vitest";
import TableNode from "@src/erd_plugins/TableNode.vue";

describe("TableNode.vue", () => {
  const mountComponent = (props = {}) => {
    return mount(TableNode, {
      props: { id: "table1", data: {}, ...props },
    });
  };

  it("renders the table label from data.label", () => {
    const wrapper = mountComponent({ data: { label: "users" } });

    expect(wrapper.find(".vue-flow__node-table__title").text()).toBe("users");
  });

  it("renders the schema in front of the table label when data.schema is set", () => {
    const wrapper = mountComponent({ data: { label: "users", schema: "sales" } });

    expect(wrapper.find(".vue-flow__node-table__title").text()).toBe(
      "sales.users",
    );
  });

  it("renders an empty title when data.label is not set", () => {
    const wrapper = mountComponent({ data: {} });

    expect(wrapper.find(".vue-flow__node-table__title").text()).toBe("");
  });

  it("updates the rendered label reactively when data changes", async () => {
    const wrapper = mountComponent({ data: { label: "users" } });

    await wrapper.setProps({ data: { label: "accounts" } });

    expect(wrapper.find(".vue-flow__node-table__title").text()).toBe(
      "accounts",
    );
  });
});
