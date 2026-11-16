<template>
  <PowerTree
    ref="tree"
    v-model="nodes"
    @nodedblclick="doubleClickNode"
    @toggle="onToggle"
    @nodecontextmenu="onContextMenu"
    :allow-multiselect="false"
    @nodeclick="onClickHandler"
    @click="handleLeftSideClick"
    @dblclick="handleLeftSideDblClick"
    tabindex="0"
  >
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
          <span
            v-else-if="
              node.data.type === 'database' && node.title === selectedDatabase
            "
          >
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
import { operationModes } from "../constants";
import {
  connectionsStore,
  tabsStore,
  dbMetadataStore,
} from "../stores/stores_initializer";

import { TemplateSelectMssql } from "../tree_context_functions/tree_mssql";

import { findNode, findChild } from "../utils.js";

import { tabSQLTemplate } from "../tree_context_functions/tree_postgresql";

export default {
  name: "TreeMssql",
  components: {
    PowerTree: PowerTree,
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
          title: "Mssql",
          isExpanded: false,
          isDraggable: false,
          data: {
            icon: "node node-mssql",
            type: "server",
            contextMenu: "cm_server",
          },
        },
      ],
      serverVersion: null,
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
                `https://learn.microsoft.com/sql/relational-databases/databases/databases?view=sql-server-ver${this.serverVersion}`
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
              );
              this.prepareDropModal(this.selectedNode, template);
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
                `https://learn.microsoft.com/sql/relational-databases/security/authentication-access/create-a-database-schema?view=sql-server-ver${this.serverVersion}`
              );
            },
          },
        ],
        cm_schema: [
          {
            label: "ER Diagram",
            icon: "fab fa-hubspot",
            onClick: () => {
              tabsStore.createERDTab(this.selectedNode.data.schema);
            },
          },
          {
            label: "Drop Schema",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              let template = this.templates.drop_schema.replace(
                "#schema_name#",
                this.selectedNode.title
              );
              this.prepareDropModal(this.selectedNode, template);
            },
          },
        ],
        cm_tables: [
          this.cmRefreshObject,
          {
            label: "Create Table",
            icon: "fas fa-plus",
            onClick: () => {
              tabsStore.createSchemaEditorTab(
                this.selectedNode.title,
                this.selectedNode.data.schema,
                operationModes.CREATE,
              );
            },
          },
          {
            label: "Doc: Tables",
            icon: "fas fa-globe-americas",
            onClick: () => {
              this.openWebSite(
                `https://learn.microsoft.com/sql/relational-databases/tables/tables?view=sql-server-ver${this.serverVersion}`
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
              TemplateSelectMssql(
                this.selectedNode.data.schema,
                this.selectedNode.title,
                "t"
              );
            },
          },
          {
            label: "Edit Data",
            icon: "fas fa-table",
            onClick: () => {
              tabsStore.createDataEditorTab(
                this.selectedNode.title,
                this.selectedNode.data.schema
              );
            },
          },
          {
            label: "Alter Table",
            icon: "fas fa-edit",
            onClick: () => {
              tabsStore.createSchemaEditorTab(
                this.selectedNode.title,
                this.selectedNode.data.schema,
                operationModes.UPDATE,
              );
            },
          },
          {
            label: "Drop Table",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              let template = this.templates.drop_table
                .replace("#table_name#", this.selectedNode.title)
                .replace("#schema_name#", this.selectedNode.data.schema);
              this.prepareDropModal(this.selectedNode, template);
            },
          },
        ],
        cm_columns: [],
        cm_column: [],
        cm_pks: [this.cmRefreshObject],
        cm_pk: [this.cmRefreshObject],
        cm_fks: [this.cmRefreshObject],
        cm_fk: [this.cmRefreshObject],
        cm_uniques: [this.cmRefreshObject],
        cm_unique: [this.cmRefreshObject],
        cm_checks: [this.cmRefreshObject],
        cm_check: [],
        cm_indexes: [
          this.cmRefreshObject,
          {
            label: "Doc: Indexes",
            icon: "fas fa-globe-americas",
            onClick: () => {
              this.openWebSite(
                `https://learn.microsoft.com/sql/relational-databases/indexes/indexes?view=sql-server-ver${this.serverVersion}`
              );
            },
          },
        ],
        cm_index: [this.cmRefreshObject],
        cm_triggers: [
          this.cmRefreshObject,
          {
            label: "Create Trigger",
            icon: "fas fa-plus",
            onClick: () => {
              tabSQLTemplate("Create Trigger", this.templates.create_trigger);
            },
          },
          {
            label: "Doc: Triggers",
            icon: "fas fa-globe-americas",
            onClick: () => {
              this.openWebSite(
                `https://learn.microsoft.com/sql/relational-databases/triggers/dml-triggers?view=sql-server-ver${this.serverVersion}`
              );
            },
          },
        ],
        cm_trigger: [
          {
            label: "Drop Trigger",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              let template = this.templates.drop_trigger
                .replace("#table_name#", this.selectedNode.title)
                .replace("#schema_name#", this.selectedNode.data.schema);
              this.prepareDropModal(this.selectedNode, template);
            },
          },
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
              );
            },
          },
          {
            label: "Doc: Statistics",
            icon: "fas fa-globe-americas",
            onClick: () => {
              this.openWebSite(
                `https://learn.microsoft.com/sql/relational-databases/statistics/statistics?view=sql-server-ver${this.serverVersion}`
              );
            },
          },
        ],
        cm_statistic: [
          this.cmRefreshObject,
          {
            label: "Drop Statistics",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              let template = this.templates.drop_statistics
                .replace("#schema_name#", this.selectedNode.data.schema)
                .replace("#statistic_name#", this.selectedNode.title)
                .replace(
                  "#table_name#",
                  this.getParentNodeDeep(this.selectedNode, 2).title
                );
              this.prepareDropModal(this.selectedNode, template);
            },
          },
        ],
        cm_views: [
          this.cmRefreshObject,
          {
            label: "Create View",
            icon: "fas fa-plus",
            onClick: () => {
              tabSQLTemplate("Create View", this.templates.create_view);
            },
          },
          {
            label: "Doc: Views",
            icon: "fas fa-globe-americas",
            onClick: () => {
              this.openWebSite(
                `https://learn.microsoft.com/sql/relational-databases/views/views?view=sql-server-ver${this.serverVersion}`
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
              TemplateSelectMssql(
                this.selectedNode.data.schema,
                this.selectedNode.title,
                "v"
              );
            },
          },
          {
            label: "Alter View",
            icon: "fas fa-edit",
            onClick: () => {
              tabSQLTemplate(
                "Alter View",
                this.templates.alter_view
                  .replace("#view_name#", this.selectedNode.title)
                  .replace("#schema_name#", this.selectedNode.data.schema)
              );
            },
          },
          {
            label: "Drop View",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              let template = this.templates.drop_view
                .replace("#view_name#", this.selectedNode.title)
                .replace("#schema_name#", this.selectedNode.data.schema);
              this.prepareDropModal(this.selectedNode, template);
            },
          },
        ],
        cm_functions: [
          this.cmRefreshObject,
          {
            label: "Create Function",
            icon: "fas fa-plus",
            onClick: () => {
              tabSQLTemplate("Create Function", this.templates.create_function);
            },
          },
          {
            label: "Doc: Functions",
            icon: "fas fa-globe-americas",
            onClick: () => {
              this.openWebSite(
                `https://learn.microsoft.com/sql/t-sql/functions/functions?view=sql-server-ver${this.serverVersion}`
              );
            },
          },
        ],
        cm_function: [
          this.cmRefreshObject,
          {
            label: "Alter Function",
            icon: "fas fa-edit",
            onClick: () => {
              tabSQLTemplate(
                "Alter Function",
                this.templates.alter_function
                  .replace("#function_name#", this.selectedNode.title)
                  .replace("#schema_name#", this.selectedNode.data.schema)
              );
            },
          },
          {
            label: "Drop Function",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              let template = this.templates.drop_function
                .replace("#function_name#", this.selectedNode.title)
                .replace("#schema_name#", this.selectedNode.data.schema);
              this.prepareDropModal(this.selectedNode, template);
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
                this.templates.create_procedure
              );
            },
          },
          {
            label: "Doc: Procedures",
            icon: "fas fa-globe-americas",
            onClick: () => {
              this.openWebSite(
                `https://learn.microsoft.com/sql/relational-databases/stored-procedures/stored-procedures-database-engine?view=sql-server-ver${this.serverVersion}`
              );
            },
          },
        ],
        cm_procedure: [
          this.cmRefreshObject,
          {
            label: "Alter Procedure",
            icon: "fas fa-edit",
            onClick: () => {
              tabSQLTemplate(
                "Alter Procedure",
                this.templates.alter_procedure
                  .replace("#procedure_name#", this.selectedNode.title)
                  .replace("#schema_name#", this.selectedNode.data.schema)
              );
            },
          },
          {
            label: "Drop Procedure",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              let template = this.templates.drop_procedure
                .replace("#procedure_name#", this.selectedNode.title)
                .replace("#schema_name#", this.selectedNode.data.schema);
              this.prepareDropModal(this.selectedNode, template);
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
                `https://learn.microsoft.com/sql/t-sql/data-types/data-types-transact-sql?view=sql-server-ver${this.serverVersion}`
              );
            },
          },
        ],
        cm_type: [
          {
            label: "Drop Type",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              let template = this.templates.drop_type
                .replace("#type_name#", this.selectedNode.title)
                .replace("#schema_name#", this.selectedNode.data.schema);
              this.prepareDropModal(this.selectedNode, template);
            },
          },
        ],
        cm_users: [
          this.cmRefreshObject,
          {
            label: "Create User",
            icon: "fas fa-plus",
            onClick: () => {
              tabSQLTemplate("Create User", this.templates.create_user);
            },
          },
          {
            label: "Doc: Database Users",
            icon: "fas fa-globe-americas",
            onClick: () => {
              this.openWebSite(
                `https://learn.microsoft.com/sql/relational-databases/security/authentication-access/create-a-database-user?view=sql-server-ver${this.serverVersion}`
              );
            },
          },
        ],
        cm_user: [
          {
            label: "Alter User",
            icon: "fas fa-edit",
            onClick: () => {
              tabSQLTemplate(
                "Alter User",
                this.templates.alter_user.replace(
                  "#user_name#",
                  this.selectedNode.title
                )
              );
            },
          },
          {
            label: "Drop User",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              let template = this.templates.drop_user.replace(
                "#user_name#",
                this.selectedNode.title
              );
              this.prepareDropModal(this.selectedNode, template);
            },
          },
        ],
        cm_database_roles: [
          this.cmRefreshObject,
          {
            label: "Create Database Role",
            icon: "fas fa-plus",
            onClick: () => {
              tabSQLTemplate(
                "Create Database Role",
                this.templates.create_database_role
              );
            },
          },
          {
            label: "Doc: Database Roles",
            icon: "fas fa-globe-americas",
            onClick: () => {
              this.openWebSite(
                `https://learn.microsoft.com/sql/relational-databases/security/authentication-access/database-level-roles?view=sql-server-ver${this.serverVersion}`
              );
            },
          },
        ],
        cm_database_role: [
          {
            label: "Alter Database Role",
            icon: "fas fa-edit",
            onClick: () => {
              tabSQLTemplate(
                "Alter Database Role",
                this.templates.alter_database_role.replace(
                  "#role_name#",
                  this.selectedNode.title
                )
              );
            },
          },
          {
            label: "Drop Database Role",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              let template = this.templates.drop_database_role.replace(
                "#role_name#",
                this.selectedNode.title
              );
              this.prepareDropModal(this.selectedNode, template);
            },
          },
        ],
        cm_logins: [
          this.cmRefreshObject,
          {
            label: "Create Login",
            icon: "fas fa-plus",
            onClick: () => {
              tabSQLTemplate("Create Login", this.templates.create_login);
            },
          },
          {
            label: "Doc: Logins",
            icon: "fas fa-globe-americas",
            onClick: () => {
              this.openWebSite(
                `https://learn.microsoft.com/sql/relational-databases/security/authentication-access/principals-database-engine?view=sql-server-ver${this.serverVersion}`
              );
            },
          },
        ],
        cm_login: [
          {
            label: "Alter Login",
            icon: "fas fa-edit",
            onClick: () => {
              tabSQLTemplate(
                "Alter Login",
                this.templates.alter_login.replace(
                  "#login_name#",
                  this.selectedNode.title
                )
              );
            },
          },
          {
            label: "Drop Login",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              let template = this.templates.drop_login.replace(
                "#login_name#",
                this.selectedNode.title
              );
              this.prepareDropModal(this.selectedNode, template);
            },
          },
        ],
        cm_server_roles: [
          this.cmRefreshObject,
          {
            label: "Create Server Role",
            icon: "fas fa-plus",
            onClick: () => {
              tabSQLTemplate(
                "Create Server Role",
                this.templates.create_server_role
              );
            },
          },
          {
            label: "Doc: Server Roles",
            icon: "fas fa-globe-americas",
            onClick: () => {
              this.openWebSite(
                `https://learn.microsoft.com/sql/relational-databases/security/authentication-access/server-level-roles?view=sql-server-ver${this.serverVersion}`
              );
            },
          },
        ],
        cm_server_role: [
          {
            label: "Alter Server Role",
            icon: "fas fa-edit",
            onClick: () => {
              tabSQLTemplate(
                "Alter Server Role",
                this.templates.alter_server_role.replace(
                  "#role_name#",
                  this.selectedNode.title
                )
              );
            },
          },
          {
            label: "Drop Server Role",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              let template = this.templates.drop_server_role.replace(
                "#role_name#",
                this.selectedNode.title
              );
              this.prepareDropModal(this.selectedNode, template);
            },
          },
        ],
      };
    },
  },
  mounted() {
    this.$hooks?.add_tree_context_menu_item?.forEach((hook) => {
      hook.call(this);
    });
    this.doubleClickNode(this.getRootNode());

    emitter.on(
      `schemaChanged_${this.workspaceId}`,
      ({ schema_name, database_name }) => {
        const tree = this.$refs.tree;
        let db_node = tree.getNextNode([0], (node) => {
          return (
            node.data.type === "database" &&
            node.title === database_name
          );
        });
        let schema_node = tree.getNextNode(db_node.path, (node) => {
          return (
            node.data.type === "schema" && node.data.schema === schema_name
          );
        });
        let tables_node = tree.getNextNode(schema_node.path, (node) => {
          return node.data.type === "table_list";
        });
        // this is to handle cases when tables_node is absent because schema_node is not expanded and therefore empty
        this.refreshTree(tables_node || schema_node, true);
      }
    );

    emitter.on(
      `goToNode_${this.workspaceId}`,
      async ({ name, type, schema, database }) => {
        const rootNode = this.getRootNode();
        // Step 1: Find "Databases" node
        const databasesRoot = rootNode.children.find(
          (child) => child.data.type === "database_list"
        );
        if (!databasesRoot) return;

        await this.expandAndRefreshIfNeeded(databasesRoot);
        const updatedDatabasesRoot = this.$refs.tree.getNode(
          databasesRoot.path
        );

        // Step 2: Find the specific database node
        const databaseNode = findNode(
          updatedDatabasesRoot,
          (node) =>
            node.title === database && node.data.type === "database"
        );
        if (!databaseNode) return;

        await this.expandAndRefreshIfNeeded(databaseNode);
        const updatedDatabaseNode = this.$refs.tree.getNode(databaseNode.path);

        // If target is a database, stop here
        if (type === "database") {
          this.goToNodeAndSelect(updatedDatabaseNode);
          return;
        }

        // Step 3: Find "schemas_node"
        const schemasNode = findChild(updatedDatabaseNode, "schema_list");
        if (!schemasNode) return;
        await this.expandAndRefreshIfNeeded(schemasNode);

        const updatedSchemasNode = this.$refs.tree.getNode(schemasNode.path);

        const schemaNode = findNode(
          updatedSchemasNode,
          (node) => node.title === schema && node.data.type === "schema"
        );
        if (!schemaNode) return;
        await this.expandAndRefreshIfNeeded(schemaNode);

        const updatedSchemaNode = this.$refs.tree.getNode(schemaNode.path);

        // If target is a schema, stop here
        if (type === "schema") {
          this.goToNodeAndSelect(updatedSchemaNode);
          return;
        }

        // Step 3: Find '_list' that we need
        const containerType = `${type}_list`;
        const containerNode = findChild(updatedSchemaNode, containerType);
        if (!containerNode) return;
        await this.expandAndRefreshIfNeeded(containerNode);

        const updatedContainerNode = this.$refs.tree.getNode(
          containerNode.path
        );

        // Step 4: Find the target node
        const targetNode = findNode(
          updatedContainerNode,
          (node) => node.title === name && node.data.type === type
        );
        if (!targetNode) return;

        // Step 5: Select and scroll to it
        this.goToNodeAndSelect(targetNode);
      }
    );
  },
  unmounted() {
    emitter.all.delete(`schemaChanged_${this.workspaceId}`);
    emitter.all.delete(`goToNode_${this.workspaceId}`);
  },
  methods: {
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

              this.refreshTreeConfirm(node)
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
              dbMetadataStore.fetchDbMeta(
                this.databaseIndex,
                this.workspaceId,
                nodeDatabase
              );
              connectionsStore.updateConnection(this.databaseIndex, {
                last_used_database: nodeDatabase,
              });
              const database_nodes = this.$refs.tree.getNode([0, 0]).children;

              database_nodes.forEach((el) => {
                if (nodeDatabase === el.title) {
                  this.selectedDatabase = nodeDatabase;
                  tabsStore.selectedPrimaryTab.metaData.selectedDatabase =
                    nodeDatabase;
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
    refreshTreeConfirm(node) {
      if (node.data.type == "server") {
        return this.getTreeDetails(node);
      } else if (node.data.type == "database_list") {
        return this.getDatabases(node);
      } else if (node.data.type == "database") {
        return this.getDatabaseObjects(node);
      } else if (node.data.type == "schema_list") {
        return this.getSchemas(node);
      } else if (node.data.type == "schema") {
        return this.getSchemasObjects(node);
      } else if (node.data.type == "table_list") {
        return this.getTables(node);
      } else if (node.data.type == "table") {
        return this.getColumns(node);
      } else if (node.data.type == "primary_keys") {
        return this.getPKs(node);
      } else if (node.data.type == "primary_key") {
        return this.getPKsColumns(node);
      } else if (node.data.type == "foreign_keys") {
        return this.getFKs(node);
      } else if (node.data.type == "foreign_key") {
        return this.getFKsColumns(node);
      } else if (node.data.type == "uniques") {
        return this.getUniques(node);
      } else if (node.data.type == "unique") {
        return this.getUniquesColumns(node);
      } else if (node.data.type == "check_list") {
        return this.getChecks(node);
      } else if (node.data.type == "indexes") {
        return this.getIndexes(node);
      } else if (node.data.type == "index") {
        return this.getIndexesColumns(node);
      } else if (node.data.type == "trigger_list") {
        return this.getTriggers(node);
      } else if (node.data.type == "statistics_list") {
        return this.getStatistics(node);
      } else if (node.data.type == "view_list") {
        return this.getViews(node);
      } else if (node.data.type == "view") {
        return this.getViewsColumns(node);
      } else if (node.data.type == "function_list") {
        return this.getFunctions(node);
      } else if (node.data.type == "function") {
        return this.getFunctionFields(node);
      } else if (node.data.type == "procedure_list") {
        return this.getProcedures(node);
      } else if (node.data.type == "procedure") {
        return this.getProcedureFields(node);
      } else if (node.data.type == "type_list") {
        return this.getTypes(node);
      } else if (node.data.type == "users_list") {
        return this.getUsers(node);
      } else if (node.data.type == "database_role_list") {
        return this.getDatabaseRoles(node);
      } else if (node.data.type == "server_role_list") {
        return this.getServerRoles(node);
      } else if (node.data.type == "logins_list") {
        return this.getLogins(node);
      } else {
        return Promise.resolve("success");
      }
    },
    async getTreeDetails(node) {
      try {
        const response = await this.api.post("/get_tree_info_mssql/");
        this.removeChildNodes(node);

        this.cm_server_extra = [
          {
            label: "Doc: SQL Server",
            icon: "fas fa-globe-americas",
            onClick: () => {
              this.openWebSite(
                `https://learn.microsoft.com/sql/sql-server/?view=sql-server-ver${this.serverVersion}`
              );
            },
          },
          {
            label: "Doc: T-SQL Language",
            icon: "fas fa-globe-americas",
            onClick: () => {
              this.openWebSite(
                `https://learn.microsoft.com/sql/t-sql/language-reference/?view=sql-server-ver${this.serverVersion}`
              );
            },
          },
          {
            label: "Doc: T-SQL Statements",
            icon: "fas fa-globe-americas",
            onClick: () => {
              this.openWebSite(
                `https://learn.microsoft.com/sql/t-sql/statements/statements/?view=sql-server-ver${this.serverVersion}`
              );
            },
          },
        ];

        this.templates = response.data.templates;
        this.serverVersion = response.data.major_version;

        this.$refs.tree.updateNode(node.path, {
          title: response.data.version,
        });

        this.insertNode(node, "Server Roles", {
          icon: "fas node-all fa-users node-user-list",
          type: "server_role_list",
          contextMenu: "cm_server_roles",
        });

        this.insertNode(node, "Logins", {
          icon: "fas node-all fa-users node-user-list",
          type: "logins_list",
          contextMenu: "cm_logins",
        });
        this.insertNode(node, "Databases", {
          icon: "fas node-all fa-database node-database-list",
          type: "database_list",
          contextMenu: "cm_databases",
        });
      } catch (error) {
        throw error;
      }
    },
    async getDatabases(node) {
      try {
        const response = await this.api.post("/get_databases_mssql/");

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
              database_id: el.database_id,
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
    async getDatabaseObjects(node) {
      this.removeChildNodes(node);
      return new Promise((resolve, reject) => {
        try {
          this.insertNode(node, "Database Roles", {
            icon: "fas node-all fa-users node-user-list",
            type: "database_role_list",
            contextMenu: "cm_database_roles",
          });

          this.insertNode(node, "Users", {
            icon: "fas node-all fa-users node-user-list",
            type: "users_list",
            contextMenu: "cm_users",
          });
          this.insertNode(node, "Schemas", {
            icon: "fas node-all fa-layer-group node-schema-list",
            type: "schema_list",
            contextMenu: "cm_schemas",
          });
          resolve("success");
        } catch (error) {
          reject(error);
        }
      });
    },
    async getSchemas(node) {
      try {
        const response = await this.api.post("/get_schemas_mssql/");

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
            },
          }
        });

        this.insertNodes(node, childNodes);
      } catch (error) {
        throw error;
      }
    },
    async getSchemasObjects(node) {
      this.removeChildNodes(node);
      return new Promise((resolve, reject) => {
        try {
          this.insertNode(node, "Types", {
            icon: "fas node-all fa-square node-type-list",
            type: "type_list",
            contextMenu: "cm_types",
            schema: node.data.schema,
          });

          this.insertNode(node, "Procedures", {
            icon: "fas node-all fa-cog node-procedure-list",
            type: "procedure_list",
            contextMenu: "cm_procedures",
            schema: node.data.schema,
          });

          this.insertNode(node, "Functions", {
            icon: "fas node-all fa-cog node-function-list",
            type: "function_list",
            contextMenu: "cm_functions",
            schema: node.data.schema,
          });

          this.insertNode(node, "Views", {
            icon: "fas node-all fa-eye node-view-list",
            type: "view_list",
            contextMenu: "cm_views",
            schema: node.data.schema,
          });

          this.insertNode(node, "Tables", {
            icon: "fas node-all fa-th node-table-list",
            type: "table_list",
            contextMenu: "cm_tables",
            schema: node.data.schema,
          });
          resolve("success");
        } catch (error) {
          reject(error);
        }
      });
    },
    async getTables(node) {
      try {
        const response = await this.api.post("/get_tables_mssql/", {
          schema: node.data.schema,
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
              schema: node.data.schema,
            },
          }
        });

        this.insertNodes(node, childNodes);
      } catch (error) {
        throw error;
      }
    },
    async getColumns(node) {
      try {
        const response = await this.api.post("/get_columns_mssql/", {
          table: node.title,
          schema: node.data.schema,
        });
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
              position: el.position,
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
              type: "primary_keys",
              contextMenu: "cm_pks",
              schema: node.data.schema,
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
            },
          },
        ];

        this.insertNodes(node, tableEntities);
      } catch (error) {
        throw error;
      }
    },
    async getPKs(node) {
      try {
        const response = await this.api.post("/get_pk_mssql/", {
          table: this.getParentNode(node).title,
          schema: node.data.schema,
        });

        this.removeChildNodes(node);

        this.$refs.tree.updateNode(node.path, {
          title: `Primary Key (${response.data.length})`,
        });

        response.data.forEach((el) => {
          this.insertNode(node, el.constraint_name, {
            icon: "fas node-all fa-key node-pkey",
            type: "primary_key",
            contextMenu: "cm_pk",
            schema: node.data.schema,
          });
        });
      } catch (error) {
        throw error;
      }
    },
    async getPKsColumns(node) {
      try {
        const response = await this.api.post("/get_pk_columns_mssql/", {
          key: node.title,
          table: this.getParentNodeDeep(node, 2).title,
          schema: node.data.schema,
        });

        this.removeChildNodes(node);

        response.data.forEach((el) => {
          this.insertNode(
            node,
            el,
            {
              icon: "fas node-all fa-columns node-column",
              schema: node.data.schema,
            },
            true
          );
        });
      } catch (error) {
        throw error;
      }
    },
    async getFKs(node) {
      try {
        const response = await this.api.post("/get_fks_mssql/", {
          table: this.getParentNode(node).title,
          schema: node.data.schema,
        });
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
              schema: node.data.schema,
            },
          }
        });

        this.insertNodes(node, childNodes);
      } catch (error) {
        throw error;
      }
    },
    async getFKsColumns(node) {
      try {
        const response = await this.api.post("/get_fks_columns_mssql/", {
          fkey: node.title,
          table: this.getParentNodeDeep(node, 2).title,
          schema: node.data.schema,
        });
        this.removeChildNodes(node);

        response.data.forEach((el) => {
          this.insertNode(
            node,
            `${el.column_name} <i class='fas node-all fa-arrow-right'></i> ${el.r_column_name}`,
            {
              icon: "fas node-all fa-columns node-column",
              raw_html: true,
              schema: node.data.schema,
            },
            true
          );
          this.insertNode(
            node,
            `Update Rule: ${el.update_rule}`,
            {
              icon: "fas node-all fa-ellipsis-h node-bullet",
              schema: node.data.schema,
            },
            true
          );
          this.insertNode(
            node,
            `Delete Rule: ${el.delete_rule}`,
            {
              icon: "fas node-all fa-ellipsis-h node-bullet",
              schema: node.data.schema,
            },
            true
          );
          this.insertNode(
            node,
            `Referenced Table: ${el.r_table_name}`,
            {
              icon: "fas node-all fa-table node-table",
              schema: node.data.schema,
            },
            true
          );
        });
      } catch (error) {
        throw error;
      }
    },
    async getUniques(node) {
      try {
        const response = await this.api.post("/get_uniques_mssql/", {
          table: this.getParentNode(node).title,
          schema: node.data.schema,
        });
        this.removeChildNodes(node);

        this.$refs.tree.updateNode(node.path, {
          title: `Uniques (${response.data.length})`,
        });

        response.data.forEach((el) => {
          this.insertNode(node, el.constraint_name, {
            icon: "fas node-all fa-key node-unique",
            type: "unique",
            contextMenu: "cm_unique",
            schema: node.data.schema,
          });
        });
      } catch (error) {
        throw error;
      }
    },
    async getUniquesColumns(node) {
      try {
        const response = await this.api.post("/get_uniques_columns_mssql/", {
          unique: node.title,
          table: this.getParentNodeDeep(node, 2).title,
          schema: node.data.schema,
        });
        this.removeChildNodes(node);

        response.data.forEach((el) => {
          this.insertNode(
            node,
            el,
            {
              icon: "fas node-all fa-columns node-column",
              schema: node.data.schema,
            },
            true
          );
        });
      } catch (error) {
        throw error;
      }
    },
    async getChecks(node) {
      try {
        const response = await this.api.post("/get_checks_mssql/", {
          table: this.getParentNode(node).title,
          schema: node.data.schema,
        });

        this.removeChildNodes(node);

        this.$refs.tree.updateNode(node.path, {
          title: `Checks (${response.data.length})`,
        });

        response.data.forEach((el) => {
          this.insertNode(node, el.constraint_name, {
            icon: "fas node-all fa-check-square node-check",
            type: "check",
            contextMenu: "cm_check",
            schema: node.data.schema,
          });

          const check_node = this.getFirstChildNode(node);

          this.insertNode(
            check_node,
            el.check_clause,
            {
              icon: "fas node-all fa-edit node-check-value",
              schema: node.data.schema,
            },
            true
          );
        });
      } catch (error) {
        throw error;
      }
    },
    async getIndexes(node) {
      try {
        const response = await this.api.post("/get_indexes_mssql/", {
          table: this.getParentNode(node).title,
          schema: node.data.schema,
        });

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
            unique: el.unique ? "Unique" : "Non unique",
          });
        });
      } catch (error) {
        throw error;
      }
    },
    async getIndexesColumns(node) {
      try {
        const response = await this.api.post("/get_indexes_columns_mssql/", {
          index: node.title,
          table: this.getParentNodeDeep(node, 2).title,
          schema: node.data.schema,
        });

        this.removeChildNodes(node);

        response.data.forEach((el) => {
          this.insertNode(
            node,
            el,
            {
              icon: "fas node-all fa-columns node-column",
              schema: node.data.schema,
            },
            true
          );
        });
      } catch (error) {
        throw error;
      }
    },
    async getTriggers(node) {
      try {
        const response = await this.api.post("/get_triggers_mssql/", {
          table: this.getParentNode(node).title,
          schema: node.data.schema,
        });

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
          });

          const trigger_node = this.getFirstChildNode(node);

          this.insertNode(
            trigger_node,
            `Enabled: ${el.enabled}`,
            {
              icon: "fas node-all fa-ellipsis-h node-bullet",
              schema: node.data.schema,
            },
            true
          );
        });
      } catch (error) {
        throw error;
      }
    },
    async getStatistics(node) {
      try {
        const response = await this.api.post("/get_statistics_mssql/", {
          table: this.getParentNode(node).title,
          schema: node.data.schema,
        });

        this.removeChildNodes(node);

        this.$refs.tree.updateNode(node.path, {
          title: `Statistics (${response.data.length})`,
        });

        response.data.forEach((el) => {
          this.insertNode(
            node,
            el.statistic_name,
            {
              icon: "fas node-all fa-chart-bar node-statistic",
              type: "statistic",
              contextMenu: "cm_statistic",
              schema: el.schema_name,
              statistics: el.statistic_name,
            },
            true
          );
        });
      } catch (error) {
        throw error;
      }
    },
    async getViews(node) {
      try {
        const response = await this.api.post("/get_views_mssql/", {
          schema: node.data.schema,
        });

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
            },
          }
        });

        this.insertNodes(node, childNodes);
      } catch (error) {
        throw error;
      }
    },
    async getViewsColumns(node) {
      try {
        const response = await this.api.post("/get_views_columns_mssql/", {
          table: node.title,
          schema: node.data.schema,
        });

        this.removeChildNodes(node);

        let columnsData = response.data.map((el) => {
          return {
            title: el.column_name,
            isLeaf: false,
            isExpanded: false,
            isDraggable: false,
            data: {
              icon: "fas node-all fa-columns node-column",
              type: "view_field",
              schema: node.data.schema,
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
            },
            children: columnsData,
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
            },
          },
        ];

        this.insertNodes(node, viewEntities);
      } catch (error) {
        throw error;
      }
    },
    async getProcedures(node) {
      try {
        const response = await this.api.post("/get_procedures_mssql/", {
          schema: node.data.schema,
        });

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
              id: el.oid,
            },
          }
        });

        this.insertNodes(node, childNodes);
      } catch (error) {
        throw error;
      }
    },
    async getProcedureFields(node) {
      try {
        const response = await this.api.post("/get_procedure_fields_mssql/", {
          procedure: node.title,
          schema: node.data.schema,
        });

        this.removeChildNodes(node);

        response.data.reduceRight((_, el) => {
          if (el.type === "O") {
            this.insertNode(
              node,
              el.name,
              {
                icon: "fas node-all fa-arrow-right node-function-field",
                schema: node.data.schema,
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
              },
              true
            );
          }
        }, null);
      } catch (error) {
        throw error;
      }
    },
    async getFunctions(node) {
      try {
        const response = await this.api.post("/get_functions_mssql/", {
          schema: node.data.schema,
        });

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
            },
          };
        });

        this.insertNodes(node, childNodes);
      } catch (error) {
        throw error;
      }
    },
    async getFunctionFields(node) {
      try {
        const response = await this.api.post("/get_function_fields_mssql/", {
          function: node.title,
          schema: node.data.schema,
        });

        this.removeChildNodes(node);

        response.data.reduceRight((_, el) => {
          if (el.type === "O") {
            this.insertNode(
              node,
              el.name,
              {
                icon: "fas node-all fa-arrow-right node-function-field",
                schema: node.data.schema,
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
              },
              true
            );
          }
        }, null);
      } catch (error) {
        throw error;
      }
    },
    async getServerRoles(node) {
      try {
        const response = await this.api.post("/get_server_roles_mssql/");

        this.removeChildNodes(node);

        this.$refs.tree.updateNode(node.path, {
          title: `Server Roles (${response.data.data.length})`,
        });

        let childNodes = response.data.data.map((el) => {
          return {
            title: el.name,
            isLeaf: true,
            isExpanded: false,
            isDraggable: false,
            data: {
              icon: "fas node-all fa-user node-user",
              type: "server_role",
              contextMenu: "cm_server_role",
            },
          }
        });

        this.insertNodes(node, childNodes);
      } catch (error) {
        throw error;
      }
    },
    async getDatabaseRoles(node) {
      try {
        const response = await this.api.post("/get_database_roles_mssql/");

        this.removeChildNodes(node);

        this.$refs.tree.updateNode(node.path, {
          title: `Database Roles (${response.data.data.length})`,
        });

        let childNodes = response.data.data.map((el) => {
          return {
            title: el.name,
            isLeaf: true,
            isExpanded: false,
            isDraggable: false,
            data: {
              icon: "fas node-all fa-user node-user",
              type: "database_role",
              contextMenu: "cm_database_role",
            },
          }
        });

        this.insertNodes(node, childNodes);
      } catch (error) {
        throw error;
      }
    },
    async getLogins(node) {
      try {
        const response = await this.api.post("/get_logins_mssql/");

        this.removeChildNodes(node);

        this.$refs.tree.updateNode(node.path, {
          title: `Logins (${response.data.data.length})`,
        });

        let childNodes = response.data.data.map((el) => {
          return {
            title: el.name,
            isLeaf: true,
            isExpanded: false,
            isDraggable: false,
            data: {
              icon: "fas node-all fa-user node-user",
              type: "login",
              contextMenu: "cm_login",
            },
          }
        });

        this.insertNodes(node, childNodes);
      } catch (error) {
        throw error;
      }
    },
    async getUsers(node) {
      try {
        const response = await this.api.post("/get_users_mssql/");

        this.removeChildNodes(node);

        this.$refs.tree.updateNode(node.path, {
          title: `Users (${response.data.data.length})`,
        });

        let childNodes = response.data.data.map((el) => {
          return {
            title: el.name,
            isLeaf: true,
            isExpanded: false,
            isDraggable: false,
            data: {
              icon: "fas node-all fa-user node-user",
              type: "user",
              contextMenu: "cm_user",
            },
          }
        });

        this.insertNodes(node, childNodes);
      } catch (error) {
        throw error;
      }
    },
    async getTypes(node) {
      try {
        const response = await this.api.post("/get_types_mssql/", {
          schema: node.data.schema,
          all_schemas: false,
        });

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
            },
          }
        });

        this.insertNodes(node, childNodes);
      } catch (error) {
        throw error;
      }
    },
    getProperties(node) {
      this.checkCurrentDatabase(node, true, () => {
        this.getPropertiesConfirm(node);
      });
    },
    getPropertiesConfirm(node) {
      let schema = node.data.schema ? node.data.schema : null;
      let table = null;
      let object = node.title;
      let handledTypes = [
        "database",
        "login",
        "server_role",
        "database_role",
        "user",
        "schema",
        "table",
        "view",
        "table_field",
        "view_field",
        "primary_key",
        "foreign_key",
        "unique",
        "check",
        "trigger",
        "index",
        "function",
        "procedure",
        "statistic",
        "type",
      ];

      switch (node.data.type) {
        case "table_field":
        case "view_field":
        case "primary_key":
        case "foreign_key":
        case "unique":
        case "check":
        case "trigger":
        case "index":
        case "statistic":
          table = this.getParentNodeDeep(node, 2).title;
          break;
      }

      if (handledTypes.includes(node.data.type)) {
        this.$emit("treeTabsUpdate", {
          data: {
            schema: schema,
            table: table,
            object: object,
            type: node.data.type,
          },
          view: "/get_properties_mssql/",
        });
      } else {
        this.$emit("clearTabs");
      }
    },
    openWebSite(site) {
      window.open(site, "_blank");
    },
  },
};
</script>
