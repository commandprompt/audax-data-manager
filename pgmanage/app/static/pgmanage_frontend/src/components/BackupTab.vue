<template>
  <div ref="highlightEl" class="backup-tab-scrollable p-2">
  <form @submit.prevent>
      <div class="row">
        <div class="col-4 d-flex">
          <div class="card flex-grow-1">
            <h4 class="card-header fw-bold px-3 py-2">General</h4>
            <div class="card-body d-flex flex-column px-3 py-2">
              <div class="form-group mb-2">
                <label :for="`${backupTabId}_backupFileName`" class="fw-bold mb-1">File name</label>
                  <div class="input-group">
                      <button class="btn btn-secondary" @click="openFileManagerModal">Select</button>
                        <input :id="`${backupTabId}_backupFileName`" type="text" class="form-control" :value="truncateText(backupOptions.fileName, 20)"
                          placeholder="backup file" disabled>
                    </div>
                  </div>
                  <div v-if="isObjectsType" class="form-group mb-2">
                    <label for="backupFormat" class="fw-bold mb-1">Format</label>
                    <select id="backupFormat" class="form-select" v-model="backupOptions.format">
                      <option v-for="(value, key) in formats" :value="key" :key="key">{{ value }}</option>
                    </select>
                  </div>
                  <div class="row mt-1">
                    <div
                      v-tooltip
                      data-bs-toggle="tooltip"
                      data-bs-placement="bottom"
                      data-bs-title="Backup compression level. 0 is faster with minimal space saving; 9 provides maximum space savings, but is slower."
                      class="form-group col-6 d-flex flex-column justify-content-end mb-1">
                      <label for="backupCompressionRatio" class="fw-bold mb-1">Compression level</label>
                      <select id="backupCompressionRatio" class="form-select" v-model="backupOptions.compression_ratio" :disabled="isTarFormat || (isServerType && !backupOptions.pigz)">
                        <option value="" disabled>Select an item...</option>
                        <option v-for="compress_ratio in compressionRatioValues" :value="compress_ratio" :key="compress_ratio">{{ compress_ratio }}</option>
                      </select>
                    </div>

                    <div
                      v-tooltip
                      data-bs-toggle="tooltip"
                      data-bs-placement="bottom"
                      data-bs-title="Sets parallel processes to speed up backups. Controls pg_dump workers for Directory format, or pigz compressor threads if Pigz is enabled."
                      class="form-group col-6 d-flex flex-column justify-content-end mb-1">
                      <label for="backupNumberOfJobs" class="fw-bold mb-1">Number of jobs</label>
                      <select id="backupNumberOfJobs" class="form-select" v-model="backupOptions.number_of_jobs" :disabled="isTarFormat || (isServerType && !backupOptions.pigz)">
                        <option value="" disabled>Select an item...</option>
                        <option v-for="number_of_jobs in numberOfJobs" :value="number_of_jobs" :key="number_of_jobs">{{ number_of_jobs }}</option>
                      </select>
                    </div>

                    <div v-if="!isWindowsOS" class="form-group col align-content-end mb-1">
                      <div class="form-check form-switch">
                        <input class="form-check-input" type="checkbox" :id="`${backupTabId}_backupOptionsPigz`" v-model="backupOptions.pigz" :disabled="isDirectoryFormat || isTarFormat">
                        <label class="form-check-label" :for="`${backupTabId}_backupOptionsPigz`">
                          Compress with Pigz
                        </label>
                      </div>
                    </div>
                  </div>

                  <div 
                    v-tooltip
                    data-bs-toggle="tooltip"
                    data-bs-placement="bottom"
                    data-bs-title="The character set encoding to use for the backup file."
                    class="form-group my-1">
                    <label for="backupEncoding" class="fw-bold mb-1">Encoding</label>
                    <select ref="focusableEl" id="backupEncoding" class="form-select" v-model="backupOptions.encoding">
                      <option value="">Use database encoding</option>
                      <option v-for="encoding in encodingList" :key="encoding" :value="encoding">{{ encoding }}</option>
                    </select>
                  </div>

                  <div class="row mt-1">
                    <div
                      v-tooltip
                      data-bs-toggle="tooltip"
                      data-bs-placement="bottom"
                      data-bs-title="The database role to use when creating the backup."
                      class="form-group col-6 d-flex flex-column justify-content-end"
                      >
                      <label for="backupRoleName" class="fw-bold mb-1">Backup as:</label>
                      <select id="backupRoleName" class="form-select" v-model="backupOptions.role">
                        <option value="" disabled>Select an item...</option>
                        <option v-for="name in roleNames" :value="name" :key="name">{{ name }}</option>
                      </select>
                    </div>
                    <div
                      v-if="pgKeys.length"
                      v-tooltip
                      class="form-group col-6 d-flex flex-column justify-content-end"
                      data-bs-toggle="tooltip"
                      data-bs-placement="bottom"
                      data-bs-title="The Postgres client binary version used for the backup. A version matching the database server is preferred; otherwise, the latest available version is used."
                      >
                        <label class="fw-bold mb-1">PG version:</label>
                        <select class="form-select" v-model="backupOptions.pg_version">
                          <option v-for="k in pgKeys" :key="k" :value="k">
                            {{ k }}
                          </option>
                        </select>
                    </div>
                  </div>

                  <div v-if="isServerType" class="d-flex fst-italic mt-auto muted-text">
                    <i class="fa-solid fa-circle-info me-1"></i>
                    <p>The backup will be in PLAIN format.</p>
                  </div>
            </div>
          </div>
        </div>


        <div class="col-4 d-flex">
          <div class="card flex-grow-1">
            <h4 class="card-header fw-bold px-3 py-2">Data/Objects</h4>
            <div class="card-body px-3 py-2">
              <div v-if="isObjectsType" class="form-group mb-1">
                <p class="fw-bold mb-2">Sections</p>
                <div class="form-check form-switch">
                  <input class="form-check-input" type="checkbox" :id="`${backupTabId}_backupOptionsPreData`"
                    v-model="backupOptions.pre_data" :disabled="isOnlyDataOrSchemaSelected">
                  <label class="form-check-label" :for="`${backupTabId}_backupOptionsPreData`">
                    Pre-data
                  </label>
                </div>
                <div class="form-check form-switch">
                  <input class="form-check-input" type="checkbox" :id="`${backupTabId}_backupOptionsData`" v-model="backupOptions.data"
                    :disabled="isOnlyDataOrSchemaSelected">
                  <label class="form-check-label" :for="`${backupTabId}_backupOptionsData`">
                    Data
                  </label>
                </div>
                <div class="form-check form-switch">
                  <input class="form-check-input" type="checkbox" :id="`${backupTabId}_backupOptionsPostData`"
                    v-model="backupOptions.post_data" :disabled="isOnlyDataOrSchemaSelected">
                  <label class="form-check-label" :for="`${backupTabId}_backupOptionsPostData`">
                    Post-data
                  </label>
                </div>
              </div>

              <div class="form-group mb-1">
                <p class="fw-bold mb-1">Type of objects</p>
                <div class="form-check form-switch">
                  <input class="form-check-input" type="checkbox" :id="`${backupTabId}_backupOptionsOnlyData`"
                    v-model="backupOptions.only_data"
                    :disabled="backupOptions.pre_data || backupOptions.data || backupOptions.post_data || backupOptions.include_drop_commands">
                  <label class="form-check-label" :for="`${backupTabId}_backupOptionsOnlyData`">
                    Only data
                  </label>
                </div>
                <div class="form-check form-switch">
                  <input class="form-check-input" type="checkbox" :id="`${backupTabId}_backupOptionsOnlySchema`"
                    v-model="backupOptions.only_schema"
                    :disabled="backupOptions.pre_data || backupOptions.data || backupOptions.post_data">
                  <label class="form-check-label" :for="`${backupTabId}_backupOptionsOnlySchema`">
                    Only schema
                  </label>
                </div>
                <div v-if="isObjectsType" class="form-check form-switch">
                  <input class="form-check-input" type="checkbox" :id="`${backupTabId}_backupOptionsBlobs`" v-model="backupOptions.blobs">
                  <label class="form-check-label" :for="`${backupTabId}_backupOptionsBlobs`">
                    Blobs
                  </label>
                </div>
                <div v-if="isServerType" class="form-check form-switch">
                  <input class="form-check-input" type="checkbox" :id="`${backupTabId}_backupOptionsOnlyRoles`"
                    v-model="backupOptions.only_roles" 
                    :disabled="backupOptions.only_tablespaces || backupOptions.only_globals">
                  <label class="form-check-label" :for="`${backupTabId}_backupOptionsOnlyRoles`">
                    Only roles
                  </label>
                </div>
                <div v-if="isServerType" class="form-check form-switch">
                  <input class="form-check-input" type="checkbox" :id="`${backupTabId}_backupOptionsOnlyTablespaces`"
                    v-model="backupOptions.only_tablespaces"
                    :disabled="backupOptions.only_roles || backupOptions.only_globals">
                  <label class="form-check-label" :for="`${backupTabId}_backupOptionsOnlyTablespaces`">
                    Only tablespaces
                  </label>
                </div>
                <div v-if="isServerType" class="form-check form-switch">
                <input class="form-check-input" type="checkbox" :id="`${backupTabId}_backupOptionsOnlyGlobals`"
                  v-model="backupOptions.only_globals"
                  :disabled="backupOptions.only_roles || backupOptions.only_tablespaces">
                <label class="form-check-label" :for="`${backupTabId}_backupOptionsOnlyGlobals`">
                  Only global objects
                </label>
              </div>
              </div>

              <div class="form-group mb-0">
                <p class="fw-bold mb-2">Do not save</p>
                <div class="form-check form-switch">
                  <input class="form-check-input" type="checkbox" :id="`${backupTabId}_backupOptionsOwner`" v-model="backupOptions.owner">
                  <label class="form-check-label" :for="`${backupTabId}_backupOptionsOwner`">
                    Owner
                  </label>
                </div>
                <div class="form-check form-switch">
                  <input class="form-check-input" type="checkbox" :id="`${backupTabId}_backupOptionsPrivilege`"
                    v-model="backupOptions.privilege">
                  <label class="form-check-label" :for="`${backupTabId}_backupOptionsPrivilege`">
                    Privilege
                  </label>
                </div>
                <div class="form-check form-switch">
                  <input class="form-check-input" type="checkbox" :id="`${backupTabId}_backupOptionsTablespace`"
                    v-model="backupOptions.tablespace">
                  <label class="form-check-label" :for="`${backupTabId}_backupOptionsTablespace`">
                    Tablespace
                  </label>
                </div>
                <div class="form-check form-switch">
                  <input class="form-check-input" type="checkbox" :id="`${backupTabId}_backupOptionsUnloggedTableData`"
                    v-model="backupOptions.unlogged_tbl_data">
                  <label class="form-check-label" :for="`${backupTabId}_backupOptionsUnloggedTableData`">
                    Unlogged table data
                  </label>
                </div>
                <div class="form-check form-switch">
                  <input class="form-check-input" type="checkbox" :id="`${backupTabId}_backupOptionsComments`"
                    v-model="backupOptions.comments">
                  <label class="form-check-label" :for="`${backupTabId}_backupOptionsComments`">
                    Comments
                  </label>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        <div class="col-4 d-flex">
          <div class="card flex-grow-1">
            <h4 class="card-header fw-bold px-3 py-2">Options</h4>
            <div class="card-body px-2 px-3 py-2">
            <div class="form-group mb-1">
              <p class="fw-bold mb-1">Queries</p>
              <div class="form-check form-switch">
                <input class="form-check-input" type="checkbox" :id="`${backupTabId}_backupOptionsColumnInserts`"
                  v-model="backupOptions.use_column_inserts">
                <label class="form-check-label" :for="`${backupTabId}_backupOptionsColumnInserts`">
                  Use Column Inserts
                </label>
              </div>
              <div class="form-check form-switch">
                <input class="form-check-input" type="checkbox" :id="`${backupTabId}_backupOptionsInsertCommands`"
                  v-model="backupOptions.use_insert_commands">
                <label class="form-check-label" :for="`${backupTabId}_backupOptionsInsertCommands`">
                  Use Insert Commands
                </label>
              </div>
              <div v-if="isObjectsType" class="form-check form-switch">
                <input class="form-check-input" type="checkbox" :id="`${backupTabId}_backupOptionsCreateDbStatement`"
                  v-model="backupOptions.include_create_database">
                <label class="form-check-label" :for="`${backupTabId}_backupOptionsCreateDbStatement`">
                  Include CREATE DATABASE statement
                </label>
              </div>
              <div class="form-check form-switch">
                <input class="form-check-input" type="checkbox" :id="`${backupTabId}_backupOptionsDropCommands`"
                  v-model="backupOptions.include_drop_commands" :disabled="backupOptions.only_data">
                <label class="form-check-label" :for="`${backupTabId}_backupOptionsDropCommands`">
                  Include DROP commands
                </label>
              </div>
              <div v-if="isObjectsType" class="form-check form-switch">
                <input class="form-check-input" type="checkbox" :id="`${backupTabId}_backupOptionsPartitionRoot`"
                  v-model="backupOptions.load_via_partition_root">
                <label class="form-check-label" :for="`${backupTabId}_backupOptionsPartitionRoot`">
                  Load Via Partition Root
                </label>
              </div>
            </div>

            <div class="form-group mb-1">
              <p class="fw-bold mb-1">Disable</p>
              <div class="form-check form-switch">
                <input class="form-check-input" type="checkbox" :id="`${backupTabId}_backupOptionsTrigger`"
                  title="disabled on object backup" v-model="backupOptions.disable_trigger"
                  :disabled="!backupOptions.only_data">
                <label class="form-check-label" :for="`${backupTabId}_backupOptionsTrigger`">
                  Trigger
                </label>
              </div>
              <div class="form-check form-switch">
                <input class="form-check-input" type="checkbox" :id="`${backupTabId}_backupOptionsQuoting`"
                  v-model="backupOptions.disable_quoting">
                <label class="form-check-label" :for="`${backupTabId}_backupOptionsQuoting`">
                  $ quoting
                </label>
              </div>
            </div>
            
            <div class="form-group mb-0">
              <p class="fw-bold mb-1">Miscellaneous</p>
              <div class="form-check form-switch">
                <input class="form-check-input" type="checkbox" :id="`${backupTabId}_backupOptionsVerboseMessages`"
                  v-model="backupOptions.verbose">
                <label class="form-check-label" :for="`${backupTabId}_backupOptionsVerboseMessages`">
                  Verbose messages
                </label>
              </div>
              <div class="form-check form-switch">
                <input class="form-check-input" type="checkbox" :id="`${backupTabId}_backupOptionsDoubleQuote`"
                  v-model="backupOptions.dqoute">
                <label class="form-check-label" :for="`${backupTabId}_backupOptionsDoubleQuote`">
                  Force double quote on identifiers
                </label>
              </div>
              <div class="form-check form-switch">
                <input class="form-check-input" type="checkbox" :id="`${backupTabId}_backupOptionsSetSeessionAuthorization`"
                  v-model="backupOptions.use_set_session_auth">
                <label class="form-check-label" :for="`${backupTabId}_backupOptionsSetSeessionAuthorization`">
                  Use SET SESSION AUTHORIZATION
                </label>
              </div>
            </div>
            </div>
          </div>
        </div>
      </div>

      <div class="d-flex justify-content-between mt-3">
        <a data-testid="revert-settings-button" :class="['btn', 'btn-outline-secondary', 'mb-2', { 'disabled': !isOptionsChanged }]" 
            @click="resetToDefault">Revert settings</a>
          <div class="btn-group">
            <a data-testid="preview-button" :class="['btn', 'btn-outline-primary', 'mb-2', { 'disabled': !backupOptions.fileName}]"
                @click="previewCommand">Preview</a>
            <a data-testid="backup-button" :class="['btn', 'btn-success', 'mb-2', 'ms-0', { 'disabled': !backupOptions.fileName || backupLocked }]"
                @click.prevent="saveBackup">Backup</a>
          </div>
      </div>
  </form>
  <UtilityJobs @jobExit="handleJobExit" ref="jobs" />

</div>
</template>
<script>
import UtilityJobs from "./UtilityJobs.vue";
import axios from 'axios'
import { showAlertText } from "../notification_control";
import { fileManagerStore, tabsStore, settingsStore } from "../stores/stores_initializer";
import { truncateText, flashHighlight } from "../utils";
import { handleError } from "../logging/utils";
import { emitter } from "../emitter";

export default {
  name: "BackupTab",
  components: {
    UtilityJobs,
  },
  props: {
    workspaceId: String,
    tabId: String,
    databaseIndex: Number,
    backupType: String,
    treeNode: Object,
    database: String,
  },
  data() {
    return {
      roleNames: [],
      formats: {
        custom: 'Custom',
        tar: 'Tar',
        plain: 'Plain',
        directory: 'Directory'
      },
      encodingList: [
        'BIG5', 'EUC_CN', 'EUC_JIS_2004', 'EUC_JP', 'EUC_KR', 'EUC_TW', 'GB18030',
        'GBK', 'ISO_8859_5', 'ISO_8859_6', 'ISO_8859_7', 'ISO_8859_8', 'JOHAB',
        'KOI18R', 'KOI8U', 'LATIN1', 'LATIN10', 'LATIN2', 'LATIN3', 'LATIN4', 'LATIN5',
        'LATIN6', 'LATIN7', 'LATIN8', 'LATIN9', 'MULE_INTERNAL', 'SHIFT_JIS_2004', 'SJIS', 'SQL_ASCII',
        'UHC', 'UTF8', 'WIN1250', 'WIN1251', 'WIN1252', 'WIN1253', 'WIN1254', 'WIN1255', 'WIN1256',
        'WIN1257', 'WIN1258', 'WIN866', 'WIN874'
      ],
      backupOptionsDefault: {
        database: this.database,
        pg_version: '',
        tables: [],
        schemas: [],
        role: "",
        format: this.backupType === 'objects' ? 'custom' : 'plain',
        encoding: "",
        fileName: "",
        pre_data: false,
        data: false,
        post_data: false,
        only_data: false,
        only_schema: false,
        only_roles: false,
        only_tablespaces: false,
        only_globals: false,
        blobs: this.backupType === 'objects' ? true : false,
        owner: false,
        privilege: false,
        tablespace: false,
        unlogged_tbl_data: false,
        comments: false,
        use_column_inserts: false,
        use_insert_commands: false,
        include_create_database: false,
        include_drop_commands: false,
        load_via_partition_root: false,
        disable_trigger: false,
        disable_quoting: false,
        verbose: true,
        dqoute: false,
        use_set_session_auth: false,
        number_of_jobs: "",
        compression_ratio: "",
        pigz: false,
      },
      backupOptions: {},
      backupTabId: this.tabId,
      backupLocked: false,
      lastJobId: 0
    }
  },
  computed: {
    isOptionsChanged() {
      return JSON.stringify(this.backupOptionsDefault) !== JSON.stringify(this.backupOptions)
    },
    compressionRatioValues() {
      return [...Array(10).keys()]
    },
    isTarFormat() {
      return this.backupOptions.format === 'tar'
    },
    type() {
      return this.backupOptions.only_globals ? 'globals' : this.backupType
    },
    isServerType() {
      return this.backupType === 'server'
    },
    isObjectsType() {
      return this.backupType === 'objects'
    },
    isOnlyDataOrSchemaSelected() {
      return this.backupOptions.only_data || this.backupOptions.only_schema
    },
    dialogType() {
      return this.backupOptions.format === 'directory' ? 'select_folder' : 'create_file'
    },
    numberOfJobs() {
      return ['auto', ...Array.from({length: 8}, (_, index) => index + 1)]
    },
    isDirectoryFormat() {
      return this.backupOptions.format === 'directory'
    },
    isWindowsOS() {
      return navigator.userAgent.indexOf("Win") != -1
    },
    pgKeys() {
      const keys = Object.keys(settingsStore.binaryPaths || {}).filter(k => settingsStore.binaryPaths[k]);
      return keys.map(k => parseInt(k.split('-')[1])).sort();
    },
  },
  mounted() {
    this.$nextTick(() => {
      if (this.treeNode.data.type === 'schema') {
        this.backupOptionsDefault.schemas.push(this.treeNode.title)
      } else if (this.treeNode.data.type === 'table') {
        this.backupOptionsDefault.tables.push(`${this.treeNode.data.schema}.${this.treeNode.title}`)
      }
      this.backupOptions = { ...this.backupOptionsDefault }
      this.getRoleNames()
      this.getServerVersion();
    })

    fileManagerStore.$onAction(({ name, store, after }) => {
      if (
        name === "changeFile" &&
        this.tabId === tabsStore.selectedPrimaryTab.metaData.selectedTab.id
      ) {
        after(() => {
          this.changeFilePath(store.file.path);
          if (store.file.is_directory) {
            this.backupOptions.format = "directory";
            return;
          }

          switch (store.file?.type) {
            case "sql":
              this.backupOptions.format = "plain";
              break;
            case "tar":
              this.backupOptions.format = "tar";
              break;
            default:
              this.backupOptions.format = "custom";
          }
        });
      }
    });

    emitter.on(`${this.tabId}_focus`, () => {
      this.$refs.focusableEl.focus();
      flashHighlight(this.$refs.highlightEl);
    });
  },
  unmounted() {
    emitter.all.delete(`${this.tabId}_focus`);
  },
  watch: {
    'backupOptions.format'(newValue){
      if (['directory', 'tar'].includes(newValue)) {
        this.backupOptions.pigz = false
      }
      if (!this.backupOptions.fileName) return;


      // Remove the current extension, if any
      this.backupOptions.fileName = this.backupOptions.fileName.replace(/\.[^/.]+$/, ""); 

      switch (newValue) {
        case 'directory':
          break;
        case 'plain':
          this.backupOptions.fileName += '.sql';
          break;
        case 'custom':
          this.backupOptions.fileName += '.dump';
          break;
        case 'tar':
          this.backupOptions.fileName += '.tar';
          break;
      }
    },
    backupOptions: {
      handler() {
        this.backupLocked = false;
      },
      deep: true
    },
  },
  methods: {
    getRoleNames() {
      axios.post("/get_roles_postgresql/", {
        database_index: this.databaseIndex,
        workspace_id: this.workspaceId,
      })
        .then((resp) => {
          resp.data.data.forEach(element => this.roleNames.push(element.name))
        })
        .catch((error) => {
          handleError(error);
        })
    },
    saveBackup() {
      this.backupLocked = true;
      axios.post("/backup/", {
        database_index: this.databaseIndex,
        workspaceId: this.workspaceId,
        data: this.backupOptions,
        backup_type: this.type
      })
        .then((resp) => {
          this.$refs.jobs.startJob(resp.data.job_id, resp.data.description);
          this.lastJobId = resp.data.job_id;
        })
        .catch((error) => {
          handleError(error);
          this.backupLocked = false;
        })
    },
    onFile(e) {
      const [file] = e.target.files
      this.backupOptions.fileName = file?.path

      if (e.target.hasAttribute('nwdirectory')) return;

      switch (file?.type) {
        case 'application/sql':
          this.backupOptions.format = 'plain';
          break;
        case 'application/x-tar':
          this.backupOptions.format = 'tar';
          break;
        default:
          this.backupOptions.format = 'custom';
      }
    },
    changeFilePath(filePath) {
      this.backupOptions.fileName = filePath;
    },
    openFileManagerModal() {
      fileManagerStore.showModal(settingsStore.desktopMode, this.onFile, this.dialogType, 'Choose a backup destination');
    },
    resetToDefault() {
      this.backupOptions = { ...this.backupOptionsDefault }
    },
    previewCommand() {
      axios.post("/backup/preview_command/", {
        database_index: this.databaseIndex,
        workspaceId: this.workspaceId,
        data: this.backupOptions,
        backup_type: this.type
      })
        .then((resp) => {
          showAlertText(resp.data.command.cmd)
        })
        .catch((error) => {
          handleError(error);
        })
    },
    handleJobExit(jobId) {
      if(jobId === this.lastJobId)
        this.backupLocked = false;
    },
    truncateText,
    getServerVersion() {
      axios
        .post("/get_postgresql_version/", {
          database_index: this.databaseIndex,
          workspace_id: this.workspaceId,
        })
        .then((response) => {
          let version = this.pgKeys.includes(response.data.version) ? response.data.version : this.pgKeys.at(-1);
          this.backupOptionsDefault.pg_version = version;
          this.backupOptions.pg_version = version;
        })
        .catch((error) => {
          handleError(error);
        });
    },
  }
}

</script>