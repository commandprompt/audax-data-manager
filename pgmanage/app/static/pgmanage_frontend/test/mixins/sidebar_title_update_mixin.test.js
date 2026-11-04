import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { Tooltip } from "bootstrap";
import mixin from "@src/mixins/sidebar_title_update_mixin";
import {
  connectionsStore,
  tabsStore,
} from "@src/stores/stores_initializer";

const { tooltipInstance } = vi.hoisted(() => ({
  tooltipInstance: { dispose: vi.fn() },
}));

vi.mock("bootstrap", async (importOriginal) => {
  const Tooltip = vi.fn(function () {
    return {};
  });
  Tooltip.getInstance = vi.fn(() => tooltipInstance);
  return { ...(await importOriginal()), Tooltip };
});

describe("sidebar title update mixin", () => {
  let wrappers, tab;

  const connection = (overrides = {}) => ({
    id: 1,
    alias: "Local",
    conn_string: "",
    details1: "PostgreSQL 16",
    details2: "127.0.0.1:5432",
    ...overrides,
  });

  // Same as the workspace tab: the mixin looks for the tooltip element inside the tab element
  const mountTab = (tabToWatch, databaseIndex = 1) => {
    const wrapper = mount(
      {
        mixins: [mixin],
        props: { tabId: String, databaseIndex: Number },
        template: `<div :id="tabId"><span data-bs-toggle="tooltip"></span></div>`,
        mounted() {
          this.subscribeToConnectionChanges(this.tabId, this.databaseIndex);
        },
      },
      {
        props: { tabId: tabToWatch.id, databaseIndex },
        attachTo: document.body,
      }
    );
    wrappers.push(wrapper);
    return wrapper;
  };

  beforeEach(() => {
    wrappers = [];
    connectionsStore.$reset();
    tab = tabsStore.addTab({ name: "Old name", tooltip: "Old tooltip" });
  });

  afterEach(() => {
    wrappers.forEach((wrapper) => wrapper.unmount());
    tabsStore.$reset();
    vi.clearAllMocks();
  });

  it("renames the tab after the alias of the connection", () => {
    mountTab(tab);

    connectionsStore.$patch({ connections: [connection({ alias: "Staging" })] });

    expect(tab.name).toBe("Staging");
  });

  describe("tooltip text", () => {
    it("shows the alias and the connection string", () => {
      mountTab(tab);

      connectionsStore.$patch({
        connections: [connection({ conn_string: "host=db user=app" })],
      });

      expect(tab.tooltip).toBe(
        '<h5 class="my-1">Local</h5><div class="mb-1">host=db user=app</div>'
      );
    });

    it("shows the alias and the details when there is no connection string", () => {
      mountTab(tab);

      connectionsStore.$patch({ connections: [connection()] });

      expect(tab.tooltip).toBe(
        '<h5 class="my-1">Local</h5>' +
          '<div class="mb-1">PostgreSQL 16</div>' +
          '<div class="mb-1">127.0.0.1:5432</div>'
      );
    });

    it.each([
      [
        "alias of a connection string",
        { alias: "", conn_string: "host=db" },
        '<div class="mb-1">host=db</div>',
      ],
      [
        "alias and first detail",
        { alias: "", details1: "" },
        '<div class="mb-1">127.0.0.1:5432</div>',
      ],
      [
        "second detail",
        { details2: "" },
        '<h5 class="my-1">Local</h5><div class="mb-1">PostgreSQL 16</div>',
      ],
    ])("leaves out the empty %s", (_, overrides, expected) => {
      mountTab(tab);

      connectionsStore.$patch({ connections: [connection(overrides)] });

      expect(tab.tooltip).toBe(expected);
    });
  });

  it("replaces the tooltip of the tab element with the new text", () => {
    const wrapper = mountTab(tab);
    const tooltipEl = wrapper.element.querySelector("[data-bs-toggle='tooltip']");

    connectionsStore.$patch({ connections: [connection()] });

    expect(Tooltip.getInstance).toHaveBeenCalledWith(tooltipEl);
    expect(tooltipInstance.dispose).toHaveBeenCalledOnce();
    expect(Tooltip).toHaveBeenCalledWith(
      tooltipEl,
      expect.objectContaining({ title: tab.tooltip, html: true })
    );
  });

  it("updates each tab with its own connection", () => {
    const otherTab = tabsStore.addTab({ name: "Other" });
    mountTab(tab, 1);
    mountTab(otherTab, 2);

    connectionsStore.$patch({
      connections: [
        connection({ id: 1, alias: "First" }),
        connection({ id: 2, alias: "Second" }),
      ],
    });

    expect(tab.name).toBe("First");
    expect(otherTab.name).toBe("Second");
  });

  it("does not change the tab when other store data changes", async () => {
    mountTab(tab);

    connectionsStore.connections.push(connection());
    await nextTick();

    expect(tab.name).toBe("Old name");
    expect(tab.tooltip).toBe("Old tooltip");
    expect(Tooltip).not.toHaveBeenCalled();
  });

  it("does not change the tab after the component is unmounted", () => {
    const wrapper = mountTab(tab);
    wrapper.unmount();
    wrappers = [];

    expect(() =>
      connectionsStore.$patch({ connections: [connection()] })
    ).not.toThrow();
    expect(tab.name).toBe("Old name");
  });
});
