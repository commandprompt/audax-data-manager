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
  >
    <template v-slot:toggle="{ node }">
      <i v-if="node.isExpanded" class="exp_col fas fa-chevron-down fa-sm"></i>
      <i v-if="!node.isExpanded" class="exp_col fas fa-chevron-right fa-sm"></i>
    </template>

    <template v-slot:title="{ node }">
      <span class="item-icon">
        <i :class="['icon_tree', node.data.icon]"></i>
      </span>
      <span v-if="node.data.raw_html" v-html="node.title"> </span>
      <span v-else>
        {{ formatTitle(node) }}
      </span>
    </template>
  </PowerTree>
</template>

<script>
import TreeMixin from "../mixins/power_tree.js";
import { PowerTree } from "@onekiloparsec/vue-power-tree";
import { showToast } from "../notification_control";
import { emitter } from "../emitter";
import { messageModalStore, tabsStore } from "../stores/stores_initializer";

export default {
  name: "TreeSnippets",
  components: {
    PowerTree,
  },
  mixins: [TreeMixin],
  props: {
    workspaceId: String,
  },
  emits: ["treeUpdated"],
  data() {
    return {
      nodes: [
        {
          title: "Snippets",
          isExpanded: false,
          isDraggable: false,
          data: {
            icon: "fas node-all fa-list-alt node-snippet-list",
            type: "folder",
            contextMenu: "cm_node_root",
            id: null,
          },
        },
      ],
    };
  },
  computed: {
    contextMenu() {
      return {
        cm_node_root: [
          this.cmRefreshObject,
          {
            label: "Create Snippet",
            icon: "fas fa-plus",
            onClick: () => {
              this.newNodeSnippet(this.selectedNode, "snippet");
            },
          },
          {
            label: "Create Folder",
            icon: "fas fa-folder-plus",
            onClick: () => {
              this.newNodeSnippet(this.selectedNode, "folder");
            },
          },
        ],
        cm_node: [
          this.cmRefreshObject,
          {
            label: "Create Snippet",
            icon: "fas fa-plus",
            onClick: () => {
              this.newNodeSnippet(this.selectedNode, "snippet");
            },
          },
          {
            label: "Create Folder",
            icon: "fas fa-folder-plus",
            onClick: () => {
              this.newNodeSnippet(this.selectedNode, "folder");
            },
          },
          {
            label: "Rename",
            icon: "fas fa-i-cursor",
            onClick: () => {
              this.renameNodeSnippet(this.selectedNode);
            },
          },
          {
            label: "Delete",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              this.deleteNodeSnippet(this.selectedNode);
            },
          },
        ],
        cm_snippet: [
          {
            label: "Edit",
            icon: "fas fa-edit",
            onClick: () => {
              this.startEditSnippetText(this.selectedNode);
            },
          },
          {
            label: "Rename",
            icon: "fas fa-i-cursor",
            onClick: () => {
              this.renameNodeSnippet(this.selectedNode);
            },
          },
          {
            label: "Delete",
            icon: "fas fa-times",
            divided: "up",
            onClick: () => {
              this.deleteNodeSnippet(this.selectedNode);
            },
          },
        ],
      };
    },
  },
  mounted() {
    emitter.on(`refresh_snippet_tree`, (parent_id = null) => {
      this.refreshTreeRecursive(parent_id);
    });
  },
  unmounted() {
    emitter.all.delete('refresh_snippet_tree');
  },
  methods: {
    doubleClickNode(node, e) {
      if (node.isLeaf) {
        this.startEditSnippetText(node);
        return;
      }
      this.onToggle(node);
      this.toggleNode(node);
    },
    refreshTree(node) {
      if (node.children.length == 0) this.insertSpinnerNode(node);
      if (node.data.type === "folder") {
        this.getChildSnippetNodes(node);
      }
    },
    getChildSnippetNodes(node) {
      this.api
        .post("/get_node_children/", {
          snippet_id: node.data.id,
        })
        .then((resp) => {
          this.removeChildNodes(node);

          resp.data.snippets.forEach((el) => {
            this.insertNode(
              node,
              el.name,
              {
                icon: "far node-all fa-file-code node-snippet-snippet",
                type: "snippet",
                contextMenu: "cm_snippet",
                id: el.id,
                id_parent: node.data.id,
                name: el.name,
              },
              true
            );
          });

          resp.data.folders.forEach((el) => {
            this.insertNode(node, el.name, {
              icon: "fas node-all fa-folder node-snippet-folder",
              type: "folder",
              contextMenu: "cm_node",
              id: el.id,
              id_parent: node.data.id,
              name: el.name,
            });
          });
        })
        .catch((error) => {
          this.nodeOpenError(error, node);
        });
    },
    newNodeSnippet(node, mode) {
      let placeholder = "Snippet Name";
      if (mode === "folder") placeholder = "Folder Name";

      messageModalStore.showPromptModal(
        "",
        "",
        (inputValue) => {
          let value = inputValue.trim();
          if (!value) {
            showToast("error", "Name cannot be empty.");
            return;
          }

          this.api
            .post("/new_node_snippet/", {
              snippet_id: node.data.id,
              mode: mode,
              name: value,
            })
            .then((resp) => {
              this.refreshTree(node);

              this.$emit("treeUpdated");
            })
            .catch((error) => {
              this.nodeOpenError(error, node);
            });
        },
        null,
        placeholder
      );
    },
    renameNodeSnippet(node) {
      messageModalStore.showPromptModal("", node.title, (inputValue) => {
        let value = inputValue.trim();
        if (!value) {
          showToast("error", "Name cannot be empty.");
          return;
        }

        this.api
          .post("/rename_node_snippet/", {
            id: node.data.id,
            mode: node.data.type,
            name: value,
          })
          .then((resp) => {
            this.refreshTree(this.getParentNode(node));

            this.$emit("treeUpdated");
          })
          .catch((error) => {
            this.nodeOpenError(error, node);
          });
      });
    },
    deleteNodeSnippet(node) {
      messageModalStore.showModal(
        `Are you sure you want to delete this ${node.data.type}?`,
        () => {
          this.api
            .post("/delete_node_snippet/", {
              id: node.data.id,
              mode: node.data.type,
            })
            .then((resp) => {
              // Checking if there is a tab for this snippet.
              let snippetPanel = tabsStore.tabs.find((tab) => tab.name === "Snippets");
              let existing_tab = snippetPanel.metaData.secondaryTabs.find(
                (snippet_tab) => {
                  return snippet_tab.metaData?.snippetObject?.id === node.data.id;
                }
              );
              if (existing_tab) {
                tabsStore.removeTab(existing_tab);
              } 
              this.refreshTree(this.getParentNode(node));

              this.$emit("treeUpdated");
            })
            .catch((error) => {
              this.nodeOpenError(error, node);
            });
        }
      );
    },
    startEditSnippetText(node) {
      this.api
      .post("/get_snippet_text/", {
        snippet_id: node.data.id,
      })
      .then((resp) => {
        // Checking if there is a tab for this snippet.
        let snippetPanel = tabsStore.tabs.find((tab) => tab.name === "Snippets");
        let existing_tab = snippetPanel.metaData.secondaryTabs.find(
          (snippet_tab) => {
            return snippet_tab.metaData?.snippetObject?.id === node.data.id;
          }
        );
        if (existing_tab) {
          tabsStore.selectTab(existing_tab);
        } else {
          tabsStore.createSnippetTab(this.workspaceId, {...node.data, text: resp.data.data})
        }
        })
        .catch((error) => {
          this.nodeOpenError(error, node);
        });
    },
    refreshTreeRecursive(parent_id) {
      const rootNode = this.getRootNode();

      const getInnerNode = (node, parent_id) => {
        if (node.data.id === parent_id && node.data.type === "folder") {
          this.refreshTree(node);
          this.expandNode(node);
        }
        if (!!node.children.length) {
          node.children.forEach((childNode) => {
            getInnerNode(childNode, parent_id);
          });
        }
      };

      rootNode.children.forEach((childNode) => {
        getInnerNode(childNode, parent_id);
      });
    },
  },
};
</script>
