<template>
  <div>
  <splitpanes class="default-theme query-body" horizontal @resized="handleResize">
    <pane size="30">
      <QueryEditor ref="editor" class="h-100 me-2"
        :read-only="readOnlyEditor"
        :tab-id="tabId"
        :workspace-id="workspaceId"
        :database-index="databaseIndex"
        :database-name="databaseName"
        tab-mode="query"
        :dialect="dialect" 
        :autocomplete="autocomplete"
        @editor-change="updateEditorContent" 
        @run-selection="queryRunOrExplain(false)" 
        @run-selection-explain="runExplain(0)"
        @run-selection-explain-analyze="runExplain(1)"
        />
    </pane>

    <pane size="70" class="border-top">
      <!-- ACTION BUTTONS-->
      <div class="py-2 pe-1 d-flex align-items-center">
        <div class="tab-actions d-flex w-100 px-2">
          <div class="btn-group me-2">
            <button class="btn btn-square btn-primary btn-run" title="Run" @click="queryRunOrExplain()" :disabled="executingState">
              <i class="fas fa-play fa-light"></i>
            </button>
  
            <button class="btn btn-square btn-primary btn-run" title="Run Selection" @click="queryRunOrExplain(false)" :disabled="executingState">
              [
              <i class="fas fa-play fa-light"></i>
              ]
            </button>
            <button type="button" class="btn btn-sm btn-primary dropdown-toggle dropdown-toggle-split ps-1" data-bs-toggle="dropdown" aria-expanded="false">
            </button>
            <ul class="dropdown-menu">
              <li>
                <a class="dropdown-item">
                  <input
                    :id="`check_autocommit_${tabId}`"
                    class="form-check-input me-1"
                    type="checkbox"
                    v-model="autocommit"
                  />
                  <label
                    class="form-check-label"
                    :for="`check_autocommit_${tabId}`"
                  >
                    Autocommit
                  </label>
                </a>
              </li>
            </ul>
          </div>

          <button class="btn btn-square btn-secondary" title="Indent SQL" @click="indentSQL()">
            <i class="fas fa-indent fa-light"></i>
          </button>

          <button class="btn btn-square btn-secondary" title="Find/Replace" @click="showFindReplace()">
            <i class="fas fa-magnifying-glass fa-light"></i>
          </button>

          <button class="btn btn-square btn-secondary me-2" title="Command History"
            @click="showCommandsHistory()">
            <i class="fas fa-clock-rotate-left fa-light"></i>
          </button>

          <button class="btn btn-square btn-secondary ms-2" title="Load from File" @click="openFileManagerModal">
            <i class="fas fa-folder-open fa-light"></i>
          </button>

          <button :disabled="fileSaveDisabled" class="btn btn-square btn-secondary me-2 " title="Save to File" @click="saveFile">
            <i class="fas fa-download fa-light"></i>
          </button>

          <template v-if="postgresqlDialect">
            <!-- EXPLAIN ANALYZE BUTTONS-->
            <div class="btn-group ms-2 me-2">
              <button class="btn btn-square btn-secondary" title="Explain" @click="runExplain(0)"
                :disabled="!enableExplainButtons">
                <i class="fas fa-chart-simple fa-light"></i>
              </button>

              <button class="btn btn-square btn-secondary" title="Explain Analyze"
                @click="runExplain(1)" :disabled="!enableExplainButtons">
                <i class="fas fa-magnifying-glass-chart fa-light"></i>
              </button>
            </div>

            <TabStatusIndicator :tab-status="tabStatus" />
          </template>

          <!-- Query ACTIONS BUTTONS-->
          <button v-show="showFetchButtons" class="btn btn-sm btn-secondary" title="Fetch More"
            @click="querySQL(queryModes.FETCH_MORE)">
            Fetch More
          </button>
          <BlockSizeSelector v-show="showFetchButtons" v-model="blockSize"/>

          <button class="btn btn-sm btn-secondary" title="Fetch All" v-show="showFetchButtons"
            @click="querySQL(queryModes.FETCH_ALL)">
            Fetch all
          </button>

          <button v-show="activeTransaction" class="btn btn-sm btn-primary" title="Commit"
            @click="querySQL(queryModes.COMMIT)">
            Commit
          </button>

          <button v-show="activeTransaction" class="btn btn-sm btn-secondary" title="Rollback"
            @click="querySQL(queryModes.ROLLBACK)">
            Rollback
          </button>

          <CancelButton v-show="executingState && longQuery" :tab-id="tabId" :workspace-id="workspaceId"
            @cancelled="cancelSQLTab()" />

          <!-- QUERY INFO-->
          <p class="m-0 h6" v-show="cancelled">
            <b>Cancelled</b>
          </p>
          <p v-show="showStartTimeAndDuration" class="h6 m-0  me-2">
            <b>Start time:</b> {{ formattedStartTime }}<br/>
            <b>Duration:</b> {{ formattedCompletionStatus }}
          </p>
          <p v-show="showStartTime" class=" m-0 h6">
            <b>Start time:</b> {{ formattedStartTime }}
          </p>

          <!-- EXPORT BUTTON with SELECT OPTIONS -->
          <button class="btn btn-square btn-primary ms-auto" title="Export Data" @click="exportData()">
            <i class="fas fa-download fa-light"></i>
          </button>

          <div class="form-group mb-0">
            <select v-model="exportType" class="form-select" style="width: 80px;">
              <option v-for="(name, value) in exportTypes" :value="value">
                {{ name }}
              </option>
            </select>
          </div>
        </div>
      </div>
      <QueryResultTabs ref="queryResults" :block-size="blockSize" :workspace-id="workspaceId" :tab-id="tabId" :editor-content="editorContent"
        :dialect="dialect" :tab-status="tabStatus" :resize-div="resizeResultDiv" @enable-explain-buttons="toggleExplainButtons"
        @run-explain="runExplain(0)" @show-fetch-buttons="toggleFetchButtons" @resized="resizeResultDiv = false"/>
    </pane>
  </splitpanes>
</div>
</template>

<script>
import { Splitpanes, Pane } from "splitpanes";
import { showToast } from "../notification_control";
import moment from "moment";
import { createRequest } from "../long_polling";
import { queryModes, requestState, tabStatusMap, queryRequestCodes } from "../constants";
import CancelButton from "./CancelSQLButton.vue";
import QueryEditor from "./QueryEditor.vue";
import { emitter } from "../emitter";
import { flashHighlight } from "../utils";
import TabStatusIndicator from "./TabStatusIndicator.vue";
import QueryResultTabs from "./QueryResultTabs.vue";
import FileInputChangeMixin from '../mixins/file_input_mixin'
import { tabsStore, connectionsStore, messageModalStore, fileManagerStore, commandsHistoryStore } from "../stores/stores_initializer";
import BlockSizeSelector from './BlockSizeSelector.vue';
import { saveBlobAs } from '../utils/native_dialog';

export default {
  name: "QueryTab",
  components: {
    Splitpanes,
    Pane,
    CancelButton,
    QueryEditor,
    TabStatusIndicator,
    QueryResultTabs,
    BlockSizeSelector
  },
  mixins: [FileInputChangeMixin],
  props: {
    workspaceId: String,
    tabId: String,
    databaseIndex: Number,
    databaseName: String,
    dialect: String,
    initTabDatabaseId: Number,
    initialQuery: String,
  },
  data() {
    return {
      queryState: requestState.Idle,
      tabStatus: tabStatusMap.NOT_CONNECTED,
      autocommit: true,
      queryStartTime: "",
      queryDuration: "",
      queryRowsAffected: null,
      queryOffset: 0,
      data: "",
      context: "",
      tempData: [],
      tabDatabaseId: this.initTabDatabaseId,
      cancelled: false,
      enableExplainButtons: false,
      exportTypes: {
        csv: "CSV",
        "csv-no_headers": "CSV(no headers)",
        xlsx: "XLSX",
        "xlsx-no_headers": "XLSX(no headers)",
        json: "JSON"
      },
      exportType: "csv",
      showFetchButtons: false,
      readOnlyEditor: false,
      editorContent: "",
      longQuery: false,
      lastQuery: null,
      queryInterval: null,
      resizeResultDiv: false,
      blockSize: 50,
    };
  },
  computed: {
    postgresqlDialect() {
      return this.dialect === "postgresql";
    },
    idleState() {
      return this.queryState === requestState.Idle;
    },
    executingState() {
      return this.queryState === requestState.Executing;
    },
    activeTransaction() {
      return [
        tabStatusMap.IDLE_IN_TRANSACTION,
        tabStatusMap.IDLE_IN_TRANSACTION_ABORTED,
      ].includes(this.tabStatus);
    },
    queryModes() {
      return queryModes;
    },
    autocomplete() {
      return connectionsStore.getConnection(this.databaseIndex).autocomplete
    },
    fileSaveDisabled() {
      return !this.editorContent;
    },
    hasChanges() {
      let lastQueryModified = (!!this.lastQuery && this.lastQuery !== this.editorContent)
      let initialQueryModified = (!this.initialQuery && !!this.editorContent && this.lastQuery !== this.editorContent)
      let runningQuery = this.activeTransaction || this.executingState
      return initialQueryModified || lastQueryModified || runningQuery
    },
    showStartTimeAndDuration() {
      return !this.cancelled && this.queryStartTime && this.queryDuration;
    },
    showStartTime() {
      return !this.cancelled && this.queryStartTime && !this.queryDuration;
    },
    formattedStartTime() {
      return this.queryStartTime ? this.queryStartTime.format() : '';
    },
    formattedCompletionStatus() {
      return this.queryRowsAffected !== null
        ? `${this.queryDuration}, ${this.queryRowsAffected} rows affected`
        : this.queryDuration;
    }
  },
  mounted() {
    this.setupEvents();

    if (!!this.initialQuery) {
      emitter.emit(`${this.tabId}_copy_to_editor`, this.initialQuery);
    }
  },
  unmounted() {
    this.clearEvents();
  },
  updated() {
    if (tabsStore.selectedPrimaryTab?.metaData?.selectedTab?.id === this.tabId) {
      this.handleResize()
    }
  },
  methods: {
    getEditorContent(fullContent=false, onlySelected=false) {
      return this.$refs.editor.getEditorContent(fullContent, onlySelected)
    },
    querySQL(
      mode,
      cmd_type = null,
      all_data = false,
      query = this.getEditorContent(true),
      log_query = true,
      save_query = this.editorContent,
      clear_data = false
    ) {
      if (!this.idleState) {
        showToast("info", "Tab with activity in progress.");
      } else {
        if (!query) {
          showToast("info", "Please provide a string.");
        } else {
          let tab = tabsStore.getSelectedSecondaryTab(this.workspaceId);
          this.queryDuration = "";
          this.queryRowsAffected = null;
          this.cancelled = false;
          this.showFetchButtons = false;
          this.longQuery = false;
          this.tempData = [];
          this.lastQuery = query.trim();
          if (cmd_type === "explain" && this.getEditorContent(true) !== query) {
            this.lastQuery = this.getEditorContent(true);
          } 

          let message_data = {
            sql_cmd: query,
            mode: mode,
            autocommit: this.autocommit,
            db_index: this.databaseIndex,
            workspace_id: this.workspaceId,
            tab_id: this.tabId,
            tab_db_id: this.tabDatabaseId,
            sql_save: save_query,
            database_name: this.databaseName,
            cmd_type: cmd_type,
            all_data: all_data,
            log_query: log_query,
            tab_title: tab.name,
            block_size: this.blockSize
          };

          this.readOnlyEditor = true;
          this.queryStartTime = moment();

          let context = {
            tab: tab,
            database_index: this.databaseIndex,
            acked: false,
            clear_data: clear_data,
            cmd_type: cmd_type,
            mode: mode,
            callback: this.querySQLReturn.bind(this),
            passwordSuccessCallback: this.passwordSuccessCallback.bind(this),
            passwordFailCalback: () => {
              emitter.emit(`${this.tabId}_cancel_query`);
            },
          };

          context.tab.metaData.context = context;

          createRequest(queryRequestCodes.Query, message_data, context);
          this.$refs.editor.editor.getSession().clearAnnotations()
          this.queryState = requestState.Executing;

          setTimeout(() => {
            if (this.queryState === requestState.Executing) {
              tab.metaData.isLoading = true;
              this.longQuery = true;
            }
          }, 1000);

          this.queryInterval = setInterval((function(){
            let diff = moment().diff(this.queryStartTime)
            this.queryDuration = moment.utc(diff).format('HH:mm:ss')
          }).bind(this), 1000)

          tab.metaData.isReady = false;

          this.tabStatus = tabStatusMap.RUNNING;
        }
      }
    },
    querySQLReturn(data, context) {
      if (!data.error) {
        Array.prototype.push.apply(this.tempData, data.data.data)
      }

      if(data.error && data.data?.position) {
        let pos = data.data.position
        this.$refs.editor.editor.getSession().setAnnotations([{
            row: pos.row - 1 + this.queryOffset, //annotation rows are counted from 0
            column: pos.col,
            text: data.data.message,
            type: "error"
          }]);
      }
      //Update tab_db_id if not null in response
      if (data.data.inserted_id) {
        let tab = tabsStore.getSecondaryTabById(this.tabId, this.workspaceId);
        this.tabDatabaseId = data.data.inserted_id;
        tab.metaData.initTabDatabaseId = data.data.inserted_id;
      }

      //If query wasn't canceled already

      if (!this.idleState && (data.data.last_block || data.data.file_name || data.error )) {
        data.data.data = this.tempData;
        this.tempData = [];
        this.readOnlyEditor = false;
        this.tabStatus = data.data.con_status;
        clearInterval(this.queryInterval)
        this.queryInterval = null;
        if (
          this.workspaceId === tabsStore.selectedPrimaryTab.id &&
          this.tabId === tabsStore.selectedPrimaryTab.metaData.selectedTab.id
        ) {
          this.context = "";
          this.data = "";

          this.queryState = requestState.Idle;
          this.$refs.queryResults.renderResult(data, context);

          this.queryDuration = data.data.duration;
          this.queryRowsAffected = data.data.rows_affected ?? null;

          context.tab.metaData.isReady = false;
          context.tab.metaData.isLoading = false;
        } else {
          this.queryState = requestState.Ready;
          this.data = data;
          this.context = context;

          context.tab.metaData.isReady = true
          context.tab.metaData.isLoading = false
        }
      }
    },
    runExplain(explainMode) {
      let command = this.getEditorContent();

      if (command.trim() === "") {
        showToast("info", "Please provide a string.");
      } else {
        let explainRegex =
          /^(EXPLAIN ANALYZE|EXPLAIN)\s*(\([^\)\(]+\))?\s+(.+)/is;
        let queryMatch = command.match(explainRegex);
        if (queryMatch) {
          command = queryMatch[3] ?? command;
        }

        if (explainMode === 0) {
          command = "explain " + command;
        } else if (explainMode === 1) {
          command = "explain (analyze, buffers) " + command;
        }

        this.querySQL(
          this.queryModes.DATA_OPERATION,
          "explain",
          true,
          command,
          false
        );
      }
    },
    queryRunOrExplain(use_raw_query=true) {
      let query = this.getEditorContent(use_raw_query, true)
      if (this.dialect === "postgresql") {
        let should_explain =
          query.trim().split(" ")[0].toUpperCase() === "EXPLAIN";
        if (should_explain) {
          return this.querySQL(
            this.queryModes.DATA_OPERATION,
            "explain",
            true,
            query,
            false
          );
        }
      }

      // queryOffset is needed to correctly annotate errors when "Run Selection" is used
      this.queryOffset = use_raw_query ? 0 : this.$refs.editor.getQueryOffset()
      this.querySQL(this.queryModes.DATA_OPERATION, null, false, query=query)
    },
    exportData() {
      let cmd_type = `export_${this.exportType}`;
      let command = this.lastQuery || this.getEditorContent(true);
      let explainRegex =
          /^(EXPLAIN ANALYZE|EXPLAIN)\s*(\([^\)\(]+\))?\s+(.+)/is;
      let queryMatch = command.match(explainRegex);
      if (queryMatch) {
        command = queryMatch[3] ?? command;
      }
      this.querySQL(
        this.queryModes.DATA_OPERATION,
        cmd_type,
        true,
        command,
        true,
        command,
        true
      );
    },
    cancelSQLTab() {
      clearInterval(this.queryInterval);
      this.queryInterval = null;

      this.readOnlyEditor = false;

      this.queryState = requestState.Idle;
      this.tabStatus = tabStatusMap.NOT_CONNECTED;

      this.cancelled = true;
    },
    indentSQL() {
      emitter.emit(`${this.tabId}_indent_sql`);
    },
    showFindReplace() {
      emitter.emit(`${this.tabId}_find_replace`);
    },
    updateEditorContent(newContent) {
      this.editorContent = newContent;
    },
    toggleFetchButtons(newValue) {
      this.showFetchButtons = newValue;
    },
    toggleExplainButtons() {
      this.enableExplainButtons = !this.enableExplainButtons;
    },
    passwordSuccessCallback(context) {
      emitter.emit(`${this.tabId}_cancel_query`);

      this.querySQL(
        context.mode,
        context.cmd_type,
        context.all_data,
        context.query,
        context.log_query,
        context.save_query,
        context.clear_data
      );
    },
    setupEvents() {
      emitter.on(`${this.tabId}_check_query_status`, () => {
        this.$refs.editor.focus();
        if (this.queryState === requestState.Ready) {
          this.context.tab.metaData.isReady = false;
          this.context.tab.metaData.isLoading = false;
          this.queryState = requestState.Idle;

          this.$refs.queryResults.renderResult(this.data, this.context);
        }
      });

      emitter.on(`${this.tabId}_run_query`, (sql_command) => {
        if (sql_command) {
          emitter.emit(`${this.tabId}_copy_to_editor`, sql_command);
        }
        this.queryRunOrExplain();
      });

      emitter.on(`${this.tabId}_run_selection`, (sql_command) => {
        this.queryRunOrExplain(false)
      });

      emitter.on(`${this.tabId}_run_explain`, () => {
        this.runExplain(0);
      });

      emitter.on(`${this.tabId}_run_explain_analyze`, () => {
        this.runExplain(1);
      });

      emitter.on(`${this.tabId}_focus`, () => {
        this.$refs.editor.focus();
        flashHighlight(this.$refs.editor.$el);
      });

      emitter.on(`${this.tabId}_focus_secondary`, () => {
        this.$refs.queryResults.focus();
        flashHighlight(this.$refs.queryResults.$el);
      });
    },
    clearEvents() {
      emitter.all.delete(`${this.tabId}_check_query_status`);
      emitter.all.delete(`${this.tabId}_run_explain`);
      emitter.all.delete(`${this.tabId}_run_explain_analyze`);
      emitter.all.delete(`${this.tabId}_run_query`);
      emitter.all.delete(`${this.tabId}_run_selection`);
      emitter.all.delete(`${this.tabId}_focus`);
      emitter.all.delete(`${this.tabId}_focus_secondary`);
    },
    showCommandsHistory() {
      commandsHistoryStore.showModal(this.tabId, this.databaseIndex, "Query");
    },
    openFileManagerModal() {
      if (!!this.editorContent) {
        messageModalStore.showModal(
          "Are you sure you wish to discard the current changes?",
          () => {
            fileManagerStore.showModal(true, this.handleFileInputChange);
          },
          null
        );
      } else {
        fileManagerStore.showModal(true, this.handleFileInputChange);
      }
    },
    async saveFile() {
      const today = new Date()
      const nameSuffix = `${today.getHours()}${today.getMinutes()}`
      let tab = tabsStore.getSelectedSecondaryTab(this.workspaceId);
      const fileName = tab.metaData?.editingFile ? tab.name : `pgmanage-query-${nameSuffix}.sql`

      const file = new File([this.editorContent], fileName, {
        type: "application/sql",
      })

      if(window.showSaveFilePicker) {
        try {
          const handle = await showSaveFilePicker(
            { suggestedName: file.name,
              types: [{
                description: 'SQL Script',
                accept: {
                  'application/sql': ['.sql'],
                }
              }],
            }
          )

          const writable = await handle.createWritable()
          await writable.write(file)
          writable.close()
        } catch(e) {
          console.log(e)
        }

      } else {
        await saveBlobAs(file, file.name);
      }
    },
    handleResize() {
      this.resizeResultDiv = true
    }
  },
  watch: {
    hasChanges() {
      const tab = tabsStore.getSecondaryTabById(this.tabId, this.workspaceId);
      if (tab) {
        tab.metaData.hasUnsavedChanges = this.hasChanges;
      }
    },
  }
};
</script>

<style scoped>
.query-body {
  height: calc(100vh - 2.5rem);
  /* padding-top: 16px; */
}

.tab-actions {
  align-items: center;
  display: flex;
  justify-content: flex-start;
  min-height: 35px;
}

.tab-actions>button {
  margin-right: 5px;
}

.splitpanes .splitpanes__pane {
  transition: none;
}

.btn-run {
  padding-left: 2px;
  padding-right: 2px;
}

.btn-run i {
    margin-left: -3px;
    margin-right: -3px;
}
</style>
