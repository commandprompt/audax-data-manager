import { defineStore } from "pinia";
import ShortUniqueId from "short-unique-id";
import { connectionsStore, messageModalStore, dbMetadataStore } from "./stores_initializer";
import { showToast, showConfirm } from "../notification_control";
import { createRequest, removeContext } from "../long_polling";
import moment from "moment";
import { emitter } from "../emitter";
import { queryRequestCodes, operationModes, dialectOf } from "../constants";
import { showMenuNewTabOuter, renameTab } from "../workspace";

import postgresqlIcon from '@src/assets/images/db_icons/postgresql.svg'
import mysqlIcon from '@src/assets/images/db_icons/mysql.svg'
import mariadbIcon from '@src/assets/images/db_icons/mariadb.svg'
import mssqlIcon from '@src/assets/images/db_icons/mssql.svg'
import oracleIcon from '@src/assets/images/db_icons/oracle.svg'
import sqliteIcon from '@src/assets/images/db_icons/sqlite.svg'

const useTabsStore = defineStore("tabs", {
  state: () => ({
    id: new ShortUniqueId({
      dictionary: "alpha_lower",
      length: 8,
    }).randomUUID(),
    tabs: [],
    selectedPrimaryTab: "",
  }),
  getters: {
    selectablePrimaryTabs() {
      return this.tabs.filter((tab) => tab.selectable);
    },
    hasAnyUnsavedChanges() {
      return this.tabs.some(primaryTab => {
        return primaryTab.metaData?.secondaryTabs?.some(
          sec => sec.metaData?.hasUnsavedChanges
        );
      });
    },
  },
  actions: {
    addTab({
      parentId = null,
      name = "",
      component = null,
      icon = false,
      tooltip = false,
      disabled = false,
      isDraggable = true,
      selectable = true,
      clickFunction = null,
      closable = true,
      closeFunction = null,
      dblClickFunction = null,
      rightClickFunction = false,
      selectFunction = null,
      mode = null,
    }) {
      let tabId = new ShortUniqueId({
        dictionary: "alpha_lower",
        length: 8,
      }).randomUUID();

      let tab = {
        id: tabId,
        parentId: parentId,
        name: name,
        component: component,
        icon: icon,
        tooltip: tooltip,
        disabled: disabled,
        isDraggable: isDraggable,
        selectable: selectable,
        closable: closable,
        clickFunction: clickFunction,
        selectFunction: selectFunction,
        dblClickFunction: dblClickFunction,
        closeFunction: closeFunction,
        rightClickFunction: rightClickFunction,
        metaData: {
          secondaryTabs: [],
          selectedTab: "",
          isLoading: false,
          isReady: false,
          mode: mode,
        },
        dragEndFunction: this.dragEndFunction,
      };
      if (parentId) {
        let primaryTab = this.tabs.find((tab) => tab.id === parentId);
        //TODO: handle case if tab with specified Id not exist
        primaryTab.metaData.secondaryTabs.push(tab);
      } else {
        this.tabs.push(tab);
      }
      return tab;
    },
    selectTab(tab) {
      if (tab.parentId) {
        let primaryTab = this.tabs.find(
          (primaryTab) => primaryTab.id === tab.parentId
        );
        primaryTab.metaData.selectedTab = tab;
      } else {
        this.selectedPrimaryTab = tab;
      }

      if (tab.selectFunction != null) {
        tab.selectFunction();
      }
    },
    removeTab(tabToRemove) {
      const isPrimaryTab = !tabToRemove.parentId;
      if (isPrimaryTab) {
        this.removePrimaryTab(tabToRemove);
      } else {
        this.removeSecondaryTab(tabToRemove);
      }
    },
    removePrimaryTab(tabToRemove) {
      const tabIndex = this.tabs.indexOf(tabToRemove);
      if (this.selectedPrimaryTab === tabToRemove) {
        const selectableTabs = this.selectablePrimaryTabs;
        const nextTabIndex = selectableTabs.indexOf(tabToRemove) + 1;
        const newSelectedTab =
          nextTabIndex < selectableTabs.length
            ? selectableTabs[nextTabIndex]
            : selectableTabs[nextTabIndex - 2];

        this.selectedPrimaryTab = newSelectedTab;
      }
      this.tabs.splice(tabIndex, 1);
    },
    removeSecondaryTab(tabToRemove) {
      const primaryTab = this.tabs.find(
        (tab) => tab.id === tabToRemove.parentId
      );

      const secondaryTabs = primaryTab.metaData.secondaryTabs;
      const tabIndex = secondaryTabs.indexOf(tabToRemove);
      if (primaryTab.metaData.selectedTab === tabToRemove) {
        const nextTabIndex = tabIndex + 1;
        if (secondaryTabs.length > 1) {
          const newSelectedTab = secondaryTabs[nextTabIndex]?.selectable
            ? secondaryTabs[nextTabIndex]
            : secondaryTabs[nextTabIndex - 2];
          primaryTab.metaData.selectedTab = newSelectedTab;
        }
      }
      secondaryTabs.splice(tabIndex, 1);
    },
    getSecondaryTabs(parentId) {
      const primaryTabIdx = this.tabs.findIndex((tab) => tab.id === parentId);
      return this.tabs[primaryTabIdx]?.metaData?.secondaryTabs || [];
    },
    getSelectedSecondaryTab(parentId) {
      const primaryTabIdx = this.tabs.findIndex((tab) => tab.id === parentId);
      return this.tabs[primaryTabIdx]?.metaData?.selectedTab;
    },
    dragEndFunction(e, tab) {
      // Get the dragged element and drop position
      let el = e.target;
      let drop_pos_x = e.clientX;
      let drop_pos_y = e.clientY;
      let allNodes = Array.from(el.parentNode.children);
      let oldIndex = allNodes.indexOf(el);

      let newIndex = allNodes.findIndex((node) => {
        let rect = node.getBoundingClientRect();
        return (
          drop_pos_x >= rect.left &&
          drop_pos_x <= rect.right &&
          drop_pos_y >= rect.top &&
          drop_pos_y <= rect.bottom &&
          !!node.draggable
        );
      });

      if (newIndex === -1) {
        newIndex = oldIndex;
      }

      // Reorder the tabs based on the new index
      if (oldIndex !== -1 && oldIndex !== newIndex) {
        if (!tab.parentId) {
          let removedEl = this.tabs.splice(oldIndex, 1)[0];
          this.tabs.splice(newIndex, 0, removedEl);
        } else {
          let primaryTab = this.tabs.find(
            (primaryTab) => primaryTab.id === tab.parentId
          );
          let removedEl = primaryTab.metaData.secondaryTabs.splice(
            oldIndex,
            1
          )[0];
          primaryTab.metaData.secondaryTabs.splice(newIndex, 0, removedEl);
        }
      }
    },
    getPrimaryTabById(tabId) {
      return this.tabs.find((tab) => tab.id === tabId);
    },
    getSecondaryTabById(tabId, parentId) {
      const primaryTab = this.tabs.find((tab) => tab.id === parentId);
      if (primaryTab) {
        const secondaryTab = primaryTab.metaData.secondaryTabs.find(
          (tab) => tab.id === tabId
        );
        return secondaryTab;
      }
    },
    beforeCloseTab(e, confirmFunction) {
      if (e) {
        if (e.clientX == 0 && e.clientY == 0) {
          showConfirm("Are you sure you want to remove this tab?", function () {
            confirmFunction();
          });
        } else {
          confirmFunction();
        }
      } else {
        confirmFunction();
      }
    },
    createSnippetPanel() {
      this.addTab({
        name: "Snippets",
        component: "SnippetPanel",
        icon: '<i class="fas fa-file-code"></i>',
        tooltip: "Snippets Panel",
        closable: false,
        selectable: false,
        isDraggable: false,
        clickFunction: function () {
          emitter.emit("toggle_snippet_panel");
        },
      });
    },
    createConnectionsTab() {
      this.addTab({
        name: "Connections",
        icon: '<i class="fas fa-bolt"></i>',
        tooltip: "Connections",
        closable: false,
        selectable: false,
        isDraggable: false,
        clickFunction: function (e) {
          showMenuNewTabOuter(e);
        },
      });
    },
    createWelcomeTab() {
      const tab = this.addTab({
        name: "Welcome",
        component: "WelcomeScreen",
        icon: '<i class="fas fa-hand-spock"></i>',
        tooltip: "Welcome to Audax Data Manager",
        closable: false,
        isDraggable: false,
      });

      this.selectTab(tab);
    },
    createWorkspaceTab(
      index,
      createInitialTabs = true,
      name = false,
      tooltipName = false
    ) {
      return new Promise((resolve, reject) => {
        if (connectionsStore.connections.length == 0) {
          showToast("error", "Create connections first.");
          reject("No connections available.");
        } else {
          let connection = connectionsStore.getConnection(index);

          // patch the connection last used date when connecting
          // to refresh last-used labels on the welcome screen
          connectionsStore.updateConnection(index, {
            last_access_date: moment.now(),
          });
          let connName = "";
          if (name) {
            connName = name;
          }
          if (connName === "" && connection.alias && connection.alias !== "") {
            connName = connection.alias;
          }

          if (!tooltipName) {
            tooltipName = "";

            if (connection.conn_string && connection.conn_string !== "") {
              if (connection.alias) {
                tooltipName += `<h5 class="my-1">${connection.alias}</h5>`;
              }
              tooltipName += `<div class="mb-1">${connection.conn_string}</div>`;
            } else {
              if (connection.alias) {
                tooltipName += `<h5 class="my-1">${connection.alias}</h5>`;
              }
              if (connection.details1) {
                tooltipName += `<div class="mb-1">${connection.details1}</div>`;
              }
              if (connection.details2) {
                tooltipName += `<div class="mb-1">${connection.details2}</div>`;
              }
            }
          }

          const dbIcons = {
            'postgresql': postgresqlIcon,
            'rdspostgresql': postgresqlIcon,
            'mysql': mysqlIcon,
            'mariadb': mariadbIcon,
            'oracle': oracleIcon,
            'sqlite': sqliteIcon,
            'mssql': mssqlIcon,
          }

          let imgPath = dbIcons[connection.technology];
          let icon = `<img src="${imgPath}"/>`;

          const connTab = this.addTab({
            name: connName,
            component: "WorkspaceTab",
            icon: icon,
            tooltip: tooltipName,
            mode: "connection",
            selectFunction: () => {
              document.title = "Audax Data Manager";
              this.checkTabStatus();
            },
            closeFunction: (e, primaryTab) => {
              this.beforeCloseTab(e, () => {
                const secondaryTabs = this.getSecondaryTabs(primaryTab.id);

                const hasUnsavedChanges = secondaryTabs.some(
                  (tab) => tab.metaData.hasUnsavedChanges
                );

                if (hasUnsavedChanges) {
                  messageModalStore.showModal(
                    "Some tabs have unsaved changes. Do you wish to discard all changes and close?",
                    () => {
                      this.closeWorkspaceTab(primaryTab, secondaryTabs);
                    },
                    null
                  );
                } else {
                  this.closeWorkspaceTab(primaryTab, secondaryTabs);
                }
              });
            },
          });
          connTab.metaData.selectedDBMS = dialectOf(connection.technology);
          connTab.metaData.consoleHelp = connection.console_help;
          connTab.metaData.selectedDatabaseIndex = connection.id;
          connTab.metaData.selectedDatabase =
            connection.last_used_database || connection.service;
          connTab.metaData.createInitialTabs = createInitialTabs;

          this.selectTab(connTab);
          resolve(connTab);
        }
      });
    },
    createTerminalTab(index, alias, details) {
      let tooltipName = "";

      if (alias) {
        tooltipName += `<h5 class="my-1">${alias}</h5>`;
      }
      if (details) {
        tooltipName += `<div class="mb-1">${details}</div>`;
      }

      connectionsStore.updateConnection(index, {
        last_access_date: moment.now(),
      });

      const tab = this.addTab({
        name: alias,
        component: "TerminalTab",
        icon: '<i class="fas fa-terminal"></i>',
        tooltip: tooltipName,
        closable: true,
        mode: "outer_terminal",
        selectFunction: function () {
          emitter.emit(`${this.id}_resize`);
        },
        closeFunction: (e, tab) => {
          this.beforeCloseTab(e, () => {
            this.closeTab(tab);
          });
        },
      });
      tab.metaData.selectedDatabaseIndex = index;

      this.selectTab(tab);
    },
    createConsoleTab(parentId) {
      const tab = this.addTab({
        parentId: parentId ?? this.selectedPrimaryTab.id,
        name: "Console",
        component: "ConsoleTab",
        icon: "<i class='fas fa-terminal icon-tab-title'></i>",
        mode: "console",
        selectFunction: function () {
          emitter.emit(`${this.id}_resize`);
          emitter.emit(`${this.id}_check_console_status`);
        },
        closeFunction: (e, tab) => {
          this.closeTabWithConfirmation(
            tab,
            "Are you sure you wish to discard unsaved console changes?",
            this.closeTab
          );
        },
      });
      const primaryTab = !!parentId
        ? this.getPrimaryTabById(parentId)
        : this.selectedPrimaryTab;
      tab.metaData.consoleHelp = primaryTab.metaData?.consoleHelp;
      tab.metaData.databaseIndex = primaryTab.metaData?.selectedDatabaseIndex;
      tab.metaData.dialect = primaryTab.metaData?.selectedDBMS;
      tab.metaData.databaseName = primaryTab.metaData?.selectedDatabase;

      this.selectTab(tab);
    },
    createQueryTab(
      name = "Query",
      tabDbId = null,
      tabDbName = null,
      initialQuery = null,
      parentId = null
    ) {
      return new Promise((resolve, reject) => {
        const tab = this.addTab({
          parentId: parentId ?? this.selectedPrimaryTab.id,
          name: name,
          icon: '<i class="fas fa-database icon-tab-title"></i>',
          component: "QueryTab",
          mode: "query",
          selectFunction: function () {
            emitter.emit(`${this.id}_check_query_status`);
          },
          closeFunction: (e, tab) => {
            this.closeTabWithConfirmation(
              tab,
              "Are you sure you wish to discard unsaved query changes?",
              this.closeTab
            );
          },
          dblClickFunction: renameTab,
        });
        const primaryTab = !!parentId
          ? this.getPrimaryTabById(parentId)
          : this.selectedPrimaryTab;
        tab.metaData.databaseName =
          tabDbName ?? primaryTab.metaData?.selectedDatabase;
        tab.metaData.initTabDatabaseId = tabDbId;
        tab.metaData.initialQuery = initialQuery;
        tab.metaData.databaseIndex = primaryTab.metaData?.selectedDatabaseIndex;
        tab.metaData.dialect = primaryTab.metaData?.selectedDBMS;
        this.selectTab(tab);
        resolve(tab);
      });
    },
    createSnippetTab(tabId, snippet) {
      let snippetName = "New Snippet";

      let snippetDetails = {
        id: null,
        name: null,
        parent: null,
        type: "snippet",
      };

      if (snippet) {
        snippetName = snippet.name;
        snippetDetails = {
          id: snippet.id,
          name: snippetName,
          text: snippet.text,
          parent: snippet.id_parent,
          type: "snippet",
        };
      }

      let tab = this.addTab({
        name: snippetName,
        parentId: tabId,
        component: "SnippetTab",
        mode: "snippet",
        selectFunction: function () {
          emitter.emit(`${this.id}_editor_focus`);
          emitter.emit(`${this.id}_resize`);
        },
        closeFunction: (e, tab) => {
          this.closeTabWithConfirmation(
            tab,
            "Are you sure you wish to discard unsaved changes?",
            this.closeTab
          );
        },
      });

      tab.metaData.snippetObject = snippetDetails;

      this.selectTab(tab);
    },
    createMonitoringDashboardTab() {
      let secondaryTabs = this.selectedPrimaryTab.metaData.secondaryTabs;
      let existingTab = secondaryTabs.filter((t) => {
        return t.component === "MonitoringDashboard"
      })[0]

      if(existingTab) {
        this.selectTab(existingTab);
        return
      }

      const tab = this.addTab({
        parentId: this.selectedPrimaryTab.id,
        name: "Monitoring",
        icon: '<i class="fas fa-chart-line icon-tab-title"></i>',
        component: "MonitoringDashboard",
        mode: "monitoring_dashboard",
        selectFunction: function () {
          emitter.emit(`${this.id}_redraw_widget_grid`);
        },
        closeFunction: (e, tab) => {
          this.closeTab(tab);
        },
        dblClickFunction: renameTab,
      });

      tab.metaData.databaseIndex =
        this.selectedPrimaryTab?.metaData?.selectedDatabaseIndex;
      this.selectTab(tab);
    },
    createConfigurationTab() {
      const tab = this.addTab({
        parentId: this.selectedPrimaryTab.id,
        name: "Configuration",
        icon: '<i class="fas fa-cog icon-tab-title"></i>',
        component: "ConfigTab",
        mode: "configuration",
        closeFunction: (e, tab) => {
          this.closeTabWithConfirmation(
            tab,
            "Are you sure you wish to discard unsaved configuration changes?",
            this.closeTab
          );
        },
      });

      tab.metaData.databaseIndex =
        this.selectedPrimaryTab?.metaData?.selectedDatabaseIndex;
      this.selectTab(tab);
    },
    createUtilityTab(node, database, utility, backupType = "objects") {
      let utilityTitle =
        backupType === "objects"
          ? `(${node.data.type}:${node.title})`
          : backupType;
      let tabName = `${utility} ${utilityTitle}`;
      let mode = utility.toLowerCase();
      let icon = `<i class="fas ${
        mode === "backup" ? "fa-download" : "fa-upload"
      } icon-tab-title"></i>`;

      const tab = this.addTab({
        parentId: this.selectedPrimaryTab.id,
        name: tabName,
        icon: icon,
        mode: mode,
        component: `${utility}Tab`,
        closeFunction: (e, tab) => {
          this.closeTab(tab);
        },
      });

      tab.metaData.treeNode = node;
      tab.metaData.database = database;
      tab.metaData.backupType = backupType;
      tab.metaData.databaseIndex =
        this.selectedPrimaryTab?.metaData?.selectedDatabaseIndex;

      this.selectTab(tab);
    },
    createERDTab(schema = "") {
      let secondaryTabs = this.selectedPrimaryTab.metaData.secondaryTabs;
      let existingTabs = secondaryTabs.filter((t) => {
        return t.component === "ERDTab";
      });

      let tabName = schema
        ? `ERD: ${this.selectedPrimaryTab?.metaData?.selectedDatabase}@${schema}`
        : "ERD";
      if (existingTabs) {
        let existingSameTab = existingTabs.find((t) => t.name == tabName);
        if (!!existingSameTab) {
          this.selectTab(existingSameTab);
          return;
        }
      }

      const tab = this.addTab({
        parentId: this.selectedPrimaryTab.id,
        name: tabName,
        component: "ERDTab",
        icon: '<i class="fab fa-hubspot icon-tab-title"></i>',
        selectFunction: function () {
          document.title = "Audax Data Manager";
        },
        closeFunction: (e, tab) => {
          this.closeTab(tab);
        },
      });

      tab.metaData.schema = schema;
      tab.metaData.databaseIndex =
        this.selectedPrimaryTab?.metaData?.selectedDatabaseIndex;
      tab.metaData.databaseName =
        this.selectedPrimaryTab?.metaData?.selectedDatabase;

      this.selectTab(tab);
    },
    createDataEditorTab(table, schema = "") {
      let tabName = schema
        ? `Edit data: ${schema}.${table}`
        : `Edit data: ${table}`;

      const tab = this.addTab({
        icon: '<i class="fas fa-table icon-tab-title"></i>',
        parentId: this.selectedPrimaryTab.id,
        name: tabName,
        component: "DataEditorTab",
        mode: "edit",
        selectFunction: function () {
          emitter.emit(`${this.id}_check_query_edit_status`);
        },
        closeFunction: (e, tab) => {
          this.closeTabWithConfirmation(
            tab,
            "Are you sure you wish to discard unsaved data editor changes?",
            this.closeTab
          );
        },
      });

      tab.metaData.dialect = this.selectedPrimaryTab.metaData.selectedDBMS;
      tab.metaData.table = table;
      tab.metaData.schema = schema;
      tab.metaData.databaseIndex =
        this.selectedPrimaryTab?.metaData?.selectedDatabaseIndex;

      this.selectTab(tab);
    },
    createSchemaEditorTab(title, schema, mode) {
      const isCreate = mode === operationModes.CREATE;
      const tableName = title.replace(/^"(.*)"$/, "$1");
      const tabTitle = isCreate ? "New Table" : `Alter: ${tableName}`;
      const iconClass = isCreate ? "fa-plus" : "fa-edit";

      const tab = this.addTab({
        parentId: this.selectedPrimaryTab.id,
        name: tabTitle,
        icon: `<i class="fas ${iconClass} icon-tab-title"></i>`,
        component: "SchemaEditorTab",
        mode: "alter",
        closeFunction: (e, tab) => {
          this.closeTabWithConfirmation(
            tab,
            "Are you sure you wish to discard unsaved schema editor changes?",
            this.closeTab
          );
        },
      });

      const { metaData } = this.selectedPrimaryTab;

      Object.assign(tab.metaData, {
        dialect: metaData.selectedDBMS,
        editMode: mode,
        databaseIndex: metaData.selectedDatabaseIndex,
        table: isCreate ? null : tableName,
        schema: schema,
        databaseName: metaData.selectedDatabase
      });

      this.selectTab(tab);
    },
    createMonitoringTab(name = "Backends", query) {
      let secondaryTabs = this.selectedPrimaryTab.metaData.secondaryTabs;
      let existingTab = secondaryTabs.filter((t) => {
        return t.component === "MonitoringTab"
      })[0]

      if(existingTab) {
        this.selectTab(existingTab);
        return
      }
      const tab = this.addTab({
        parentId: this.selectedPrimaryTab.id,
        name: name,
        component: "MonitoringTab",
        icon: `<i class="fas fa-tasks icon-tab-title"></i>`,
        mode: "monitor_grid",
        selectFunction: function() {
          emitter.emit(`${this.id}_redraw_monitoring_tab`);
        },
        closeFunction: (e, tab) => {
          this.closeTab(tab);
        },
        dblClickFunction: renameTab,
      });

      tab.metaData.query = query;
      tab.metaData.databaseIndex =
        this.selectedPrimaryTab?.metaData?.selectedDatabaseIndex;
      tab.metaData.dialect = this.selectedPrimaryTab?.metaData?.selectedDBMS;

      this.selectTab(tab);
    },
    checkTabStatus() {
      const tab = this.selectedPrimaryTab.metaData.selectedTab;
      switch (tab?.metaData?.mode) {
        case "query":
          emitter.emit(`${tab.id}_check_query_status`);
          break;
        case "console":
          emitter.emit(`${tab.id}_check_console_status`);
          break;
        case "edit":
          emitter.emit(`${tab.id}_check_query_edit_status`);
          break;
        default:
          break;
      }
    },
    closeTab(tab) {
      if (
        ["query", "edit", "console", "outer_terminal"].includes(
          tab.metaData.mode
        )
      ) {
        if (tab.metaData?.context && tab.metaData?.context?.code) {
          removeContext(tab.metaData.context.code);
        }
        let messageData = {
          tab_id: tab.id,
          tab_db_id: null,
          workspace_id: this.selectedPrimaryTab.id,
        };
        if (tab.metaData.mode === "query") {
          messageData.tab_db_id = tab.metaData.initTabDatabaseId;
        }

        if (tab.metaData.mode === "outer_terminal") {
          messageData.tab_id = null;
        }

        createRequest(queryRequestCodes.CloseTab, [messageData]);
      }

      this.removeTab(tab);
    },
    closeTabWithConfirmation(tab, message, callback) {
      if (tab.metaData.hasUnsavedChanges) {
        messageModalStore.showModal(
          message || "Are you sure you wish to discard unsaved changes?",
          () => {
            callback(tab);
          },
          null
        );
      } else {
        callback(tab);
      }
    },
    closeWorkspaceTab(workspaceTab, secondaryTabs) {
      let tabsToRemove = [];
      let tab_ids = secondaryTabs.map((tab) => tab.id);
      tab_ids.forEach((tab_id) => {
        let tab = this.getSecondaryTabById(tab_id, workspaceTab.id);
        if (
          tab.metaData.mode == "query" ||
          tab.metaData.mode == "edit" ||
          tab.metaData.mode == "debug" ||
          tab.metaData.mode == "console"
        ) {
          if (tab.metaData?.context && tab.metaData?.context?.code) {
            removeContext(tab.metaData.context.code);
          }
          let messageData = {
            tab_id: tab.id,
            tab_db_id: null,
            workspace_id: workspaceTab.id,
          };
          if (tab.metaData.mode == "query")
            messageData.tab_db_id = tab.metaData.initTabDatabaseId;
          tabsToRemove.push(messageData);
        }
      });
      let messageData = {
        workspace_id: workspaceTab.id,
        tab_db_id: null,
        tab_id: null,
      };
      tabsToRemove.push(messageData);

      if (tabsToRemove.length > 0) {
        createRequest(queryRequestCodes.CloseTab, tabsToRemove);
      }
      dbMetadataStore.deleteDbMeta(workspaceTab.metaData.selectedDatabaseIndex);
      this.removeTab(workspaceTab);
    },
    closeTabsForConnection(connectionId) {
      const tabsToClose = this.tabs.filter(
        (tab) => tab.metaData?.selectedDatabaseIndex === connectionId
      );
      tabsToClose.forEach((tab) => {
        if (tab.component === "WorkspaceTab") {
          this.closeWorkspaceTab(tab, this.getSecondaryTabs(tab.id));
        } else {
          this.closeTab(tab);
        }
      });
    },
  },
});

export { useTabsStore };
