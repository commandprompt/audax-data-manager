import { defineStore } from "pinia";
import axios from "axios";

const useDbMetadataStore = defineStore("dbMetadata", {
  state: () => ({
    initialized: 'false',
    dbMeta: {},
    databases: {},
  }),
  actions: {
    getDbMeta(conn_id, db_name) {
      if(this.dbMeta[conn_id])
        if(this.dbMeta[conn_id][db_name])
          return this.dbMeta[conn_id][db_name]
    },
    getDatabases(conn_id) {
      return this.databases[conn_id] ?? [];
    },
    async fetchDbMeta(conn_id, workspace_id, db_name, tab_id) {
      if(this.dbMeta[conn_id])
        if(this.dbMeta[conn_id][db_name])
          return
      const meta_response = await axios.post('/get_database_meta/', {
        database_index: conn_id,
        workspace_id: workspace_id,
        database_name: db_name,
        tab_id: tab_id
      })

      if(!this.dbMeta[conn_id])
        this.dbMeta[conn_id] = {}
      this.dbMeta[conn_id][db_name] = meta_response.data.schemas
      this.databases[conn_id] = meta_response.data.databases
      return meta_response
    },
    async refreshDBMeta(conn_id, workspace_id, db_name) {
      const meta_response = await axios.post("/get_database_meta/", {
        database_index: conn_id,
        workspace_id: workspace_id,
        database_name: db_name,
      });

      if (!this.dbMeta[conn_id]) this.dbMeta[conn_id] = {};

      this.dbMeta[conn_id][db_name] = meta_response.data.schemas;
      this.databases[conn_id] = meta_response.data.databases;

      return meta_response;
    },
    deleteDbMeta(conn_id) {
      if (this.dbMeta[conn_id]) {
        delete this.dbMeta[conn_id];
      }
    },
  },
});

export { useDbMetadataStore };
