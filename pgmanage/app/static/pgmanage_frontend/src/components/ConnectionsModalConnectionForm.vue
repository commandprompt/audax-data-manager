<template>
<div v-if="visible" class="col-9 d-flex ms-auto position-relative">
  <div class="modal-connections__forms position-absolute w-100">
    <div class="modal-connections__forms_connection connection-form position-absolute">
        <div class="connection-form__header d-flex justify-content-between align-items-center pb-3">
        <!-- TODO: integrate with active connection list -->
        <div class="d-flex align-items-center">
          <h3 class="connection-form__header_title mb-0">{{initialConnection.alias}} {{connectionLocal.locked ? "(Active/Read Only)": ""}}</h3>
          <button type="button"
            class="btn dropdown-toggle ms-3 color-picker__btn"
            :class='colorLabelPickerClass'
            title="Color Label"
            data-bs-toggle="dropdown"></button>
          <div class="dropdown-menu dropdown-menu-sm color-picker__dropdown">
            <a v-for="(label, index) in colorLabelMap"
              class="dropdown-item"
              @click="setColorLabel(index)"
              :class="label.class"
              :key=index
              :value="index">
                <p class="d-flex align-items-center">
                  <span class="d-inline-block me-2"></span>
                  {{label.name}}
                </p>
            </a>
          </div>
        </div>
          <div>
            <button @click="testConnection(this.connectionLocal)" class="btn btn-outline-primary me-2" id="connectionTestButton" :disabled="testIsRunning">
              <template v-if="testIsRunning">
                <span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                <span>Testing...</span>
                </template>
              <span v-else>Test</span>
            </button>
            <button v-if="this.connectionLocal.id" @click="selectConnection(this.connectionLocal.id)" class="btn btn-success">Connect</button>
          </div>
        </div>

        <form autocomplete="off">
          <div class="row mt-3">
            <div class="form-group col-6 position-relative">
              <label for="connectionName" class="fw-bold mb-2">Name</label>
              <input v-model="connectionLocal.alias" type="text"
                :class="['form-control', { 'is-invalid': v$.connectionLocal.alias.$invalid }]" id="connectionName" placeholder="Connection name">
              <div class="invalid-feedback">
                <span v-for="error of v$.connectionLocal.alias.$errors" :key="error.$uid">
                  {{ error.$message }}
                </span>
              </div>
            </div>
            <div class="form-group col-3 position-relative">
              <label for="connectionType" class="fw-bold mb-2">Type</label>
              <select v-model="connectionLocal.technology" @change="handleTypeChange" id="connectionType" class="form-select" placeholder="Connection type">
                  <option disabled>Choose...</option>
                  <option v-for="(technology, index) in technologies"
                    :key=index
                    :value="technology">
                      {{ techName(technology) }}
                  </option>
              </select>
            </div>
            <div class="form-group col-3 position-relative">
              <label for="connectionGroup" class="fw-bold mb-2">Group</label>
              <select v-model="connectionLocal.group" id="connectionGroup" class="form-select" placeholder="Connection group">
                  <option value=""></option>
                  <option v-for="(group, index) in connectionGroups"
                    :key=index
                    :value="group.id">
                      {{group.name}}
                  </option>
              </select>
            </div>
          </div>

          <div class="row">
            <div class="form-group col-6 position-relative">
              <label for="connectionName" class="fw-bold mb-2">Server</label>
              <input v-model="connectionLocal.server" type="text" class="form-control" id="connectionServer"
                :class="['form-control', { 'is-invalid': v$.connectionLocal.server.$invalid }]"
                :placeholder="placeholder.server"
                :disabled="dbFormDisabled">
                <div class="invalid-feedback">
                  <span class="me-2" v-for="error of v$.connectionLocal.server.$errors" :key="error.$uid">
                    {{ error.$message }}
                  </span>
                </div>
            </div>

            <div class="form-group col-3">
              <label for="connectionPort" class="fw-bold mb-2">Port</label>
              <input v-model="connectionLocal.port" type="text" class="form-control" id="connectionPort"
                :class="['form-control', { 'is-invalid': v$.connectionLocal.port.$invalid }]"
                :placeholder="placeholder.port"
                :disabled="dbFormDisabled">
                <div class="invalid-feedback">
                  <span v-for="error of v$.connectionLocal.port.$errors" :key="error.$uid">
                    {{ error.$message }}
                  </span>
                </div>
            </div>

            <div class="form-group col-3">
              <label for="connectionSSL" class="fw-bold mb-2">SSL</label>
                <select v-if="isPostgresFamily" id="connectionSSL" class="form-select" v-model="connectionLocal.connection_params.sslmode" :disabled="dbFormDisabled">
                    <option v-for="mode in sslModes" :key="mode" :value="mode">{{ mode }}</option>
                </select>
                <select v-else-if="connectionLocal.technology === 'mssql'" id="connectionSSL" class="form-select" v-model="connectionLocal.connection_params.encryption" :disabled="dbFormDisabled">
                    <option v-for="mode in sslModes" :key="mode" :value="mode">{{ mode }}</option>
                </select>
                <select v-else-if="connectionLocal.technology === 'oracle'" id="connectionSSL" class="form-select" v-model="connectionLocal.connection_params.protocol" :disabled="dbFormDisabled">
                    <option v-for="mode in sslModes" :key="mode" :value="mode">{{ mode }}</option>
                </select>

                <select v-else id="connectionSSL" class="form-select" :value='tempMode' @change="changeSelect" :disabled="dbFormDisabled">
                    <option v-for="mode in sslModes" :key="mode.text" :value="mode.value">{{ mode.text }}</option>
                </select>
            </div>
          </div>

          <div class="row">
            <div class="form-group col-6">
              <label for="connectionDatabase" class="fw-bold mb-2">Database</label>
              <input v-model="connectionLocal.service" type="text" class="form-control" id="connectionDatabase"
                :class="['form-control', { 'is-invalid': v$.connectionLocal.service.$invalid }]"
                :placeholder="placeholder.service"
                :disabled="connectionLocal.technology==='terminal' || !!connectionLocal?.conn_string?.length">
                <div class="invalid-feedback">
                  <span v-for="error of v$.connectionLocal.service.$errors" :key="error.$uid">
                    {{ error.$message }}
                  </span>
                </div>
            </div>

            <div class="form-group col-3">
              <label for="connectionUsername" class="fw-bold mb-2">Username</label>
              <input v-model="connectionLocal.user"
                type="text" class="form-control" id="connectionUsername" autocomplete="new-password"
                :class="['form-control', { 'is-invalid': v$.connectionLocal.user.$invalid }]"
                :placeholder="placeholder.user"
                :disabled="dbFormDisabled">
                <div class="invalid-feedback">
                  <span v-for="error of v$.connectionLocal.user.$errors" :key="error.$uid">
                    {{ error.$message }}
                  </span>
                </div>
            </div>
            <div class="form-group col-3">
              <label for="connectionPassword" class="fw-bold mb-2">Password</label>
              <div class="position-relative">
                <input v-model="connectionLocal.password"
                  type="password" class="form-control" id="connectionPassword" autocomplete="new-password"
                  :placeholder="this.connectionLocal.password_set ? '••••••••' : ''"
                  :disabled="dbFormDisabled || iamAuthInUse">
                <a v-if="this.connectionLocal.password_set || this.connectionLocal.password?.length > 0"
                  @click.prevent="this.connectionLocal.password_set = false; this.connectionLocal.password = ''"
                  class="btn btn-icon btn-icon-danger position-absolute input-clear-btn"><i class="fas fa-circle-xmark"></i></a>
              </div>
            </div>
          </div>

          <div v-if="isRdsPostgresql" class="row mt-3">
            <div class="form-group col-3">
              <label for="awsRegion" class="fw-bold mb-2">AWS Region</label>
              <input v-model="connectionLocal.credentials_extra.aws_region"
                type="text" class="form-control" id="awsRegion" placeholder="ex: us-east-1"
                :disabled="dbFormDisabled || passwordAuthInUse">
            </div>
            <div class="form-group col-3">
              <label for="accessKeyId" class="fw-bold mb-2">Access Key ID</label>
              <input v-model="connectionLocal.credentials_extra.access_key_id"
                type="password" class="form-control" id="accessKeyId" autocomplete="new-password"
                :disabled="dbFormDisabled || passwordAuthInUse">
            </div>
            <div class="form-group col-3">
              <label for="secretAccessKey" class="fw-bold mb-2">Secret Access Key</label>
              <input v-model="connectionLocal.credentials_extra.secret_access_key"
                type="password" class="form-control" id="secretAccessKey" autocomplete="new-password"
                :disabled="dbFormDisabled || passwordAuthInUse">
            </div>
          </div>

          <div class="connection-form__divider d-flex align-items-center my-3">
              <span class="connection-form__divider_text">OR</span>
          </div>

          <div class="form-group">
            <label for="connectionSring" class="fw-bold mb-2">Use a connection string</label>
            <input v-model="connectionLocal.conn_string" @input="clearPort" type="text" class="form-control" id="connectionSring"
              :class="['form-control', { 'is-invalid': v$.connectionLocal.conn_string.$invalid }]"
              :placeholder="placeholder.conn_string"
              :disabled="connStringDisabled">
              <div class="invalid-feedback">
                <span v-for="error of v$.connectionLocal.user.$errors" :key="error.$uid">
                  {{ error.$message }}
                </span>
              </div>
          </div>

          <div class="form-check form-switch mb-3">
            <input v-model="connectionLocal.tunnel.enabled" @change="scrollToTunnel" type="checkbox" class="form-check-input" id="sshTunel" data-bs-toggle="collapse" data-target="#sshSettings" :disabled="connectionLocal.technology==='terminal'">
            <label class="form-check-label fw-bold" for="sshTunel">Use SSH tunnel</label>
          </div>

          <div id="sshSettings" :class="(connectionLocal.tunnel.enabled) ? 'collapse show':'collapse'">
            <div class="row">
              <div class="form-group col-6">
                <label for="sshServer" class="fw-bold mb-2">SSH Server</label>
                <input v-model="connectionLocal.tunnel.server"
                  :class="['form-control', { 'is-invalid': v$.connectionLocal.tunnel.server.$invalid }]"
                  type="text" id="sshServer" placeholder="SSH Server">
                <div class="invalid-feedback">
                  <span v-for="error of v$.connectionLocal.tunnel.server.$errors" :key="error.$uid">
                    {{ error.$message }}
                  </span>
                </div>
              </div>

              <div class="form-group col-3">
                <label for="sshPort" class="fw-bold mb-2">SSH Port</label>
                <input v-model="connectionLocal.tunnel.port"
                  :class="['form-control', { 'is-invalid': v$.connectionLocal.tunnel.port.$invalid }]"
                  type="text" class="form-control" id="sshPort" placeholder="SSH Port">
                <div class="invalid-feedback">
                  <span v-for="error of v$.connectionLocal.tunnel.port.$errors" :key="error.$uid">
                    {{ error.$message }}
                  </span>
                </div>
              </div>

              <div class="form-group col-3">
                <label for="sshUsername" class="fw-bold mb-2">SSH Username</label>
                <input v-model="connectionLocal.tunnel.user"
                  :class="['form-control', { 'is-invalid': v$.connectionLocal.tunnel.user.$invalid }]"
                  type="text" class="form-control" id="sshUsername" placeholder="SSH Username">
                <div class="invalid-feedback">
                  <span v-for="error of v$.connectionLocal.tunnel.user.$errors" :key="error.$uid">
                    {{ error.$message }}
                  </span>
                </div>
              </div>
            </div>

            <div class="row">
              <div class="form-group col-6">
                <label for="sshPassphrase" class="fw-bold mb-2">{{sshPassLabel}}</label>
                <div class="position-relative">
                    <input v-model="connectionLocal.tunnel.password"
                      :placeholder="this.connectionLocal.tunnel.password_set ? '••••••••' : ''" type="password" class="form-control"
                      id="sshPassphrase">
                    <a v-if="this.connectionLocal.tunnel.password_set || this.connectionLocal?.tunnel?.password?.length > 0"
                    @click="this.connectionLocal.tunnel.password_set = false; this.connectionLocal.tunnel.password = ''"
                  class="btn btn-icon btn-icon-danger position-absolute input-clear-btn"><i class="fas fa-circle-xmark"></i></a>
                </div>
              </div>

              <div class="form-group col-6">
                <p class="fw-bold mb-2">SSH Key</p>
                <label class="btn btn-secondary" id="sshFileLabel">
                {{connectionLocal.tunnel.key || connectionLocal.tunnel.key_set ? 'Key File Loaded' : 'Select Key' }} <input type="file" @change="updateConnectionKey" ref="keyFile" hidden>
                </label>
                <button
                  v-if="this.connectionLocal.tunnel.key_set || this.connectionLocal.tunnel.key != ''"
                  @click="this.connectionLocal.tunnel.key_set = false; this.connectionLocal.tunnel.key = ''; this.$refs.keyFile.value = ''"
                  class="btn btn-outline-danger ms-2">Clear
                </button>
              </div>
            </div>
          </div>
        </form>
    </div>
  </div>
  <div class="modal-footer mt-auto justify-content-between w-100">
    <ConfirmableButton v-if="connectionLocal.id" :callbackFunc="deleteConnection" class="btn btn-outline-danger" />
    <button v-if="connectionLocal.id"
      type="button"
      @click="$emit('connection:clone', this.connectionLocal)"
      class="btn btn-ghost btn-ghost-secondary">Clone</button>
    <button type="button"
      @click="trySave()"
      :disabled="connectionLocal.locked || v$.$invalid || (!isChanged && !!connectionLocal.id)"
      class="btn btn-primary ms-auto">Save changes</button>
  </div>
</div>
</template>


<script>
import { useVuelidate } from '@vuelidate/core'
import { required, between, maxLength, helpers } from '@vuelidate/validators'
import { connectionsStore, messageModalStore } from '../stores/stores_initializer';
import { colorLabelMap } from '../constants'
import ConfirmableButton from './ConfirmableButton.vue'
import isEqual from 'lodash/isEqual';
import isEmpty from 'lodash/isEmpty';
import { showToast } from '../notification_control';
import { Modal } from 'bootstrap';
import { handleError } from '../logging/utils';
import { dbTechNames } from '../constants'

  export default {
    name: 'ConnectionsModalConnectionForm',
    components: {
      ConfirmableButton
    },
    emits: [
      "connection:change",
      "connection:save",
      "connection:delete",
      "connection:clone",
    ],
    data() {
      return {
        connectionLocal: {
          alias: '',
          color_label: 0
        },
        postgresql_ssl_modes: ["allow", "prefer", "require", "disable", "verify-full", "verify-ca"],
        mssql_encryption_modes: ['off', 'request', 'require'],
        mysql_mariadb_modes: [
          { text: 'disable', value: 'ssl_disabled'},
          { text: 'require', value: 'ssl' },
          { text: 'verify certificate', value: "ssl_verify_cert" },
          { text: 'verify server identity', value: "ssl_verify_identity" }],
        oracle_modes: ['tcp', 'tcps'],
        tempMode: "ssl",
        testIsRunning: false,
      }
    },
    created() {
      this.colorLabelMap = colorLabelMap
    },
    validations() {
      const needsServer = !['terminal', 'sqlite'].includes(this.connectionLocal.technology)
      const needsTunnel = this.connectionLocal.technology === 'terminal' || (this.connectionLocal.tunnel && this.connectionLocal.tunnel.enabled)
      const hostOrIp = function(value) {
        const hostre = /^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])$/
        const ipv4re = /^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$/
        // yes, this one is pretty long and cannot be easily made multi-line without extra tricks
        const ipv6re = /^(([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|:((:[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|::(ffff(:0{1,4}){0,1}:){0,1}((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])|([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9]))$/
        // absolute paths without .. . and ~
        const pathre = /^\/$|(^(?=\/))(\/(?=[^/\0])[^/\0]+)*\/?$/

        if(['mariadb', 'mysql'].includes(this.connectionLocal.technology)) {
          return ipv4re.test(value) || ipv6re.test(value) || hostre.test(value) || pathre.test(value)
        }else if (this.isPostgresFamily){
          return ipv4re.test(value) || ipv6re.test(value) || hostre.test(value) || pathre.test(value) || !helpers.req(value)
        } else {
          return ipv4re.test(value) || ipv6re.test(value) || hostre.test(value)
        }
      }

      let baseRules = {
        connectionLocal: {
          alias: {
            required: required,
            maxLength: maxLength(30),
          },
          technology: {
            required,
          },
          server: {},
          port: {},
          service: {},
          user: {},
          conn_string: {},
          tunnel: {
            user: {},
            server: {},
            port: {}
          }
        }
      }

      if(needsServer) {
        if(!this.connectionLocal.conn_string) {
          if(['postgresql', 'rdspostgresql', 'mariadb', 'mysql'].includes(this.connectionLocal.technology)){
            baseRules.connectionLocal.server = {
              hostOrIp: helpers.withMessage('Must be a valid hostname, IP or a UNIX socket base path', hostOrIp)
            }
          } else {
            baseRules.connectionLocal.server = {
              required,
              hostOrIp: helpers.withMessage('Must be a valid hostname or IP', hostOrIp)
            }
          }

          baseRules.connectionLocal.port = {
            required,
            between: between(1,65535),
          }

          baseRules.connectionLocal.service = {
            required,
          }

          baseRules.connectionLocal.user = {
            required,
          }

        } else {
          baseRules.connectionLocal.conn_string = {
            required,
          }
        }
      }

      if(this.connectionLocal.technology === 'sqlite') {
        baseRules.connectionLocal.service = {
          required,
        }
      }

      if(needsTunnel) {
        baseRules.connectionLocal.tunnel.server = {
          required,
        },
        baseRules.connectionLocal.tunnel.port = {
          required,
          between: between(1,65535),
        },
        baseRules.connectionLocal.tunnel.user = {
          required,
        }
      }

      return baseRules;
    },
    setup() {
      return { v$: useVuelidate({ $lazy: true, $autoDirty: true }) }
    },
    props: {
      visible: Boolean,
      initialConnection: {
        type: Object,
        required: true,
        default: {
          id: null,
          alias: 'New Connection',
          locked: false,
          public: false,
          is_mine: true,
          technology: 'postgresql',
          group: null,
          conn_string: "",
          server: "",
          port: "5432",
          service: "",
          user: "",
          password: "",
          password_set: false,
          tunnel: {
            enabled: false,
            server: "",
            port: "",
            user: "",
            password: "",
            password_set: false,
            key: "",
            key_set: false
          },
          connection_params: {
            sslmode: "prefer"
          },
          credentials_extra: {},
          color_label: 0
        }
      },
      technologies: Array,
    },
    computed: {
      isPostgresFamily() {
        return ['postgresql', 'rdspostgresql'].includes(this.connectionLocal.technology)
      },
      isRdsPostgresql() {
        return this.connectionLocal.technology === 'rdspostgresql'
      },
      iamAuthInUse() {
        if (!this.isRdsPostgresql) return false
        const credentials = this.connectionLocal.credentials_extra ?? {}
        return ['aws_region', 'access_key_id', 'secret_access_key']
          .some((name) => !!credentials[name]?.length)
      },
      passwordAuthInUse() {
        return this.connectionLocal.password_set || !!this.connectionLocal.password?.length
      },
      colorLabelPickerClass() {
        return colorLabelMap[this.connectionLocal.color_label || 0].class
      },
      placeholder() {
        const placeholderMap = {
          'postgresql': {
            'server': 'ex: host or UNIX socket basedir, blank for default basedir',
            'port': 'ex: 5432',
            'service': 'ex: postgres',
            'user': 'ex: postgres',
            'conn_string': 'ex: postgresql://postgres@localhost:5432/postgres'
          },
          'rdspostgresql': {
            'server': 'ex: mydb.abc123.us-east-1.rds.amazonaws.com',
            'port': 'ex: 5432',
            'service': 'ex: postgres',
            'user': 'ex: postgres',
            'conn_string': 'ex: postgresql://postgres@mydb.abc123.us-east-1.rds.amazonaws.com:5432/postgres'
          },
          'mysql': {
            'server': 'ex: host or absolute UNIX socket path',
            'port': 'ex: 3306',
            'service': 'ex: db',
            'user': 'ex: root',
            'conn_string': 'ex: mysql://root@localhost:3306/db'
          },
          'mariadb': {
            'server': 'ex: host or absolute UNIX socket path',
            'port': 'ex: 3306',
            'service': 'ex: db',
            'user': 'ex: root',
            'conn_string': 'ex: mysql://root@localhost:3306/db'
          },
          'oracle': {
            'server': 'ex: 127.0.0.1',
            'port': 'ex: 1521',
            'service': 'ex: xe',
            'user': 'ex: system',
            'conn_string': 'ex: oracle://system@localhost:1521/xe'
          },
          'sqlite': {
            'server': '',
            'port': '',
            'service': 'ex: /home/user/sqlite_file.db',
            'user': '',
            'conn_string': ''
          },
          'terminal': {
            'server': '',
            'port': '',
            'service': '',
            'user': '',
            'conn_string': ''
          },
          'mssql': {
            'server': 'ex: 127.0.0.1',
            'port': 'ex: 1433',
            'service': 'ex: master',
            'user': 'ex: sa',
            'conn_string': 'ex: mssql://sa@localhost:1433/master'
          },
        }
        let current_db = this.connectionLocal.technology || 'postgresql'
        return placeholderMap[current_db]
      },
      dbFormDisabled() {
        return ['sqlite', 'terminal'].includes(this.connectionLocal.technology) || !!this.connectionLocal?.conn_string?.length
      },
      connStringDisabled() {
        return (!!this.connectionLocal.server ||
        !!this.connectionLocal.user ||
        !!this.connectionLocal.password ||
        !!this.connectionLocal.service ||
        ['terminal', 'sqlite'].includes(this.connectionLocal.technology))
      },
      sslModes() {
        if (this.isPostgresFamily) {
          return this.postgresql_ssl_modes
        } else if (this.connectionLocal.technology === 'oracle') {
          return this.oracle_modes
        } else if (['mysql', 'mariadb'].includes(this.connectionLocal.technology)) {
          return this.mysql_mariadb_modes
        } else if (this.connectionLocal.technology === 'mssql') {
          return this.mssql_encryption_modes
        } else {
          return []
        }
      },
      connectionGroups() {
        return connectionsStore.groups
      },
      sshPassLabel() {
        return this.connectionLocal.tunnel.key_set ? 'SSH Key Passphrase' : 'SSH Password'
      },
      isChanged() {
        return !isEmpty(this.initialConnection) && !isEqual(this.connectionLocal, this.initialConnection)
      }
    },
    methods: {
      changeSelect(e){
        const value = e.target.value;
        if (value === 'ssl'){
          this.connectionLocal.connection_params = {"ssl": {"ssl": true}}
        } else {
          this.connectionLocal.connection_params = {[value]: true}
        }
        this.tempMode = value;
      },
      clearPort() {
        this.connectionLocal.port = ''
      },
      reset() {
        this.connectionLocal = JSON.parse(JSON.stringify(this.initialConnection));
        this.v$.connectionLocal.$reset()
      },
      selectConnection(conn_id) {
        if (this.isChanged) {
          messageModalStore.showModal(
          "Are you sure you wish to discard the current changes?",
          () => {
            this.reset();
            this.$nextTick(() => {
              Modal.getOrCreateInstance('#connections-modal').hide();
              connectionsStore.selectConnection(conn_id);
            });
          },
          null
        );
        } else {
          Modal.getOrCreateInstance('#connections-modal').hide()
          connectionsStore.selectConnection(conn_id)
        }
      },
      setColorLabel(val) {
        // without timeout bootstrap dropdown fails to close
        setTimeout(() => {this.connectionLocal.color_label = val}, 100)
      },
      trySave() {
        this.v$.connectionLocal.$validate()
        if(!this.v$.$invalid) {
          this.$emit('connection:save', this.connectionLocal)
        }
      },
      testConnection(connection) {
        this.v$.connectionLocal.$validate()
        if(!this.v$.$invalid) {
          this.testIsRunning = true
          connectionsStore.testConnection(connection)
          .then((response) => {
            showToast("success", response.data.data)
            this.testIsRunning = false;
          })
          .catch((error) => {
            this.testIsRunning = false;
            handleError(error);
          })
        }
      },
      techName(technology) {
        return dbTechNames[technology]
      },
      updateConnectionKey(event) {
        let file = (event.target.files) ? event.target.files[0] : false;
        let reader = new FileReader();
        reader.onload = (e) => { this.connectionLocal.tunnel.key = e.target.result; };
        reader.readAsText(file);
      },
      handleTypeChange(event) {
        let technology = event.target.value
        this.connectionLocal.credentials_extra = {}
        switch(technology) {
          case 'terminal':
            // erase db fields
            this.connectionLocal.server = ''
            this.connectionLocal.service = ''
            this.connectionLocal.user = ''
            this.connectionLocal.password = ''
            // open ssh subform
            this.connectionLocal.tunnel.enabled = true
            setTimeout(this.scrollToTunnel,10)
            break

          case 'sqlite':
            this.connectionLocal.server = ''
            this.connectionLocal.user = ''
            this.connectionLocal.password = ''
            break

          case 'postgresql':
          case 'rdspostgresql':
            this.connectionLocal.connection_params =  {sslmode: 'prefer'}
            break

          case 'mariadb':
          case 'mysql':
            this.connectionLocal.connection_params = {'ssl': {'ssl': true}}
            this.tempMode = 'ssl'
            break

          case 'oracle':
            this.connectionLocal.connection_params = {protocol: "tcps"}
            break
          
          case 'mssql':
            this.connectionLocal.connection_params = { encryption: 'request' }
            break
        }
        this.connectionLocal.port = this.placeholder.port.replace('ex: ','')
      },
      scrollToTunnel(){
        // scroll the tunnel form into viewport if tunnel was enabled
        if(this.connectionLocal.tunnel.enabled) {
          document.getElementById('sshSettings').scrollIntoView()
        }
      },
      deleteConnection() {
        this.$emit('connection:delete', this.connectionLocal)
      }
    },
    watch: {
      initialConnection: {
        handler(newVal, oldVal) {
          this.connectionLocal = JSON.parse(JSON.stringify(newVal));
          this.connectionLocal.tunnel = {...newVal.tunnel};
          this.v$.connectionLocal.$reset();
        },
        deep: true
      },
      isChanged(value) {
        this.$emit("connection:change", value);
      },
    }
  }
</script>