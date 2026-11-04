<template>
  <div>
    <div ref="editor" class="snippet-editor"></div>

    <div ref="bottomToolbar" class="row px-2">
      <div class="tab-actions col-12">
        <button
          data-testid="snippet-tab-indent-button"
          class="btn btn-secondary"
          title="Indent SQL"
          @click="indentSQL"
        >
          <i class="fas fa-indent me-2"></i>Indent
        </button>
        <button
          data-testid="snippet-tab-save-button"
          class="btn btn-primary"
          title="Save"
          @click="saveSnippetText"
        >
          <i class="fas fa-save me-2"></i>Save
        </button>
        <button
          data-testid="snippet-tab-open-file-button"
          class="btn btn-primary"
          title="Open file"
          @click="openFileManagerModal"
        >
          <i class="fas fa-folder-open me-2"></i>Open file
        </button>

        <button
          :disabled="fileSaveDisabled"
          data-testid="snippet-tab-save-file-button"
          class="btn btn-primary"
          title="Save to File"
          @click="saveFile"
        >
          <i class="fas fa-download me-2"></i>Save to File
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import { format } from "sql-formatter";
import { emitter } from "../emitter";
import ContextMenu from "@imengyu/vue3-context-menu";
import { buildSnippetContextMenuObjects } from "../tree_context_functions/tree_snippets";
import {
  snippetsStore,
  settingsStore,
  tabsStore,
  messageModalStore,
  fileManagerStore
} from "../stores/stores_initializer";
import { setupAceDragDrop, setupAceSelectionHighlight } from "../ace_extras/plugins";
import FileInputChangeMixin from "../mixins/file_input_mixin";
import { maxLinesForIndentSQL } from "../constants";
import { showToast } from "../notification_control";
import { saveBlobAs } from "../utils/native_dialog";

export default {
  name: "SnippetTab",
  mixins: [FileInputChangeMixin],
  props: {
    tabId: String,
    snippet: {
      type: Object,
      default: {
        id: null,
        name: null,
        text: null,
        parent: null,
        type: "snippet",
      },
    },
  },
  data() {
    return {
      editor: null,
      formatOptions: {
        tabWidth: 2,
        keywordCase: "upper",
        linesBetweenQueries: 1,
        language: "sql",
      },
      heightSubtract: 100 + settingsStore.fontSize,
      fileSaveDisabled: true,
      editorValue: "",
    };
  },
  computed: {
    editorSize() {
      return `calc(100vh - ${this.heightSubtract}px)`;
    },
    snippetPanel() {
      return tabsStore.tabs.find((tab) => tab.name === "Snippets");
    },
    hasChanges() {
      return (
        (!!this.snippet?.id && this.snippet.text !== this.editorValue) ||
        (this.snippet?.id === null && !!this.editorValue)
      );
    },
  },
  beforeMount() {
    if (!!this.snippet.id) {
      this.fileSaveDisabled = false;
    }
  },
  mounted() {
    this.setupEditor();
    this.handleResize();
    this.setupEvents();
  },
  unmounted() {
    this.clearEvents();
  },
  updated() {
    this.handleResize();
  },
  methods: {
    setupEditor() {
      this.editor = ace.edit(this.$refs.editor);
      this.editor.$blockScrolling = Infinity;
      this.editor.setTheme(`ace/theme/${settingsStore.editorTheme}`);
      this.editor.session.setMode("ace/mode/sql");

      this.editor.setFontSize(settingsStore.fontSize);
      this.editor.setShowPrintMargin(false);
      this.editor.setValue(this.snippet.text);
      this.editorValue = this.snippet.text;
      this.editor.clearSelection();

      this.editor.commands.bindKey("ctrl-space", null);

      //Remove shortcuts from ace in order to avoid conflict with omnidb shortcuts
      this.editor.commands.bindKey("Cmd-,", null);
      this.editor.commands.bindKey("Ctrl-,", null);
      this.editor.commands.bindKey("Cmd-Delete", null);
      this.editor.commands.bindKey("Ctrl-Delete", null);
      this.editor.commands.bindKey("Ctrl-Up", null);
      this.editor.commands.bindKey("Ctrl-Down", null);
      this.editor.commands.bindKey("ctrl-p", null);

      this.editor.on("change", () => {
        const editorValue = this.editor.getValue();
        this.fileSaveDisabled = !editorValue;
        this.editorValue = editorValue;
      });

      this.editor.focus();
      setupAceDragDrop(this.editor, true);
      setupAceSelectionHighlight(this.editor);
    },
    setupEvents() {
      emitter.on(`${this.tabId}_editor_focus`, () => {
        this.editor.focus();
      });

      emitter.on(`${this.tabId}_copy_to_editor`, (snippet) => {
        this.editor.setValue(snippet);
        this.editor.clearSelection();
        this.editor.gotoLine(0, 0, true);
      });

      emitter.on(`${this.tabId}_resize`, () => {
        this.handleResize();
      });

      settingsStore.$onAction((action) => {
        if (action.name === "setFontSize") {
          action.after(() => {
            this.editor.setFontSize(settingsStore.fontSize);
            this.handleResize();
          });
        } else if (action.name === "setEditorTheme") {
          action.after(() => {
            this.editor.setTheme(`ace/theme/${settingsStore.editorTheme}`);
          });
        }
      });
    },
    clearEvents() {
      emitter.all.delete(`${this.tabId}_resize`);
      emitter.all.delete(`${this.tabId}_editor_focus`);
      emitter.all.delete(`${this.tabId}_copy_to_editor`);
    },
    indentSQL() {
      let editor_value = this.editor.getValue();

      if (this.editor.session.getLength() > maxLinesForIndentSQL) {
        showToast(
          "error",
          `Max lines(${maxLinesForIndentSQL}) for indentSQL exceeded.`
        );
        return;
      }

      let formatted = format(editor_value, this.formatOptions);
      if (formatted.length) {
        this.editor.setValue(formatted);
        this.editor.clearSelection();
        this.editor.gotoLine(0, 0, true);
      }
    },
    saveSnippetText(event) {
      let callback = function (return_object) {
        let snippetPanel = tabsStore.tabs.find(
          (tab) => tab.name === "Snippets"
        );
        snippetPanel.metaData.selectedTab.metaData.snippetObject =
          return_object;
        snippetPanel.metaData.selectedTab.name = return_object.name;
      };

      if (this.snippet.id !== null) {
        emitter.emit("save_snippet_text_confirm", {
          saveObject: this.snippet,
          text: this.editor.getValue(),
          callback: callback,
        });
      } else {
        ContextMenu.showContextMenu({
          theme: "pgmanage",
          x: event.x,
          y: event.y,
          zIndex: 1000,
          minWidth: 230,
          direction: "tr",
          items: buildSnippetContextMenuObjects(
            "save",
            snippetsStore,
            this.editor.getValue(),
            callback
          ),
        });
      }
    },
    handleResize() {
      // handle case when snippets panel is not visible
      const top =
        this.$refs.editor.getBoundingClientRect().top > window.innerHeight
          ? 55
          : this.$refs.editor.getBoundingClientRect().top;
      this.heightSubtract = top + 30 * (settingsStore.fontSize / 10);
    },
    openFileManagerModal() {
      const editorContent = this.editor.getValue();
      if (!!editorContent) {
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
      const today = new Date();
      const nameSuffix = this.$props.snippet?.name
        ? this.$props.snippet?.name
        : `${today.getHours()}${today.getMinutes()}`;
      let snippetTab = tabsStore.getSelectedSecondaryTab(this.snippetPanel.id)
      const fileName = snippetTab.metaData?.editingFile ? snippetTab.name : `pgmanage-snippet-${nameSuffix}.sql`

      const file = new File(
        [this.editor.getValue()],
        fileName,
        {
          type: "application/sql",
        }
      );

      if (window.showSaveFilePicker) {
        try {
          const handle = await showSaveFilePicker({
            suggestedName: file.name,
            types: [
              {
                description: "SQL Script",
                accept: {
                  "application/sql": [".sql"],
                },
              },
            ],
          });

          const writable = await handle.createWritable();
          await writable.write(file);
          writable.close();
        } catch (e) {
          console.log(e);
        }
      } else {
        await saveBlobAs(file, file.name);
      }
    },
  },
  watch: {
    hasChanges() {
      const tab = tabsStore.getSecondaryTabById(this.tabId, this.snippetPanel?.id);
      if (tab) {
        tab.metaData.hasUnsavedChanges = this.hasChanges;
      }
    },
  }
};
</script>

<style scoped>
.snippet-editor {
  height: v-bind(editorSize);
}

.tab-actions {
  align-items: center;
  display: flex;
  justify-content: flex-start;
  min-height: 35px;
}

.tab-actions > button {
  margin-right: 5px;
}
</style>
