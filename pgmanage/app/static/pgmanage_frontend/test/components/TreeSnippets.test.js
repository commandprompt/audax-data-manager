import { describe, it, expect, vi, beforeEach } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import TreeSnippets from "@src/components/TreeSnippets.vue";
import { emitter } from "@src/emitter";
import { messageModalStore, tabsStore } from "@src/stores/stores_initializer";
import { showToast } from "@src/notification_control";

vi.mock("@src/notification_control", () => ({
  showToast: vi.fn(),
}));

vi.mock("@src/emitter", () => ({
  emitter: {
    on: vi.fn(),
    all: {
      delete: vi.fn(),
    },
  },
}));

vi.mock("@src/stores/stores_initializer", () => ({
  messageModalStore: {
    showModal: vi.fn(),
    showPromptModal: vi.fn(),
  },
  tabsStore: {
    tabs: [],
    removeTab: vi.fn(),
    selectTab: vi.fn(),
    createSnippetTab: vi.fn(),
  },
}));

vi.mock("@src/mixins/power_tree.js", () => ({
  default: {
    data() {
      return {
        selectedNode: null,
        cmRefreshObject: {
          label: "Refresh",
          icon: "fas fa-sync-alt",
          onClick: vi.fn(),
        },
        api: {
          post: vi.fn(),
        },
      };
    },
    methods: {
      onToggle: vi.fn(),
      onContextMenu: vi.fn(),
      onClickHandler: vi.fn(),
      handleLeftSideClick: vi.fn(),
      formatTitle(node) {
        return node.title;
      },
      toggleNode: vi.fn(),
      expandNode: vi.fn(),
      insertSpinnerNode: vi.fn(),
      insertNode: vi.fn(),
      removeChildNodes: vi.fn(),
      nodeOpenError: vi.fn(),
      getParentNode: vi.fn(() => ({
        title: "parent-folder",
        data: {
          id: 1,
          type: "folder",
        },
        children: [],
      })),
      getRootNode: vi.fn(() => ({
        title: "Snippets",
        data: {
          id: null,
          type: "folder",
        },
        children: [],
      })),
    },
  },
}));

describe("TreeSnippets.vue", () => {
  const mountComponent = () => {
    return mount(TreeSnippets, {
      props: {
        workspaceId: "ws-1",
      },
      global: {
        stubs: {
          PowerTree: true,
        },
      },
      shallow: true,
    });
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders with default root node", () => {
    const wrapper = mountComponent();

    expect(wrapper.vm.nodes).toEqual([
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
    ]);
  });

  it("mounted registers refresh_snippet_tree listener", () => {
    mountComponent();

    expect(emitter.on).toHaveBeenCalledWith(
      "refresh_snippet_tree",
      expect.any(Function),
    );
  });

  it("refresh_snippet_tree listener calls refreshTreeRecursive with parent id", () => {
    const wrapper = mountComponent();
    const refreshTreeRecursiveSpy = vi.spyOn(
      wrapper.vm,
      "refreshTreeRecursive",
    );
    const handler = emitter.on.mock.calls.find(
      ([eventName]) => eventName === "refresh_snippet_tree",
    )[1];

    handler(10);

    expect(refreshTreeRecursiveSpy).toHaveBeenCalledWith(10);
  });

  it("unmounted removes refresh_snippet_tree listener", () => {
    const wrapper = mountComponent();

    wrapper.unmount();

    expect(emitter.all.delete).toHaveBeenCalledWith("refresh_snippet_tree");
  });

  it("cm_node_root Create Snippet calls newNodeSnippet with snippet mode", () => {
    const wrapper = mountComponent();
    const selectedNode = {
      title: "Snippets",
      data: {
        id: null,
        type: "folder",
      },
    };

    wrapper.vm.selectedNode = selectedNode;
    wrapper.vm.newNodeSnippet = vi.fn();

    wrapper.vm.contextMenu.cm_node_root[1].onClick();

    expect(wrapper.vm.newNodeSnippet).toHaveBeenCalledWith(
      selectedNode,
      "snippet",
    );
  });

  it("cm_node_root Create Folder calls newNodeSnippet with folder mode", () => {
    const wrapper = mountComponent();
    const selectedNode = {
      title: "Snippets",
      data: {
        id: null,
        type: "folder",
      },
    };

    wrapper.vm.selectedNode = selectedNode;
    wrapper.vm.newNodeSnippet = vi.fn();

    wrapper.vm.contextMenu.cm_node_root[2].onClick();

    expect(wrapper.vm.newNodeSnippet).toHaveBeenCalledWith(
      selectedNode,
      "folder",
    );
  });

  it("cm_node Rename calls renameNodeSnippet", () => {
    const wrapper = mountComponent();
    const selectedNode = {
      title: "Folder 1",
      data: {
        id: 1,
        type: "folder",
      },
    };

    wrapper.vm.selectedNode = selectedNode;
    wrapper.vm.renameNodeSnippet = vi.fn();

    wrapper.vm.contextMenu.cm_node[3].onClick();

    expect(wrapper.vm.renameNodeSnippet).toHaveBeenCalledWith(selectedNode);
  });

  it("cm_node Delete calls deleteNodeSnippet", () => {
    const wrapper = mountComponent();
    const selectedNode = {
      title: "Folder 1",
      data: {
        id: 1,
        type: "folder",
      },
    };

    wrapper.vm.selectedNode = selectedNode;
    wrapper.vm.deleteNodeSnippet = vi.fn();

    wrapper.vm.contextMenu.cm_node[4].onClick();

    expect(wrapper.vm.deleteNodeSnippet).toHaveBeenCalledWith(selectedNode);
  });

  it("cm_snippet Edit calls startEditSnippetText", () => {
    const wrapper = mountComponent();
    const selectedNode = {
      title: "Snippet 1",
      isLeaf: true,
      data: {
        id: 1,
        type: "snippet",
      },
    };

    wrapper.vm.selectedNode = selectedNode;
    wrapper.vm.startEditSnippetText = vi.fn();

    wrapper.vm.contextMenu.cm_snippet[0].onClick();

    expect(wrapper.vm.startEditSnippetText).toHaveBeenCalledWith(selectedNode);
  });

  it("cm_snippet Rename calls renameNodeSnippet", () => {
    const wrapper = mountComponent();
    const selectedNode = {
      title: "Snippet 1",
      isLeaf: true,
      data: {
        id: 1,
        type: "snippet",
      },
    };

    wrapper.vm.selectedNode = selectedNode;
    wrapper.vm.renameNodeSnippet = vi.fn();

    wrapper.vm.contextMenu.cm_snippet[1].onClick();

    expect(wrapper.vm.renameNodeSnippet).toHaveBeenCalledWith(selectedNode);
  });

  it("cm_snippet Delete calls deleteNodeSnippet", () => {
    const wrapper = mountComponent();
    const selectedNode = {
      title: "Snippet 1",
      isLeaf: true,
      data: {
        id: 1,
        type: "snippet",
      },
    };

    wrapper.vm.selectedNode = selectedNode;
    wrapper.vm.deleteNodeSnippet = vi.fn();

    wrapper.vm.contextMenu.cm_snippet[2].onClick();

    expect(wrapper.vm.deleteNodeSnippet).toHaveBeenCalledWith(selectedNode);
  });

  it("doubleClickNode opens snippet editor for leaf node", () => {
    const wrapper = mountComponent();
    const node = {
      title: "Snippet 1",
      isLeaf: true,
      data: {
        id: 1,
        type: "snippet",
      },
    };

    wrapper.vm.startEditSnippetText = vi.fn();
    const onToggleSpy = vi.spyOn(wrapper.vm, "onToggle");
    const toggleNodeSpy = vi.spyOn(wrapper.vm, "toggleNode");

    wrapper.vm.doubleClickNode(node);

    expect(wrapper.vm.startEditSnippetText).toHaveBeenCalledWith(node);
    expect(onToggleSpy).not.toHaveBeenCalled();
    expect(toggleNodeSpy).not.toHaveBeenCalled();
  });

  it("doubleClickNode toggles folder node", () => {
    const wrapper = mountComponent();
    const node = {
      title: "Folder 1",
      isLeaf: false,
      data: {
        id: 1,
        type: "folder",
      },
    };

    wrapper.vm.startEditSnippetText = vi.fn();
    const onToggleSpy = vi.spyOn(wrapper.vm, "onToggle");
    const toggleNodeSpy = vi.spyOn(wrapper.vm, "toggleNode");

    wrapper.vm.doubleClickNode(node);

    expect(wrapper.vm.startEditSnippetText).not.toHaveBeenCalled();
    expect(onToggleSpy).toHaveBeenCalledWith(node);
    expect(toggleNodeSpy).toHaveBeenCalledWith(node);
  });

  it("refreshTree inserts spinner and loads folder children", () => {
    const wrapper = mountComponent();
    const insertSpinnerNodeSpy = vi.spyOn(wrapper.vm, "insertSpinnerNode");
    const node = {
      title: "Folder 1",
      children: [],
      data: {
        id: 1,
        type: "folder",
      },
    };

    wrapper.vm.getChildSnippetNodes = vi.fn();

    wrapper.vm.refreshTree(node);

    expect(insertSpinnerNodeSpy).toHaveBeenCalledWith(node);
    expect(wrapper.vm.getChildSnippetNodes).toHaveBeenCalledWith(node);
  });

  it("refreshTree does not insert spinner when node already has children", () => {
    const wrapper = mountComponent();
    const insertSpinnerNodeSpy = vi.spyOn(wrapper.vm, "insertSpinnerNode");
    const node = {
      title: "Folder 1",
      children: [{}],
      data: {
        id: 1,
        type: "folder",
      },
    };

    wrapper.vm.getChildSnippetNodes = vi.fn();

    wrapper.vm.refreshTree(node);

    expect(insertSpinnerNodeSpy).not.toHaveBeenCalled();
    expect(wrapper.vm.getChildSnippetNodes).toHaveBeenCalledWith(node);
  });

  it("refreshTree does not load children for non-folder node", () => {
    const wrapper = mountComponent();
    const insertSpinnerNodeSpy = vi.spyOn(wrapper.vm, "insertSpinnerNode");
    const node = {
      title: "Snippet 1",
      children: [],
      data: {
        id: 1,
        type: "snippet",
      },
    };

    wrapper.vm.getChildSnippetNodes = vi.fn();

    wrapper.vm.refreshTree(node);

    expect(insertSpinnerNodeSpy).toHaveBeenCalledWith(node);
    expect(wrapper.vm.getChildSnippetNodes).not.toHaveBeenCalled();
  });

  it("getChildSnippetNodes loads snippets and folders", async () => {
    const wrapper = mountComponent();
    const removeChildNodesSpy = vi.spyOn(wrapper.vm, "removeChildNodes");
    const insertNodeSpy = vi.spyOn(wrapper.vm, "insertNode");
    const node = {
      title: "Folder 1",
      children: [],
      data: {
        id: 1,
        type: "folder",
      },
    };

    wrapper.vm.api.post.mockResolvedValue({
      data: {
        snippets: [
          {
            id: 10,
            name: "Snippet 1",
          },
        ],
        folders: [
          {
            id: 20,
            name: "Folder 2",
          },
        ],
      },
    });

    await wrapper.vm.getChildSnippetNodes(node);
    await flushPromises();

    expect(wrapper.vm.api.post).toHaveBeenCalledWith("/get_node_children/", {
      snippet_id: 1,
    });

    expect(removeChildNodesSpy).toHaveBeenCalledWith(node);

    expect(insertNodeSpy).toHaveBeenCalledWith(
      node,
      "Snippet 1",
      {
        icon: "far node-all fa-file-code node-snippet-snippet",
        type: "snippet",
        contextMenu: "cm_snippet",
        id: 10,
        id_parent: 1,
        name: "Snippet 1",
      },
      true,
    );

    expect(insertNodeSpy).toHaveBeenCalledWith(node, "Folder 2", {
      icon: "fas node-all fa-folder node-snippet-folder",
      type: "folder",
      contextMenu: "cm_node",
      id: 20,
      id_parent: 1,
      name: "Folder 2",
    });
  });

  it("getChildSnippetNodes handles error via nodeOpenError", async () => {
    const wrapper = mountComponent();
    const nodeOpenErrorSpy = vi.spyOn(wrapper.vm, "nodeOpenError");
    const error = new Error("boom");
    const node = {
      title: "Folder 1",
      children: [],
      data: {
        id: 1,
        type: "folder",
      },
    };

    wrapper.vm.api.post.mockRejectedValue(error);

    await wrapper.vm.getChildSnippetNodes(node);
    await flushPromises();

    expect(nodeOpenErrorSpy).toHaveBeenCalledWith(error, node);
  });

  it("newNodeSnippet shows confirmation modal with snippet placeholder", () => {
    const wrapper = mountComponent();
    const node = {
      title: "Folder 1",
      data: {
        id: 1,
        type: "folder",
      },
    };

    wrapper.vm.newNodeSnippet(node, "snippet");

    expect(messageModalStore.showPromptModal).toHaveBeenCalledWith(
      "",
      "",
      expect.any(Function),
      null,
      "Snippet Name",
    );
  });

  it("newNodeSnippet shows confirmation modal with folder placeholder", () => {
    const wrapper = mountComponent();
    const node = {
      title: "Folder 1",
      data: {
        id: 1,
        type: "folder",
      },
    };

    wrapper.vm.newNodeSnippet(node, "folder");

    expect(messageModalStore.showPromptModal).toHaveBeenCalledWith(
      "",
      "",
      expect.any(Function),
      null,
      "Folder Name",
    );
  });

  it("newNodeSnippet shows toast when name is empty", () => {
    const wrapper = mountComponent();
    const node = {
      title: "Folder 1",
      data: {
        id: 1,
        type: "folder",
      },
    };


    wrapper.vm.newNodeSnippet(node, "snippet");

    const confirmCallback =
      messageModalStore.showPromptModal.mock.calls[0][2];
    confirmCallback("   ");

    expect(showToast).toHaveBeenCalledWith("error", "Name cannot be empty.");
    expect(wrapper.vm.api.post).not.toHaveBeenCalled();
  });

  it("newNodeSnippet creates node, refreshes tree, and emits treeUpdated", async () => {
    const wrapper = mountComponent();
    const node = {
      title: "Folder 1",
      children: [],
      data: {
        id: 1,
        type: "folder",
      },
    };

    wrapper.vm.refreshTree = vi.fn();
    wrapper.vm.api.post.mockResolvedValue({
      data: {},
    });


    wrapper.vm.newNodeSnippet(node, "snippet");

    const confirmCallback =
      messageModalStore.showPromptModal.mock.calls[0][2];
    confirmCallback("Snippet 1");

    await flushPromises();

    expect(wrapper.vm.api.post).toHaveBeenCalledWith("/new_node_snippet/", {
      snippet_id: 1,
      mode: "snippet",
      name: "Snippet 1",
    });

    expect(wrapper.vm.refreshTree).toHaveBeenCalledWith(node);
    expect(wrapper.emitted("treeUpdated")).toEqual([[]]);
  });

  it("newNodeSnippet handles create error via nodeOpenError", async () => {
    const wrapper = mountComponent();
    const nodeOpenErrorSpy = vi.spyOn(wrapper.vm, "nodeOpenError");
    const error = new Error("boom");
    const node = {
      title: "Folder 1",
      children: [],
      data: {
        id: 1,
        type: "folder",
      },
    };

    wrapper.vm.api.post.mockRejectedValue(error);


    wrapper.vm.newNodeSnippet(node, "snippet");

    const confirmCallback =
      messageModalStore.showPromptModal.mock.calls[0][2];
    confirmCallback("Snippet 1");

    await flushPromises();

    expect(nodeOpenErrorSpy).toHaveBeenCalledWith(error, node);
  });

  it("renameNodeSnippet shows toast when name is empty", () => {
    const wrapper = mountComponent();
    const node = {
      title: "Snippet 1",
      data: {
        id: 10,
        type: "snippet",
      },
    };


    wrapper.vm.renameNodeSnippet(node);

    const confirmCallback =
      messageModalStore.showPromptModal.mock.calls[0][2];
    confirmCallback("   ");

    expect(showToast).toHaveBeenCalledWith("error", "Name cannot be empty.");
    expect(wrapper.vm.api.post).not.toHaveBeenCalled();
  });

  it("renameNodeSnippet renames node, refreshes parent, and emits treeUpdated", async () => {
    const wrapper = mountComponent();
    const parentNode = {
      title: "Parent Folder",
      children: [],
      data: {
        id: 1,
        type: "folder",
      },
    };
    const node = {
      title: "Snippet 1",
      data: {
        id: 10,
        type: "snippet",
      },
    };

    wrapper.vm.getParentNode = vi.fn(() => parentNode);
    wrapper.vm.refreshTree = vi.fn();
    wrapper.vm.api.post.mockResolvedValue({
      data: {},
    });


    wrapper.vm.renameNodeSnippet(node);

    const confirmCallback =
      messageModalStore.showPromptModal.mock.calls[0][2];
    confirmCallback("Snippet renamed");

    await flushPromises();

    expect(wrapper.vm.api.post).toHaveBeenCalledWith("/rename_node_snippet/", {
      id: 10,
      mode: "snippet",
      name: "Snippet renamed",
    });

    expect(wrapper.vm.getParentNode).toHaveBeenCalledWith(node);
    expect(wrapper.vm.refreshTree).toHaveBeenCalledWith(parentNode);
    expect(wrapper.emitted("treeUpdated")).toEqual([[]]);
  });

  it("renameNodeSnippet handles rename error via nodeOpenError", async () => {
    const wrapper = mountComponent();
    const nodeOpenErrorSpy = vi.spyOn(wrapper.vm, "nodeOpenError");
    const error = new Error("boom");
    const node = {
      title: "Snippet 1",
      data: {
        id: 10,
        type: "snippet",
      },
    };

    wrapper.vm.api.post.mockRejectedValue(error);


    wrapper.vm.renameNodeSnippet(node);

    const confirmCallback =
      messageModalStore.showPromptModal.mock.calls[0][2];
    confirmCallback("Snippet renamed");

    await flushPromises();

    expect(nodeOpenErrorSpy).toHaveBeenCalledWith(error, node);
  });

  it("deleteNodeSnippet deletes node, removes opened snippet tab, refreshes parent, and emits treeUpdated", async () => {
    const wrapper = mountComponent();
    const existingTab = {
      id: "snippet-tab-1",
      metaData: {
        snippetObject: {
          id: 10,
        },
      },
    };
    const snippetPanel = {
      name: "Snippets",
      metaData: {
        secondaryTabs: [existingTab],
      },
    };
    const parentNode = {
      title: "Parent Folder",
      children: [],
      data: {
        id: 1,
        type: "folder",
      },
    };
    const node = {
      title: "Snippet 1",
      data: {
        id: 10,
        type: "snippet",
      },
    };

    tabsStore.tabs = [snippetPanel];

    wrapper.vm.getParentNode = vi.fn(() => parentNode);
    wrapper.vm.refreshTree = vi.fn();
    wrapper.vm.api.post.mockResolvedValue({
      data: {},
    });

    messageModalStore.showModal.mockImplementation((message, callback) => {
      callback();
    });

    wrapper.vm.deleteNodeSnippet(node);

    await flushPromises();

    expect(messageModalStore.showModal).toHaveBeenCalledWith(
      "Are you sure you want to delete this snippet?",
      expect.any(Function),
    );

    expect(wrapper.vm.api.post).toHaveBeenCalledWith("/delete_node_snippet/", {
      id: 10,
      mode: "snippet",
    });

    expect(tabsStore.removeTab).toHaveBeenCalledWith(existingTab);
    expect(wrapper.vm.getParentNode).toHaveBeenCalledWith(node);
    expect(wrapper.vm.refreshTree).toHaveBeenCalledWith(parentNode);
    expect(wrapper.emitted("treeUpdated")).toEqual([[]]);
  });

  it("deleteNodeSnippet does not remove tab when snippet tab is not opened", async () => {
    const wrapper = mountComponent();
    const snippetPanel = {
      name: "Snippets",
      metaData: {
        secondaryTabs: [],
      },
    };
    const node = {
      title: "Snippet 1",
      data: {
        id: 10,
        type: "snippet",
      },
    };

    tabsStore.tabs = [snippetPanel];

    wrapper.vm.refreshTree = vi.fn();
    wrapper.vm.api.post.mockResolvedValue({
      data: {},
    });

    messageModalStore.showModal.mockImplementation((message, callback) => {
      callback();
    });

    wrapper.vm.deleteNodeSnippet(node);

    await flushPromises();

    expect(tabsStore.removeTab).not.toHaveBeenCalled();
    expect(wrapper.vm.refreshTree).toHaveBeenCalled();
    expect(wrapper.emitted("treeUpdated")).toEqual([[]]);
  });

  it("deleteNodeSnippet handles delete error via nodeOpenError", async () => {
    const wrapper = mountComponent();
    const nodeOpenErrorSpy = vi.spyOn(wrapper.vm, "nodeOpenError");
    const error = new Error("boom");
    const node = {
      title: "Snippet 1",
      data: {
        id: 10,
        type: "snippet",
      },
    };

    wrapper.vm.api.post.mockRejectedValue(error);

    messageModalStore.showModal.mockImplementation((message, callback) => {
      callback();
    });

    wrapper.vm.deleteNodeSnippet(node);

    await flushPromises();

    expect(nodeOpenErrorSpy).toHaveBeenCalledWith(error, node);
  });

  it("startEditSnippetText selects existing snippet tab", async () => {
    const wrapper = mountComponent();
    const existingTab = {
      id: "snippet-tab-1",
      metaData: {
        snippetObject: {
          id: 10,
        },
      },
    };
    const snippetPanel = {
      name: "Snippets",
      metaData: {
        secondaryTabs: [existingTab],
      },
    };
    const node = {
      title: "Snippet 1",
      data: {
        id: 10,
        type: "snippet",
        name: "Snippet 1",
      },
    };

    tabsStore.tabs = [snippetPanel];

    wrapper.vm.api.post.mockResolvedValue({
      data: {
        data: "select 1;",
      },
    });

    await wrapper.vm.startEditSnippetText(node);
    await flushPromises();

    expect(wrapper.vm.api.post).toHaveBeenCalledWith("/get_snippet_text/", {
      snippet_id: 10,
    });

    expect(tabsStore.selectTab).toHaveBeenCalledWith(existingTab);
    expect(tabsStore.createSnippetTab).not.toHaveBeenCalled();
  });

  it("startEditSnippetText creates snippet tab when it is not opened", async () => {
    const wrapper = mountComponent();
    const snippetPanel = {
      name: "Snippets",
      metaData: {
        secondaryTabs: [],
      },
    };
    const node = {
      title: "Snippet 1",
      data: {
        id: 10,
        type: "snippet",
        name: "Snippet 1",
      },
    };

    tabsStore.tabs = [snippetPanel];

    wrapper.vm.api.post.mockResolvedValue({
      data: {
        data: "select 1;",
      },
    });

    await wrapper.vm.startEditSnippetText(node);
    await flushPromises();

    expect(tabsStore.selectTab).not.toHaveBeenCalled();
    expect(tabsStore.createSnippetTab).toHaveBeenCalledWith("ws-1", {
      id: 10,
      type: "snippet",
      name: "Snippet 1",
      text: "select 1;",
    });
  });

  it("startEditSnippetText handles get text error via nodeOpenError", async () => {
    const wrapper = mountComponent();
    const nodeOpenErrorSpy = vi.spyOn(wrapper.vm, "nodeOpenError");
    const error = new Error("boom");
    const node = {
      title: "Snippet 1",
      data: {
        id: 10,
        type: "snippet",
      },
    };

    wrapper.vm.api.post.mockRejectedValue(error);

    await wrapper.vm.startEditSnippetText(node);
    await flushPromises();

    expect(nodeOpenErrorSpy).toHaveBeenCalledWith(error, node);
  });
});
