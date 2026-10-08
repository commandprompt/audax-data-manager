<template>
  <div data-testid="connection-tab" class="container-fluid position-relative g-0">
    <div class="row g-0">
      <splitpanes @resized="handleDatabaseTreeWidthChange" class="default-theme">
        <pane min-size="18" size="25">
          <div
            :id="`${workspaceId}_div_left`"
            class="omnidb__workspace__div-left col"
          >
            <div class="row g-0">
              <div class="omnidb__workspace__content-left border-end">
                <div class="omnidb__workspace__connection-details d-flex align-items-center flex-wrap-wrap justify-content-between">
                  <p class="d-flex align-items-center flex-nowrap mb-0">
                    <span class="text-nowrap">Selected DB:&nbsp;</span>
                    <span class="text-info">{{ databaseName }}</span>
                  </p>
                  
                  <div class="d-flex align-items-center">
                    <button class="btn btn-icon btn-icon-primary me-2" title="Quick Search" @click="showQuickSearch">
                      <i class="fa-solid fa-magnifying-glass px-2"></i>
                    </button>
                    <div
                      :id="`${workspaceId}_switch`"
                      class="omnidb__switch omnidb__switch--sm"
                      data-bs-toggle="tooltip"
                      data-bs-placement="bottom"
                      data-bs-html="true"
                      data-bs-title="<h5>Toggle autocomplete.</h5><div>Switch OFF <b>disables the autocomplete</b> on the inner tabs for this connection.</div>"
                    >
                      <input
                        type="checkbox"
                        :id="`${workspaceId}_autocomplete`"
                        class="omnidb__switch--input"
                        v-model="autocompleteStatus"
                        @change="emitConnectionSave"
                      />
                      <label
                        :for="`${workspaceId}_autocomplete`"
                        class="omnidb__switch--label"
                      >
                        <span>
                          <i class="fas fa-spell-check"></i>
                        </span>
                      </label>
                    </div>
                  </div>
                </div>
                <splitpanes
                  class="left-div-panes default-theme"
                  horizontal
                  @resized="handleDatabaseTreeResize"
                >
                  <pane :size="100 - treeTabsPaneSize">
                    <div :id="`${workspaceId}_tree`" class="database-tree">
                      <component
                        :is="treeComponent"
                        :workspace-id="workspaceId"
                        :database-index="databaseIndex"
                        @tree-tabs-update="getProperties"
                        @clear-tabs="clearTreeTabsData"
                      ></component>
                    </div>
                  </pane>

                  <pane
                    min-size="2"
                    :size="treeTabsPaneSize"
                    style="min-height: 2rem"
                  >
                    <TreePropertiesDDL
                      :workspace-id="workspaceId"
                      :database-technology="databaseTechnology"
                      :ddl-data="ddlData"
                      :properties-data="propertiesData"
                      :show-loading="showTreeTabsLoading"
                      :is-visible="isTreeTabsVisible"
                      :db-explorer-width="dbExplorerWidth"
                      @show-tree-tabs="showTreeTabPane"
                      @hide-tree-tabs="hideTreeTabpane"
                    />
                  </pane>
                </splitpanes>
              </div>
            </div>
          </div>
        </pane>
        <pane min-size="2">
          <div
            :id="`${workspaceId}_div_right`"
            class="omnidb__workspace__div-right col position-relative vh-100"
          >
            <div class="row">
              <DatabaseTabs
                :id="`${workspaceId}`"
                class="w-100"
                :workspace-id="workspaceId"
                :color-label-class='workspaceTab.metaData?.colorLabelClass'
              />
            </div>
          </div>
        </pane>
      </splitpanes>
    </div>
    <SearchModal :workspace-id="workspaceId" :database-index="databaseIndex" :database-technology="databaseTechnology" />
  </div>
</template>

<script>
import DatabaseTabs from "./DatabaseTabs.vue";
import { tabsStore, connectionsStore } from "../stores/stores_initializer";
import axios from "axios";
import { defineAsyncComponent } from "vue";
import { emitter } from "../emitter";
import { truncateText } from "../utils";
import { Splitpanes, Pane } from "splitpanes";
import TreePropertiesDDL from "./TreePropertiesDDL.vue";
import TabTitleUpdateMixin from "../mixins/sidebar_title_update_mixin";
import { Tooltip } from "bootstrap";
import { handleError } from "../logging/utils";
import SearchModal from "./SearchModal.vue";
import debounce from 'lodash/debounce'
import { dialectOf } from "../constants";

export default {
  name: "WorkspaceTab",
  components: {
    DatabaseTabs,
    TreePostgresql: defineAsyncComponent(() => import("@conditional/components/TreePostgresql.vue")),
    TreeSqlite: defineAsyncComponent(() => import("./TreeSqlite.vue")),
    TreeMariaDB: defineAsyncComponent(() => import("./TreeMariaDB.vue")),
    TreeOracle: defineAsyncComponent(() => import("./TreeOracle.vue")),
    TreeMysql: defineAsyncComponent(() => import("./TreeMysql.vue")),
    TreeMssql: defineAsyncComponent(() => import("./TreeMssql.vue")),
    Splitpanes,
    Pane,
    TreePropertiesDDL,
    SearchModal,
  },
  mixins: [TabTitleUpdateMixin],
  props: {
    workspaceId: String,
  },
  data() {
    return {
      ddlData: "",
      dbExplorerWidth: 18,
      propertiesData: [],
      treeTabsPaneSize: 2,
      lastTreeTabsPaneSize: null,
      showTreeTabsLoading: false,
      lastTreeTabsData: null,
      lastTreeTabsView: null,
      treeTabsDataStale: false,
    };
  },
  computed: {
    workspaceTab() {
      return tabsStore.getPrimaryTabById(this.workspaceId);
    },
    databaseConnection() {
      return connectionsStore.getConnection(this.databaseIndex);
    },
    autocompleteStatus: {
      get() {
        return this.databaseConnection.autocomplete;
      },
      set(value) {
        let connection = connectionsStore.getConnection(this.databaseIndex);
        connection.autocomplete = value;
      },
    },
    databaseIndex() {
      return this.workspaceTab.metaData.selectedDatabaseIndex;
    },
    databaseTechnology() {
      return this.workspaceTab.metaData.selectedDBMS;
    },
    databaseName() {
      if (this.databaseTechnology === "sqlite") {
        return truncateText(this.workspaceTab.metaData.selectedDatabase, 10);
      }
      return this.workspaceTab.metaData.selectedDatabase;
    },
    treeComponent() {
      const treeTechnologiesMap = {
        postgresql: "TreePostgresql",
        sqlite: "TreeSqlite",
        mysql: "TreeMysql",
        mariadb: "TreeMariaDB",
        oracle: "TreeOracle",
        mssql: "TreeMssql"
      };
      return treeTechnologiesMap[this.databaseTechnology];
    },
    isTreeTabsVisible() {
      return this.treeTabsPaneSize !== 2;
    },
  },
  mounted() {
    this.changeDatabase(this.workspaceTab.metaData.selectedDatabaseIndex);
    this.subscribeToConnectionChanges(this.workspaceId, this.databaseIndex);
    this.$nextTick(() => {
      if (this.workspaceTab.metaData.createInitialTabs) {
        let name = tabsStore.selectedPrimaryTab.metaData.selectedDatabase.replace('\\', '/').split('/').pop()
        tabsStore.createConsoleTab();
        tabsStore.createQueryTab(name);
      }
    });

    new Tooltip(`#${this.workspaceId}_switch`, {
      boundary: "window",
      trigger: 'hover'
    });
  },
  methods: {
    changeDatabase(value) {
      let connObject = null;

      // Finding the connection object.
      for (let i = 0; i < connectionsStore.connections.length; i++) {
        if (value == connectionsStore.connections[i].id) {
          connObject = connectionsStore.connections[i];
          break;
        }
      }

      // Selecting the first connection when none is found.

      if (!connObject) {
        connObject = connectionsStore.connections[0];
      }

      let tabData = tabsStore.getPrimaryTabById(this.workspaceId);

      tabData.metaData.selectedDatabaseIndex = value;
      tabData.metaData.selectedDBMS = dialectOf(connObject.technology);
      tabData.metaData.consoleHelp = connObject.console_help;
      tabData.metaData.selectedDatabase =
        connObject.last_used_database || connObject.service;
      tabData.metaData.selectedTitle = connObject.alias;

      if (["oracle", "sqlite"].includes(connObject.technology)) {
        connectionsStore.queueChangeActiveDatabaseThreadSafe({
          database_index: value,
          workspace_id: this.workspaceId,
          database: tabData.metaData.selectedDatabase,
        });
      } else {
        axios
          .post(`/get_databases_${dialectOf(connObject.technology)}/`, {
            database_index: value,
            workspace_id: this.workspaceId,
          })
          .then((resp) => {
            if (
              !resp.data
                .map((database) => database.name)
                .includes(tabData.metaData.selectedDatabase)
            ) {
              tabData.metaData.selectedDatabase = connObject.service;
            }
            connectionsStore.queueChangeActiveDatabaseThreadSafe({
              database_index: value,
              workspace_id: this.workspaceId,
              database: tabData.metaData.selectedDatabase,
            });
          })
          .catch((error) => {
            if (error?.response?.data?.password_timeout) return
            handleError(error);
          });
      }
    },
    emitConnectionSave() {
      let connection = connectionsStore.getConnection(this.databaseIndex);
      emitter.emit("connection-save", connection);
    },
    debouncedFetchProperties: debounce(function(view, data) {
      let loadingTimeout = setTimeout(() => {
        this.showTreeTabsLoading = true;
      }, 1000);

      axios
        .post(view, {
          database_index: this.databaseIndex,
          workspace_id: this.workspaceId,
          data: data,
        })
        .then((resp) => {
          clearTimeout(loadingTimeout);
          this.propertiesData = resp.data.properties;
          this.ddlData = resp.data.ddl;
          this.showTreeTabsLoading = false;
        })
        .catch((error) => {
          clearTimeout(loadingTimeout);
          if (error?.response?.data?.password_timeout) {
            emitter.emit("show_password_prompt", {
              databaseIndex: this.databaseIndex,
              successCallback: () => {
                this.getProperties(view, data);
              },
              message: error.response.data.data,
            });
          } else {
            handleError(error);
          }
          this.showTreeTabsLoading = false;
        });
    }, 200),
    getProperties({ view, data }) {
      // remember last DB object to load properties for
      // use this data later when properties/ddl is expanded
      this.lastTreeTabsData = data;
      this.lastTreeTabsView = view;

      if (!this.isTreeTabsVisible) {
        this.treeTabsDataStale = true;
        return;
      }

      this.treeTabsDataStale = false;
      this.debouncedFetchProperties(view, data);
    },
    clearTreeTabsData() {
      this.ddlData='';
      this.propertiesData=[];
    },
    showTreeTabPane() {
      this.treeTabsPaneSize = this.lastTreeTabsPaneSize || 40;
      if (this.treeTabsDataStale && !!this.lastTreeTabsData && !!this.lastTreeTabsView)
        this.getProperties({
          data: this.lastTreeTabsData,
          view: this.lastTreeTabsView,
        });
    },
    hideTreeTabpane() {
      this.lastTreeTabsPaneSize = this.treeTabsPaneSize;
      this.treeTabsPaneSize = 2;
    },
    handleDatabaseTreeResize(event) {
      this.treeTabsPaneSize = event[1].size < 5 ? 2 : event[1].size;
      if (this.treeTabsPaneSize !== 2)  {
        this.lastTreeTabsPaneSize = this.treeTabsPaneSize;
      }
    },
    handleDatabaseTreeWidthChange(event) {
      this.dbExplorerWidth = event[1].size;
      const selectedTab = tabsStore.getSelectedSecondaryTab(this.workspaceId);
      if (selectedTab) {
        emitter.emit(`${selectedTab.id}_resize`);
      }
    },
    showQuickSearch(event) {
      emitter.emit(`${this.workspaceId}_show_quick_search`, event);
    },
  },
};
</script>

<style scoped>
.left-div-panes {
  height: calc(100vh - 30px);
}

.database-tree {
  overflow: auto;
  transition: scroll 0.3s;
  height: 100%;
}
</style>
