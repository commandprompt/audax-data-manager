<template>
  <PowerTree ref="tree" v-model="nodes" @nodedblclick="doubleClickNode" @toggle="onToggle"
    @nodecontextmenu="onContextMenu" :allow-multiselect="false" @nodeclick="onClickHandler" @click="handleLeftSideClick" @dblclick="handleLeftSideDblClick" tabindex="0">
    <template v-slot:toggle="{ node }">
      <i v-if="node.isExpanded" class="exp_col fas fa-chevron-down fa-sm"></i>
      <i v-if="!node.isExpanded" class="exp_col fas fa-chevron-right fa-sm"></i>
    </template>

    <template v-slot:title="{ node }">
      <div class="d-flex flex-grow-1 justify-content-between">
        <div>
          <span class="item-icon">
            <i :class="['icon_tree', node.data.icon]"></i>
          </span>
          
          <span v-if="node.data.raw_html" v-html="node.title"> </span>
          <span v-else-if="node.data.type === 'database' && node.title === selectedDatabase
            ">
            <b>{{ node.title }}</b>
          </span>
          <span v-else>
            {{ formatTitle(node) }}
          </span>
        </div>
  
        <!-- Pin icon for database nodes -->
         <span>
           <i
             v-if="node.data.type === 'database'"
             class="fas fa-thumbtack database-pin-icon me-2"
             :class="node.data.pinned ? 'text-primary pinned' : 'text-muted'"
             @click.stop="pinDatabase(node)"
             :title="`${node.data.pinned ? 'Unpin' : 'Pin'} this database`"
           ></i>
         </span>
      </div>
    </template>
  </PowerTree>
</template>

<script>
import { emitter } from "../emitter";
import TreeMixin from "../mixins/power_tree.js";
import PinDatabaseMixin from "../mixins/power_tree_pin_database_mixin.js";
import DropDbObjectMixin from "../mixins/power_tree_drop_db_object_mixin.js";
import { PowerTree } from "@onekiloparsec/vue-power-tree";
import { checkBeforeChangeDatabase } from "../workspace";
import {
  tabSQLTemplate,
  TemplateSelectPostgresql,
  TemplateUpdatePostgresql,
  TemplateInsertPostgresql,
  TemplateSelectFunctionPostgresql,
  TemplateCallProcedurePostgresql,
} from "../tree_context_functions/tree_postgresql";
import { createExtensionModal, createPgCronModal, createRoleModal } from "./postgresql_modals";
import { operationModes } from "../constants";
import { connectionsStore, messageModalStore, tabsStore, dbMetadataStore } from "../stores/stores_initializer";
import { findNode, findChild } from "../utils.js";


export default {
  name: "TreePostgresql",
  components: {
    PowerTree,
  },
  mixins: [TreeMixin, PinDatabaseMixin, DropDbObjectMixin],
  props: {
    databaseIndex: {
      type: Number,
      required: true,
    },
    workspaceId: {
      type: String,
      required: true,
    },
  },
  data() {
    return {
      nodes: [
        {
          title: "PostgreSQL",
          isExpanded: false,
          isDraggable: false,
          data: {
            icon: "node node-postgresql",
            type: "server",
            contextMenu: "cm_server",
          },
        },
      ],
      currentSchema: "public",
      cm_server_extra: [],
      serverVersion: null,
    };
  },
  computed: {
    contextMenu() {
      const COMMENT_MENUITEM = {
        label: "Edit Comment",
        icon: "fas fa-comment",
        onClick: () => {
          this.getObjectDescriptionPostgresql(this.selectedNode);
        },
      };

      return {
        cm_server: [this.cmRefreshObject, ...this.cm_server_extra],
        cm_databases: [
          this.cmRefreshObject,
          {
            label: "Create Database",
            icon: "fas fa-plus",
            onClick: () => {
              tabSQLTemplate("Create Database", this.templates.create_database);
            },
          },
          {
            label: "Doc: Databases",
            icon: "fas fa-globe-americas",
            onClick: () => {
              this.openWebSite(
                `https://www.postgresql.org/docs/${this.serverVersion}/managing-databases.html`
              );
            },
          },
        ],
        cm_database: [
          {
            label: "ER Diagram",
            icon: "fab fa-hubspot",
            onClick: () => {
              this.checkCurrentDatabase(this.selectedNode, true, () => {
                tabsStore.createERDTab();
              });
            },
          },
          {
            label: "Query Database",
            icon: "fas fa-search",
            onClick: () => {
              this.checkCurrentDatabase(this.selectedNode, true, () => {
                let tab_name = `Query: ${tabsStore.selectedPrimaryTab.metaData.selectedDatabase}`;
                tabsStore.createQueryTab(tab_name);
              });
            }
          },
          {
            label: "Alter Database",
            icon: "fas fa-edit",
            onClick: () => {
              //FIXME rewrite to use vue instance
              tabSQLTemplate(
                "Alter Database",
                this.templates.alter_database.replace(
                  "#database_name#",
                  this.selectedNode.data.raw_value
                )
              );
            },
          },
          {
            label: "Backup",
            icon: "fa-solid fa-download ",
            onClick: () => {
              const nodeDatabase = this.getNodeDatabase(this.selectedNode);
              tabsStore.createUtilityTab(this.selectedNode, nodeDatabase, 'Backup');
            },
          },
          {
            label: "Restore",
            icon: "fa-solid fa-upload ",
            onClick: () => {
              const nodeDatabase = this.getNodeDatabase(this.selectedNode);
              tabsStore.createUtilityTab(this.selectedNode, nodeDatabase, 'Restore');
            },
          },
          COMMENT_MENUITEM,
          {
            label: "Drop Database",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              let template = this.templates.drop_database.replace(
                  "#database_name#",
                  this.selectedNode.data.raw_value ?? this.selectedNode.title
                )
              this.prepareDropModal(this.selectedNode, template)
            },
          },
        ],
        cm_schemas: [
          this.cmRefreshObject,
          {
            label: "Create Schema",
            icon: "fas fa-plus",
            onClick: () => {
              tabSQLTemplate("Create Schema", this.templates.create_schema);
            },
          },
          {
            label: "Doc: Schemas",
            icon: "fas fa-globe-americas",
            onClick: () => {
              this.openWebSite(
                `https://www.postgresql.org/docs/${this.serverVersion}/ddl-schemas.html`
              );
            },
          },
        ],
        cm_schema: [
          {
            label: "ER Diagram",
            icon: "fab fa-hubspot",
            onClick: () => {
              tabsStore.createERDTab(this.selectedNode.data.schema_raw)
            },
          },
          {
            label: "Alter Schema",
            icon: "fas fa-edit",
            onClick: () => {
              tabSQLTemplate(
                "Alter Schema",
                this.templates.alter_schema.replace(
                  "#schema_name#",
                  this.selectedNode.data.schema_raw
                )
              );
            },
          },
          {
            label: "Backup",
            icon: "fa-solid fa-download ",
            onClick: () => {
              const nodeDatabase = this.getNodeDatabase(this.selectedNode);
              tabsStore.createUtilityTab(this.selectedNode, nodeDatabase, 'Backup');
            },
          },
          {
            label: "Restore",
            icon: "fa-solid fa-upload ",
            onClick: () => {
              const nodeDatabase = this.getNodeDatabase(this.selectedNode);
              tabsStore.createUtilityTab(this.selectedNode, nodeDatabase, 'Restore');
            },
          },
          COMMENT_MENUITEM,
          {
            label: "Drop Schema",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
            let template = this.templates.drop_schema.replace(
                  "#schema_name#",
                  this.selectedNode.data.schema_raw
                )
              this.prepareDropModal(this.selectedNode, template)
            },
          },
        ],
        cm_tables: [
          this.cmRefreshObject,
          {
            label: "Create Table",
            icon: "fas fa-plus",
            onClick: () => {
              tabsStore.createSchemaEditorTab(this.selectedNode.title, this.selectedNode.data.schema, operationModes.CREATE);
            },
          },
          {
            label: "Doc: Basics",
            icon: "fas fa-globe-americas",
            onClick: () => {
              this.openWebSite(
                `https://www.postgresql.org/docs/${this.serverVersion}/ddl-basics.html`
              );
            },
          },
          {
            label: "Doc: Constraints",
            icon: "fas fa-globe-americas",
            onClick: () => {
              this.openWebSite(
                `https://www.postgresql.org/docs/${this.serverVersion}/ddl-constraints.html`
              );
            },
          },
          {
            label: "Doc: Modifying",
            icon: "fas fa-globe-americas",
            onClick: () => {
              this.openWebSite(
                `https://www.postgresql.org/docs/${this.serverVersion}/ddl-alter.html`
              );
            },
          },
        ],
        cm_table: [
          this.cmRefreshObject,
          {
            label: "Query Data",
            icon: "fas fa-search",
            onClick: () => {
              TemplateSelectPostgresql(
                this.selectedNode.data.schema_raw,
                this.selectedNode.data.raw_value,
                "t"
              );
            },
          },
          {
            label: "Edit Data",
            icon: "fas fa-table",
            onClick: () => {
              tabsStore.createDataEditorTab(this.selectedNode.data.raw_value, this.selectedNode.data.schema_raw)
            },
          },
          {
            label: "Alter Table",
            icon: "fas fa-edit",
            onClick: () => {
              tabsStore.createSchemaEditorTab(this.selectedNode.title, this.selectedNode.data.schema, operationModes.UPDATE);
            },
          },
          {
            label: "Backup",
            icon: "fa-solid fa-download ",
            onClick: () => {
              const nodeDatabase = this.getNodeDatabase(this.selectedNode);
              tabsStore.createUtilityTab(this.selectedNode, nodeDatabase, 'Backup');
            },
          },
          {
            label: "Restore",
            icon: "fa-solid fa-upload ",
            onClick: () => {
              const nodeDatabase = this.getNodeDatabase(this.selectedNode);
              tabsStore.createUtilityTab(this.selectedNode, nodeDatabase, 'Restore');
            },
          },
          {
            label: "Templates",
            icon: "fas fa-list",
            children: [
              {
                label: "Insert Record",
                icon: "fas fa-edit",
                onClick: () => {
                  TemplateInsertPostgresql(
                    this.selectedNode.data.schema_raw,
                    this.selectedNode.data.raw_value
                  );
                },
              },
              {
                label: "Update Records",
                icon: "fas fa-edit",
                onClick: () => {
                  TemplateUpdatePostgresql(
                    this.selectedNode.data.schema_raw,
                    this.selectedNode.data.raw_value
                  );
                },
              },
              {
                label: "Delete Records",
                icon: "fas fa-times",
                onClick: () => {
                  tabSQLTemplate(
                    "Delete Records",
                    this.templates.delete.replace(
                      "#table_name#",
                      `${this.selectedNode.data.schema_raw}.${this.selectedNode.data.raw_value}`
                    )
                  );
                },
              },
              {
                label: "Truncate Table",
                icon: "fas fa-cut",
                onClick: () => {
                  tabSQLTemplate(
                    "Truncate Table",
                    this.templates.truncate.replace(
                      "#table_name#",
                      `${this.selectedNode.data.schema_raw}.${this.selectedNode.data.raw_value}`
                    )
                  );
                },
              },
              {
                label: "Vacuum Table",
                icon: "fas fa-broom",
                onClick: () => {
                  tabSQLTemplate(
                    "Vacuum table",
                    this.templates.vacuum_table.replace(
                      "#table_name#",
                      `${this.selectedNode.data.schema_raw}.${this.selectedNode.data.raw_value}`
                    )
                  );
                },
              },
              {
                label: "Analyze Table",
                icon: "fas fa-search-plus",
                onClick: () => {
                  tabSQLTemplate(
                    "Analyze Table",
                    this.templates.analyze_table.replace(
                      "#table_name#",
                      `${this.selectedNode.data.schema_raw}.${this.selectedNode.data.raw_value}`
                    )
                  );
                },
              },
            ],
          },
          COMMENT_MENUITEM,
          {
            label: "Drop Table",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              let template = this.templates.drop_table.replace(
                "#table_name#",
                `${this.selectedNode.data.schema_raw}.${this.selectedNode.data.raw_value}`
              )
              this.prepareDropModal(this.selectedNode, template)
            },
          },
        ],
        cm_columns: [
          {
            label: "Create Column",
            icon: "fas fa-plus",
            onClick: () => {
              tabSQLTemplate(
                "Create Column",
                this.templates.create_column.replace(
                  "#table_name#",
                  `${this.selectedNode.data.schema_raw}.${this.getParentNode(this.selectedNode).data.raw_value
                  }`
                )
              );
            },
          },
        ],
        cm_column: [
          {
            // FIXME: do we need alter column templates at all?
            label: "Alter Column",
            icon: "fas fa-edit",
            onClick: () => {
              tabSQLTemplate(
                "Alter Column",
                this.templates.alter_column
                  .replace(
                    "#table_name#",
                    `${this.selectedNode.data.schema_raw}.${this.getParentNodeDeep(this.selectedNode, 2).data
                      .raw_value
                    }`
                  )
                  .replace(/#column_name#/g, this.selectedNode.data.raw_value)
              );
            },
          },
          COMMENT_MENUITEM,

          {
            label: "Drop Column",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              let template = this.templates.drop_column.replace(
                "#table_name#",
                `${this.selectedNode.data.schema_raw}.${this.getParentNodeDeep(this.selectedNode, 2).data
                  .raw_value
                }`
              ).replace(/#column_name#/g, this.selectedNode.data.raw_value)
              this.prepareDropModal(this.selectedNode, template)
            },
          },
        ],
        cm_pks: [
          this.cmRefreshObject,
          {
            label: "Create Primary Key",
            icon: "fas fa-plus",
            onClick: () => {
              tabSQLTemplate(
                "Create Primary Key",
                this.templates.create_primarykey.replace(
                  "#table_name#",
                  `${this.selectedNode.data.schema_raw}.${this.getParentNode(this.selectedNode).data.raw_value
                  }`
                )
              );
            },
          },
        ],
        cm_pk: [
          this.cmRefreshObject,
          COMMENT_MENUITEM,
          {
            label: "Drop Primary Key",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              let template = this.templates.drop_primarykey
                  .replace(
                    "#table_name#",
                    `${this.selectedNode.data.schema_raw}.${this.getParentNodeDeep(this.selectedNode, 2).data
                      .raw_value
                    }`
                  )
                  .replace(
                    "#constraint_name#",
                    this.selectedNode.data.raw_value
                  )
              this.prepareDropModal(this.selectedNode, template)
            },
          },
        ],
        cm_fks: [
          this.cmRefreshObject,
          {
            label: "Create Foreign Key",
            icon: "fas fa-plus",
            onClick: () => {
              tabSQLTemplate(
                "Create Foreign Key",
                this.templates.create_foreignkey.replace(
                  "#table_name#",
                  `${this.selectedNode.data.schema_raw}.${this.getParentNode(this.selectedNode).data.raw_value
                  }`
                )
              );
            },
          },
        ],
        cm_fk: [
          this.cmRefreshObject,
          COMMENT_MENUITEM,
          {
            label: "Drop Foreign Key",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              let template = this.templates.drop_foreignkey
                  .replace(
                    "#table_name#",
                    `${this.selectedNode.data.schema_raw}.${this.getParentNodeDeep(this.selectedNode, 2).data
                      .raw_value
                    }`
                  )
                  .replace(
                    "#constraint_name#",
                    this.selectedNode.data.raw_value
                  )
              this.prepareDropModal(this.selectedNode, template)
            },
          },
        ],
        cm_uniques: [
          this.cmRefreshObject,
          {
            label: "Create Unique",
            icon: "fas fa-plus",
            onClick: () => {
              tabSQLTemplate(
                "Create Unique",
                this.templates.create_unique.replace(
                  "#table_name#",
                  `${this.selectedNode.data.schema_raw}.${this.getParentNode(this.selectedNode).data.raw_value
                  }`
                )
              );
            },
          },
        ],
        cm_unique: [
          this.cmRefreshObject,
          COMMENT_MENUITEM,
          {
            label: "Drop Unique",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              let template = this.templates.drop_unique
                  .replace(
                    "#table_name#",
                    `${this.selectedNode.data.schema_raw}.${this.getParentNodeDeep(this.selectedNode, 2).data
                      .raw_value
                    }`
                  )
                  .replace(
                    "#constraint_name#",
                    this.selectedNode.data.raw_value
                  )
              this.prepareDropModal(this.selectedNode, template)
            },
          },
        ],
        cm_checks: [
          this.cmRefreshObject,
          {
            label: "Create Check",
            icon: "fas fa-plus",
            onClick: () => {
              tabSQLTemplate(
                "Create Check",
                this.templates.create_check.replace(
                  "#table_name#",
                  `${this.selectedNode.data.schema_raw}.${this.getParentNode(this.selectedNode).data.raw_value
                  }`
                )
              );
            },
          },
        ],
        cm_check: [
          COMMENT_MENUITEM,
          {
            label: "Drop Check",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              let template = this.templates.drop_check
                .replace(
                  "#table_name#",
                  `${this.selectedNode.data.schema_raw}.${this.getParentNodeDeep(this.selectedNode, 2).data
                    .raw_value
                  }`
                )
                .replace(
                  "#constraint_name#",
                  this.selectedNode.data.raw_value
                )
              this.prepareDropModal(this.selectedNode, template)
            },
          },
        ],
        cm_excludes: [
          this.cmRefreshObject,
          {
            label: "Create Exclude",
            icon: "fas fa-plus",
            onClick: () => {
              tabSQLTemplate(
                "Create Exclude",
                this.templates.create_exclude.replace(
                  "#table_name#",
                  `${this.selectedNode.data.schema_raw}.${this.getParentNode(this.selectedNode).data.raw_value
                  }`
                )
              );
            },
          },
        ],
        cm_exclude: [
          COMMENT_MENUITEM,
          {
            label: "Drop Exclude",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              let template = this.templates.drop_exclude
                  .replace(
                    "#table_name#",
                    `${this.selectedNode.data.schema_raw}.${this.getParentNodeDeep(this.selectedNode, 2).data
                      .raw_value
                    }`
                  )
                  .replace(
                    "#constraint_name#",
                    this.selectedNode.data.raw_value
                  )
              this.prepareDropModal(this.selectedNode, template)
            },
          },
        ],
        cm_indexes: [
          this.cmRefreshObject,
          {
            label: "Create Index",
            icon: "fas fa-plus",
            onClick: () => {
              tabSQLTemplate(
                "Create Index",
                this.templates.create_index.replace(
                  "#table_name#",
                  `${this.selectedNode.data.schema_raw}.${this.getParentNode(this.selectedNode).data.raw_value
                  }`
                )
              );
            },
          },
          {
            label: "Doc: Indexes",
            icon: "fas fa-globe-americas",
            onClick: () => {
              this.openWebSite(
                `https://www.postgresql.org/docs/${this.serverVersion}/indexes.html`
              );
            },
          },
        ],
        cm_index: [
          this.cmRefreshObject,
          {
            label: "Alter Index",
            icon: "fas fa-edit",
            onClick: () => {
              tabSQLTemplate(
                "Alter Index",
                this.templates.alter_index.replace(
                  "#index_name#",
                  `${this.selectedNode.data.schema_raw}.${this.selectedNode.data.raw_value}`
                )
              );
            },
          },
          {
            label: "Reindex",
            icon: "fas fa-edit",
            onClick: () => {
              tabSQLTemplate(
                "Reindex",
                this.templates.reindex.replace(
                  "#index_name#",
                  `${this.selectedNode.data.schema_raw}.${this.selectedNode.data.raw_value}`
                )
              );
            },
          },
          COMMENT_MENUITEM,
          {
            label: "Drop Index",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              let template = this.templates.drop_index.replace(
                "#index_name#",
                `${this.selectedNode.data.schema_raw}.${this.selectedNode.data.raw_value}`
              )
              this.prepareDropModal(this.selectedNode, template)
            },
          },
        ],
        cm_rules: [
          this.cmRefreshObject,
          {
            label: "Create Rule",
            icon: "fas fa-plus",
            onClick: () => {
              tabSQLTemplate(
                "Create Rule",
                this.templates.create_rule.replace(
                  "#table_name#",
                  `${this.selectedNode.data.schema_raw}.${this.getParentNode(this.selectedNode).data.raw_value
                  }`
                )
              );
            },
          },
          {
            label: "Doc: Rules",
            icon: "fas fa-globe-americas",
            onClick: () => {
              this.openWebSite(
                `https://www.postgresql.org/docs/${this.serverVersion}/rules.html`
              );
            },
          },
        ],
        cm_rule: [
          {
            label: "Alter Rule",
            icon: "fas fa-edit",
            onClick: () => {
              tabSQLTemplate(
                "Alter Rule",
                this.templates.alter_rule
                  .replace(
                    "#table_name#",
                    `${this.selectedNode.data.schema_raw}.${this.getParentNodeDeep(this.selectedNode, 2).data
                      .raw_value
                    }`
                  )
                  .replace("#rule_name#", this.selectedNode.data.raw_value)
              );
            },
          },
          {
            label: "Edit Rule",
            icon: "fas fa-edit",
            onClick: () => {
              this.getRuleDefinitionPostgresql(this.selectedNode);
            },
          },
          COMMENT_MENUITEM,
          {
            label: "Drop Rule",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              let template = this.templates.drop_rule
                  .replace(
                    "#table_name#",
                    `${this.selectedNode.data.schema_raw}.${this.getParentNodeDeep(this.selectedNode, 2).data
                      .raw_value
                    }`
                  )
                  .replace("#rule_name#", this.selectedNode.data.raw_value)
              this.prepareDropModal(this.selectedNode, template)
            },
          },
        ],
        cm_triggers: [
          this.cmRefreshObject,
          {
            label: "Create Trigger",
            icon: "fas fa-plus",
            onClick: () => {
              tabSQLTemplate(
                "Create Trigger",
                this.templates.create_trigger.replace(
                  "#table_name#",
                  `${this.selectedNode.data.schema_raw}.${this.getParentNode(this.selectedNode).data.raw_value
                  }`
                )
              );
            },
          },
          {
            label: "Doc: Triggers",
            icon: "fas fa-globe-americas",
            onClick: () => {
              this.openWebSite(
                `https://www.postgresql.org/docs/${this.serverVersion}/trigger-definition.html`
              );
            },
          },
        ],
        cm_trigger: [
          {
            label: "Alter Trigger",
            icon: "fas fa-edit",
            onClick: () => {
              tabSQLTemplate(
                "Alter Trigger",
                this.templates.alter_trigger
                  .replace(
                    "#table_name#",
                    `${this.selectedNode.data.schema_raw}.${this.getParentNodeDeep(this.selectedNode, 2).data
                      .raw_value
                    }`
                  )
                  .replace("#trigger_name#", this.selectedNode.data.raw_value)
              );
            },
          },
          {
            label: "Enable Trigger",
            icon: "fas fa-edit",
            onClick: () => {
              tabSQLTemplate(
                "Enable Trigger",
                this.templates.enable_trigger
                  .replace(
                    "#table_name#",
                    `${this.selectedNode.data.schema_raw}.${this.getParentNodeDeep(this.selectedNode, 2).data
                      .raw_value
                    }`
                  )
                  .replace("#trigger_name#", this.selectedNode.data.raw_value)
              );
            },
          },
          {
            label: "Disable Trigger",
            icon: "fas fa-edit",
            onClick: () => {
              tabSQLTemplate(
                "Disable Trigger",
                this.templates.disable_trigger
                  .replace(
                    "#table_name#",
                    `${this.selectedNode.data.schema_raw}.${this.getParentNodeDeep(this.selectedNode, 2).data
                      .raw_value
                    }`
                  )
                  .replace("#trigger_name#", this.selectedNode.data.raw_value)
              );
            },
          },
          {
            label: "Restore",
            icon: "fa-solid fa-upload ",
            onClick: () => {
              const nodeDatabase = this.getNodeDatabase(this.selectedNode);
              tabsStore.createUtilityTab(this.selectedNode, nodeDatabase, 'Restore');
            },
          },
          COMMENT_MENUITEM,
          {
            label: "Drop Trigger",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              let template = this.templates.drop_trigger
                  .replace(
                    "#table_name#",
                    `${this.selectedNode.data.schema_raw}.${this.getParentNodeDeep(this.selectedNode, 2).data
                      .raw_value
                    }`
                  )
                  .replace("#trigger_name#", this.selectedNode.data.raw_value)
              this.prepareDropModal(this.selectedNode, template)
            },
          }
        ],
        cm_direct_trigger_function: [
          this.cmRefreshObject,
          {
            label: "Edit Trigger Function",
            icon: "fas fa-edit",
            onClick: () => {
              this.getTriggerFunctionDefinitionPostgresql(this.selectedNode);
            },
          },
          {
            label: "Alter Trigger Function",
            icon: "fas fa-edit",
            onClick: () => {
              tabSQLTemplate(
                "Alter Trigger Function",
                this.templates.alter_triggerfunction.replace(
                  "#function_name#",
                  this.selectedNode.data.id
                )
              );
            },
          },
          COMMENT_MENUITEM,
          {
            label: "Drop Trigger Function",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              let template = this.templates.drop_triggerfunction.replace(
                  "#function_name#",
                  this.selectedNode.data.id
                )
              this.prepareDropModal(this.selectedNode, template)
            },
          }
        ],
        cm_inheriteds: [
          this.cmRefreshObject,
          {
            label: "Create Inherited",
            icon: "fas fa-plus",
            onClick: () => {
              tabSQLTemplate(
                "Create Inherited",
                this.templates.create_inherited.replace(
                  "#table_name#",
                  `${this.selectedNode.data.schema}.${this.getParentNode(this.selectedNode).title
                  }`
                )
              );
            },
          },
          {
            label: "Doc: Partitioning",
            icon: "fas fa-globe-americas",
            onClick: () => {
              this.openWebSite(
                `https://www.postgresql.org/docs/${this.serverVersion}/ddl-partitioning.html`
              );
            },
          },
        ],
        cm_inherited: [
          {
            label: "No Inherit Table",
            icon: "fas fa-edit",
            onClick: () => {
              tabSQLTemplate(
                "No Inherit Partition",
                this.templates.noinherit_partition
                  .replace(
                    "#table_name#",
                    `${this.selectedNode.data.schema}.${this.getParentNodeDeep(this.selectedNode, 2).title
                    }`
                  )
                  .replace("#partition_name#", this.selectedNode.title)
              );
            },
          },
          {
            label: "Drop Inherited",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              let template = this.templates.drop_partition.replace(
                  "#partition_name#",
                  this.selectedNode.title
                )
              this.prepareDropModal(this.selectedNode, template)
            },
          }
        ],
        cm_partitions: [
          this.cmRefreshObject,
          {
            label: "Create Partition",
            icon: "fas fa-plus",
            onClick: () => {
              tabSQLTemplate(
                "Create Partition",
                this.templates.create_partition.replace(
                  "#table_name#",
                  `${this.selectedNode.data.schema_raw}.${this.getParentNode(this.selectedNode).data.raw_value
                  }`
                )
              );
            },
          },
          {
            label: "Doc: Partitioning",
            icon: "fas fa-globe-americas",
            onClick: () => {
              this.openWebSite(
                `https://www.postgresql.org/docs/${this.serverVersion}/ddl-partitioning.html`
              );
            },
          },
        ],
        cm_partition: [
          {
            label: "Detach Partition",
            icon: "fas fa-edit",
            onClick: () => {
              tabSQLTemplate(
                "Detach Partition",
                this.templates.detach_partition
                  .replace(
                    "#table_name#",
                    `${this.selectedNode.data.schema_raw}.${this.getParentNodeDeep(this.selectedNode, 2).data
                      .raw_value
                    }`
                  )
                  .replace("#partition_name#", this.selectedNode.data.raw_value)
              );
            },
          },
          {
            label: "Drop Partition",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              let template = this.templates.drop_partition.replace(
                  "#partition_name#",
                  this.selectedNode.title
                )
              this.prepareDropModal(this.selectedNode, template)
            },
          }
        ],
        cm_statistics: [
          this.cmRefreshObject,
          {
            label: "Create Statistics",
            icon: "fas fa-plus",
            onClick: () => {
              tabSQLTemplate(
                "Create Statistics",
                this.templates.create_statistics
                  .replace(
                    "#table_name#",
                    `${this.selectedNode.data.schema}.${this.getParentNode(this.selectedNode).title
                    }`
                  )
                  .replace("#schema_name#", this.selectedNode.data.schema)
              );
            },
          },
          {
            label: "Doc: Statistics",
            icon: "fas fa-globe-americas",
            onClick: () => {
              this.openWebSite(
                `https://www.postgresql.org/docs/${this.serverVersion}/planner-stats.html`
              );
            },
          },
        ],
        cm_statistic: [
          this.cmRefreshObject,
          {
            label: "Alter Statistics",
            icon: "fas fa-edit",
            onClick: () => {
              tabSQLTemplate(
                "Alter Statistics",
                this.templates.alter_statistics.replace(
                  "#statistics_name#",
                  this.selectedNode.data.raw_value
                )
              );
            },
          },
          COMMENT_MENUITEM,
          {
            label: "Drop Statistics",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              let template = this.templates.drop_statistics.replace(
                  "#statistics_name#",
                  this.selectedNode.data.raw_value
                )
              this.prepareDropModal(this.selectedNode, template)
            },
          }
        ],
        cm_partitioned_tables: [
          this.cmRefreshObject,
          {
            label: "Doc: Partitioning",
            icon: "fas fa-globe-americas",
            onClick: () => {
              this.openWebSite(
                `https://www.postgresql.org/docs/${this.serverVersion}/ddl-partitioning.html`
              );
            },
          },
        ],
        cm_partitioned_parent: [this.cmRefreshObject],
        cm_inherited_tables: [
          this.cmRefreshObject,
          {
            label: "Doc: Inheritance",
            icon: "fas fa-globe-americas",
            onClick: () => {
              this.openWebSite(
                `https://www.postgresql.org/docs/${this.serverVersion}/tutorial-inheritance.html`
              );
            },
          },
        ],
        cm_inherited_parent: [this.cmRefreshObject],
        cm_foreign_tables: [
          this.cmRefreshObject,
          {
            label: "Create Foreign Table",
            icon: "fas fa-plus",
            onClick: () => {
              tabSQLTemplate(
                "Create Foreign Table",
                this.templates.create_foreign_table.replace(
                  "#schema_name#",
                  this.selectedNode.data.schema_raw
                )
              );
            },
          },
        ],
        cm_foreign_table: [
          this.cmRefreshObject,
          {
            label: "Query Data",
            icon: "fas fa-search",
            onClick: () => {
              TemplateSelectPostgresql(
                this.selectedNode.data.schema_raw,
                this.selectedNode.data.raw_value,
                "f"
              );
            },
          },
          {
            label: "Edit Data",
            icon: "fas fa-table",
            onClick: () => {
              tabsStore.createDataEditorTab(this.selectedNode.data.raw_value, this.selectedNode.data.schema_raw)
            },
          },
          {
            label: "Alter Foreign Table",
            icon: "fas fa-edit",
            onClick: () => {
              tabSQLTemplate(
                "Alter Foreign Table",
                this.templates.alter_foreign_table.replace(
                  "#table_name#",
                  `${this.selectedNode.data.schema_raw}.${this.selectedNode.data.raw_value}`
                )
              );
            },
          },
          {
            label: "Templates",
            icon: "fas fa-list",
            children: [
            {
                label: "Insert Record",
                icon: "fas fa-edit",
                onClick: () => {
                  TemplateInsertPostgresql(
                    this.selectedNode.data.schema_raw,
                    this.selectedNode.data.raw_value
                  );
                },
              },
              {
                label: "Update Records",
                icon: "fas fa-edit",
                onClick: () => {
                  TemplateUpdatePostgresql(
                    this.selectedNode.data.schema_raw,
                    this.selectedNode.data.raw_value
                  );
                },
              },
              {
                label: "Delete Records",
                icon: "fas fa-times",
                onClick: () => {
                  tabSQLTemplate(
                    "Delete Records",
                    this.templates.delete.replace(
                      "#table_name#",
                      `${this.selectedNode.data.schema_raw}.${this.selectedNode.data.raw_value}`
                    )
                  );
                },
              },
              {
                label: "Analyze Foreign Table",
                icon: "fas fa-table",
                onClick: () => {
                  tabSQLTemplate(
                    "Analyze Foreign Table",
                    this.templates.analyze_table.replace(
                      "#table_name#",
                      `${this.selectedNode.data.schema_raw}.${this.selectedNode.data.raw_value}`
                    )
                  );
                },
              },
            ],
          },
          COMMENT_MENUITEM,
          {
            label: "Drop Foreign Table",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              let template = this.templates.drop_foreign_table.replace(
                  "#table_name#",
                  `${this.selectedNode.data.schema_raw}.${this.selectedNode.data.raw_value}`
                )
              this.prepareDropModal(this.selectedNode, template)
            },
          }
        ],
        cm_foreign_columns: [
          {
            label: "Create Foreign Column",
            icon: "fas fa-plus",
            onClick: () => {
              tabSQLTemplate(
                "Create Foreign Column",
                this.templates.create_foreign_column.replace(
                  "#table_name#",
                  `${this.selectedNode.data.schema_raw}.${this.getParentNode(this.selectedNode).data.raw_value
                  }`
                )
              );
            },
          },
        ],
        cm_foreign_column: [
          {
            label: "Alter Foreign Column",
            icon: "fas fa-edit",
            onClick: () => {
              tabSQLTemplate(
                "Alter Foreign Column",
                this.templates.alter_foreign_column
                  .replace(
                    "#table_name#",
                    `${this.selectedNode.data.schema_raw}.${this.getParentNodeDeep(this.selectedNode, 2).data
                      .raw_value
                    }`
                  )
                  .replace(/#column_name#/g, this.selectedNode.data.raw_value)
              );
            },
          },
          {
            label: "Drop Foreign Column",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              let template = this.templates.drop_foreign_column
                    .replace(
                      "#table_name#",
                      `${this.selectedNode.data.schema_raw}.${this.getParentNodeDeep(this.selectedNode, 2).data
                        .raw_value
                      }`
                    )
                    .replace(/#column_name#/g, this.selectedNode.data.raw_value)
              this.prepareDropModal(this.selectedNode, template)
            },
          }
        ],
        cm_sequences: [
          this.cmRefreshObject,
          {
            label: "Create Sequence",
            icon: "fas fa-plus",
            onClick: () => {
              tabSQLTemplate(
                "Create Sequence",
                this.templates.create_sequence.replace(
                  "#schema_name#",
                  this.selectedNode.data.schema_raw
                )
              );
            },
          },
          {
            label: "Doc: Sequences",
            icon: "fas fa-globe-americas",
            onClick: () => {
              this.openWebSite(
                `https://www.postgresql.org/docs/${this.serverVersion}/sql-createsequence.html`
              );
            },
          },
        ],
        cm_sequence: [
          {
            label: "Alter Sequence",
            icon: "fas fa-edit",
            onClick: () => {
              tabSQLTemplate(
                "Alter Sequence",
                this.templates.alter_sequence.replace(
                  "#sequence_name#",
                  `${this.selectedNode.data.schema_raw}.${this.selectedNode.data.raw_value}`
                )
              );
            },
          },
          COMMENT_MENUITEM,
          {
            label: "Drop Sequence",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              let template = this.templates.drop_sequence.replace(
                  "#sequence_name#",
                  `${this.selectedNode.data.schema_raw}.${this.selectedNode.data.raw_value}`
                )
              this.prepareDropModal(this.selectedNode, template)
            },
          }
        ],
        cm_views: [
          this.cmRefreshObject,
          {
            label: "Create View",
            icon: "fas fa-plus",
            onClick: () => {
              tabSQLTemplate(
                "Create View",
                this.templates.create_view.replace(
                  "#schema_name#",
                  this.selectedNode.data.schema_raw
                )
              );
            },
          },
          {
            label: "Doc: Views",
            icon: "fas fa-globe-americas",
            onClick: () => {
              this.openWebSite(
                `https://www.postgresql.org/docs/${this.serverVersion}/sql-createview.html`
              );
            },
          },
        ],
        cm_view: [
          this.cmRefreshObject,
          {
            label: "Query Data",
            icon: "fas fa-search",
            onClick: () => {
              TemplateSelectPostgresql(
                this.selectedNode.data.schema_raw,
                this.selectedNode.data.raw_value,
                "v"
              );
            },
          },
          {
            label: "Edit View",
            icon: "fas fa-edit",
            onClick: () => {
              this.getViewDefinitionPostgresql(this.selectedNode);
            },
          },
          {
            label: "Alter View",
            icon: "fas fa-edit",
            onClick: () => {
              tabSQLTemplate(
                "Alter View",
                this.templates.alter_view.replace(
                  /#view_name#/g,
                  `${this.selectedNode.data.schema_raw}.${this.selectedNode.data.raw_value}`
                )
              );
            },
          },
          COMMENT_MENUITEM,
          {
            label: "Drop View",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              let template = this.templates.drop_view.replace(
                  "#view_name#",
                  `${this.selectedNode.data.schema_raw}.${this.selectedNode.data.raw_value}`
                )
              this.prepareDropModal(this.selectedNode, template)
            },
          }
        ],
        cm_view_triggers: [
          this.cmRefreshObject,
          {
            label: "Create Trigger",
            icon: "fas fa-plus",
            onClick: () => {
              tabSQLTemplate(
                "Create Trigger",
                this.templates.create_view_trigger.replace(
                  "#table_name#",
                  `${this.selectedNode.data.schema_raw}.${this.getParentNode(this.selectedNode).data.raw_value
                  }`
                )
              );
            },
          },
          {
            label: "Doc: Triggers",
            icon: "fas fa-globe-americas",
            onClick: () => {
              this.openWebSite(
                `https://www.postgresql.org/docs/${this.serverVersion}/trigger-definition.html`
              );
            },
          },
        ],
        cm_mviews: [
          this.cmRefreshObject,
          {
            label: "Create Mat. View",
            icon: "fas fa-plus",
            onClick: () => {
              tabSQLTemplate(
                "Create Materialized View",
                this.templates.create_mview.replace(
                  "#schema_name#",
                  this.selectedNode.data.schema_raw
                )
              );
            },
          },
          {
            label: "Doc: Mat. Views",
            icon: "fas fa-globe-americas",
            onClick: () => {
              this.openWebSite(
                `https://www.postgresql.org/docs/${this.serverVersion}/sql-creatematerializedview.html`
              );
            },
          },
        ],
        cm_mview: [
          this.cmRefreshObject,
          {
            label: "Query Data",
            icon: "fas fa-search",
            onClick: () => {
              TemplateSelectPostgresql(
                this.selectedNode.data.schema_raw,
                this.selectedNode.data.raw_value,
                "m"
              );
            },
          },
          {
            label: "Edit Mat. View",
            icon: "fas fa-edit",
            onClick: () => {
              this.getMaterializedViewDefinitionPostgresql(this.selectedNode);
            },
          },
          {
            label: "Alter Mat. View",
            icon: "fas fa-edit",
            onClick: () => {
              tabSQLTemplate(
                "Alter Materialized View",
                this.templates.alter_mview.replace(
                  "#view_name#",
                  `${this.selectedNode.data.schema_raw}.${this.selectedNode.data.raw_value}`
                )
              );
            },
          },
          {
            label: "Refresh Mat. View",
            icon: "fas fa-edit",
            onClick: () => {
              tabSQLTemplate(
                "Refresh Materialized View",
                this.templates.refresh_mview.replace(
                  "#view_name#",
                  `${this.selectedNode.data.schema_raw}.${this.selectedNode.data.raw_value}`
                )
              );
            },
          },
          {
            label: "Analyze Mat. View",
            icon: "fas fa-search-plus",
            onClick: () => {
              tabSQLTemplate(
                "Analyze Mat. View",
                this.templates.analyze_table.replace(
                  "#table_name#",
                  `${this.selectedNode.data.schema_raw}.${this.selectedNode.data.raw_value}`
                )
              );
            },
          },
          COMMENT_MENUITEM,
          {
            label: "Drop Mat. View",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              let template = this.templates.drop_mview.replace(
                  "#view_name#",
                  `${this.selectedNode.data.schema}.${this.selectedNode.data.raw_value}`
                )
              this.prepareDropModal(this.selectedNode, template)
            },
          }
        ],
        cm_functions: [
          this.cmRefreshObject,
          {
            label: "Create Function",
            icon: "fas fa-plus",
            onClick: () => {
              tabSQLTemplate(
                "Create Function",
                this.templates.create_function.replace(
                  "#schema_name#",
                  this.selectedNode.data.schema_raw
                )
              );
            },
          },
          {
            label: "Doc: Functions",
            icon: "fas fa-globe-americas",
            onClick: () => {
              this.openWebSite(
                `https://www.postgresql.org/docs/${this.serverVersion}/sql-createfunction.html`
              );
            },
          },
        ],
        cm_function: [
          this.cmRefreshObject,
          {
            label: "Select Function",
            icon: "fas fa-edit",
            onClick: () => {
              TemplateSelectFunctionPostgresql(
                this.selectedNode.data.schema_raw,
                this.selectedNode.data.raw_value,
                this.selectedNode.data.id
              );
            },
          },
          {
            label: "Edit Function",
            icon: "fas fa-edit",
            onClick: () => {
              this.getFunctionDefinitionPostgresql(this.selectedNode);
            },
          },
          {
            label: "Alter Function",
            icon: "fas fa-edit",
            onClick: () => {
              tabSQLTemplate(
                "Alter Function",
                this.templates.alter_function.replace(
                  "#function_name#",
                  this.selectedNode.data.id
                )
              );
            },
          },
          {
            label: "Restore",
            icon: "fa-solid fa-upload",
            onClick: () => {
              const nodeDatabase = this.getNodeDatabase(this.selectedNode);
              tabsStore.createUtilityTab(this.selectedNode, nodeDatabase, 'Restore');
            },
          },
          COMMENT_MENUITEM,
          {
            label: "Drop Function",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              let template = this.templates.drop_function.replace(
                  "#function_name#",
                  this.selectedNode.data.id
                )
              this.prepareDropModal(this.selectedNode, template)
            },
          }
        ],
        cm_trigger_functions: [
          this.cmRefreshObject,
          {
            label: "Create Trigger Function",
            icon: "fas fa-plus",
            onClick: () => {
              tabSQLTemplate(
                "Create Trigger Function",
                this.templates.create_triggerfunction.replace(
                  "#schema_name#",
                  this.selectedNode.data.schema_raw
                )
              );
            },
          },
          {
            label: "Doc: Trigger Functions",
            icon: "fas fa-globe-americas",
            onClick: () => {
              this.openWebSite(
                `https://www.postgresql.org/docs/${this.serverVersion}/plpgsql-trigger.html`
              );
            },
          },
        ],
        cm_trigger_function: [
          {
            label: "Edit Trigger Function",
            icon: "fas fa-edit",
            onClick: () => {
              this.getTriggerFunctionDefinitionPostgresql(this.selectedNode);
            },
          },
          {
            label: "Alter Trigger Function",
            icon: "fas fa-edit",
            onClick: () => {
              tabSQLTemplate(
                "Alter Trigger Function",
                this.templates.alter_triggerfunction.replace(
                  "#function_name#",
                  this.selectedNode.data.id
                )
              );
            },
          },
          COMMENT_MENUITEM,
          {
            label: "Drop Trigger Function",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              let template = this.templates.drop_triggerfunction.replace(
                  "#function_name#",
                  this.selectedNode.data.id
                )
              this.prepareDropModal(this.selectedNode, template)
            },
          }
        ],
        cm_event_trigger_functions: [
          this.cmRefreshObject,
          {
            label: "Create Event Trigger Function",
            icon: "fas fa-plus",
            onClick: () => {
              tabSQLTemplate(
                "Create Event Trigger Function",
                this.templates.create_eventtriggerfunction.replace(
                  "#schema_name#",
                  this.selectedNode.data.schema_raw
                )
              );
            },
          },
          {
            label: "Doc: Event Trigger Functions",
            icon: "fas fa-globe-americas",
            onClick: () => {
              this.openWebSite(
                `https://www.postgresql.org/docs/${this.serverVersion}/functions-event-triggers.html`
              );
            },
          },
        ],
        cm_event_trigger_function: [
          {
            label: "Edit Event Trigger Function",
            icon: "fas fa-edit",
            onClick: () => {
              this.getEventTriggerFunctionDefinitionPostgresql(
                this.selectedNode
              );
            },
          },
          {
            label: "Alter Event Trigger Function",
            icon: "fas fa-edit",
            onClick: () => {
              tabSQLTemplate(
                "Alter Event Trigger Function",
                this.templates.alter_eventtriggerfunction.replace(
                  "#function_name#",
                  this.selectedNode.data.id
                )
              );
            },
          },
          COMMENT_MENUITEM,
          {
            label: "Drop Event Trigger Function",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              let template = this.templates.drop_eventtriggerfunction.replace(
                  "#function_name#",
                  this.selectedNode.data.id
                )
              this.prepareDropModal(this.selectedNode, template)
            },
          }
        ],
        cm_procedures: [
          this.cmRefreshObject,
          {
            label: "Create Procedure",
            icon: "fas fa-plus",
            onClick: () => {
              tabSQLTemplate(
                "Create Procedure",
                this.templates.create_procedure.replace(
                  "#schema_name#",
                  this.selectedNode.data.schema
                )
              );
            },
          },
          {
            label: "Doc: Procedures",
            icon: "fas fa-globe-americas",
            onClick: () => {
              this.openWebSite(
                `https://www.postgresql.org/docs/${this.serverVersion}/sql-createprocedure.html`
              );
            },
          },
        ],
        cm_procedure: [
          this.cmRefreshObject,
          {
            label: "Call Procedure",
            icon: "fas fa-edit",
            onClick: () => {
              TemplateCallProcedurePostgresql(
                this.selectedNode.data.schema,
                this.selectedNode.title,
                this.selectedNode.data.id
              );
            },
          },
          {
            label: "Edit Procedure",
            icon: "fas fa-edit",
            onClick: () => {
              this.getProcedureDefinitionPostgresql(this.selectedNode);
            },
          },
          {
            label: "Alter Procedure",
            icon: "fas fa-edit",
            onClick: () => {
              tabSQLTemplate(
                "Alter Procedure",
                this.templates.alter_procedure.replace(
                  "#procedure_name#",
                  this.selectedNode.data.id
                )
              );
            },
          },
          COMMENT_MENUITEM,
          {
            label: "Drop Procedure",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              let template = this.templates.drop_procedure.replace(
                  "#procedure_name#",
                  this.selectedNode.data.id
                )
              this.prepareDropModal(this.selectedNode, template)
            },
          }
        ],
        cm_aggregates: [
          this.cmRefreshObject,
          {
            label: "Create Aggregate",
            icon: "fas fa-plus",
            onClick: () => {
              tabSQLTemplate(
                "Create Aggregate",
                this.templates.create_aggregate.replace(
                  "#schema_name#",
                  this.selectedNode.data.schema
                )
              );
            },
          },
          {
            label: "Doc: Aggregates",
            icon: "fas fa-globe-americas",
            onClick: () => {
              this.openWebSite(
                `https://www.postgresql.org/docs/${this.serverVersion}/sql-createaggregate.html`
              );
            },
          },
        ],
        cm_aggregate: [
          this.cmRefreshObject,
          {
            label: "Alter Aggregate",
            icon: "fas fa-edit",
            onClick: () => {
              tabSQLTemplate(
                "Alter Aggregate",
                this.templates.alter_aggregate.replace(
                  "#aggregate_name#",
                  this.selectedNode.data.id
                )
              );
            },
          },
          COMMENT_MENUITEM,
          {
            label: "Drop Aggregate",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              let template = this.templates.drop_aggregate.replace(
                  "#aggregate_name#",
                  this.selectedNode.data.id
                )
              this.prepareDropModal(this.selectedNode, template)
            },
          },
        ],
        cm_types: [
          this.cmRefreshObject,
          {
            label: "Create Type",
            icon: "fas fa-plus",
            onClick: () => {
              tabSQLTemplate(
                "Create Type",
                this.templates.create_type.replace(
                  "#schema_name#",
                  this.selectedNode.data.schema_raw
                )
              );
            },
          },
          {
            label: "Doc: Types",
            icon: "fas fa-globe-americas",
            onClick: () => {
              this.openWebSite(
                `https://www.postgresql.org/docs/${this.serverVersion}/sql-createtype.html`
              );
            },
          },
        ],
        cm_type: [
          {
            label: "Alter Type",
            icon: "fas fa-edit",
            onClick: () => {
              tabSQLTemplate(
                "Alter Type",
                this.templates.alter_type.replace(
                  "#type_name#",
                  `${this.selectedNode.data.schema_raw}.${this.selectedNode.data.raw_value}`
                )
              );
            },
          },
          COMMENT_MENUITEM,
          {
            label: "Drop Type",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              let template = this.templates.drop_type.replace(
                  "#type_name#",
                  `${this.selectedNode.data.schema_raw}.${this.selectedNode.data.raw_value}`
                )
              this.prepareDropModal(this.selectedNode, template)
            },
          },
        ],
        cm_domains: [
          this.cmRefreshObject,
          {
            label: "Create Domain",
            icon: "fas fa-plus",
            onClick: () => {
              tabSQLTemplate(
                "Create Domain",
                this.templates.create_domain.replace(
                  "#schema_name#",
                  this.selectedNode.data.schema_raw
                )
              );
            },
          },
          {
            label: "Doc: Domains",
            icon: "fas fa-globe-americas",
            onClick: () => {
              this.openWebSite(
                `https://www.postgresql.org/docs/${this.serverVersion}/sql-createdomain.html`
              );
            },
          },
        ],
        cm_domain: [
          {
            label: "Alter Domain",
            icon: "fas fa-edit",
            onClick: () => {
              tabSQLTemplate(
                "Alter Domain",
                this.templates.alter_domain.replace(
                  "#domain_name#",
                  `${this.selectedNode.data.schema_raw}.${this.selectedNode.data.raw_value}`
                )
              );
            },
          },
          COMMENT_MENUITEM,
          {
            label: "Drop Domain",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              let template = this.templates.drop_domain.replace(
                  "#domain_name#",
                  `${this.selectedNode.data.schema_raw}.${this.selectedNode.data.raw_value}`
                )
              this.prepareDropModal(this.selectedNode, template)
            },
          },
        ],
        cm_extensions: [
          this.cmRefreshObject,
          {
            label: "Create Extension",
            icon: "fas fa-plus",
            onClick: () => {
              createExtensionModal(this.selectedNode, operationModes.CREATE);
            },
          },
          {
            label: "Doc: Extensions",
            icon: "fas fa-globe-americas",
            onClick: () => {
              this.openWebSite(
                `https://www.postgresql.org/docs/${this.serverVersion}/extend-extensions.html`
              );
            },
          },
        ],
        cm_extension: [
          {
            label: "Alter Extension",
            icon: "fas fa-edit",
            onClick: () => {
              createExtensionModal(this.selectedNode, operationModes.UPDATE);
            },
          },
          COMMENT_MENUITEM,
          {
            label: "Drop Extension",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              createExtensionModal(this.selectedNode, operationModes.DELETE);
            },
          },
        ],
        cm_foreign_data_wrappers: [
          this.cmRefreshObject,
          {
            label: "Create Foreign Data Wrapper",
            icon: "fas fa-plus",
            onClick: () => {
              tabSQLTemplate(
                "Create Foreign Data Wrapper",
                this.templates.create_fdw
              );
            },
          },
          {
            label: "Doc: Foreign Data Wrappers",
            icon: "fas fa-globe-americas",
            onClick: () => {
              this.openWebSite(
                `https://www.postgresql.org/docs/${this.serverVersion}/postgres-fdw.html`
              );
            },
          },
        ],
        cm_foreign_data_wrapper: [
          {
            label: "Alter Foreign Data Wrapper",
            icon: "fas fa-edit",
            onClick: () => {
              tabSQLTemplate(
                "Alter Foreign Data Wrapper",
                this.templates.alter_fdw.replace(
                  "#fdwname#",
                  this.selectedNode.title
                )
              );
            },
          },
          COMMENT_MENUITEM,
          {
            label: "Drop Foreign Data Wrapper",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              let template = this.templates.drop_fdw.replace(
                  "#fdwname#",
                  this.selectedNode.title
                )
              this.prepareDropModal(this.selectedNode, template)
            },
          },
        ],
        cm_foreign_servers: [
          this.cmRefreshObject,
          {
            label: "Create Foreign Server",
            icon: "fas fa-plus",
            onClick: () => {
              tabSQLTemplate(
                "Create Foreign Server",
                this.templates.create_foreign_server.replace(
                  "#fdwname#",
                  this.getParentNode(this.selectedNode).title
                )
              );
            },
          },
        ],
        cm_foreign_server: [
          {
            label: "Alter Foreign Server",
            icon: "fas fa-edit",
            onClick: () => {
              tabSQLTemplate(
                "Alter Foreign Server",
                this.templates.alter_foreign_server.replace(
                  "#srvname#",
                  this.selectedNode.data.raw_value
                )
              );
            },
          },
          {
            label: "Import Foreign Schema",
            icon: "fas fa-edit",
            onClick: () => {
              tabSQLTemplate(
                "Import Foreign Schema",
                this.templates.import_foreign_schema.replace(
                  "#srvname#",
                  this.selectedNode.data.raw_value
                )
              );
            },
          },
          COMMENT_MENUITEM,
          {
            label: "Drop Foreign Server",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              let template = this.templates.drop_foreign_server.replace(
                  "#srvname#",
                  this.selectedNode.data.raw_value
                )
              this.prepareDropModal(this.selectedNode, template)
            },
          },
        ],
        cm_user_mappings: [
          this.cmRefreshObject,
          {
            label: "Create User Mapping",
            icon: "fas fa-plus",
            onClick: () => {
              tabSQLTemplate(
                "Create User Mapping",
                this.templates.create_user_mapping.replace(
                  "#srvname#",
                  this.getParentNode(this.selectedNode).data.raw_value
                )
              );
            },
          },
        ],
        cm_user_mapping: [
          {
            label: "Alter User Mapping",
            icon: "fas fa-edit",
            onClick: () => {
              tabSQLTemplate(
                "Alter User Mapping",
                this.templates.alter_user_mapping
                  .replace("#user_name#", this.selectedNode.data.raw_value)
                  .replace(
                    "#srvname#",
                    this.getParentNodeDeep(this.selectedNode, 2).data.raw_value
                  )
              );
            },
          },
          {
            label: "Drop User Mapping",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              let template = this.templates.drop_user_mapping
                  .replace("#user_name#", this.selectedNode.data.raw_value)
                  .replace(
                    "#srvname#",
                    this.getParentNodeDeep(this.selectedNode, 2).data.raw_value
                  )
              this.prepareDropModal(this.selectedNode, template)
            },
          },
        ],
        cm_event_triggers: [
          this.cmRefreshObject,
          {
            label: "Create Event Trigger",
            icon: "fas fa-plus",
            onClick: () => {
              tabSQLTemplate(
                "Create Event Trigger",
                this.templates.create_eventtrigger
              );
            },
          },
          {
            label: "Doc: Event Triggers",
            icon: "fas fa-globe-americas",
            onClick: () => {
              this.openWebSite(
                `https://www.postgresql.org/docs/${this.serverVersion}/event-triggers.html`
              );
            },
          },
        ],
        cm_event_trigger: [
          {
            label: "Alter Event Trigger",
            icon: "fas fa-edit",
            onClick: () => {
              tabSQLTemplate(
                "Alter Trigger",
                this.templates.alter_eventtrigger.replace(
                  "#trigger_name#",
                  this.selectedNode.data.raw_value
                )
              );
            },
          },
          {
            label: "Enable Event Trigger",
            icon: "fas fa-edit",
            onClick: () => {
              tabSQLTemplate(
                "Enable Event Trigger",
                this.templates.enable_eventtrigger.replace(
                  "#trigger_name#",
                  this.selectedNode.data.raw_value
                )
              );
            },
          },
          {
            label: "Disable Event Trigger",
            icon: "fas fa-edit",
            onClick: () => {
              tabSQLTemplate(
                "Disable Event Trigger",
                this.templates.disable_eventtrigger.replace(
                  "#trigger_name#",
                  this.selectedNode.data.raw_value
                )
              );
            },
          },
          COMMENT_MENUITEM,
          {
            label: "Drop Event Trigger",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              let template = this.templates.drop_eventtrigger.replace(
                  "#trigger_name#",
                  this.selectedNode.data.raw_value
                )
              this.prepareDropModal(this.selectedNode, template)
            },
          },
        ],
        cm_direct_event_trigger_function: [
          {
            label: "Edit Event Trigger Function",
            icon: "fas fa-edit",
            onClick: () => {
              this.getEventTriggerFunctionDefinitionPostgresql(
                this.selectedNode
              );
            },
          },
          {
            label: "Alter Event Trigger Function",
            icon: "fas fa-edit",
            onClick: () => {
              tabSQLTemplate(
                "Alter Event Trigger Function",
                this.templates.alter_eventtriggerfunction.replace(
                  "#function_name#",
                  this.selectedNode.data.id
                )
              );
            },
          },
          COMMENT_MENUITEM,
          {
            label: "Drop Event Trigger Function",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              let template = this.templates.drop_eventtriggerfunction.replace(
                  "#function_name#",
                  this.selectedNode.data.id
                )
              this.prepareDropModal(this.selectedNode, template)
            },
          },
        ],
        cm_publications: [
          this.cmRefreshObject,
          {
            label: "Create Publication",
            icon: "fas fa-plus",
            onClick: () => {
              tabSQLTemplate(
                "Create Publication",
                this.templates.create_publication
              );
            },
          },
          {
            label: "Doc: Publications",
            icon: "fas fa-globe-americas",
            onClick: () => {
              this.openWebSite(
                `https://www.postgresql.org/docs/${this.serverVersion}/logical-replication-publication.html`
              );
            },
          },
        ],
        cm_publication: [
          {
            label: "Alter Publication",
            icon: "fas fa-edit",
            onClick: () => {
              tabSQLTemplate(
                "Alter Publication",
                this.templates.alter_publication.replace(
                  "#pub_name#",
                  this.selectedNode.data.raw_value
                )
              );
            },
          },
          COMMENT_MENUITEM,
          {
            label: "Drop Publication",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              let template = this.templates.drop_publication.replace(
                  "#pub_name#",
                  this.selectedNode.data.raw_value
                )
              this.prepareDropModal(this.selectedNode, template)
            },
          },
        ],
        cm_pubtables: [
          this.cmRefreshObject,
          {
            label: "Add Table",
            icon: "fas fa-edit",
            onClick: () => {
              tabSQLTemplate(
                "Add Table",
                this.templates.add_pubtable.replace(
                  "#pub_name#",
                  this.getParentNode(this.selectedNode).title
                )
              );
            },
          },
        ],
        cm_pubtable: [
          {
            label: "Drop Publication Table",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              let template = this.templates.drop_pubtable
                  .replace(
                    "#pub_name#",
                    this.getParentNodeDeep(this.selectedNode, 2).title
                  )
                  .replace("#table_name#", this.selectedNode.title)
              this.prepareDropModal(this.selectedNode, template)
            },
          },
        ],
        cm_subscriptions: [
          this.cmRefreshObject,
          {
            label: "Create Subscription",
            icon: "fas fa-plus",
            onClick: () => {
              tabSQLTemplate(
                "Create Subscription",
                this.templates.create_subscription
              );
            },
          },
          {
            label: "Doc: Subscriptions",
            icon: "fas fa-globe-americas",
            onClick: () => {
              this.openWebSite(
                `https://www.postgresql.org/docs/${this.serverVersion}/logical-replication-subscription.html`
              );
            },
          },
        ],
        cm_subscription: [
          {
            label: "Alter Subscription",
            icon: "fas fa-edit",
            onClick: () => {
              tabSQLTemplate(
                "Alter Subscription",
                this.templates.alter_subscription.replace(
                  "#sub_name#",
                  this.selectedNode.data.raw_value
                )
              );
            },
          },
          COMMENT_MENUITEM,
          {
            label: "Drop Subscription",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              let template = this.templates.drop_subscription.replace(
                  "#sub_name#",
                  this.selectedNode.data.raw_value
                )
              this.prepareDropModal(this.selectedNode, template)
            },
          },
        ],
        cm_tablespaces: [
          this.cmRefreshObject,
          {
            label: "Create Tablespace",
            icon: "fas fa-plus",
            onClick: () => {
              tabSQLTemplate(
                "Create Tablespace",
                this.templates.create_tablespace
              );
            },
          },
          {
            label: "Doc: Tablespaces",
            icon: "fas fa-globe-americas",
            onClick: () => {
              this.openWebSite(
                `https://www.postgresql.org/docs/${this.serverVersion}/manage-ag-tablespaces.html`
              );
            },
          },
        ],
        cm_tablespace: [
          {
            label: "Alter Tablespace",
            icon: "fas fa-edit",
            onClick: () => {
              tabSQLTemplate(
                "Alter Tablespace",
                this.templates.alter_tablespace.replace(
                  "#tablespace_name#",
                  this.selectedNode.title
                )
              );
            },
          },
          COMMENT_MENUITEM,
          {
            label: "Drop Tablespace",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              let template = this.templates.drop_tablespace.replace(
                  "#tablespace_name#",
                  this.selectedNode.title
                )
              this.prepareDropModal(this.selectedNode, template)
            },
          },
        ],
        cm_roles: [
          this.cmRefreshObject,
          {
            label: "Create Role",
            icon: "fas fa-plus",
            onClick: () => {
              createRoleModal(this.selectedNode, operationModes.CREATE, this.serverVersion);
            },
          },
          {
            label: "Doc: Roles",
            icon: "fas fa-globe-americas",
            onClick: () => {
              this.openWebSite(
                `https://www.postgresql.org/docs/${this.serverVersion}/user-manag.html`
              );
            },
          },
        ],
        cm_role: [
          {
            label: "Alter Role",
            icon: "fas fa-edit",
            onClick: () => {
              createRoleModal(this.selectedNode, operationModes.UPDATE, this.serverVersion);
            },
          },
          COMMENT_MENUITEM,
          {
            label: "Drop Role",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              let template = this.templates.drop_role.replace(
                  "#role_name#",
                  this.selectedNode.data.raw_value
                )
              this.prepareDropModal(this.selectedNode, template)
            },
          },
        ],
        cm_physical_replication_slots: [
          this.cmRefreshObject,
          {
            label: "Create Slot",
            icon: "fas fa-plus",
            onClick: () => {
              tabSQLTemplate(
                "Create Physical Replication Slot",
                this.templates.create_physicalreplicationslot
              );
            },
          },
          {
            label: "Doc: Replication Slots",
            icon: "fas fa-globe-americas",
            onClick: () => {
              this.openWebSite(
                `https://www.postgresql.org/docs/${this.serverVersion}/warm-standby.html#streaming-replication-slots`
              );
            },
          },
        ],
        cm_physical_replication_slot: [
          {
            label: "Drop Slot",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              let template = this.templates.drop_physicalreplicationslot.replace(
                  "#slot_name#",
                  this.selectedNode.title
                )
              this.prepareDropModal(this.selectedNode, template)
            },
          },
        ],
        cm_logical_replication_slots: [
          this.cmRefreshObject,
          {
            label: "Create Slot",
            icon: "fas fa-plus",
            onClick: () => {
              tabSQLTemplate(
                "Create Logical Replication Slot",
                this.templates.create_logicalreplicationslot
              );
            },
          },
          {
            label: "Doc: Replication Slots",
            icon: "fas fa-globe-americas",
            onClick: () => {
              this.openWebSite(
                `https://www.postgresql.org/docs/${this.serverVersion}/logicaldecoding-explanation.html#logicaldecoding-replication-slots`
              );
            },
          },
        ],
        cm_logical_replication_slot: [
          {
            label: "Drop Slot",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              let template = this.templates.drop_logicalreplicationslot.replace(
                  "#slot_name#",
                  this.selectedNode.title
                )
              this.prepareDropModal(this.selectedNode, template)
            },
          },
        ],
        cm_jobs: [
          this.cmRefreshObject,
          {
            label: "New Job",
            icon: "fas fa-edit",
            onClick: () => {
              createPgCronModal(this.selectedNode, operationModes.CREATE);
            },
          },
        ],
        cm_job: [
          {
            label: "View/Edit",
            icon: "fas fa-edit",
            onClick: () => {
              createPgCronModal(this.selectedNode, operationModes.UPDATE);
            },
          },
          {
            label: "Delete",
            icon: "fas fa-xmark",
            onClick: () => {
              messageModalStore.showModal(
                `Are you sure you want to delete job "${this.selectedNode.title}"?`,
                () => {
                  this.deleteJobPostgresql(this.selectedNode);
                },
                null
              );
            },
          },
        ],
      };
    },
  },
  mounted() {
    this.$hooks?.add_tree_context_menu_item?.forEach((hook) => {
      hook.call(this);
    })
    this.doubleClickNode(this.getRootNode());
    this.$nextTick(() => {
      const processNode = (node) => {
        if (["database_list", "schema_list"].includes(node.data.type)) {
          this.doubleClickNode(node);
        } else if (
          node.data.type === "database" &&
          node.title === this.selectedDatabase
        ) {
          this.doubleClickNode(node);
        } else if (
          node.data.type === "schema" &&
          node.title === this.currentSchema
        ) {
          this.doubleClickNode(node);
        } else if (node.data.type === "table_list") {
          this.doubleClickNode(node);
          return;
        }

        setTimeout(() => {
          const nodeElement = this.$refs.tree.getNode(node.path);
          nodeElement.children.forEach((childNode) => {
            processNode(childNode);
          });
        }, 200);
      };
      setTimeout(() => {
        this.getRootNode().children.forEach((node) => {
          processNode(node);
        });
      }, 200);
    });
    emitter.on(`schemaChanged_${this.workspaceId}`, ({ schema_name, database_name }) => {
      const tree = this.$refs.tree;
      let db_node = tree.getNextNode([0], (node) => {
        return (
          node.data.type === "database" && node.title === database_name
        );
      });
      let schema_node = tree.getNextNode(db_node.path, (node) => {
        return node.data.type === "schema" && node.data.schema === schema_name;
      });
      let tables_node = tree.getNextNode(schema_node.path, (node) => {
        return node.data.type === "table_list";
      });
      // this is to handle cases when tables_node is absent because schema_node is not expanded and therefore empty
      this.refreshTree(tables_node || schema_node, true);
    });

    emitter.on(`goToNode_${this.workspaceId}`, async ({ name, type, schema, database }) => {
      const rootNode = this.getRootNode();
       // Step 1: Find "Databases" node
      const databasesRoot = rootNode.children.find(child => child.data.type === "database_list");
      if (!databasesRoot) return;

      await this.expandAndRefreshIfNeeded(databasesRoot);
      const updatedDatabasesRoot = this.$refs.tree.getNode(databasesRoot.path)
      
      // Step 2: Find the specific database node
      const databaseNode = findNode(updatedDatabasesRoot, node => node.title === database && node.data.type === 'database');
      if (!databaseNode) return;

      await this.expandAndRefreshIfNeeded(databaseNode);
      const updatedDatabaseNode = this.$refs.tree.getNode(databaseNode.path)

      // If target is a database, stop here
      if (type === 'database') {
        this.goToNodeAndSelect(updatedDatabaseNode);
        return;
      }

      // Step 3: Find "schemas_node"
      const schemasNode = findChild(updatedDatabaseNode, 'schema_list');
      if (!schemasNode) return;
      await this.expandAndRefreshIfNeeded(schemasNode);

      const updatedSchemasNode = this.$refs.tree.getNode(schemasNode.path)

      const schemaNode = findNode(updatedSchemasNode, node => node.title === schema && node.data.type === 'schema');
      if (!schemaNode) return;
      await this.expandAndRefreshIfNeeded(schemaNode);

      const updatedSchemaNode = this.$refs.tree.getNode(schemaNode.path)

      // If target is a schema, stop here
      if (type === 'schema') {
        this.goToNodeAndSelect(updatedSchemaNode);
        return;
      }

      // Step 3: Find '_list' that we need
      const containerType = `${type}_list`;
      const containerNode = findChild(updatedSchemaNode, containerType);
      if (!containerNode) return;
      await this.expandAndRefreshIfNeeded(containerNode);

      const updatedContainerNode = this.$refs.tree.getNode(containerNode.path)

      // Step 4: Find the target node
      const targetNode = findNode(updatedContainerNode, node => node.title === name && node.data.type === type);
      if (!targetNode) return;

      this.goToNodeAndSelect(targetNode);
    });
  },
  unmounted() {
    emitter.all.delete(`schemaChanged_${this.workspaceId}`);
    emitter.all.delete(`goToNode_${this.workspaceId}`);
  },
  methods: {
    refreshTreePostgresqlConfirm(node) {
      if (node.data.type == "server") {
        return this.getTreeDetailsPostgresql(node)
      } else if (node.data.type == "database_list") {
        return this.getDatabasesPostgresql(node)
      } else if (node.data.type == "database") {
        return this.getDatabaseObjectsPostgresql(node);
      } else if (node.data.type == "schema_list") {
        return this.getSchemasPostgresql(node);
      } else if (node.data.type == "schema") {
        return this.getSchemasObjectsPostgresql(node);
      } else if (node.data.type == "table_list") {
        return this.getTablesPostgresql(node);
      } else if (node.data.type == "table") {
        return this.getColumnsPostgresql(node);
      } else if (node.data.type == "primary_key") {
        return this.getPKPostgresql(node);
      } else if (node.data.type == "pk") {
        return this.getPKColumnsPostgresql(node);
      } else if (node.data.type == "foreign_keys") {
        return this.getFKsPostgresql(node);
      } else if (node.data.type == "foreign_key") {
        return this.getFKsColumnsPostgresql(node);
      } else if (node.data.type == "uniques") {
        return this.getUniquesPostgresql(node);
      } else if (node.data.type == "unique") {
        return this.getUniquesColumnsPostgresql(node);
      } else if (node.data.type == "check_list") {
        return this.getChecksPostgresql(node);
      } else if (node.data.type == "exclude_list") {
        return this.getExcludesPostgresql(node);
      } else if (node.data.type == "indexes") {
        return this.getIndexesPostgresql(node);
      } else if (node.data.type == "index") {
        return this.getIndexesColumnsPostgresql(node);
      } else if (node.data.type == "rule_list") {
        return this.getRulesPostgresql(node);
      } else if (node.data.type == "trigger_list") {
        return this.getTriggersPostgresql(node);
      } else if (node.data.type == "inherited_list") {
        return this.getInheritedsPostgresql(node);
      } else if (node.data.type == "partition_list") {
        return this.getPartitionsPostgresql(node);
      } else if (node.data.type == "statistics_list") {
        return this.getStatisticsPostgresql(node);
      } else if (node.data.type == "statistic") {
        return this.getStatisticsColumnsPostgresql(node);
      } else if (node.data.type == "partitioned_table_list") {
        return this.getPartitionedParentsPostgresql(node);
      } else if (node.data.type == "partitioned_parent") {
        return this.getPartitionedChildrenPostgresql(node);
      } else if (node.data.type == "inherited_table_list") {
        return this.getInheritedsParentsPostgresql(node);
      } else if (node.data.type == "inherited_parent") {
        return this.getInheritedsChildrenPostgresql(node);
      } else if (node.data.type == "foreign_table_list") {
        return this.getForeignTablesPostgresql(node);
      } else if (node.data.type == "foreign_table") {
        return this.getForeignColumnsPostgresql(node);
      } else if (node.data.type == "sequence_list") {
        return this.getSequencesPostgresql(node);
      } else if (node.data.type == "view_list") {
        return this.getViewsPostgresql(node);
      } else if (node.data.type == "view") {
        return this.getViewsColumnsPostgresql(node);
      } else if (node.data.type == "mview_list") {
        return this.getMaterializedViewsPostgresql(node);
      } else if (node.data.type == "mview") {
        return this.getMaterializedViewsColumnsPostgresql(node);
      } else if (node.data.type == "function_list") {
        return this.getFunctionsPostgresql(node);
      } else if (node.data.type == "function") {
        return this.getFunctionFieldsPostgresql(node);
      } else if (node.data.type == "trigger_function_list") {
        return this.getTriggerFunctionsPostgresql(node);
      } else if (node.data.type == "event_trigger_function_list") {
        return this.getEventTriggerFunctionsPostgresql(node);
      } else if (node.data.type == "procedure_list") {
        return this.getProceduresPostgresql(node);
      } else if (node.data.type == "procedure") {
        return this.getProcedureFieldsPostgresql(node);
      } else if (node.data.type == "aggregate_list") {
        return this.getAggregatesPostgresql(node);
      } else if (node.data.type == "aggregate") {
        return this.getFunctionFieldsPostgresql(node);
      } else if (node.data.type == "type_list") {
        return this.getTypesPostgresql(node);
      } else if (node.data.type == "domain_list") {
        return this.getDomainsPostgresql(node);
      } else if (node.data.type == "extension_list") {
        return this.getExtensionsPostgresql(node);
      } else if (node.data.type == "foreign_data_wrapper_list") {
        return this.getForeignDataWrappersPostgresql(node);
      } else if (node.data.type == "foreign_server_list") {
        return this.getForeignServersPostgresql(node);
      } else if (node.data.type == "user_mapping_list") {
        return this.getUserMappingsPostgresql(node);
      } else if (node.data.type == "event_trigger_list") {
        return this.getEventTriggersPostgresql(node);
      } else if (node.data.type == "publication_list") {
        return this.getPublicationsPostgresql(node);
      } else if (node.data.type == "publication_table_list") {
        return this.getPublicationTablesPostgresql(node);
      } else if (node.data.type == "subscription_list") {
        return this.getSubscriptionsPostgresql(node);
      } else if (node.data.type == "subscription_table_list") {
        return this.getSubscriptionTablesPostgresql(node);
      } else if (node.data.type == "tablespace_list") {
        return this.getTablespacesPostgresql(node);
      } else if (node.data.type == "role_list") {
        return this.getRolesPostgresql(node);
      } else if (node.data.type == "physical_replication_slot_list") {
        return this.getPhysicalReplicationSlotsPostgresql(node);
      } else if (node.data.type == "logical_replication_slot_list") {
        return this.getLogicalReplicationSlotsPostgresql(node);
      } else if (node.data.type == "job_list") {
        return this.getPgCronJobsPostgresql(node);
      } else {
        return Promise.resolve('success');
      }
    },
    refreshTree(node, force = false) {
      return new Promise((resolve, reject) => {
        this.checkCurrentDatabase(
          node,
          true,
          () => {
            setTimeout(() => {
              if (!this.shouldUpdateNode(node, force)) {
                resolve();
                return;
              }

              if (node.children.length === 0) this.insertSpinnerNode(node);

              this.refreshTreePostgresqlConfirm(node)
                .then(() => {
                  this.$hooks?.add_tree_node_item?.forEach((hook) => {
                    hook(node);
                  });
                  resolve();
                })
                .catch((error) => {
                  this.nodeOpenError(error, node);
                  reject(error);
                });
            }, 100);
          },
          () => {
            this.toggleNode(node);
            resolve();
          }
        );
      });
    },
    checkCurrentDatabase(
      node,
      complete_check,
      callback_continue,
      callback_stop
    ) {
      const nodeDatabase = this.getNodeDatabase(node);

      if (
        nodeDatabase &&
        nodeDatabase !== this.selectedDatabase &&
        (complete_check || (!complete_check && node.data.type !== "database"))
      ) {
        let isAllowed = checkBeforeChangeDatabase(callback_stop);
        if (isAllowed) {
          this.api
            .post("/change_active_database/", {
              database: nodeDatabase,
            })
            .then((resp) => {
              dbMetadataStore.fetchDbMeta(this.databaseIndex, this.workspaceId, nodeDatabase)
              connectionsStore.updateConnection(this.databaseIndex, {"last_used_database" : nodeDatabase})
              const database_nodes = this.$refs.tree.getNode([0, 0]).children;

              database_nodes.forEach((el) => {
                if (nodeDatabase === el.title) {
                  this.selectedDatabase = nodeDatabase;
                  tabsStore.selectedPrimaryTab.metaData.selectedDatabase = nodeDatabase;
                }
              });
              if (callback_continue) callback_continue();
            })
            .catch((error) => {
              this.nodeOpenError(error, node);
            });
        }
      } else {
        if (callback_continue) callback_continue();
      }
    },
    getProperties(node) {
      this.checkCurrentDatabase(node, true, () => {
        this.getPropertiesConfirm(node);
      });
    },
    getPropertiesConfirm(node) {
      let schema = node.data.schema_raw ? node.data.schema_raw : null;
      let table = null;
      let object = node.data.raw_value ?? node.title;
      let handledTypes = [
        "role",
        "tablespace",
        "database",
        "extension",
        "schema",
        "event_trigger",
        "foreign_server",
        "foreign_data_wrapper",
        "publication",
        "subscription",
        "table",
        "sequence",
        "view",
        "mview",
        "foreign_table",
        "type",
        "domain",
        "table_field",
        "pk",
        "foreign_key",
        "unique",
        "check",
        "exclude",
        "rule",
        "trigger",
        "index",
        "function",
        "procedure",
        "trigger_function",
        "direct_trigger_function",
        "event_trigger_function",
        "aggregate",
        "direct_event_trigger_function",
        "user_mapping",
        "statistic",
      ];

      switch (node.data.type) {
        case "table_field":
        case "pk":
        case "foreign_key":
        case "unique":
        case "check":
        case "exclude":
        case "rule":
        case "trigger":
        case "index":
          table = this.getParentNodeDeep(node, 2).data.raw_value;
          break;
        case "function":
        case "procedure":
        case "trigger_function":
        case "direct_trigger_function":
        case "event_trigger_function":
        case "aggregate":
        case "direct_event_trigger_function":
          object = node.data.id;
          break;
        case "user_mapping":
          schema = node.data.foreign_server;
          break;
        case "table":
          table = node.data.raw_value;
          break;
      }

      if (handledTypes.includes(node.data.type)) {
        this.$emit("treeTabsUpdate", {data:
          {schema: schema,
          table: table,
          object: object,
          type: node.data.type,},
          view: "/get_properties_postgresql/"
        });
      } else {
        this.$emit("clearTabs");
      }
    },
    getObjectDescriptionPostgresql(node) {
      let position;
      let oid;
      if (node.data.type === "table_field") {
        oid = this.getParentNodeDeep(node, 2).data.oid;
        position = node.data.position;
      } else if (
        [
          "function",
          "trigger_function",
          "direct_trigger_function",
          "event_trigger_function",
          "direct_event_trigger_function",
          "procedure",
        ].includes(node.data.type)
      ) {
        oid = node.data.function_oid;
        position = 0;
      } else {
        oid = node.data.oid;
        position = 0;
      }

      this.api
        .post("/get_object_description_postgresql/", {
          oid: oid,
          object_type: node.data.type,
          position: position,
        })
        .then((resp) => {
          tabsStore.createQueryTab(`${node.title} Comment`, null, null, resp.data.data)
        })
        .catch((error) => {
          this.nodeOpenError(error, node);
        });
    },
    async getTreeDetailsPostgresql(node) {
      try {
        const response = await this.api.post("/get_tree_info_postgresql/")

        this.removeChildNodes(node);
        
        this.cm_server_extra = [{
            label: "Server Configuration",
            icon: "fas fa-cog",
            onClick: () => {
              tabsStore.createConfigurationTab()
            },
          },
          {
            label: "Backup Server",
            icon: "fa-solid fa-download ",
            onClick: () => {
              const nodeDatabase = this.getNodeDatabase(this.selectedNode);
              tabsStore.createUtilityTab(this.selectedNode, nodeDatabase, 'Backup', 'server');
            },
          },
          {
            label: "Restore Server",
            icon: "fa-solid fa-upload ",
            onClick: () => {
              const nodeDatabase = this.getNodeDatabase(this.selectedNode);
              tabsStore.createUtilityTab(this.selectedNode, nodeDatabase, 'Restore', 'server');
            },
          },
          {
            label: "Monitoring",
            icon: "fas fa-chart-line",
            children: [
              {
                label: "Dashboard",
                icon: "fas fa-chart-line",
                onClick: () => {
                  tabsStore.createMonitoringDashboardTab()
                },
              },
              {
                label: "Backends",
                icon: "fas fa-tasks",
                onClick: () => {
                  tabsStore.createMonitoringTab(
                    "Backends",
                    '/*pgmanage-dash*/ \
                    select pid as "Pid",\
                    datname as "Database",\
                    usename as "User",\
                    application_name as "Application",\
                    client_addr as "Client Addr",\
                    backend_start as "Backend Start",\
                    xact_start as "Transaction Start",\
                    state as "State",\
                    wait_event as "Wait Event",\
                    backend_type as "Backend Type",\
                    query as "Query" from pg_stat_activity'
                  );
                },
              },
            ],
          },
          {
            label: "Doc: PostgreSQL",
            icon: "fas fa-globe-americas",
            onClick: () => {
              this.openWebSite(
                `https://www.postgresql.org/docs/${this.serverVersion}/`
              );
            },
          },
          {
            label: "Doc: SQL Language",
            icon: "fas fa-globe-americas",
            onClick: () => {
              this.openWebSite(
                `https://www.postgresql.org/docs/${this.serverVersion}/sql.html`
              );
            },
          },
          {
            label: "Doc: SQL Commands",
            icon: "fas fa-globe-americas",
            onClick: () => {
              this.openWebSite(
                `https://www.postgresql.org/docs/${this.serverVersion}/sql-commands.html`
              );
            },
          }];
  
        this.templates = response.data.templates;
        this.serverVersion = response.data.major_version;
        this.featureFlags = response.data.feature_flags

        this.$refs.tree.updateNode(node.path, {
          title: response.data.version,
        });
        
        if (this.featureFlags.has_replication_slots) {
          this.insertNode(node, "Replication Slots", {
            icon: "fas node-all fa-sitemap node-repslot-list",
            type: "replication",
          });
    
          const replication_node = this.getFirstChildNode(node);
    
          this.insertNode(replication_node, "Logical Replication Slots", {
            icon: "fas node-all fa-sitemap node-repslot-list",
            type: "logical_replication_slot_list",
            contextMenu: "cm_logical_replication_slots",
          });
    
          this.insertNode(replication_node, "Physical Replication Slots", {
            icon: "fas node-all fa-sitemap node-repslot-list",
            type: "physical_replication_slot_list",
            contextMenu: "cm_physical_replication_slots",
          });
        }
  
        this.insertNode(node, "Roles", {
          icon: "fas node-all fa-users node-user-list",
          type: "role_list",
          contextMenu: "cm_roles",
        });
  
        this.insertNode(node, "Tablespaces", {
          icon: "fas node-all fa-folder-open node-tablespace-list",
          type: "tablespace_list",
          contextMenu: "cm_tablespaces",
        });
  
        this.insertNode(node, "Databases", {
          icon: "fas node-all fa-database node-database-list",
          type: "database_list",
          contextMenu: "cm_databases",
        });
      } catch(error) {
        throw error; 
      }
    },
    async getDatabasesPostgresql(node) {
      try {
        const response = await this.api.post("/get_databases_postgresql/")

        this.removeChildNodes(node);

        this.$refs.tree.updateNode(node.path, {
          title: `Databases (${response.data.length})`,
        });

        let childNodes = response.data.map((el) => {
          return {
            title: el.name,
            isLeaf: false,
            isExpanded: false,
            isDraggable: false,
            data: {
              icon: "fas node-all fa-database node-database",
              type: "database",
              contextMenu: "cm_database",
              oid: el.oid,
              raw_value: el.name_raw,
              pinned: el.pinned,
            },
          }
        });
        this.insertNodes(node, childNodes);

        const databasesNode = this.$refs.tree.getNode(node.path)
        this.sortPinnedNodes(databasesNode)
      } catch(error) {
        throw error;
      }
    },
    async getDatabaseObjectsPostgresql(node) {
      try {
        const response = await this.api.post("/get_database_objects_postgresql/")

        this.removeChildNodes(node);
  
        this.currentSchema = response.data.current_schema;
  
        if (response.data.has_pg_cron) {
          this.insertNode(node, "Jobs", {
            icon: "fas node-all fa-clock",
            type: "job_list",
            contextMenu: "cm_jobs",
          });
        }

        if (this.featureFlags.has_logical_replication) {
          this.insertNode(node, "Logical Replication", {
            icon: "fas node-all fa-sitemap node-logrep",
            type: "replication",
          });
          const logical_replication_node = this.getFirstChildNode(node);
    
          this.insertNode(logical_replication_node, "Subscriptions", {
            icon: "fas node-all fa-arrow-alt-circle-up node-subscription-list",
            type: "subscription_list",
            contextMenu: "cm_subscriptions",
          });
    
          this.insertNode(logical_replication_node, "Publications", {
            icon: "fas node-all fa-arrow-alt-circle-down node-publication-list",
            type: "publication_list",
            contextMenu: "cm_publications",
          });
        }
        
        if (this.featureFlags.has_event_triggers) {
          this.insertNode(node, "Event Triggers", {
            icon: "fas node-all fa-bolt node-eventtrigger",
            type: "event_trigger_list",
            contextMenu: "cm_event_triggers",
          });
        }
  
        if (this.featureFlags.has_fdw) {
          this.insertNode(node, "Foreign Data Wrappers", {
            icon: "fas node-all fa-cube node-fdw-list",
            type: "foreign_data_wrapper_list",
            contextMenu: "cm_foreign_data_wrappers",
          });
        }

        if (this.featureFlags.has_extensions) {
          this.insertNode(node, "Extensions", {
            icon: "fas node-all fa-cubes node-extension-list",
            type: "extension_list",
            contextMenu: "cm_extensions",
          });
        } 
  
        this.insertNode(node, "Schemas", {
          icon: "fas node-all fa-layer-group node-schema-list",
          type: "schema_list",
          contextMenu: "cm_schemas",
        });
      } catch(error) {
        throw error;
      }
    },
    async getSchemasPostgresql(node) {
      try {
        const response = await this.api.post("/get_schemas_postgresql/")

        this.removeChildNodes(node);
  
        this.$refs.tree.updateNode(node.path, {
          title: `Schemas (${response.data.length})`,
        });

        let childNodes = response.data.map((el) => {
          return {
            title: el.name,
            isLeaf: false,
            isExpanded: false,
            isDraggable: false,
            data: {
              icon: "fas node-all fa-layer-group node-schema",
              type: "schema",
              contextMenu: "cm_schema",
              schema: el.name,
              schema_raw: el.name_raw,
              raw_value: el.name_raw,
              oid: el.oid,
            },
          }
        });

        this.insertNodes(node, childNodes);
      } catch(error) {
        throw error;
      }
    },
    async getSchemasObjectsPostgresql(node) {
      this.removeChildNodes(node);
      return new Promise((resolve, reject) => {
        try {
          
          this.insertNode(node, "Domains", {
            icon: "fas node-all fa-square node-domain-list",
            type: "domain_list",
            contextMenu: "cm_domains",
            schema: node.data.schema,
            schema_raw: node.data.schema_raw,
          });
    
          this.insertNode(node, "Types", {
            icon: "fas node-all fa-square node-type-list",
            type: "type_list",
            contextMenu: "cm_types",
            schema: node.data.schema,
            schema_raw: node.data.schema_raw,
          });
    
          this.insertNode(node, "Aggregates", {
            icon: "fas node-all fa-cog node-aggregate-list",
            type: "aggregate_list",
            contextMenu: "cm_aggregates",
            schema: node.data.schema,
            schema_raw: node.data.schema_raw,
          });
    
          this.insertNode(node, "Procedures", {
            icon: "fas node-all fa-cog node-procedure-list",
            type: "procedure_list",
            contextMenu: "cm_procedures",
            schema: node.data.schema,
            schema_raw: node.data.schema_raw,
          });
    
          this.insertNode(node, "Event Trigger Functions", {
            icon: "fas node-all fa-cog node-etfunction-list",
            type: "event_trigger_function_list",
            contextMenu: "cm_event_trigger_functions",
            schema: node.data.schema,
            schema_raw: node.data.schema_raw,
          });
    
          this.insertNode(node, "Trigger Functions", {
            icon: "fas node-all fa-cog node-tfunction-list",
            type: "trigger_function_list",
            contextMenu: "cm_trigger_functions",
            schema: node.data.schema,
            schema_raw: node.data.schema_raw,
          });
    
          this.insertNode(node, "Functions", {
            icon: "fas node-all fa-cog node-function-list",
            type: "function_list",
            contextMenu: "cm_functions",
            schema: node.data.schema,
            schema_raw: node.data.schema_raw,
          });
    
          this.insertNode(node, "Materialized Views", {
            icon: "fas node-all fa-eye node-mview-list",
            type: "mview_list",
            contextMenu: "cm_mviews",
            schema: node.data.schema,
            schema_raw: node.data.schema_raw,
          });
    
          this.insertNode(node, "Views", {
            icon: "fas node-all fa-eye node-view-list",
            type: "view_list",
            contextMenu: "cm_views",
            schema: node.data.schema,
            schema_raw: node.data.schema_raw,
          });
    
          this.insertNode(node, "Sequences", {
            icon: "fas node-all fa-sort-numeric-down node-sequence-list",
            type: "sequence_list",
            contextMenu: "cm_sequences",
            schema: node.data.schema,
            schema_raw: node.data.schema_raw,
          });
    
          this.insertNode(node, "Foreign Tables", {
            icon: "fas node-all fa-th node-ftable-list",
            type: "foreign_table_list",
            contextMenu: "cm_foreign_tables",
            schema: node.data.schema,
            schema_raw: node.data.schema_raw,
          });
    
          this.insertNode(node, "Inheritance Tables", {
            icon: "fas node-all fa-th node-itable-list",
            type: "inherited_table_list",
            contextMenu: "cm_inherited_tables",
            schema: node.data.schema,
            schema_raw: node.data.schema_raw,
          });
    
          this.insertNode(node, "Partitioned Tables", {
            icon: "fas node-all fa-th node-ptable-list",
            type: "partitioned_table_list",
            contextMenu: "cm_partitioned_tables",
            schema: node.data.schema,
            schema_raw: node.data.schema_raw,
          });
    
          this.insertNode(node, "Tables", {
            icon: "fas node-all fa-th node-table-list",
            type: "table_list",
            contextMenu: "cm_tables",
            schema: node.data.schema,
            schema_raw: node.data.schema_raw,
          });
          resolve("success")
        } catch (error) {
          reject(error)
        }
      })
    },
    async getTablesPostgresql(node) {
      try {
        const response = await this.api.post("/get_tables_postgresql/", {
          schema: node.data.schema_raw
        })
        this.removeChildNodes(node);
  
        this.$refs.tree.updateNode(node.path, {
          title: `Tables (${response.data.length})`,
        });

        let childNodes = response.data.map((el) => {
          return {
            title: el.name,
            isLeaf: false,
            isExpanded: false,
            isDraggable: false,
            data: {
              icon: "fas node-all fa-table node-table",
              type: "table",
              contextMenu: "cm_table",
              schema: node.data.schema,
              schema_raw: node.data.schema_raw,
              raw_value: el.name_raw,
              oid: el.oid,
            },
          }
        });

        this.insertNodes(node, childNodes);
      } catch(error) {
        throw error;
      }
    },
    async getColumnsPostgresql(node) {
      try {
        const response = await this.api.post("/get_columns_postgresql/", {
          table: node.data.raw_value,
          schema: node.data.schema_raw,
        })
        this.removeChildNodes(node);
        
        let columnsData = response.data.map((el) => {
          return {
            title: el.column_name,
            isLeaf: false,
            isExpanded: false,
            isDraggable: false,
            data: {
              icon: "fas node-all fa-columns node-column",
              type: "table_field",
              contextMenu: "cm_column",
              schema: node.data.schema,
              schema_raw: node.data.schema_raw,
              position: el.position,
              raw_value: el.name_raw,
            },
            children: [
              {
                title: `Type: ${el.data_type}`,
                isLeaf: true,
                isExpanded: false,
                isDraggable: false,
                data: {
                  icon: "fas node-all fa-ellipsis-h node-bullet",
                  schema: node.data.schema,
                  schema_raw: node.data.schema_raw,
                },
              },
              {
                title: `Nullable: ${el.nullable}`,
                isLeaf: true,
                isExpanded: false,
                isDraggable: false,
                data: {
                  icon: "fas node-all fa-ellipsis-h node-bullet",
                  schema: node.data.schema,
                  schema_raw: node.data.schema_raw,
                },
              },
            ],
          }
        });

        let tableEntities = [
          {
            title: `Columns (${response.data.length})`,
            isLeaf: false,
            isExpanded: false,
            isDraggable: false,
            data: {
              icon: "fas node-all fa-columns node-column",
              type: "column_list",
              contextMenu: "cm_columns",
              schema: node.data.schema,
              schema_raw: node.data.schema_raw,
            },
            children: columnsData,
          },
          {
            title: "Primary Key",
            isLeaf: false,
            isExpanded: false,
            isDraggable: false,
            data: {
              icon: "fas node-all fa-key node-pkey",
              type: "primary_key",
              contextMenu: "cm_pks",
              schema: node.data.schema,
              schema_raw: node.data.schema_raw,
            },
          },
          {
            title: "Foreign Keys",
            isLeaf: false,
            isExpanded: false,
            isDraggable: false,
            data: {
              icon: "fas node-all fa-key node-fkey",
              type: "foreign_keys",
              contextMenu: "cm_fks",
              schema: node.data.schema,
              schema_raw: node.data.schema_raw,
            },
          },
          {
            title: "Uniques",
            isLeaf: false,
            isExpanded: false,
            isDraggable: false,
            data: {
              icon: "fas node-all fa-key node-unique",
              type: "uniques",
              contextMenu: "cm_uniques",
              schema: node.data.schema,
              schema_raw: node.data.schema_raw,
            },
          },
          {
            title: "Checks",
            isLeaf: false,
            isExpanded: false,
            isDraggable: false,
            data: {
              icon: "fas node-all fa-check-square node-check",
              type: "check_list",
              contextMenu: "cm_checks",
              schema: node.data.schema,
              schema_raw: node.data.schema_raw,
            },
          },
          {
            title: "Excludes",
            isLeaf: false,
            isExpanded: false,
            isDraggable: false,
            data: {
              icon: "fas node-all fa-times-circle node-exclude",
              type: "exclude_list",
              contextMenu: "cm_excludes",
              schema: node.data.schema,
              schema_raw: node.data.schema_raw,
            },
          },
          {
            title: "Indexes",
            isLeaf: false,
            isExpanded: false,
            isDraggable: false,
            data: {
              icon: "fas node-all fa-thumbtack node-index",
              type: "indexes",
              contextMenu: "cm_indexes",
              schema: node.data.schema,
              schema_raw: node.data.schema_raw,
            },
          },
          {
            title: "Rules",
            isLeaf: false,
            isExpanded: false,
            isDraggable: false,
            data: {
              icon: "fas node-all fa-lightbulb node-rule",
              type: "rule_list",
              contextMenu: "cm_rules",
              schema: node.data.schema,
              schema_raw: node.data.schema_raw,
            },
          },
          {
            title: "Triggers",
            isLeaf: false,
            isExpanded: false,
            isDraggable: false,
            data: {
              icon: "fas node-all fa-bolt node-trigger",
              type: "trigger_list",
              contextMenu: "cm_triggers",
              schema: node.data.schema,
              schema_raw: node.data.schema_raw,
            },
          },
          {
            title: "Inherited Tables",
            isLeaf: false,
            isExpanded: false,
            isDraggable: false,
            data: {
              icon: "fas node-all fa-table node-inherited",
              type: "inherited_list",
              contextMenu: "cm_inheriteds",
              schema: node.data.schema,
              schema_raw: node.data.schema_raw,
            },
          },
          {
            title: "Partitions",
            isLeaf: false,
            isExpanded: false,
            isDraggable: false,
            data: {
              icon: "fas node-all fa-table node-partition",
              type: "partition_list",
              contextMenu: "cm_partitions",
              schema: node.data.schema,
              schema_raw: node.data.schema_raw,
            },
          },
          {
            title: "Statistics",
            isLeaf: false,
            isExpanded: false,
            isDraggable: false,
            data: {
              icon: "fas node-all fa-chart-bar node-statistics",
              type: "statistics_list",
              contextMenu: "cm_statistics",
              schema: node.data.schema,
              schema_raw: node.data.schema_raw,
            },
          },
        ];

        this.insertNodes(node, tableEntities);
      } catch(error) {
        throw error;
      }
    },
    async getPKPostgresql(node) {
      try {
        const response = await this.api.post("/get_pk_postgresql/", {
          table: this.getParentNode(node).data.raw_value,
          schema: node.data.schema_raw,
        })

        this.removeChildNodes(node);
  
        this.$refs.tree.updateNode(node.path, {
          title: `Primary Key (${response.data.length})`,
        });
  
        response.data.forEach((el) => {
          this.insertNode(node, el.constraint_name, {
            icon: "fas node-all fa-key node-pkey",
            type: "pk",
            contextMenu: "cm_pk",
            oid: el.oid,
            schema: node.data.schema,
            schema_raw: node.data.schema_raw,
            raw_value: el.name_raw,
          });
        });
      } catch(error) {
        throw error;
      }
    },
    async getPKColumnsPostgresql(node) {
      try {
        const response = await this.api.post("/get_pk_columns_postgresql/", {
          key: node.data.raw_value,
          table: this.getParentNodeDeep(node, 2).data.raw_value,
          schema: node.data.schema_raw,
        })

        this.removeChildNodes(node);
  
        response.data.forEach((el) => {
          this.insertNode(
            node,
            el,
            {
              icon: "fas node-all fa-columns node-column",
              schema: node.data.schema,
              schema_raw: node.data.schema_raw,
            },
            true
          );
        });
      } catch(error) {
        throw error;
      }
    },
    async getFKsPostgresql(node) {
      try {
        const response = await this.api.post("/get_fks_postgresql/", {
          table: this.getParentNode(node).data.raw_value,
          schema: node.data.schema_raw,
        })
        this.removeChildNodes(node);
  
        this.$refs.tree.updateNode(node.path, {
          title: `Foreign Keys (${response.data.length})`,
        });
        
        let childNodes = response.data.map((el) => {
          return {
            title: el.constraint_name,
            isLeaf: false,
            isExpanded: false,
            isDraggable: false,
            data: {
              icon: "fas node-all fa-key node-fkey",
              type: "foreign_key",
              contextMenu: "cm_fk",
              oid: el.oid,
              schema: node.data.schema,
              schema_raw: node.data.schema_raw,
              raw_value: el.name_raw,
            },
          }
        });

        this.insertNodes(node, childNodes);
      } catch(error) {
        throw error;
      }
    },
    async getFKsColumnsPostgresql(node) {
      try {
        const response = await this.api.post("/get_fks_columns_postgresql/", {
          fkey: node.data.raw_value,
          table: this.getParentNodeDeep(node, 2).data.raw_value,
          schema: node.data.schema_raw,
        })
        this.removeChildNodes(node);
  
        response.data.forEach((el) => {
          this.insertNode(
            node,
            `${el.column_name} <i class='fas node-all fa-arrow-right'></i> ${el.r_column_name}`,
            {
              icon: "fas node-all fa-columns node-column",
              raw_html: true,
              schema: node.data.schema,
              schema_raw: node.data.schema_raw,
            },
            true
          );
          this.insertNode(
            node,
            `Update Rule: ${el.update_rule}`,
            {
              icon: "fas node-all fa-ellipsis-h node-bullet",
              schema: node.data.schema,
              schema_raw: node.data.schema_raw,
            },
            true
          );
          this.insertNode(
            node,
            `Delete Rule: ${el.delete_rule}`,
            {
              icon: "fas node-all fa-ellipsis-h node-bullet",
              schema: node.data.schema,
              schema_raw: node.data.schema_raw,
            },
            true
          );
          this.insertNode(
            node,
            `Referenced Table: ${el.r_table_name}`,
            {
              icon: "fas node-all fa-table node-table",
              schema: node.data.schema,
              schema_raw: node.data.schema_raw,
            },
            true
          );
        });
      } catch(error) {
        throw error;
      }
    },
    async getUniquesPostgresql(node) {
      try {
        const response = await this.api.post("/get_uniques_postgresql/", {
          table: this.getParentNode(node).data.raw_value,
          schema: node.data.schema_raw,
        })
        this.removeChildNodes(node);
  
        this.$refs.tree.updateNode(node.path, {
          title: `Uniques (${response.data.length})`,
        });
  
        response.data.forEach((el) => {
          this.insertNode(node, el.constraint_name, {
            icon: "fas node-all fa-key node-unique",
            type: "unique",
            contextMenu: "cm_unique",
            oid: el.oid,
            schema: node.data.schema,
            schema_raw: node.data.schema_raw,
            raw_value: el.name_raw,
          });
        });
      } catch(error) {
        throw error;
      }
    },
    async getUniquesColumnsPostgresql(node) {
      try {
        const response = await this.api.post("/get_uniques_columns_postgresql/", {
          unique: node.data.raw_value,
          table: this.getParentNodeDeep(node, 2).data.raw_value,
          schema: node.data.schema_raw,
        })
        this.removeChildNodes(node);
  
        response.data.forEach((el) => {
          this.insertNode(
            node,
            el,
            {
              icon: "fas node-all fa-columns node-column",
              schema: node.data.schema,
              schema_raw: node.data.schema_raw,
            },
            true
          );
        });
      } catch(error) {
        throw error;
      }
    },
    async getChecksPostgresql(node) {
      try {
        const response = await this.api.post("/get_checks_postgresql/", {
          table: this.getParentNode(node).data.raw_value,
          schema: node.data.schema_raw,
        })
        
        this.removeChildNodes(node);
  
        this.$refs.tree.updateNode(node.path, {
          title: `Checks (${response.data.length})`,
        });
  
        response.data.forEach((el) => {
          this.insertNode(node, el.constraint_name, {
            icon: "fas node-all fa-check-square node-check",
            type: "check",
            contextMenu: "cm_check",
            oid: el.oid,
            schema: node.data.schema,
            schema_raw: node.data.schema_raw,
            raw_value: el.name_raw,
          });
  
          const check_node = this.getFirstChildNode(node);
  
          this.insertNode(
            check_node,
            el.constraint_source,
            {
              icon: "fas node-all fa-edit node-check-value",
              schema: node.data.schema,
              schema_raw: node.data.schema_raw,
            },
            true
          );
        });

      } catch(error) {
        throw error;
      }
    },
    async getExcludesPostgresql(node) {
      try {
        const response = await this.api.post("/get_excludes_postgresql/", {
          table: this.getParentNode(node).data.raw_value,
          schema: node.data.schema_raw,
        })
        
        this.removeChildNodes(node);
  
        this.$refs.tree.updateNode(node.path, {
          title: `Excludes (${response.data.length})`,
        });
  
        response.data.forEach((el) => {
          this.insertNode(node, el.constraint_name, {
            icon: "fas node-all fa-times-circle node-exclude",
            type: "exclude",
            contextMenu: "cm_exclude",
            schema: node.data.schema,
            schema_raw: node.data.schema_raw,
            oid: el.oid,
            raw_value: el.name_raw,
          });
  
          const exclude_node = this.getFirstChildNode(node);
  
          this.insertNode(
            exclude_node,
            `Operators: ${el.operations}`,
            {
              icon: "fas node-all fa-ellipsis-h node-bullet",
              schema: node.data.schema,
              schema_raw: node.data.schema_raw,
            },
            true
          );
  
          this.insertNode(
            exclude_node,
            `Attributes: ${el.attributes}`,
            {
              icon: "fas node-all fa-ellipsis-h node-bullet",
              schema: node.data.schema,
              schema_raw: node.data.schema_raw,
            },
            true
          );
        });
      } catch(error) {
        throw error;
      }
    },
    async getIndexesPostgresql(node) {
      try {
        const response = await this.api.post("/get_indexes_postgresql/", {
          table: this.getParentNode(node).data.raw_value,
          schema: node.data.schema_raw,
        })

        this.removeChildNodes(node);
  
        this.$refs.tree.updateNode(node.path, {
          title: `Indexes (${response.data.length})`,
        });
  
        response.data.forEach((el) => {
          this.insertNode(node, el.index_name, {
            icon: "fas node-all fa-thumbtack node-index",
            type: "index",
            contextMenu: "cm_index",
            schema: node.data.schema,
            schema_raw: node.data.schema_raw,
            oid: el.oid,
            unique: el.unique ? 'Unique' : "Non unique",
            raw_value: el.name_raw,
          });
        });
      } catch(error) {
        throw error;
      }
    },
    async getIndexesColumnsPostgresql(node) {
      try {
        const response = await this.api.post("/get_indexes_columns_postgresql/", {
          index: node.title,
          table: this.getParentNodeDeep(node, 2).data.raw_value,
          schema: node.data.schema_raw,
        })

        this.removeChildNodes(node);
  
        response.data.forEach((el) => {
          this.insertNode(
            node,
            el,
            {
              icon: "fas node-all fa-columns node-column",
              schema: node.data.schema,
              schema_raw: node.data.schema_raw,
            },
            true
          );
        });
      } catch(error) {
        throw error;
      }
    },
    async getRulesPostgresql(node) {
      try {
        const response = await this.api.post("/get_rules_postgresql/", {
          table: this.getParentNode(node).data.raw_value,
          schema: node.data.schema_raw,
        })

        this.removeChildNodes(node);
  
        this.$refs.tree.updateNode(node.path, {
          title: `Rules (${response.data.length})`,
        });
  
        response.data.forEach((el) => {
          this.insertNode(
            node,
            el.rule_name,
            {
              icon: "fas node-all fa-lightbulb node-rule",
              type: "rule",
              contextMenu: "cm_rule",
              schema: node.data.schema,
              schema_raw: node.data.schema_raw,
              oid: el.oid,
              raw_value: el.name_raw,
            },
            true
          );
        });
      } catch(error) {
        throw error;
      }
    },
    getRuleDefinitionPostgresql(node) {
      this.api
        .post("/get_rule_definition_postgresql/", {
          rule: node.data.raw_value,
          table: this.getParentNodeDeep(node, 2).data.raw_value,
          schema: node.data.schema_raw,
        })
        .then((resp) => {
          tabsStore.createQueryTab(this.selectedNode.data.raw_value, null, null, resp.data.data)
        })
        .catch((error) => {
          this.nodeOpenError(error, node);
        });
    },
    async getTriggersPostgresql(node) {
      try {
        const response = await this.api.post("/get_triggers_postgresql/", {
          table: this.getParentNode(node).data.raw_value,
          schema: node.data.schema_raw,
        })

        this.removeChildNodes(node);
  
        this.$refs.tree.updateNode(node.path, {
          title: `Triggers (${response.data.length})`,
        });
  
        response.data.forEach((el) => {
          this.insertNode(node, el.trigger_name, {
            icon: "fas node-all fa-bolt node-trigger",
            type: "trigger",
            contextMenu: "cm_trigger",
            schema: node.data.schema,
            schema_raw: node.data.schema_raw,
            oid: el.oid,
            raw_value: el.name_raw,
          });
  
          const trigger_node = this.getFirstChildNode(node);
  
          this.insertNode(
            trigger_node,
            el.trigger_function,
            {
              icon: "fas node-all fa-cog node-tfunction",
              type: "direct_trigger_function",
              contextMenu: "cm_direct_trigger_function",
              schema: node.data.schema,
              schema_raw: node.data.schema_raw,
              id: el.id,
              function_oid: el.function_oid,
            },
            true
          );
  
          this.insertNode(
            trigger_node,
            `Enabled: ${el.enabled}`,
            {
              icon: "fas node-all fa-ellipsis-h node-bullet",
              schema: node.data.schema,
              schema_raw: node.data.schema_raw,
            },
            true
          );
        });
      } catch(error) {
        throw error;
      }
    },
    async getInheritedsPostgresql(node) {
      try {
        const response = await this.api.post("/get_inheriteds_postgresql/", {
          table: this.getParentNode(node).data.raw_value,
          schema: node.data.schema_raw, 
        })
        
        this.removeChildNodes(node);
  
        this.$refs.tree.updateNode(node.path, {
          title: `Inherited Tables (${response.data.length})`,
        });
  
        response.data.forEach((el) => {
          this.insertNode(
            node,
            el,
            {
              icon: "fas node-all fa-table node-inherited",
              type: "inherit",
              contextMenu: "cm_inherited",
              schema: node.data.schema,
              schema_raw: node.data.schema_raw,
              raw_value: el.name_raw,
            },
            true
          );
        });
      } catch(error) {
        throw error;
      }
    },
    async getPartitionsPostgresql(node) {
      try {
        const response = await this.api.post("/get_partitions_postgresql/", {
          table: this.getParentNode(node).data.raw_value,
          schema: node.data.schema_raw,
        })
        
        this.removeChildNodes(node);
  
        this.$refs.tree.updateNode(node.path, {
          title: `Partitions (${response.data.length})`,
        });

        let childNodes = response.data.map((el) => {
          return {
            title: el,
            isLeaf: true,
            isExpanded: false,
            isDraggable: false,
            data: {
              icon: "fas node-all fa-table node-partition",
              type: "partition",
              contextMenu: "cm_partition",
              schema: node.data.schema,
              schema_raw: node.data.schema_raw,
            },
          }
        });
  
        this.insertNodes(node, childNodes);
      } catch(error) {
        throw error;
      }
    },
    async getStatisticsPostgresql(node) {
      try {
        const response = await this.api.post("/get_statistics_postgresql/", {
          table: this.getParentNode(node).data.raw_value,
          schema: node.data.schema_raw,
        })

        this.removeChildNodes(node);
  
        this.$refs.tree.updateNode(node.path, {
          title: `Statistics (${response.data.length})`,
        });
  
        response.data.forEach((el) => {
          this.insertNode(node, `${el.schema_name}.${el.statistic_name}`, {
            icon: "fas node-all fa-chart-bar node-statistic",
            type: "statistic",
            contextMenu: "cm_statistic",
            schema: el.schema_name,
            schema_raw: node.data.schema_raw,
            oid: el.oid,
            statistics: el.statistic_name,
            raw_value: el.name_raw,
          });
        });
      } catch(error) {
        throw error;
      }
    },
    async getStatisticsColumnsPostgresql(node) {
      try {
        const response = await this.api.post("/get_statistics_columns_postgresql/", {
          statistics: node.data.raw_value,
          schema: node.data.schema_raw,
        })

        this.removeChildNodes(node);
  
        response.data.forEach((el) => {
          this.insertNode(
            node,
            el.column_name,
            {
              icon: "fas node-all fa-columns node-column",
              schema: node.data.schema,
              schema_raw: node.data.schema_raw,
            },
            true
          );
        });
      } catch(error) {
        throw error;
      }
    },
    async getPartitionedParentsPostgresql(node) {
      try {
        const response = await this.api.post("/get_partitions_parents_postgresql/", {
          schema: node.data.schema_raw,
        })

        this.removeChildNodes(node);
  
        this.$refs.tree.updateNode(node.path, {
          title: `Partitioned Tables (${response.data.length})`,
        });
  
        let childNodes = response.data.map((el) => {
          return {
            title: el.name,
            isLeaf: false,
            isExpanded: false,
            isDraggable: false,
            data: {
              icon: "fas node-all fa-layer-group node-ptable",
              type: "partitioned_parent",
              contextMenu: "cm_partitioned_parent",
              schema: node.data.schema,
              schema_raw: node.data.schema_raw,
              raw_value: el.name_raw,
              name: el.name,
            },
          };
        });

        this.insertNodes(node, childNodes);
      } catch(error) {
        throw error;
      } 
    },
    async getPartitionedChildrenPostgresql(node) {
      try {
        const response = await this.api.post("/get_partitions_children_postgresql/", {
          schema: node.data.schema_raw,
          table: node.data.raw_value,
        })

        this.removeChildNodes(node);
        this.$refs.tree.updateNode(node.path, {
          title: `${node.data.name} (${response.data.length})`,
        });

        let childNodes = response.data.map((el) => {
          return {
            title: el.name,
            isLeaf: false,
            isExpanded: false,
            isDraggable: false,
            data: {
              icon: "fas node-all fa-table node-ptable",
              type: "table",
              contextMenu: "cm_table",
              schema: node.data.schema,
              schema_raw: node.data.schema_raw,
              oid: el.oid,
              raw_value: el.name_raw,
            },
          }
        })
  
        this.insertNodes(node, childNodes);
      } catch(error) {
        throw error;
      }
    },
    async getInheritedsParentsPostgresql(node) {
      try {
        const response = await this.api.post("/get_inheriteds_parents_postgresql/", {
          schema: node.data.schema_raw,
        })

        this.removeChildNodes(node);
  
        this.$refs.tree.updateNode(node.path, {
          title: `Inheritance Tables (${response.data.length})`,
        });
        
        let childNodes = response.data.map((el) => {
          return {
            title: el.name,
            isLeaf: false,
            isExpanded: false,
            isDraggable: false,
            data: {
              icon: "fas node-all fa-layer-group node-itable",
              type: "inherited_parent",
              contextMenu: "cm_inherited_parent",
              schema: node.data.schema,
              schema_raw: node.data.schema_raw,
              raw_value: el.name_raw,
              name: el.name,
            },
          }
        });

        this.insertNodes(node, childNodes);
      } catch(error) {
        throw error;
      }
    },
    async getInheritedsChildrenPostgresql(node) {
      try {
        const response = await this.api.post("/get_inheriteds_children_postgresql/", {
          schema: node.data.schema_raw,
          table: node.data.raw_value,
        })

        this.removeChildNodes(node);
  
        this.$refs.tree.updateNode(node.path, {
          title: `${node.data.name} (${response.data.length})`,
        });
  
        response.data.forEach((el) => {
          this.insertNode(node, el.name, {
            icon: "fas node-all fa-table node-itable",
            type: "table",
            contextMenu: "cm_table",
            schema: node.data.schema,
            schema_raw: node.data.schema_raw,
            oid: el.oid,
            raw_value: el.name_raw,
          });
        });
      } catch(error) {
        throw error;
      }
    },
    async getForeignTablesPostgresql(node) {
      try {
        const response = await this.api.post("/get_foreign_tables_postgresql/", {
          schema: node.data.schema_raw,
        })

        this.removeChildNodes(node);
  
        this.$refs.tree.updateNode(node.path, {
          title: `Foreign Tables (${response.data.length})`,
        });
        
        let childNodes = response.data.map((el) => {
          return {
            title: el.name,
            isLeaf: false,
            isExpanded: false,
            isDraggable: false,
            data: {
              icon: "fas node-all fa-table node-ftable",
              type: "foreign_table",
              contextMenu: "cm_foreign_table",
              schema: node.data.schema,
              schema_raw: node.data.schema_raw,
              oid: el.oid,
              raw_value: el.name_raw,
            },
          }
        });

        this.insertNodes(node, childNodes);
      } catch(error) {
        throw error;
      }
    },
    async getForeignColumnsPostgresql(node) {
      try {
        const response = await this.api.post("/get_foreign_columns_postgresql/", {
          table: node.title, // CHeck here
          schema: node.data.schema_raw,
        })

        this.removeChildNodes(node);
  
        this.insertNode(node, "Statistics", {
          icon: "fas node-all fa-chart-bar node-statistics",
          type: "statistics_list",
          contextMenu: "cm_statistics",
          schema: node.data.schema,
          schema_raw: node.data.schema_raw,
        });
  
        if (!!response.data.length) {
          this.insertNode(
            node,
            response.data[0].fdw,
            {
              icon: "fas node-all fa-cube node-fdw",
              schema: node.data.schema,
              schema_raw: node.data.schema_raw,
            },
            true
          );
          this.insertNode(
            node,
            response.data[0].server,
            {
              icon: "fas node-all fa-server node-server",
              schema: node.data.schema,
              schema_raw: node.data.schema_raw,
            },
            true
          );
  
          let options = response.data[0].table_options.split(",");
          options.forEach((el) => {
            this.insertNode(
              node,
              el,
              {
                icon: "fas node-all fa-ellipsis-h node-bullet",
                schema: node.data.schema,
                schema_raw: node.data.schema_raw,
              },
              true
            );
          });
        }
  
        this.insertNode(node, `Columns (${response.data.length})`, {
          icon: "fas node-all fa-columns node-column",
          type: "foreign_column_list",
          contextMenu: "cm_foreign_columns",
          schema: node.data.schema,
          schema_raw: node.data.schema_raw,
        });
  
        const foreign_columns_node = this.getFirstChildNode(node);
  
        response.data.reduceRight((_, el) => {
          this.insertNode(
            foreign_columns_node,
            el.column_name,
            {
              icon: "fas node-all fa-columns node-column",
              type: "foreign_table_field",
              contextMenu: "cm_foreign_column",
              schema: node.data.schema,
              schema_raw: node.data.schema_raw,
            },
            null
          );
          const foreign_table_field =
            this.getFirstChildNode(foreign_columns_node);
  
          if (!!el.options) {
            let options = el.options.split(",");
            options.forEach((option_el) => {
              this.insertNode(
                foreign_table_field,
                option_el,
                {
                  icon: "fas node-all fa-ellipsis-h node-bullet",
                  schema: node.data.schema,
                  schema_raw: node.data.schema_raw,
                },
                true
              );
            });
          }
  
          this.insertNode(
            foreign_table_field,
            `Nullable: ${el.nullable}`,
            {
              icon: "fas node-all fa-ellipsis-h node-bullet",
              schema: node.data.schema,
              schema_raw: node.data.schema_raw,
            },
            true
          );
          this.insertNode(
            foreign_table_field,
            `Type: ${el.data_type}`,
            {
              icon: "fas node-all fa-ellipsis-h node-bullet",
              schema: node.data.schema,
              schema_raw: node.data.schema_raw,
            },
            true
          );
        }, null);
      } catch(error) {
        throw error;
      }
    },
    async getSequencesPostgresql(node) {
      try {
        const response = await this.api.post("/get_sequences_postgresql/", {
          schema: node.data.schema_raw,
        })

        this.removeChildNodes(node);
        this.$refs.tree.updateNode(node.path, {
          title: `Sequences (${response.data.length})`,
        });

        let childNodes = response.data.map((el) => {
          return {
            title: el.sequence_name,
            isLeaf: true,
            isExpanded: false,
            isDraggable: false,
            data: {
              icon: "fas node-all fa-sort-numeric-down node-sequence",
              type: "sequence",
              contextMenu: "cm_sequence",
              schema: node.data.schema,
              schema_raw: node.data.schema_raw,
              oid: el.oid,
              raw_value: el.name_raw,
            },
          }
        });

        this.insertNodes(node, childNodes);
      } catch(error) {
        throw error;
      }
    },
    async getViewsPostgresql(node) {
      try {
        const response = await this.api.post("/get_views_postgresql/", {
          schema: node.data.schema_raw,
        })

        this.removeChildNodes(node);

        this.$refs.tree.updateNode(node.path, {
          title: `Views (${response.data.length})`,
        });

        let childNodes = response.data.map((el) => {
          return {
            title: el.name,
            isLeaf: false,
            isExpanded: false,
            isDraggable: false,
            data: {
              icon: "fas node-all fa-eye node-view",
              type: "view",
              contextMenu: "cm_view",
              schema: node.data.schema,
              schema_raw: node.data.schema_raw,
              oid: el.oid,
              raw_value: el.name_raw,
            },
          }
        });

        this.insertNodes(node, childNodes);
      } catch(error) {
        throw error;
      }
    },
    async getViewsColumnsPostgresql(node) {
      try {
        const response = await this.api.post("/get_views_columns_postgresql/", {
          table: node.data.raw_value,
          schema: node.data.schema_raw,
        })

        this.removeChildNodes(node);

        let columnsData = response.data.map((el) => {
          return {
            title: el.column_name,
            isLeaf: false,
            isExpanded: false,
            isDraggable: false,
            data: {
              icon: "fas node-all fa-columns node-column",
              type: "table_field",
              schema: node.data.schema,
              schema_raw: node.data.schema_raw,
              raw_value: el.name_raw,
            },
            children: [
              {
                title: `Type: ${el.data_type}`,
                isLeaf: true,
                isExpanded: false,
                isDraggable: false,
                data: {
                  icon: "fas node-all fa-ellipsis-h node-bullet",
                  schema: node.data.schema,
                  schema_raw: node.data.schema_raw,
                },
              },
            ],
          }
        });

        let viewEntities = [
          {
            title: `Columns (${response.data.length})`,
            isLeaf: false,
            isExpanded: false,
            isDraggable: false,
            data: {
              icon: "fas node-all fa-columns node-column",
              schema: node.data.schema,
              schema_raw: node.data.schema_raw,
            },
            children: columnsData,
          },
          {
            title: "Rules",
            isLeaf: false,
            isExpanded: false,
            isDraggable: false,
            data: {
              icon: "fas node-all fa-lightbulb node-rule",
              type: "rule_list",
              contextMenu: "cm_rules",
              schema: node.data.schema,
              schema_raw: node.data.schema_raw,
            },
          },
          {
            title: "Triggers",
            isLeaf: false,
            isExpanded: false,
            isDraggable: false,
            data: {
              icon: "fas node-all fa-bolt node-trigger",
              type: "trigger_list",
              contextMenu: "cm_view_triggers",
              schema: node.data.schema,
              schema_raw: node.data.schema_raw,
            },
          },
        ];
  
        this.insertNodes(node, viewEntities);
      } catch(error) {
        throw error;
      }
    },
    getViewDefinitionPostgresql(node) {
      this.api
        .post("/get_view_definition_postgresql/", {
          view: node.title,
          schema: node.data.schema_raw,
        })
        .then((resp) => {
          tabsStore.createQueryTab(this.selectedNode.title, null, null, resp.data.data)
        })
        .catch((error) => {
          this.nodeOpenError(error, node);
        });
    },
    async getMaterializedViewsPostgresql(node) {
      try {
        const response = await this.api.post("/get_mviews_postgresql/", {
          schema: node.data.schema_raw,
        })

        this.removeChildNodes(node);
  
        this.$refs.tree.updateNode(node.path, {
          title: `Materialized Views (${response.data.length})`,
        });
        
        let childNodes = response.data.map((el) => {
          return {
            title: el.name,
            isLeaf: false,
            isExpanded: false,
            isDraggable: false,
            data: {
              icon: "fas node-all fa-eye node-mview",
              type: "mview",
              contextMenu: "cm_mview",
              schema: node.data.schema,
              schema_raw: node.data.schema_raw,
              oid: el.oid,
              raw_value: el.name_raw,
            },
          }
        });

        this.insertNodes(node, childNodes);
      } catch(error) {
        throw error;
      }
    },
    async getMaterializedViewsColumnsPostgresql(node) {
      try {
        const response = await this.api.post("/get_mviews_columns_postgresql/", {
          table: node.data.raw_value,
          schema: node.data.schema_raw,
        })

        this.removeChildNodes(node);

        let columnsData = response.data.map((el) => {
          return {
            title: el.column_name,
            isLeaf: false,
            isExpanded: false,
            isDraggable: false,
            data: {
              icon: "fas node-all fa-columns node-column",
              type: "table_field",
              schema: node.data.schema,
              schema_raw: node.data.schema_raw,
              raw_value: el.name_raw,
            },
            children: [
              {
                title: `Type: ${el.data_type}`,
                isLeaf: true,
                isExpanded: false,
                isDraggable: false,
                data: {
                  icon: "fas node-all fa-ellipsis-h node-bullet",
                  schema: node.data.schema,
                  schema_raw: node.data.schema_raw,
                },
              },
            ],
          }
        });

        let viewEntities = [
          {
            title: `Columns (${response.data.length})`,
            isLeaf: false,
            isExpanded: false,
            isDraggable: false,
            data: {
              icon: "fas node-all fa-columns node-column",
              schema: node.data.schema,
              schema_raw: node.data.schema_raw,
            },
            children: columnsData,
          },
          {
            title: "Indexes",
            isLeaf: false,
            isExpanded: false,
            isDraggable: false,
            data: {
              icon: "fas node-all fa-thumbtack node-index",
              type: "indexes",
              contextMenu: "cm_indexes",
              schema: node.data.schema,
              schema_raw: node.data.schema_raw,
            },
          },
          {
            title: "Statistics",
            isLeaf: false,
            isExpanded: false,
            isDraggable: false,
            data: {
              icon: "fas node-all fa-chart-bar node-statistics",
              type: "statistics_list",
              contextMenu: "cm_statistics",
              schema: node.data.schema,
              schema_raw: node.data.schema_raw,
            },
          },
        ];
  
        this.insertNodes(node, viewEntities);
      } catch(error) {
        throw error;
      }
    },
    getMaterializedViewDefinitionPostgresql(node) {
      this.api
        .post("/get_mview_definition_postgresql/", {
          view: node.data.raw_value,
          schema: node.data.schema_raw,
        })
        .then((resp) => {
          tabsStore.createQueryTab(this.selectedNode.data.raw_value, null, null, resp.data.data)
        })
        .catch((error) => {
          this.nodeOpenError(error, node);
        });
    },
    async getFunctionsPostgresql(node) {
      try {
        const response = await this.api.post("/get_functions_postgresql/", {
          schema: node.data.schema_raw,
        })

        this.removeChildNodes(node);
  
        this.$refs.tree.updateNode(node.path, {
          title: `Functions (${response.data.length})`,
        });
  
        let childNodes = response.data.map((el) => {
          return {
            title: el.name,
            isLeaf: false,
            isExpanded: false,
            isDraggable: false,
            data: {
              icon: "fas node-all fa-cog node-function",
              type: "function",
              contextMenu: "cm_function",
              schema: node.data.schema,
              schema_raw: node.data.schema_raw,
              function_oid: el.function_oid,
              id: el.id,
              raw_value: el.name_raw,
            },
          };
        });
  
        this.insertNodes(node, childNodes);
      } catch(error) {
        throw error;
      }
    },
    async getFunctionFieldsPostgresql(node) {
      try {
        const response = await this.api.post("/get_function_fields_postgresql/", {
          function: node.data.id,
          schema: node.data.schema_raw,
        })

        this.removeChildNodes(node);
  
        response.data.reduceRight((_, el) => {
          if (el.type === "O") {
            this.insertNode(
              node,
              el.name,
              {
                icon: "fas node-all fa-arrow-right node-function-field",
                schema: node.data.schema,
                schema_raw: node.data.schema_raw,
              },
              true
            );
          } else if (el.type === "I") {
            this.insertNode(
              node,
              el.name,
              {
                icon: "fas node-all fa-arrow-left node-function-field",
                schema: node.data.schema,
                schema_raw: node.data.schema_raw,
              },
              true
            );
          } else {
            this.insertNode(
              node,
              el.name,
              {
                icon: "fas node-all fa-exchange-alt node-function-field",
                schema: node.data.schema,
                schema_raw: node.data.schema_raw,
              },
              true
            );
          }
        }, null);
      } catch(error) {
        throw error;
      }
    },
    getFunctionDefinitionPostgresql(node) {
      this.api
        .post("/get_function_definition_postgresql/", {
          function: node.data.id,
        })
        .then((resp) => {
          tabsStore.createQueryTab(this.selectedNode.title, null, null, resp.data.data)
        })
        .catch((error) => {
          this.nodeOpenError(error, node);
        });
    },
    async getTriggerFunctionsPostgresql(node) {
      try {
        const response = await this.api.post("/get_triggerfunctions_postgresql/", {
          schema: node.data.schema_raw,
        })

        this.removeChildNodes(node);
  
        this.$refs.tree.updateNode(node.path, {
          title: `Trigger Functions (${response.data.length})`,
        });
        
        let childNodes = response.data.map((el) => {
          return {
            title: el.name,
            isLeaf: true,
            isExpanded: false,
            isDraggable: false,
            data: {
              icon: "fas node-all fa-cog node-tfunction",
              type: "trigger_function",
              contextMenu: "cm_trigger_function",
              schema: node.data.schema,
              schema_raw: node.data.schema_raw,
              function_oid: el.function_oid,
              id: el.id,
            },
          }
        });

        this.insertNodes(node, childNodes);
      } catch(error) {
        throw error;
      }
    },
    getTriggerFunctionDefinitionPostgresql(node) {
      this.api
        .post("/get_triggerfunction_definition_postgresql/", {
          function: node.data.id,
        })
        .then((resp) => {
          tabsStore.createQueryTab(this.selectedNode.title, null, null, resp.data.data)
        })
        .catch((error) => {
          this.nodeOpenError(error, node);
        });
    },
    async getEventTriggerFunctionsPostgresql(node) {
      try {
        const response = await this.api.post("/get_eventtriggerfunctions_postgresql/", {
          schema: node.data.schema_raw,
        })

        this.removeChildNodes(node);
  
        this.$refs.tree.updateNode(node.path, {
          title: `Event Trigger Functions (${response.data.length})`,
        });

        let childNodes = response.data.map((el) => {
          return {
            title: el.name,
            isLeaf: true,
            isExpanded: false,
            isDraggable: false,
            data: {
              icon: "fas node-all fa-cog node-etfunction",
              type: "event_trigger_function",
              contextMenu: "cm_event_trigger_function",
              schema: node.data.schema,
              schema_raw: node.data.schema_raw,
              id: el.id,
              function_oid: el.function_oid,
            },
          }
        });
        
        this.insertNodes(node, childNodes);
      } catch (error) {
        throw error;
      }
    },
    getEventTriggerFunctionDefinitionPostgresql(node) {
      this.api
        .post("/get_eventtriggerfunction_definition_postgresql/", {
          function: node.data.id,
        })
        .then((resp) => {
          tabsStore.createQueryTab(this.selectedNode.title, null, null, resp.data.data)
        })
        .catch((error) => {
          this.nodeOpenError(error, node);
        });
    },
    async getProceduresPostgresql(node) {
      try {
        const response = await this.api.post("/get_procedures_postgresql/", {
          schema: node.data.schema_raw,
        })

        this.removeChildNodes(node);
  
        this.$refs.tree.updateNode(node.path, {
          title: `Procedures (${response.data.length})`,
        });
        
        let childNodes = response.data.map((el) => {
          return {
            title: el.name,
            isLeaf: false,
            isExpanded: false,
            isDraggable: false,
            data: {
              icon: "fas node-all fa-cog node-procedure",
              type: "procedure",
              contextMenu: "cm_procedure",
              schema: node.data.schema,
              schema_raw: node.data.schema_raw,
              id: el.id,
              function_oid: el.function_oid,
            },
          }
        });

        this.insertNodes(node, childNodes);
      } catch(error) {
        throw error;
      }
    },
    async getProcedureFieldsPostgresql(node) {
      try {
        const response = await this.api.post("/get_procedure_fields_postgresql/", {
          procedure: node.data.id,
          schema: node.data.schema_raw,
        })

        this.removeChildNodes(node);
  
        response.data.reduceRight((_, el) => {
          if (el.type === "O") {
            this.insertNode(
              node,
              el.name,
              {
                icon: "fas node-all fa-arrow-right node-function-field",
                schema: node.data.schema,
                schema_raw: node.data.schema_raw,
              },
              true
            );
          } else if (el.type === "I") {
            this.insertNode(
              node,
              el.name,
              {
                icon: "fas node-all fa-arrow-left node-function-field",
                schema: node.data.schema,
                schema_raw: node.data.schema_raw,
              },
              true
            );
          } else {
            this.insertNode(
              node,
              el.name,
              {
                icon: "fas node-all fa-exchange-alt node-function-field",
                schema: node.data.schema,
                schema_raw: node.data.schema_raw,
              },
              true
            );
          }
        }, null);
      } catch(error) {
        throw error;
      }
    },
    getProcedureDefinitionPostgresql(node) {
      this.api
        .post("/get_procedure_definition_postgresql/", {
          procedure: node.data.id,
        })
        .then((resp) => {
          tabsStore.createQueryTab(this.selectedNode.title, null, null, resp.data.data)
        })
        .catch((error) => {
          this.nodeOpenError(error, node);
        });
    },
    async getAggregatesPostgresql(node) {
      try {
        const response = await this.api.post("/get_aggregates_postgresql/", {
          schema: node.data.schema_raw,
        })

        this.removeChildNodes(node);
  
        this.$refs.tree.updateNode(node.path, {
          title: `Aggregates (${response.data.length})`,
        });
        
        let childNodes = response.data.map((el) => {
          return {
            title: el.name,
            isLeaf: false,
            isExpanded: false,
            isDraggable: false,
            data: {
              icon: "fas node-all fa-cog node-aggregate",
              type: "aggregate",
              contextMenu: "cm_aggregate",
              schema: node.data.schema,
              schema_raw: node.data.schema_raw,
              id: el.id,
              oid: el.oid,
            },
          }
        });

        this.insertNodes(node, childNodes);
      } catch(error) {
        throw error;
      }
    },
    async getTypesPostgresql(node) {
      try {
        const response = await this.api.post("/get_types_postgresql/", {
          schema: node.data.schema_raw,
        })

        this.removeChildNodes(node);
  
        this.$refs.tree.updateNode(node.path, {
          title: `Types (${response.data.length})`,
        });

        let childNodes = response.data.map((el) => {
          return {
            title: el.type_name,
            isLeaf: true,
            isExpanded: false,
            isDraggable: false,
            data: {
              icon: "fas node-all fa-square node-type",
              type: "type",
              contextMenu: "cm_type",
              schema: node.data.schema,
              schema_raw: node.data.schema_raw,
              oid: el.oid,
              raw_value: el.name_raw,
            },
          }
        });
  
        this.insertNodes(node, childNodes);
      } catch(error) {
        throw error;
      }
    },
    async getDomainsPostgresql(node) {
      try {
        const response = await this.api.post("/get_domains_postgresql/", {
          schema: node.data.schema_raw,
        })

        this.removeChildNodes(node);
  
        this.$refs.tree.updateNode(node.path, {
          title: `Domains (${response.data.length})`,
        });
        
        let childNodes = response.data.map((el) => {
          return {
            title: el.domain_name,
            isLeaf: true,
            isExpanded: false,
            isDraggable: false,
            data: {
              icon: "fas node-all fa-square node-domain",
              type: "domain",
              contextMenu: "cm_domain",
              schema: node.data.schema,
              schema_raw: node.data.schema_raw,
              oid: el.oid,
              raw_value: el.name_raw,
            },
          }
        });
        
        this.insertNodes(node, childNodes);
      } catch(error) {
        throw error;
      }
    },
    async getExtensionsPostgresql(node) {
      try {
        const response = await this.api.post("/get_extensions_postgresql/")

        this.removeChildNodes(node);
  
        this.$refs.tree.updateNode(node.path, {
          title: `Extensions (${response.data.length})`,
        });

        let childNodes = response.data.map((el) => {
          return {
            title: el.name,
            isLeaf: true,
            isExpanded: false,
            isDraggable: false,
            data: {
              icon: "fas node-all fa-cubes node-extension",
              type: "extension",
              contextMenu: "cm_extension",
              oid: el.oid,
              raw_value: el.name_raw,
            },
          }
        });

        this.insertNodes(node, childNodes);
      } catch(error) {
        throw error;
      }
    },
    async getForeignDataWrappersPostgresql(node) {
      try {
        const response = await this.api.post("/get_foreign_data_wrappers_postgresql/")

        this.removeChildNodes(node);
  
        this.$refs.tree.updateNode(node.path, {
          title: `Foreign Data Wrappers (${response.data.length})`,
        });

        let childNodes = response.data.map((el) => {
          return {
            title: el.name,
            isLeaf: false,
            isExpanded: false,
            isDraggable: false,
            data: {
              icon: "fas node-all fa-cube node-fdw",
              type: "foreign_data_wrapper",
              contextMenu: "cm_foreign_data_wrapper",
              oid: el.oid,
            },
            children: [
              {
                title: "Foreign Servers",
                isLeaf: false,
                isExpanded: false,
                isDraggable: false,
                data: {
                  icon: "fas node-all fa-server node-server",
                  type: "foreign_server_list",
                  contextMenu: "cm_foreign_servers",
                },
              },
            ],
          }
        });
  
        this.insertNodes(node, childNodes);
      } catch(error) {
        throw error;
      }
    },
    async getForeignServersPostgresql(node) {
      try {
        const response = await this.api.post("/get_foreign_servers_postgresql/", {
          fdw: this.getParentNode(node).title,
        })

        this.removeChildNodes(node);
  
        this.$refs.tree.updateNode(node.path, {
          title: `Foreign Servers (${response.data.length})`,
        });
  
        response.data.forEach((el) => {
          this.insertNode(node, el.name, {
            icon: "fas node-all fa-server node-server",
            type: "foreign_server",
            contextMenu: "cm_foreign_server",
            raw_value: el.name_raw,
            oid: el.oid,
          });
          const foreign_server_node = this.getFirstChildNode(node);
  
          this.insertNode(foreign_server_node, "User Mappings", {
            icon: "fas node-all fa-user-friends node-user",
            type: "user_mapping_list",
            contextMenu: "cm_user_mappings",
          });

          let options = el.options?.split(",") || [];
          options.forEach((option_el) => {
            this.insertNode(
              foreign_server_node,
              option_el,
              {
                icon: "fas node-all fa-ellipsis-h node-bullet",
              },
              true
            );
          });
  
          this.insertNode(
            foreign_server_node,
            `Version: ${el.version}`,
            {
              icon: "fas node-all fa-ellipsis-h node-bullet",
            },
            true
          );
  
          this.insertNode(
            foreign_server_node,
            `Type: ${el.type}`,
            {
              icon: "fas node-all fa-ellipsis-h node-bullet",
            },
            true
          );
        });
      } catch(error) {
        throw error;
      }
    },
    async getUserMappingsPostgresql(node) {
      try {
        const response = await this.api.post("/get_user_mappings_postgresql/", {
          foreign_server: this.getParentNode(node).data.raw_value,
        })

        this.removeChildNodes(node);
  
        this.$refs.tree.updateNode(node.path, {
          title: `User Mappings (${response.data.length})`,
        });
  
        response.data.forEach((el) => {
          this.insertNode(node, el.name, {
            icon: "fas node-all fa-user-friends node-user",
            type: "user_mapping",
            contextMenu: "cm_user_mapping",
            foreign_server: el.foreign_server,
            raw_value: el.name_raw,
          });
  
          const user_mapping_node = this.getFirstChildNode(node);
  
          let options = el.options?.split(",") || [];
  
          options.forEach((option_el) => {
            this.insertNode(
              user_mapping_node,
              option_el,
              {
                icon: "fas node-all fa-ellipsis-h node-bullet",
              },
              true
            );
          });
        });
      } catch(error) {
        throw error;
      }
    },
    async getEventTriggersPostgresql(node) {
      try {
        const response = await this.api.post("/get_eventtriggers_postgresql/")

        this.removeChildNodes(node);
  
        this.$refs.tree.updateNode(node.path, {
          title: `Event Triggers (${response.data.length})`,
        });
  
        response.data.forEach((el) => {
          this.insertNode(node, el.name, {
            icon: "fas node-all fa-bolt node-eventtrigger",
            type: "event_trigger",
            contextMenu: "cm_event_trigger",
            oid: el.oid,
            raw_value: el.name_raw,
          });
          const trigger_node = this.getFirstChildNode(node);
  
          this.insertNode(
            trigger_node,
            el.function,
            {
              icon: "fas node-all fa-cog node-etfunction",
              type: "direct_event_trigger_function",
              contextMenu: "cm_direct_event_trigger_function",
              id: el.id,
              function_oid: el.function_oid,
            },
            true
          );
  
          this.insertNode(
            trigger_node,
            `Event: ${el.event}`,
            {
              icon: "fas node-all fa-ellipsis-h node-bullet",
            },
            true
          );
  
          this.insertNode(
            trigger_node,
            `Enabled: ${el.enabled}`,
            {
              icon: "fas node-all fa-ellipsis-h node-bullet",
            },
            true
          );
        });
      } catch(error) {
        throw error;
      }
    },
    async getPublicationsPostgresql(node) {
      try {
        const response = await this.api.post("/get_publications_postgresql/")

        this.removeChildNodes(node);
  
        this.$refs.tree.updateNode(node.path, {
          title: `Publications (${response.data.length})`,
        });
  
        response.data.forEach((el) => {
          this.insertNode(node, el.name, {
            icon: "fas node-all fa-arrow-alt-circle-down node-publication",
            type: "publication",
            contextMenu: "cm_publication",
            raw_value: el.name_raw,
            oid: el.oid,
          });
          const publication_node = this.getFirstChildNode(node);
  
          if (el.alltables === "False") {
            this.insertNode(publication_node, "Tables", {
              icon: "fas node-all fa-th node-table-list",
              type: "publication_table_list",
              contextMenu: "cm_pubtables",
            });
          }
  
          this.insertNode(
            publication_node,
            `Truncate: ${el.truncate}`,
            {
              icon: "fas node-all fa-ellipsis-h node-bullet",
            },
            true
          );
  
          this.insertNode(
            publication_node,
            `Delete: ${el.delete}`,
            {
              icon: "fas node-all fa-ellipsis-h node-bullet",
            },
            true
          );
  
          this.insertNode(
            publication_node,
            `Update: ${el.update}`,
            {
              icon: "fas node-all fa-ellipsis-h node-bullet",
            },
            true
          );
  
          this.insertNode(
            publication_node,
            `Insert: ${el.insert}`,
            {
              icon: "fas node-all fa-ellipsis-h node-bullet",
            },
            true
          );
  
          this.insertNode(
            publication_node,
            `All Tables: ${el.alltables}`,
            {
              icon: "fas node-all fa-ellipsis-h node-bullet",
            },
            true
          );
        });
      } catch(error) {
        throw error;
      }
    },
    async getPublicationTablesPostgresql(node) {
      try {
        const response = await this.api.post("/get_publication_tables_postgresql/", {
          pub: this.getParentNode(node).title,
        })

        this.removeChildNodes(node);
  
        this.$refs.tree.updateNode(node.path, {
          title: `Tables (${response.data.length})`,
        });
  
        response.data.forEach((el) => {
          this.insertNode(
            node,
            el.name,
            {
              icon: "fas node-all fa-table node-table",
              type: "pubtable",
              contextMenu: "cm_pubtable",
            },
            true
          );
        });
      } catch(error) {
        throw error;
      }
    },
    async getSubscriptionsPostgresql(node) {
      try {
        const response = await this.api.post("/get_subscriptions_postgresql/")

        this.removeChildNodes(node);
  
        this.$refs.tree.updateNode(node.path, {
          title: `Subscriptions (${response.data.length})`,
        });
  
        response.data.forEach((el) => {
          this.insertNode(node, el.name, {
            icon: "fas node-all fa-arrow-alt-circle-up node-subscription",
            type: "subscription",
            contextMenu: "cm_subscription",
            oid: el.oid,
            raw_value: el.name_raw,
          });
          const subscription_node = this.getFirstChildNode(node);
  
          this.insertNode(subscription_node, "Tables", {
            icon: "fas node-all fa-th node-table-list",
            type: "subscription_table_list",
          });
  
          this.insertNode(subscription_node, "Referenced Publications", {
            icon: "fas node-all fa-arrow-alt-circle-down node-publication",
            type: "subpubs",
          });
          const referenced_publications =
            this.getFirstChildNode(subscription_node);
  
          const publications = el.publications.split(",");
          publications.forEach((pub_el) => {
            this.insertNode(
              referenced_publications,
              pub_el,
              {
                icon: "fas node-all fa-arrow-alt-circle-down node-publication",
                type: "subpub",
              },
              true
            );
          });
  
          this.insertNode(
            subscription_node,
            `ConnInfo: ${el.conn_info}`,
            {
              icon: "fas node-all fa-ellipsis-h node-bullet",
            },
            true
          );
  
          this.insertNode(
            subscription_node,
            `Enabled: ${el.enabled}`,
            {
              icon: "fas node-all fa-ellipsis-h node-bullet",
            },
            true
          );
        });
      } catch(error) {
        throw error;
      }
    },
    async getSubscriptionTablesPostgresql(node) {
      try {
        const response = await this.api.post("/get_subscription_tables_postgresql/", {
          sub: this.getParentNode(node).title,
        })

        this.removeChildNodes(node);
  
        this.$refs.tree.updateNode(node.path, {
          title: `Tables (${response.data.length})`,
        });
  
        response.data.forEach((el) => {
          this.insertNode(
            node,
            el.name,
            {
              icon: "fas node-all fa-table node-table",
              type: "subtable",
            },
            true
          );
        });
      } catch(error) {
        throw error;
      }
    },
    async getTablespacesPostgresql(node) {
      try {
        const response = await this.api.post("/get_tablespaces_postgresql/")

        this.removeChildNodes(node);
  
        this.$refs.tree.updateNode(node.path, {
          title: `Tablespaces (${response.data.length})`,
        });
        
        let childNodes = response.data.map((el) => {
          return {
            title: el.name,
            isLeaf: true,
            isExpanded: false,
            isDraggable: false,
            data: {
              icon: "fas node-all fa-folder node-tablespace",
              type: "tablespace",
              contextMenu: "cm_tablespace",
              oid: el.oid,
            },
          }
        });

        this.insertNodes(node, childNodes);
      } catch(error) {
        throw error;
      }
    },
    async getRolesPostgresql(node) {
      try {
        const response = await this.api.post("/get_roles_postgresql/")

        this.removeChildNodes(node);
  
        this.$refs.tree.updateNode(node.path, {
          title: `Roles (${response.data.data.length})`,
        });
        
        let childNodes = response.data.data.map((el) => {
          return {
            title: el.name,
            isLeaf: true,
            isExpanded: false,
            isDraggable: false,
            data: {
              icon: "fas node-all fa-user node-user",
              type: "role",
              contextMenu: "cm_role",
              oid: el.oid,
              raw_value: el.name_raw,
            },
          }
        });

        this.insertNodes(node, childNodes);
      } catch(error) {
        throw error;
      }
    },
    async getPhysicalReplicationSlotsPostgresql(node) {
      try {
        const response = await this.api.post("/get_physicalreplicationslots_postgresql/")

        this.removeChildNodes(node);
  
        this.$refs.tree.updateNode(node.path, {
          title: `Physical Replication Slots (${response.data.length})`,
        });
  
        response.data.forEach((el) => {
          this.insertNode(
            node,
            el.name,
            {
              icon: "fas node-all fa-sitemap node-repslot",
              type: "physical_replication_slot",
              contextMenu: "cm_physical_replication_slot",
            },
            true
          );
        });
      } catch(error) {
        throw error;
      }
    },
    async getLogicalReplicationSlotsPostgresql(node) {
      try {
        const response = await this.api.post("/get_logicalreplicationslots_postgresql/")

        this.removeChildNodes(node);
  
        this.$refs.tree.updateNode(node.path, {
          title: `Logical Replication Slots (${response.data.length})`,
        });
  
        response.data.forEach((el) => {
          this.insertNode(
            node,
            el.name,
            {
              icon: "fas node-all fa-sitemap node-repslot",
              type: "logical_replication_slot",
              contextMenu: "cm_logical_replication_slot",
            },
            true
          );
        });
      } catch(error) {
        throw error;
      }
    },
    async getPgCronJobsPostgresql(node) {
      try {
        const response = await this.api.post("/get_pgcron_jobs/")

        this.removeChildNodes(node);
  
        let jobs = response.data.jobs;
  
        jobs.forEach((job) => {
          this.insertNode(
            node,
            job.name,
            {
              icon: "fas node-all fa-clock",
              contextMenu: "cm_job",
              job_meta: job,
            },
            true
          );
        });
      } catch(error) {
        throw error;
      }
    },
    deleteJobPostgresql(node) {
      this.api
        .post("/delete_pgcron_job/", {
          job_meta: node.data.job_meta,
        })
        .then((resp) => {
          this.removeNode(node);
        })
        .catch((error) => {
          this.nodeOpenError(error, node);
        });
    },
    openWebSite(site) {
      window.open(site, "_blank");
    },
  },
};
</script>
