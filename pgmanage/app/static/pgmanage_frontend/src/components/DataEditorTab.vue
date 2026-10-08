<template>
<div ref="editorDiv" class="data-editor p-2">
  <button :id="`bt_fullscreen_${tabId}`" style="position: absolute; right: 0.5rem" type="button"
      class="btn btn-sm btn-icon btn-icon-primary pe-2" title='Fullscreen' @click="toggleFullScreen()">
      <i :class="inFullscreen ? 'fas fa-compress':'fas fa-expand'"></i>
  </button>
  <div ref="topToolbar" class="row">
    <div class="form-group col-10 align-content-center overflow-auto" style="max-height: 170px;">
        <label class="mb-2">
          <span class="fw-bold">Filter</span>
        </label>
      <DataEditorTabFilter :operators="dialectOperators" :updated-raw-query="updatedRawQuery" :columns="columnNames" :filters="queryFilters" @update="handleFilterUpdate"/>
    </div>
    <div class="form-group col-2">
      <div class="form" @submit.prevent>
        <label class="fw-bold mb-2" :for="`${tabId}_rowLimit`">Limit</label>
        <div class="d-flex">
          <select :id="`${tabId}_rowLimit`" v-model="rowLimit" class="form-select">
            <option v-for="(option, index) in [25, 100, 1000]"
              :key=index
              :value="option">
                {{option}} rows
            </option>
        </select>

        <button class="btn btn-primary mx-2" title="Load Data" @click="confirmGetTableData()">
          <i class="fa-solid fa-filter"></i>
        </button>
        </div>
      </div>
    </div>
  </div>

  <div ref="tabulator" class="tabulator-custom data-grid grid-height" @keydown.delete="clearSelectedData">
    <!-- tabulator placeholder -->
  </div>

  <div ref="bottomToolbar" class="data-editor__footer d-flex align-items-center justify-content-end p-2">
    <p class="text-info me-2" v-if="!hasPK" ><i class="fa-solid fa-circle-info"></i> The table has no primary key, existing rows can not be updated</p>
    <button type="submit" class="btn btn-success btn-sm" :disabled="!hasChanges"
      @click.prevent="applyChanges">
      {{this.applyBtnTitle()}}
    </button>
  </div>
</div>
</template>

<script>
import ClipboardMixin from "../mixins/table_clipboard_copy_mixin";
import ContextMenuMixin from "../mixins/tabulator_context_menu_mixin";
import { markRaw } from "vue";
import axios from 'axios'
import Knex from 'knex'
import isEqual from 'lodash/isEqual';
import isEqualWith from 'lodash/isEqualWith';
import zipObject from 'lodash/zipObject';
import forIn from 'lodash/forIn';
import isArray from 'lodash/isArray'
import escape from 'lodash/escape';
import isNil from 'lodash/isNil';
import isEmpty from 'lodash/isEmpty';
import last from 'lodash/last';
import mean from 'lodash/mean';
import { showToast } from "../notification_control";
import { queryRequestCodes, requestState, knexDialectMap } from '../constants'
import { createRequest } from '../long_polling'
import { TabulatorFull as Tabulator} from 'tabulator-tables'
import { emitter } from '../emitter';
import { settingsStore, tabsStore, messageModalStore, cellDataModalStore } from '../stores/stores_initializer';
import DataEditorTabFilterList from './DataEditorTabFilterList.vue'
import { dataEditorFilterModes } from '../constants';
import { handleError } from '../logging/utils';
import dialects from './dialect-data';
import { extractOrderByClause, flashHighlight } from '../utils';
import { readClipboardText } from "@src/utils/clipboard";

// TODO: run query in transaction

function escapeColumnName(name) {
  if (name === "*") return name;
  const nestedMatch = name.match(/(.*?)(\[[0-9]\])/);
  return nestedMatch
    ? `${escapeColumnName(nestedMatch[1])}${nestedMatch[2]}`
    : `"${name.replace(/"/g, '""')}"`;
}

const contextEdits = new WeakSet();

export default {
  name: "DataEditorTab",
  components: {
    DataEditorTabFilter: DataEditorTabFilterList
  },
  mixins: [ClipboardMixin, ContextMenuMixin],
  props: {
    dialect: String,
    schema: String,
    table: String,
    tabId: String,
    workspaceId: String,
    databaseIndex: Number,
  },
  data() {
    return {
      knex: null,
      tableColumns: [],
      colWidthArray: [],
      defaultColWidthArray: [],
      inFullscreen: false,
      customLayout: undefined,
      previousLayout: undefined,
      tableData: [],
      tableDataLocal: [],
      queryFilters: [{ column: "", operator: "=", value: "" }],
      rowLimit: 25,
      dataLoaded: false,
      heightSubtract: 200, //default safe value, recalculated in handleResize
      tabulator: null,
      maxInitialWidth: 200,
      queryState: requestState.Idle,
      rawQuery: "",
      updatedRawQuery: "",
      dialectData: {},
    };
  },
  computed: {
    talbleUnquoted() {
      return this.table.replace(/^"(.*)"$/, '$1')
    },
    hasChanges() {
      return this.pendingChanges.length > 0
    },
    pendingChanges() {
      if(this.hasPK)
        return this.tableDataLocal.filter((row) => row["rowMeta"].is_dirty || row["rowMeta"].is_new || row["rowMeta"].is_deleted)
      else
        return this.tableDataLocal.filter((row) => row["rowMeta"].is_new)
    },
    hasPK() {
      return this.tableColumns.some(c => c.is_primary)
    },
    gridHeight() {
      return `calc(100vh - ${this.heightSubtract}px)`;
    },
    columnNames() {
      return this.tableColumns.map(col => col.name)
    },
    primaryKeys() {
      return this.tableColumns.filter(col => col.is_primary).map(col => col.name)
    },
    dialectOperators() {
      return this.dialectData?.operators ?? [];
    },
    nonEditableDataTypes() {
      return this.dialectData?.nonEditableDataTypes ?? [];
    },
  },
  mounted() {
    let mappedDialect = knexDialectMap[this.dialect] || this.dialect;
    this.dialectData = dialects[mappedDialect];
    this.handleResize()
    let table = new Tabulator(this.$refs.tabulator, {
      placeholder: "No Data Available",
      layout: "fitDataFill",
      data: [],
      autoResize: false,
      columnDefaults: {
          headerHozAlign: "left",
          headerSort: false,
          maxInitialWidth: this.maxInitialWidth,
        },
      selectableRangeAutoFocus:false,
      selectableRange:1,
      selectableRangeColumns:true,
      selectableRangeRows:true,
      editTriggerEvent:"dblclick",
      rowFormatter: this.rowFormatter,
      sortMode: 'remote',
      headerSortClickElement:"icon",
      ajaxURL: "http://fake",
      ajaxRequestFunc: this.getTableData,
      clipboard: true,
      clipboardCopyRowRange: "range",
      clipboardPasteParser:"range",
      clipboardPasteAction: "range",
      clipboardCopyConfig: {
        columnHeaders: false, //do not include column headers in clipboard output
        formatCells:false, //cell formatting on clipboard copy breaks rowFormatter's ability to colorize data grid rows
      },
    })

    table.on("tableBuilt", () => {
      this.tabulator = markRaw(table); // markRaw fixes problem with making tabulator proxy, that we don't need
      this.tabulator.on("cellEditing", (cell) => { // Prevent Tabulator from hijacking left/right arrow keys, delete key and mouse click while editing
        this.$nextTick(() => {
          const el = cell.getElement().querySelector("input");
          if (!el) return;
          el.addEventListener("keydown", (e) => {
            if (["ArrowLeft", "ArrowRight", "Delete"].includes(e.key)) e.stopPropagation();
          });
          el.addEventListener("mousedown", (e) => {
            e.stopPropagation();
          });
        })
      });

      this.tabulator.on("cellEdited", this.cellEdited);
      this.tabulator.on("clipboardPasted", (clipboard, rowData, rows) => {
        const dataLength = rowData.length;
        // manually trigger cellEdited on changed cells because clipboard paste doesn't do that
        rows.forEach((row, rowIndex) => {
          const rowValues = rowData[rowIndex % dataLength];
          if (!rowValues) return;

          const cells = row.getCells();

          cells.forEach((cell, cellIndex) => {
            if (!(cellIndex in rowValues)) return;   // no pasted data for this column

            this.cellEdited(cell.getComponent())
          });
        });
      });
      this.knex = Knex({ client: mappedDialect || 'postgres'})
      this.getTableColumns().then(() => {
        this.addHeaderMenuOverlayElement();
        this.tabulator.setSort("0", "asc");
        if (this.defaultColWidthArray.length !== this.tabulator.getColumns().length) {
          this.defaultColWidthArray = this.tabulator.getColumns().map(col => col.getWidth());
        }
      });
    })

    emitter.on(`${this.tabId}_query_edit`, () => {
      this.confirmGetTableData();
    })

    emitter.on(`${this.tabId}_check_query_edit_status`, () => {
        if (this.queryState === requestState.Ready) {
          const tab = tabsStore.getSecondaryTabById(this.tabId, this.workspaceId);
          tab.metaData.isReady = false;
          tab.metaData.isLoading = false;
          this.queryState = requestState.Idle;
        }
      });

    emitter.on(`${this.tabId}_focus`, () => {
      this.focus();
      flashHighlight(this.$refs.tabulator);
    });

    settingsStore.$onAction((action) => {
      if(action.name === "setFontSize") {
        action.after(() => {
          requestAnimationFrame(() => {
            requestAnimationFrame(() => {
              this.handleResize();
            })
          })
        })
      }
    })

  },
  unmounted() {
    emitter.all.delete(`${this.tabId}_query_edit`);
    emitter.all.delete(`${this.tabId}_check_query_edit_status`);
    emitter.all.delete(`${this.tabId}_focus`);
  },
  updated() {
    if (tabsStore.selectedPrimaryTab?.metaData?.selectedTab?.id === this.tabId) {
      this.handleResize();
    }
  },
  methods: {
    focus() {
      this.tabulator?.element.querySelector(".tabulator-tableholder")?.focus();
    },
    actionsFormatter(cell, formatterParams, onRendered) {
      const div = document.createElement("div");
      div.className = 'btn btn-grid-actions';

      let cellData = cell.getValue()
      if (!cellData)
        return

      if (cellData.is_deleted || cellData.is_dirty) {
        const revertIcon = document.createElement('i')
        revertIcon.className = 'fas fa-rotate-left text-info p-2'
        revertIcon.title = 'Revert'
        revertIcon.dataset.action = 'revert'
        div.appendChild(revertIcon);
      } else {
        const deleteIcon = document.createElement('i')
        deleteIcon.className = 'fas fa-circle-xmark text-danger p-2'
        deleteIcon.title = 'Remove'
        deleteIcon.dataset.action = 'delete'
        div.appendChild(deleteIcon)
      }

      return div
    },
    applyLayout() {
      this.colWidthArray = []

      this.tabulator.blockRedraw();

      this.tabulator.getColumns().forEach((col, idx) => {
        if(idx > 0) {
          if(this.customLayout == 'adaptive') {
            let widths = col.getCells().map((cell) => {return cell.getElement().scrollWidth}).filter((el) => el > 0)
            col.setWidth(mean(widths))
            this.colWidthArray.push(mean(widths))
          }

          if(this.customLayout === undefined) {
            col.setWidth(this.defaultColWidthArray[idx]);
          }
        }
      });

      this.tabulator.restoreRedraw();
    },
    rowFormatter(row) {
      row.getElement().classList.remove('row-deleted', 'row-dirty', 'row-new');
      let rowMeta = row.getData()["rowMeta"]
      if (rowMeta) {
        if (rowMeta.is_dirty)
          row.getElement().classList.add('row-dirty')
        if (rowMeta.is_deleted)
          row.getElement().classList.add('row-deleted')
        if (rowMeta.is_new)
          row.getElement().classList.add('row-new')
      }
    },
    getTableColumns() {
      return axios
        .post("/get_table_columns/", {
          database_index: this.databaseIndex,
          workspace_id: this.workspaceId,
          schema: this.schema,
          table: this.table
        })
        .then((response) => {
          this.tableColumns = response.data.columns

          let actionsCol = {
            title: `<div data-action="add" class="btn p-0 btn-grid-actions" title="Add column">
              <i data-action="add" class="fa-solid fa-circle-plus text-success p-2"></i>
              </div>`,
            field: 'rowMeta',
            frozen: 'true',
            hozAlign: 'center',
            formatter: this.actionsFormatter,
            cellClick: this.handleClick,
            headerClick: this.addRow,
          }

          let cellContextMenu = (e, cellComponent) => {
            const selectedRange = cellComponent.getTable().getRanges()[0];
            const isOneCellSelected =
              selectedRange.getBottomEdge() === selectedRange.getTopEdge() &&
              selectedRange.getRightEdge() === selectedRange.getLeftEdge();
            const colType = this.tableColumns[cellComponent.getField()]?.data_type;
            const nonEditable = this.nonEditableDataTypes.includes(colType)
              return [
                {
                  label: '<i class="fas fa-edit"></i><span>Edit in modal</span>',
                  action: (e, cell) => {
                    let cellValue = cell.getValue();
                    cellDataModalStore.showModal(cellValue, colType, true, false, (newValue) => {
                      cell.setValue(newValue);
                    });
                },
                disabled: !isOneCellSelected || nonEditable,
              },
              {
                separator:true,
              },
              {
                label: '<i class="fas fa-copy"></i><span>Copy</span>',
                action: function (e, cell) {
                  cell.getTable().copyToClipboard();
                },
              },
              {
                label: '<i class="fas fa-copy"></i><span>Copy as JSON</span>',
                action: () => {
                  const data = last(this.tabulator.getRangesData());
                  this.copyTableData(data, "json", this.columnNames);
                },
              },
              {
                label: '<i class="fas fa-copy"></i><span>Copy as CSV</span>',
                action: () => {
                  const data = last(this.tabulator.getRangesData());
                  this.copyTableData(data, "csv", this.columnNames);
                },
              },
              {
                label: '<i class="fas fa-copy"></i><span>Copy as Markdown</span>',
                action: () => {
                  const data = last(this.tabulator.getRangesData());
                  this.copyTableData(data, "markdown", this.columnNames);
                },
              },
              {
                separator:true,
              },
              {
                label: '<i class="fas fa-paste"></i><span>Paste</span>',
                action: async () => {
                  const text = await readClipboardText();

                  if (!text) {
                    return;
                  }

                  const clip = this.tabulator.modules.clipboard;

                  const rowData = clip.pasteParser.call(clip, text);
                  if (!rowData || rowData === false) return;

                  const rows = clip.pasteAction.call(clip, rowData);

                  clip.dispatchExternal("clipboardPasted", text, rowData, rows);
                },
              },
              {
                separator:true,
              },
              {
                label: '<span>Set Null</span>',
                action: () => {
                  const range = last(this.tabulator.getRanges());
                  range.getCells().flat().forEach((cell) => {
                    contextEdits.add(cell);
                    cell.setValue(null);
                  })
                }
              },
              {
                label: '<span>Set Empty</span>',
                action: () => {
                  const range = last(this.tabulator.getRanges());
                  range.getCells().flat().forEach((cell) => {
                    contextEdits.add(cell);
                    cell.setValue("");
                  })
                } 
              },
            ];
          } 
          let columns = this.tableColumns.map((col, idx) => {
            let prepend = col.is_primary ? '<i class="fas fa-key action-key text-secondary me-1"></i>' : ''
            let title = `${prepend}<span>${col.name}</span><div class='fw-light'>${col.data_type}</div>`

            return {
              field: (idx).toString(),
              title: title,
              editor: this.nonEditableDataTypes.includes(col.data_type) ? false : "input",
              headerSort: true,
              contextMenu: cellContextMenu,
              headerDblClick: (e, column) => {
                if (column.getWidth() > this.maxInitialWidth) {
                  column.setWidth(this.maxInitialWidth);
                } else {
                  column.setWidth(true);
                }
              },
              formatter: this.cellFormatter,
            }
          })
          columns.unshift(actionsCol)
          this.tabulator.setColumns(columns)

          this.dataLoaded = true
        })
        .catch((error) => {
          handleError(error);
        });
    },
    buildQueryFilter() {
      if (this.mode === dataEditorFilterModes.MANUAL) {
        return this.processManualModeQuery();
      } 
      return this.processAutoModeFilters();
    },
    processAutoModeFilters() {
      const preprocessFilters = (rawFilters) => {
        return rawFilters
          .filter((f) => f.operator && f.column && f.value)
          .map((f) => ({
            ...f,
            value:
              f.operator === "in" ? f.value.split(/\s*,\s*/) : String(f.value),
          }));
      };

      const combineFilters = (filterStrings, filterObjects) => {
        return filterStrings.length === 0
          ? ""
          : filterStrings.reduce((acc, filter, idx) => {
              const logic = filterObjects[idx]?.condition || "AND";
              return `${acc} ${logic} ${filter}`;
            });
      };

      let queryFilter = ""
      const filters = preprocessFilters(this.queryFilters);
        if (filters?.length > 0) {
          const filterClauses = filters.map((filter) => {
            if (filter.operator === "in" && isArray(filter.value)) {
              const formattedValues = filter.value.map((val) => {
                return this.knex.raw("?", [val]).toQuery();
              });
              return `${escapeColumnName(
                filter.column
              )} ${filter.operator.toUpperCase()} (${formattedValues.join(",")})`;
            }
            const formattedValue = this.knex.raw("?", [filter.value]).toQuery();
            return `${escapeColumnName(
              filter.column
            )} ${filter.operator.toUpperCase()} ${formattedValue}`;
          });
          queryFilter = "WHERE " + combineFilters(filterClauses, filters);
        }
        return queryFilter
    },
    buildOrderByClause(params) {
      const parseOrderBy = (query) => {
        const orderByRegex = /ORDER\s+BY\s+([\w\s",.]+)$/i;
        const match = query.match(orderByRegex);

        if (!match) return [];

        return match[1].split(",").map((part) => {
          let [column, direction] = part.trim().split(/\s+/);
          direction = direction ? direction.toLowerCase() : "asc";

          if (column.includes(".")) {
            column = column.split(".")[1];
          }

          return { name: column, dir: direction };
        });
      };

      const mapColumnsToIndexes = (orderByColumns, tableColumns) => {
        return orderByColumns
          .map((column) => {
            const columnIndex = tableColumns.findIndex(
              (col) => col.name === column.name
            );
            return columnIndex !== -1
              ? { column: columnIndex, dir: column.dir }
              : null;
          })
          .filter((item) => item !== null);
      };

      const trimmedQuery = this.rawQuery.trim();
      const { queryFilterCleaned, orderByClause } =
        extractOrderByClause(trimmedQuery);

      const orderByColumns = parseOrderBy(orderByClause);

      if (!params?.sort && orderByClause) {
        const result = mapColumnsToIndexes(orderByColumns, this.tableColumns);
        this.tabulator.setSort(result);
        return null;
      }

      if (params?.sort && params.sort.length === 1) {
        let sortColumnName = this.columnNames[params.sort[0].field];
        let updatedOrderClause = '';
        if (this.dialect === 'oracle') {
          // sort column should be quoted
          let quotedColumnName = this.knex.raw("?", [sortColumnName]).toQuery()
          updatedOrderClause = `ORDER BY ${quotedColumnName} ${params.sort[0].dir}`;
        } else {
          updatedOrderClause = `ORDER BY ${sortColumnName} ${params.sort[0].dir}`;
        }
        this.updatedRawQuery = `${queryFilterCleaned} ${updatedOrderClause}`;
        return updatedOrderClause;
      }

      if (params?.sort) {
        return (
          "ORDER BY " +
          params.sort
            .map((item) => {
              const columnName = this.columnNames[item.field];
              return `${escapeColumnName(
                columnName
              )} ${item.dir.toUpperCase()}`;
            })
            .join(",")
        );
      } else {
        this.tabulator.setSort("0", "asc");
        return null;
      }
    },
    processManualModeQuery() {
      const trimmedQuery = this.rawQuery.trim().toLowerCase();
      const hasWhere = trimmedQuery.startsWith("where ");
      const hasOrderBy = trimmedQuery.includes("order by");
      const { queryFilterCleaned } = extractOrderByClause(trimmedQuery);

      if (!trimmedQuery) return ""
      if (hasOrderBy) {
        if (!!queryFilterCleaned) return hasWhere ? queryFilterCleaned : `WHERE ${queryFilterCleaned}`;
        return ""
      } else {
        return hasWhere ? trimmedQuery : `WHERE ${trimmedQuery}`;
      }
    },
    sendDataRequest(finalFilter) {
      var message_data = {
        table: this.table,
        schema: this.schema,
        db_index: this.databaseIndex,
        query_filter: finalFilter,
        count: this.rowLimit,
        workspace_id: this.workspaceId,
        tab_id: this.tabId,
      };

      var context = {
        tab_tag: null,
        callback: this.handleResponse.bind(this),
        start_time: new Date().getTime(),
        database_index: this.databaseIndex,
      };

      createRequest(queryRequestCodes.QueryEditData, message_data, context);
      const tab = tabsStore.getSecondaryTabById(this.tabId, this.workspaceId);

      this.queryState = requestState.Executing;
      setTimeout(() => {
        if (this.queryState === requestState.Executing) 
          tab.metaData.isLoading = true;
      }, 1000);
      tab.metaData.isReady = false;
    },
    getTableData(_url, _config, params) {
      const queryFilter = this.buildQueryFilter();
      const orderBy = this.buildOrderByClause(params);

      if (orderBy === null) {
        return 
      }

      const finalFilter = `${queryFilter} ${orderBy}`;

      this.sendDataRequest(finalFilter)

      // we need to return promise for tabulator ajaxRequestFunc to work
      return new Promise((resolve, reject) => {
        resolve([])
      })
    },
    toggleFullScreen() {
      this.$refs.editorDiv.classList.toggle("omnidb__panel-view--full");

      this.inFullscreen = !this.inFullscreen

      if(this.inFullscreen) {
        this.previousLayout = this.customLayout
        this.customLayout = 'adaptive'
      } else {
        this.customLayout = this.previousLayout
      }

      this.applyLayout()
      this.handleResize()
    },
    handleResize() {
      if(this.$refs === null)
        return

      if(this.tabulator)
        this.tabulator.redraw();

      this.heightSubtract =
        this.$refs.bottomToolbar.getBoundingClientRect().height +
        this.$refs.topToolbar.getBoundingClientRect().bottom
    },
    handleClick(e, cell) {
      let rowNum = cell.getRow().getIndex()
      let action_type = e.target.dataset.action
      if (action_type) {
        let row = cell.getRow()
        let rowMeta = {}
        if (row.getCell('rowMeta')) {
          rowMeta = row.getCell('rowMeta').getValue()
        }
        if (action_type === 'delete')
          this.deleteRow(rowMeta, rowNum)
        if (action_type === 'revert') {
          this.revertRow(rowMeta, rowNum)

        }
      }
    },
    cellEdited(cell) {
      if (!this.hasPK)
        return

      const fromContext = contextEdits.has(cell);
      contextEdits.delete(cell);

      // workaround when empty cell with initial null value is changed to empty string when starting editing
      if (cell.getOldValue() === null && cell.getValue() === '' && !fromContext) {
        cell.restoreOldValue() // prevents from triggering cellEdited handler again
        return
      }

      let rowData = cell.getRow().getData()
      let rowMeta = rowData["rowMeta"]
      let originalRow = this.tableData.find((row) => isEqual(row["rowMeta"].initial_id, rowMeta.initial_id))

      if (originalRow) {
        rowMeta.is_dirty = !isEqualWith(rowData, originalRow, (val1, val2, key) => {
          if (key === 'rowMeta') {
            return true
          }
        }) && !rowMeta.is_new

        const row = cell.getRow();

        row.update({}); // triggers row formatter without wiping everything like with reformat()

        const actionsCell = row.getCell("rowMeta");
        if (actionsCell) {
            const val = actionsCell.getValue();
            actionsCell.setValue(val);  // re-triggers the actionsCell formatter
        }
      }

    },
    handleResponse(response) {
      const tab = tabsStore.getSecondaryTabById(this.tabId, this.workspaceId);
      tab.metaData.isLoading = false;
      if (
          this.workspaceId === tabsStore.selectedPrimaryTab.id &&
          this.tabId === tabsStore.selectedPrimaryTab.metaData.selectedTab.id
        ) {
          this.queryState = requestState.Idle;

          tab.metaData.isReady = false;
        } else {
          this.queryState = requestState.Ready;

          tab.metaData.isReady = true;
        }

      if(response.error == true) {
        showToast("error", response.data)
      } else {
        //store table data into original var, clone it to the working copy
        const pkIndexes = this.tableColumns.flatMap((col, idx) => col.is_primary ? [idx] : [])
        this.tableData = response.data.rows.map((row, index) => {
          let rowMeta = {
            is_dirty: false,
            is_new: false,
            is_deleted: false,
            initial_id: pkIndexes.map((idx) => row[idx])
          }
          return {id: index, rowMeta: rowMeta, ...row}
        })
        this.tableDataLocal = JSON.parse(JSON.stringify(this.tableData))
        this.tabulator.replaceData(this.tableDataLocal)
      }
    },
    handleSaveResponse(response) {
      const tab = tabsStore.getSecondaryTabById(this.tabId, this.workspaceId);
      tab.metaData.isReady = false;
      tab.metaData.isLoading = false;
      this.queryState = requestState.Idle;
      if(response.error == true) {
        showToast("error", response.data)
      } else {
        showToast("success", 'data updated')
        setTimeout(() => {
          this.getTableData()
        }, 100);
      }
    },
    addRow(e, cell) {
      if(e.target.dataset['action'] !== 'add')
        return;
      let newRow = Array(this.tableColumns.length + 1).fill(null); //+1 adds an extra actions column
      let rowMeta = {
        is_dirty: false,
        is_new: true,
        is_deleted: false,
        initial_id: -1,
      };

      let newRowId = this.tabulator.getRows().length;
      const newRowObject = { rowMeta: rowMeta, id: newRowId, ...newRow };
      this.tabulator.addData(newRowObject, true);
      this.tableDataLocal.unshift(this.tabulator.getRow(newRowId).getData());

      const firstRow = this.tabulator.getRows()[0];
      if (!firstRow) return;

      const firstCell = firstRow.getCells()[0];
      if (!firstCell) return;

      let currentRange = last(this.tabulator.getRanges())

      currentRange.setBounds(firstCell, firstCell)
    },
    revertRow(rowMeta, rowNum) {
      let sourceRow = this.tableData.find(
        (row) => isEqual(row["rowMeta"].initial_id, rowMeta.initial_id)
      );
      let copyRow = JSON.parse(JSON.stringify(sourceRow));
      this.tabulator.updateData([{ id: rowNum, ...copyRow }]).then(() => {
        this.tabulator.getRow(rowNum).reformat();
      });
    },
    deleteRow(rowMeta, rowNum) {
      if (rowMeta.is_new) {
        this.tabulator.deleteRow(rowNum).then(() => {
          this.tableDataLocal = this.tableDataLocal.filter(
            (row) => row.id !== rowNum
          );
        });
      } else {
        rowMeta.is_deleted = true;
        this.tabulator
          .updateData([{ id: rowNum, rowMeta: rowMeta }])
          .then(() => {
            this.tabulator.getRow(rowNum).reformat();
          });
      }
    },
    generateSQL() {
      let colNames = this.tableColumns.map(c => c.name)
      let deletes = []
      let inserts = []
      let updates = []
      let changes = this.pendingChanges
      let pkColNames = this.primaryKeys

      changes.forEach(function(change) {
        let rowMeta = change["rowMeta"]
        let {rowMeta:_, ...changeWitNoRowmeta} = change
        if(rowMeta.is_new) {
          let zippedChange = zipObject(colNames, Object.values(change))
          let insert = Object.entries(zippedChange).reduce((acc, [columnName, value]) => {
            // skip primary keys if no value
            if (this.primaryKeys.includes(columnName) && !value) {
              return acc;
            }
            acc[columnName] = value;
            return acc;
          }, {});

          inserts.push(insert)
        }
        if(rowMeta.is_dirty && !rowMeta.is_deleted){
          let originalRow = this.tableData.find((row) => isEqual(row["rowMeta"].initial_id, rowMeta.initial_id))
          let updateArgs = {}

          forIn(changeWitNoRowmeta, (value, key) => {
            if (value !== originalRow[key]) {
              updateArgs[colNames[key]] = value
            }
          })

          updates.push(this.knex(this.talbleUnquoted).withSchema(this.schema).whereIn(pkColNames, [rowMeta.initial_id]).update(updateArgs))
        }
      }, this)
      let deletableIds = changes.filter((c) => c["rowMeta"].is_deleted).map((c) => {return c["rowMeta"].initial_id})
      if(deletableIds.length > 0)
        deletes.push(this.knex(this.talbleUnquoted).withSchema(this.schema).whereIn(pkColNames, deletableIds).del())

      let insQ = []
      if(inserts.length)
        insQ = this.knex(this.talbleUnquoted).withSchema(this.schema).insert(inserts)

      return [].concat(updates, insQ, deletes).join(';\n')
    },
    applyChanges() {
      let query = this.generateSQL()

      let message_data = {
        sql_cmd : query,
        sql_save : false,
        db_index: this.databaseIndex,
        workspace_id: this.workspaceId,
        tab_id: this.tabId,
        tab_db_id: this.databaseIndex,
      }

      let context = {
        callback: this.handleSaveResponse.bind(this),
      }

      createRequest(queryRequestCodes.SaveEditData, message_data, context)

      const tab = tabsStore.getSecondaryTabById(this.tabId, this.workspaceId);
  
      this.queryState = requestState.Executing;
      setTimeout(() => {
        if (this.queryState === requestState.Executing) 
          tab.metaData.isLoading = true;
      }, 1000);

      tab.metaData.isReady = false;
    },
    applyBtnTitle() {
      let count = this.pendingChanges.length

      if(count === 0)
        return 'No Changes'
      return `Apply ${count} ${(count > 1 || count == 0) ? 'changes' : 'change'}`
    },
    handleFilterUpdate({ mode, filters, rawQuery }) {
      this.$nextTick(() => {
        this.handleResize();
      })
      this.mode = mode;
      if (filters) this.filters = filters;
      if (rawQuery !== undefined) {
        this.rawQuery = rawQuery;
      } 
    },
    confirmGetTableData(url, config, params) {
      if (this.hasChanges) {
        messageModalStore.showModal(
          "Are you sure you wish to discard the current changes?",
          () => {
            this.getTableData(url, config, params);
          },
          null
        );
      } else {
        this.getTableData(url, config, params);
      }

      return new Promise((resolve, reject) => {
        resolve(this.tableDataLocal);
      });
    },
    cellFormatter(cell, params, onRendered) {
      let cellVal = cell.getValue()
      if (!!cellVal && cellVal?.length > 1000) {
          let filtered = escape(cellVal.slice(0, 1000).toString().replace(/\n/g, ' ↲ '))
          return `${filtered}...`;
        }

      if (isNil(cellVal)) {
        return '<span class="text-muted">[null]</span>'
      }

      if(isEmpty(cellVal)) {
        return '<span class="text-muted">[empty]</span>'
      }
      return cellVal
    },
    addHeaderMenuOverlayElement() {
      const targetElement = document.querySelector(`#${this.tabId}_content .tabulator-frozen-left .tabulator-col-title-holder`)
      const overlay = document.createElement("div");
      overlay.className =  "position-absolute w-100 h-100";
      overlay.style.zIndex = "1000"; 
      overlay.style.cursor = "pointer"
      overlay.style.backgroundColor = "rgba(0, 0, 0, 0)";

      targetElement.appendChild(overlay)

      targetElement.addEventListener("mousedown", (e) => {
        e.stopPropagation();
        e.preventDefault();
      });
    },
    clearSelectedData(event) {
      if (event.key === 'Backspace') return

      const range = last(this.tabulator.getRanges());
      if (!range) return;

      range.getCells().flat().forEach((cell) => {
        cell.setValue(null);
      })
    },
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
  .grid-scrollable {
    width: 100%;
  }

  .grid-height {
    height: v-bind(gridHeight);
    
  }
</style>
