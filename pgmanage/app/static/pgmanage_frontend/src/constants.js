const requestState = {
  Idle: 0,
  Executing: 1,
  Ready: 2,
};

const tabStatusMap = {
  NOT_CONNECTED: 0,
  IDLE: 1,
  RUNNING: 2,
  IDLE_IN_TRANSACTION: 3,
  IDLE_IN_TRANSACTION_ABORTED: 4,
};

const queryModes = {
  DATA_OPERATION: 0,
  FETCH_MORE: 1,
  FETCH_ALL: 2,
  COMMIT: 3,
  ROLLBACK: 4,
};

const consoleModes = {
  DATA_OPERATION: 0,
  FETCH_MORE: 1,
  FETCH_ALL: 2,
  SKIP_FETCH: 3,
};

const operationModes = {
  CREATE: 0,
  UPDATE: 1,
  DELETE: 2,
};

/// <summary>
/// Transaction codes of client requests.
/// </summary>
const queryRequestCodes = {
  Login: 0,
  Query: 1,
  Execute: 2,
  Script: 3,
  QueryEditData: 4,
  SaveEditData: 5,
  CancelThread: 6,
  Debug: 7,
  CloseTab: 8,
  AdvancedObjectSearch: 9,
  Console: 10,
  Terminal: 11,
  Ping: 12,
  SchemaEditData: 13,
};

/// <summary>
/// Transaction codes of server responses.
/// </summary>
const queryResponseCodes = {
  LoginResult: 0,
  QueryResult: 1,
  QueryEditDataResult: 2,
  SaveEditDataResult: 3,
  SessionMissing: 4,
  PasswordRequired: 5,
  QueryAck: 6,
  MessageException: 7,
  DebugResponse: 8,
  RemoveContext: 9,
  AdvancedObjectSearchResult: 10,
  ConsoleResult: 11,
  TerminalResult: 12,
  Pong: 13,
  OperationCancelled: 14,
  SchemaEditResult: 15,
};

const allowedFileTypes = ["application/sql", "text/csv", "text/plain", "Text"];

const mimeTypeMap = {
  sql: "application/sql",
  csv: "text/csv",
  txt: "text/plain",
};

const colorLabelMap = {
  0: { class: "", name: "neutral" },
  1: { class: "color-label--red", name: "red" },
  2: { class: "color-label--orange", name: "orange" },
  3: { class: "color-label--yellow", name: "yellow" },
  4: { class: "color-label--green", name: "green" },
  5: { class: "color-label--cyan", name: "cyan" },
  6: { class: "color-label--purple", name: "purple" },
  7: { class: "color-label--pink", name: "pink" },
};

const maxFileSizeInMB = 50;

const maxFileSizeInKB = 1024 ** 2 * maxFileSizeInMB;

const maxLinesForIndentSQL = 7 * 1000;

const editorModeMap = {
  postgresql: "pgsql_extended",
  mysql: "mysql_extended",
  mariadb: "mysql_extended",
  oracle: "plsql",
  mssql: "sqlserver",
};

const dataEditorFilterModes = {
  MANUAL: "manual",
  BUILDER: "builder",
};

const dbTechNames = {
  sqlite: 'SQLite3',
  terminal: 'Terminal',
  mysql: 'MySQL',
  mariadb: 'MariaDB',
  postgresql: 'PostgreSQL',
  rdspostgresql: 'RDS Postgresql',
  oracle: 'Oracle',
  mssql: 'SQL Server'
}

const dialectAliases = {
  rdspostgresql: 'postgresql',
}

function dialectOf(technology) {
  return dialectAliases[technology] ?? technology
}

const minFontSize = 10;
const maxFontSize = 20;

//sql-formatter uses 'plsql' for oracle and tsql for mssql sql flavor
//otherwise - our db technology names match perfectly
const sqlFormatterDialectMap = {
  oracle: "plsql",
  mssql: "transactsql"
}

const knexDialectMap = {
  oracle: "oracledb",
  mariadb: "mysql",
  postgresql: "postgres",
  sqlite: "sqlite3",
};

export {
  requestState,
  tabStatusMap,
  queryModes,
  queryRequestCodes,
  queryResponseCodes,
  allowedFileTypes,
  maxFileSizeInMB,
  maxFileSizeInKB,
  maxLinesForIndentSQL,
  mimeTypeMap,
  minFontSize,
  maxFontSize,
  consoleModes,
  colorLabelMap,
  operationModes,
  editorModeMap,
  dataEditorFilterModes,
  dbTechNames,
  dialectOf,
  sqlFormatterDialectMap,
  knexDialectMap,
};
