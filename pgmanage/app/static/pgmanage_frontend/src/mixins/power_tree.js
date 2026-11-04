import { emitter } from "../emitter";
import ContextMenu from "@imengyu/vue3-context-menu";
import axios from "axios";
import { tabsStore, settingsStore, connectionsStore } from "../stores/stores_initializer";
import { logger } from "../logging/logger_setup";
import { axiosHooks } from "../logging/service";
import { handleError } from "../logging/utils";
import { h } from "vue";
import debounce from "lodash/debounce";
import { flashHighlight } from "../utils";

export default {
  emits: ["treeTabsUpdate", "clearTabs"],
  data() {
    return {
      selectedDatabase: tabsStore.selectedPrimaryTab.metaData.selectedDatabase,
      treeContextMenuOpen: false,
    };
  },
  computed: {
    cmRefreshObject() {
      return {
        label: "Refresh",
        icon: "fas fa-sync-alt",
        onClick: this.refreshNode,
      };
    },
    selectedNode() {
      return this.getSelectedNode();
    },
  },
  mounted() {
    this.api = axios.create({
      transformRequest: [
        (data) => {
          const transformedData = {
            ...data,
            database_index: this.databaseIndex,
            workspace_id: this.workspaceId,
          };
          return transformedData;
        },
        ...axios.defaults.transformRequest,
      ],
    });
    axiosHooks(logger, this.api)

    emitter.on(`refreshNode_${this.workspaceId}`, (e) => {
      this.refreshTree(e.node, true);
    });

    emitter.on(`removeNode_${this.workspaceId}`, (e) => {
      this.removeNode(e.node);
    });

    emitter.on(`refreshTreeRecursive_${this.workspaceId}`, (node_type) => {
      this.refreshTreeRecursive(node_type);
    });

    emitter.on(`focusTree_${this.workspaceId}`, () => {
      this.$refs.tree.$el.focus();
      flashHighlight(this.$refs.tree.$el.parentElement.parentElement);
    })

    this.$watch("selectedNode", (newVal) => {
      if (newVal === undefined) {
        this.$emit("clearTabs");
      }
    });
    const treeEl = document.getElementById(`${this.workspaceId}_tree`);
    if (treeEl) {
      treeEl.addEventListener("contextmenu", (e) => { e.preventDefault(); return false; });
      treeEl.addEventListener('keydown', this.handleTreeKeyboardNavigation);
    }
  },
  unmounted() {
    emitter.all.delete(`refreshNode_${this.workspaceId}`);
    emitter.all.delete(`removeNode_${this.workspaceId}`);
    emitter.all.delete(`refreshTreeRecursive_${this.workspaceId}`)
    emitter.all.delete(`focusTree_${this.workspaceId}`);
  },
  methods: {
    onClickHandler(node, e) {
      if (this.getRootNode().title !== "Snippets") {
        this.getProperties(node);
      }
    },
    onToggle(node, e) {
      this.$refs.tree.select(node.path);
      if (this.getRootNode().title !== "Snippets") {
        debounce((node) => {
          this.getProperties(node);
        }, 200)(node);
      }
      if (node.isExpanded) return;
      this.refreshTree(node);
      if(settingsStore.scrollTree) {
        this.$nextTick(() => {
          this.scrollIntoViewIfPossible(node)
        })
      }
    },
    doubleClickNode(node, e) {
      if (node.isLeaf) return;
      this.onToggle(node);
      this.toggleNode(node);
    },
    showContextMenu(node, e) {
      this.treeContextMenuOpen = true;
      ContextMenu.showContextMenu(
        {
          theme: "pgmanage",
          x: e.x,
          y: e.y,
          zIndex: 1000,
          minWidth: 230,
          keyboardControl: true,
          customClass: 'diagonal-safe-menu',
          items: this.contextMenu[node.data.contextMenu],
          onClose: () => {this.treeContextMenuOpen = false}
        }
      );
    },
    onContextMenu(node, e) {
      this.$refs.tree.select(node.path);
      e.preventDefault();
      if (!!node.data.contextMenu) {
        this.showContextMenu(node, e);
      }
    },
    removeChildNodes(node) {
      this.$refs.tree.updateNode(node.path, { children: [] });
    },
    insertSpinnerNode(node) {
      this.insertNode(
        node,
        "",
        {
          icon: "node-spin",
        },
        true
      );
    },
    insertNode(node, title, data, isLeaf = false) {
      this.$refs.tree.insert(
        { node: node, placement: "inside" },
        {
          title: title,
          isLeaf: isLeaf,
          isExpanded: false,
          isDraggable: false,
          data: {
            ...data,
          },
        }
      );
    },
    insertNodes(node, child_nodes) {
      this.$refs.tree.insert({ node: node, placement: "inside" }, child_nodes);
    },
    getParentNode(node) {
      const parentNode = this.$refs.tree.getNode(node.path.slice(0, -1));
      return parentNode;
    },
    getParentNodeDeep(node, depth = 1) {
      if (depth <= 0) {
        return node;
      }

      const parentNode = this.getParentNode(node);
      return this.getParentNodeDeep(parentNode, depth - 1);
    },
    getSelectedNode() {
      return this.$refs.tree.getSelected()[0];
    },
    getFirstChildNode(node) {
      const actualNode = this.$refs.tree.getNode(node.path);
      return actualNode.children[0];
    },
    getNodeEl(path) {
      return this.$refs.tree.$el.querySelector(
        `[path="${JSON.stringify(path)}"]`
      );
    },
    expandNode(node) {
      this.$refs.tree.updateNode(node.path, { isExpanded: true });
    },
    toggleNode(node) {
      this.$refs.tree.updateNode(node.path, { isExpanded: !node.isExpanded });
    },
    refreshNode() {
      const node = this.getSelectedNode();
      this.expandNode(node);
      this.refreshTree(node, true);
    },
    formatTitle(node) {
      if (node.data.unique !== undefined) {
        return `${node.title} (${node.data.unique})`;
      }
      return node.title;
    },
    removeNode(node) {
      this.$refs.tree.remove([node.path]);
    },
    nodeOpenError(error, node) {
      if (error?.response?.data?.password_timeout) {
        emitter.emit('show_password_prompt', {
          databaseIndex: this.databaseIndex,
          successCallback: () => {
            connectionsStore.queueChangeActiveDatabaseThreadSafe({
              database_index: this.databaseIndex,
              workspace_id: this.workspaceId,
              database: this.selectedDatabase,
            });

            this.refreshNode()
          },
          message: error.response.data.data,
          kind: error.response.data.kind})
      } else {
        this.removeChildNodes(node);
        handleError(error);
      }
    },
    getRootNode() {
      return this.$refs.tree.getFirstNode();
    },
    goToNodeAndSelect(node) {
      this.$refs.tree.select(node.path);
      const nodeElement = this.getNodeEl(node.path).querySelector('.vue-power-tree-row');
      nodeElement.scrollIntoView({
        block: "start",
        inline: "start",
        behavior: "smooth",
      });
      this.onClickHandler(node);
    },
    refreshTreeRecursive(node_type) {
      const rootNode = this.getRootNode();
      const getInnerNode = (node, node_type) => {
        if (node.data.type === node_type) {
          this.refreshTree(node, true);
          this.expandNode(node);
        }
        if (!!node.children.length) {

          for (let i = 0; i < node.children.length; i++) {
            let childNode = node.children[i];

            const childDatabase = this.getNodeDatabase(childNode);

            if (childDatabase === this.selectedDatabase) {
              if (
                childNode.data.type === "database" &&
                node_type === "extension_list"
              ) {
                this.refreshTree(childNode, true);

                setTimeout(() => {
                  getInnerNode(childNode, node_type);
                }, 200);
              } else {
                getInnerNode(childNode, node_type);
              }
            }
          }
        }
      };

      for (let i = 0; i < rootNode.children.length; i++) {
        getInnerNode(rootNode.children[i], node_type);
      }
    },
    scrollIntoViewIfPossible(node) {
      const nodeElement = this.getNodeEl(node.path).querySelector('.vue-power-tree-row');
      const nodeRect = nodeElement.getBoundingClientRect();
      const parentElement = this.$refs.tree.$el.parentElement

      const scrollTop = parentElement.scrollTop;
      const scrollHeight = parentElement.scrollHeight;
      const clientHeight = parentElement.clientHeight;

      // Calculate the space needed to scroll the node to the top
      const spaceAvailableForScroll = scrollHeight - scrollTop - clientHeight;
      const spaceNeededForScroll = nodeRect.top - 40

      if (spaceNeededForScroll <= spaceAvailableForScroll) {
        nodeElement.scrollIntoView({
          block: "start",
          inline: "start",
          behavior: "smooth",
        });
      } 
    },
    shouldUpdateNode(node, force) {
      const now = new Date();
      if (!force && !!node?.data?.last_update) {
        const lastUpdateDate = new Date(node.data.last_update);
        const interval = (now - lastUpdateDate) / 1000;
        if (interval < 60) return false;
      }

      this.$refs.tree.updateNode(node.path, {
        data: { ...node.data, last_update: now.toISOString() },
      });
      return true;
    },
    async expandAndRefreshIfNeeded(node) {
      if (!node.children || node.children.length === 0) {
        await this.refreshTree(node, true);
        this.expandNode(node);
      } else {
        this.expandNode(node);
        this.onClickHandler(node);
      }
    },
    handleTreeKeyboardNavigation(event) {
      if(this.treeContextMenuOpen)
        return;
      const keyCode = event.code;
      const tree = this.$refs.tree;
      
      const container = this.$refs.tree.$el.parentElement;
      const selectedNode = tree.getSelected()[0];
      let nodeToSelect;
      
      switch (keyCode) {
        case "ArrowDown":
          event.preventDefault();
          nodeToSelect = tree.getNextNode(selectedNode.path, node => node.isVisible);
          break;
        case "ArrowUp":
          event.preventDefault()
          nodeToSelect = tree.getPrevNode(selectedNode.path, node => node.isVisible);
          break;
        case "ArrowRight":
          if (selectedNode.isLeaf) return;

          if (!selectedNode.isExpanded) {
            this.onToggle(selectedNode);
            this.expandNode(selectedNode);
          } else {
            nodeToSelect = tree.getNextNode(selectedNode.path, node => node.isVisible);
          }
          break;
        case "ArrowLeft":
          if (selectedNode.level === 1) return;

          if (selectedNode.isLeaf || !selectedNode.isExpanded) {
            nodeToSelect = tree.getPrevNode(selectedNode.path, node => node.level === selectedNode.level - 1);
          } else if (selectedNode.isExpanded) {
            this.toggleNode(selectedNode);
          }
          break;
        case "Home":
          nodeToSelect = tree.getFirstNode()
          tree.select(nodeToSelect.path);
          return;
        case "End":
          nodeToSelect = tree.getLastNode() // last node might be not visible
          if (!nodeToSelect.isVisible) {
            // find any visible prev
            nodeToSelect = tree.getPrevNode(nodeToSelect.path, node => node.isVisible);
          }
          tree.select(nodeToSelect.path);
          return;
        case "PageDown": {
          event.preventDefault()
          const nodeEl = this.getNodeEl(selectedNode.path);
          const nodeHeight = nodeEl?.offsetHeight || 24;
          const visibleCount = Math.floor(container.clientHeight / nodeHeight);

          let node = selectedNode;
          for (let i = 0; i < visibleCount; i++) {
            const next = tree.getNextNode(node.path, node => node.isVisible);
            if (!next) break;
            node = next;
          }
          nodeToSelect = node;
          break;
        }
        case "PageUp": {
          event.preventDefault()
          const nodeEl = this.getNodeEl(selectedNode.path);
          const nodeHeight = nodeEl?.offsetHeight || 24;
          const visibleCount = Math.floor(container.clientHeight / nodeHeight);

          let node = selectedNode;
          for (let i = 0; i < visibleCount; i++) {
            const prev = tree.getPrevNode(node.path, node => node.isVisible);
            if (!prev) break;
            node = prev;
          }
          nodeToSelect = node;
          break;
        }
        case "Enter":
        case "Space":
          event.preventDefault()
          if (selectedNode.isLeaf) return;
          this.onToggle(selectedNode);
          this.toggleNode(selectedNode);
          return;
        case "ContextMenu":
        case "F10":
          if (keyCode === "ContextMenu" || event.shiftKey) {
            event.preventDefault();
            const nodeEl = this.getNodeEl(selectedNode.path);
            const rect = nodeEl.getBoundingClientRect();

            const fakeEvent = new MouseEvent("contextmenu", {
              bubbles: true,
              clientX: rect.left + rect.width / 2,
              clientY: rect.top + rect.height / 2,
            });

            this.onContextMenu(selectedNode, fakeEvent);
            return;
          }
          return;
        default:
          return;
      }

      if (!nodeToSelect) return;
      
      tree.select(nodeToSelect.path);
      this.getProperties(nodeToSelect);

      const nodeEl = this.getNodeEl(nodeToSelect.path).querySelector('.vue-power-tree-title');
      const nodeRect = nodeEl.getBoundingClientRect();
      const contRect = container.getBoundingClientRect();
      const headerHeight = 40;
      const footerHeight = 30;

      // Convert node position relative to scrollable content
      const nodeTop = container.scrollTop + (nodeRect.top - contRect.top);
      const nodeBottom = nodeTop + nodeRect.height;
      const viewTop = container.scrollTop + headerHeight;
      const viewBottom = viewTop + container.clientHeight - headerHeight - footerHeight;

      if (nodeTop < viewTop) {
        container.scrollTo({
          top: nodeTop - headerHeight,
          behavior: 'instant',
        });
      } else if (nodeBottom > viewBottom) {
        container.scrollTo({
          top: nodeBottom - container.clientHeight + footerHeight,
          behavior: 'instant',
        });
      }
    },
    resolveNodeFromEvent(event) {
      let target = event.target;
      let nodePath = null;

      if (target.classList.contains("vue-power-tree-gap")) {
        let parent = target.parentElement;
        nodePath = JSON.parse(parent.getAttribute("path"));
      } else if (!!target.getAttribute("path")) {
        nodePath = JSON.parse(target.getAttribute("path"));
      }

      if (!nodePath) return;

      const node = this.$refs.tree.getNode(nodePath);

      return node;
    },
    handleLeftSideClick(event) {
      const node = this.resolveNodeFromEvent(event);
      if (!node) return;
      
      this.$refs.tree.select(node.path);
      this.onClickHandler(node, event);
    },
    handleLeftSideDblClick(event) {
      const node = this.resolveNodeFromEvent(event);
      if (!node) return;

      this.doubleClickNode(node);
    },
    getNodeDatabase(node) {
      if (node.data?.type === "database") return node.title;

      let current = node;

      while (current?.path?.length > 1) {
        current = this.getParentNode(current);

        if (current?.data?.type === 'database') {
          return current.title;
        }
      }

      return null
    },
  },
};
