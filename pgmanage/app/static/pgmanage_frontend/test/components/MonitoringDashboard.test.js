import { flushPromises, mount } from "@vue/test-utils";
import { test, describe, beforeEach, vi, expect } from "vitest";
import MonitoringDashboard from "@src/components/MonitoringDashboard.vue";
import MonitoringWidget from "@src/components/MonitoringWidget.vue";

import axios from "axios";

describe("MonitoringDashboard", () => {
  let dashboardWrapper;

  beforeEach(() => {
    vi.useFakeTimers();
    vi.resetAllMocks();

    axios.post
      .mockResolvedValue({ data: { data: "1234" } })
      .mockResolvedValueOnce({
        data: {
          widgets: [
            {
              saved_id: 1,
              id: 0,
              title: "Backends",
              plugin_name: "postgresql",
              interval: 5,
              type: "grid",
              widget_data: null,
              visible: true,
            },
          ],
        },
      })
      .mockResolvedValueOnce({ data: { data: "1234" } });
    dashboardWrapper = mount(MonitoringDashboard, {
      props: {
        workspaceId: "workspaceId",
      },
    });
  });

  test("should render MonitoringDashboard component with expected elements", () => {
    expect(dashboardWrapper.html()).toContain("Backends");
    expect(dashboardWrapper.html()).toContain("Manage Widgets");
    expect(dashboardWrapper.html()).toContain("Refresh All");
  });

  test("should refresh all widgets on 'Refresh All' button click", async () => {
    const refreshWidgetsSpy = vi.spyOn(dashboardWrapper.vm, "refreshWidgets");

    await dashboardWrapper
      .get('[data-testid="refresh-all-widgets-button"]')
      .trigger("click");

    expect(refreshWidgetsSpy).toBeCalledTimes(1);

    expect(
      dashboardWrapper.getComponent(MonitoringWidget).emitted()
    ).toHaveProperty("widgetRefreshed");
  });

  test("should not refresh widgets when none exist", async () => {
    axios.patch.mockResolvedValueOnce();
    await dashboardWrapper.vm.toggleWidget(
      dashboardWrapper.vm.widgets[0],
      false
    );
    await flushPromises();

    const refreshWidgetsSpy = vi.spyOn(dashboardWrapper.vm, "refreshWidgets");
    await dashboardWrapper
      .get('[data-testid="refresh-all-widgets-button"]')
      .trigger("click");

    expect(refreshWidgetsSpy).toBeCalledTimes(1);
    expect(dashboardWrapper.vm.refreshWidget).toBe(false);
  });

  test("should toggle widget in dashboard on 'close' button click", async () => {
    axios.patch.mockResolvedValueOnce();
    expect(dashboardWrapper.vm.widgets).toStrictEqual([
      {
        saved_id: 1,
        id: 0,
        title: "Backends",
        plugin_name: "postgresql",
        interval: 5,
        type: "grid",
        widget_data: null,
        visible: true,
      },
    ]);

    await dashboardWrapper
      .get("[data-testid='widget-close-button']")
      .trigger("click");

    expect(dashboardWrapper.vm.visibleSortedWidgets).toStrictEqual([]);
  });
});
