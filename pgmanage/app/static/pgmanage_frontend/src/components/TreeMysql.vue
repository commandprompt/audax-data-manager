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
import TreeMixin from "../mixins/power_tree.js";
import PinDatabaseMixin from "../mixins/power_tree_pin_database_mixin.js";
import DropDbObjectMixin from "../mixins/power_tree_drop_db_object_mixin.js";
import { PowerTree } from "@onekiloparsec/vue-power-tree";
import { tabSQLTemplate } from "../tree_context_functions/tree_postgresql";
import {
  TemplateSelectMysql,
  TemplateInsertMysql,
  TemplateUpdateMysql,
} from "../tree_context_functions/tree_mysql";
import { emitter } from "../emitter";
import { tabsStore, connectionsStore, dbMetadataStore } from "../stores/stores_initializer";
import { checkBeforeChangeDatabase } from "../workspace";
import { operationModes } from "../constants";
import { findNode, findChild } from "../utils.js";

export default {
  name: "TreeMySQL",
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
          title: "MySQL",
          isExpanded: false,
          isDraggable: false,
          data: {
            icon: "node node-mysql",
            type: "server",
            contextMenu: "cm_server",
          },
        },
      ],
      templates: "",
      cm_server_extra: [],
    };
  },
  computed: {
    contextMenu() {
      return {
        cm_server: [this.cmRefreshObject, ...this.cm_server_extra],
        cm_databases: [
          this.cmRefreshObject,
          {
            label: "ER Diagram",
            icon: "fab fa-hubspot",
            onClick: () => {
              tabsStore.createERDTab();
            },
          },
          {
            label: "Create Database",
            icon: "fas fa-plus",
            onClick: () => {
              tabSQLTemplate("Create Database", this.templates.create_database);
            },
          },
        ],
        cm_database: [
          {
            label: "ER Diagram",
            icon: "fab fa-hubspot",
            onClick: () => {
              tabsStore.createERDTab(this.selectedNode.title);
            },
          },
          {
            label: "Alter Database",
            icon: "fas fa-edit",
            onClick: () => {
              tabSQLTemplate(
                "Alter Database",
                this.templates.alter_database.replace(
                  "#database_name#",
                  this.selectedNode.title
                )
              );
            },
          },
          {
            label: "Drop Database",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              let template = this.templates.drop_database.replace(
                  "#database_name#",
                  this.selectedNode.title
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
              const nodeDatabase = this.getNodeDatabase(this.selectedNode);
              tabsStore.createSchemaEditorTab(this.selectedNode.title, nodeDatabase, operationModes.CREATE);
            },
          },
        ],
        cm_table: [
          this.cmRefreshObject,
          {
            label: "Query Data",
            icon: "fas fa-search",
            onClick: () => {
              TemplateSelectMysql(
                this.getParentNodeDeep(this.selectedNode, 2).title,
                this.selectedNode.title
              );
            },
          },
          {
            label: "Edit Data",
            icon: "fas fa-table",
            onClick: () => {
              tabsStore.createDataEditorTab(this.selectedNode.title, this.getParentNodeDeep(this.selectedNode, 2).title)
            },
          },
          {
            label: "Alter Table",
            icon: "fas fa-edit",
            onClick: () => {
              const nodeDatabase = this.getNodeDatabase(this.selectedNode);
              tabsStore.createSchemaEditorTab(this.selectedNode.title, nodeDatabase, operationModes.UPDATE);
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
                  TemplateInsertMysql(
                    this.getParentNodeDeep(this.selectedNode, 2).title,
                    this.selectedNode.title
                  );
                },
              },
              {
                label: "Update Records",
                icon: "fas fa-edit",
                onClick: () => {
                  TemplateUpdateMysql(
                    this.getParentNodeDeep(this.selectedNode, 2).title,
                    this.selectedNode.title
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
                      `${this.getParentNodeDeep(this.selectedNode, 2).title}.${this.selectedNode.title
                      }`
                    )
                  );
                },
              },
            ],
          },
          {
            label: "Drop Table",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              let template = this.templates.drop_table.replace(
                  "#table_name#",
                  `${this.getParentNodeDeep(this.selectedNode, 2).title}.${this.selectedNode.title
                  }`
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
                "Create Field",
                this.templates.create_column.replace(
                  "#table_name#",
                  `${this.getParentNodeDeep(this.selectedNode, 3).title}.${this.getParentNode(this.selectedNode).title
                  }`
                )
              );
            },
          },
        ],
        cm_column: [
          {
            label: "Alter Column",
            icon: "fas fa-edit",
            onClick: () => {
              tabSQLTemplate(
                "Alter Column",
                this.templates.alter_column
                  .replace(
                    "#table_name#",
                    `${this.getParentNodeDeep(this.selectedNode, 4).title}.${this.getParentNodeDeep(this.selectedNode, 2).title
                    }`
                  )
                  .replace(/#column_name#/g, this.selectedNode.title)
              );
            },
          },
          {
            label: "Drop Column",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              let template = this.templates.drop_column
                  .replace(
                    "#table_name#",
                    `${this.getParentNodeDeep(this.selectedNode, 4).title}.${this.getParentNodeDeep(this.selectedNode, 2).title
                    }`
                  )
                  .replace(/#column_name#/g, this.selectedNode.title)
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
                  `${this.getParentNodeDeep(this.selectedNode, 3).title}.${this.getParentNode(this.selectedNode).title
                  }`
                )
              );
            },
          },
        ],
        cm_pk: [
          this.cmRefreshObject,
          {
            label: "Drop Primary Key",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              let template = this.templates.drop_primarykey
                  .replace(
                    "#table_name#",
                    `${this.getParentNodeDeep(this.selectedNode, 4).title}.${this.getParentNodeDeep(this.selectedNode, 2).title
                    }`
                  )
                  .replace("#constraint_name#", this.selectedNode.title)
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
                  `${this.getParentNodeDeep(this.selectedNode, 3).title}.${this.getParentNode(this.selectedNode).title
                  }`
                )
              );
            },
          },
        ],
        cm_fk: [
          this.cmRefreshObject,
          {
            label: "Drop Foreign Key",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              let template = this.templates.drop_foreignkey
                  .replace(
                    "#table_name#",
                    `${this.getParentNodeDeep(this.selectedNode, 4).title}.${this.getParentNodeDeep(this.selectedNode, 2).title
                    }`
                  )
                  .replace("#constraint_name#", this.selectedNode.title)
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
                  `${this.getParentNodeDeep(this.selectedNode, 3).title}.${this.getParentNode(this.selectedNode).title
                  }`
                )
              );
            },
          },
        ],
        cm_unique: [
          this.cmRefreshObject,
          {
            label: "Drop Unique",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              let template = this.templates.drop_unique
                  .replace(
                    "#table_name#",
                    `${this.getParentNodeDeep(this.selectedNode, 4).title}.${this.getParentNodeDeep(this.selectedNode, 2).title
                    }`
                  )
                  .replace("#constraint_name#", this.selectedNode.title)
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
                  `${this.getParentNodeDeep(this.selectedNode, 3).title}.${this.getParentNode(this.selectedNode).title
                  }`
                )
              );
            },
          },
        ],
        cm_index: [
          this.cmRefreshObject,
          {
            label: "Drop Index",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              let template = this.templates.drop_index.replace(
                  "#index_name#",
                  this.selectedNode.title
                )
                .replace("#table_name#", `${this.getParentNodeDeep(this.selectedNode, 4).title}.${this.getParentNodeDeep(this.selectedNode, 2).title}`)
              this.prepareDropModal(this.selectedNode, template)
            },
          },
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
                  this.getParentNode(this.selectedNode).title
                )
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
              // FIX this to use TemplateSelectMysql
              let table_name = `${this.getParentNodeDeep(this.selectedNode, 2).title
                }.${this.selectedNode.title}`;

              let command = `-- Querying Data\nselect t.*\nfrom ${table_name} t`
              tabsStore.createQueryTab(this.selectedNode.title, null, null, command)
                
              setTimeout(() => {
                emitter.emit(`${tabsStore.selectedPrimaryTab.metaData.selectedTab.id}_run_query`)
              }, 200)
            },
          },
          {
            label: "Edit View",
            icon: "fas fa-edit",
            onClick: () => {
              this.getViewDefinitionMysql(this.selectedNode);
            },
          },
          {
            label: "Drop View",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              let template = this.templates.drop_view.replace(
                  "#view_name#",
                  `${this.getParentNodeDeep(this.selectedNode, 2).title}.${this.selectedNode.title
                  }`
                )
              this.prepareDropModal(this.selectedNode, template)
            },
          },
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
                  this.getParentNode(this.selectedNode).title
                )
              );
            },
          },
        ],
        cm_function: [
          this.cmRefreshObject,
          {
            label: "Edit Function",
            icon: "fas fa-edit",
            onClick: () => {
              this.getFunctionDefinitionMysql(this.selectedNode);
            },
          },
          {
            label: "Drop Function",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              let template = this.templates.drop_function.replace(
                  "#function_name#",
                  `${this.getParentNodeDeep(this.selectedNode, 2).title}.${this.selectedNode.title
                  }`
                )
              this.prepareDropModal(this.selectedNode, template)
            },
          },
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
                  this.getParentNode(this.selectedNode).title
                )
              );
            },
          },
        ],
        cm_procedure: [
          this.cmRefreshObject,
          {
            label: "Edit Procedure",
            icon: "fas fa-edit",
            onClick: () => {
              this.getProcedureDefinitionMysql(this.selectedNode);
            },
          },
          {
            label: "Drop Procedure",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              let template = this.templates.drop_procedure.replace(
                  "#function_name#",
                  `${this.getParentNodeDeep(this.selectedNode, 2).title}.${this.selectedNode.title
                  }`
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
              tabSQLTemplate("Create Role", this.templates.create_role);
            },
          },
        ],
        cm_role: [
          {
            label: "Alter Role",
            icon: "fas fa-edit",
            onClick: () => {
              tabSQLTemplate(
                "Alter Role",
                this.templates.alter_role.replace(
                  "#role_name#",
                  this.selectedNode.title
                )
              );
            },
          },
          {
            label: "Drop Role",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              let template = this.templates.drop_role.replace(
                  "#role_name#",
                  this.selectedNode.title
                )
              this.prepareDropModal(this.selectedNode, template)
            },
          },
        ],
      };
    },
  },
  mounted() {
    this.doubleClickNode(this.getRootNode())
    this.$nextTick(() => {
      const processNode = (node) => {
        if (node.data.type === "database_list") {
          this.doubleClickNode(node);
        } else if (
          node.data.type === "database" &&
          node.title === this.selectedDatabase
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
    })

    emitter.on(`schemaChanged_${this.workspaceId}`, ({ schema_name, database_name }) => {
      const tree = this.$refs.tree;
      let db_node = tree.getNextNode([0], (node) => {
        return (
          node.data.type === "database" && node.title === database_name
        );
      });
      let tables_node = tree.getNextNode(db_node.path, (node) => {
        return node.data.type === "table_list";
      });
      this.refreshTree(tables_node, true);
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

      // Step 3: Find '_list' that we need
      const containerType = `${type}_list`;
      const containerNode = findChild(updatedDatabaseNode, containerType);
      if (!containerNode) return;
      await this.expandAndRefreshIfNeeded(containerNode);

      const updatedContainerNode = this.$refs.tree.getNode(containerNode.path)

      // Step 4: Find the target node
      const targetNode = findNode(updatedContainerNode, node => node.title === name && node.data.type === type);
      if (!targetNode) return;

      // Step 5: Select and scroll to it
      this.goToNodeAndSelect(targetNode);
    });
  },
  unmounted() {
    emitter.all.delete(`schemaChanged_${this.workspaceId}`);
    emitter.all.delete(`goToNode_${this.workspaceId}`);
  },
  methods: {
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
    refreshTree(node, force) {
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
              if (node.children.length == 0) this.insertSpinnerNode(node);

              this.refreshTreeConfirm(node)
                .then(() => {
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
    async refreshTreeConfirm(node) {
      if (node.data.type == "server") {
        return this.getTreeDetailsMysql(node);
      } else if (node.data.type == "database_list") {
        return this.getDatabasesMysql(node);
      } else if (node.data.type == "database") {
        return this.getDatabaseObjectsMysql(node);
      } else if (node.data.type == "table_list") {
        return this.getTablesMysql(node);
      } else if (node.data.type == "table") {
        this.getColumnsMysql(node);
      } else if (node.data.type == "primary_key") {
        this.getPKMysql(node);
      } else if (node.data.type == "pk") {
        this.getPKColumnsMysql(node);
      } else if (node.data.type == "foreign_keys") {
        this.getFKsMysql(node);
      } else if (node.data.type == "foreign_key") {
        this.getFKsColumnsMysql(node);
      } else if (node.data.type == "uniques") {
        this.getUniquesMysql(node);
      } else if (node.data.type == "unique") {
        this.getUniquesColumnsMysql(node);
      } else if (node.data.type == "indexes") {
        this.getIndexesMysql(node);
      } else if (node.data.type == "index") {
        this.getIndexesColumnsMysql(node);
      } else if (node.data.type == "view_list") {
        return this.getViewsMysql(node);
      } else if (node.data.type == "view") {
        this.getViewsColumnsMysql(node);
      } else if (node.data.type == "function_list") {
        this.getFunctionsMysql(node);
      } else if (node.data.type == "function") {
        this.getFunctionFieldsMysql(node);
      } else if (node.data.type == "procedure_list") {
        this.getProceduresMysql(node);
      } else if (node.data.type == "procedure") {
        this.getProcedureFieldsMysql(node);
      } else if (node.data.type == "role_list") {
        this.getRolesMysql(node);
      }
    },
    getProperties(node) {
      this.checkCurrentDatabase(node, true, () => {
        this.getPropertiesConfirm(node);
      });
    },
    getPropertiesConfirm(node) {
      const handledTypes = ["table", "view", "function", "procedure", "index"];
      if (handledTypes.includes(node.data.type)) {
        const table = node.data.table ?? null
        const schema = node.data.schema ?? this.getParentNodeDeep(node, 2).title
        this.$emit("treeTabsUpdate", {
          data: {
            schema: schema,
            table: table,
            object: node.title,
            type: node.data.type,
          },
          view: "/get_properties_mysql/"
        })
      } else {
        this.$emit("clearTabs");
      }
    },
    async getTreeDetailsMysql(node) {
      try {
        const response = await this.api.post("/get_tree_info_mysql/");

        this.removeChildNodes(node);

        this.$refs.tree.updateNode(node.path, {
          title: response.data.version,
        });

        this.templates = response.data;

        if (response.data.superuser) {
          this.insertNode(node, "Roles", {
            icon: "fas node-all fa-users node-user-list",
            type: "role_list",
            contextMenu: "cm_roles",
            database: false,
          });
        }
        this.insertNode(node, "Databases", {
          icon: "fas node-all fa-database node-database-list",
          type: "database_list",
          contextMenu: "cm_databases",
          database: false,
        });
        this.cm_server_extra = [
          {
            label: "Monitoring",
            icon: "fas fa-chart-line",
            children: [
              {
                label: "Process List",
                icon: "fas fa-chart-line",
                onClick: () => {
                  tabsStore.createMonitoringTab(
                    "Process List",
                    "/*pgmanage-dash*/ select * from information_schema.processlist"
                  );
                },
              },
            ],
          },
        ];
      } catch (error) {
        throw error;
      }
    },
    async getDatabasesMysql(node) {
      try {
        const response = await this.api.post("/get_databases_mysql/");

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
              pinned: el.pinned,
            },
          }
        });

        this.insertNodes(node, childNodes);

        const databasesNode = this.$refs.tree.getNode(node.path);
        this.sortPinnedNodes(databasesNode);
      } catch (error) {
        throw error;
      }
    },
    async getDatabaseObjectsMysql(node) {
      this.removeChildNodes(node);
      return new Promise((resolve, reject) => {
        try {
          this.insertNode(node, "Procedures", {
            icon: "fas node-all fa-cog node-procedure-list",
            type: "procedure_list",
            contextMenu: "cm_procedures",
          });

          this.insertNode(node, "Functions", {
            icon: "fas node-all fa-cog node-function-list",
            type: "function_list",
            contextMenu: "cm_functions",
          });

          this.insertNode(node, "Views", {
            icon: "fas node-all fa-eye node-view-list",
            type: "view_list",
            contextMenu: "cm_views",
          });

          this.insertNode(node, "Tables", {
            icon: "fas node-all fa-th node-table-list",
            type: "table_list",
            contextMenu: "cm_tables",
          });
          resolve("success");
        } catch (error) {
          reject(error);
        }
      });
    },
    async getTablesMysql(node) {
      try {
        const response = await this.api.post("/get_tables_mysql/", {
          schema: this.getParentNode(node).title,
        });
        this.removeChildNodes(node);

        this.$refs.tree.updateNode(node.path, {
          title: `Tables (${response.data.length})`,
        });

        let childNodes = response.data.map((el) => {
          return {
            title: el,
            isLeaf: false,
            isExpanded: false,
            isDraggable: false,
            data: {
              icon: "fas node-all fa-table node-table",
              type: "table",
              contextMenu: "cm_table",
            },
          }
        });

        this.insertNodes(node, childNodes);
      } catch (error) {
        throw error;
      }
    },
    getColumnsMysql(node) {
      this.api
        .post("/get_columns_mysql/", {
          table: node.title,
          schema: this.getParentNodeDeep(node, 2).title,
        })
        .then((resp) => {
          this.removeChildNodes(node);


          let columnsData = resp.data.map((el) => {
            return {
              title: el.column_name,
              isLeaf: false,
              isExpanded: false,
              isDraggable: false,
              data: {
                icon: "fas node-all fa-columns node-column",
                type: "table_field",
                contextMenu: "cm_column",
              },
              children: [
                {
                  title: `Type: ${el.data_type}`,
                  isLeaf: true,
                  isExpanded: false,
                  isDraggable: false,
                  data: {
                    icon: "fas node-all fa-ellipsis-h node-bullet",
                  },
                },
                {
                  title: `Nullable: ${el.nullable}`,
                  isLeaf: true,
                  isExpanded: false,
                  isDraggable: false,
                  data: {
                    icon: "fas node-all fa-ellipsis-h node-bullet",
                  },
                },
              ],
            }
          });

          let tableEntities = [
            {
              title: `Columns (${resp.data.length})`,
              isLeaf: false,
              isExpanded: false,
              isDraggable: false,
              data: {
                icon: "fas node-all fa-columns node-column",
                type: "column_list",
                contextMenu: "cm_columns",
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
              },
            },
          ];

          this.insertNodes(node, tableEntities);
        })
        .catch((error) => {
          this.nodeOpenError(error, node);
        });
    },
    getPKMysql(node) {
      this.api
        .post("/get_pk_mysql/", {
          table: this.getParentNode(node).title,
          schema: this.getParentNodeDeep(node, 3).title,
        })
        .then((resp) => {
          this.removeChildNodes(node);

          this.$refs.tree.updateNode(node.path, {
            title: `Primary Key (${resp.data.length})`,
          });

          resp.data.forEach((el) => {
            this.insertNode(node, el, {
              icon: "fas node-all fa-key node-pkey",
              type: "pk",
              contextMenu: "cm_pk",
            });
          });
        })
        .catch((error) => {
          this.nodeOpenError(error, node);
        });
    },
    getPKColumnsMysql(node) {
      this.api
        .post("/get_pk_columns_mysql/", {
          key: node.title,
          table: this.getParentNodeDeep(node, 2).title,
          schema: this.getParentNodeDeep(node, 4).title,
        })
        .then((resp) => {
          this.removeChildNodes(node);

          resp.data.forEach((el) => {
            this.insertNode(
              node,
              el,
              {
                icon: "fas node-all fa-columns node-column",
              },
              true
            );
          });
        })
        .catch((error) => {
          this.nodeOpenError(error, node);
        });
    },
    getFKsMysql(node) {
      this.api
        .post("/get_fks_mysql/", {
          table: this.getParentNode(node).title,
          schema: this.getParentNodeDeep(node, 3).title,
        })
        .then((resp) => {
          this.removeChildNodes(node);

          this.$refs.tree.updateNode(node.path, {
            title: `Foreign Keys (${resp.data.length})`,
          });

          let childNodes = resp.data.map((el) => {
            return {
              title: el.constraint_name,
              isLeaf: false,
              isExpanded: false,
              isDraggable: false,
              data: {
                icon: "fas node-all fa-key node-fkey",
                type: "foreign_key",
                contextMenu: "cm_fk",
              },
            }
          });

          this.insertNodes(node, childNodes);
        })
        .catch((error) => {
          this.nodeOpenError(error, node);
        });
    },
    getFKsColumnsMysql(node) {
      this.api
        .post("/get_fks_columns_mysql/", {
          fkey: node.title,
          table: this.getParentNodeDeep(node, 2).title,
          schema: this.getParentNodeDeep(node, 4).title,
        })
        .then((resp) => {
          this.removeChildNodes(node);

          this.insertNode(
            node,
            `${resp.data.column_name} <i class='fas node-all fa-arrow-right'></i> ${resp.data.r_column_name}`,
            {
              icon: "fas node-all fa-columns node-column",
              raw_html: true,
            },
            true
          );
          this.insertNode(
            node,
            `Update Rule: ${resp.data.update_rule}`,
            {
              icon: "fas node-all fa-ellipsis-h node-bullet",
            },
            true
          );
          this.insertNode(
            node,
            `Delete Rule: ${resp.data.delete_rule}`,
            {
              icon: "fas node-all fa-ellipsis-h node-bullet",
            },
            true
          );
          this.insertNode(
            node,
            `Referenced Table: ${resp.data.r_table_name}`,
            {
              icon: "fas node-all fa-table node-table",
            },
            true
          );
        })
        .catch((error) => {
          this.nodeOpenError(error, node);
        });
    },
    getUniquesMysql(node) {
      this.api
        .post("/get_uniques_mysql/", {
          table: this.getParentNode(node).title,
          schema: this.getParentNodeDeep(node, 3).title,
        })
        .then((resp) => {
          this.removeChildNodes(node);

          this.$refs.tree.updateNode(node.path, {
            title: `Uniques (${resp.data.length})`,
          });

          resp.data.forEach((el) => {
            this.insertNode(node, el, {
              icon: "fas node-all fa-key node-unique",
              type: "unique",
              contextMenu: "cm_unique",
            });
          });
        })
        .catch((error) => {
          this.nodeOpenError(error, node);
        });
    },
    getUniquesColumnsMysql(node) {
      this.api
        .post("/get_uniques_columns_mysql/", {
          unique: node.title,
          table: this.getParentNodeDeep(node, 2).title,
          schema: this.getParentNodeDeep(node, 4).title,
        })
        .then((resp) => {
          this.removeChildNodes(node);

          resp.data.forEach((el) => {
            this.insertNode(
              node,
              el,
              {
                icon: "fas node-all fa-columns node-column",
              },
              true
            );
          });
        })
        .catch((error) => {
          this.nodeOpenError(error, node);
        });
    },
    getIndexesMysql(node) {
      this.api
        .post("/get_indexes_mysql/", {
          table: this.getParentNode(node).title,
          schema: this.getParentNodeDeep(node, 3).title,
        })
        .then((resp) => {
          this.removeChildNodes(node);

          this.$refs.tree.updateNode(node.path, {
            title: `Indexes (${resp.data.length})`,
          });

          resp.data.forEach((el) => {
            this.insertNode(node, el.index_name, {
              icon: "fas node-all fa-thumbtack node-index",
              type: "index",
              contextMenu: "cm_index",
              unique: el.unique ? 'Unique' : "Non unique",
              table: this.getParentNode(node).title,
              schema: this.getParentNodeDeep(node, 3).title,
            });
          });
        })
        .catch((error) => {
          this.nodeOpenError(error, node);
        });
    },
    getIndexesColumnsMysql(node) {
      this.api
        .post("/get_indexes_columns_mysql/", {
          index: node.title,
          table: this.getParentNodeDeep(node, 2).title,
          schema: this.getParentNodeDeep(node, 4).title,
        })
        .then((resp) => {
          this.removeChildNodes(node);

          resp.data.forEach((el) => {
            this.insertNode(
              node,
              el,
              {
                icon: "fas node-all fa-columns node-column",
              },
              true
            );
          });
        })
        .catch((error) => {
          this.nodeOpenError(error, node);
        });
    },
    async getViewsMysql(node) {
      try {
        const response = await this.api.post("/get_views_mysql/", {
          schema: this.getParentNode(node).title,
        });

        this.removeChildNodes(node);

        this.$refs.tree.updateNode(node.path, {
          title: `Views (${response.data.length})`,
        });

        response.data.forEach((el) => {
          this.insertNode(node, el.name, {
            icon: "fas node-all fa-eye node-view",
            type: "view",
            contextMenu: "cm_view",
          });
        });
      } catch (error) {
        throw error;
      }
    },
    getViewsColumnsMysql(node) {
      this.api
        .post("/get_views_columns_mysql/", {
          table: node.title,
          schema: this.getParentNodeDeep(node, 2).title,
        })
        .then((resp) => {
          this.removeChildNodes(node);

          let columnsData = resp.data.map((el) => {
            return {
              title: el.column_name,
              isLeaf: false,
              isExpanded: false,
              isDraggable: false,
              data: {
                icon: "fas node-all fa-columns node-column",
                type: "table_field",
              },
              children: [
                {
                  title: `Type: ${el.data_type}`,
                  isLeaf: true,
                  isExpanded: false,
                  isDraggable: false,
                  data: {
                    icon: "fas node-all fa-ellipsis-h node-bullet",
                  },
                },
              ],
            }
          });

          let viewEntities = [
            {
              title: `Columns (${resp.data.length})`,
              isLeaf: false,
              isExpanded: false,
              isDraggable: false,
              data: {
                icon: "fas node-all fa-columns node-column",
              },
              children: columnsData,
            },
          ];

          this.insertNodes(node, viewEntities);
        })
        .catch((error) => {
          this.nodeOpenError(error, node);
        });
    },
    getViewDefinitionMysql(node) {
      this.api
        .post("/get_view_definition_mysql/", {
          view: node.title,
          schema: this.getParentNodeDeep(node, 2).title,
        })
        .then((resp) => {
          tabsStore.createQueryTab(this.selectedNode.title, null, null, resp.data.data)
        })
        .catch((error) => {
          this.nodeOpenError(error, node);
        });
    },
    getFunctionsMysql(node) {
      this.api
        .post("/get_functions_mysql/", {
          schema: this.getParentNode(node).title,
        })
        .then((resp) => {
          this.removeChildNodes(node);

          this.$refs.tree.updateNode(node.path, {
            title: `Functions (${resp.data.length})`,
          });

          resp.data.forEach((el) => {
            this.insertNode(node, el.name, {
              icon: "fas node-all fa-cog node-function",
              type: "function",
              id: el.id,
              contextMenu: "cm_function",
            });
          });
        })
        .catch((error) => {
          this.nodeOpenError(error, node);
        });
    },
    getFunctionFieldsMysql(node) {
      this.api
        .post("/get_function_fields_mysql/", {
          function: node.data.id,
          schema: this.getParentNodeDeep(node, 2).title,
        })
        .then((resp) => {
          this.removeChildNodes(node);

          resp.data.reduceRight((_, el) => {
            if (el.type === "O") {
              this.insertNode(
                node,
                el.name,
                {
                  icon: "fas node-all fa-arrow-right node-function-field",
                },
                true
              );
            } else if (el.type === "I") {
              this.insertNode(
                node,
                el.name,
                {
                  icon: "fas node-all fa-arrow-left node-function-field",
                },
                true
              );
            } else {
              this.insertNode(
                node,
                el.name,
                {
                  icon: "fas node-all fa-exchange-alt node-function-field",
                },
                true
              );
            }
          }, null);
        })
        .catch((error) => {
          this.nodeOpenError(error, node);
        });
    },
    getFunctionDefinitionMysql(node) {
      this.api
        .post("/get_function_definition_mysql/", {
          function: node.data.id,
        })
        .then((resp) => {
          tabsStore.createQueryTab(this.selectedNode.title, null, null, resp.data.data)
        })
        .catch((error) => {
          this.nodeOpenError(error, node);
        });
    },
    getProceduresMysql(node) {
      this.api
        .post("/get_procedures_mysql/", {
          schema: this.getParentNode(node).title,
        })
        .then((resp) => {
          this.removeChildNodes(node);

          this.$refs.tree.updateNode(node.path, {
            title: `Procedures (${resp.data.length})`,
          });

          resp.data.forEach((el) => {
            this.insertNode(node, el.name, {
              icon: "fas node-all fa-cog node-procedure",
              type: "procedure",
              contextMenu: "cm_procedure",
              id: el.id,
            });
          });
        })
        .catch((error) => {
          this.nodeOpenError(error, node);
        });
    },
    getProcedureFieldsMysql(node) {
      this.api
        .post("/get_procedure_fields_mysql/", {
          procedure: node.data.id,
          schema: this.getParentNodeDeep(node, 2).title,
        })
        .then((resp) => {
          this.removeChildNodes(node);

          resp.data.reduceRight((_, el) => {
            if (el.type === "O") {
              this.insertNode(
                node,
                el.name,
                {
                  icon: "fas node-all fa-arrow-right node-function-field",
                },
                true
              );
            } else if (el.type === "I") {
              this.insertNode(
                node,
                el.name,
                {
                  icon: "fas node-all fa-arrow-left node-function-field",
                },
                true
              );
            } else {
              this.insertNode(
                node,
                el.name,
                {
                  icon: "fas node-all fa-exchange-alt node-function-field",
                },
                true
              );
            }
          }, null);
        })
        .catch((error) => {
          this.nodeOpenError(error, node);
        });
    },
    getProcedureDefinitionMysql(node) {
      this.api
        .post("/get_procedure_definition_mysql/", {
          procedure: node.data.id,
        })
        .then((resp) => {
          tabsStore.createQueryTab(this.selectedNode.title, null, null, resp.data.data)
        })
        .catch((error) => {
          this.nodeOpenError(error, node);
        });
    },
    getRolesMysql(node) {
      this.api
        .post("/get_roles_mysql/")
        .then((resp) => {
          this.removeChildNodes(node);

          this.$refs.tree.updateNode(node.path, {
            title: `Roles (${resp.data.length})`,
          });

          resp.data.forEach((el) => {
            this.insertNode(
              node,
              el.name,
              {
                icon: "fas node-all fa-user node-user",
                type: "role",
                contextMenu: "cm_role",
              },
              true
            );
          });
        })
        .catch((error) => {
          this.nodeOpenError(error, node);
        });
    },
  },
};
</script>
