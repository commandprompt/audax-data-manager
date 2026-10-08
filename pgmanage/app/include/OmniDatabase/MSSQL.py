import re
from enum import Enum
from urllib.parse import urlparse

import app.include.Spartacus as Spartacus
from app.include.OmniDatabase.sql_templates import get_template
from sqlparse import format as sql_format


class TemplateType(Enum):
    EXECUTE = 1
    SCRIPT = 2


class Template:
    def __init__(self, text, template_type=TemplateType.EXECUTE):
        self.text = text
        self.type = template_type


class MSSQL:
    def __init__(self, server, port, service, user, password, conn_id, alias, conn_string='', parse_conn_string = False, connection_params = None):
        self.lock = None
        self.connection_params = connection_params if connection_params else {}
        self.alias = alias
        self.db_type = "mssql"
        self.conn_string = ""
        self.conn_string_error = ""
        self.password = password
        self.conn_id = conn_id

        self.server = server
        self.active_server = server
        self.user = user
        self.active_user = user
        self.schema = service
        self.service = service
        self.active_service = service

        self.port = port

        if port is None or port == "":
            self.active_port = "1433"
        else:
            self.active_port = port

        #try to get info from connection string
        # FIXME: move connection string parsing into some common place
        if conn_string!='' and parse_conn_string:
            try:
                parsed = urlparse(conn_string)
                if parsed.port!=None:
                    self.active_port = str(parsed.port)
                if parsed.hostname!=None:
                    self.active_server = parsed.hostname
                if parsed.username!=None:
                    self.active_user = parsed.username
                if parsed.password!=None and password == '':
                    self.password = parsed.password
                if parsed.query!=None:
                    self.conn_string_query = parsed.query
                parsed_database = parsed.path
                if len(parsed_database)>1:
                    self.active_service = parsed_database[1:]
            except Exception as exc:
                # FIXME: this is naiive since urlparse rarely returns any exceptions for weird strings
                self.conn_string_error = 'Syntax error in the connection string.'

        self.connection = Spartacus.Database.MSSQL(
            self.active_server,
            self.active_port,
            self.active_service,
            self.active_user,
            self.password,
            connection_params=self.connection_params,
        )
        self.has_schema = True

        self.console_help = "Console tab. Type the commands in the editor below this box."

        self.use_server_cursor = False

        self._version = None
        self._major_version = None

    @property
    def version(self):
        if self._version is None:
            self._fetch_version()
        return self._version

    @property
    def major_version(self):
        if self._major_version is None:
            self._fetch_version()
        return self._major_version

    # Decorator to acquire lock before performing action
    def lock_required(function):
        def wrap(self, *args, **kwargs):
            try:
                if self.lock != None:
                    self.lock.acquire()
            except:
                None
            try:
                r = function(self, *args, **kwargs)
            except:
                try:
                    if self.lock != None:
                        self.lock.release()
                except:
                    None
                raise
            try:
                if self.lock != None:
                    self.lock.release()
            except:
                None
            return r

        wrap.__doc__ = function.__doc__
        wrap.__name__ = function.__name__
        return wrap

    def _fetch_version(self):
        try:
            self._version = self.ExecuteScalar("SELECT CAST(SERVERPROPERTY('productversion') AS VARCHAR);")
            self._major_version = self.ExecuteScalar("SELECT CAST(SERVERPROPERTY('ProductMajorVersion') AS INT);")
        except Exception:
            self._version = None
            self._major_version = None

    def GetVersion(self):
        return f"MSSQL {self.version}"

    def PrintDatabaseDetails(self):
        return self.active_server + ":" + self.active_port

    def PrintDatabaseInfo(self):
        return self.active_user + "@" + self.active_service

    @lock_required
    def TestConnection(self):
        message = ""
        status = False
        if self.conn_string and self.conn_string_error!='':
            return self.conn_string_error, status

        try:
            self.connection.Open()
            self.connection.Close()
            message = "Connection successful."
            status = True
        except Exception as exc:
            message = str(exc)
        return message, status

    def GetErrorPosition(self, error_message, sql_cmd):
        ret = None
        try:
            err_token = re.search(".*near '(.*)'.*", error_message).group(1)
            if err_token:
                row = sql_cmd.count("\n", 0, sql_cmd.find(err_token)) + 1
                ret = {"row": row, "col": 0}
        except AttributeError:
            pass

        return ret

    @lock_required
    def Query(self, sql, alltypesstr=False, simple=False):
        return self.connection.Query(sql, alltypesstr, simple)

    @lock_required
    def ExecuteScalar(self, sql):
        return self.connection.ExecuteScalar(sql)

    @lock_required
    def Execute(self, sql):
        return self.connection.Execute(sql)

    def QueryDatabases(self):
        return self.Query(
            """SELECT name, database_id
FROM sys.databases; """,
            True,
            True,
        )

    def QuerySchemas(self):
        return self.Query(
            """
 SELECT schema_name
      FROM INFORMATION_SCHEMA.SCHEMATA
      ORDER BY schema_name
"""
        )

    def QueryTables(self, all_schemas=False, schema=None):
        query_filter = ""
        if not all_schemas:
            query_filter = f"AND table_schema = '{schema or self.schema}'"
        return self.Query(
            """
            SELECT table_name,
                   table_schema
            FROM information_schema.tables
            WHERE table_type != 'VIEW'
            {0}
        """.format(
                query_filter
            ),
            True,
        )

    def QueryTablesFields(self, table=None, all_schemas=False, schema=None):
        query_filter = ""

        if table:
            if schema:
                query_filter = (
                    f"WHERE s.name = '{schema}' "
                    f"AND tbl.name = '{table}'"
                )
            else:
                query_filter = f"WHERE tbl.name = '{table}'"

        elif schema and not all_schemas:
            query_filter = f"WHERE s.name = '{schema}'"
    
        return self.Query(
            """
SELECT 
    s.name       AS schema_name,
    tbl.name     AS table_name,
    c.name       AS column_name,
    t.name       AS data_type,
    c.max_length,
    c.precision,
    c.scale,
    c.is_nullable,
    c.is_identity
FROM sys.columns c
JOIN sys.types t ON c.user_type_id = t.user_type_id
JOIN sys.tables tbl
    ON c.object_id = tbl.object_id
JOIN sys.schemas s
    ON tbl.schema_id = s.schema_id
{0}
ORDER BY s.name, tbl.name, c.column_id;
""".format(
                query_filter
            ),
            True,
        )

    def QueryTablesStatistics(self, table=None, all_schemas=False, schema=None):
        query_filter = ""
        if not all_schemas:
            table_filter_part = f"AND t.name = '{table}' " if table else " "
            schema_filter_part = f"AND s.name = '{schema or self.schema}' "
            query_filter += table_filter_part + schema_filter_part
        else:
            query_filter = f"AND t.name = '{table}'" if table else ""

        return self.Query(
            """
SELECT 
    s.name AS schema_name,
    t.name AS table_name,
    st.name AS statistic_name
FROM sys.stats st
JOIN sys.tables t 
    ON st.object_id = t.object_id
JOIN sys.schemas s 
    ON t.schema_id = s.schema_id
WHERE 1=1
        {0}
        
""".format(
                query_filter
            ),
            True,
        )

    def QueryViews(self, all_schemas=False, schema=None):
        query_filter = ""
        if not all_schemas:
            query_filter = f"WHERE table_schema = '{schema or self.schema}'"
        return self.Query(
            """
            SELECT table_name
FROM INFORMATION_SCHEMA.VIEWS
{0}
ORDER BY table_name;
        """.format(
                query_filter
            ),
            True,
        )

    def QueryViewFields(self, table=None, all_schemas=False, schema=None):
        query_filter = f"WHERE c.object_id = OBJECT_ID('{schema}.{table}')"
        return self.Query(
            """
SELECT 
    c.name       AS column_name,
    t.name       AS data_type,
    c.max_length,
    c.precision,
    c.scale,
    c.is_nullable,
    c.is_identity
FROM sys.columns c
JOIN sys.types t ON c.user_type_id = t.user_type_id
{0}
ORDER BY c.column_id;
""".format(
                query_filter
            ),
            True,
        )

    def QueryProcedures(self, all_schemas=False, schema=None):
        query_filter = ""
        if not all_schemas:
            query_filter = f"WHERE s.name = '{schema or self.schema}'"
        return self.Query(
            """
SELECT p.name, p.object_id
FROM sys.procedures p
JOIN sys.schemas s ON p.schema_id = s.schema_id
{0}
ORDER BY s.name, p.name;
""".format(
                query_filter
            ),
            True,
        )

    def QueryFunctionFields(self, function, schema):
        query_filter = f"WHERE specific_schema = '{schema or self.schema}' AND specific_name = '{function}'"
        return self.Query(
            """
            SELECT parameter_name,
            data_type,
            CASE parameter_mode
                WHEN 'OUT' THEN 'O'
                WHEN 'INOUT' THEN 'X'
                ELSE 'I'
            END AS param_type
FROM INFORMATION_SCHEMA.PARAMETERS
                          {0}
ORDER BY ORDINAL_POSITION;
""".format(
                query_filter
            ),
            True,
        )

    def QueryFunctions(self, all_schemas=False, schema=None):
        query_filter = ""
        if not all_schemas:
            query_filter = f"AND routine_schema = '{schema or self.schema}'"
        return self.Query(
            """
SELECT routine_name
FROM INFORMATION_SCHEMA.ROUTINES
WHERE routine_type = 'FUNCTION'
{}
ORDER BY routine_name;
""".format(
                query_filter
            )
        )

    def QueryTablesPrimaryKeys(self, table=None, all_schemas=False, schema=None):
        query_filter = ""

        if not all_schemas:
            table_filter_part = f"AND table_name = '{table}' " if table else " "
            schema_filter_part = f"AND table_schema = '{schema or self.schema}'"
            query_filter += table_filter_part + schema_filter_part
        else:
            query_filter = f"AND table_name = '{table}'" if table else ""

        return self.Query(
            """

SELECT table_schema,
       table_name,
       constraint_name
FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS 
WHERE constraint_type = 'PRIMARY KEY'
        {0}
ORDER BY table_schema, table_name;
""".format(
                query_filter
            )
        )

    def QueryTablesPrimaryKeysColumns(self, pkey, table=None, all_schemas=False, schema=None):
        query_filter = ""
        if not all_schemas:
            table_filter_part = f"AND kc.table_name = '{table}' " if table else " "
            schema_filter_part = f"AND kc.table_schema = '{schema or self.schema}' "
            query_filter += table_filter_part + schema_filter_part
        else:
            query_filter = f"AND kc.table_name = '{table}'" if table else ""

        query_filter = query_filter + f"AND kc.constraint_name = '{pkey}' "
        return self.Query(
            """
            SELECT kc.table_schema,
       kc.table_name,
       kc.constraint_name,
       kc.column_name,
       kc.ordinal_position
FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE kc
JOIN INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
  ON kc.constraint_name = tc.constraint_name
  AND kc.table_schema = tc.table_schema
WHERE tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
  {0}
ORDER BY kc.table_schema, kc.table_name, kc.ordinal_position;
        """.format(
                query_filter
            ),
            True,
        )

    def QueryTablesForeignKeys(self, table=None, all_schemas=False, schema=None):
        query_filter = ""

        if not all_schemas:
            table_filter_part = f"AND fk.table_name = '{table}' " if table else " "
            schema_filter_part = f"AND fk.table_schema = '{schema or self.schema}'"
            query_filter += table_filter_part + schema_filter_part
        else:
            query_filter = f"AND fk.table_name = '{table}'" if table else ""

        return self.Query(
            """
SELECT 
    fk.table_schema,
    fk.table_name,
    fk.constraint_name,
    fk.column_name,
    pk.table_schema AS r_table_schema,
    pk.table_name   AS r_table_name,
    pk.column_name  AS r_column_name,
    rc.unique_constraint_name AS r_constraint_name,
    rc.update_rule,
    rc.delete_rule
FROM INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS rc
JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE fk
    ON rc.constraint_name = fk.constraint_name
    AND rc.constraint_schema = fk.constraint_schema
JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE pk
    ON rc.unique_constraint_name = pk.constraint_name
    AND rc.unique_constraint_schema = pk.constraint_schema
    AND fk.ordinal_position = pk.ordinal_position
WHERE 1=1
            {0}
    ORDER BY fk.table_schema, fk.table_name, fk.constraint_name, fk.ordinal_position;
    """.format(
                query_filter
            )
        )

    def QueryTablesForeignKeysColumns(self, fkey, table=None, all_schemas=False, schema=None):
        query_filter = ""
        if not all_schemas:
            table_filter_part = f"AND fk.table_name = '{table}' " if table else " "
            schema_filter_part = f"AND fk.table_schema = '{schema or self.schema}' "
            query_filter += table_filter_part + schema_filter_part
        else:
            query_filter = f"AND fk.table_name = '{table}'" if table else ""

        fkeys = fkey if isinstance(fkey, list) else [fkey]

        fkeys_list = ", ".join([f"'{str(e)}'" for e in fkeys])

        if fkeys_list:
            query_filter = query_filter + f"AND fk.constraint_name in ({fkeys_list}) "

        return self.Query(
            """
        SELECT fk.table_schema,
       fk.table_name,
       fk.constraint_name,
       fk.column_name,
       pk.table_schema AS r_schema_name,
       pk.table_name   AS r_table_name,
       pk.column_name  AS r_column_name,
        update_rule,
        delete_rule
FROM INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS rc
JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE fk
  ON rc.constraint_name = fk.constraint_name
  AND rc.constraint_schema = fk.constraint_schema
JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE pk
  ON rc.unique_constraint_name = pk.constraint_name
  AND rc.unique_constraint_schema = pk.constraint_schema
  AND fk.ordinal_position = pk.ordinal_position
WHERE 1=1
                          {0}
ORDER BY fk.table_schema, fk.table_name, fk.constraint_name, fk.ordinal_position;
""".format(
                query_filter
            ),
            True,
        )

    def QueryTablesUniques(self, table=None, all_schemas=False, schema=None):
        query_filter = ""

        if not all_schemas:
            table_filter_part = f"AND table_name = '{table}' " if table else " "
            schema_filter_part = f"AND table_schema = '{schema or self.schema}'"
            query_filter += table_filter_part + schema_filter_part
        else:
            query_filter = f"AND table_name = '{table}'" if table else ""

        return self.Query(
            """

    SELECT table_schema,
        table_name,
        constraint_name
    FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS 
    WHERE constraint_type = 'UNIQUE'
            {0}
    ORDER BY table_schema, table_name;
    """.format(
                query_filter
            )
        )

    def QueryTablesUniquesColumns(self, unique_name, table=None, all_schemas=False, schema=None):
        query_filter = ""
        if not all_schemas:
            table_filter_part = f"AND kc.table_name = '{table}' " if table else " "
            schema_filter_part = f"AND kc.table_schema = '{schema or self.schema}' "
            query_filter += table_filter_part + schema_filter_part
        else:
            query_filter = f"AND kc.table_name = '{table}'" if table else ""

        query_filter = query_filter + f"AND kc.constraint_name = '{unique_name}' "
        return self.Query(
            """
    SELECT kc.table_schema,
        kc.table_name,
        kc.constraint_name,
        kc.column_name,
        kc.ordinal_position
    FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE kc
    JOIN INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
    ON kc.constraint_name = tc.constraint_name
    AND kc.table_schema = tc.table_schema
    WHERE tc.constraint_type = 'UNIQUE'
    {0}
    ORDER BY kc.table_schema, kc.table_name, kc.ordinal_position;
    """.format(
                query_filter
            ),
            True,
        )

    def QueryTablesIndexes(self, table=None, all_schemas=False, schema=None):
        query_filter = ""

        if not all_schemas:
            table_filter_part = f"AND t.name = '{table}' " if table else " "
            schema_filter_part = f"AND s.name = '{schema or self.schema}'"
            query_filter += table_filter_part + schema_filter_part
        else:
            query_filter = f"AND t.name = '{table}'" if table else ""
        return self.Query(
            """
SELECT 
    i.name          AS index_name,
    i.is_unique     AS is_unique,
    i.is_primary_key AS is_primary,
    i.filter_definition AS predicate,
    STRING_AGG(c.name, ',') 
        WITHIN GROUP (ORDER BY ic.key_ordinal, c.name) AS columns
FROM sys.indexes i
JOIN sys.tables t ON i.object_id = t.object_id
JOIN sys.schemas s ON t.schema_id = s.schema_id
JOIN sys.index_columns ic ON i.object_id = ic.object_id AND i.index_id = ic.index_id
JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
WHERE i.is_hypothetical = 0 
  AND i.index_id > 0 
        {0}
GROUP BY i.name, i.is_unique, i.is_primary_key, i.filter_definition
ORDER BY i.name;
""".format(
                query_filter
            ),
            True,
        )

    def QueryTablesIndexesColumns(self, index_name, table=None, all_schemas=False, schema=None):
        query_filter = ""
        if not all_schemas:
            table_filter_part = f"AND t.name = '{table}' " if table else " "
            schema_filter_part = f"AND s.name = '{schema or self.schema}' "
            query_filter += table_filter_part + schema_filter_part
        else:
            query_filter = f"AND t.name = '{table}'" if table else ""

        query_filter = query_filter + f"AND i.name = '{index_name}' "
        return self.Query(
            """
SELECT c.name AS column_name
FROM sys.indexes i
JOIN sys.index_columns ic ON i.object_id = ic.object_id AND i.index_id = ic.index_id
JOIN sys.columns c        ON ic.object_id = c.object_id AND ic.column_id = c.column_id
JOIN sys.tables t         ON i.object_id = t.object_id
JOIN sys.schemas s        ON t.schema_id = s.schema_id
WHERE i.is_hypothetical = 0
  AND i.index_id > 0
{0}
;
""".format(
                query_filter
            )
        )

    def QueryTablesChecks(self, table=None, all_schemas=False, schema=None):
        query_filter = ""

        if not all_schemas:
            table_filter_part = f"AND ctu.table_name = '{table}' " if table else " "
            schema_filter_part = f"AND cc.constraint_schema = '{schema or self.schema}'"
            query_filter += table_filter_part + schema_filter_part
        else:
            query_filter = f"AND ctu.table_name = '{table}'" if table else ""

        return self.Query(
            """
        SELECT cc.constraint_schema,
       ctu.table_name,
       cc.constraint_name,
       cc.check_clause
        FROM INFORMATION_SCHEMA.CHECK_CONSTRAINTS cc
        JOIN INFORMATION_SCHEMA.CONSTRAINT_TABLE_USAGE ctu
        ON cc.constraint_name = ctu.constraint_name
        WHERE 1=1
                                {0}
        ORDER BY cc.constraint_name;
""".format(
                query_filter
            ),
            True,
        )

    def QueryTablesTriggers(self, table=None, all_schemas=False, schema=None):
        query_filter = ""

        if not all_schemas:
            table_filter_part = f"AND t.name = '{table}' " if table else " "
            schema_filter_part = f"AND s.name = '{schema or self.schema}'"
            query_filter += table_filter_part + schema_filter_part
        else:
            query_filter = f"AND t.name = '{table}'" if table else ""

        return self.Query(
            """
SELECT 
    s.name AS schema_name,
    t.name AS table_name,
    tr.name AS trigger_name,
    tr.is_disabled AS is_disabled
FROM sys.triggers tr
JOIN sys.tables t 
    ON tr.parent_id = t.object_id
JOIN sys.schemas s 
    ON t.schema_id = s.schema_id
WHERE 1=1
    {0}
""".format(
                query_filter
            ),
            True,
        )

    def QueryServerRoles(self):
        return self.Query(
            """
    SELECT 
    sp.name AS role_name
FROM sys.server_principals sp
WHERE sp.type = 'R'
ORDER BY sp.name;
"""
        )

    def QueryDatabaseRoles(self):
        return self.Query(
            """
SELECT 
    dp.name       AS role_name
FROM sys.database_principals dp
WHERE dp.type = 'R'
ORDER BY dp.name;
"""
        )

    def QueryLogins(self):
        return self.Query(
            """
    SELECT 
    sp.name AS login_name
FROM sys.server_principals sp
WHERE sp.type IN ('S', 'U', 'G')
ORDER BY sp.name;
"""
        )

    def QueryUsers(self):
        return self.Query(
            """
                          SELECT 
    dp.name  AS user_name
FROM sys.database_principals dp
WHERE dp.type IN ('S', 'U', 'G')  
  AND dp.sid IS NOT NULL 
ORDER BY dp.name;
                          """
        )

    def TemplateSelect(self, schema, table, object_type):
        if object_type == "t":
            sql = "SELECT "
            fields = self.QueryTablesFields(table, False, schema)
            if fields.Rows:
                sql += ", ".join([f"t.{r['column_name']}" for r in fields.Rows])
            sql += f"\nFROM [{schema}].[{table}] t"
            pk = self.QueryTablesPrimaryKeys(table, False, schema)
            if pk.Rows:
                fields = self.QueryTablesPrimaryKeysColumns(pk.Rows[0]["constraint_name"], table, False, schema)
                if fields.Rows:
                    sql += "\nORDER BY " + ", ".join(f"t.{r['column_name']}" for r in fields.Rows)
        elif object_type == "v":
            sql = "SELECT "
            fields = self.QueryViewFields(table, False, schema)
            if fields.Rows:
                sql += ", ".join([f"t.{r['column_name']}" for r in fields.Rows])
            sql += f"\nFROM [{schema}].[{table}] t"
        else:
            sql = f"SELECT t.*\nFROM [{schema}].[{table}] t"
        formatted_sql = sql_format(sql, keyword_case="upper", reindent=True)
        return Template(formatted_sql)

    def GetPropertiesDatabase(self, database_name):
        return self.Query(
            f"""
SELECT 
    d.name AS "Database",
    suser_sname(d.owner_sid) AS "Owner",
    d.state_desc  AS "State",
    d.is_encrypted AS "Encrypted",
    d.collation_name AS "Collation",
    d.user_access_desc AS "User Access",
    MIN(mf.physical_name) AS "File Path",
    CAST(SUM(mf.size) * 8. / 1024 AS DECIMAL(18, 2)) AS "SizeMB"               
FROM sys.databases d
JOIN sys.master_files mf
    ON d.database_id = mf.database_id        
    WHERE d.name = '{database_name}'
GROUP BY d.name, d.owner_sid, d.state_desc, d.is_encrypted, d.collation_name, d.user_access_desc
"""
        )

    def GetPropertiesLogin(self, login_name):
        return self.Query(
            f"""
SELECT 
    sp.name                  AS "Login Name",
    sp.type_desc             AS "Principal Type",
    sp.default_database_name AS "Default Database",
    sp.default_language_name AS "Default Language",
    sp.create_date           AS "Create Date",
    sp.modify_date           AS "Modify Date",
    sp.is_disabled           AS "Disabled",
    sl.is_policy_checked     AS "Policy Checked",
    sl.is_expiration_checked AS "Expiration Checked",
    sp.credential_id         AS "Credential ID"
FROM sys.server_principals sp
LEFT JOIN sys.sql_logins sl ON sp.principal_id = sl.principal_id
WHERE sp.type IN ('S', 'U', 'G') 
AND sp.name = '{login_name}'
"""
        )

    def GetPropertiesServerRole(self, role_name):
        return self.Query(
            f"""
        SELECT 
    r.name AS "Role Name",
    r.type_desc AS "Role Type",              
    r.create_date AS "Create Date",
    r.modify_date AS "Modify Date",
    r.is_fixed_role AS "Is Fixed Role"
    FROM sys.server_principals r
    WHERE r.type = 'R' AND r.name = '{role_name}'
"""
        )

    def GetPropertiesDatabaseRole(self, role_name):
        return self.Query(
            f"""
SELECT 
    r.name AS "Role Name",
    r.type_desc AS "Role Type",
    r.create_date AS "Create Date",
    r.modify_date AS "Modify Date",
    r.is_fixed_role AS "Is Fixed Role"
FROM sys.database_principals r
WHERE r.type = 'R' AND r.name = '{role_name}' 
"""
        )

    def GetPropertiesUser(self, user_name):
        return self.Query(
            f"""
SELECT 
    dp.name              AS "User Name",
    dp.type_desc         AS "User Type",
    dp.authentication_type_desc AS "Authentication Type",
    dp.default_schema_name AS "Default Schema",
    dp.create_date       AS "Create Date",
    dp.modify_date       AS "Modify Date",
    dp.owning_principal_id AS "Owning Principal Id",
    dp.principal_id      AS "Principal Id",
    dp.is_fixed_role     AS "Is Fixed Role"
FROM sys.database_principals dp
WHERE dp.type IN ('S', 'U', 'G')
  AND dp.sid IS NOT NULL
  AND dp.name = '{user_name}'
"""
        )

    def GetPropertiesSchema(self, schema_name):
        return self.Query(
            f"""
SELECT 
    s.name              AS "Schema Name",
    dp.name             AS "Owner Name",
    dp.type_desc        AS "Owner Type",
    s.schema_id         AS "Schema Id",
    s.principal_id      AS "Principal Id",
    dp.create_date       AS "Create Date",
    dp.modify_date       AS "Modify Date"
FROM sys.schemas s
JOIN sys.database_principals dp 
     ON s.principal_id = dp.principal_id
WHERE s.name = '{schema_name}'
"""
        )

    def GetPropertiesTable(self, schema, table_name):
        return self.Query(
            f"""
SELECT 
    s.name          AS "Schema Name",
    t.name          AS "Table Name",
    t.object_id     AS "Object Id",
    t.create_date   AS "Create Date",
    t.modify_date   AS "Modify Date",
    t.is_ms_shipped AS "Is System Table"
FROM sys.tables t
JOIN sys.schemas s ON t.schema_id = s.schema_id
    WHERE t.name = '{table_name}' AND s.name = '{schema}'
"""
        )

    def GetPropertiesView(self, schema, view_name):
        return self.Query(
            f"""
SELECT 
    s.name          AS "Schema Name",
    v.name          AS "View Name",
    v.object_id     AS "Object Id",
    v.create_date   AS "Create Date",
    v.modify_date   AS "Modify Date"
FROM sys.views v
JOIN sys.schemas s ON v.schema_id = s.schema_id
WHERE v.name = '{view_name}' AND s.name = '{schema}'
"""
        )

    def GetPropertiesFunction(self, schema, function_name):
        return self.Query(
            f"""
SELECT 
    s.name        AS "Schema Name",
    f.name        AS "Function Name",
    f.object_id   AS "Object Id",
    f.type_desc   AS "Function Type",
    f.create_date AS "Create Date",
    f.modify_date AS "Modify Date"
FROM sys.objects f
JOIN sys.schemas s ON f.schema_id = s.schema_id
WHERE f.type IN ('FN', 'IF', 'TF') AND s.name = '{schema}' AND f.name = '{function_name}'
"""
        )

    def GetPropertiesProcedure(self, schema, procedure_name):
        return self.Query(
            f"""
SELECT 
    s.name        AS "Schema Name",
    p.name        AS "Procedure Name",
    p.object_id   AS "Object Id",
    p.create_date AS "Create Date",
    p.modify_date AS "Modify Date"
FROM sys.procedures p
JOIN sys.schemas s ON p.schema_id = s.schema_id
WHERE s.name = '{schema}' AND p.name = '{procedure_name}'
"""
        )

    def GetPropertiesTableField(self, schema, table, table_field):
        return self.Query(
            f"""
SELECT 
    s.name              AS "Schema Name",
    t.name              AS "Table Name",
    c.name              AS "Column Name",
    c.column_id         AS "Column Id",
    ty.name             AS "Data Type",
    c.max_length        AS "Max Length",
    c.precision         AS "Precision",
    c.scale             AS "Scale",
    c.is_nullable       AS "Is Nullable",
    c.is_identity       AS "Is Identity",
    dc.definition       AS "Default Definition",
    c.collation_name    AS "Collation"
FROM sys.columns c
JOIN sys.tables t         ON c.object_id = t.object_id
JOIN sys.schemas s        ON t.schema_id = s.schema_id
JOIN sys.types ty         ON c.user_type_id = ty.user_type_id
LEFT JOIN sys.default_constraints dc 
       ON c.default_object_id = dc.object_id
WHERE s.name = '{schema}'
  AND t.name = '{table}'
  AND c.name = '{table_field}'
ORDER BY c.column_id;
"""
        )

    def GetPropertiesPK(self, schema, table, constraint_name):
        return self.Query(
            f"""
SELECT 
    kc.table_schema     AS "Schema Name",
    kc.table_name       AS "Table Name",
    kc.constraint_name  AS "Constraint Name",
    STRING_AGG(
        QUOTENAME(kc.column_name) ,
        ', '
    ) WITHIN GROUP (ORDER BY kc.ordinal_position) AS "Columns"
FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kc
    ON kc.constraint_name = tc.constraint_name
   AND kc.table_schema = tc.table_schema
WHERE tc.constraint_type = 'PRIMARY KEY'
  AND kc.table_schema = '{schema}'
  AND kc.table_name   = '{table}'
  AND kc.constraint_name = '{constraint_name}'
  GROUP BY kc.table_schema, kc.table_name, kc.constraint_name;
"""
        )

    def GetPropertiesFK(self, schema, table, constraint_name):
        return self.Query(
            f"""
       SELECT fk.table_schema AS "Table Schema",
       fk.table_name AS "TABLE NAME",
       fk.constraint_name AS "Constraint Name",
       fk.column_name AS "Column Name",
       pk.table_schema AS "Referenced Schema",
       pk.table_name   AS "Referenced Table",
       pk.column_name  AS "Referenced Column",
       update_rule AS "Update Rule",
       delete_rule AS "Delete Rule"
FROM INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS rc
JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE fk
  ON rc.constraint_name = fk.constraint_name
  AND rc.constraint_schema = fk.constraint_schema
JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE pk
  ON rc.unique_constraint_name = pk.constraint_name
  AND rc.unique_constraint_schema = pk.constraint_schema
  AND fk.ordinal_position = pk.ordinal_position
WHERE fk.table_schema = '{schema}'
  AND fk.table_name   = '{table}'
  AND fk.constraint_name = '{constraint_name}'
"""
        )

    def GetPropertiesCheck(self, schema, table, constraint_name):
        return self.Query(
            f"""
SELECT 
    s.name             AS "Schema Name",
    t.name             AS "Table Name",
    cc.name            AS "Constraint Name",
    cc.definition      AS "Check Definition",
    cc.is_disabled     AS "Is Disabled",
    cc.is_not_for_replication AS "Is Not For Replication",
    cc.create_date     AS "Create Date",
    cc.modify_date     AS "Modify Date"
FROM sys.check_constraints cc
JOIN sys.tables t   ON cc.parent_object_id = t.object_id
JOIN sys.schemas s  ON t.schema_id = s.schema_id
WHERE s.name = '{schema}'
  AND t.name = '{table}'
  AND cc.name = '{constraint_name}'
"""
        )

    def GetPropertiesUnique(self, schema, table, constraint_name):
        return self.Query(
            f"""
SELECT 
    kc.table_schema     AS "Schema Name",
    kc.table_name       AS "Table Name",
    kc.constraint_name  AS "Constraint Name",
    kc.column_name      AS "Column Name",
    kc.ordinal_position AS "Column Order"
FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kc
    ON kc.constraint_name = tc.constraint_name
   AND kc.table_schema = tc.table_schema
WHERE tc.constraint_type = 'UNIQUE'
  AND kc.table_schema = '{schema}'
  AND kc.table_name   = '{table}'
  AND kc.constraint_name = '{constraint_name}'
"""
        )

    def GetPropertiesIndex(self, schema, table, index_name):
        return self.Query(
            f""" 
    SELECT 
    s.name          AS "Schema Name",
    t.name          AS "Table Name",
    i.name          AS "Index Name",
    i.index_id      AS "Index Id",
    i.type_desc     AS "Index Type",
    i.is_unique     AS "Is Unique",
    i.is_primary_key AS "Is Primary Key",
    i.is_unique_constraint AS "Is Unique Constraint",
    i.is_disabled   AS "Is Disabled",
    i.fill_factor   AS "Fill Factor",
    i.allow_row_locks AS "Allow Row Locks",
    i.allow_page_locks AS "Allow Page Locks",
    STRING_AGG(
        CASE 
            WHEN ic.is_included_column = 1 
                THEN c.name + ' (INCLUDE)'
            ELSE c.name + CASE WHEN ic.is_descending_key = 1 THEN ' DESC' ELSE ' ASC' END
        END, ', '
    ) WITHIN GROUP (ORDER BY ic.key_ordinal) AS "Columns"
FROM sys.indexes i
JOIN sys.tables t ON i.object_id = t.object_id
JOIN sys.schemas s ON t.schema_id = s.schema_id
JOIN sys.index_columns ic ON i.object_id = ic.object_id AND i.index_id = ic.index_id
JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
WHERE s.name = '{schema}'
  AND t.name = '{table}'
  AND i.name = '{index_name}'
GROUP BY 
    s.name, t.name, i.name, i.index_id, i.type_desc,
    i.is_unique, i.is_primary_key, i.is_unique_constraint,
    i.is_disabled, i.fill_factor, i.allow_row_locks, i.allow_page_locks;
"""
        )

    def GetPropertiesStatistic(self, schema, table, statistic_name):
        return self.Query(
            f"""
SELECT 
    s.name        AS "Schema Name",
    t.name        AS "Table Name",
    st.name       AS "Statistic Name",
    st.stats_id   AS "Stats Id",
    st.auto_created AS "Auto Created",
    st.user_created AS "User Created",
    STRING_AGG(c.name, ', ') WITHIN GROUP (ORDER BY sc.stats_column_id) AS "Columns"
FROM sys.stats st
JOIN sys.stats_columns sc 
     ON st.object_id = sc.object_id AND st.stats_id = sc.stats_id
JOIN sys.columns c 
     ON sc.object_id = c.object_id AND sc.column_id = c.column_id
JOIN sys.tables t 
     ON st.object_id = t.object_id
JOIN sys.schemas s 
     ON t.schema_id = s.schema_id
WHERE s.name = '{schema}'
  AND t.name = '{table}'
  AND st.name = '{statistic_name}'
  GROUP BY s.name, t.name, st.name, st.stats_id, st.auto_created, st.user_created
"""
        )

    def GetPropertiesViewField(self, schema, view, view_field):
        return self.Query(
            f"""
SELECT 
    c.name       AS "Column Name",
    t.name       AS "Data Type",
    c.max_length AS "Max Length",
    c.precision  AS "Precision",
    c.scale AS "Scale",
    c.is_nullable AS "Is Nullable",
    c.is_identity AS "Is Identity"
FROM sys.columns c
JOIN sys.types t ON c.user_type_id = t.user_type_id
WHERE c.object_id = OBJECT_ID('{schema}.{view}') AND c.name = '{view_field}'
"""
        )

    def GetPropertiesTrigger(self, schema, table, trigger):
        return self.Query(
            f"""
SELECT 
    sch.name        AS "Schema Name",
    tbl.name        AS "Table Name",
    tr.name         AS "Trigger Name",
    tr.object_id    AS "Object Id",
    tr.is_disabled  AS "Is Disabled",
    tr.is_instead_of_trigger AS "Is Instead Of",
    tr.create_date  AS "Create Date",
    tr.modify_date  AS "Modify Date"
FROM sys.triggers tr
JOIN sys.tables tbl
     ON tr.parent_id = tbl.object_id
JOIN sys.schemas sch
     ON tbl.schema_id = sch.schema_id
LEFT JOIN sys.sql_modules m
     ON tr.object_id = m.object_id
WHERE sch.name = '{schema}'
  AND tbl.name = '{table}'
  AND tr.name = '{trigger}';

"""
        )

    def GetPropertiesType(self, type_name):
        return self.Query(
            f"""
    SELECT 
    s.name AS [Schema Name],
    t.name AS [Type Name],
    t.user_type_id AS [User Type ID],
    st.name AS [Base Type],
    t.max_length AS [Max Length],
    t.precision AS [Precision],
    t.scale AS [Scale],
    t.is_nullable AS [Is Nullable],
    t.is_table_type AS [Is Table Type],
    t.is_user_defined AS [Is User Defined],
    t.is_assembly_type AS [Is Assembly Type],
    t.is_nullable AS [Is Nullable],
    t.collation_name AS [Collation],
    t.default_object_id AS [Default Object ID],
    t.rule_object_id AS [Rule Object ID]
FROM sys.types t
JOIN sys.schemas s ON t.schema_id = s.schema_id
LEFT JOIN sys.types st 
       ON t.system_type_id = st.user_type_id  -- base system type
WHERE t.is_user_defined = 1
  AND t.is_table_type = 0
  AND t.name = '{type_name}';
"""
        )

    def GetProperties(self, schema, table, object_name, object_type):
        if object_type == "database":
            return self.GetPropertiesDatabase(object_name).Transpose("Property", "Value")
        if object_type == "login":
            return self.GetPropertiesLogin(object_name).Transpose("Property", "Value")
        if object_type == "server_role":
            return self.GetPropertiesServerRole(object_name).Transpose("Property", "Value")
        if object_type == "database_role":
            return self.GetPropertiesDatabaseRole(object_name).Transpose("Property", "Value")
        if object_type == "user":
            return self.GetPropertiesUser(object_name).Transpose("Property", "Value")
        if object_type == "schema":
            return self.GetPropertiesSchema(object_name).Transpose("Property", "Value")
        if object_type == "table":
            return self.GetPropertiesTable(schema, object_name).Transpose("Property", "Value")
        if object_type == "table_field":
            return self.GetPropertiesTableField(schema, table, object_name).Transpose("Property", "Value")
        if object_type == "index":
            return self.GetPropertiesIndex(schema, table, object_name).Transpose("Property", "Value")
        if object_type == "primary_key":
            return self.GetPropertiesPK(schema, table, object_name).Transpose("Property", "Value")
        if object_type == "foreign_key":
            return self.GetPropertiesFK(schema, table, object_name).Transpose("Property", "Value")
        if object_type == "unique":
            return self.GetPropertiesUnique(schema, table, object_name).Transpose("Property", "Value")
        if object_type == "check":
            return self.GetPropertiesCheck(schema, table, object_name).Transpose("Property", "Value")
        if object_type == "statistic":
            return self.GetPropertiesStatistic(schema, table, object_name).Transpose("Property", "Value")
        if object_type == "view":
            return self.GetPropertiesView(schema, object_name).Transpose("Property", "Value")
        if object_type == "view_field":
            return self.GetPropertiesViewField(schema, table, object_name).Transpose("Property", "Value")
        if object_type == "function":
            return self.GetPropertiesFunction(schema, object_name).Transpose("Property", "Value")
        if object_type == "procedure":
            return self.GetPropertiesProcedure(schema, object_name).Transpose("Property", "Value")
        if object_type == "trigger":
            return self.GetPropertiesTrigger(schema, table, object_name).Transpose("Property", "Value")
        if object_type == "type":
            return self.GetPropertiesType(object_name).Transpose("Property", "Value")

    def GetDDLTable(self, schema, table):
        return self.ExecuteScalar(
            f"""
WITH ColumnDefs AS (
    SELECT 
        TABLE_SCHEMA,
        TABLE_NAME,
        STRING_AGG(
            CAST(
                '  ' + QUOTENAME(COLUMN_NAME) + ' ' + DATA_TYPE +
                CASE 
                    WHEN CHARACTER_MAXIMUM_LENGTH IS NOT NULL 
                         AND DATA_TYPE LIKE '%char%' 
                         THEN '(' + 
                              CASE WHEN CHARACTER_MAXIMUM_LENGTH = -1 
                                   THEN 'MAX' 
                                   ELSE CAST(
                                       CASE WHEN DATA_TYPE LIKE 'n%' 
                                            THEN CHARACTER_MAXIMUM_LENGTH/2 
                                            ELSE CHARACTER_MAXIMUM_LENGTH 
                                       END AS NVARCHAR(10)
                                   ) 
                              END + ')'
                    WHEN DATA_TYPE IN ('decimal','numeric') 
                         THEN '(' + CAST(NUMERIC_PRECISION AS NVARCHAR(10)) + ',' + CAST(NUMERIC_SCALE AS NVARCHAR(10)) + ')'
                    ELSE ''
                END +
                CASE WHEN COLLATION_NAME IS NOT NULL 
                          AND DATA_TYPE LIKE '%char%' 
                     THEN ' COLLATE ' + COLLATION_NAME 
                     ELSE '' END +
                CASE WHEN IS_NULLABLE = 'YES' THEN ' NULL' ELSE ' NOT NULL' END
                AS NVARCHAR(MAX)
            ), ',' + CHAR(10)
        ) WITHIN GROUP (ORDER BY ORDINAL_POSITION) AS ColumnList
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = '{schema}' AND TABLE_NAME = '{table}'
    GROUP BY TABLE_SCHEMA, TABLE_NAME
)
SELECT 
    'CREATE TABLE ' + QUOTENAME(c.TABLE_SCHEMA) + '.' + QUOTENAME(c.TABLE_NAME) + ' (' + CHAR(10) +
    c.ColumnList + CHAR(10) +
    ');' + CHAR(10) +
    ISNULL(pk.PKScript, '') AS [CreateTableScript]
FROM ColumnDefs c
LEFT JOIN (
    SELECT 
        kc.TABLE_SCHEMA,
        kc.TABLE_NAME,
        'ALTER TABLE ' + QUOTENAME(kc.TABLE_SCHEMA) + '.' + QUOTENAME(kc.TABLE_NAME) + 
        ' ADD CONSTRAINT ' + QUOTENAME(tc.CONSTRAINT_NAME) +
        ' PRIMARY KEY (' + 
        STRING_AGG(QUOTENAME(kc.COLUMN_NAME), ', ') WITHIN GROUP (ORDER BY kc.ORDINAL_POSITION) +
        ');' AS PKScript
    FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
    JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kc
      ON tc.CONSTRAINT_NAME = kc.CONSTRAINT_NAME
     AND tc.TABLE_SCHEMA = kc.TABLE_SCHEMA
    WHERE tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
      AND kc.TABLE_SCHEMA = '{schema}'
      AND kc.TABLE_NAME = '{table}'
    GROUP BY kc.TABLE_SCHEMA, kc.TABLE_NAME, tc.CONSTRAINT_NAME
) pk
  ON pk.TABLE_SCHEMA = c.TABLE_SCHEMA AND pk.TABLE_NAME = c.TABLE_NAME;
"""
        )

    def GetDDLProcedure(self, schema, procedure):
        return self.ExecuteScalar(
            f"""
    SELECT OBJECT_DEFINITION(p.object_id) AS [Definition]
FROM sys.procedures p
JOIN sys.schemas s ON p.schema_id = s.schema_id
WHERE s.name = '{schema}'
AND p.name = '{procedure}'
"""
        )

    def GetDDLView(self, schema, view):
        return self.ExecuteScalar(
            f"""
SELECT OBJECT_DEFINITION(v.object_id) AS [Definition]
FROM sys.views v
JOIN sys.schemas s ON v.schema_id = s.schema_id
WHERE s.name = '{schema}'
AND v.name = '{view}'
"""
        )

    def GetDDLFunction(self, schema, function):
        return self.ExecuteScalar(
            f"""
SELECT OBJECT_DEFINITION(f.object_id) AS [Definition]
FROM sys.objects f
JOIN sys.schemas s ON f.schema_id = s.schema_id
WHERE f.type in ('FN', 'IF', 'TF')
AND s.name = '{schema}'
AND f.name = '{function}'
"""
        )

    def GetDDLTrigger(self, schema, trigger):
        return self.ExecuteScalar(
            f"""
SELECT OBJECT_DEFINITION(tr.object_id) AS [Definition]
FROM sys.triggers tr
JOIN sys.tables tbl
     ON tr.parent_id = tbl.object_id
JOIN sys.schemas s ON tbl.schema_id = s.schema_id
WHERE s.name = '{schema}'
AND tr.name = '{trigger}'
"""
        )

    def GetDDL(self, schema, table, object_name, object_type):
        if object_type == "table":
            return self.GetDDLTable(schema, object_name)
        if object_type == "view":
            return self.GetDDLView(schema, object_name)
        if object_type == "function":
            return self.GetDDLFunction(schema, object_name)
        if object_type == "procedure":
            return self.GetDDLProcedure(schema, object_name)
        if object_type == "trigger":
            return self.GetDDLTrigger(schema, object_name)
        return ""

    def QueryTableRecords(self, column_list, table, schema, query_filter, count=-1):
        table_name = "{0}.{1}".format(schema, table) if schema else table

        limit = ""
        if count != -1:
            limit = f" TOP {count}"
        return self.Query(
            """
            select {3} {0}
            from {1} t
            {2}
        """.format(
                column_list, table_name, query_filter, limit
            ),
            False,
        )

    def QueryTableDefinition(self, table=None, schema=None):
        in_schema = schema if schema else self.schema

        return self.Query('''
SELECT
  s.name AS SCHEMA_NAME,
  t.name AS table_name,
  c.name AS column_name,
  /* ---------- Full data type (incl. length/precision/scale) ---------- */
  CASE
    WHEN ty.name IN ('char', 'varchar', 'nchar', 'nvarchar') THEN ty.name + '(' + CASE
      WHEN c.max_length = -1 THEN 'MAX'
      ELSE CAST(
        c.max_length / CASE
          WHEN ty.name LIKE 'n%' THEN 2
          ELSE 1
        END AS varchar(10)
      )
    END + ')'
    WHEN ty.name IN ('binary', 'varbinary') THEN ty.name + '(' + CASE
      WHEN c.max_length = -1 THEN 'MAX'
      ELSE CAST(c.max_length AS varchar(10))
    END + ')'
    WHEN ty.name IN ('decimal', 'numeric') THEN ty.name + '(' + CAST(c.precision AS varchar(5)) + ',' + CAST(c.scale AS varchar(5)) + ')'
    ELSE ty.name
  END AS data_type,
  dc.definition AS column_default,
  c.is_nullable AS is_nullable,
  /* ---------- Primary‑key flag ---------- */
  CAST(
    CASE
      WHEN pkc.column_id IS NOT NULL THEN 1
      ELSE 0
    END AS BIT
  ) AS is_primary
FROM
  sys.schemas AS s
  JOIN sys.tables AS t ON t.schema_id = s.schema_id
  JOIN sys.columns AS c ON c.object_id = t.object_id
  JOIN sys.types AS ty ON ty.user_type_id = c.user_type_id
  LEFT JOIN sys.default_constraints AS dc ON dc.parent_object_id = t.object_id
  AND dc.parent_column_id = c.column_id
  /* ----- Detect primary‑key columns ----- */
  LEFT JOIN (
    SELECT
      ic.object_id,
      ic.column_id
    FROM
      sys.key_constraints AS kc
      JOIN sys.index_columns AS ic ON ic.object_id = kc.parent_object_id
      AND ic.index_id = kc.unique_index_id
    WHERE
      kc.type = 'PK' -- only primary keys
  ) pkc ON pkc.object_id = c.object_id
  AND pkc.column_id = c.column_id
WHERE
  s.name = '{0}'
  AND t.name = '{1}'
ORDER BY
  c.column_id;
        '''.format(in_schema, table), False)

    def TemplateCreateUser(self):
        template = get_template("mssql", "create_user")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateAlterUser(self):
        template = get_template("mssql", "alter_user")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateDropUser(self):
        template = get_template("mssql", "drop_user")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateCreateLogin(self):
        template = get_template("mssql", "create_login")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateAlterLogin(self):
        template = get_template("mssql", "alter_login")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateDropLogin(self):
        template = get_template("mssql", "drop_login")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateCreateServerRole(self):
        template = get_template("mssql", "create_server_role")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateAlterServerRole(self):
        template = get_template("mssql", "alter_server_role")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateDropServerRole(self):
        template = get_template("mssql", "drop_server_role")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateCreateDatabaseRole(self):
        template = get_template("mssql", "create_database_role")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateAlterDatabaseRole(self):
        template = get_template("mssql", "alter_database_role")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateDropDatabaseRole(self):
        template = get_template("mssql", "drop_database_role")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateCreateDatabase(self):
        template = get_template("mssql", "create_database")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateAlterDatabase(self):
        template = get_template("mssql", "alter_database")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateDropDatabase(self):
        template = get_template("mssql", "drop_database")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateCreateSchema(self):
        template = get_template("mssql", "create_schema")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateDropSchema(self):
        template = get_template("mssql", "drop_schema")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateCreateFunction(self):
        template = get_template("mssql", "create_function")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateAlterFunction(self):
        template = get_template("mssql", "alter_function")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateDropFunction(self):
        template = get_template("mssql", "drop_function")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateCreateProcedure(self):
        template = get_template("mssql", "create_procedure")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateAlterProcedure(self):
        template = get_template("mssql", "alter_procedure")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateDropProcedure(self):
        template = get_template("mssql", "drop_procedure")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateCreateView(self):
        template = get_template("mssql", "create_view")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateAlterView(self):
        template = get_template("mssql", "alter_view")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateDropView(self):
        template = get_template("mssql", "drop_view")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateDropTable(self):
        template = get_template("mssql", "drop_table")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateCreateTrigger(self):
        template = get_template("mssql", "create_trigger")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateDropTrigger(self):
        template = get_template("mssql", "drop_trigger")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateCreateStatistics(self):
        template = get_template("mssql", "create_statistics")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateDropStatistics(self):
        template = get_template("mssql", "drop_statistics")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateCreateType(self):
        template = get_template("mssql", "create_type")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateDropType(self):
        template = get_template("mssql", "drop_type")
        return template.safe_substitute(major_version=self.major_version)

    def QueryTypes(self, all_schemas, schema):
        query_filter = "" if all_schemas else f"AND s.name = '{schema or self.schema}'"
        return self.Query(
            f"""
SELECT  
    t.name AS type_name,
    t.user_type_id,
    t.system_type_id
FROM sys.types t
JOIN sys.schemas s ON t.schema_id = s.schema_id
WHERE t.is_user_defined = 1 AND t.is_table_type = 0 
    {query_filter}
ORDER BY s.name, t.name;
"""
        )
