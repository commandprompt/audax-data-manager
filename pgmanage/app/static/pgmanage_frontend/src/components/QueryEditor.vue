<template>
  <div ref="editor" @contextmenu.stop.prevent="contextMenu">
  </div>
</template>
<script>
import ContextMenu from "@imengyu/vue3-context-menu";
import { snippetsStore, settingsStore, dbMetadataStore  } from "../stores/stores_initializer";
import { buildSnippetContextMenuObjects } from "../tree_context_functions/tree_snippets";
import { emitter } from "../emitter";
import { format } from "sql-formatter";
import { setupAceDragDrop, setupAceSelectionHighlight } from "../ace_extras/plugins";
import { editorModeMap, maxLinesForIndentSQL, sqlFormatterDialectMap } from "../constants";
import { showToast } from "../notification_control";
import { SQLAutocomplete, SQLDialect } from 'sql-autocomplete';
import { readClipboardText } from "@src/utils/clipboard";

export default {
  props: {
    readOnly: {
      type: Boolean,
      default: false,
    },
    autocomplete: {
      type: Boolean,
      default: true,
    },
    tabId: String,
    workspaceId: String,
    tabMode: String,
    dialect: String,
    databaseIndex: Number,
    databaseName: String,
  },
  emits: ["editorChange"],
  data() {
    return {
      editor: "",
      formatOptions: {
        tabWidth: 2,
        keywordCase: "upper",
        language: sqlFormatterDialectMap[this.dialect] ?? this.dialect,
        linesBetweenQueries: 1,
      },
      completer: null
    };
  },
  computed: {
    autocompleteMode() {
      return this.tabMode === "query" ? 0 : 1;
    },
  },
  watch: {
    readOnly(newValue, oldValue) {
      this.editor.setReadOnly(newValue);
    },
    autocomplete(newVal, oldVal) {
      this.editor.setOptions({
        enableLiveAutocompletion: newVal,
        liveAutocompletionDelay: 100,
      })
    }
  },
  mounted() {
    this.setupEditor();
    this.setupEvents();
    this.editor.on("change", (obj, editor) => {
      this.$emit("editorChange", this.editor.getValue().trim());
    });

    settingsStore.$subscribe((mutation, state) => {
      this.editor.setTheme(`ace/theme/${state.editorTheme}`);
      this.editor.setFontSize(state.fontSize);
    });
    if(this.databaseIndex && this.databaseName) {
      dbMetadataStore.fetchDbMeta(this.databaseIndex, this.workspaceId, this.databaseName, this.tabId).then(() => {
        this.setupCompleter(); 
      })
    }
    if(this.autocomplete) {
      this.editor.setOptions({
        enableLiveAutocompletion: true,
        liveAutocompletionDelay: 100,
      })
    }

    dbMetadataStore.$onAction((action) => {
      if (action.name === "refreshDBMeta") {
        if (
          action.args[0] === this.databaseIndex &&
          action.args[1] === this.workspaceId &&
          action.args[2] === this.databaseName
        ) {
          action.after(() => {
            this.setupCompleter();
          });
        }
      }
    });
  },
  unmounted() {
    this.clearEvents();
  },
  methods: {
    setupEditor() {
      let editor_mode = editorModeMap[this.dialect] || 'sql'

      this.editor = ace.edit(this.$refs.editor);
      this.editor.$blockScrolling = Infinity;
      this.editor.setTheme(`ace/theme/${settingsStore.editorTheme}`);
      this.editor.session.setMode(`ace/mode/${editor_mode}`);
      this.editor.setFontSize(settingsStore.fontSize);
      this.editor.setShowPrintMargin(false);

      // Remove shortcuts from ace in order to avoid conflict with pgmanage shortcuts
      this.editor.commands.bindKey("ctrl-space", null);
      this.editor.commands.bindKey("alt-e", null);
      this.editor.commands.bindKey("Cmd-,", null);
      this.editor.commands.bindKey("Cmd-Delete", null);
      this.editor.commands.bindKey("Ctrl-Delete", null);
      this.editor.commands.bindKey("Ctrl-Up", null);
      this.editor.commands.bindKey("Ctrl-Down", null);
      this.editor.commands.bindKey("Ctrl-F", null);
      this.editor.commands.bindKey("Ctrl-,", null);
      this.editor.commands.bindKey("ctrl-p", null);

      const scoreMap = {
        COLUMN: 5000,
        SCHEMA: 4000,
        TABLE: 3000,
        VIEW: 2000,
        KEYWORD: 1000,
      };

      this.editor.setOptions({
        enableBasicAutocompletion: [
          {
            getCompletions: (function (editor, session, pos, prefix, callback) {
              if(!this.completer)
                return
              const options = this.completer.autocomplete(
                editor.getValue(),
                editor.session.doc.positionToIndex(editor.selection.getCursor())
              );

              let ret = [];
              options.forEach(function(opt) {
                ret.push({
                    caption: opt.value,
                    value: opt.value,
                    meta: opt.optionType.toLowerCase(),
                    score: scoreMap[opt.optionType]
                });
              })
              callback(null, ret)
            }).bind(this),
            triggerCharacters: [".",],
          }
        ],
        enableHoverLinking: true
      });

      this.editor.focus();
      this.editor.resize();

      setupAceDragDrop(this.editor);
      setupAceSelectionHighlight(this.editor);
    },
    setupCompleter() {
      // TODO:
      // figure out how to do completion for console tab - suggest keywords only?
      // reuse completer instance for the same dbindex/database combo if possible
      // use fuzzy matching for completions
      // fix cursor overlapping with text letters in the editor
      // oracle support
      // multiple get meta requests ?

      const dbMeta = dbMetadataStore.getDbMeta(this.databaseIndex, this.databaseName)

      if(!dbMeta)
        return

      const filteredMeta = dbMeta.filter((schema) => !["information_schema", "pg_catalog"].includes(schema.name));
      
      const DIALECT_MAP = {
        'postgresql': SQLDialect.PLpgSQL,
        'mysql': SQLDialect.MYSQL,
        'mariadb': SQLDialect.MYSQL,
        'oracle': SQLDialect.PLSQL,
        'sqlite': SQLDialect.SQLITE,
        'mssql': SQLDialect.TSQL,
      }

      this.completer = new SQLAutocomplete(DIALECT_MAP[this.dialect] || SQLDialect.PLpgSQL, filteredMeta);
    },
    getEditorContent(fullContent, onlySelected) {
      if (fullContent) return this.editor.getValue()
      
      let selectedText = this.editor.getSelectedText()

      if (onlySelected) return selectedText
      return selectedText || this.editor.getValue()
    },
    getQueryOffset() {
      return this.editor.selection.getRange().start.row
    },
    contextMenu(event) {
      const hasSelectedContent = !!this.editor.getSelectedText()

      let option_list = [
        {
          label: "Run selection",
          icon: "fas fa-play",
          disabled: !hasSelectedContent,
          onClick: () => {
            this.$emit("run-selection");
          },
        },
        {
          label: "Copy",
          icon: "fas fa-copy",
          disabled: !hasSelectedContent,
          onClick: () => {
            document.execCommand("copy");
          },
        },
        {
          label: "Paste",
          icon: "fas fa-paste",
          onClick: async () => {
            const text = await readClipboardText();

            if (!text) {
              return;
            }

            this.editor.execCommand("paste", text);
          },
        },
        {
          label: "Save as snippet",
          icon: "fas fa-save",
          children: buildSnippetContextMenuObjects(
            "save",
            snippetsStore,
            this.editor.getValue()
          ),
        },
      ];

      let postgres_options = [
        {
          label: "Explain selection",
          icon: "fas fa-chart-simple",
          disabled: !hasSelectedContent,
          onClick: () => {
            this.$emit("run-selection-explain");
          },
        },
        {
          label: "Explain Analyze selection",
          icon: "fas fa-magnifying-glass-chart",
          disabled: !hasSelectedContent,
          onClick: () => {
            this.$emit("run-selection-explain-analyze");
          },
        },
      ];

      if (this.dialect === "postgresql") {
        option_list.splice(1, 0, ...postgres_options);
      };

      if (snippetsStore.files.length != 0 || snippetsStore.folders.length != 0)
        option_list.push({
          label: "Use snippet",
          icon: "fas fa-file-code",
          children: buildSnippetContextMenuObjects(
            "load",
            snippetsStore,
            this.editor.getValue()
          ),
        });
      ContextMenu.showContextMenu({
        theme: "pgmanage",
        x: event.x,
        y: event.y,
        zIndex: 1000,
        minWidth: 230,
        items: option_list,
      });
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
    focus() {
      this.editor.focus();
    },
    setupEvents() {
      emitter.on(`${this.tabId}_show_autocomplete_results`, (event) => {
        this.editor.execCommand("startAutocomplete")
      });

      emitter.on(`${this.tabId}_copy_to_editor`, (command) => {
        this.editor.setValue(command);
        this.editor.clearSelection();
        this.editor.gotoLine(0, 0, true);
      });

      emitter.on(`${this.tabId}_insert_to_editor`, (command) => {
        this.editor.insert(command);
        this.editor.clearSelection();
      });

      emitter.on(`${this.tabId}_indent_sql`, () => {
        this.indentSQL();
      });

      emitter.on(`${this.tabId}_find_replace`, () => {
        this.editor.execCommand("find")
      });

    },
    clearEvents() {
      emitter.all.delete(`${this.tabId}_show_autocomplete_results`);
      emitter.all.delete(`${this.tabId}_copy_to_editor`);
      emitter.all.delete(`${this.tabId}_insert_to_editor`);
      emitter.all.delete(`${this.tabId}_indent_sql`);
      emitter.all.delete(`${this.tabId}_find_replace`);

    },
  }
};
</script>
