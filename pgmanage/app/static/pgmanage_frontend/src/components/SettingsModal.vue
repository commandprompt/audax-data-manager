<template>
  <div class="modal fade" ref="settingsModal" id="modal_settings" tabindex="-1" role="dialog" aria-hidden="true">
    <div class="modal-dialog" role="document">
      <div class="modal-content">
        <div class="modal-header align-items-center">
          <h2 class="modal-title fw-bold">Settings</h2>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close" @click="resetUnsavedSettings"></button>
        </div>
        <div class="modal-body">
          <ul class="nav nav-tabs" role="tablist">
            <li class="nav-item">
              <a class="nav-link active" id="settings_shortcuts-tab" data-bs-toggle="tab" href="#settings_shortcuts"
                role="tab" aria-controls="settings_shortcuts" aria-selected="true">Shortcuts</a>
            </li>
            <li class="nav-item">
              <a class="nav-link" id="settings_options-tab" data-bs-toggle="tab" href="#settings_options" role="tab"
              aria-controls="settings_options" aria-selected="false">Options</a>
            </li>
            <li class="nav-item">
              <a class="nav-link" id="settings-paths-tab" data-bs-toggle="tab" href="#settings_paths" role="tab"
                aria-controls="settings_paths" aria-selected="false">Paths</a>
            </li>
            <li v-if="!desktopMode" class="nav-item">
              <a class="nav-link" id="settings_password-tab" data-bs-toggle="tab" href="#settings_password" role="tab"
                aria-controls="settings_password" aria-selected="false">Password</a>
            </li>
          </ul>

          <div class="tab-content p-3">
            <ShortcutsTab 
              @recording-status:update="(status) => { recordingShortcut = status }" 
              @save-settings="saveSettings"
              />

            <div class="tab-pane fade" id="settings_options" role="tabpanel" aria-labelledby="settings_options-tab">
              <div class="row">
                <div class="form-group col-6">
                  <label for="sel_theme" class="fw-bold mb-2">Theme</label>
                  <select id="sel_theme" class="form-select" v-model="theme">
                    <option value="light">Light</option>
                    <option value="dark">Dark</option>
                  </select>
                </div>
                <div class="form-group col-6">
                  <label for="sel_interface_font_size" class="fw-bold mb-2">Font Size</label>
                  <select id="sel_interface_font_size" class="form-select" v-model="fontSize">
                    <option v-for="font_size in fontSizeOptions" :key="font_size" :value="font_size">{{ font_size }}
                    </option>
                  </select>
                </div>
              </div>

              <div class="row">
                <div class="form-group col-6">
                  <label for="sel_csv_encoding" class="fw-bold mb-2">CSV Encoding</label>
                  <select id="sel_csv_encoding" class="form-select" v-model="csvEncoding">
                    <option v-for="encoding in encodingValues" :key="encoding" :value="encoding">{{ encoding }}</option>
                  </select>
                </div>

                <div class="form-group col-6">
                  <label for="txt_csv_delimiter" class="fw-bold mb-2">CSV Delimiter</label>
                  <input type="text" id="txt_csv_delimiter" placeholder="Delimiter"
                    :class="['form-control', { 'is-invalid': v$.csvDelimiter.$invalid }]"
                    v-model="csvDelimiter">
                  <div class="invalid-feedback">
                    <span v-for="error of v$.csvDelimiter.$errors" :key="error.$uid">
                      {{ error.$message }}
                    </span>
                  </div>
                </div>

              </div>

              <div class="row">
                <div class="col-6">
                  <div
                    class="form-check form-switch"
                    v-tooltip
                    data-bs-toggle="tooltip"
                    data-bs-placement="bottom"
                    data-bs-title="Restore workspace tabs when application is loaded"
                  >
                    <input v-model="restoreTabs" id="restore_tabs" type="checkbox" class="form-check-input" >
                    <label for="restore_tabs" class="form-check-label fw-bold mb-2">Restore Tabs on Start</label>
                  </div>
                </div>

                <div class="col-6">
                  <div
                    class="form-check form-switch"
                    v-tooltip
                    data-bs-toggle="tooltip"
                    data-bs-placement="bottom"
                    data-bs-title="Scroll the Database Explorer tree node into view when expanded."
                    >
                    <input v-model="scrollTree" id="scroll_tree" type="checkbox" class="form-check-input" >
                    <label for="scroll_tree" class="form-check-label fw-bold mb-2">Database Tree Autoscroll</label>
                  </div>
                </div>
              </div>

              <div class="row">
                <div class="form-group col-6">
                  <label for="date_format" class="fw-bold mb-2">Date format</label>
                  <select id="date_format" class="form-select" v-model="selectedDateFormat">
                    <option v-for="dateFormat in dateFormats" :key="dateFormat" :value="dateFormat">{{ dateFormat }}
                    </option>
                  </select>
                </div>

                <div class="col-6">
                  <label class="fw-bold mb-3">Preview</label>
                  <p class="fw-bold"> {{ formattedDatePreview }}</p>
                </div>

              </div>

              <div class="text-end">
                <button class='btn btn-success' @click='saveSettings'>Save</button>
              </div>
            </div>

            <div class="tab-pane fade" id="settings_paths" role="tabpanel" aria-labelledby="settings-paths-tab">
              <div class="row">
                <div class="form-group col-12">
                  <div class="d-flex justify-content-between mb-3">
                    <label class="fw-bold my-2">PostgreSQL Binaries</label>
                    <button class='btn btn-ghost btn-ghost-secondary' @click='discoverBinaries'>Discover binaries</button>
                  </div>

                  <div v-for="k in pgKeys" :key="k" class="mb-2">
                    <div class="d-flex align-items-center">
                      <label :for="`binary_path_${k}`" class="w-25 text-muted">{{ k }}</label>
                      <div class="input-group">
                        <input
                          :id="`binary_path_${k}`"
                          type="text"
                          class="form-control"
                          :value="binaryPaths[k] || ''"
                          @input="setBinaryPathForVersion(k, $event.target.value)"
                          :placeholder="`${action} binary path..`"
                          autocomplete="off"
                        />

                        <button v-if="desktopMode" class="btn btn-outline-secondary mb-0" type="button"
                          @click="selectPostgresqlPathForVersion(k)">
                          Select
                        </button>
                      </div>

                      <a data-testid="validate-binary-path-button"
                        class="btn btn-outline-primary ms-2"
                        @click="validateBinaryPath(binaryPaths[k], 'postgres')"
                        title="Validate">
                        Validate
                      </a>
                    </div>
                  </div>
                </div>
              </div>

              <div v-if="!isWindowsOS" class="row">
                <div class="form-group col-12">
                  <label for="pigz_path" class="fw-bold mb-2">Pigz Binary Path</label>
                  <div class="d-flex">
                    <div class="input-group">
                      <input id="pigz_path" type="text" class="form-control" v-model="pigzPath"
                        :placeholder="`${action} binary path..`" autocomplete="off">
                      <button v-if="desktopMode" class="btn btn-outline-secondary mb-0" type="button"
                        @click="selectPigzPath">
                        Select
                      </button>
                    </div>
                    <a class="btn btn-outline-primary ms-2" @click="validateBinaryPath(pigzPath, 'pigz')" title="Validate">
                      Validate
                    </a>
                  </div>
                </div>
              </div>

              <div class="text-end">
                <button class='btn btn-success' @click='saveSettings'>Save</button>
              </div>
            </div>

            <div class="tab-pane fade" id="settings_password" role="tabpanel" aria-labelledby="settings_password-tab">
              <div class="row">
                <div class="form-group col-6">
                  <label for="txt_new_pwd" class="fw-bold mb-2">New Password</label>
                  <input v-model="password" id="txt_new_pwd" type="password" class="form-control" @input="checkPassword"
                    minlength="8" required>
                  <password-meter :password="password" />
                </div>
                <div class="form-group col-6">
                  <label for="txt_confirm_new_pwd" class="fw-bold mb-2">Confirm</label>
                  <input ref="passwordConfirm" v-model="passwordConfirm" id="txt_confirm_new_pwd" type="password"
                    class="form-control" @input="checkPassword" minlength="8" required>
                  <div class="invalid-feedback">
                    Password must be matching.
                  </div>
                </div>
              </div>
              <div class="text-end">
                <button class='btn btn-success' @click='saveUserPassword' :disabled="buttonFormDisabled">Save</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { refreshHeights } from '../workspace'
import axios from 'axios'
import { showAlertText, showToast } from '../notification_control'
import { minFontSize, maxFontSize } from '../constants'
import moment from 'moment'
import { settingsStore } from '../stores/stores_initializer'
import { useVuelidate } from '@vuelidate/core'
import { required, maxLength } from '@vuelidate/validators'
import { Modal } from 'bootstrap'
import PasswordMeter from 'vue-simple-password-meter';
import { handleError } from '@src/logging/utils';
import { pickNativePath } from '../utils/native_dialog'
import SettingsModalShortcutsTab from './SettingsModalShortcutsTab.vue'

const light_terminal_theme = {
      background: '#FFFFFF',
      brightBlue: '#006de2',
      brightGreen: '#4b9800',
      foreground: '#454545',
      cursor: '#454545',
      cursorAccent: '#FFFFFF',
      selectionBackground: '#1560AD15'
    }

const dark_terminal_theme = {
      background: '#16171E',
      selectionBackground: '#1560AD30',
      foreground: '#F8FAFD',
    }

export default {
  name: 'SettingsModal',
  components: {
    PasswordMeter,
    ShortcutsTab: SettingsModalShortcutsTab,
  },
  data() {
    return {
      buttonFormDisabled: true,
      password: '',
      passwordConfirm: '',
      encodingValues: [
        "ascii", "big5", "big5hkscs", "cp037", "cp273", "cp424",
        "cp437", "cp500", "cp720", "cp737", "cp775", "cp850",
        "cp852", "cp855", "cp856", "cp857", "cp858", "cp860",
        "cp861", "cp862", "cp863", "cp864", "cp865", "cp866",
        "cp869", "cp874", "cp875", "cp932", "cp949", "cp950",
        "cp1006", "cp1026", "cp1125", "cp1140", "cp1250", "cp1251",
        "cp1252", "cp1253", "cp1254", "cp1255", "cp1256", "cp1257",
        "cp1258", "cp65001", "euc-jp", "euc-jis-2004", "euc-jisx0213",
        "euc-kr", "gb2312", "gbk", "gb18030", "hz", "iso2022-jp",
        "iso2022-jp-1", "iso2022-jp-2", "iso2022-jp-2004", "iso2022-jp-3",
        "iso2022-jp-ext", "iso2022-kr", "latin-1", "iso8859-2", "iso8859-3",
        "iso8859-4", "iso8859-5", "iso8859-6", "iso8859-7", "iso8859-8", "iso8859-9",
        "iso8859-10", "iso8859-11", "iso8859-13", "iso8859-14", "iso8859-15",
        "iso8859-16", "johab", "koi8-r", "koi8-t", "koi8-u", "kz1048", "mac-cyrillic",
        "mac-greek", "mac-iceland", "mac-latin2", "mac-roman", "mac-turkish", "ptcp154",
        "shift-jis", "shift-jis-2004", "shift-jisx0213", "utf-32", "utf-32-be",
        "utf-32-le", "utf-16", "utf-16-be", "utf-16-le", "utf-7", "utf-8",
        "utf-8-sig", "windows-1252"
      ],
      dateFormats: ['YYYY-MM-DD, HH:mm:ss', 'MM/D/YYYY, h:mm:ss A', 'MMM D YYYY, h:mm:ss A'],
      fallbackFontSize: null,
      fallbackTheme: null,
      hidden: true,
      recordingShortcut: false,
    }
  },
  validations() {
    let baseRules = {
      csvDelimiter: {
        required: required,
        maxLength: maxLength(1),
      }
    }
    return baseRules
  },
  setup() {
    return { v$: useVuelidate({ $lazy: true }) }
  },
  computed: {
    fontSizeOptions() {
      return Array(1 + maxFontSize - minFontSize).fill(minFontSize).map((x, y) => x + y)
    },
    action() {
      return this.desktopMode ? 'Select' : 'Enter'
    },
    formattedDatePreview() {
      return moment().format(this.selectedDateFormat)
    },
    isWindowsOS() {
      return navigator.userAgent.indexOf("Win") != -1
    },
    fontSize: {
      get() {
        return settingsStore.fontSize;
      },
      set(value) {
        settingsStore.setFontSize(value);
      },
    },
    theme: {
      get() {
        return settingsStore.theme
      },
      set(value) {
        settingsStore.setTheme(value);
      },
    },
    csvEncoding: {
      get() {
        return settingsStore.csvEncoding
      },
      set(value) {
        settingsStore.setCSVEncoding(value)
      }
    },
    csvDelimiter: {
      get() {
        return settingsStore.csvDelimiter
      },
      set(value) {
        settingsStore.setCSVDelimiter(value)
      }
    },
    pigzPath: {
      get() {
        return settingsStore.pigzPath
      },
      set(value) {
        settingsStore.setPigzPath(value)
      }
    },
    selectedDateFormat: {
      get() {
        return settingsStore.dateFormat
      },
      set(value) {
        settingsStore.setDateFormat(value)
      }
    },
    restoreTabs: {
      get() {
        return settingsStore.restoreTabs
      },
      set(value) {
        settingsStore.setRestoreTabs(value)
      }
    },
    scrollTree: {
      get() {
        return settingsStore.scrollTree
      },
      set(value) {
        settingsStore.setScrollTree(value)
      }
    },
    desktopMode() {
      return settingsStore.desktopMode
    },
    binaryPaths() {
      return settingsStore.binaryPaths;
    },
    pgKeys() {
      const keys = Object.keys(this.binaryPaths || {});
      return keys.sort((a,b) => parseInt(a.split("-")[1]) - parseInt(b.split("-")[1]));
    },
  },
  watch: {
    fontSize(newValue, oldValue) {
      if (!this.hidden && !this.fallbackFontSize)
        this.fallbackFontSize = oldValue
      this.changeInterfaceFontSize()
    },
    csvDelimiter(newValue, oldValue) {
      this.v$.csvDelimiter.$validate()
    },
    theme(newValue, oldValue) {
      if (!this.hidden && !this.fallbackTheme)
        this.fallbackTheme = oldValue
      this.applyThemes();
    },
  },
  mounted() {
    this.$nextTick(() => {
      this.$refs.settingsModal.addEventListener('hide.bs.modal', (e) => {
        // intercept close event via ESC key, ignore if we're recording a shortcut
        if(this.recordingShortcut) {
          e.preventDefault()
        } else {
          // revert settings if closing via ESC
          this.resetUnsavedSettings()
        }
      });

      this.$refs.settingsModal.addEventListener('hidden.bs.modal', (e) => {
        this.password = '';
        this.passwordConfirm = '';
        this.buttonFormDisabled = true;
        this.$refs.passwordConfirm.classList.remove('is-invalid', 'is-valid')
        // workaround for removing validation indicator when the empty form is closed
        setTimeout(function () {
          $('#txt_new_pwd').keydown()
        }, 100);
      });
    })

    this.applyThemes()

    this.$refs.settingsModal.addEventListener("show.bs.modal", () => {
      this.hidden = false
      settingsStore.getSettings();
    });
  },
  methods: {
    changeInterfaceFontSize() {
      document.documentElement.style.fontSize = `${this.fontSize}px`
      refreshHeights();
    },
    applyThemes() {
      if (this.theme === 'dark') {
        settingsStore.setEditorTheme('omnidb_dark')
        settingsStore.setTerminalTheme(dark_terminal_theme)

        document.body.classList.remove('pgmanage-theme--light', 'omnidb--theme-light');
		    document.body.classList.add('pgmanage-theme--dark', 'omnidb--theme-dark');
      } else {
        settingsStore.setEditorTheme('omnidb')
        settingsStore.setTerminalTheme(light_terminal_theme)
        document.body.classList.remove('pgmanage-theme--dark', 'omnidb--theme-dark',);
		    document.body.classList.add('pgmanage-theme--light', 'omnidb--theme-light');
      }

      document.body.setAttribute('data-bs-theme', this.theme);
    },
    saveSettings() {
      if(!this.v$.$invalid) {
        settingsStore.saveSettings().then(() => {
          this.fallbackFontSize = null
          this.fallbackTheme = null
          this.hidden = true
          Modal.getInstance(this.$refs.settingsModal).hide()
        })
      }
    },
    saveUserPassword() {
      if ((this.passwordConfirm != '' || this.password != '') && (this.password != this.passwordConfirm))
        showToast("error", "New Password and Confirm New Password fields do not match.")
      else if ((this.password === this.passwordConfirm) && (this.password.length < 8 && this.password.length >= 1))
        showToast("error", "New Password and Confirm New Password fields must be longer than 8.")
      else {
          axios.post("/save-user-password/", {
            "password": this.password,
          })
          .then(() => {
            Modal.getInstance(this.$refs.settingsModal).hide()
            showToast("success", "Password saved.");
          })
          .catch((error) => {
            handleError(error);
            })
      }
    },
    checkPassword() {
      let password1 = document.getElementById('txt_new_pwd');
      let password2 = document.getElementById('txt_confirm_new_pwd');
      if (password1.checkValidity() && password2.value === password1.value) {
        password2.classList.remove("is-invalid");
        password2.classList.add('is-valid');
        this.buttonFormDisabled = false
      } else if (password2.value.length >= password1.value.length && password2.value !== password1.value) {
        password2.classList.add("is-invalid");
        password2.classList.remove('is-valid');
        this.buttonFormDisabled = true;
      }
      else {
        password2.classList.remove('is-invalid', 'is-valid');
        this.buttonFormDisabled = true;
      }
    },
    validateBinaryPath(binary_path, utilityGroup) {
      axios.post('/validate_binary_path/', {
        binary_path: binary_path,
        utility_group: utilityGroup
      })
        .then((resp) => {
          const binary_paths = Object.entries(resp.data.data)
            .map(([key, value]) => `${key}: ${value}`).join('\n')
          showAlertText(binary_paths)
        })
        .catch((error) => {
          handleError(error);
        })
    },
    selectPigzPath() {
      pickNativePath('select_folder')
        .then((file) => {
          if (file) this.pigzPath = file.path
        })
        .catch((error) => handleError(error))
    },
    resetUnsavedSettings() {
      this.hidden = true
      if (this.fallbackFontSize) {
        this.fontSize = this.fallbackFontSize
        this.fallbackFontSize = null
      }

      if (this.fallbackTheme) {
        this.theme = this.fallbackTheme
        this.fallbackTheme = null
      }
    },
    selectPostgresqlPathForVersion(versionKey) {
      pickNativePath('select_folder')
        .then((file) => {
          if (file) settingsStore.setBinaryPathForVersion(versionKey, file.path);
        })
        .catch((error) => handleError(error));
    },
    setBinaryPathForVersion(versionKey, value) {
      settingsStore.setBinaryPathForVersion(versionKey, value);
    },
    discoverBinaries() {
      axios.get('/discover_binary_paths/')
        .then((resp) => {
          settingsStore.setBinaryPaths(resp.data);
        })
        .catch((error) => {
          handleError(error);
        })
    }
  }
}
</script>
