'''
The MIT License (MIT)

Portions Copyright (c) 2015-2019, The OmniDB Team
Portions Copyright (c) 2017-2019, 2ndQuadrant Limited

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''

from enum import Enum
from urllib.parse import urlparse

import app.include.Spartacus as Spartacus

from .sql_templates import get_template

'''
------------------------------------------------------------------------
Template
------------------------------------------------------------------------
'''
class TemplateType(Enum):
    EXECUTE = 1
    SCRIPT = 2

class Template:
    def __init__(self, text, template_type=TemplateType.EXECUTE):
        self.text = text
        self.type = template_type

'''
------------------------------------------------------------------------
PostgreSQL
------------------------------------------------------------------------
'''
class PostgreSQL:
    def __init__(self, server, port, service, user, password, conn_id=0, alias='', application_name='PgManage', conn_string='', parse_conn_string = False, connection_params=None):
        self.lock = None
        self.connection_params = connection_params if connection_params else {}
        self.alias = alias
        self.db_type = 'postgresql'
        self.conn_id = conn_id
        self.conn_string = conn_string
        self.conn_string_error = ''
        self.password = password
        self.port = port
        if port is None or port == '':
            self.active_port = '5432'
        else:
            self.active_port = port
        self.service = service
        if service is None or service == '':
            self.active_service = 'postgres'
        else:
            self.active_service = service
        self.server = server
        self.active_server = server
        self.user = user
        self.active_user = user
        self.conn_string_query = ''
        #try to get info from connection string
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
                self.conn_string_error = 'Syntax error in the connection string.'

        self.schema = 'public'
        self.connection = Spartacus.Database.PostgreSQL(self.active_server, self.active_port, self.active_service, self.active_user, self.password, application_name, conn_string, connection_params=self.connection_params)

        self.data_types = {
            'bigint': { 'quoted': False },
            'bigserial': { 'quoted': False },
            'char': { 'quoted': True },
            'character': { 'quoted': True },
            'character varying': { 'quoted': True },
            'date': { 'quoted': True },
            'decimal': { 'quoted': False },
            'double precision': { 'quoted': False },
            'float': { 'quoted': False },
            'integer': { 'quoted': False },
            'money': { 'quoted': False },
            'numeric': { 'quoted': False },
            'real': { 'quoted': False },
            'serial': { 'quoted': False },
            'smallint': { 'quoted': False },
            'smallserial': { 'quoted': False },
            'text': { 'quoted': True },
            'time with time zone': { 'quoted': True },
            'time without time zone': { 'quoted': True },
            'timestamp with time zone': { 'quoted': True },
            'timestamp without time zone': { 'quoted': True },
            'varchar': { 'quoted': True }
        }

        self.can_rename_table = True
        self.rename_table_command = "alter table #p_table_name# rename to #p_new_table_name#"
        self.create_pk_command = "constraint #p_constraint_name# primary key (#p_columns#)"
        self.create_fk_command = "constraint #p_constraint_name# foreign key (#p_columns#) references #p_r_table_name# (#p_r_columns#) #p_delete_update_rules#"
        self.create_unique_command = "constraint #p_constraint_name# unique (#p_columns#)"
        self.can_alter_type = True
        self.alter_type_command = "alter table #p_table_name# alter #p_column_name# type #p_new_data_type#"
        self.can_alter_nullable = True
        self.set_nullable_command = "alter table #p_table_name# alter #p_column_name# drop not null"
        self.drop_nullable_command = "alter table #p_table_name# alter #p_column_name# set not null"
        self.can_rename_column = True
        self.rename_column_command = "alter table #p_table_name# rename #p_column_name# to #p_new_column_name#"
        self.can_add_column = True
        self.add_column_command = "alter table #p_table_name# add column #p_column_name# #p_data_type# #p_nullable#"
        self.can_drop_column = True
        self.drop_column_command = "alter table #p_table_name# drop #p_column_name#"
        self.can_add_constraint = True
        self.add_pk_command = "alter table #p_table_name# add constraint #p_constraint_name# primary key (#p_columns#)"
        self.add_fk_command = "alter table #p_table_name# add constraint #p_constraint_name# foreign key (#p_columns#) references #p_r_table_name# (#p_r_columns#) #p_delete_update_rules#"
        self.add_unique_command = "alter table #p_table_name# add constraint #p_constraint_name# unique (#p_columns#)"
        self.can_drop_constraint = True
        self.drop_pk_command = "alter table #p_table_name# drop constraint #p_constraint_name#"
        self.drop_fk_command = "alter table #p_table_name# drop constraint #p_constraint_name#"
        self.drop_unique_command = "alter table #p_table_name# drop constraint #p_constraint_name#"
        self.create_index_command = "create index #p_index_name# on #p_table_name# (#p_columns#)";
        self.create_unique_index_command = "create unique index #p_index_name# on #p_table_name# (#p_columns#)"
        self.drop_index_command = "drop index #p_schema_name#.#p_index_name#"

        self.console_help = "Console tab. Type the commands in the editor below this box. \\? to view command list."
        self._version = None
        self._version_num = None
        self._major_version = None
        self.use_server_cursor = True
        self.set_default_feature_flags()


    @property
    def version(self):
        if self._version is None:
            self._fetch_version()
        return self._version

        
    @property
    def version_num(self):
        if self._version_num is None:
            self._fetch_version()
        return self._version_num
    
        
    @property
    def major_version(self):
        if self._major_version is None:
            self._fetch_version()
        return self._major_version
        
    
    def _fetch_version(self):
        try:
            self._version = self.connection.ExecuteScalar('show server_version')
            self._version_num = int(self.connection.ExecuteScalar('show server_version_num'))
            self._major_version = self.version_num // 10000
        except Exception:
            self._version = None
            self._version_num = None
            self._major_version = None
    

    def set_default_feature_flags(self):
        self.has_schema = True
        self.has_functions = True
        self.has_procedures = True
        self.has_packages = False
        self.has_sequences = True
        self.has_primary_keys = True
        self.has_foreign_keys = True
        self.has_uniques = True
        self.has_indexes = True
        self.has_checks = True
        self.has_excludes = True
        self.has_rules = True
        self.has_triggers = True
        self.has_partitions = True
        self.has_statistics = True

        self.has_extensions = False
        self.has_fdw = False
        self.has_event_triggers = False
        self.has_event_trigger_functions = False
        self.has_procedures = False
        self.has_replication_slots = False
        self.has_logical_replication = False
        self.has_update_rule = True

    
    def update_feature_flags(self):
        self.has_schema = True
        self.has_extensions = self.version_num >= 90100
        self.has_fdw = self.version_num >= 90300
        self.has_event_triggers = self.version_num >= 90300
        self.has_event_trigger_functions = self.version_num >= 90300
        self.has_procedures = self.version_num >= 110000
        self.has_replication_slots = self.version_num >= 90400
        self.has_logical_replication = self.version_num >= 100000

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

    def GetName(self):
        return self.service

    @lock_required
    def GetVersion(self):
        if self.version_num: # self.version_num indicates that the connection is active and we can now fetch db capabilities
            self.update_feature_flags()
        return f"PostgreSQL {self.version.split(' ')[0]}" if self.version else "Unknown"

    @lock_required
    def GetUserSuper(self):
        return self.connection.ExecuteScalar("select rolsuper from pg_roles where rolname = '{0}'".format(self.user))

    def PrintDatabaseInfo(self):
        if self.conn_string=='':
            return self.active_user + '@' + self.active_service
        else:
            return self.active_user + '@' + self.active_service

    def PrintDatabaseDetails(self):
        return self.active_server + ':' + self.active_port

    def HandleUpdateDeleteRules(self, p_update_rule, p_delete_rule):
        rules = ''
        if p_update_rule.strip() != '':
            rules += ' on update ' + p_update_rule + ' '
        if p_delete_rule.strip() != '':
            rules += ' on delete ' + p_delete_rule + ' '
        return rules

    @lock_required
    def TestConnection(self):
        message = ''
        status = False
        if self.conn_string and self.conn_string_error!='':
            return self.conn_string_error, status
        try:
            self.connection.connection_params["connect_timeout"] = 5
            self.connection.Open()
            schema = self.QuerySchemas()
            if len(schema.Rows) > 0:
                message = 'Connection successful.'
                status = True
            self.connection.Close()
        except Exception as exc:
            message = str(exc)
        self.connection.connection_params.pop("connect_timeout")
        return message, status

    def GetErrorPosition(self, p_error_message, sql_cmd):
        vector = str(p_error_message).split('\n')
        return_data = None
        if len(vector) > 1 and vector[1][0:4]=='LINE':
            return_data = {
                'row': vector[1].split(':')[0].split(' ')[1],
                'col': vector[2].index('^') - len(vector[1].split(':')[0])-2
            }
        return return_data

    @lock_required
    def Query(self, sql, alltypesstr=False, simple=False):
        return self.connection.Query(sql, alltypesstr, simple)

    @lock_required
    def ExecuteScalar(self, sql):
        return self.connection.ExecuteScalar(sql)

    @lock_required
    def Execute(self, sql):
        return self.connection.Execute(sql)

    @lock_required
    def Terminate(self, pid):
        return self.connection.Terminate(pid)

    @lock_required
    def QueryRoles(self):
        return self.connection.Query('''
            select quote_ident(rolname) as name_raw,
                   rolname as role_name,
                   oid
            from pg_roles
            order by rolname
        ''', True)

    @lock_required
    def QueryRoleDetails(self, oid):
        return self.connection.Query('''
            select quote_ident(rolname) as name_raw,
            rolname as role_name, oid, rolcanlogin,
            rolsuper, rolinherit, rolcreaterole,
            rolcreatedb, rolreplication, rolbypassrls,
            rolconnlimit, rolpassword, rolvaliduntil,
            ARRAY(
                SELECT
                    array[rm.rolname, pgam.admin_option::text]
                FROM
                    (SELECT * FROM pg_catalog.pg_auth_members WHERE member = pgr.oid) pgam
                    LEFT JOIN pg_catalog.pg_roles rm ON (rm.oid = pgam.roleid)
                ORDER BY rm.rolname
            ) AS member_of,
            ARRAY(
                SELECT
                    array[pgrm.name, pgrm.admin_option::text]
                FROM
                    (SELECT pg_roles.rolname AS name, pg_auth_members.admin_option AS admin_option FROM pg_roles
                    JOIN pg_auth_members ON pg_roles.oid=pg_auth_members.member AND pg_auth_members.roleid={0}) pgrm
            ) members
            from pg_roles pgr
            where oid={0}
        '''.format(oid), False)

    @lock_required
    def QueryTablespaces(self):
        return self.connection.Query('''
            select quote_ident(spcname) as tablespace_name,
                   oid
            from pg_tablespace
            order by spcname
        ''', True)

    @lock_required
    def QueryDatabases(self):
        return self.connection.Query('''
            select database_name,
                   oid,
                   quote_ident(database_name) as name_raw
            from (
            select datname as database_name,
                   1 as sort,
                   oid
            from pg_database
            where datname = 'postgres'
            union all
            select database_name,
                   1 + row_number() over() as sort,
                   oid
            from (
            select datname as database_name,
                   oid
            from pg_database
            where not datistemplate
              and datname <> 'postgres'
            order by datname asc
            ) x
            ) y
            order by sort
        ''', True)

    @lock_required
    def QueryExtensions(self):
        return self.connection.Query('''
            select extname as extension_name,
                 quote_ident(extname) as name_raw,
                oid, extversion
            from pg_extension
            order by extname
        ''', True)


    @lock_required
    def QueryAvailableExtensionsVersions(self):
        return self.connection.Query('''
                SELECT name, ARRAY_AGG(version ORDER BY version ASC) AS versions, MAX(comment) as comment, MAX(schema) as required_schema
                FROM pg_available_extension_versions
                WHERE name NOT IN (SELECT extname FROM pg_extension)
                GROUP BY name
                ORDER BY name ASC;
        ''')

    @lock_required
    def QueryExtensionByName(self, name):
        return self.connection.Query('''
            SELECT x.oid AS oid,
                pg_catalog.pg_get_userbyid(extowner) AS owner,
                x.extname AS name,
                n.nspname AS schema,
                bool_or(x.extrelocatable) AS relocatable,
                x.extversion AS version,
                e.comment as comment,
                ARRAY_AGG(r.version
                            ORDER BY r.version ASC) AS versions
            FROM pg_catalog.pg_extension x
            LEFT JOIN pg_catalog.pg_namespace n ON x.extnamespace=n.oid
            JOIN pg_catalog.pg_available_extensions() e(name, default_version, comment) ON x.extname=e.name
            JOIN pg_available_extension_versions r on x.extname=r.name
            WHERE x.extname = '%s'
            GROUP BY x.oid, x.extname, n.nspname, x.extrelocatable, x.extversion, e.comment;
        ''' % (name,))

    def QueryOptionNamesForCategory(self, catname):
        return self.connection.Query('''
        set local lc_messages to 'C';
        SELECT name
        FROM pg_settings
        WHERE category = '{0}'
        ORDER BY name;
    '''.format(catname))

    @lock_required
    def QueryConfiguration(self, exclude_read_only=False):
        namesQ = self.QueryOptionNamesForCategory('Preset Options')
        names = [f"'{x[0]}'"  for x in namesQ.Rows]
        where = ''
        if exclude_read_only:
            where = "WHERE name NOT IN ({})".format(','.join(names))

        return self.connection.Query('''
        SELECT name, setting,
      current_setting(name) AS current_setting,
        unit,
        vartype,
        min_val, max_val, enumvals,
        context, category,
        short_desc || ' ' || coalesce(extra_desc, '') AS desc,
        boot_val, reset_val,
        pending_restart,
        (name IN ({1})) AS is_preset_option
        FROM pg_settings
        {0}
        ORDER BY category, name
    '''.format(where, ','.join(names)), True)

    @lock_required
    def QueryConfigCategories(self):
        return self.connection.Query(
            '''
            SELECT DISTINCT(category) FROM pg_settings ORDER BY category
            ''', True)

    @lock_required
    def QuerySchemas(self):
        return self.connection.Query(
            '''
            SELECT
            schema_name,
            quote_ident(schema_name) AS name_raw,
            oid
            FROM
            (
                SELECT
                schema_name,
                oid
                FROM
                (
                    SELECT
                    nspname AS schema_name,
                    oid
                    FROM
                    pg_catalog.pg_namespace
                    WHERE
                    nspname NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
                    AND nspname NOT LIKE 'pg%%temp%%'
                    ORDER BY
                    nspname
                ) x
                UNION ALL
                SELECT
                schema_name,
                oid
                FROM
                (
                    SELECT
                    nspname AS schema_name,
                    oid
                    FROM
                    pg_catalog.pg_namespace
                    WHERE
                    nspname IN ('pg_catalog', 'information_schema')
                    ORDER BY
                    nspname DESC
                ) x
            ) y
            ''', True)

    @lock_required
    def QueryCurrentSchema(self):
        return self.connection.Query('Select current_schema();', True)

    @lock_required
    def QueryTables(self, all_schemas=False, schema=None):
        query_filter = ''
        if not all_schemas:
            if schema:
                query_filter = "and quote_ident(n.nspname) = '{0}' ".format(schema)
            else:
                query_filter = "and quote_ident(n.nspname) = '{0}' ".format(self.schema)
        else:
            query_filter = "and quote_ident(n.nspname) not in ('information_schema','pg_catalog') "
        return self.connection.Query('''
            with parents as (
                select distinct c.relname as table_name,
                       n.nspname as table_schema
                from pg_inherits i
                inner join pg_class c on c.oid = i.inhparent
                inner join pg_namespace n on n.oid = c.relnamespace
                inner join pg_class cc on cc.oid = i.inhrelid
                inner join pg_namespace nc on nc.oid = cc.relnamespace
                where c.relkind in ('r', 'p')
                {0}
            ),
            children as (
                select distinct c.relname as table_name,
                       n.nspname as table_schema
                from pg_inherits i
                inner join pg_class cp on cp.oid = i.inhparent
                inner join pg_namespace np on np.oid = cp.relnamespace
                inner join pg_class c on c.oid = i.inhrelid
                inner join pg_namespace n on n.oid = c.relnamespace
                where 1=1
                {0}
            )
            select c.relname as table_name,
                    quote_ident(c.relname) as name_raw,
                   quote_ident(n.nspname) as table_schema,
                   c.oid
            from pg_class c
            inner join pg_namespace n
            on n.oid = c.relnamespace
            left join parents p
            on p.table_name = quote_ident(c.relname)
            and p.table_schema = quote_ident(n.nspname)
            left join children ch
            on ch.table_name = quote_ident(c.relname)
            and ch.table_schema = quote_ident(n.nspname)
            where ch.table_name is null
              and c.relkind in ('r', 'p')
            {0}
            order by 2, 1
        '''.format(query_filter), True)

    @lock_required
    def QueryTablesFields(self, table=None, all_schemas=False, schema=None):
        query_filter = ''
        if not all_schemas:
            if table and schema:
                query_filter = "and quote_ident(n.nspname) = '{0}' and quote_ident(c.relname) = '{1}' ".format(schema, table)
            elif table:
                query_filter = "and quote_ident(n.nspname) = '{0}' and quote_ident(c.relname) = '{1}' ".format(self.schema, table)
            elif schema:
                query_filter = "and quote_ident(n.nspname) = '{0}' ".format(schema)
            else:
                query_filter = "and quote_ident(n.nspname) = '{0}' ".format(self.schema)
        else:
            if table:
                query_filter = "and quote_ident(n.nspname) not in ('information_schema','pg_catalog') and quote_ident(c.relname) = '{0}'".format(table)
            else:
                query_filter = "and quote_ident(n.nspname) not in ('information_schema','pg_catalog') "
        return self.connection.Query('''
            select quote_ident(c.relname) as table_name,
                   quote_ident(a.attname) as name_raw,
                    a.attname as column_name,
                   (case when t.typtype = 'd'::"char"
                         then case when bt.typelem <> 0::oid and bt.typlen = '-1'::integer
                                   then 'ARRAY'::text
                                   when nbt.nspname = 'pg_catalog'::name
                                   then format_type(t.typbasetype, NULL::integer)
                                   else 'USER-DEFINED'::text
                              end
                         else case when t.typelem <> 0::oid and t.typlen = '-1'::integer
                                   then 'ARRAY'::text
                                   when nt.nspname = 'pg_catalog'::name
                                   then format_type(a.atttypid, NULL::integer)
                                   else 'USER-DEFINED'::text
                              end
                    end) as data_type,
                   (case when a.attnotnull or t.typtype = 'd'::char and t.typnotnull
                         then 'NO'
                         else 'YES'
                    end
                   ) as nullable,
                   (select case when x.truetypmod = -1 /* default typmod */
                                then null
                                when x.truetypid in (1042, 1043) /* char, varchar */
                                then x.truetypmod - 4
                                when x.truetypid in (1560, 1562) /* bit, varbit */
                                then x.truetypmod
                                else null
                           end
                    from (
                        select (case when t.typtype = 'd'
                                     then t.typbasetype
                                     else a.atttypid
                                end
                               ) as truetypid,
                               (case when t.typtype = 'd'
                                     then t.typtypmod
                                     else a.atttypmod
                                end
                               ) as truetypmod
                    ) x
                   ) as data_length,
                   null as data_precision,
                   null as data_scale,
                   a.attnum AS position
            from pg_attribute a
            inner join pg_class c
            on c.oid = a.attrelid
            inner join pg_namespace n
            on n.oid = c.relnamespace
            inner join (
                pg_type t
                inner join pg_namespace nt
                on t.typnamespace = nt.oid
            ) on a.atttypid = t.oid
            left join (
                pg_type bt
                inner join pg_namespace nbt
                on bt.typnamespace = nbt.oid
            ) on t.typtype = 'd'::"char" and t.typbasetype = bt.oid
            where a.attnum > 0
              and not a.attisdropped
              and c.relkind in ('r', 'f', 'p')
              {0}
            order by quote_ident(c.relname),
                     a.attnum
        '''.format(query_filter), True)

    @lock_required
    def QueryTableDefinition(self, table=None, schema=None):
        in_schema = schema if schema else self.schema

        return self.connection.Query('''
            SELECT
            table_schema,
            table_name,
            column_name,
            is_nullable,
            ordinal_position,
            column_default,
            CASE
                WHEN character_maximum_length is not null  and udt_name != 'text'
                THEN CONCAT(udt_name, concat('(', concat(character_maximum_length::varchar(255), ')')))
                ELSE udt_name
            END as data_type,
            pg_catalog.col_description(format('%s.%s',isc.table_schema,quote_ident(isc.table_name))::regclass::oid,isc.ordinal_position) as comment
            FROM information_schema.columns isc
            WHERE table_schema = '{0}' AND table_name = '{1}'
            ORDER BY ordinal_position
        '''.format(in_schema, table), False)

    @lock_required
    def QueryTablePKColumns(self, table=None, schema=None):
        in_schema = schema if schema else self.schema

        return self.connection.Query('''
            SELECT a.attname as column_name
            FROM   pg_index i
            JOIN   pg_attribute a ON a.attrelid = i.indrelid
                                AND a.attnum = ANY(i.indkey)
            WHERE  i.indrelid = ('{0}' || '.' || quote_ident('{1}'))::regclass
            AND    i.indisprimary;
        '''.format(in_schema, table), True)

    @lock_required
    def QueryTablesForeignKeys(self, table=None, all_schemas=False, schema=None):
        query_filter = ''
        if not all_schemas:
            if table and schema:
                query_filter = "AND c.connamespace = '{0}'::regnamespace AND quote_ident(t.relname) = '{1}' ".format(schema, table)
            elif table:
                query_filter = "AND c.connamespace = '{0}'::regnamespace AND quote_ident(t.relname) = '{1}' ".format(self.schema, table)
            elif schema:
                query_filter = "AND c.connamespace = '{0}'::regnamespace ".format(schema)
            else:
                query_filter = "AND c.connamespace = '{0}'::regnamespace ".format(self.schema)
        else:
            if table:
                query_filter = "AND c.connamespace NOT IN ('information_schema'::regnamespace, 'pg_catalog'::regnamespace) AND quote_ident(t.relname) = {0}".format(table)
            else:
                query_filter = "AND c.connamespace NOT IN ('information_schema'::regnamespace, 'pg_catalog'::regnamespace) "
        return self.connection.Query('''
            SELECT DISTINCT quote_ident(c.conname) AS name_raw,
                            c.conname AS constraint_name,
                            quote_ident(t.relname) AS table_name,
                            quote_ident(rc.conname) AS r_constraint_name,
                            quote_ident(rt.relname) AS r_table_name,
                            quote_ident(tn.nspname) AS table_schema,
                            quote_ident(rtn.nspname) AS r_table_schema,
                            c.update_rule,
                            c.delete_rule,
                            c.oid,
                            lc.local_columns as column_name,
                            fc.foreign_columns as r_column_name      
            FROM (
                SELECT oid,
                       connamespace,
                       conname,
                       conrelid,
                       confrelid,
                       conkey,
                       confkey,
                       (CASE confupdtype WHEN 'c'
                                         THEN 'CASCADE'
                                         WHEN 'n'
                                         THEN 'SET NULL'
                                         WHEN 'd'
                                         THEN 'SET DEFAULT'
                                         WHEN 'r'
                                         THEN 'RESTRICT'
                                         WHEN 'a'
                                         THEN 'NO ACTION'
                        END) AS update_rule,
                       (CASE confdeltype WHEN 'c'
                                         THEN 'CASCADE'
                                         WHEN 'n'
                                         THEN 'SET NULL'
                                         WHEN 'd'
                                         THEN 'SET DEFAULT'
                                         WHEN 'r'
                                         THEN 'RESTRICT'
                                         WHEN 'a'
                                         THEN 'NO ACTION'
                        END) AS delete_rule
                FROM pg_constraint
                WHERE contype = 'f'
            ) c
            INNER JOIN pg_class t
                    ON c.conrelid = t.oid
            INNER JOIN pg_namespace tn
                    ON t.relnamespace = tn.oid
            INNER JOIN (
                SELECT objid,
                       refobjid
                FROM pg_depend
                WHERE classid = 'pg_constraint'::regclass::oid
                  AND refclassid = 'pg_class'::regclass::oid
                  AND refobjsubid = 0
            ) d1
                    ON c.oid = d1.objid
            INNER JOIN (
                SELECT objid,
                       refobjid
                FROM pg_depend
                WHERE refclassid = 'pg_constraint'::regclass::oid
                  AND classid = 'pg_class'::regclass::oid
                  AND deptype = 'i'
                  AND objsubid = 0
            ) d2
                    ON d1.refobjid = d2.objid
            INNER JOIN (
                SELECT oid,
                       conrelid,
                       connamespace,
                       conname
                FROM pg_constraint
                WHERE contype IN (
                    'p',
                    'u'
                )
            ) rc
                    ON d2.refobjid = rc.oid
                   AND c.confrelid = rc.conrelid
            INNER JOIN pg_class rt
                    ON rc.conrelid = rt.oid
            INNER JOIN pg_namespace rtn
                    ON rt.relnamespace = rtn.oid
                    
            -- Local column names
            LEFT JOIN LATERAL (
                SELECT string_agg(quote_ident(att.attname), ', ') AS local_columns
                FROM unnest(c.conkey) WITH ORDINALITY AS cols(attnum, ord)
                JOIN pg_attribute att ON att.attrelid = c.conrelid AND att.attnum = cols.attnum
            ) AS lc ON true

            -- Foreign column names
            LEFT JOIN LATERAL (
                SELECT string_agg(quote_ident(att.attname), ', ') AS foreign_columns
                FROM unnest(c.confkey) WITH ORDINALITY AS cols(attnum, ord)
                JOIN pg_attribute att ON att.attrelid = c.confrelid AND att.attnum = cols.attnum
            ) AS fc ON true

            WHERE 1 = 1
            {0}
            ORDER BY quote_ident(c.conname),
                     quote_ident(t.relname)
        '''.format(query_filter), True)

    @lock_required
    def QueryTablesForeignKeysColumns(self, fkey, table=None, all_schemas=False, schema=None):
        query_filter = ''
        if not all_schemas:
            if table and schema:
                query_filter = "and quote_ident(rc.constraint_schema) = '{0}' and quote_ident(kcu1.table_name) = '{1}' ".format(schema, table)
            elif table:
                query_filter = "and quote_ident(rc.constraint_schema) = '{0}' and quote_ident(kcu1.table_name) = '{1}' ".format(self.schema, table)
            elif schema:
                query_filter = "and quote_ident(rc.constraint_schema) = '{0}' ".format(schema)
            else:
                query_filter = "and quote_ident(rc.constraint_schema) = '{0}' ".format(self.schema)
        else:
            if table:
                query_filter = "and quote_ident(rc.constraint_schema) not in ('information_schema','pg_catalog') and quote_ident(kcu1.table_name) = {0}".format(table)
            else:
                query_filter = "and quote_ident(rc.constraint_schema) not in ('information_schema','pg_catalog') "


        if type(fkey) == list:
            fkeys = fkey
        else:
            fkeys = [fkey]

        fkey_list = ', '.join(list(f'\'{str(e)}\'' for e in fkeys))

        if fkey_list:
            query_filter = query_filter + "and quote_ident(kcu1.constraint_name) in ({0}) ".format(fkey_list)

        return self.connection.Query('''
            select *
            from (select distinct
                         quote_ident(kcu1.constraint_name) as constraint_name,
                         quote_ident(kcu1.table_name) as table_name,
                         quote_ident(kcu1.column_name) as column_name,
                         quote_ident(kcu2.constraint_name) as r_constraint_name,
                         quote_ident(kcu2.table_name) as r_table_name,
                         quote_ident(kcu2.column_name) as r_column_name,
                         quote_ident(kcu1.constraint_schema) as table_schema,
                         quote_ident(kcu2.constraint_schema) as r_table_schema,
                         rc.update_rule as update_rule,
                         rc.delete_rule as delete_rule,
                         kcu1.ordinal_position
            from information_schema.referential_constraints rc
            join information_schema.key_column_usage kcu1
            on kcu1.constraint_catalog = rc.constraint_catalog
            and kcu1.constraint_schema = rc.constraint_schema
            and kcu1.constraint_name = rc.constraint_name
            join information_schema.key_column_usage kcu2
            on kcu2.constraint_catalog = rc.unique_constraint_catalog
            and kcu2.constraint_schema = rc.unique_constraint_schema
            and kcu2.constraint_name = rc.unique_constraint_name
            and kcu2.ordinal_position = kcu1.ordinal_position
            where 1 = 1
            {0}
            ) t
            order by ordinal_position
        '''.format(query_filter), True)

    @lock_required
    def QueryTablesPrimaryKeys(self, table=None, all_schemas=False, schema=None):
        if self.version_num < 90500:
            table_schema_column = "quote_ident(n.nspname)"
            join_namespace = "INNER JOIN pg_namespace n ON t.relnamespace = n.oid"
        else:  # PostgreSQL ≥ 9.5
            table_schema_column = "quote_ident(t.relnamespace::regnamespace::text)"
            join_namespace = ""

        query_filter = ''
        if not all_schemas:
            if table and schema:
                query_filter = f"AND {table_schema_column} = '{schema}' AND quote_ident(t.relname) = '{table}' "
            elif table:
                query_filter = f"AND {table_schema_column} = '{self.schema}' AND quote_ident(t.relname) = '{table}' "
            elif schema:
                query_filter = f"AND {schema} = '{table_schema_column}' "
            else:
                query_filter = f"AND {table_schema_column} = '{self.schema}' "
        else:
            if table:
                query_filter = f"AND {table_schema_column} NOT IN ('information_schema','pg_catalog') AND quote_ident(t.relname) = {table}"
            else:
                query_filter = f"AND {table_schema_column} NOT IN ('information_schema','pg_catalog') "
        return self.connection.Query(f'''
            SELECT quote_ident(c.conname) AS name_raw,
                   c.conname AS constraint_name,
                   quote_ident(t.relname) AS table_name,
                   {table_schema_column} AS table_schema,
                   c.oid
            FROM (
                SELECT oid,
                       conrelid,
                       conname
                FROM pg_constraint
                WHERE contype = 'p'
            ) c
            INNER JOIN pg_class t
                    ON c.conrelid = t.oid
            {join_namespace}
            WHERE 1 = 1
              {query_filter}
            ORDER BY quote_ident(c.conname),
                      {table_schema_column}
        ''', True)

    @lock_required
    def QueryTablesPrimaryKeysColumns(self, pkey, table=None, all_schemas=False, schema=None):
        query_filter = ''
        if not all_schemas:
            if table and schema:
                query_filter = "and quote_ident(tc.table_schema) = '{0}' and quote_ident(tc.table_name) = '{1}' ".format(schema, table)
            elif table:
                query_filter = "and quote_ident(tc.table_schema) = '{0}' and quote_ident(tc.table_name) = '{1}' ".format(self.schema, table)
            elif schema:
                query_filter = "and quote_ident(tc.table_schema) = '{0}' ".format(schema)
            else:
                query_filter = "and quote_ident(tc.table_schema) = '{0}' ".format(self.schema)
        else:
            if table:
                query_filter = "and quote_ident(tc.table_schema) not in ('information_schema','pg_catalog') and quote_ident(tc.table_name) = {0}".format(table)
            else:
                query_filter = "and quote_ident(tc.table_schema) not in ('information_schema','pg_catalog') "
        query_filter = query_filter + "and quote_ident(tc.constraint_name) = '{0}' ".format(pkey)
        return self.connection.Query('''
            select quote_ident(kc.column_name) as column_name
            from information_schema.table_constraints tc
            join information_schema.key_column_usage kc
            on kc.table_name = tc.table_name
            and kc.table_schema = tc.table_schema
            and kc.constraint_name = tc.constraint_name
            where tc.constraint_type = 'PRIMARY KEY'
            {0}
            order by kc.ordinal_position
        '''.format(query_filter), True)

    @lock_required
    def QueryTablesUniques(self, table=None, all_schemas=False, schema=None):
        query_filter = ''
        if not all_schemas:
            if table and schema:
                query_filter = "AND quote_ident(t.relnamespace::regnamespace::text) = '{0}' AND quote_ident(t.relname) = '{1}' ".format(schema, table)
            elif table:
                query_filter = "AND quote_ident(t.relnamespace::regnamespace::text) = '{0}' AND quote_ident(t.relname) = '{1}' ".format(self.schema, table)
            elif schema:
                query_filter = "AND quote_ident(t.relnamespace::regnamespace::text) = '{0}' ".format(schema)
            else:
                query_filter = "AND quote_ident(t.relnamespace::regnamespace::text) = '{0}' ".format(self.schema)
        else:
            if table:
                query_filter = "AND quote_ident(t.relnamespace::regnamespace::text) NOT IN ('information_schema','pg_catalog') AND quote_ident(t.relname) = {0}".format(table)
            else:
                query_filter = "AND quote_ident(t.relnamespace::regnamespace::text) NOT IN ('information_schema','pg_catalog') "
        return self.connection.Query('''
            SELECT quote_ident(c.conname) AS name_raw,
                   c.conname AS constraint_name,
                   quote_ident(t.relname) AS table_name,
                   quote_ident(t.relnamespace::regnamespace::text) AS table_schema,
                   c.oid
            FROM (
                SELECT oid,
                       conrelid,
                       conname
                FROM pg_constraint
                WHERE contype = 'u'
            ) c
            INNER JOIN pg_class t
                    ON c.conrelid = t.oid
            WHERE 1 = 1
              {0}
            ORDER BY quote_ident(c.conname),
                     quote_ident(t.relnamespace::regnamespace::text)
        '''.format(query_filter), True)

    @lock_required
    def QueryTablesUniquesColumns(self, unique_name, table=None, all_schemas=False, schema=None):
        query_filter = ''
        if not all_schemas:
            if table and schema:
                query_filter = "and quote_ident(tc.table_schema) = '{0}' and quote_ident(tc.table_name) = '{1}' ".format(schema, table)
            elif table:
                query_filter = "and quote_ident(tc.table_schema) = '{0}' and quote_ident(tc.table_name) = '{1}' ".format(self.schema, table)
            elif schema:
                query_filter = "and quote_ident(tc.table_schema) = '{0}' ".format(schema)
            else:
                query_filter = "and quote_ident(tc.table_schema) = '{0}' ".format(self.schema)
        else:
            if table:
                query_filter = "and quote_ident(tc.table_schema) not in ('information_schema','pg_catalog') and quote_ident(tc.table_name) = {0}".format(table)
            else:
                query_filter = "and quote_ident(tc.table_schema) not in ('information_schema','pg_catalog') "
        query_filter = query_filter + "and quote_ident(tc.constraint_name) = '{0}' ".format(unique_name)
        return self.connection.Query('''
            select quote_ident(kc.column_name) as column_name
            from information_schema.table_constraints tc
            join information_schema.key_column_usage kc
            on kc.table_name = tc.table_name
            and kc.table_schema = tc.table_schema
            and kc.constraint_name = tc.constraint_name
            where tc.constraint_type = 'UNIQUE'
            {0}
            order by kc.ordinal_position
        '''.format(query_filter), True)

    @lock_required
    def QueryTablesIndexes(self, table=None, all_schemas=False, schema=None):
        return self.QueryTablesIndexesHelper(table, all_schemas, schema)

    def QueryTablesIndexesHelper(self, table=None, all_schemas=False, schema=None):
        query_filter = ''
        if not all_schemas:
            if table and schema:
                query_filter = "and quote_ident(n.nspname) = '{0}' and quote_ident(c.relname) = '{1}' ".format(schema, table)
            elif table:
                query_filter = "and quote_ident(n.nspname) = '{0}' and quote_ident(c.relname) = '{1}' ".format(self.schema, table)
            elif schema:
                query_filter = "and quote_ident(n.nspname) = '{0}' ".format(schema)
            else:
                query_filter = "and quote_ident(n.nspname) = '{0}' ".format(self.schema)
        else:
            if table:
                query_filter = "and quote_ident(n.nspname) not in ('information_schema','pg_catalog') and quote_ident(c.relname) = {0}".format(table)
            else:
                query_filter = "and quote_ident(n.nspname) not in ('information_schema','pg_catalog') "
        return self.connection.Query('''
            select quote_ident(c.relname) as table_name,
                   quote_ident(ci.relname) as name_raw,
                   ci.relname as index_name,
                   i.indisprimary as is_primary,
                   (case when i.indisunique then 'Unique' else 'Non Unique' end) as uniqueness,
                   quote_ident(n.nspname) as schema_name,
                   format(
                       '%s;',
                       pg_get_indexdef(i.indexrelid)
                   ) AS definition,
                   ci.oid,
                   array_agg(quote_ident(a.attname)) AS columns,
                am.amname AS method,
                pg_get_expr(i.indpred, i.indrelid, true) AS constraint
            from pg_index i
            inner join pg_class ci
            on ci.oid = i.indexrelid
            inner join pg_namespace ni
            on ni.oid = ci.relnamespace
            inner join pg_class c
            on c.oid = i.indrelid
            inner join pg_namespace n
            on n.oid = c.relnamespace
            inner join pg_attribute a 
            on a.attrelid = c.oid AND a.attnum = ANY(i.indkey)
            inner join pg_am am on ci.relam = am.oid
            where i.indisvalid
              and i.indislive
              {0}
            group by c.relname, ci.relname, ci.oid, i.indisprimary, i.indisunique, n.nspname, i.indexrelid, am.amname
            order by 1, 2
        '''.format(query_filter), True)

    @lock_required
    def QueryTablesIndexesColumns(self, index_name, table=None, all_schemas=False, schema=None):
        query_filter = ''
        if not all_schemas:
            if table and schema:
                query_filter = "and quote_ident(n.nspname) = '{0}' and quote_ident(c.relname) = '{1}' ".format(schema, table)
            elif table:
                query_filter = "and quote_ident(n.nspname) = '{0}' and quote_ident(c.relname) = '{1}' ".format(self.schema, table)
            elif schema:
                query_filter = "and quote_ident(n.nspname) = '{0}' ".format(schema)
            else:
                query_filter = "and quote_ident(n.nspname) = '{0}' ".format(self.schema)
        else:
            if table:
                query_filter = "and quote_ident(n.nspname) not in ('information_schema','pg_catalog') and quote_ident(c.relname) = {0}".format(table)
            else:
                query_filter = "and quote_ident(n.nspname) not in ('information_schema','pg_catalog') "
        query_filter = query_filter + "and quote_ident(ci.relname) = '{0}' ".format(index_name)
        return self.connection.Query('''
            select unnest(string_to_array(replace(substr(t.indexdef, strpos(t.indexdef, '(')+1, strpos(t.indexdef, ')')-strpos(t.indexdef, '(')-1), ' ', ''),',')) as column_name
            from (
            select pg_get_indexdef(i.indexrelid) as indexdef
            from pg_index i
            inner join pg_class ci
            on ci.oid = i.indexrelid
            inner join pg_namespace ni
            on ni.oid = ci.relnamespace
            inner join pg_class c
            on c.oid = i.indrelid
            inner join pg_namespace n
            on n.oid = c.relnamespace
            where i.indisvalid
              and i.indislive
              {0}
            ) t
        '''.format(query_filter), True)

    @lock_required
    def QueryTablesChecks(self, table=None, all_schemas=False, schema=None):
        query_filter = ''
        if not all_schemas:
            if table and schema:
                query_filter = "and quote_ident(n.nspname) = '{0}' and quote_ident(t.relname) = '{1}' ".format(schema, table)
            elif table:
                query_filter = "and quote_ident(n.nspname) = '{0}' and quote_ident(t.relname) = '{1}' ".format(self.schema, table)
            elif schema:
                query_filter = "and quote_ident(n.nspname) = '{0}' ".format(schema)
            else:
                query_filter = "and quote_ident(n.nspname) = '{0}' ".format(self.schema)
        else:
            if table:
                query_filter = "and quote_ident(n.nspname) not in ('information_schema','pg_catalog') and quote_ident(t.relname) = {0}".format(table)
            else:
                query_filter = "and quote_ident(n.nspname) not in ('information_schema','pg_catalog') "
        return self.connection.Query('''
            select quote_ident(n.nspname) as schema_name,
                   quote_ident(t.relname) as table_name,
                   quote_ident(c.conname) as name_raw,
                   c.conname as constraint_name,
                   pg_get_constraintdef(c.oid) as constraint_source,
                   c.oid
            from pg_constraint c
            join pg_class t
            on t.oid = c.conrelid
            join pg_namespace n
            on t.relnamespace = n.oid
            where contype = 'c'
            {0}
            order by 1, 2, 3
        '''.format(query_filter), True)

    @lock_required
    def QueryTablesExcludes(self, table=None, all_schemas=False, schema=None):
        query_filter = ''
        if not all_schemas:
            if table and schema:
                query_filter = "and quote_ident(n.nspname) = '{0}' and quote_ident(t.relname) = '{1}' ".format(schema, table)
            elif table:
                query_filter = "and quote_ident(n.nspname) = '{0}' and quote_ident(t.relname) = '{1}' ".format(self.schema, table)
            elif schema:
                query_filter = "and quote_ident(n.nspname) = '{0}' ".format(schema)
            else:
                query_filter = "and quote_ident(n.nspname) = '{0}' ".format(self.schema)
        else:
            if table:
                query_filter = "and quote_ident(n.nspname) not in ('information_schema','pg_catalog') and quote_ident(t.relname) = {0}".format(table)
            else:
                query_filter = "and quote_ident(n.nspname) not in ('information_schema','pg_catalog') "
        return self.connection.Query('''
            create or replace function pg_temp.fnc_omnidb_exclude_ops(text, text, text)
            returns text as $$
            select array_to_string(array(
            select oprname
            from (
            select o.oprname
            from (
            select unnest(c.conexclop) as conexclop
            from pg_constraint c
            join pg_class t
            on t.oid = c.conrelid
            join pg_namespace n
            on t.relnamespace = n.oid
            where contype = 'x'
              and quote_ident(n.nspname) = $1
              and quote_ident(t.relname) = $2
              and quote_ident(c.conname) = $3
            ) x
            inner join pg_operator o
            on o.oid = x.conexclop
            ) t
            ), ',')
            $$ language sql;
            create or replace function pg_temp.fnc_omnidb_exclude_attrs(text, text, text)
            returns text as $$
            select array_to_string(array(
            select a.attname
            from (
            select unnest(c.conkey) as conkey
            from pg_constraint c
            join pg_class t
            on t.oid = c.conrelid
            join pg_namespace n
            on t.relnamespace = n.oid
            where contype = 'x'
              and quote_ident(n.nspname) = $1
              and quote_ident(t.relname) = $2
              and quote_ident(c.conname) = $3
            ) x
            inner join pg_attribute a
            on a.attnum = x.conkey
            inner join pg_class r
            on r.oid = a.attrelid
            inner join pg_namespace n
            on n.oid = r.relnamespace
            where quote_ident(n.nspname) = $1
              and quote_ident(r.relname) = $2
            ), ',')
            $$ language sql;
            select quote_ident(n.nspname) as schema_name,
                   quote_ident(t.relname) as table_name,
                   quote_ident(c.conname) as name_raw,
                   c.conname as constraint_name,
                   pg_temp.fnc_omnidb_exclude_ops(
                       quote_ident(n.nspname),
                       quote_ident(t.relname),
                       quote_ident(c.conname)
                   ) as operations,
                   pg_temp.fnc_omnidb_exclude_attrs(
                       quote_ident(n.nspname),
                       quote_ident(t.relname),
                       quote_ident(c.conname)
                   ) as attributes,
                   c.oid
            from pg_constraint c
            join pg_class t
            on t.oid = c.conrelid
            join pg_namespace n
            on t.relnamespace = n.oid
            where contype = 'x'
            {0}
            order by 1, 2, 3
        '''.format(query_filter), True)

    @lock_required
    def QueryTablesRules(self, table=None, all_schemas=False, schema=None):
        query_filter = ''
        if not all_schemas:
            if table and schema:
                query_filter = "and quote_ident(schemaname) = '{0}' and quote_ident(tablename) = '{1}' ".format(schema, table)
            elif table:
                query_filter = "and quote_ident(schemaname) = '{0}' and quote_ident(tablename) = '{1}' ".format(self.schema, table)
            elif schema:
                query_filter = "and quote_ident(schemaname) = '{0}' ".format(schema)
            else:
                query_filter = "and quote_ident(schemaname) = '{0}' ".format(self.schema)
        else:
            if table:
                query_filter = "and quote_ident(schemaname) not in ('information_schema','pg_catalog') and quote_ident(tablename) = {0}".format(table)
            else:
                query_filter = "and quote_ident(schemaname) not in ('information_schema','pg_catalog') "
        return self.connection.Query('''
            select quote_ident(r.schemaname) as table_schema,
                   quote_ident(r.tablename) as table_name,
                   quote_ident(r.rulename) as name_raw,
                   r.rulename as rule_name,
                   rw.oid
            from pg_rules r
            INNER JOIN pg_rewrite rw
                    ON r.rulename = rw.rulename
            where 1 = 1
            {0}
            order by 1, 2, 3
        '''.format(query_filter), True)

    @lock_required
    def GetRuleDefinition(self, rule, table, schema):
        return self.connection.ExecuteScalar('''
            select r.definition ||
                   (CASE WHEN obj_description(rw.oid, 'pg_rewrite') IS NOT NULL
                         THEN format(
                                 E'\n\nCOMMENT ON RULE %s ON %s IS %s;',
                                 quote_ident(r.rulename),
                                 quote_ident(rw.ev_class::regclass::text),
                                 quote_literal(obj_description(rw.oid, 'pg_rewrite'))
                             )
                         ELSE ''
                    END)
            from pg_rules r
            INNER JOIN pg_rewrite rw
                    ON r.rulename = rw.rulename
            where quote_ident(r.schemaname) = '{0}'
              and quote_ident(r.tablename) = '{1}'
              and quote_ident(r.rulename) = '{2}'
        '''.format(schema, table, rule)).replace('CREATE RULE', 'CREATE OR REPLACE RULE')

    @lock_required
    def QueryEventTriggers(self):
        return self.connection.Query('''
            select quote_ident(t.evtname) as name_raw,
                   t.evtname as trigger_name,
                   t.evtenabled as trigger_enabled,
                   t.evtevent as event_name,
                   quote_ident(np.nspname) || '.' || quote_ident(p.proname) as trigger_function,
                   quote_ident(np.nspname) || '.' || quote_ident(p.proname) || '()' as id,
                   p.oid AS function_oid,
                   t.oid
            from pg_event_trigger t
            inner join pg_proc p
            on p.oid = t.evtfoid
            inner join pg_namespace np
            on np.oid = p.pronamespace
        ''')

    @lock_required
    def QueryTablesTriggers(self, table=None, all_schemas=False, schema=None):
        query_filter = ''
        if not all_schemas:
            if table and schema:
                query_filter = "and quote_ident(n.nspname) = '{0}' and quote_ident(c.relname) = '{1}' ".format(schema, table)
            elif table:
                query_filter = "and quote_ident(n.nspname) = '{0}' and quote_ident(c.relname) = '{1}' ".format(self.schema, table)
            elif schema:
                query_filter = "and quote_ident(n.nspname) = '{0}' ".format(schema)
            else:
                query_filter = "and quote_ident(n.nspname) = '{0}' ".format(self.schema)
        else:
            if table:
                query_filter = "and quote_ident(n.nspname) not in ('information_schema','pg_catalog') and quote_ident(c.relname) = {0}".format(table)
            else:
                query_filter = "and quote_ident(n.nspname) not in ('information_schema','pg_catalog') "
        return self.connection.Query('''
            select quote_ident(n.nspname) as schema_name,
                   quote_ident(c.relname) as table_name,
                   quote_ident(t.tgname) as name_raw,
                   t.tgname as trigger_name,
                   t.tgenabled as trigger_enabled,
                   quote_ident(np.nspname) || '.' || quote_ident(p.proname) as trigger_function,
                   quote_ident(np.nspname) || '.' || quote_ident(p.proname) || '(' || oidvectortypes(p.proargtypes) || ')' as id,
                   p.oid AS function_oid,
                   t.oid
            from pg_trigger t
            inner join pg_class c
            on c.oid = t.tgrelid
            inner join pg_namespace n
            on n.oid = c.relnamespace
            inner join pg_proc p
            on p.oid = t.tgfoid
            inner join pg_namespace np
            on np.oid = p.pronamespace
            where not t.tgisinternal
            {0}
            order by 1, 2, 3
        '''.format(query_filter), True)

    @lock_required
    def QueryTablesInheriteds(self, table=None, all_schemas=False, schema=None):
        query_filter = ''
        if not all_schemas:
            if table and schema:
                query_filter = "and quote_ident(np.nspname) = '{0}' and quote_ident(cp.relname) = '{1}' ".format(schema, table)
            elif table:
                query_filter = "and quote_ident(np.nspname) = '{0}' and quote_ident(cp.relname) = '{1}' ".format(self.schema, table)
            elif schema:
                query_filter = "and quote_ident(np.nspname) = '{0}' ".format(schema)
            else:
                query_filter = "and quote_ident(np.nspname) = '{0}' ".format(self.schema)
        else:
            if table:
                query_filter = "and quote_ident(np.nspname) not in ('information_schema','pg_catalog') and quote_ident(cp.relname) = {0}".format(table)
            else:
                query_filter = "and quote_ident(np.nspname) not in ('information_schema','pg_catalog') "
        if self.version_num >= 100000:
            return self.connection.Query('''
                select quote_ident(np.nspname) as parent_schema,
                       quote_ident(cp.relname) as parent_table,
                       quote_ident(nc.nspname) as child_schema,
                       quote_ident(cc.relname) as child_table
                from pg_inherits i
                inner join pg_class cp on cp.oid = i.inhparent
                inner join pg_namespace np on np.oid = cp.relnamespace
                inner join pg_class cc on cc.oid = i.inhrelid
                inner join pg_namespace nc on nc.oid = cc.relnamespace
                where not cc.relispartition
                {0}
                order by 1, 2, 3, 4
            '''.format(query_filter))
        else:
            return self.connection.Query('''
                select quote_ident(np.nspname) as parent_schema,
                       quote_ident(cp.relname) as parent_table,
                       quote_ident(nc.nspname) as child_schema,
                       quote_ident(cc.relname) as child_table
                from pg_inherits i
                inner join pg_class cp on cp.oid = i.inhparent
                inner join pg_namespace np on np.oid = cp.relnamespace
                inner join pg_class cc on cc.oid = i.inhrelid
                inner join pg_namespace nc on nc.oid = cc.relnamespace
                where 1 = 1
                {0}
                order by 1, 2, 3, 4
            '''.format(query_filter))

    @lock_required
    def QueryTablesInheritedsParents(self, all_schemas=False, schema=None):
        query_filter = ''
        if not all_schemas:
            if schema:
                query_filter = "and quote_ident(n.nspname) = '{0}' ".format(schema)
            else:
                query_filter = "and quote_ident(n.nspname) = '{0}' ".format(self.schema)
        else:
            query_filter = "and quote_ident(n.nspname) not in ('information_schema','pg_catalog') "
        return self.connection.Query('''
            select distinct quote_ident(cp.relname) as name_raw,
                        cp.relname as table_name,
                   np.nspname as table_schema,
                quote_ident(np.nspname) as table_schema_raw
            from pg_inherits i
            inner join pg_class cp on cp.oid = i.inhparent
            inner join pg_namespace np on np.oid = cp.relnamespace
            inner join pg_class c on c.oid = i.inhrelid
            inner join pg_namespace n on n.oid = c.relnamespace
            where cp.relkind = 'r'
            {0}
            order by 2, 1
        '''.format(query_filter))

    @lock_required
    def QueryTablesInheritedsChildren(self, table, schema):
            return self.connection.Query('''
                select quote_ident(cc.relname) as name_raw,
                       cc.relname as table_name,
                       quote_ident(nc.nspname) as table_schema,
                       cc.oid
                from pg_inherits i
                inner join pg_class cp on cp.oid = i.inhparent
                inner join pg_namespace np on np.oid = cp.relnamespace
                inner join pg_class cc on cc.oid = i.inhrelid
                inner join pg_namespace nc on nc.oid = cc.relnamespace
                where not cc.relispartition
                  and quote_ident(np.nspname) || '.' || quote_ident(cp.relname) = '{0}'
                  and quote_ident(nc.nspname) = '{1}'
                order by 2, 1
            '''.format(table, schema))

    @lock_required
    def QueryTablesPartitions(self, table=None, all_schemas=False, schema=None):
        query_filter = ''
        if not all_schemas:
            if table and schema:
                query_filter = "and quote_ident(np.nspname) = '{0}' and quote_ident(cp.relname) = '{1}' ".format(schema, table)
            elif table:
                query_filter = "and quote_ident(np.nspname) = '{0}' and quote_ident(cp.relname) = '{1}' ".format(self.schema, table)
            elif schema:
                query_filter = "and quote_ident(np.nspname) = '{0}' ".format(schema)
            else:
                query_filter = "and quote_ident(np.nspname) = '{0}' ".format(self.schema)
        else:
            if table:
                query_filter = "and quote_ident(np.nspname) not in ('information_schema','pg_catalog') and quote_ident(cp.relname) = {0}".format(table)
            else:
                query_filter = "and quote_ident(np.nspname) not in ('information_schema','pg_catalog') "
        return self.connection.Query('''
            select quote_ident(np.nspname) as parent_schema,
                   quote_ident(cp.relname) as parent_table,
                   quote_ident(nc.nspname) as child_schema,
                   quote_ident(cc.relname) as child_table
            from pg_inherits i
            inner join pg_class cp on cp.oid = i.inhparent
            inner join pg_namespace np on np.oid = cp.relnamespace
            inner join pg_class cc on cc.oid = i.inhrelid
            inner join pg_namespace nc on nc.oid = cc.relnamespace
            where cc.relispartition
            {0}
            order by 1, 2, 3, 4
        '''.format(query_filter))

    @lock_required
    def QueryTablesPartitionsParents(self, all_schemas=False, schema=None):
        query_filter = ''
        if not all_schemas:
            if schema:
                query_filter = "and quote_ident(n.nspname) = '{0}' ".format(schema)
            else:
                query_filter = "and quote_ident(n.nspname) = '{0}' ".format(self.schema)
        else:
            query_filter = "and quote_ident(n.nspname) not in ('information_schema','pg_catalog') "
        return self.connection.Query('''
            select distinct quote_ident(cp.relname) as name_raw,
                            cp.relname as table_name,
                   quote_ident(np.nspname) as table_schema_raw,
                    np.nspname as table_schema
            from pg_inherits i
            inner join pg_class cp on cp.oid = i.inhparent
            inner join pg_namespace np on np.oid = cp.relnamespace
            inner join pg_class c on c.oid = i.inhrelid
            inner join pg_namespace n on n.oid = c.relnamespace
            where cp.relkind = 'p'
            {0}
            order by 2, 1
        '''.format(query_filter))

    @lock_required
    def QueryTablesPartitionsChildren(self, table, schema):
        return self.connection.Query('''
            select quote_ident(cc.relname) as name_raw,
                   cc.relname as table_name,
                   quote_ident(nc.nspname) as table_schema,
                   cc.oid
            from pg_inherits i
            inner join pg_class cp on cp.oid = i.inhparent
            inner join pg_namespace np on np.oid = cp.relnamespace
            inner join pg_class cc on cc.oid = i.inhrelid
            inner join pg_namespace nc on nc.oid = cc.relnamespace
            where cc.relispartition
              and quote_ident(np.nspname) || '.' || quote_ident(cp.relname) = '{0}'
              and quote_ident(nc.nspname) = '{1}'
            order by 2, 1
        '''.format(table, schema))

    @lock_required
    def QueryTablesStatistics(self, table=None, all_schemas=False, schema=None):
        query_filter = ''

        if not all_schemas:
            if table and schema:
                query_filter = "AND quote_ident(n.nspname) = '{0}' AND quote_ident(c.relname) = '{1}' ".format(schema, table)
            elif table:
                query_filter = "AND quote_ident(n.nspname) = '{0}' AND quote_ident(c.relname) = '{1}' ".format(self.schema, table)
            elif schema:
                query_filter = "AND quote_ident(n.nspname) = '{0}' ".format(schema)
            else:
                query_filter = "AND quote_ident(n.nspname) = '{0}' ".format(self.schema)
        else:
            if table:
                query_filter = "AND quote_ident(n.nspname) NOT IN ('information_schema','pg_catalog') AND quote_ident(c.relname) = {0}".format(table)
            else:
                query_filter = "AND quote_ident(n.nspname) NOT IN ('information_schema','pg_catalog') "

        return self.connection.Query(
            '''
                select quote_ident(c.relname) AS table_name,
                       quote_ident(se.stxname) AS name_raw,
                       se.stxname AS statistic_name,
                       quote_ident(n2.nspname) AS schema_name,
                       se.oid
                FROM pg_statistic_ext se
                INNER JOIN pg_class c
                        ON se.stxrelid = c.oid
                INNER JOIN pg_namespace n
                        ON c.relnamespace = n.oid
                INNER JOIN pg_namespace n2
                        ON se.stxnamespace = n2.oid
                WHERE 1 = 1
                  {0}
                ORDER BY 1,
                         3,
                         2
            '''.format(
                query_filter
            ),
            True
        )

    @lock_required
    def QueryStatisticsFields(self, statistics_name=None, all_schemas=False, schema=None):
        query_filter = ''

        if not all_schemas:
            if statistics_name and schema:
                query_filter = "AND quote_ident(n2.nspname) = '{0}' AND quote_ident(se.stxname) = '{1}' ".format(schema, statistics_name)
            elif statistics_name:
                query_filter = "AND quote_ident(n2.nspname) = '{0}' AND quote_ident(se.stxname) = '{1}' ".format(self.schema, statistics_name)
            elif schema:
                query_filter = "AND quote_ident(n2.nspname) = '{0}' ".format(schema)
            else:
                query_filter = "AND quote_ident(n2.nspname) = '{0}' ".format(self.schema)
        else:
            if statistics_name:
                query_filter = "AND quote_ident(n2.nspname) NOT IN ('information_schema','pg_catalog') AND quote_ident(se.stxname) = {0}".format(statistics_name)
            else:
                query_filter = "AND quote_ident(n2.nspname) NOT IN ('information_schema','pg_catalog') "

        return self.connection.Query(
            '''
                select quote_ident(n2.nspname) AS schema_name,
                       quote_ident(se.stxname) AS statistic_name,
                       quote_ident(a.attname) AS column_name
                FROM pg_statistic_ext se
                INNER JOIN pg_class c
                        ON se.stxrelid = c.oid
                INNER JOIN pg_namespace n
                        ON c.relnamespace = n.oid
                INNER JOIN pg_namespace n2
                        ON se.stxnamespace = n2.oid
                INNER JOIN pg_attribute a
                        ON c.oid = a.attrelid
                       AND a.attnum = ANY(se.stxkeys)
                WHERE 1 = 1
                  {0}
                ORDER BY 1,
                         2,
                         3
            '''.format(
                query_filter
            ),
            True
        )

    @lock_required
    def QueryDataLimited(self, query, count=-1):
        if count != -1:
            try:
                self.connection.Open()
                data = self.connection.QueryBlock(query + ' limit {0}'.format(count), count, True)
                self.connection.Close()
                return data
            except Spartacus.Database.Exception as exc:
                try:
                    self.connection.Cancel()
                except:
                    pass
                raise exc
        else:
            return self.connection.Query(query, True)

    @lock_required
    def QueryTableRecords(self, column_list, table, schema, query_filter, count=-1):
        table_name = "{0}.{1}".format(schema, table) if schema else table

        limit = ''
        if count != -1:
            limit = ' limit ' + count
        return self.connection.Query('''
            select {0}
            from {1} t
            {2}
            {3}
        '''.format(
                column_list,
                table_name,
                query_filter,
                limit
            ), True
        )

    @lock_required
    def QueryFunctions(self, all_schemas=False, schema=None):
        query_filter = ''
        if not all_schemas:
            if schema:
                query_filter = "and quote_ident(n.nspname) = '{0}' ".format(schema)
            else:
                query_filter = "and quote_ident(n.nspname) = '{0}' ".format(self.schema)
        else:
            query_filter = "and quote_ident(n.nspname) not in ('information_schema','pg_catalog') "

        return self.connection.Query('''
            select quote_ident(n.nspname) || '.' || quote_ident(p.proname) || '(' || oidvectortypes(p.proargtypes) || ')' as id,
                    quote_ident(p.proname) as name_raw,
                    p.proname as name,
                    quote_ident(n.nspname) as schema_name,
                    p.oid AS function_oid
            from pg_proc p
            join pg_namespace n
            on p.pronamespace = n.oid
            where p.prokind = 'f'
                and format_type(p.prorettype, null) not in ('trigger', 'event_trigger')
            {0}
            order by 1
        '''.format(query_filter), True)

    @lock_required
    def QueryFunctionFields(self, function_name, schema):
        if schema:
            return self.connection.Query('''
                select y.type::character varying as type,
                       quote_ident(y.name) as name,
                       1 as seq
                from (
                    select 'O' as type,
                           'returns ' || format_type(p.prorettype, null) as name
                    from pg_proc p,
                         pg_namespace n
                    where p.pronamespace = n.oid
                      and n.nspname = '{0}'
                      and n.nspname || '.' || p.proname || '(' || oidvectortypes(p.proargtypes) || ')' = '{1}'
                ) y
                union all
                select (case trim(substring((trim(x.name) || ' ') from 1 for position(' ' in (trim(x.name) || ' '))))
                          when 'OUT' then 'O'
                          when 'INOUT' then 'X'
                          else 'I'
                        end) as type,
                       trim(x.name) as name,
                       row_number() over() + 1 as seq
                from (
                    select unnest(regexp_split_to_array(pg_get_function_identity_arguments('{1}'::regprocedure), ',')) as name
                ) x
                where length(trim(x.name)) > 0
                order by 3
            '''.format(schema, function_name), True)
        else:
            return self.connection.Query('''
                select y.type::character varying as type,
                       quote_ident(y.name) as name,
                       1 as seq
                from (
                    select 'O' as type,
                           'returns ' || format_type(p.prorettype, null) as name
                    from pg_proc p,
                         pg_namespace n
                    where p.pronamespace = n.oid
                      and n.nspname = '{0}'
                      and n.nspname || '.' || p.proname || '(' || oidvectortypes(p.proargtypes) || ')' = '{1}'
                ) y
                union all
                select (case trim(substring((trim(x.name) || ' ') from 1 for position(' ' in (trim(x.name) || ' '))))
                          when 'OUT' then 'O'
                          when 'INOUT' then 'X'
                          else 'I'
                        end) as type,
                       trim(x.name) as name,
                       row_number() over() + 1 as seq
                from (
                    select unnest(regexp_split_to_array(pg_get_function_identity_arguments('{1}'::regprocedure), ',')) as name
                ) x
                where length(trim(x.name)) > 0
                order by 3
            '''.format(self.schema, function_name), True)

    @lock_required
    def GetFunctionDefinition(self, function_name):
        return self.connection.ExecuteScalar("select pg_get_functiondef('{0}'::regprocedure)".format(function_name))

    @lock_required
    def GetFunctionDebug(self, function_name):
        return self.connection.ExecuteScalar('''
            select p.prosrc
            from pg_proc p
            join pg_namespace n
            on p.pronamespace = n.oid
            where quote_ident(n.nspname) || '.' || quote_ident(p.proname) || '(' || oidvectortypes(p.proargtypes) || ')' = '{0}'
        '''.format(function_name))

    @lock_required
    def QueryProcedures(self, all_schemas=False, schema=None):
        query_filter = ''
        if not all_schemas:
            if schema:
                query_filter = "and quote_ident(n.nspname) = '{0}' ".format(schema)
            else:
                query_filter = "and quote_ident(n.nspname) = '{0}' ".format(self.schema)
        else:
            query_filter = "and quote_ident(n.nspname) not in ('information_schema','pg_catalog') "
        return self.connection.Query('''
            select quote_ident(n.nspname) || '.' || quote_ident(p.proname) || '(' || oidvectortypes(p.proargtypes) || ')' as id,
                   quote_ident(p.proname) as name,
                   quote_ident(n.nspname) as schema_name,
                   p.oid AS function_oid
            from pg_proc p
            join pg_namespace n
            on p.pronamespace = n.oid
            where p.prokind = 'p'
            {0}
            order by 1
        '''.format(query_filter), True)

    @lock_required
    def QueryProcedureFields(self, procedure, schema):
        if schema:
            return self.connection.Query('''
                select (case trim(substring((trim(x.name) || ' ') from 1 for position(' ' in (trim(x.name) || ' '))))
                          when 'OUT' then 'O'
                          when 'INOUT' then 'X'
                          else 'I'
                        end) as type,
                       trim(x.name) as name,
                       row_number() over() as seq
                from (
                    select unnest(regexp_split_to_array(pg_get_function_identity_arguments('{1}'::regprocedure), ',')) as name
                ) x
                where length(trim(x.name)) > 0
                order by 3
            '''.format(schema, procedure), True)
        else:
            return self.connection.Query('''
                select (case trim(substring((trim(x.name) || ' ') from 1 for position(' ' in (trim(x.name) || ' '))))
                          when 'OUT' then 'O'
                          when 'INOUT' then 'X'
                          else 'I'
                        end) as type,
                       trim(x.name) as name,
                       row_number() over() as seq
                from (
                    select unnest(regexp_split_to_array(pg_get_function_identity_arguments('{1}'::regprocedure), ',')) as name
                ) x
                where length(trim(x.name)) > 0
                order by 3
            '''.format(self.schema, procedure), True)

    @lock_required
    def GetProcedureDefinition(self, procedure):
        return self.connection.ExecuteScalar("select pg_get_functiondef('{0}'::regprocedure)".format(procedure))

    @lock_required
    def GetProcedureDebug(self, procedure):
        return self.connection.ExecuteScalar('''
            select p.prosrc
            from pg_proc p
            join pg_namespace n
            on p.pronamespace = n.oid
            where quote_ident(n.nspname) || '.' || quote_ident(p.proname) || '(' || oidvectortypes(p.proargtypes) || ')' = '{0}'
        '''.format(procedure))

    @lock_required
    def QueryTriggerFunctions(self, all_schemas=False, schema=None):
        query_filter = ''
        if not all_schemas:
            if schema:
                query_filter = "and quote_ident(n.nspname) = '{0}' ".format(schema)
            else:
                query_filter = "and quote_ident(n.nspname) = '{0}' ".format(self.schema)
        else:
            query_filter = "and quote_ident(n.nspname) not in ('information_schema','pg_catalog') "
        return self.connection.Query('''
            select quote_ident(n.nspname) || '.' || quote_ident(p.proname) || '(' || oidvectortypes(p.proargtypes) || ')' as id,
                   quote_ident(p.proname) as name_raw,
                   p.proname as name,
                   quote_ident(n.nspname) as schema_name,
                   p.oid AS function_oid
            from pg_proc p
            join pg_namespace n
            on p.pronamespace = n.oid
            where format_type(p.prorettype, null) = 'trigger'
            {0}
            order by 1
        '''.format(query_filter), True)

    @lock_required
    def GetTriggerFunctionDefinition(self, function_name):
        return self.connection.ExecuteScalar("select pg_get_functiondef('{0}'::regprocedure)".format(function_name))

    @lock_required
    def QueryEventTriggerFunctions(self, all_schemas=False, schema=None):
        query_filter = ''
        if not all_schemas:
            if schema:
                query_filter = "and quote_ident(n.nspname) = '{0}' ".format(schema)
            else:
                query_filter = "and quote_ident(n.nspname) = '{0}' ".format(self.schema)
        else:
            query_filter = "and quote_ident(n.nspname) not in ('information_schema','pg_catalog') "
        return self.connection.Query('''
            select quote_ident(n.nspname) || '.' || quote_ident(p.proname) || '(' || oidvectortypes(p.proargtypes) || ')' as id,
                   quote_ident(p.proname) as name_raw,
                   p.proname as name,
                   quote_ident(n.nspname) as schema_name,
                   p.oid AS function_oid
            from pg_proc p
            join pg_namespace n
            on p.pronamespace = n.oid
            where format_type(p.prorettype, null) = 'event_trigger'
            {0}
            order by 1
        '''.format(query_filter), True)

    @lock_required
    def QueryAggregates(self, all_schemas=False, schema=None):
        query_filter = ''

        if not all_schemas:
            if schema:
                query_filter = "AND quote_ident(n.nspname) = '{0}' ".format(schema)
            else:
                query_filter = "AND quote_ident(n.nspname) = '{0}' ".format(self.schema)
        else:
            query_filter = "AND quote_ident(n.nspname) NOT IN ('information_schema','pg_catalog') "

        return self.connection.Query(
            '''
                SELECT quote_ident(n.nspname) || '.' || quote_ident(p.proname) || '(' || oidvectortypes(p.proargtypes) || ')' AS id,
                        quote_ident(p.proname) AS name,
                        quote_ident(n.nspname) AS schema_name,
                        p.oid
                FROM pg_aggregate a
                INNER JOIN pg_proc p
                        ON a.aggfnoid = p.oid
                INNER JOIN pg_namespace n
                        ON p.pronamespace = n.oid
                WHERE p.prokind = 'a'
                    {0}
                ORDER BY 1
            '''.format(
                query_filter
            ),
            True
        )

    @lock_required
    def GetEventTriggerFunctionDefinition(self, function_name):
        return self.connection.ExecuteScalar("select pg_get_functiondef('{0}'::regprocedure)".format(function_name))

    @lock_required
    def QuerySequences(self, all_schemas=False, schema=None):
        query_filter = ''
        if not all_schemas:
            if schema:
                query_filter = "and quote_ident(relnamespace::regnamespace::text) = '{0}' ".format(schema)
            else:
                query_filter = "and quote_ident(relnamespace::regnamespace::text) = '{0}' ".format(self.schema)
        else:
            query_filter = "and quote_ident(relnamespace::regnamespace::text) NOT IN ('information_schema','pg_catalog') "
        table = self.connection.Query('''
            SELECT quote_ident(relnamespace::regnamespace::text) AS sequence_schema,
                   quote_ident(relname) AS name_raw,
                   relname AS sequence_name,
                   oid
            FROM pg_class
            WHERE relkind = 'S'
            {0}
            order by 1, 2
        '''.format(query_filter), True)
        return table

    @lock_required
    def QueryViews(self, all_schemas=False, schema=None):
        query_filter = ''
        if not all_schemas:
            if schema:
                query_filter = "and quote_ident(n.nspname) = '{0}' ".format(schema)
            else:
                query_filter = "and quote_ident(n.nspname) = '{0}' ".format(self.schema)
        else:
            query_filter = "and quote_ident(t.relname) not in ('information_schema','pg_catalog') "
        return self.connection.Query('''
            select quote_ident(t.relname) as name_raw,
                   t.relname as table_name,
                   quote_ident(n.nspname) as table_schema,
                   t.oid
            from pg_class t
            inner join pg_namespace n
            on n.oid = t.relnamespace
            where t.relkind = 'v'
            {0}
            order by 2, 1
        '''.format(query_filter), True)

    @lock_required
    def QueryViewFields(self, table=None, all_schemas=False, schema=None):
        query_filter = ''
        if not all_schemas:
            if table and schema:
                query_filter = "and quote_ident(n.nspname) = '{0}' and quote_ident(c.relname) = '{1}' ".format(schema, table)
            elif table:
                query_filter = "and quote_ident(n.nspname) = '{0}' and quote_ident(c.relname) = '{1}' ".format(self.schema, table)
            elif schema:
                query_filter = "and quote_ident(n.nspname) = '{0}' ".format(schema)
            else:
                query_filter = "and quote_ident(n.nspname) = '{0}' ".format(self.schema)
        else:
            if table:
                query_filter = "and quote_ident(n.nspname) not in ('information_schema','pg_catalog') and quote_ident(c.relname) = {0}".format(table)
            else:
                query_filter = "and quote_ident(n.nspname) not in ('information_schema','pg_catalog') "
        return self.connection.Query('''
            select quote_ident(c.relname) as table_name,
                   quote_ident(a.attname) as name_raw,
                   a.attname as column_name,
                   t.typname as data_type,
                   (case when a.attnotnull or t.typtype = 'd'::char and t.typnotnull
                         then 'NO'
                         else 'YES'
                    end
                   ) as nullable,
                   (select case when x.truetypmod = -1 /* default typmod */
                                then null
                                when x.truetypid in (1042, 1043) /* char, varchar */
                                then x.truetypmod - 4
                                when x.truetypid in (1560, 1562) /* bit, varbit */
                                then x.truetypmod
                                else null
                           end
                    from (
                        select (case when t.typtype = 'd'
                                     then t.typbasetype
                                     else a.atttypid
                                end
                               ) as truetypid,
                               (case when t.typtype = 'd'
                                     then t.typtypmod
                                     else a.atttypmod
                                end
                               ) as truetypmod
                    ) x
                   ) as data_length,
                   null as data_precision,
                   null as data_scale
            from pg_attribute a
            inner join pg_class c
            on c.oid = a.attrelid
            inner join pg_namespace n
            on n.oid = c.relnamespace
            inner join pg_type t
            on t.oid = a.atttypid
            where a.attnum > 0
              and not a.attisdropped
              and c.relkind = 'v'
              {0}
            order by quote_ident(c.relname),
                     a.attnum
        '''.format(query_filter), True)

    @lock_required
    def GetViewDefinition(self, view, schema):
        return '''CREATE OR REPLACE VIEW {0}.{1} AS
{2}
'''.format(schema, view,
        self.connection.ExecuteScalar('''
                select view_definition
                from information_schema.views
                where quote_ident(table_schema) = '{0}'
                  and quote_ident(table_name) = '{1}'
            '''.format(schema, view)
    ))

    @lock_required
    def QueryMaterializedViews(self, all_schemas=False, schema=None):
        query_filter = ''
        if not all_schemas:
            if schema:
                query_filter = "and quote_ident(n.nspname) = '{0}' ".format(schema)
            else:
                query_filter = "and quote_ident(n.nspname) = '{0}' ".format(self.schema)
        else:
            query_filter = "and quote_ident(t.relname) not in ('information_schema','pg_catalog') "
        return self.connection.Query('''
            select quote_ident(t.relname) as name_raw,
                   t.relname as table_name,
                   quote_ident(n.nspname) as schema_name,
                   t.oid
            from pg_class t
            inner join pg_namespace n
            on n.oid = t.relnamespace
            where t.relkind = 'm'
            {0}
            order by 2, 1
        '''.format(query_filter), True)

    @lock_required
    def QueryMaterializedViewFields(self, table=None, all_schemas=False, schema=None):
        query_filter = ''
        if not all_schemas:
            if table and schema:
                query_filter = "and quote_ident(n.nspname) = '{0}' and quote_ident(c.relname) = '{1}' ".format(schema, table)
            elif table:
                query_filter = "and quote_ident(n.nspname) = '{0}' and quote_ident(c.relname) = '{1}' ".format(self.schema, table)
            elif schema:
                query_filter = "and quote_ident(n.nspname) = '{0}' ".format(schema)
            else:
                query_filter = "and quote_ident(n.nspname) = '{0}' ".format(self.schema)
        else:
            if table:
                query_filter = "and quote_ident(n.nspname) not in ('information_schema','pg_catalog') and quote_ident(c.relname) = {0}".format(table)
            else:
                query_filter = "and quote_ident(n.nspname) not in ('information_schema','pg_catalog') "
        return self.connection.Query('''
            select quote_ident(c.relname) as table_name,
                   quote_ident(a.attname) as name_raw,
                   a.attname as column_name,
                   t.typname as data_type,
                   (case when a.attnotnull or t.typtype = 'd'::char and t.typnotnull
                         then 'NO'
                         else 'YES'
                    end
                   ) as nullable,
                   (select case when x.truetypmod = -1 /* default typmod */
                                then null
                                when x.truetypid in (1042, 1043) /* char, varchar */
                                then x.truetypmod - 4
                                when x.truetypid in (1560, 1562) /* bit, varbit */
                                then x.truetypmod
                                else null
                           end
                    from (
                        select (case when t.typtype = 'd'
                                     then t.typbasetype
                                     else a.atttypid
                                end
                               ) as truetypid,
                               (case when t.typtype = 'd'
                                     then t.typtypmod
                                     else a.atttypmod
                                end
                               ) as truetypmod
                    ) x
                   ) as data_length,
                   null as data_precision,
                   null as data_scale
            from pg_attribute a
            inner join pg_class c
            on c.oid = a.attrelid
            inner join pg_namespace n
            on n.oid = c.relnamespace
            inner join pg_type t
            on t.oid = a.atttypid
            where a.attnum > 0
              and not a.attisdropped
              and c.relkind = 'm'
              {0}
            order by quote_ident(c.relname),
                     a.attnum
        '''.format(query_filter), True)

    @lock_required
    def GetMaterializedViewDefinition(self, view, schema):
        return '''DROP MATERIALIZED VIEW {0}.{1};

CREATE MATERIALIZED VIEW {0}.{1} AS
{2}

{3}
'''.format(
    schema,
    view,
    self.connection.ExecuteScalar(
        '''
            select pg_get_viewdef('{0}.{1}'::regclass)
        '''.format(
            schema, view
        )
    ),
    '\n'.join([
        row['definition']
        for row in self.QueryTablesIndexesHelper(view, False, schema).Rows
    ])
)

    @lock_required
    def QueryPhysicalReplicationSlots(self):
        return self.connection.Query('''
            select quote_ident(slot_name) as slot_name
            from pg_replication_slots
            where slot_type = 'physical'
            order by 1
        ''', True)

    @lock_required
    def QueryLogicalReplicationSlots(self):
        return self.connection.Query('''
            select quote_ident(slot_name) as slot_name
            from pg_replication_slots
            where slot_type = 'logical'
            order by 1
        ''', True)

    @lock_required
    def QueryPublications(self):
        return self.connection.Query('''
            select quote_ident(pubname) as name_raw,
                    pubname,
                    puballtables,
                    pubinsert,
                    pubupdate,
                    pubdelete,
                    false as pubtruncate,
                    oid
            from pg_publication
            order by 1
        ''', True)

    @lock_required
    def QueryPublicationTables(self, pub):
        return self.connection.Query('''
            select quote_ident(schemaname) || '.' || quote_ident(tablename) as table_name
            from pg_publication_tables
            where quote_ident(pubname) = '{0}'
            order by 1
        '''.format(pub), True)

    @lock_required
    def QuerySubscriptions(self):
        return self.connection.Query('''
            select quote_ident(s.subname) as name_raw,
                   s.subname,
                   s.subenabled,
                   s.subconninfo,
                   array_to_string(s.subpublications, ',') as subpublications,
                   s.oid
            from pg_subscription s
            inner join pg_database d
            on d.oid = s.subdbid
            where d.datname = '{0}'
            order by 1
        '''.format(self.service), True)

    @lock_required
    def QuerySubscriptionTables(self, sub):
        return self.connection.Query('''
            select quote_ident(n.nspname) || '.' || quote_ident(c.relname) as table_name
            from pg_subscription s
            inner join pg_database d
            on d.oid = s.subdbid
            inner join pg_subscription_rel r
            on r.srsubid = s.oid
            inner join pg_class c
            on c.oid = r.srrelid
            inner join pg_namespace n
            on n.oid = c.relnamespace
            where d.datname = '{0}'
              and quote_ident(s.subname) = '{1}'
            order by 1
        '''.format(self.service, sub), True)

    @lock_required
    def QueryForeignDataWrappers(self):
        return self.connection.Query('''
            select fdwname,
                   oid
            from pg_foreign_data_wrapper
            order by 1
        ''')

    @lock_required
    def QueryForeignServers(self, fdw):
        return self.connection.Query('''
            select s.srvname,
                   quote_ident(s.srvname) as name_raw,
                   s.srvtype,
                   s.srvversion,
                   array_to_string(srvoptions, ',') as srvoptions,
                   s.oid
            from pg_foreign_server s
            inner join pg_foreign_data_wrapper w
            on w.oid = s.srvfdw
            where w.fdwname = '{0}'
            order by 1
        '''.format(fdw))

    @lock_required
    def QueryUserMappings(self, foreign_server):
        return self.connection.Query('''
            select quote_ident(rolname) as name_raw,
                    rolname,
                   umoptions
            from (
            select seq,
                   rolname,
                   string_agg(umoption, ','::text) as umoptions
            from (
            select seq,
                   rolname,
                   (case when lower(umoption[1]) in ('password', 'passwd', 'passw', 'pass', 'pwd')
                         then umoption[1] || '=' || '*****'
                         else umoption[1] || '=' || umoption[2]
                    end) as umoption
            from (
            select seq,
                   rolname,
                   string_to_array(umoption, '=') as umoption
            from (
            select 1 as seq,
                   'PUBLIC' as rolname,
                   unnest(coalesce(u.umoptions, '{{null}}')) as umoption
            from pg_user_mapping u
            inner join pg_foreign_server s
            on s.oid = u.umserver
            where u.umuser = 0
              and quote_ident(s.srvname) = '{0}'
            union
            select 1 + row_number() over(order by r.rolname) as seq,
                   r.rolname,
                   unnest(coalesce(u.umoptions, '{{null}}')) as umoption
            from pg_user_mapping u
            inner join pg_foreign_server s
            on s.oid = u.umserver
            inner join pg_roles r
            on r.oid = u.umuser
            where quote_ident(s.srvname) = '{0}'
            ) x
            ) x
            ) x
            group by seq,
                     rolname
            ) x
            order by seq
'''.format(foreign_server))

    @lock_required
    def QueryForeignTables(self, all_schemas=False, schema=None):
        query_filter = ''
        if not all_schemas:
            if schema:
                query_filter = "and quote_ident(n.nspname) = '{0}' ".format(schema)
            else:
                query_filter = "and quote_ident(n.nspname) = '{0}' ".format(self.schema)
        else:
            query_filter = "and quote_ident(n.nspname) not in ('information_schema','pg_catalog') "
        return self.connection.Query('''
            select quote_ident(c.relname) as name_raw,
                    c.relname as table_name,
                    quote_ident(n.nspname) as table_schema,
                    c.relispartition as is_partition,
                    false as is_partitioned,
                    c.oid
            from pg_class c
            inner join pg_namespace n
            on n.oid = c.relnamespace
            where c.relkind = 'f'
            {0}
            order by 2, 1
        '''.format(query_filter), True)

    @lock_required
    def QueryForeignTablesFields(self, table=None, all_schemas=False, schema=None):
        query_filter = ''
        if not all_schemas:
            if table and schema:
                query_filter = "and quote_ident(n.nspname) = '{0}' and quote_ident(c.relname) = '{1}' ".format(schema, table)
            elif table:
                query_filter = "and quote_ident(n.nspname) = '{0}' and quote_ident(c.relname) = '{1}' ".format(self.schema, table)
            elif schema:
                query_filter = "and quote_ident(n.nspname) = '{0}' ".format(schema)
            else:
                query_filter = "and quote_ident(n.nspname) = '{0}' ".format(self.schema)
        else:
            if table:
                query_filter = "and quote_ident(n.nspname) not in ('information_schema','pg_catalog') and quote_ident(c.relname) = {0}".format(table)
            else:
                query_filter = "and quote_ident(n.nspname) not in ('information_schema','pg_catalog') "
        return self.connection.Query('''
            select quote_ident(c.relname) as table_name,
                   quote_ident(a.attname) as column_name,
                   t.typname as data_type,
                   (case when a.attnotnull or t.typtype = 'd'::char and t.typnotnull
                         then 'NO'
                         else 'YES'
                    end
                   ) as nullable,
                   (select case when x.truetypmod = -1 /* default typmod */
                                then null
                                when x.truetypid in (1042, 1043) /* char, varchar */
                                then x.truetypmod - 4
                                when x.truetypid in (1560, 1562) /* bit, varbit */
                                then x.truetypmod
                                else null
                           end
                    from (
                        select (case when t.typtype = 'd'
                                     then t.typbasetype
                                     else a.atttypid
                                end
                               ) as truetypid,
                               (case when t.typtype = 'd'
                                     then t.typtypmod
                                     else a.atttypmod
                                end
                               ) as truetypmod
                    ) x
                   ) as data_length,
                   null as data_precision,
                   null as data_scale,
                   array_to_string(a.attfdwoptions, ',') as attfdwoptions,
                   array_to_string(f.ftoptions, ',') as ftoptions,
                   s.srvname,
                   w.fdwname
            from pg_attribute a
            inner join pg_class c
            on c.oid = a.attrelid
            inner join pg_namespace n
            on n.oid = c.relnamespace
            inner join pg_type t
            on t.oid = a.atttypid
            inner join pg_foreign_table f
            on f.ftrelid = c.oid
            inner join pg_foreign_server s
            on s.oid = f.ftserver
            inner join pg_foreign_data_wrapper w
            on w.oid = s.srvfdw
            where a.attnum > 0
              and not a.attisdropped
              and c.relkind = 'f'
              {0}
            order by quote_ident(c.relname),
                     a.attnum
        '''.format(query_filter), True)

    @lock_required
    def QueryTypes(self, all_schemas=False, schema=None):
        query_filter = ''
        if not all_schemas:
            if schema:
                query_filter = "and quote_ident(n.nspname) = '{0}' ".format(schema)
            else:
                query_filter = "and quote_ident(n.nspname) = '{0}' ".format(self.schema)
        else:
            query_filter = "and quote_ident(n.nspname) not in ('information_schema','pg_catalog') "
        table = self.connection.Query('''
            select quote_ident(n.nspname) as type_schema,
                   quote_ident(t.typname) as name_raw,
                   t.typname as type_name,
                   t.oid
            from pg_type t
            inner join pg_namespace n
            on n.oid = t.typnamespace
            where (t.typrelid = 0 or (select c.relkind = 'c' from pg_class c where c.oid = t.typrelid))
              and not exists(select 1 from pg_type el where el.oid = t.typelem and el.typarray = t.oid)
              and t.typtype <> 'd'
            {0}
            order by 1, 2
        '''.format(query_filter), True)
        return table

    @lock_required
    def QueryDomains(self, all_schemas=False, schema=None):
        query_filter = ''
        if not all_schemas:
            if schema:
                query_filter = "and quote_ident(n.nspname) = '{0}' ".format(schema)
            else:
                query_filter = "and quote_ident(n.nspname) = '{0}' ".format(self.schema)
        else:
            query_filter = "and quote_ident(n.nspname) not in ('information_schema','pg_catalog') "
        table = self.connection.Query('''
            select quote_ident(n.nspname) as domain_schema,
                   quote_ident(t.typname) as name_raw,
                   t.typname as domain_name,
                   t.oid
            from pg_type t
            inner join pg_namespace n
            on n.oid = t.typnamespace
            where (t.typrelid = 0 or (select c.relkind = 'c' from pg_class c where c.oid = t.typrelid))
              and not exists(select 1 from pg_type el where el.oid = t.typelem and el.typarray = t.oid)
              and t.typtype = 'd'
            {0}
            order by 1, 2
        '''.format(query_filter), True)
        return table


    @lock_required
    def QueryPgCronJobs(self):
        return self.connection.Query('''select jobid, jobname from cron.job''', True)

    @lock_required
    def DeletePgCronJob(self, job_id):
        return self.connection.Query('''select cron.unschedule({0})'''.format(job_id), True)

    @lock_required
    def DeletePgCronJobLogs(self, job_id):
        return self.connection.Query('''delete from cron.job_run_details where jobid = {0}'''.format(job_id), True)

    @lock_required
    def GetPgCronJob(self, job_id):
        return self.connection.Query('''select jobid, jobname, schedule, command, database from cron.job where jobid = {0}'''.format(job_id), True)

    @lock_required
    def GetPgCronJobLogs(self, job_id):
        return self.connection.Query('''select runid, job_pid, database, username, status, start_time, end_time, return_message, command
            from cron.job_run_details
            where jobid = {0}
            order by runid desc limit 50'''.format(job_id), True)

    @lock_required
    def GetPgCronJobStats(self, job_id):
        return self.connection.Query('''select
            (select count(job_run_details.status) from cron.job_run_details where jobid = {0} and status='succeeded') as succeeded,
            (select count(job_run_details.status) from cron.job_run_details where jobid = {0} and status='failed') as failed'''.format(job_id), True)

    @lock_required
    def SavePgCronJob(self, job_name, job_schedule, job_command, job_database=None):
        dbarg = 'null'
        if job_database:
            dbarg = f"'{job_database}'"
        return self.connection.Query('''
            select cron.schedule_in_database('{0}', '{1}', '{2}', {3})'''
            .format(job_name, job_schedule, job_command, dbarg), True)

    def AdvancedObjectSearchData(self, text_pattern, case_sensitive, regex, in_schemas, data_category_filter):
        sql_dict = {}

        if in_schemas != '': #At least one schema must be selected
            columns_sql = '''
                select n.nspname as schema_name,
                       c.relname as table_name,
                       a.attname as column_name
                from pg_namespace n
                inner join pg_class c
                           on n.oid = c.relnamespace
                inner join pg_attribute a
                           on c.oid = a.attrelid
                where n.nspname not in ('information_schema', 'omnidb', 'pg_catalog', 'pg_toast')
                  and n.nspname not like 'pg%%temp%%'
                  and c.relkind = 'r'
                  and attnum > 0
                  and not a.attisdropped
                  and n.nspname in ({0})
                  --#FILTER_DATA_CATEGORY_FILTER# and n.nspname || '.' || c.relname like any (string_to_array('#VALUE_DATA_CATEGORY_FILTER#', '|'))
            '''.format(in_schemas)

            if data_category_filter.strip() != '':
                columns_sql = columns_sql.replace('--#FILTER_DATA_CATEGORY_FILTER#', '').replace('#VALUE_DATA_CATEGORY_FILTER#', data_category_filter)

            columns_table = self.connection.Query(columns_sql)

            for column_row in columns_table.Rows:
                sql = '''
                    select 'Data' as category,
                           '{0}' as schema_name,
                           '{1}' as table_name,
                           '{2}' as column_name,
                           t.{2}::text as match_value
                    from (
                        select t.{2}
                        from {0}.{1} t
                        where 1 = 1
                        --#FILTER_PATTERN_CASE_SENSITIVE#  and t.{2}::text like '#VALUE_PATTERN_CASE_SENSITIVE#'
                        --#FILTER_PATTERN_CASE_INSENSITIVE#  and lower(t.{2}::text) like lower('#VALUE_PATTERN_CASE_INSENSITIVE#')
                        --#FILTER_PATTERN_REGEX_CASE_SENSITIVE# and t.{2}::text ~ '#VALUE_PATTERN_REGEX_CASE_SENSITIVE#'
                        --#FILTER_PATTERN_REGEX_CASE_INSENSITIVE# and t.{2}::text ~* '#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#'
                    ) t
                '''.format(
                    column_row['schema_name'],
                    column_row['table_name'],
                    column_row['column_name']
                )

                if in_schemas != '':
                    sql = sql.replace('--#FILTER_BY_SCHEMA#', '').replace('#VALUE_BY_SCHEMA#', in_schemas)

                if regex:
                    if case_sensitive:
                        sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
                    else:
                        sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))
                else:
                    if case_sensitive:
                        sql = sql.replace('--#FILTER_PATTERN_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
                    else:
                        sql = sql.replace('--#FILTER_PATTERN_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))

                key = '{0}.{1}'.format(column_row['schema_name'], column_row['table_name'])

                if key not in sql_dict:
                    sql_dict[key] = sql
                else:
                    sql_dict[key] += '''

                        union

                        {0}
                    '''.format(sql)

        return sql_dict

    def AdvancedObjectSearchFKName(self, text_pattern, case_sensitive, regex, in_schemas):
        sql = '''
            select 'FK Name'::text as category,
                   tc.table_schema::text as schema_name,
                   tc.table_name::text as table_name,
                   ''::text as column_name,
                   tc.constraint_name::text as match_value
            from information_schema.table_constraints tc
            where tc.table_schema not in ('information_schema', 'omnidb', 'pg_catalog', 'pg_toast')
              and tc.table_schema not like 'pg%%temp%%'
              and tc.constraint_type = 'FOREIGN KEY'
            --#FILTER_PATTERN_CASE_SENSITIVE#  and tc.constraint_name like '#VALUE_PATTERN_CASE_SENSITIVE#'
            --#FILTER_PATTERN_CASE_INSENSITIVE#  and lower(tc.constraint_name) like lower('#VALUE_PATTERN_CASE_INSENSITIVE#')
            --#FILTER_PATTERN_REGEX_CASE_SENSITIVE# and tc.constraint_name ~ '#VALUE_PATTERN_REGEX_CASE_SENSITIVE#'
            --#FILTER_PATTERN_REGEX_CASE_INSENSITIVE# and tc.constraint_name ~* '#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#'
            --#FILTER_BY_SCHEMA#  and lower(tc.table_schema) in (#VALUE_BY_SCHEMA#)
        '''

        if in_schemas != '':
            sql = sql.replace('--#FILTER_BY_SCHEMA#', '').replace('#VALUE_BY_SCHEMA#', in_schemas)

        if regex:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))
        else:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))

        return sql

    def AdvancedObjectSearchFunctionDefinition(self, text_pattern, case_sensitive, regex, in_schemas):
        sql = '''
            select 'Function Definition'::text as category,
                   y.schema_name::text as schema_name,
                   ''::text as table_name,
                   ''::text as column_name,
                   y.function_definition::text as match_value
            from (
                select pg_get_functiondef(z.function_oid::regprocedure) as function_definition,
                       *
                from (
                    select n.nspname || '.' || p.proname || '(' || oidvectortypes(p.proargtypes) || ')' as function_oid,
                           p.proname as function_name,
                           n.nspname as schema_name
                    from pg_proc p
                    inner join pg_namespace n
                               on p.pronamespace = n.oid
                    where n.nspname not in ('information_schema', 'omnidb', 'pg_catalog', 'pg_toast')
                      and n.nspname not like 'pg%%temp%%'
                      and format_type(p.prorettype, null) <> 'trigger'
                    --#FILTER_BY_SCHEMA#  and lower(n.nspname) in (#VALUE_BY_SCHEMA#)
                ) z
            ) y
            where 1 = 1
            --#FILTER_PATTERN_CASE_SENSITIVE#  and y.function_definition like '#VALUE_PATTERN_CASE_SENSITIVE#'
            --#FILTER_PATTERN_CASE_INSENSITIVE#  and lower(y.function_definition) like lower('#VALUE_PATTERN_CASE_INSENSITIVE#')
            --#FILTER_PATTERN_REGEX_CASE_SENSITIVE# and y.function_definition ~ '#VALUE_PATTERN_REGEX_CASE_SENSITIVE#'
            --#FILTER_PATTERN_REGEX_CASE_INSENSITIVE# and y.function_definition ~* '#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#'
        '''

        if in_schemas != '':
            sql = sql.replace('--#FILTER_BY_SCHEMA#', '').replace('#VALUE_BY_SCHEMA#', in_schemas)

        if regex:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))
        else:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))

        return sql

    def AdvancedObjectSearchFunctionName(self, text_pattern, case_sensitive, regex, in_schemas):
        sql = '''
            select 'Function Name'::text as category,
                   n.nspname::text as schema_name,
                   ''::text as table_name,
                   ''::text as column_name,
                   p.proname::text as match_value
            from pg_proc p
            inner join pg_namespace n
                       on p.pronamespace = n.oid
            where n.nspname not in ('information_schema', 'omnidb', 'pg_catalog', 'pg_toast')
              and n.nspname not like 'pg%%temp%%'
              and format_type(p.prorettype, null) <> 'trigger'
            --#FILTER_PATTERN_CASE_SENSITIVE#  and p.proname like '#VALUE_PATTERN_CASE_SENSITIVE#'
            --#FILTER_PATTERN_CASE_INSENSITIVE#  and lower(p.proname) like lower('#VALUE_PATTERN_CASE_INSENSITIVE#')
            --#FILTER_PATTERN_REGEX_CASE_SENSITIVE# and p.proname ~ '#VALUE_PATTERN_REGEX_CASE_SENSITIVE#'
            --#FILTER_PATTERN_REGEX_CASE_INSENSITIVE# and p.proname ~* '#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#'
            --#FILTER_BY_SCHEMA#  and lower(n.nspname) in (#VALUE_BY_SCHEMA#)
        '''

        if in_schemas != '':
            sql = sql.replace('--#FILTER_BY_SCHEMA#', '').replace('#VALUE_BY_SCHEMA#', in_schemas)

        if regex:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))
        else:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))

        return sql

    def AdvancedObjectSearchProcedureDefinition(self, text_pattern, case_sensitive, regex, in_schemas):
        sql = '''
            select 'Procedure Definition'::text as category,
                   y.schema_name::text as schema_name,
                   ''::text as table_name,
                   ''::text as column_name,
                   y.procedure_definition::text as match_value
            from (
                select pg_get_functiondef(z.procedure_oid::regprocedure) as procedure_definition,
                       *
                from (
                    select n.nspname || '.' || p.proname || '(' || oidvectortypes(p.proargtypes) || ')' as procedure_oid,
                           p.proname as procedure_name,
                           n.nspname as schema_name
                    from pg_proc p
                    inner join pg_namespace n
                               on p.pronamespace = n.oid
                    where n.nspname not in ('information_schema', 'omnidb', 'pg_catalog', 'pg_toast')
                      and n.nspname not like 'pg%%temp%%'
                      and p.prokind = 'p'
                    --#FILTER_BY_SCHEMA#  and lower(n.nspname) in (#VALUE_BY_SCHEMA#)
                ) z
            ) y
            where 1 = 1
            --#FILTER_PATTERN_CASE_SENSITIVE#  and y.procedure_definition like '#VALUE_PATTERN_CASE_SENSITIVE#'
            --#FILTER_PATTERN_CASE_INSENSITIVE#  and lower(y.procedure_definition) like lower('#VALUE_PATTERN_CASE_INSENSITIVE#')
            --#FILTER_PATTERN_REGEX_CASE_SENSITIVE# and y.procedure_definition ~ '#VALUE_PATTERN_REGEX_CASE_SENSITIVE#'
            --#FILTER_PATTERN_REGEX_CASE_INSENSITIVE# and y.procedure_definition ~* '#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#'
        '''

        if in_schemas != '':
            sql = sql.replace('--#FILTER_BY_SCHEMA#', '').replace('#VALUE_BY_SCHEMA#', in_schemas)

        if regex:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))
        else:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))

        return sql

    def AdvancedObjectSearchProcedureName(self, text_pattern, case_sensitive, regex, in_schemas):
        sql = '''
            select 'Procedure Name'::text as category,
                   n.nspname::text as schema_name,
                   ''::text as table_name,
                   ''::text as column_name,
                   p.proname::text as match_value
            from pg_proc p
            inner join pg_namespace n
                       on p.pronamespace = n.oid
            where n.nspname not in ('information_schema', 'omnidb', 'pg_catalog', 'pg_toast')
              and n.nspname not like 'pg%%temp%%'
              and p.prokind = 'p'
            --#FILTER_PATTERN_CASE_SENSITIVE#  and p.proname like '#VALUE_PATTERN_CASE_SENSITIVE#'
            --#FILTER_PATTERN_CASE_INSENSITIVE#  and lower(p.proname) like lower('#VALUE_PATTERN_CASE_INSENSITIVE#')
            --#FILTER_PATTERN_REGEX_CASE_SENSITIVE# and p.proname ~ '#VALUE_PATTERN_REGEX_CASE_SENSITIVE#'
            --#FILTER_PATTERN_REGEX_CASE_INSENSITIVE# and p.proname ~* '#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#'
            --#FILTER_BY_SCHEMA#  and lower(n.nspname) in (#VALUE_BY_SCHEMA#)
        '''

        if in_schemas != '':
            sql = sql.replace('--#FILTER_BY_SCHEMA#', '').replace('#VALUE_BY_SCHEMA#', in_schemas)

        if regex:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))
        else:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))

        return sql

    def AdvancedObjectSearchIndexName(self, text_pattern, case_sensitive, regex, in_schemas):
        sql = '''
            select 'Index Name'::text as category,
                   i.schemaname::text as schema_name,
                   i.tablename::text as table_name,
                   ''::text as column_name,
                   i.indexname::text as match_value
            from pg_indexes i
            where i.schemaname not in ('information_schema', 'omnidb', 'pg_catalog', 'pg_toast')
              and i.schemaname not like 'pg%%temp%%'
            --#FILTER_PATTERN_CASE_SENSITIVE#  and i.indexname like '#VALUE_PATTERN_CASE_SENSITIVE#'
            --#FILTER_PATTERN_CASE_INSENSITIVE#  and lower(i.indexname) like lower('#VALUE_PATTERN_CASE_INSENSITIVE#')
            --#FILTER_PATTERN_REGEX_CASE_SENSITIVE# and i.indexname ~ '#VALUE_PATTERN_REGEX_CASE_SENSITIVE#'
            --#FILTER_PATTERN_REGEX_CASE_INSENSITIVE# and i.indexname ~* '#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#'
            --#FILTER_BY_SCHEMA#  and lower(i.schemaname) in (#VALUE_BY_SCHEMA#)
        '''

        if in_schemas != '':
            sql = sql.replace('--#FILTER_BY_SCHEMA#', '').replace('#VALUE_BY_SCHEMA#', in_schemas)

        if regex:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))
        else:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))

        return sql

    def AdvancedObjectSearchMaterializedViewColumnName(self, text_pattern, case_sensitive, regex, in_schemas):
        sql = '''
            select 'Materialized View Column Name'::text as category,
                   n.nspname::text as schema_name,
                   c.relname::text as table_name,
                   ''::text as column_name,
                   a.attname::text as match_value
            from pg_attribute a
            inner join pg_class c
                       on c.oid = a.attrelid
            inner join pg_namespace n
                       on n.oid = c.relnamespace
            inner join pg_type t
                       on t.oid = a.atttypid
            where n.nspname not in ('information_schema', 'omnidb', 'pg_catalog', 'pg_toast')
              and n.nspname not like 'pg%%temp%%'
              and a.attnum > 0
              and not a.attisdropped
              and c.relkind = 'm'
            --#FILTER_PATTERN_CASE_SENSITIVE#  and a.attname like '#VALUE_PATTERN_CASE_SENSITIVE#'
            --#FILTER_PATTERN_CASE_INSENSITIVE#  and lower(a.attname) like lower('#VALUE_PATTERN_CASE_INSENSITIVE#')
            --#FILTER_PATTERN_REGEX_CASE_SENSITIVE# and a.attname ~ '#VALUE_PATTERN_REGEX_CASE_SENSITIVE#'
            --#FILTER_PATTERN_REGEX_CASE_INSENSITIVE# and a.attname ~* '#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#'
            --#FILTER_BY_SCHEMA#  and lower(n.nspname) in (#VALUE_BY_SCHEMA#)
        '''

        if in_schemas != '':
            sql = sql.replace('--#FILTER_BY_SCHEMA#', '').replace('#VALUE_BY_SCHEMA#', in_schemas)

        if regex:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))
        else:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))

        return sql

    def AdvancedObjectSearchMaterializedViewName(self, text_pattern, case_sensitive, regex, in_schemas):
        sql = '''
            select 'Materialized View Name'::text as category,
                   n.nspname::text as schema_name,
                   ''::text as table_name,
                   ''::text as column_name,
                   c.relname::text as match_value
            from pg_class c
            inner join pg_namespace n
                       on n.oid = c.relnamespace
            where n.nspname not in ('information_schema', 'omnidb', 'pg_catalog', 'pg_toast')
              and n.nspname not like 'pg%%temp%%'
              and c.relkind = 'm'
            --#FILTER_PATTERN_CASE_SENSITIVE#  and c.relname like '#VALUE_PATTERN_CASE_SENSITIVE#'
            --#FILTER_PATTERN_CASE_INSENSITIVE#  and lower(c.relname) like lower('#VALUE_PATTERN_CASE_INSENSITIVE#')
            --#FILTER_PATTERN_REGEX_CASE_SENSITIVE# and c.relname ~ '#VALUE_PATTERN_REGEX_CASE_SENSITIVE#'
            --#FILTER_PATTERN_REGEX_CASE_INSENSITIVE# and c.relname ~* '#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#'
            --#FILTER_BY_SCHEMA#  and lower(n.nspname) in (#VALUE_BY_SCHEMA#)
        '''

        if in_schemas != '':
            sql = sql.replace('--#FILTER_BY_SCHEMA#', '').replace('#VALUE_BY_SCHEMA#', in_schemas)

        if regex:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))
        else:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))

        return sql

    def AdvancedObjectSearchPKName(self, text_pattern, case_sensitive, regex, in_schemas):
        sql = '''
            select 'PK Name'::text as category,
                   tc.table_schema::text as schema_name,
                   tc.table_name::text as table_name,
                   ''::text as column_name,
                   tc.constraint_name::text as match_value
            from information_schema.table_constraints tc
            where tc.table_schema not in ('information_schema', 'omnidb', 'pg_catalog', 'pg_toast')
              and tc.table_schema not like 'pg%%temp%%'
              and tc.constraint_type = 'PRIMARY KEY'
            --#FILTER_PATTERN_CASE_SENSITIVE#  and tc.constraint_name like '#VALUE_PATTERN_CASE_SENSITIVE#'
            --#FILTER_PATTERN_CASE_INSENSITIVE#  and lower(tc.constraint_name) like lower('#VALUE_PATTERN_CASE_INSENSITIVE#')
            --#FILTER_PATTERN_REGEX_CASE_SENSITIVE# and tc.constraint_name ~ '#VALUE_PATTERN_REGEX_CASE_SENSITIVE#'
            --#FILTER_PATTERN_REGEX_CASE_INSENSITIVE# and tc.constraint_name ~* '#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#'
            --#FILTER_BY_SCHEMA#  and lower(tc.table_schema) in (#VALUE_BY_SCHEMA#)
        '''

        if in_schemas != '':
            sql = sql.replace('--#FILTER_BY_SCHEMA#', '').replace('#VALUE_BY_SCHEMA#', in_schemas)

        if regex:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))
        else:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))

        return sql

    def AdvancedObjectSearchSchemaName(self, text_pattern, case_sensitive, regex, in_schemas):
        sql = '''
            select 'Schema Name'::text as category,
                   ''::text as schema_name,
                   ''::text as table_name,
                   ''::text as column_name,
                   n.nspname::text as match_value
            from pg_namespace n
            where n.nspname not in ('information_schema', 'omnidb', 'pg_catalog', 'pg_toast')
              and n.nspname not like 'pg%%temp%%'
            --#FILTER_PATTERN_CASE_SENSITIVE#  and n.nspname like '#VALUE_PATTERN_CASE_SENSITIVE#'
            --#FILTER_PATTERN_CASE_INSENSITIVE#  and lower(n.nspname) like lower('#VALUE_PATTERN_CASE_INSENSITIVE#')
            --#FILTER_PATTERN_REGEX_CASE_SENSITIVE# and n.nspname ~ '#VALUE_PATTERN_REGEX_CASE_SENSITIVE#'
            --#FILTER_PATTERN_REGEX_CASE_INSENSITIVE# and n.nspname ~* '#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#'
        '''

        if in_schemas != '':
            sql = sql.replace('--#FILTER_BY_SCHEMA#', '').replace('#VALUE_BY_SCHEMA#', in_schemas)

        if regex:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))
        else:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))

        return sql

    def AdvancedObjectSearchSequenceName(self, text_pattern, case_sensitive, regex, in_schemas):
        sql = '''
            select 'Sequence Name'::text as category,
                   s.sequence_schema::text as schema_name,
                   ''::text as table_name,
                   ''::text as column_name,
                   s.sequence_name::text as match_value
            from information_schema.sequences s
            where s.sequence_schema not in ('information_schema', 'omnidb', 'pg_catalog', 'pg_toast')
              and s.sequence_schema not like 'pg%%temp%%'
            --#FILTER_PATTERN_CASE_SENSITIVE#  and s.sequence_name like '#VALUE_PATTERN_CASE_SENSITIVE#'
            --#FILTER_PATTERN_CASE_INSENSITIVE#  and lower(s.sequence_name) like lower('#VALUE_PATTERN_CASE_INSENSITIVE#')
            --#FILTER_PATTERN_REGEX_CASE_SENSITIVE# and s.sequence_name ~ '#VALUE_PATTERN_REGEX_CASE_SENSITIVE#'
            --#FILTER_PATTERN_REGEX_CASE_INSENSITIVE# and s.sequence_name ~* '#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#'
            --#FILTER_BY_SCHEMA#  and lower(s.sequence_schema) in (#VALUE_BY_SCHEMA#)
        '''

        if in_schemas != '':
            sql = sql.replace('--#FILTER_BY_SCHEMA#', '').replace('#VALUE_BY_SCHEMA#', in_schemas)

        if regex:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))
        else:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))

        return sql

    def AdvancedObjectSearchTableColumnName(self, text_pattern, case_sensitive, regex, in_schemas):
        sql = '''
            select 'Table Column Name'::text as category,
                   c.table_schema::text as schema_name,
                   c.table_name::text as table_name,
                   ''::text as column_name,
                   c.column_name::text as match_value
            from information_schema.tables t
            inner join information_schema.columns c
                       on t.table_name = c.table_name and t.table_schema = c.table_schema
            where c.table_schema not in ('information_schema', 'omnidb', 'pg_catalog', 'pg_toast')
              and c.table_schema not like 'pg%%temp%%'
              and t.table_type = 'BASE TABLE'
            --#FILTER_PATTERN_CASE_SENSITIVE#  and c.column_name like '#VALUE_PATTERN_CASE_SENSITIVE#'
            --#FILTER_PATTERN_CASE_INSENSITIVE#  and lower(c.column_name) like lower('#VALUE_PATTERN_CASE_INSENSITIVE#')
            --#FILTER_PATTERN_REGEX_CASE_SENSITIVE# and c.column_name ~ '#VALUE_PATTERN_REGEX_CASE_SENSITIVE#'
            --#FILTER_PATTERN_REGEX_CASE_INSENSITIVE# and c.column_name ~* '#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#'
            --#FILTER_BY_SCHEMA#  and lower(c.table_schema) in (#VALUE_BY_SCHEMA#)
        '''

        if in_schemas != '':
            sql = sql.replace('--#FILTER_BY_SCHEMA#', '').replace('#VALUE_BY_SCHEMA#', in_schemas)

        if regex:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))
        else:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))

        return sql

    def AdvancedObjectSearchTableName(self, text_pattern, case_sensitive, regex, in_schemas):
        sql = '''
            select 'Table Name'::text as category,
                   t.table_schema::text as schema_name,
                   ''::text as table_name,
                   ''::text as column_name,
                   t.table_name::text as match_value
            from information_schema.tables t
            where t.table_schema not in ('information_schema', 'omnidb', 'pg_catalog', 'pg_toast')
              and t.table_schema not like 'pg%%temp%%'
              and t.table_type = 'BASE TABLE'
            --#FILTER_PATTERN_CASE_SENSITIVE#  and t.table_name like '#VALUE_PATTERN_CASE_SENSITIVE#'
            --#FILTER_PATTERN_CASE_INSENSITIVE#  and lower(t.table_name) like lower('#VALUE_PATTERN_CASE_INSENSITIVE#')
            --#FILTER_PATTERN_REGEX_CASE_SENSITIVE# and t.table_name ~ '#VALUE_PATTERN_REGEX_CASE_SENSITIVE#'
            --#FILTER_PATTERN_REGEX_CASE_INSENSITIVE# and t.table_name ~* '#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#'
            --#FILTER_BY_SCHEMA#  and lower(t.table_schema) in (#VALUE_BY_SCHEMA#)
        '''

        if in_schemas != '':
            sql = sql.replace('--#FILTER_BY_SCHEMA#', '').replace('#VALUE_BY_SCHEMA#', in_schemas)

        if regex:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))
        else:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))

        return sql

    def AdvancedObjectSearchTriggerName(self, text_pattern, case_sensitive, regex, in_schemas):
        sql = '''
            select 'Trigger Name'::text as category,
                   n.nspname::text as schema_name,
                   ''::text as table_name,
                   ''::text as column_name,
                   p.proname::text as match_value
            from pg_proc p
            inner join pg_namespace n
                       on p.pronamespace = n.oid
            where n.nspname not in ('information_schema', 'omnidb', 'pg_catalog', 'pg_toast')
              and n.nspname not like 'pg%%temp%%'
              and format_type(p.prorettype, null) = 'trigger'
            --#FILTER_PATTERN_CASE_SENSITIVE#  and p.proname like '#VALUE_PATTERN_CASE_SENSITIVE#'
            --#FILTER_PATTERN_CASE_INSENSITIVE#  and lower(p.proname) like lower('#VALUE_PATTERN_CASE_INSENSITIVE#')
            --#FILTER_PATTERN_REGEX_CASE_SENSITIVE# and p.proname ~ '#VALUE_PATTERN_REGEX_CASE_SENSITIVE#'
            --#FILTER_PATTERN_REGEX_CASE_INSENSITIVE# and p.proname ~* '#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#'
            --#FILTER_BY_SCHEMA#  and lower(n.nspname) in (#VALUE_BY_SCHEMA#)
        '''

        if in_schemas != '':
            sql = sql.replace('--#FILTER_BY_SCHEMA#', '').replace('#VALUE_BY_SCHEMA#', in_schemas)

        if regex:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))
        else:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))

        return sql

    def AdvancedObjectSearchTriggerSource(self, text_pattern, case_sensitive, regex, in_schemas):
        sql = '''
            select 'Trigger Source'::text as category,
                   n.nspname::text as schema_name,
                   ''::text as table_name,
                   ''::text as column_name,
                   p.prosrc::text as match_value
            from pg_proc p
            inner join pg_namespace n
                       on p.pronamespace = n.oid
            where n.nspname not in ('information_schema', 'omnidb', 'pg_catalog', 'pg_toast')
              and n.nspname not like 'pg%%temp%%'
              and format_type(p.prorettype, null) = 'trigger'
            --#FILTER_PATTERN_CASE_SENSITIVE#  and p.prosrc like '#VALUE_PATTERN_CASE_SENSITIVE#'
            --#FILTER_PATTERN_CASE_INSENSITIVE#  and lower(p.prosrc) like lower('#VALUE_PATTERN_CASE_INSENSITIVE#')
            --#FILTER_PATTERN_REGEX_CASE_SENSITIVE# and p.prosrc ~ '#VALUE_PATTERN_REGEX_CASE_SENSITIVE#'
            --#FILTER_PATTERN_REGEX_CASE_INSENSITIVE# and p.prosrc ~* '#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#'
            --#FILTER_BY_SCHEMA#  and lower(n.nspname) in (#VALUE_BY_SCHEMA#)
        '''

        if in_schemas != '':
            sql = sql.replace('--#FILTER_BY_SCHEMA#', '').replace('#VALUE_BY_SCHEMA#', in_schemas)

        if regex:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))
        else:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))

        return sql

    def AdvancedObjectSearchUniqueName(self, text_pattern, case_sensitive, regex, in_schemas):
        sql = '''
            select 'Unique Name'::text as category,
                   tc.table_schema::text as schema_name,
                   tc.table_name::text as table_name,
                   ''::text as column_name,
                   tc.constraint_name::text as match_value
            from information_schema.table_constraints tc
            where tc.table_schema not in ('information_schema', 'omnidb', 'pg_catalog', 'pg_toast')
              and tc.table_schema not like 'pg%%temp%%'
              and tc.constraint_type = 'UNIQUE'
            --#FILTER_PATTERN_CASE_SENSITIVE#  and tc.constraint_name like '#VALUE_PATTERN_CASE_SENSITIVE#'
            --#FILTER_PATTERN_CASE_INSENSITIVE#  and lower(tc.constraint_name) like lower('#VALUE_PATTERN_CASE_INSENSITIVE#')
            --#FILTER_PATTERN_REGEX_CASE_SENSITIVE# and tc.constraint_name ~ '#VALUE_PATTERN_REGEX_CASE_SENSITIVE#'
            --#FILTER_PATTERN_REGEX_CASE_INSENSITIVE# and tc.constraint_name ~* '#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#'
            --#FILTER_BY_SCHEMA#  and lower(tc.table_schema) in (#VALUE_BY_SCHEMA#)
        '''

        if in_schemas != '':
            sql = sql.replace('--#FILTER_BY_SCHEMA#', '').replace('#VALUE_BY_SCHEMA#', in_schemas)

        if regex:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))
        else:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))

        return sql

    def AdvancedObjectSearchViewColumnName(self, text_pattern, case_sensitive, regex, in_schemas):
        sql = '''
            select 'View Column Name'::text as category,
                   c.table_schema::text as schema_name,
                   c.table_name::text as table_name,
                   ''::text as column_name,
                   c.column_name::text as match_value
            from information_schema.views v
            inner join information_schema.columns c
                       on v.table_name = c.table_name and v.table_schema = c.table_schema
            where v.table_schema not in ('information_schema', 'omnidb', 'pg_catalog', 'pg_toast')
              and v.table_schema not like 'pg%%temp%%'
            --#FILTER_PATTERN_CASE_SENSITIVE#  and c.column_name like '#VALUE_PATTERN_CASE_SENSITIVE#'
            --#FILTER_PATTERN_CASE_INSENSITIVE#  and lower(c.column_name) like lower('#VALUE_PATTERN_CASE_INSENSITIVE#')
            --#FILTER_PATTERN_REGEX_CASE_SENSITIVE# and c.column_name ~ '#VALUE_PATTERN_REGEX_CASE_SENSITIVE#'
            --#FILTER_PATTERN_REGEX_CASE_INSENSITIVE# and c.column_name ~* '#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#'
            --#FILTER_BY_SCHEMA#  and lower(c.table_schema) in (#VALUE_BY_SCHEMA#)
        '''

        if in_schemas != '':
            sql = sql.replace('--#FILTER_BY_SCHEMA#', '').replace('#VALUE_BY_SCHEMA#', in_schemas)

        if regex:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))
        else:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))

        return sql

    def AdvancedObjectSearchViewName(self, text_pattern, case_sensitive, regex, in_schemas):
        sql = '''
            select 'View Name'::text as category,
                   v.table_schema::text as schema_name,
                   ''::text as table_name,
                   ''::text as column_name,
                   v.table_name::text as match_value
            from information_schema.views v
            where v.table_schema not in ('information_schema', 'omnidb', 'pg_catalog', 'pg_toast')
              and v.table_schema not like 'pg%%temp%%'
            --#FILTER_PATTERN_CASE_SENSITIVE#  and v.table_name like '#VALUE_PATTERN_CASE_SENSITIVE#'
            --#FILTER_PATTERN_CASE_INSENSITIVE#  and lower(v.table_name) like lower('#VALUE_PATTERN_CASE_INSENSITIVE#')
            --#FILTER_PATTERN_REGEX_CASE_SENSITIVE# and v.table_name ~ '#VALUE_PATTERN_REGEX_CASE_SENSITIVE#'
            --#FILTER_PATTERN_REGEX_CASE_INSENSITIVE# and v.table_name ~* '#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#'
            --#FILTER_BY_SCHEMA#  and lower(v.table_schema) in (#VALUE_BY_SCHEMA#)
        '''

        if in_schemas != '':
            sql = sql.replace('--#FILTER_BY_SCHEMA#', '').replace('#VALUE_BY_SCHEMA#', in_schemas)

        if regex:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))
        else:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))

        return sql

    def AdvancedObjectSearchCheckName(self, text_pattern, case_sensitive, regex, in_schemas):
        sql = '''
            select 'Check Name'::text as category,
                   quote_ident(n.nspname)::text as schema_name,
                   quote_ident(t.relname)::text as table_name,
                   ''::text as column_name,
                   quote_ident(c.conname)::text as match_value
            from pg_constraint c
            inner join pg_class t
                       on t.oid = c.conrelid
            inner join pg_namespace n
                       on t.relnamespace = n.oid
            where contype = 'c'
            --#FILTER_PATTERN_CASE_SENSITIVE#  and quote_ident(c.conname) like '#VALUE_PATTERN_CASE_SENSITIVE#'
            --#FILTER_PATTERN_CASE_INSENSITIVE#  and lower(quote_ident(c.conname)) like lower('#VALUE_PATTERN_CASE_INSENSITIVE#')
            --#FILTER_PATTERN_REGEX_CASE_SENSITIVE# and quote_ident(c.conname) ~ '#VALUE_PATTERN_REGEX_CASE_SENSITIVE#'
            --#FILTER_PATTERN_REGEX_CASE_INSENSITIVE# and quote_ident(c.conname) ~* '#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#'
            --#FILTER_BY_SCHEMA#  and lower(quote_ident(n.nspname)) in (#VALUE_BY_SCHEMA#)
        '''

        if in_schemas != '':
            sql = sql.replace('--#FILTER_BY_SCHEMA#', '').replace('#VALUE_BY_SCHEMA#', in_schemas)

        if regex:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))
        else:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))

        return sql

    def AdvancedObjectSearchRuleName(self, text_pattern, case_sensitive, regex, in_schemas):
        sql = '''
            select 'Rule Name'::text as category,
                   quote_ident(schemaname)::text as schema_name,
                   quote_ident(tablename)::text as table_name,
                   ''::text as column_name,
                   quote_ident(rulename)::text as match_value
            from pg_rules
            where 1 = 1
            --#FILTER_PATTERN_CASE_SENSITIVE#  and quote_ident(rulename) like '#VALUE_PATTERN_CASE_SENSITIVE#'
            --#FILTER_PATTERN_CASE_INSENSITIVE#  and lower(quote_ident(rulename)) like lower('#VALUE_PATTERN_CASE_INSENSITIVE#')
            --#FILTER_PATTERN_REGEX_CASE_SENSITIVE# and quote_ident(rulename) ~ '#VALUE_PATTERN_REGEX_CASE_SENSITIVE#'
            --#FILTER_PATTERN_REGEX_CASE_INSENSITIVE# and quote_ident(rulename) ~* '#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#'
            --#FILTER_BY_SCHEMA#  and lower(quote_ident(schemaname)) in (#VALUE_BY_SCHEMA#)
        '''

        if in_schemas != '':
            sql = sql.replace('--#FILTER_BY_SCHEMA#', '').replace('#VALUE_BY_SCHEMA#', in_schemas)

        if regex:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))
        else:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))

        return sql

    def AdvancedObjectSearchRuleDefinition(self, text_pattern, case_sensitive, regex, in_schemas):
        sql = '''
            select 'Rule Definition'::text as category,
                   quote_ident(schemaname)::text as schema_name,
                   quote_ident(tablename)::text as table_name,
                   ''::text as column_name,
                   definition::text as match_value
            from pg_rules
            where 1 = 1
            --#FILTER_PATTERN_CASE_SENSITIVE#  and definition like '#VALUE_PATTERN_CASE_SENSITIVE#'
            --#FILTER_PATTERN_CASE_INSENSITIVE#  and lower(definition) like lower('#VALUE_PATTERN_CASE_INSENSITIVE#')
            --#FILTER_PATTERN_REGEX_CASE_SENSITIVE# and definition ~ '#VALUE_PATTERN_REGEX_CASE_SENSITIVE#'
            --#FILTER_PATTERN_REGEX_CASE_INSENSITIVE# and definition ~* '#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#'
            --#FILTER_BY_SCHEMA#  and lower(quote_ident(schemaname)) in (#VALUE_BY_SCHEMA#)
        '''

        if in_schemas != '':
            sql = sql.replace('--#FILTER_BY_SCHEMA#', '').replace('#VALUE_BY_SCHEMA#', in_schemas)

        if regex:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))
        else:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))

        return sql

    def AdvancedObjectSearchInheritedTableName(self, text_pattern, case_sensitive, regex, in_schemas):
        sql = '''
            select 'Inherited Table Name'::text as category,
                    quote_ident(np.nspname)::text as schema_name,
                    quote_ident(cp.relname)::text as table_name,
                    ''::text as column_name,
                    quote_ident(cc.relname)::text as match_value
            from pg_inherits i
            inner join pg_class cp
                        on cp.oid = i.inhparent
            inner join pg_namespace np
                        on np.oid = cp.relnamespace
            inner join pg_class cc
                        on cc.oid = i.inhrelid
            inner join pg_namespace nc
                        on nc.oid = cc.relnamespace
            where not cc.relispartition
            --#FILTER_PATTERN_CASE_SENSITIVE#  and quote_ident(cc.relname) like '#VALUE_PATTERN_CASE_SENSITIVE#'
            --#FILTER_PATTERN_CASE_INSENSITIVE#  and lower(quote_ident(cc.relname)) like lower('#VALUE_PATTERN_CASE_INSENSITIVE#')
            --#FILTER_PATTERN_REGEX_CASE_SENSITIVE# and quote_ident(cc.relname) ~ '#VALUE_PATTERN_REGEX_CASE_SENSITIVE#'
            --#FILTER_PATTERN_REGEX_CASE_INSENSITIVE# and quote_ident(cc.relname) ~* '#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#'
            --#FILTER_BY_SCHEMA#  and lower(quote_ident(np.nspname)) in (#VALUE_BY_SCHEMA#)
        '''

        if in_schemas != '':
            sql = sql.replace('--#FILTER_BY_SCHEMA#', '').replace('#VALUE_BY_SCHEMA#', in_schemas)

        if regex:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))
        else:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))

        return sql

    def AdvancedObjectSearchPartitionName(self, text_pattern, case_sensitive, regex, in_schemas):
        sql = '''
            select 'Partition Name'::text as category,
                   quote_ident(np.nspname)::text as schema_name,
                   quote_ident(cp.relname)::text as table_name,
                   ''::text as column_name,
                   quote_ident(cc.relname)::text as match_value
            from pg_inherits i
            inner join pg_class cp
                       on cp.oid = i.inhparent
            inner join pg_namespace np
                       on np.oid = cp.relnamespace
            inner join pg_class cc
                       on cc.oid = i.inhrelid
            inner join pg_namespace nc
                       on nc.oid = cc.relnamespace
            where cc.relispartition
            --#FILTER_PATTERN_CASE_SENSITIVE#  and quote_ident(cc.relname) like '#VALUE_PATTERN_CASE_SENSITIVE#'
            --#FILTER_PATTERN_CASE_INSENSITIVE#  and lower(quote_ident(cc.relname)) like lower('#VALUE_PATTERN_CASE_INSENSITIVE#')
            --#FILTER_PATTERN_REGEX_CASE_SENSITIVE# and quote_ident(cc.relname) ~ '#VALUE_PATTERN_REGEX_CASE_SENSITIVE#'
            --#FILTER_PATTERN_REGEX_CASE_INSENSITIVE# and quote_ident(cc.relname) ~* '#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#'
            --#FILTER_BY_SCHEMA#  and lower(quote_ident(np.nspname)) in (#VALUE_BY_SCHEMA#)
        '''

        if in_schemas != '':
            sql = sql.replace('--#FILTER_BY_SCHEMA#', '').replace('#VALUE_BY_SCHEMA#', in_schemas)

        if regex:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))
        else:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))

        return sql

    def AdvancedObjectSearchRoleName(self, text_pattern, case_sensitive, regex):
        sql = '''
            select 'Role Name'::text as category,
                   ''::text as schema_name,
                   ''::text as table_name,
                   ''::text as column_name,
                   quote_ident(rolname)::text as match_value
            from pg_roles
            where 1 = 1
            --#FILTER_PATTERN_CASE_SENSITIVE#  and quote_ident(rolname) like '#VALUE_PATTERN_CASE_SENSITIVE#'
            --#FILTER_PATTERN_CASE_INSENSITIVE#  and lower(quote_ident(rolname)) like lower('#VALUE_PATTERN_CASE_INSENSITIVE#')
            --#FILTER_PATTERN_REGEX_CASE_SENSITIVE# and quote_ident(rolname) ~ '#VALUE_PATTERN_REGEX_CASE_SENSITIVE#'
            --#FILTER_PATTERN_REGEX_CASE_INSENSITIVE# and quote_ident(rolname) ~* '#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#'
        '''

        if regex:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))
        else:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))

        return sql

    def AdvancedObjectSearchTablespaceName(self, text_pattern, case_sensitive, regex):
        sql = '''
            select 'Tablespace Name'::text as category,
                   ''::text as schema_name,
                   ''::text as table_name,
                   ''::text as column_name,
                   quote_ident(spcname)::text as match_value
            from pg_tablespace
            where 1 = 1
            --#FILTER_PATTERN_CASE_SENSITIVE#  and quote_ident(spcname) like '#VALUE_PATTERN_CASE_SENSITIVE#'
            --#FILTER_PATTERN_CASE_INSENSITIVE#  and lower(quote_ident(spcname)) like lower('#VALUE_PATTERN_CASE_INSENSITIVE#')
            --#FILTER_PATTERN_REGEX_CASE_SENSITIVE# and quote_ident(spcname) ~ '#VALUE_PATTERN_REGEX_CASE_SENSITIVE#'
            --#FILTER_PATTERN_REGEX_CASE_INSENSITIVE# and quote_ident(spcname) ~* '#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#'
        '''

        if regex:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))
        else:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))

        return sql

    def AdvancedObjectSearchExtensionName(self, text_pattern, case_sensitive, regex):
        sql = '''
            select 'Extension Name'::text as category,
                   ''::text as schema_name,
                   ''::text as table_name,
                   ''::text as column_name,
                   quote_ident(extname)::text as match_value
            from pg_extension
            where 1 = 1
            --#FILTER_PATTERN_CASE_SENSITIVE#  and quote_ident(extname) like '#VALUE_PATTERN_CASE_SENSITIVE#'
            --#FILTER_PATTERN_CASE_INSENSITIVE#  and lower(quote_ident(extname)) like lower('#VALUE_PATTERN_CASE_INSENSITIVE#')
            --#FILTER_PATTERN_REGEX_CASE_SENSITIVE# and quote_ident(extname) ~ '#VALUE_PATTERN_REGEX_CASE_SENSITIVE#'
            --#FILTER_PATTERN_REGEX_CASE_INSENSITIVE# and quote_ident(extname) ~* '#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#'
        '''

        if regex:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))
        else:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))

        return sql

    def AdvancedObjectSearchFKColumnName(self, text_pattern, case_sensitive, regex, in_schemas):
        sql = '''
            with select_fks as (
                select distinct
                       quote_ident(kcu1.constraint_schema) as table_schema,
                       quote_ident(kcu1.table_name) as table_name,
                       quote_ident(kcu1.column_name) as column_name,
                       quote_ident(kcu2.constraint_schema) as r_table_schema,
                       quote_ident(kcu2.table_name) as r_table_name,
                       quote_ident(kcu2.column_name) as r_column_name
                from information_schema.referential_constraints rc
                inner join information_schema.key_column_usage kcu1
                           on  kcu1.constraint_catalog = rc.constraint_catalog
                           and kcu1.constraint_schema = rc.constraint_schema
                           and kcu1.constraint_name = rc.constraint_name
                inner join information_schema.key_column_usage kcu2
                           on  kcu2.constraint_catalog = rc.unique_constraint_catalog
                           and kcu2.constraint_schema = rc.unique_constraint_schema
                           and kcu2.constraint_name = rc.unique_constraint_name
                           and kcu2.ordinal_position = kcu1.ordinal_position
                where 1 = 1
                  --#FILTER_BY_SCHEMA#  and lower(quote_ident(kcu1.constraint_schema)) in (#VALUE_BY_SCHEMA#) or lower(quote_ident(kcu2.constraint_schema)) in (#VALUE_BY_SCHEMA#)
            )
            select 'FK Column Name'::text as category,
                   sf.table_schema::text as schema_name,
                   sf.table_name::text as table_name,
                   ''::text as column_name,
                   sf.column_name::text as match_value
            from select_fks sf
            where sf.table_schema not in ('information_schema', 'omnidb', 'pg_catalog', 'pg_toast')
              and sf.table_schema not like 'pg%%temp%%'
            --#FILTER_PATTERN_CASE_SENSITIVE#  and sf.column_name like '#VALUE_PATTERN_CASE_SENSITIVE#'
            --#FILTER_PATTERN_CASE_INSENSITIVE#  and lower(sf.column_name) like lower('#VALUE_PATTERN_CASE_INSENSITIVE#')
            --#FILTER_PATTERN_REGEX_CASE_SENSITIVE# and sf.column_name ~ '#VALUE_PATTERN_REGEX_CASE_SENSITIVE#'
            --#FILTER_PATTERN_REGEX_CASE_INSENSITIVE# and sf.column_name ~* '#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#'
            --#FILTER_BY_SCHEMA#  and lower(sf.table_schema) in (#VALUE_BY_SCHEMA#)

            union

            select 'FK Column Name'::text as category,
                   (sf.r_table_schema || ' (referenced)')::text as schema_name,
                   (sf.r_table_name || ' (referenced)')::text as table_name,
                   ''::text as column_name,
                   (sf.r_column_name || ' (referenced)')::text as match_value
            from select_fks sf
            where sf.r_table_schema not in ('information_schema', 'omnidb', 'pg_catalog', 'pg_toast')
              and sf.r_table_schema not like 'pg%%temp%%'
            --#FILTER_PATTERN_CASE_SENSITIVE#  and sf.r_column_name like '#VALUE_PATTERN_CASE_SENSITIVE#'
            --#FILTER_PATTERN_CASE_INSENSITIVE#  and lower(sf.r_column_name) like lower('#VALUE_PATTERN_CASE_INSENSITIVE#')
            --#FILTER_PATTERN_REGEX_CASE_SENSITIVE# and sf.r_column_name ~ '#VALUE_PATTERN_REGEX_CASE_SENSITIVE#'
            --#FILTER_PATTERN_REGEX_CASE_INSENSITIVE# and sf.r_column_name ~* '#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#'
            --#FILTER_BY_SCHEMA#  and lower(sf.r_table_schema) in (#VALUE_BY_SCHEMA#)
        '''

        if in_schemas != '':
            sql = sql.replace('--#FILTER_BY_SCHEMA#', '').replace('#VALUE_BY_SCHEMA#', in_schemas)

        if regex:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))
        else:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))

        return sql

    def AdvancedObjectSearchPKColumnName(self, text_pattern, case_sensitive, regex, in_schemas):
        sql = '''
            select 'PK Column Name'::text as category,
                   quote_ident(tc.table_schema)::text as schema_name,
                   quote_ident(tc.table_name)::text as table_name,
                   ''::text as column_name,
                   quote_ident(kc.column_name) as match_value
            from information_schema.table_constraints tc
            inner join information_schema.key_column_usage kc
                       on  kc.table_name = tc.table_name
                       and kc.table_schema = tc.table_schema
                       and kc.constraint_name = tc.constraint_name
            where tc.constraint_type = 'PRIMARY KEY'
              and quote_ident(tc.table_schema) not in ('information_schema', 'omnidb', 'pg_catalog', 'pg_toast')
              and quote_ident(tc.table_schema) not like 'pg%%temp%%'
            --#FILTER_PATTERN_CASE_SENSITIVE#  and quote_ident(kc.column_name) like '#VALUE_PATTERN_CASE_SENSITIVE#'
            --#FILTER_PATTERN_CASE_INSENSITIVE#  and lower(quote_ident(kc.column_name)) like lower('#VALUE_PATTERN_CASE_INSENSITIVE#')
            --#FILTER_PATTERN_REGEX_CASE_SENSITIVE# and quote_ident(kc.column_name) ~ '#VALUE_PATTERN_REGEX_CASE_SENSITIVE#'
            --#FILTER_PATTERN_REGEX_CASE_INSENSITIVE# and quote_ident(kc.column_name) ~* '#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#'
            --#FILTER_BY_SCHEMA#  and lower(quote_ident(tc.table_schema)) in (#VALUE_BY_SCHEMA#)
        '''

        if in_schemas != '':
            sql = sql.replace('--#FILTER_BY_SCHEMA#', '').replace('#VALUE_BY_SCHEMA#', in_schemas)

        if regex:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))
        else:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))

        return sql

    def AdvancedObjectSearchUniqueColumnName(self, text_pattern, case_sensitive, regex, in_schemas):
        sql = '''
            select 'Unique Column Name'::text as category,
                   quote_ident(tc.table_schema)::text as schema_name,
                   quote_ident(tc.table_name)::text as table_name,
                   ''::text as column_name,
                   quote_ident(kc.column_name) as match_value
            from information_schema.table_constraints tc
            inner join information_schema.key_column_usage kc
                       on  kc.table_name = tc.table_name
                       and kc.table_schema = tc.table_schema
                       and kc.constraint_name = tc.constraint_name
            where tc.constraint_type = 'UNIQUE'
              and quote_ident(tc.table_schema) not in ('information_schema', 'omnidb', 'pg_catalog', 'pg_toast')
              and quote_ident(tc.table_schema) not like 'pg%%temp%%'
            --#FILTER_PATTERN_CASE_SENSITIVE#  and quote_ident(kc.column_name) like '#VALUE_PATTERN_CASE_SENSITIVE#'
            --#FILTER_PATTERN_CASE_INSENSITIVE#  and lower(quote_ident(kc.column_name)) like lower('#VALUE_PATTERN_CASE_INSENSITIVE#')
            --#FILTER_PATTERN_REGEX_CASE_SENSITIVE# and quote_ident(kc.column_name) ~ '#VALUE_PATTERN_REGEX_CASE_SENSITIVE#'
            --#FILTER_PATTERN_REGEX_CASE_INSENSITIVE# and quote_ident(kc.column_name) ~* '#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#'
            --#FILTER_BY_SCHEMA#  and lower(quote_ident(tc.table_schema)) in (#VALUE_BY_SCHEMA#)
        '''

        if in_schemas != '':
            sql = sql.replace('--#FILTER_BY_SCHEMA#', '').replace('#VALUE_BY_SCHEMA#', in_schemas)

        if regex:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))
        else:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))

        return sql

    def AdvancedObjectSearchIndexColumnName(self, text_pattern, case_sensitive, regex, in_schemas):
        sql = '''
            select *
            from (
                select 'Index Column Name'::text as category,
                       quote_ident(t.schemaname)::text as schema_name,
                       quote_ident(t.tablename)::text as table_name,
                       ''::text as column_name,
                       unnest(string_to_array(replace(substr(t.indexdef, strpos(t.indexdef, '(')+1, strpos(t.indexdef, ')')-strpos(t.indexdef, '(')-1), ' ', ''),',')) as match_value
                from pg_indexes t
            ) t
            where quote_ident(t.schemaname) not in ('information_schema', 'omnidb', 'pg_catalog', 'pg_toast')
              and quote_ident(t.schemaname) not like 'pg%%temp%%'
            --#FILTER_PATTERN_CASE_SENSITIVE#  and quote_ident(t.match_value) like '#VALUE_PATTERN_CASE_SENSITIVE#'
            --#FILTER_PATTERN_CASE_INSENSITIVE#  and lower(quote_ident(t.match_value)) like lower('#VALUE_PATTERN_CASE_INSENSITIVE#')
            --#FILTER_PATTERN_REGEX_CASE_SENSITIVE# and quote_ident(t.match_value) ~ '#VALUE_PATTERN_REGEX_CASE_SENSITIVE#'
            --#FILTER_PATTERN_REGEX_CASE_INSENSITIVE# and quote_ident(t.match_value) ~* '#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#'
            --#FILTER_BY_SCHEMA#  and lower(quote_ident(t.schema_name)) in (#VALUE_BY_SCHEMA#)
        '''

        if in_schemas != '':
            sql = sql.replace('--#FILTER_BY_SCHEMA#', '').replace('#VALUE_BY_SCHEMA#', in_schemas)

        if regex:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))
        else:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))

        return sql

    def AdvancedObjectSearchCheckDefinition(self, text_pattern, case_sensitive, regex, in_schemas):
        sql = '''
            select 'Check Definition'::text as category,
                   quote_ident(n.nspname)::text as schema_name,
                   quote_ident(t.relname)::text as table_name,
                   ''::text as column_name,
                   pg_get_constraintdef(c.oid) as match_value
            from pg_constraint c
            inner join pg_class t
                  on t.oid = c.conrelid
            inner join pg_namespace n
                  on t.relnamespace = n.oid
            where contype = 'c'
              and quote_ident(n.nspname) not in ('information_schema', 'omnidb', 'pg_catalog', 'pg_toast')
              and quote_ident(n.nspname) not like 'pg%%temp%%'
            --#FILTER_PATTERN_CASE_SENSITIVE#  and pg_get_constraintdef(c.oid) like '#VALUE_PATTERN_CASE_SENSITIVE#'
            --#FILTER_PATTERN_CASE_INSENSITIVE#  and lower(pg_get_constraintdef(c.oid)) like lower('#VALUE_PATTERN_CASE_INSENSITIVE#')
            --#FILTER_PATTERN_REGEX_CASE_SENSITIVE# and pg_get_constraintdef(c.oid) ~ '#VALUE_PATTERN_REGEX_CASE_SENSITIVE#'
            --#FILTER_PATTERN_REGEX_CASE_INSENSITIVE# and pg_get_constraintdef(c.oid) ~* '#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#'
            --#FILTER_BY_SCHEMA#  and lower(quote_ident(n.nspname)) in (#VALUE_BY_SCHEMA#)
        '''

        if in_schemas != '':
            sql = sql.replace('--#FILTER_BY_SCHEMA#', '').replace('#VALUE_BY_SCHEMA#', in_schemas)

        if regex:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))
        else:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))

        return sql

    def AdvancedObjectSearchTableTriggerName(self, text_pattern, case_sensitive, regex, in_schemas):
        sql = '''
            select 'Table Trigger Name'::text as category,
                   quote_ident(n.nspname)::text as schema_name,
                   quote_ident(c.relname)::text as table_name,
                   ''::text as column_name,
                   quote_ident(t.tgname) as match_value
            from pg_trigger t
            inner join pg_class c
                  on c.oid = t.tgrelid
            inner join pg_namespace n
                  on n.oid = c.relnamespace
            inner join pg_proc p
                  on p.oid = t.tgfoid
            inner join pg_namespace np
                  on np.oid = p.pronamespace
            where not t.tgisinternal
              and quote_ident(n.nspname) not in ('information_schema', 'omnidb', 'pg_catalog', 'pg_toast')
              and quote_ident(n.nspname) not like 'pg%%temp%%'
            --#FILTER_PATTERN_CASE_SENSITIVE#  and quote_ident(t.tgname) like '#VALUE_PATTERN_CASE_SENSITIVE#'
            --#FILTER_PATTERN_CASE_INSENSITIVE#  and lower(quote_ident(t.tgname)) like lower('#VALUE_PATTERN_CASE_INSENSITIVE#')
            --#FILTER_PATTERN_REGEX_CASE_SENSITIVE# and quote_ident(t.tgname) ~ '#VALUE_PATTERN_REGEX_CASE_SENSITIVE#'
            --#FILTER_PATTERN_REGEX_CASE_INSENSITIVE# and quote_ident(t.tgname) ~* '#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#'
            --#FILTER_BY_SCHEMA#  and lower(quote_ident(n.nspname)) in (#VALUE_BY_SCHEMA#)
        '''

        if in_schemas != '':
            sql = sql.replace('--#FILTER_BY_SCHEMA#', '').replace('#VALUE_BY_SCHEMA#', in_schemas)

        if regex:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))
        else:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))

        return sql

    def AdvancedObjectSearchMaterializedViewDefinition(self, text_pattern, case_sensitive, regex, in_schemas):
        sql = '''
            select 'Materialized View Definition'::text as category,
                   y.schema_name::text as schema_name,
                   ''::text as table_name,
                   ''::text as column_name,
                   y.mview_definition::text as match_value
            from (
                select n.nspname::text as schema_name,
                       pg_get_viewdef((n.nspname || '.' || c.relname)::regclass) as mview_definition
                from pg_class c
                inner join pg_namespace n
                           on n.oid = c.relnamespace
                where n.nspname not in ('information_schema', 'omnidb', 'pg_catalog', 'pg_toast')
                  and n.nspname not like 'pg%%temp%%'
                  and c.relkind = 'm'
                  --#FILTER_BY_SCHEMA#  and lower(n.nspname) in (#VALUE_BY_SCHEMA#)
            ) y
            where 1 = 1
            --#FILTER_PATTERN_CASE_SENSITIVE#  and y.mview_definition like '#VALUE_PATTERN_CASE_SENSITIVE#'
            --#FILTER_PATTERN_CASE_INSENSITIVE#  and lower(y.mview_definition) like lower('#VALUE_PATTERN_CASE_INSENSITIVE#')
            --#FILTER_PATTERN_REGEX_CASE_SENSITIVE# and y.mview_definition ~ '#VALUE_PATTERN_REGEX_CASE_SENSITIVE#'
            --#FILTER_PATTERN_REGEX_CASE_INSENSITIVE# and y.mview_definition ~* '#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#'
        '''

        if in_schemas != '':
            sql = sql.replace('--#FILTER_BY_SCHEMA#', '').replace('#VALUE_BY_SCHEMA#', in_schemas)

        if regex:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))
        else:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))

        return sql

    def AdvancedObjectSearchViewDefinition(self, text_pattern, case_sensitive, regex, in_schemas):
        sql = '''
            select 'View Definition'::text as category,
                   v.table_schema::text as schema_name,
                   ''::text as table_name,
                   ''::text as column_name,
                   v.view_definition::text as match_value
            from information_schema.views v
            where v.table_schema not in ('information_schema', 'omnidb', 'pg_catalog', 'pg_toast')
              and v.table_schema not like 'pg%%temp%%'
            --#FILTER_PATTERN_CASE_SENSITIVE#  and v.view_definition like '#VALUE_PATTERN_CASE_SENSITIVE#'
            --#FILTER_PATTERN_CASE_INSENSITIVE#  and lower(v.view_definition) like lower('#VALUE_PATTERN_CASE_INSENSITIVE#')
            --#FILTER_PATTERN_REGEX_CASE_SENSITIVE# and v.view_definition ~ '#VALUE_PATTERN_REGEX_CASE_SENSITIVE#'
            --#FILTER_PATTERN_REGEX_CASE_INSENSITIVE# and v.view_definition ~* '#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#'
            --#FILTER_BY_SCHEMA#  and lower(v.table_schema) in (#VALUE_BY_SCHEMA#)
        '''

        if in_schemas != '':
            sql = sql.replace('--#FILTER_BY_SCHEMA#', '').replace('#VALUE_BY_SCHEMA#', in_schemas)

        if regex:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))
        else:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))

        return sql

    def AdvancedObjectSearchTypeName(self, text_pattern, case_sensitive, regex, in_schemas):
        sql = '''
            select 'Type Name'::text as category,
                   n.nspname::text as schema_name,
                   ''::text as table_name,
                   ''::text as column_name,
                   t.typname::text as match_value
            from pg_type t
            inner join pg_namespace n
            on n.oid = t.typnamespace
            where (t.typrelid = 0 or (select c.relkind = 'c' from pg_class c where c.oid = t.typrelid))
              and not exists(select 1 from pg_type el where el.oid = t.typelem and el.typarray = t.oid)
              and t.typtype <> 'd'
              and n.nspname not in ('information_schema', 'omnidb', 'pg_catalog', 'pg_toast')
              and n.nspname not like 'pg%%temp%%'
            --#FILTER_PATTERN_CASE_SENSITIVE#  and t.typname like '#VALUE_PATTERN_CASE_SENSITIVE#'
            --#FILTER_PATTERN_CASE_INSENSITIVE#  and lower(t.typname) like lower('#VALUE_PATTERN_CASE_INSENSITIVE#')
            --#FILTER_PATTERN_REGEX_CASE_SENSITIVE# and t.typname ~ '#VALUE_PATTERN_REGEX_CASE_SENSITIVE#'
            --#FILTER_PATTERN_REGEX_CASE_INSENSITIVE# and t.typname ~* '#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#'
            --#FILTER_BY_SCHEMA#  and lower(n.nspname) in (#VALUE_BY_SCHEMA#)
        '''

        if in_schemas != '':
            sql = sql.replace('--#FILTER_BY_SCHEMA#', '').replace('#VALUE_BY_SCHEMA#', in_schemas)

        if regex:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))
        else:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))

        return sql

    def AdvancedObjectSearchDomainName(self, text_pattern, case_sensitive, regex, in_schemas):
        sql = '''
            select 'Domain Name'::text as category,
                   n.nspname::text as schema_name,
                   ''::text as table_name,
                   ''::text as column_name,
                   t.typname::text as match_value
            from pg_type t
            inner join pg_namespace n
            on n.oid = t.typnamespace
            where (t.typrelid = 0 or (select c.relkind = 'c' from pg_class c where c.oid = t.typrelid))
              and not exists(select 1 from pg_type el where el.oid = t.typelem and el.typarray = t.oid)
              and t.typtype = 'd'
              and n.nspname not in ('information_schema', 'omnidb', 'pg_catalog', 'pg_toast')
              and n.nspname not like 'pg%%temp%%'
            --#FILTER_PATTERN_CASE_SENSITIVE#  and t.typname like '#VALUE_PATTERN_CASE_SENSITIVE#'
            --#FILTER_PATTERN_CASE_INSENSITIVE#  and lower(t.typname) like lower('#VALUE_PATTERN_CASE_INSENSITIVE#')
            --#FILTER_PATTERN_REGEX_CASE_SENSITIVE# and t.typname ~ '#VALUE_PATTERN_REGEX_CASE_SENSITIVE#'
            --#FILTER_PATTERN_REGEX_CASE_INSENSITIVE# and t.typname ~* '#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#'
            --#FILTER_BY_SCHEMA#  and lower(n.nspname) in (#VALUE_BY_SCHEMA#)
        '''

        if in_schemas != '':
            sql = sql.replace('--#FILTER_BY_SCHEMA#', '').replace('#VALUE_BY_SCHEMA#', in_schemas)

        if regex:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))
        else:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))

        return sql

    def AdvancedObjectSearchEventTriggerName(self, text_pattern, case_sensitive, regex, in_schemas):
        sql = '''
            select 'Event Trigger Name'::text as category,
                   np.nspname::text as schema_name,
                   ''::text as table_name,
                   ''::text as column_name,
                   t.evtname::text as match_value
            from pg_event_trigger t
            inner join pg_proc p
                    on p.oid = t.evtfoid
            inner join pg_namespace np
                    on np.oid = p.pronamespace
            where np.nspname not in ('information_schema', 'omnidb', 'pg_catalog', 'pg_toast')
              and np.nspname not like 'pg%%temp%%'
            --#FILTER_PATTERN_CASE_SENSITIVE#  and t.evtname like '#VALUE_PATTERN_CASE_SENSITIVE#'
            --#FILTER_PATTERN_CASE_INSENSITIVE#  and lower(t.evtname) like lower('#VALUE_PATTERN_CASE_INSENSITIVE#')
            --#FILTER_PATTERN_REGEX_CASE_SENSITIVE#  and t.evtname ~ '#VALUE_PATTERN_REGEX_CASE_SENSITIVE#'
            --#FILTER_PATTERN_REGEX_CASE_INSENSITIVE#  and t.evtname ~* '#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#'
            --#FILTER_BY_SCHEMA#  and lower(np.nspname) in (#VALUE_BY_SCHEMA#)
        '''

        if in_schemas != '':
            sql = sql.replace('--#FILTER_BY_SCHEMA#', '').replace('#VALUE_BY_SCHEMA#', in_schemas)

        if regex:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))
        else:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))

        return sql

    def AdvancedObjectSearchEventTriggerFunctionName(self, text_pattern, case_sensitive, regex, in_schemas):
        sql = '''
            select 'Event Trigger Function Name'::text as category,
                   n.nspname::text as schema_name,
                   ''::text as table_name,
                   ''::text as column_name,
                   p.proname::text as match_value
            from pg_proc p
            join pg_namespace n
              on p.pronamespace = n.oid
            where format_type(p.prorettype, null) = 'event_trigger'
              and n.nspname not in ('information_schema', 'omnidb', 'pg_catalog', 'pg_toast')
              and n.nspname not like 'pg%%temp%%'
              and format_type(p.prorettype, null) <> 'trigger'
            --#FILTER_PATTERN_CASE_SENSITIVE#  and p.proname like '#VALUE_PATTERN_CASE_SENSITIVE#'
            --#FILTER_PATTERN_CASE_INSENSITIVE#  and lower(p.proname) like lower('#VALUE_PATTERN_CASE_INSENSITIVE#')
            --#FILTER_PATTERN_REGEX_CASE_SENSITIVE# and p.proname ~ '#VALUE_PATTERN_REGEX_CASE_SENSITIVE#'
            --#FILTER_PATTERN_REGEX_CASE_INSENSITIVE# and p.proname ~* '#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#'
            --#FILTER_BY_SCHEMA#  and lower(n.nspname) in (#VALUE_BY_SCHEMA#)
        '''

        if in_schemas != '':
            sql = sql.replace('--#FILTER_BY_SCHEMA#', '').replace('#VALUE_BY_SCHEMA#', in_schemas)

        if regex:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))
        else:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))

        return sql

    def AdvancedObjectSearchEventTriggerFunctionDefinition(self, text_pattern, case_sensitive, regex, in_schemas):
        sql = '''
            select 'Event Trigger Function Definition'::text as category,
                   y.schema_name::text as schema_name,
                   ''::text as table_name,
                   ''::text as column_name,
                   y.function_definition::text as match_value
            from (
                select pg_get_functiondef(z.function_oid::regprocedure) as function_definition,
                       *
                from (
                    select n.nspname || '.' || p.proname || '(' || oidvectortypes(p.proargtypes) || ')' as function_oid,
                           p.proname as function_name,
                           n.nspname as schema_name
                    from pg_proc p
                    join pg_namespace n
                      on p.pronamespace = n.oid
                    where format_type(p.prorettype, null) = 'event_trigger'
                      and n.nspname not in ('information_schema', 'omnidb', 'pg_catalog', 'pg_toast')
                      and n.nspname not like 'pg%%temp%%'
                      and format_type(p.prorettype, null) <> 'trigger'
                    --#FILTER_BY_SCHEMA#  and lower(n.nspname) in (#VALUE_BY_SCHEMA#)
                ) z
            ) y
            where 1 = 1
            --#FILTER_PATTERN_CASE_SENSITIVE#  and y.function_definition like '#VALUE_PATTERN_CASE_SENSITIVE#'
            --#FILTER_PATTERN_CASE_INSENSITIVE#  and lower(y.function_definition) like lower('#VALUE_PATTERN_CASE_INSENSITIVE#')
            --#FILTER_PATTERN_REGEX_CASE_SENSITIVE# and y.function_definition ~ '#VALUE_PATTERN_REGEX_CASE_SENSITIVE#'
            --#FILTER_PATTERN_REGEX_CASE_INSENSITIVE# and y.function_definition ~* '#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#'
        '''

        if in_schemas != '':
            sql = sql.replace('--#FILTER_BY_SCHEMA#', '').replace('#VALUE_BY_SCHEMA#', in_schemas)

        if regex:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_REGEX_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_REGEX_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))
        else:
            if case_sensitive:
                sql = sql.replace('--#FILTER_PATTERN_CASE_SENSITIVE#', '').replace('#VALUE_PATTERN_CASE_SENSITIVE#', text_pattern.replace("'", "''"))
            else:
                sql = sql.replace('--#FILTER_PATTERN_CASE_INSENSITIVE#', '').replace('#VALUE_PATTERN_CASE_INSENSITIVE#', text_pattern.replace("'", "''"))

        return sql

    def AdvancedObjectSearch(self, text_pattern, case_sensitive, regex, categories_list, schemas_list, data_category_filter):
        sql_dict = {}

        in_schemas = ''

        if len(schemas_list) > 0:
            for schema in schemas_list:
                in_schemas += "'{0}', ".format(schema)

            in_schemas = in_schemas[:-2]

        if not regex:
            if '%' not in text_pattern.replace('\%', ''):
                text_pattern = '%{0}%'.format(text_pattern)

        for category in categories_list:
            if category == 'Data':
                sql_dict[category] = self.AdvancedObjectSearchData(text_pattern, case_sensitive, regex, in_schemas, data_category_filter)
            elif category == 'FK Name':
                sql_dict[category] = self.AdvancedObjectSearchFKName(text_pattern, case_sensitive, regex, in_schemas)
            elif category == 'Function Definition':
                sql_dict[category] = self.AdvancedObjectSearchFunctionDefinition(text_pattern, case_sensitive, regex, in_schemas)
            elif category == 'Function Name':
                sql_dict[category] = self.AdvancedObjectSearchFunctionName(text_pattern, case_sensitive, regex, in_schemas)
            elif category == 'Index Name':
                sql_dict[category] = self.AdvancedObjectSearchIndexName(text_pattern, case_sensitive, regex, in_schemas)
            elif category == 'Materialized View Column Name':
                sql_dict[category] = self.AdvancedObjectSearchMaterializedViewColumnName(text_pattern, case_sensitive, regex, in_schemas)
            elif category == 'Materialized View Name':
                sql_dict[category] = self.AdvancedObjectSearchMaterializedViewName(text_pattern, case_sensitive, regex, in_schemas)
            elif category == 'PK Name':
                sql_dict[category] = self.AdvancedObjectSearchPKName(text_pattern, case_sensitive, regex, in_schemas)
            elif category == 'Schema Name':
                sql_dict[category] = self.AdvancedObjectSearchSchemaName(text_pattern, case_sensitive, regex, in_schemas)
            elif category == 'Sequence Name':
                sql_dict[category] = self.AdvancedObjectSearchSequenceName(text_pattern, case_sensitive, regex, in_schemas)
            elif category == 'Table Column Name':
                sql_dict[category] = self.AdvancedObjectSearchTableColumnName(text_pattern, case_sensitive, regex, in_schemas)
            elif category == 'Table Name':
                sql_dict[category] = self.AdvancedObjectSearchTableName(text_pattern, case_sensitive, regex, in_schemas)
            elif category == 'Trigger Name':
                sql_dict[category] = self.AdvancedObjectSearchTriggerName(text_pattern, case_sensitive, regex, in_schemas)
            elif category == 'Trigger Source':
                sql_dict[category] = self.AdvancedObjectSearchTriggerSource(text_pattern, case_sensitive, regex, in_schemas)
            elif category == 'Unique Name':
                sql_dict[category] = self.AdvancedObjectSearchUniqueName(text_pattern, case_sensitive, regex, in_schemas)
            elif category == 'View Column Name':
                sql_dict[category] = self.AdvancedObjectSearchViewColumnName(text_pattern, case_sensitive, regex, in_schemas)
            elif category == 'View Name':
                sql_dict[category] = self.AdvancedObjectSearchViewName(text_pattern, case_sensitive, regex, in_schemas)
            elif category == 'Check Name':
                sql_dict[category] = self.AdvancedObjectSearchCheckName(text_pattern, case_sensitive, regex, in_schemas)
            elif category == 'Rule Name':
                sql_dict[category] = self.AdvancedObjectSearchRuleName(text_pattern, case_sensitive, regex, in_schemas)
            elif category == 'Rule Definition':
                sql_dict[category] = self.AdvancedObjectSearchRuleDefinition(text_pattern, case_sensitive, regex, in_schemas)
            elif category == 'Inherited Table Name':
                sql_dict[category] = self.AdvancedObjectSearchInheritedTableName(text_pattern, case_sensitive, regex, in_schemas)
            elif category == 'Partition Name':
                sql_dict[category] = self.AdvancedObjectSearchPartitionName(text_pattern, case_sensitive, regex, in_schemas)
            elif category == 'Role Name':
                sql_dict[category] = self.AdvancedObjectSearchRoleName(text_pattern, case_sensitive, regex)
            elif category == 'Tablespace Name':
                sql_dict[category] = self.AdvancedObjectSearchTablespaceName(text_pattern, case_sensitive, regex)
            elif category == 'Extension Name':
                sql_dict[category] = self.AdvancedObjectSearchExtensionName(text_pattern, case_sensitive, regex)
            elif category == 'FK Column Name':
                sql_dict[category] = self.AdvancedObjectSearchFKColumnName(text_pattern, case_sensitive, regex, in_schemas)
            elif category == 'PK Column Name':
                sql_dict[category] = self.AdvancedObjectSearchPKColumnName(text_pattern, case_sensitive, regex, in_schemas)
            elif category == 'Unique Column Name':
                sql_dict[category] = self.AdvancedObjectSearchUniqueColumnName(text_pattern, case_sensitive, regex, in_schemas)
            elif category == 'Index Column Name':
                sql_dict[category] = self.AdvancedObjectSearchIndexColumnName(text_pattern, case_sensitive, regex, in_schemas)
            elif category == 'Check Definition':
                sql_dict[category] = self.AdvancedObjectSearchCheckDefinition(text_pattern, case_sensitive, regex, in_schemas)
            elif category == 'Table Trigger Name':
                sql_dict[category] = self.AdvancedObjectSearchTableTriggerName(text_pattern, case_sensitive, regex, in_schemas)
            elif category == 'Materialized View Definition':
                sql_dict[category] = self.AdvancedObjectSearchMaterializedViewDefinition(text_pattern, case_sensitive, regex, in_schemas)
            elif category == 'View Definition':
                sql_dict[category] = self.AdvancedObjectSearchViewDefinition(text_pattern, case_sensitive, regex, in_schemas)
            elif category == 'Type Name':
                sql_dict[category] = self.AdvancedObjectSearchTypeName(text_pattern, case_sensitive, regex, in_schemas)
            elif category == 'Domain Name':
                sql_dict[category] = self.AdvancedObjectSearchDomainName(text_pattern, case_sensitive, regex, in_schemas)
            elif category == 'Event Trigger Name':
                sql_dict[category] = self.AdvancedObjectSearchEventTriggerName(text_pattern, case_sensitive, regex, in_schemas)
            elif category == 'Event Trigger Function Name':
                sql_dict[category] = self.AdvancedObjectSearchEventTriggerFunctionName(text_pattern, case_sensitive, regex, in_schemas)
            elif category == 'Event Trigger Function Definition':
                sql_dict[category] = self.AdvancedObjectSearchEventTriggerFunctionDefinition(text_pattern, case_sensitive, regex, in_schemas)
            elif category == 'Procedure Definition':
                sql_dict[category] = self.AdvancedObjectSearchProcedureDefinition(text_pattern, case_sensitive, regex, in_schemas)
            elif category == 'Procedure Name':
                sql_dict[category] = self.AdvancedObjectSearchProcedureName(text_pattern, case_sensitive, regex, in_schemas)

        return sql_dict

    def TemplateDropRole(self):
        template = get_template("postgres", "drop_role")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateCreateTablespace(self):
        template = get_template("postgres", "create_tablespace")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateAlterTablespace(self):
        template = get_template("postgres", "alter_tablespace")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateDropTablespace(self):
        template = get_template("postgres", "drop_tablespace")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateCreateDatabase(self):
        template = get_template("postgres", "create_database", self.version_num)
        return template.safe_substitute(major_version=self.major_version)

    def TemplateAlterDatabase(self):
        template = get_template("postgres", "alter_database")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateDropDatabase(self):
        template = get_template("postgres", "drop_database", self.version_num)
        return template.safe_substitute(major_version=self.major_version)

    def TemplateCreateSchema(self):
        template = get_template("postgres", "create_schema")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateAlterSchema(self):
        template = get_template("postgres", "alter_schema")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateDropSchema(self):
        template = get_template("postgres", "drop_schema")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateCreateSequence(self):
        template = get_template("postgres", "create_sequence")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateAlterSequence(self):
        template = get_template("postgres", "alter_sequence")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateDropSequence(self):
        template = get_template("postgres", "drop_sequence")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateCreateFunction(self):
        template = get_template("postgres", "create_function")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateAlterFunction(self):
        template = get_template("postgres", "alter_function", self.version_num)
        return template.safe_substitute(major_version=self.major_version)

    def TemplateDropFunction(self):
        template = get_template("postgres", "drop_function")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateCreateProcedure(self):
        template = get_template("postgres", "create_procedure")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateAlterProcedure(self):
        template = get_template("postgres", "alter_procedure")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateDropProcedure(self):
        template = get_template("postgres", "drop_procedure")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateCreateTriggerFunction(self):
        template = get_template("postgres", "create_triggerfunction")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateAlterTriggerFunction(self):
        template = get_template("postgres", "alter_triggerfunction", self.version_num)
        return template.safe_substitute(major_version=self.major_version)

    def TemplateDropTriggerFunction(self):
        template = get_template("postgres", "drop_triggerfunction")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateCreateEventTriggerFunction(self):
        template = get_template("postgres", "create_eventtriggerfunction")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateAlterEventTriggerFunction(self):
        template = get_template("postgres", "alter_eventtriggerfunction", self.version_num)
        return template.safe_substitute(major_version=self.major_version)

    def TemplateDropEventTriggerFunction(self):
        template = get_template("postgres", "drop_eventtriggerfunction")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateCreateAggregate(self):
        template = get_template("postgres", "create_aggregate")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateAlterAggregate(self):
        template = get_template("postgres", "alter_aggregate")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateDropAggregate(self):
        template = get_template("postgres", "drop_aggregate")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateCreateView(self):
        template = get_template("postgres", "create_view")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateAlterView(self):
        template = get_template("postgres", "alter_view", self.version_num)
        return template.safe_substitute(major_version=self.major_version)

    def TemplateDropView(self):
        template = get_template("postgres", "drop_view")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateCreateMaterializedView(self):
        template = get_template("postgres", "create_mview")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateRefreshMaterializedView(self):
        template = get_template("postgres", "refresh_mview")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateAlterMaterializedView(self):
        template = get_template("postgres", "alter_mview")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateDropMaterializedView(self):
        template = get_template("postgres", "drop_mview")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateDropTable(self):
        template = get_template("postgres", "drop_table")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateCreateColumn(self):
        template = get_template("postgres", "create_column")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateAlterColumn(self):
        template = get_template("postgres", "alter_column")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateDropColumn(self):
        template = get_template("postgres", "drop_column")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateCreatePrimaryKey(self):
        template = get_template("postgres", "create_primarykey")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateDropPrimaryKey(self):
        template = get_template("postgres", "drop_primarykey")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateCreateUnique(self):
        template = get_template("postgres", "create_unique")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateDropUnique(self):
        template = get_template("postgres", "drop_unique")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateCreateForeignKey(self):
        template = get_template("postgres", "create_foreignkey")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateDropForeignKey(self):
        template = get_template("postgres", "drop_foreignkey")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateCreateIndex(self):
        template = get_template("postgres", "create_index", self.version_num)
        return template.safe_substitute(major_version=self.major_version)

    def TemplateAlterIndex(self):
        template = get_template("postgres", "alter_index", self.version_num)
        return template.safe_substitute(major_version=self.major_version)

    def TemplateClusterIndex(self):
        template = get_template("postgres", "cluster_index")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateReindex(self):
        template = get_template("postgres", "reindex")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateDropIndex(self):
        template = get_template("postgres", "drop_index")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateCreateCheck(self):
        template = get_template("postgres", "create_check")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateDropCheck(self):
        template = get_template("postgres", "drop_check")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateCreateExclude(self):
        template = get_template("postgres", "create_exclude")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateDropExclude(self):
        template = get_template("postgres", "drop_exclude")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateCreateRule(self):
        template = get_template("postgres", "create_rule")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateAlterRule(self):
        template = get_template("postgres", "alter_rule")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateDropRule(self):
        template = get_template("postgres", "drop_rule")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateCreateTrigger(self):
        template = get_template("postgres", "create_trigger")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateCreateViewTrigger(self):
        template = get_template("postgres", "create_view_trigger")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateAlterTrigger(self):
        template = get_template("postgres", "alter_trigger", self.version_num)
        return template.safe_substitute(major_version=self.major_version)

    def TemplateEnableTrigger(self):
        template = get_template("postgres", "enable_trigger")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateDisableTrigger(self):
        template = get_template("postgres", "disable_trigger")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateDropTrigger(self):
        template = get_template("postgres", "drop_trigger")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateCreateEventTrigger(self):
        template = get_template("postgres", "create_eventtrigger")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateAlterEventTrigger(self):
        template = get_template("postgres", "alter_eventtrigger")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateEnableEventTrigger(self):
        template = get_template("postgres", "enable_eventtrigger")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateDisableEventTrigger(self):
        template = get_template("postgres", "disable_eventtrigger")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateDropEventTrigger(self):
        template = get_template("postgres", "drop_eventtrigger")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateCreateInherited(self):
        template = get_template("postgres", "create_inherited")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateNoInheritPartition(self):
        template = get_template("postgres", "noinherit_partition")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateCreatePartition(self):
        template = get_template("postgres", "create_partition")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateDetachPartition(self):
        template = get_template("postgres", "detach_partition")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateDropPartition(self):
        template = get_template("postgres", "drop_partition")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateCreateType(self):
        template = get_template("postgres", "create_type")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateAlterType(self):
        template = get_template("postgres", "alter_type", self.version_num)
        return template.safe_substitute(major_version=self.major_version)

    def TemplateDropType(self):
        template = get_template("postgres", "drop_type")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateCreateDomain(self):
        template = get_template("postgres", "create_domain")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateAlterDomain(self):
        template = get_template("postgres", "alter_domain")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateDropDomain(self):
        template = get_template("postgres", "drop_domain")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateVacuum(self):
        template = get_template("postgres", "vacuum", self.version_num)
        return template.safe_substitute(major_version=self.major_version)

    def TemplateVacuumTable(self):
        template = get_template("postgres", "vacuum_table", self.version_num)
        return template.safe_substitute(major_version=self.major_version)

    def TemplateAnalyze(self):
        template = get_template("postgres", "analyze")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateAnalyzeTable(self):
        template = get_template("postgres", "analyze_table")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateSelect(self, schema, table, object_type):
        if object_type == 't':
            sql = 'SELECT t.'
            fields = self.QueryTablesFields(table, False, schema)
            if len(fields.Rows) > 0:
                sql += '\n     , t.'.join([r['name_raw'] for r in fields.Rows])
            sql += '\nFROM {0}.{1} t'.format(schema, table)
            pk = self.QueryTablesPrimaryKeys(table, False, schema)
            if len(pk.Rows) > 0:
                fields = self.QueryTablesPrimaryKeysColumns(pk.Rows[0]['constraint_name'], table, False, schema)
                if len(fields.Rows) > 0:
                    sql += '\nORDER BY t.'
                    sql += '\n       , t.'.join([r['column_name'] for r in fields.Rows])
        elif object_type == 'v':
            sql = 'SELECT t.'
            fields = self.QueryViewFields(table, False, schema)
            if len(fields.Rows) > 0:
                sql += '\n     , t.'.join([r['name_raw'] for r in fields.Rows])
            sql += '\nFROM {0}.{1} t'.format(schema, table)
        elif object_type == 'm':
            sql = 'SELECT t.'
            fields = self.QueryMaterializedViewFields(table, False, schema)
            if len(fields.Rows) > 0:
                sql += '\n     , t.'.join([r['name_raw'] for r in fields.Rows])
            sql += '\nFROM {0}.{1} t'.format(schema, table)
        elif object_type == 'f':
            sql = 'SELECT t.'
            fields = self.QueryForeignTablesFields(table, False, schema)
            if len(fields.Rows) > 0:
                sql += '\n     , t.'.join([r['column_name'] for r in fields.Rows])
            sql += '\nFROM {0}.{1} t'.format(schema, table)
        else:
            sql = 'SELECT t.*\nFROM {0}.{1} t'.format(schema, table)
        return Template(sql)

    def TemplateInsert(self, schema, table):
        fields = self.QueryTablesFields(table, False, schema)
        sql = f'-- https://www.postgresql.org/docs/{self.major_version}/sql-insert.html \n'
        if len(fields.Rows) > 0:
            sql += 'INSERT INTO {0}.{1} (\n'.format(schema, table)
            pk = self.QueryTablesPrimaryKeys(table, False, schema)
            if len(pk.Rows) > 0:
                table_pk_fields = self.QueryTablesPrimaryKeysColumns(pk.Rows[0]['constraint_name'], table, False, schema)
                pk_fields = [r['column_name'] for r in table_pk_fields.Rows]
                values = []
                first = True
                for r in fields.Rows:
                    if first:
                        sql += '      {0}'.format(r['column_name'])
                        if r['column_name'] in pk_fields:
                            values.append('      ? -- {0} {1} PRIMARY KEY'.format(r['column_name'], r['data_type']))
                        elif r['nullable'] == 'YES':
                            values.append('      ? -- {0} {1} NULLABLE'.format(r['column_name'], r['data_type']))
                        else:
                            values.append('      ? -- {0} {1}'.format(r['column_name'], r['data_type']))
                        first = False
                    else:
                        sql += '\n    , {0}'.format(r['column_name'])
                        if r['column_name'] in pk_fields:
                            values.append('\n    , ? -- {0} {1} PRIMARY KEY'.format(r['column_name'], r['data_type']))
                        elif r['nullable'] == 'YES':
                            values.append('\n    , ? -- {0} {1} NULLABLE'.format(r['column_name'], r['data_type']))
                        else:
                            values.append('\n    , ? -- {0} {1}'.format(r['column_name'], r['data_type']))
            else:
                values = []
                first = True
                for r in fields.Rows:
                    if first:
                        sql += '      {0}'.format(r['column_name'])
                        if r['nullable'] == 'YES':
                            values.append('      ? -- {0} {1} NULLABLE'.format(r['column_name'], r['data_type']))
                        else:
                            values.append('      ? -- {0} {1}'.format(r['column_name'], r['data_type']))
                        first = False
                    else:
                        sql += '\n    , {0}'.format(r['column_name'])
                        if r['nullable'] == 'YES':
                            values.append('\n    , ? -- {0} {1} NULLABLE'.format(r['column_name'], r['data_type']))
                        else:
                            values.append('\n    , ? -- {0} {1}'.format(r['column_name'], r['data_type']))
            sql += '\n) VALUES (\n'
            for v in values:
                sql += v
            sql += '\n)'
        return Template(sql)

    def TemplateUpdate(self, schema, table):
        fields = self.QueryTablesFields(table, False, schema)
        sql = f'-- https://www.postgresql.org/docs/{self.major_version}/sql-update.html \n'
        if len(fields.Rows) > 0:
            sql += 'UPDATE {0}.{1}\nSET '.format(schema, table)
            pk = self.QueryTablesPrimaryKeys(table, False, schema)
            if len(pk.Rows) > 0:
                table_pk_fields = self.QueryTablesPrimaryKeysColumns(pk.Rows[0]['constraint_name'], table, False, schema)
                pk_fields = [r['column_name'] for r in table_pk_fields.Rows]
                first = True
                for r in fields.Rows:
                    if first:
                        if r['column_name'] in pk_fields:
                            sql += '{0} = ? -- {1} PRIMARY KEY'.format(r['column_name'], r['data_type'])
                        elif r['nullable'] == 'YES':
                            sql += '{0} = ? -- {1} NULLABLE'.format(r['column_name'], r['data_type'])
                        else:
                            sql += '{0} = ? -- {1}'.format(r['column_name'], r['data_type'])
                        first = False
                    else:
                        if r['column_name'] in pk_fields:
                            sql += '\n    , {0} = ? -- {1} PRIMARY KEY'.format(r['column_name'], r['data_type'])
                        elif r['nullable'] == 'YES':
                            sql += '\n    , {0} = ? -- {1} NULLABLE'.format(r['column_name'], r['data_type'])
                        else:
                            sql += '\n    , {0} = ? -- {1}'.format(r['column_name'], r['data_type'])
            else:
                first = True
                for r in fields.Rows:
                    if first:
                        if r['nullable'] == 'YES':
                            sql += '{0} = ? -- {1} NULLABLE'.format(r['column_name'], r['data_type'])
                        else:
                            sql += '{0} = ? -- {1}'.format(r['column_name'], r['data_type'])
                        first = False
                    else:
                        if r['nullable'] == 'YES':
                            sql += '\n    , {0} = ? -- {1} NULLABLE'.format(r['column_name'], r['data_type'])
                        else:
                            sql += '\n    , {0} = ? -- {1}'.format(r['column_name'], r['data_type'])
            sql += '\nWHERE condition'
        return Template(sql)

    def TemplateDelete(self):
        template = get_template("postgres", "delete")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateTruncate(self):
        template = get_template("postgres", "truncate")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateSelectFunction(self, schema, function_name, function_id):
        table = self.connection.Query('''
            select p.proretset
            from pg_proc p,
                 pg_namespace n
            where p.pronamespace = n.oid
              and n.nspname = '{0}'
              and n.nspname || '.' || p.proname || '(' || oidvectortypes(p.proargtypes) || ')' = '{1}'
        '''.format(schema, function_id))
        if len(table.Rows) > 0:
            retset = table.Rows[0][0]
        else:
            retset = False
        fields = self.QueryFunctionFields(function_id, schema)
        if len(fields.Rows) > 1:
            if retset:
                sql = 'SELECT * FROM {0}.{1}(\n    '.format(schema, function_name)
            else:
                sql = 'SELECT {0}.{1}(\n    '.format(schema, function_name)
            first = True
            for r in fields.Rows:
                if r['name'].split(' ')[0] != '"returns':
                    if r['type'] == 'I':
                        field_type = 'IN'
                    elif r['type'] == 'O':
                        field_type = 'OUT'
                    else:
                        field_type = 'INOUT'
                    if first:
                        sql += '? -- {0} {1}'.format(r['name'], field_type)
                        first = False
                    else:
                        sql += '\n  , ? -- {0} {1}'.format(r['name'], field_type)
            sql += '\n)'
        else:
            if retset:
                sql = 'SELECT * FROM {0}.{1}()'.format(schema, function_name)
            else:
                sql = 'SELECT {0}.{1}()'.format(schema, function_name)
        return Template(sql)

    def TemplateCallProcedure(self, schema, procedure, procedure_id):
        fields = self.QueryProcedureFields(procedure_id, schema)
        if len(fields.Rows) > 0:
            sql = 'CALL {0}.{1}(\n    '.format(schema, procedure)
            first = True
            for r in fields.Rows:
                if r['type'] == 'I':
                    field_type = 'IN'
                elif r['type'] == 'O':
                    field_type = 'OUT'
                else:
                    field_type = 'INOUT'
                if first:
                    sql += '? -- {0} {1}'.format(r['name'], field_type)
                    first = False
                else:
                    sql += '\n  , ? -- {0} {1}'.format(r['name'], field_type)
            sql += '\n)'
        else:
            sql = 'CALL {0}.{1}()'.format(schema, procedure)
        return Template(sql)

    def TemplateCreatePhysicalReplicationSlot(self):
        template = get_template("postgres", "create_physicalreplicationslot")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateDropPhysicalReplicationSlot(self):
        template = get_template("postgres", "drop_physicalreplicationslot")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateCreateLogicalReplicationSlot(self):
        template = get_template("postgres", "create_logicalreplicationslot")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateDropLogicalReplicationSlot(self):
        template = get_template("postgres", "drop_logicalreplicationslot")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateCreatePublication(self):
        template = get_template("postgres", "create_publication", self.version_num)
        return template.safe_substitute(major_version=self.major_version)

    def TemplateAlterPublication(self):
        template = get_template("postgres", "alter_publication", self.version_num)
        return template.safe_substitute(major_version=self.major_version)

    def TemplateDropPublication(self):
        template = get_template("postgres", "drop_publication")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateAddPublicationTable(self):
        template = get_template("postgres", "add_pubtable")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateDropPublicationTable(self):
        template = get_template("postgres", "drop_pubtable")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateCreateSubscription(self):
        template = get_template("postgres", "create_subscription")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateAlterSubscription(self):
        template = get_template("postgres", "alter_subscription")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateDropSubscription(self):
        template = get_template("postgres", "drop_subscription")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateCreateForeignDataWrapper(self):
        template = get_template("postgres", "create_fdw")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateAlterForeignDataWrapper(self):
        template = get_template("postgres", "alter_fdw")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateDropForeignDataWrapper(self):
        template = get_template("postgres", "drop_fdw")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateCreateForeignServer(self):
        template = get_template("postgres", "create_foreign_server")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateAlterForeignServer(self):
        template = get_template("postgres", "alter_foreign_server")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateDropForeignServer(self):
        template = get_template("postgres", "drop_foreign_server")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateCreateUserMapping(self):
        template = get_template("postgres", "create_user_mapping")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateAlterUserMapping(self):
        template = get_template("postgres", "alter_user_mapping")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateImportForeignSchema(self):
        template = get_template("postgres", "import_foreign_schema")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateDropUserMapping(self):
        template = get_template("postgres", "drop_user_mapping")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateCreateForeignTable(self):
        template = get_template("postgres", "create_foreign_table")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateAlterForeignTable(self):
        template = get_template("postgres", "alter_foreign_table")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateDropForeignTable(self):
        template = get_template("postgres", "drop_foreign_table")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateCreateForeignColumn(self):
        template = get_template("postgres", "create_foreign_column")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateAlterForeignColumn(self):
        template = get_template("postgres", "alter_foreign_column")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateDropForeignColumn(self):
        template = get_template("postgres", "drop_foreign_column")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateCreateStatistics(self):
        template = get_template("postgres", "create_statistics")
        return template.safe_substitute(major_version=self.major_version)

    def TemplateAlterStatistics(self):
        template = get_template("postgres", "alter_statistics", self.version_num)
        return template.safe_substitute(major_version=self.major_version)

    def TemplateDropStatistics(self):
        template = get_template("postgres", "drop_statistics", self.version_num)
        return template.safe_substitute(major_version=self.major_version)

    @lock_required
    def GetPropertiesRole(self, role_name):
        return self.connection.Query('''
            select rolname as "Role",
                   oid as "OID",
                   rolsuper as "Super User",
                   rolinherit as "Inherit",
                   rolcreaterole as "Can Create Role",
                   rolcreatedb as "Can Create Database",
                   rolcanlogin as "Can Login",
                   rolreplication as "Replication",
                   rolconnlimit as "Connection Limit",
                   rolvaliduntil as "Valid Until"
            from pg_roles
            where quote_ident(rolname) = '{0}'
        '''.format(role_name))
    
    @lock_required
    def GetPropertiesTablespace(self, tablespace_name):
        return self.connection.Query('''
            select t.spcname as "Tablespace",
                   r.rolname as "Owner",
                   t.oid as "OID",
                   pg_tablespace_location(t.oid) as "Location",
                   t.spcacl as "ACL",
                   t.spcoptions as "Options"
            from pg_tablespace t
            inner join pg_roles r
            on r.oid = t.spcowner
            where quote_ident(t.spcname) = '{0}'
        '''.format(tablespace_name))
    
    @lock_required
    def GetPropertiesDatabase(self, database_name):
        datcollate = 'd.datcollate as "LC_COLLATE",' if self.version_num >= 80400 else ""
        datctype = 'd.datctype as "LC_CTYPE",' if self.version_num >= 80400 else ""
        return self.connection.Query(f'''
            select d.datname as "Database",
                   r.rolname as "Owner",
                   pg_size_pretty(pg_database_size(d.oid)) as "Size",
                   pg_encoding_to_char(d.encoding) as "Encoding",
                   {datcollate}
                   {datctype}
                   d.datistemplate as "Is Template",
                   d.datallowconn as "Allows Connections",
                   d.datconnlimit as "Connection Limit",
                   t.spcname as "Tablespace",
                   d.datacl as "ACL"
            from pg_database d
            inner join pg_roles r
            on r.oid = d.datdba
            inner join pg_tablespace t
            on t.oid = d.dattablespace
            where quote_ident(d.datname) = '{database_name}'
        ''')
    
    @lock_required
    def GetPropertiesExtension(self, extension_name):
        return self.connection.Query('''
            select current_database() as "Database",
                   e.extname as "Extension",
                   r.rolname as "Owner",
                   n.nspname as "Schema",
                   e.extrelocatable as "Relocatable",
                   e.extversion as "Version"
            from pg_extension e
            inner join pg_roles r
            on r.oid = e.extowner
            inner join pg_namespace n
            on n.oid = e.extnamespace
            where quote_ident(e.extname) = '{0}'
        '''.format(extension_name))
    
    @lock_required
    def GetPropertiesSchema(self, schema_name):
        return self.connection.Query('''
            select current_database() as "Database",
                   n.nspname as "Schema",
                   r.rolname as "Owner",
                   n.nspacl as "ACL"
            from pg_namespace n
            inner join pg_roles r
            on r.oid = n.nspowner
            where quote_ident(n.nspname) = '{0}'
        '''.format(schema_name))
    
    @lock_required
    def GetPropertiesTable(self, schema, table_name):
        return self.connection.Query('''
            select current_database() as "Database",
                    n.nspname as "Schema",
                    c.relname as "Table",
                    c.oid as "OID",
                    r.rolname as "Owner",
                    pg_size_pretty(pg_relation_size(c.oid)) as "Size",
                    coalesce(t1.spcname, t2.spcname) as "Tablespace",
                    c.relacl as "ACL",
                    c.reloptions as "Options",
                    pg_relation_filepath(c.oid) as "Filenode",
                    c.reltuples as "Estimate Count",
                    c.relhasindex as "Has Index",
                    (case c.relpersistence when 'p' then 'Permanent' when 'u' then 'Unlogged' when 't' then 'Temporary' end) as "Persistence",
                    c.relnatts as "Number of Attributes",
                    c.relchecks as "Number of Checks",
                    c.relhasrules as "Has Rules",
                    c.relhastriggers as "Has Triggers",
                    c.relhassubclass as "Has Subclass",
                    c.relkind = 'p' as "Is Partitioned",
                    c.relispartition as "Is Partition",
                    (case when c.relispartition then po.parent_table else '' end) as "Partition Of"
            from pg_class c
            inner join pg_namespace n
            on n.oid = c.relnamespace
            inner join pg_roles r
            on r.oid = c.relowner
            left join pg_tablespace t1
            on t1.oid = c.reltablespace
            inner join (
            select t.spcname
            from pg_database d
            inner join pg_tablespace t
            on t.oid = d.dattablespace
            where d.datname = current_database()
            ) t2
            on 1 = 1
            left join (
            select quote_ident(n2.nspname) || '.' || quote_ident(c2.relname) as parent_table
            from pg_inherits i
            inner join pg_class c2
            on c2.oid = i.inhparent
            inner join pg_namespace n2
            on n2.oid = c2.relnamespace
            where i.inhrelid = '{0}.{1}'::regclass
            ) po
            on 1 = 1
            where quote_ident(n.nspname) = '{0}'
                and quote_ident(c.relname) = '{1}'
        '''.format(schema, table_name))

    @lock_required
    def GetPropertiesTableField(self, schema, table, table_field):
        return self.connection.Query(
            '''
                SELECT current_database() AS "Database",
                        n.nspname AS "Schema",
                        c.relname AS "Table",
                        a.attname AS "Column",
                        c.oid AS "OID",
                        r.rolname AS "Owner",
                        a.atttypid::regtype AS "Type",
                        a.attstattarget AS "Statistics Target",
                        a.attlen AS "Type Length",
                        a.attnum AS "Position",
                        a.attndims AS "Dimension",
                        a.attcacheoff AS "Cache Offset",
                        a.atttypmod AS "Type Mod",
                        a.attbyval AS "By Value",
                        a.attstorage AS "Storage Type",
                        a.attalign AS "Storage Alignment",
                        a.attnotnull AS "Not Null",
                        a.atthasdef AS "Has Default",
                        a.atthasmissing AS "Has Missing",
                        a.attidentity AS "Identitiy",
                        a.attgenerated AS "Generated",
                        a.attisdropped AS "Is Dropped",
                        a.attislocal AS "Is Local",
                        a.attinhcount AS "Inherited Count",
                        a.attcollation AS "Collate",
                        a.attacl AS "ACL",
                        a.attoptions AS "Options",
                        a.attfdwoptions AS "FDW Options",
                        attmissingval AS "Missing Value"
                FROM pg_class c
                INNER JOIN pg_namespace n
                        ON c.relnamespace = n.oid
                INNER JOIN pg_roles r
                        ON c.relowner = r.oid
                INNER JOIN pg_attribute a
                        ON c.oid = a.attrelid
                WHERE c.oid = '{0}.{1}'::regclass
                    AND quote_ident(a.attname) = '{2}'
            '''.format(
                schema,
                table,
                table_field
            )
        )

    @lock_required
    def GetPropertiesIndex(self, schema, index_name):
        return self.connection.Query('''
            select current_database() as "Database",
                   n.nspname as "Schema",
                   c.relname as "Index",
                   c.oid as "OID",
                   r.rolname as "Owner",
                   pg_size_pretty(pg_relation_size(c.oid)) as "Size",
                   i.indisunique as "Unique",
                   i.indisprimary as "Primary",
                   i.indisexclusion as "Exclusion",
                   i.indimmediate as "Immediate",
                   i.indisclustered as "Clustered",
                   i.indisvalid as "Valid",
                   i.indisready as "Ready",
                   i.indislive as "Live",
                   a.amname as "Access Method",
                   coalesce(t1.spcname, t2.spcname) as "Tablespace",
                   pg_relation_filepath(c.oid) as "Filenode"
            from pg_class c
            inner join pg_namespace n
            on n.oid = c.relnamespace
            inner join pg_roles r
            on r.oid = c.relowner
            left join pg_tablespace t1
            on t1.oid = c.reltablespace
            inner join (
            select t.spcname
            from pg_database d
            inner join pg_tablespace t
            on t.oid = d.dattablespace
            where d.datname = current_database()
            ) t2
            on 1 = 1
            inner join pg_am a
            on a.oid = c.relam
            inner join pg_index i
            on i.indexrelid = c.oid
            where quote_ident(n.nspname) = '{0}'
              and quote_ident(c.relname) = '{1}'
        '''.format(schema, index_name))
    
    @lock_required
    def GetPropertiesSequence(self, schema, sequence_name):
        table1 = self.connection.Query('''
            select current_database() as "Database",
                   n.nspname as "Schema",
                   c.relname as "Sequence",
                   c.oid as "OID",
                   r.rolname as "Owner",
                   coalesce(t1.spcname, t2.spcname) as "Tablespace",
                   pg_relation_filepath(c.oid) as "Filenode"
            from pg_class c
            inner join pg_namespace n
            on n.oid = c.relnamespace
            inner join pg_roles r
            on r.oid = c.relowner
            left join pg_tablespace t1
            on t1.oid = c.reltablespace
            inner join (
            select t.spcname
            from pg_database d
            inner join pg_tablespace t
            on t.oid = d.dattablespace
            where d.datname = current_database()
            ) t2
            on 1 = 1
            where quote_ident(n.nspname) = '{0}'
              and quote_ident(c.relname) = '{1}'
        '''.format(schema, sequence_name)).Transpose('Property', 'Value')
        table2 = self.connection.Query('''
            select data_type as "Data Type",
                    last_value as "Last Value",
                    start_value as "Start Value",
                    increment_by as "Increment By",
                    max_value as "Max Value",
                    min_value as "Min Value",
                    cache_size as "Cache Size",
                    cycle as "Is Cycled"
            from pg_sequences
            where quote_ident(schemaname) = '{0}'
                and quote_ident(sequencename) = '{1}'
        '''.format(schema, sequence_name)).Transpose('Property', 'Value')
        table1.Merge(table2)
        return table1
    
    @lock_required
    def GetPropertiesView(self, schema, view_name):
        return self.connection.Query('''
            select current_database() as "Database",
                   n.nspname as "Schema",
                   c.relname as "View",
                   c.oid as "OID",
                   r.rolname as "Owner"
            from pg_class c
            inner join pg_namespace n
            on n.oid = c.relnamespace
            inner join pg_roles r
            on r.oid = c.relowner
            where quote_ident(n.nspname) = '{0}'
              and quote_ident(c.relname) = '{1}'
        '''.format(schema, view_name))
    
    @lock_required
    def GetPropertiesFunction(self, function_name):
        return self.connection.Query('''
            select current_database() as "Database",
                    n.nspname as "Schema",
                    p.proname as "Function",
                    quote_ident(n.nspname) || '.' || quote_ident(p.proname) || '(' || oidvectortypes(p.proargtypes) || ')' as "Function ID",
                    p.oid as "OID",
                    r.rolname as "Owner",
                    (case p.prokind when 'f' then 'Normal' when 'a' then 'Aggregate' when 'w' then 'Window' end) as "Function Kind",
                    l.lanname as "Language",
                    p.procost as "Estimated Execution Cost",
                    p.prorows as "Estimated Returned Rows",
                    p.prosecdef as "Security Definer",
                    p.proleakproof as "Leak Proof",
                    p.proisstrict as "Is Strict",
                    p.proretset as "Returns Set",
                    (case p.provolatile when 'i' then 'Immutable' when 's' then 'Stable' when 'v' then 'Volatile' end) as "Volatile",
                    (case p.proparallel when 's' then 'Safe' when 'r' then 'Restricted' when 'u' then 'Unsafe' end) as "Parallel",
                    p.pronargs as "Number of Arguments",
                    p.pronargdefaults as "Number of Default Arguments",
                    p.probin as "Invoke",
                    p.proconfig as "Configuration",
                    p.proacl as "ACL"
            from pg_proc p
            join pg_namespace n
            on p.pronamespace = n.oid
            inner join pg_roles r
            on r.oid = p.proowner
            inner join pg_language l
            on l.oid = p.prolang
            where quote_ident(n.nspname) || '.' || quote_ident(p.proname) || '(' || oidvectortypes(p.proargtypes) || ')' = '{0}'
                and p.prokind = 'f'
        '''.format(function_name))
    
    @lock_required
    def GetPropertiesProcedure(self, procedure_name):
        return self.connection.Query('''
            select current_database() as "Database",
                   n.nspname as "Schema",
                   p.proname as "Procedure",
                   quote_ident(n.nspname) || '.' || quote_ident(p.proname) || '(' || oidvectortypes(p.proargtypes) || ')' as "Procedure ID",
                   p.oid as "OID",
                   r.rolname as "Owner",
                   l.lanname as "Language",
                   p.procost as "Estimated Execution Cost",
                   p.prorows as "Estimated Returned Rows",
                   p.prosecdef as "Security Definer",
                   p.proleakproof as "Leak Proof",
                   p.proisstrict as "Is Strict",
                   (case p.provolatile when 'i' then 'Immutable' when 's' then 'Stable' when 'v' then 'Volatile' end) as "Volatile",
                   (case p.proparallel when 's' then 'Safe' when 'r' then 'Restricted' when 'u' then 'Unsafe' end) as "Parallel",
                   p.pronargs as "Number of Arguments",
                   p.pronargdefaults as "Number of Default Arguments",
                   p.probin as "Invoke",
                   p.proconfig as "Configuration",
                   p.proacl as "ACL"
            from pg_proc p
            join pg_namespace n
            on p.pronamespace = n.oid
            inner join pg_roles r
            on r.oid = p.proowner
            inner join pg_language l
            on l.oid = p.prolang
            where quote_ident(n.nspname) || '.' || quote_ident(p.proname) || '(' || oidvectortypes(p.proargtypes) || ')' = '{0}'
              and p.prokind = 'p'
        '''.format(procedure_name))
    
    @lock_required
    def GetPropertiesTrigger(self, schema, table, trigger_name):
        return self.connection.Query('''
            select current_database() as "Database",
                   y.schema_name as "Schema",
                   y.table_name as "Table",
                   y.trigger_name as "Trigger",
                   y.oid as "OID",
                   y.trigger_enabled as "Enabled",
                   y.trigger_function_name as "Trigger Function",
                   x.action_timing as "Action Timing",
                   x.event_manipulation as "Action Manipulation",
                   x.action_orientation as "Action Orientation",
                   x.action_condition as "Action Condition",
                   x.action_statement as "Action Statement"
            from (
            select distinct quote_ident(t.event_object_schema) as schema_name,
                   quote_ident(t.event_object_table) as table_name,
                   quote_ident(t.trigger_name) as trigger_name,
                   t.action_timing,
                   array_to_string(array(
                   select t2.event_manipulation::text
                   from information_schema.triggers t2
                   where t2.event_object_schema = t.event_object_schema
                     and t2.event_object_table = t.event_object_table
                     and t2.trigger_name = t.trigger_name
                   ), ' OR ') as event_manipulation,
                   t.action_orientation,
                   t.action_condition,
                   t.action_statement
            from information_schema.triggers t
            where quote_ident(t.event_object_schema) = '{0}'
              and quote_ident(t.event_object_table) = '{1}'
              and quote_ident(t.trigger_name) = '{2}'
            ) x
            inner join (
            select t.oid,
                   quote_ident(n.nspname) as schema_name,
                   quote_ident(c.relname) as table_name,
                   quote_ident(t.tgname) as trigger_name,
                   t.tgenabled as trigger_enabled,
                   quote_ident(np.nspname) || '.' || quote_ident(p.proname) as trigger_function_name,
                   quote_ident(np.nspname) || '.' || quote_ident(p.proname) || '()' as trigger_function_id
            from pg_trigger t
            inner join pg_class c
            on c.oid = t.tgrelid
            inner join pg_namespace n
            on n.oid = c.relnamespace
            inner join pg_proc p
            on p.oid = t.tgfoid
            inner join pg_namespace np
            on np.oid = p.pronamespace
            where not t.tgisinternal
              and quote_ident(n.nspname) = '{0}'
              and quote_ident(c.relname) = '{1}'
              and quote_ident(t.tgname) = '{2}'
            ) y
            on y.schema_name = x.schema_name
            and y.table_name = x.table_name
            and y.trigger_name = x.trigger_name
        '''.format(schema, table, trigger_name))
    
    @lock_required
    def GetPropertiesEventTrigger(self, event_name):
        return self.connection.Query('''
            select current_database() as "Database",
                   quote_ident(t.evtname) as "Event Trigger Name",
                   t.evtevent as "Event",
                   array_to_string(t.evttags, ', ') as "Tags",
                   t.oid as "OID",
                   t.evtenabled as "Enabled",
                   r.rolname as "Owner",
                   quote_ident(np.nspname) || '.' || quote_ident(p.proname) as "Event Trigger Function"
            from pg_event_trigger t
            inner join pg_proc p
            on p.oid = t.evtfoid
            inner join pg_namespace np
            on np.oid = p.pronamespace
            inner join pg_roles r
            on r.oid = t.evtowner
            where quote_ident(t.evtname) = '{0}'
        '''.format(event_name))

    @lock_required
    def GetPropertiesAggregate(self, aggregate_name):
        return self.connection.Query(
            '''
                WITH procs AS (
                    SELECT p.oid AS function_oid,
                            quote_ident(n.nspname) || '.' || quote_ident(p.proname) || '(' || oidvectortypes(p.proargtypes) || ')' AS function_id,
                            quote_ident(n.nspname) AS schema_name,
                            quote_ident(p.proname) AS function_name,
                            r.rolname AS function_owner,
                            p.prokind AS function_kind,
                            p.proparallel
                    FROM pg_proc p
                    INNER JOIN pg_namespace n
                            ON p.pronamespace = n.oid
                    INNER JOIN pg_roles r
                            ON p.proowner = r.oid
                ),
                operators AS (
                    SELECT o.oid AS operator_oid,
                            quote_ident(n.nspname) AS schema_name,
                            quote_ident(o.oprname) AS operator_name
                    FROM pg_operator o
                    INNER JOIN pg_namespace n
                            ON o.oprnamespace = n.oid
                ),
                types AS (
                    SELECT t.oid AS type_oid,
                            quote_ident(n.nspname) AS schema_name,
                            quote_ident(t.typname) AS type_name
                    FROM pg_type t
                    INNER JOIN pg_namespace n
                            ON t.typnamespace = n.oid
                )
                SELECT current_database() as "Database",
                        p1.schema_name AS "Schema",
                        p1.function_name AS "Aggregate",
                        p1.function_id AS "Aggregate ID",
                        a.aggfnoid AS "OID",
                        p1.function_owner as "Owner",
                        a.aggkind AS "Kind",
                        a.aggnumdirectargs AS "Number of Direct Args",
                        p2.function_id AS "Transition Function ID",
                        p3.function_id AS "Final Function ID",
                        p4.function_id AS "Combine Function ID",
                        p5.function_id AS "Serialization Function ID",
                        p6.function_id AS "Deerialization Function ID",
                        p7.function_id AS "Forward Transition Function ID",
                        p8.function_id AS "Inverse Transition Function ID",
                        p9.function_id AS "Final Moving Function ID",
                        a.aggfinalextra AS "Extra Dummy to Final Function",
                        a.aggmfinalextra AS "Extra Dummy to Final Moving Function",
                        a.aggfinalmodify AS "Final Function Modifier",
                        a.aggmfinalmodify AS "Final Moving Function Modifier",
                        o.operator_name AS "Sort Operator",
                        format('%s.%s', t1.schema_name, t1.type_name)::regtype AS "Internal Transition Data Type",
                        a.aggtransspace AS "Average Size of Transition",
                        format('%s.%s', t1.schema_name, t1.type_name)::regtype AS "Internal Transition Moving Data Type",
                        a.aggmtransspace AS "Average Size of Transition Moving",
                        a.agginitval AS "Transition Init Value",
                        a.aggminitval AS "Transition Moving Init Value",
                        p1.proparallel AS "Parallel Mode"
                FROM pg_aggregate a
                INNER JOIN procs p1
                        ON a.aggfnoid = p1.function_oid
                LEFT JOIN procs p2
                        ON a.aggtransfn = p2.function_oid
                LEFT JOIN procs p3
                        ON a.aggfinalfn = p3.function_oid
                LEFT JOIN procs p4
                        ON a.aggcombinefn = p4.function_oid
                LEFT JOIN procs p5
                        ON a.aggserialfn = p5.function_oid
                LEFT JOIN procs p6
                        ON a.aggdeserialfn = p6.function_oid
                LEFT JOIN procs p7
                        ON a.aggmtransfn = p7.function_oid
                LEFT JOIN procs p8
                        ON a.aggminvtransfn = p8.function_oid
                LEFT JOIN procs p9
                        ON a.aggmfinalfn = p9.function_oid
                LEFT JOIN operators o
                        ON a.aggsortop = o.operator_oid
                LEFT JOIN types t1
                        ON a.aggtranstype = t1.type_oid
                LEFT JOIN types t2
                        ON a.aggmtranstype = t2.type_oid
                WHERE p1.function_kind = 'a'
                    AND p1.function_id = '{0}'
            '''.format(
                aggregate_name
            )
        )

    @lock_required
    def GetPropertiesPK(self, schema, table, constraint_name):
        return self.connection.Query('''
            create or replace function pg_temp.fnc_omnidb_constraint_attrs(text, text, text)
            returns text as $$
            select array_to_string(array(
            select a.attname
            from (
            select unnest(c.conkey) as conkey
            from pg_constraint c
            join pg_class t
            on t.oid = c.conrelid
            join pg_namespace n
            on t.relnamespace = n.oid
            where contype = 'p'
              and quote_ident(n.nspname) = $1
              and quote_ident(t.relname) = $2
              and quote_ident(c.conname) = $3
            ) x
            inner join pg_attribute a
            on a.attnum = x.conkey
            inner join pg_class r
            on r.oid = a.attrelid
            inner join pg_namespace n
            on n.oid = r.relnamespace
            where quote_ident(n.nspname) = $1
              and quote_ident(r.relname) = $2
            ), ',')
            $$ language sql;
            select current_database() as "Database",
                   quote_ident(n.nspname) as "Schema",
                   quote_ident(t.relname) as "Table",
                   quote_ident(c.conname) as "Constraint Name",
                   c.oid as "OID",
                   (case c.contype when 'c' then 'Check' when 'f' then 'Foreign Key' when 'p' then 'Primary Key' when 'u' then 'Unique' when 'x' then 'Exclusion' end) as "Constraint Type",
                   pg_temp.fnc_omnidb_constraint_attrs(
                       quote_ident(n.nspname),
                       quote_ident(t.relname),
                       quote_ident(c.conname)
                   ) as "Constrained Columns",
                   quote_ident(i.relname) as "Index",
                   c.condeferrable as "Deferrable",
                   c.condeferred as "Deferred by Default",
                   c.convalidated as "Validated",
                   c.conislocal as "Is Local",
                   c.coninhcount as "Number of Ancestors",
                   c.connoinherit as "Non-Inheritable"
            from pg_constraint c
            join pg_class t
            on t.oid = c.conrelid
            join pg_namespace n
            on t.relnamespace = n.oid
            join pg_class i
            on i.oid = c.conindid
            where contype = 'p'
              and quote_ident(n.nspname) = '{0}'
              and quote_ident(t.relname) = '{1}'
              and quote_ident(c.conname) = '{2}'
        '''.format(schema, table, constraint_name))
    
    @lock_required
    def GetPropertiesFK(self, schema, table, constraint_name):
        return self.connection.Query('''
            create or replace function pg_temp.fnc_omnidb_constraint_attrs(text, text, text)
            returns text as $$
            select array_to_string(array(
            select a.attname
            from (
            select unnest(c.conkey) as conkey
            from pg_constraint c
            join pg_class t
            on t.oid = c.conrelid
            join pg_namespace n
            on t.relnamespace = n.oid
            where contype = 'f'
              and quote_ident(n.nspname) = $1
              and quote_ident(t.relname) = $2
              and quote_ident(c.conname) = $3
            ) x
            inner join pg_attribute a
            on a.attnum = x.conkey
            inner join pg_class r
            on r.oid = a.attrelid
            inner join pg_namespace n
            on n.oid = r.relnamespace
            where quote_ident(n.nspname) = $1
              and quote_ident(r.relname) = $2
            ), ',')
            $$ language sql;
            create or replace function pg_temp.fnc_omnidb_rconstraint_attrs(text, text, text)
            returns text as $$
            select array_to_string(array(
            select a.attname
            from (
            select unnest(c.confkey) as confkey
            from pg_constraint c
            join pg_class t
            on t.oid = c.conrelid
            join pg_namespace n
            on t.relnamespace = n.oid
            where contype = 'f'
              and quote_ident(n.nspname) = $1
              and quote_ident(t.relname) = $2
              and quote_ident(c.conname) = $3
            ) x
            inner join pg_attribute a
            on a.attnum = x.confkey
            inner join pg_class r
            on r.oid = a.attrelid
            inner join pg_namespace n
            on n.oid = r.relnamespace
            where quote_ident(n.nspname) = $1
              and quote_ident(r.relname) = $2
            ), ',')
            $$ language sql;
            create or replace function pg_temp.fnc_omnidb_pfconstraint_ops(text, text, text)
            returns text as $$
            select array_to_string(array(
            select oprname
            from (
            select o.oprname
            from (
            select unnest(c.conpfeqop) as conpfeqop
            from pg_constraint c
            join pg_class t
            on t.oid = c.conrelid
            join pg_namespace n
            on t.relnamespace = n.oid
            where contype = 'x'
              and quote_ident(n.nspname) = $1
              and quote_ident(t.relname) = $2
              and quote_ident(c.conname) = $3
            ) x
            inner join pg_operator o
            on o.oid = x.conpfeqop
            ) t
            ), ',')
            $$ language sql;
            create or replace function pg_temp.fnc_omnidb_ppconstraint_ops(text, text, text)
            returns text as $$
            select array_to_string(array(
            select oprname
            from (
            select o.oprname
            from (
            select unnest(c.conppeqop) as conppeqop
            from pg_constraint c
            join pg_class t
            on t.oid = c.conrelid
            join pg_namespace n
            on t.relnamespace = n.oid
            where contype = 'x'
              and quote_ident(n.nspname) = $1
              and quote_ident(t.relname) = $2
              and quote_ident(c.conname) = $3
            ) x
            inner join pg_operator o
            on o.oid = x.conppeqop
            ) t
            ), ',')
            $$ language sql;
            create or replace function pg_temp.fnc_omnidb_ffconstraint_ops(text, text, text)
            returns text as $$
            select array_to_string(array(
            select oprname
            from (
            select o.oprname
            from (
            select unnest(c.conffeqop) as conffeqop
            from pg_constraint c
            join pg_class t
            on t.oid = c.conrelid
            join pg_namespace n
            on t.relnamespace = n.oid
            where contype = 'x'
              and quote_ident(n.nspname) = $1
              and quote_ident(t.relname) = $2
              and quote_ident(c.conname) = $3
            ) x
            inner join pg_operator o
            on o.oid = x.conffeqop
            ) t
            ), ',')
            $$ language sql;
            select current_database() as "Database",
                   quote_ident(n.nspname) as "Schema",
                   quote_ident(t.relname) as "Table",
                   quote_ident(c.conname) as "Constraint Name",
                   c.oid as "OID",
                   (case c.contype when 'c' then 'Check' when 'f' then 'Foreign Key' when 'p' then 'Primary Key' when 'u' then 'Unique' when 'x' then 'Exclusion' end) as "Constraint Type",
                   pg_temp.fnc_omnidb_constraint_attrs(
                       quote_ident(n.nspname),
                       quote_ident(t.relname),
                       quote_ident(c.conname)
                   ) as "Constrained Columns",
                   quote_ident(i.relname) as "Index",
                   quote_ident(nr.nspname) as "Referenced Schema",
                   quote_ident(tr.relname) as "Referenced Table",
                   pg_temp.fnc_omnidb_rconstraint_attrs(
                       quote_ident(n.nspname),
                       quote_ident(t.relname),
                       quote_ident(c.conname)
                   ) as "Referenced Columns",
                   (case c.confupdtype when 'a' then 'No Action' when 'r' then 'Restrict' when 'c' then 'Cascade' when 'n' then 'Set Null' when 'd' then 'Set Default' end) as "Update Action",
                   (case c.confdeltype when 'a' then 'No Action' when 'r' then 'Restrict' when 'c' then 'Cascade' when 'n' then 'Set Null' when 'd' then 'Set Default' end) as "Delete Action",
                   (case c.confmatchtype when 'f' then 'Full' when 'p' then 'Partial' when 's' then 'Simple' end) as "Match Type",
                   c.condeferrable as "Deferrable",
                   c.condeferred as "Deferred by Default",
                   c.convalidated as "Validated",
                   c.conislocal as "Is Local",
                   c.coninhcount as "Number of Ancestors",
                   c.connoinherit as "Non-Inheritable",
                   pg_temp.fnc_omnidb_pfconstraint_ops(
                       quote_ident(n.nspname),
                       quote_ident(t.relname),
                       quote_ident(c.conname)
                   ) as "PK=FK Equality Operators",
                   pg_temp.fnc_omnidb_ppconstraint_ops(
                       quote_ident(n.nspname),
                       quote_ident(t.relname),
                       quote_ident(c.conname)
                   ) as "PK=PK Equality Operators",
                   pg_temp.fnc_omnidb_ffconstraint_ops(
                       quote_ident(n.nspname),
                       quote_ident(t.relname),
                       quote_ident(c.conname)
                   ) as "FK=FK Equality Operators"
            from pg_constraint c
            join pg_class t
            on t.oid = c.conrelid
            join pg_namespace n
            on t.relnamespace = n.oid
            join pg_class i
            on i.oid = c.conindid
            join pg_class tr
            on tr.oid = c.confrelid
            join pg_namespace nr
            on tr.relnamespace = nr.oid
            where contype = 'f'
              and quote_ident(n.nspname) = '{0}'
              and quote_ident(t.relname) = '{1}'
              and quote_ident(c.conname) = '{2}'
        '''.format(schema, table, constraint_name))
    
    @lock_required
    def GetPropertiesUnique(self, schema, table, constraint_name):
        return self.connection.Query('''
            create or replace function pg_temp.fnc_omnidb_constraint_attrs(text, text, text)
            returns text as $$
            select array_to_string(array(
            select a.attname
            from (
            select unnest(c.conkey) as conkey
            from pg_constraint c
            join pg_class t
            on t.oid = c.conrelid
            join pg_namespace n
            on t.relnamespace = n.oid
            where contype = 'u'
              and quote_ident(n.nspname) = $1
              and quote_ident(t.relname) = $2
              and quote_ident(c.conname) = $3
            ) x
            inner join pg_attribute a
            on a.attnum = x.conkey
            inner join pg_class r
            on r.oid = a.attrelid
            inner join pg_namespace n
            on n.oid = r.relnamespace
            where quote_ident(n.nspname) = $1
              and quote_ident(r.relname) = $2
            ), ',')
            $$ language sql;
            select current_database() as "Database",
                   quote_ident(n.nspname) as "Schema",
                   quote_ident(t.relname) as "Table",
                   quote_ident(c.conname) as "Constraint Name",
                   c.oid as "OID",
                   (case c.contype when 'c' then 'Check' when 'f' then 'Foreign Key' when 'p' then 'Primary Key' when 'u' then 'Unique' when 'x' then 'Exclusion' end) as "Constraint Type",
                   pg_temp.fnc_omnidb_constraint_attrs(
                       quote_ident(n.nspname),
                       quote_ident(t.relname),
                       quote_ident(c.conname)
                   ) as "Constrained Columns",
                   quote_ident(i.relname) as "Index",
                   c.condeferrable as "Deferrable",
                   c.condeferred as "Deferred by Default",
                   c.convalidated as "Validated",
                   c.conislocal as "Is Local",
                   c.coninhcount as "Number of Ancestors",
                   c.connoinherit as "Non-Inheritable"
            from pg_constraint c
            join pg_class t
            on t.oid = c.conrelid
            join pg_namespace n
            on t.relnamespace = n.oid
            join pg_class i
            on i.oid = c.conindid
            where contype = 'u'
              and quote_ident(n.nspname) = '{0}'
              and quote_ident(t.relname) = '{1}'
              and quote_ident(c.conname) = '{2}'
        '''.format(schema, table, constraint_name))
    
    @lock_required
    def GetPropertiesCheck(self, schema, table, constraint_name):
        return self.connection.Query('''
            create or replace function pg_temp.fnc_omnidb_constraint_attrs(text, text, text)
            returns text as $$
            select array_to_string(array(
            select a.attname
            from (
            select unnest(c.conkey) as conkey
            from pg_constraint c
            join pg_class t
            on t.oid = c.conrelid
            join pg_namespace n
            on t.relnamespace = n.oid
            where contype = 'c'
              and quote_ident(n.nspname) = $1
              and quote_ident(t.relname) = $2
              and quote_ident(c.conname) = $3
            ) x
            inner join pg_attribute a
            on a.attnum = x.conkey
            inner join pg_class r
            on r.oid = a.attrelid
            inner join pg_namespace n
            on n.oid = r.relnamespace
            where quote_ident(n.nspname) = $1
              and quote_ident(r.relname) = $2
            ), ',')
            $$ language sql;
            select current_database() as "Database",
                   quote_ident(n.nspname) as "Schema",
                   quote_ident(t.relname) as "Table",
                   quote_ident(c.conname) as "Constraint Name",
                   c.oid as "OID",
                   (case c.contype when 'c' then 'Check' when 'f' then 'Foreign Key' when 'p' then 'Primary Key' when 'u' then 'Unique' when 'x' then 'Exclusion' end) as "Constraint Type",
                   pg_temp.fnc_omnidb_constraint_attrs(
                       quote_ident(n.nspname),
                       quote_ident(t.relname),
                       quote_ident(c.conname)
                   ) as "Constrained Columns",
                   c.condeferrable as "Deferrable",
                   c.condeferred as "Deferred by Default",
                   c.convalidated as "Validated",
                   c.conislocal as "Is Local",
                   c.coninhcount as "Number of Ancestors",
                   c.connoinherit as "Non-Inheritable",
                   pg_get_constraintdef(c.oid) as "Constraint Source"
            from pg_constraint c
            join pg_class t
            on t.oid = c.conrelid
            join pg_namespace n
            on t.relnamespace = n.oid
            where contype = 'c'
              and quote_ident(n.nspname) = '{0}'
              and quote_ident(t.relname) = '{1}'
              and quote_ident(c.conname) = '{2}'
        '''.format(schema, table, constraint_name))
    
    @lock_required
    def GetPropertiesExclude(self, schema, table, constraint_name):
        return self.connection.Query('''
            create or replace function pg_temp.fnc_omnidb_constraint_ops(text, text, text)
            returns text as $$
            select array_to_string(array(
            select oprname
            from (
            select o.oprname
            from (
            select unnest(c.conexclop) as conexclop
            from pg_constraint c
            join pg_class t
            on t.oid = c.conrelid
            join pg_namespace n
            on t.relnamespace = n.oid
            where contype = 'x'
              and quote_ident(n.nspname) = $1
              and quote_ident(t.relname) = $2
              and quote_ident(c.conname) = $3
            ) x
            inner join pg_operator o
            on o.oid = x.conexclop
            ) t
            ), ',')
            $$ language sql;
            create or replace function pg_temp.fnc_omnidb_constraint_attrs(text, text, text)
            returns text as $$
            select array_to_string(array(
            select a.attname
            from (
            select unnest(c.conkey) as conkey
            from pg_constraint c
            join pg_class t
            on t.oid = c.conrelid
            join pg_namespace n
            on t.relnamespace = n.oid
            where contype = 'x'
              and quote_ident(n.nspname) = $1
              and quote_ident(t.relname) = $2
              and quote_ident(c.conname) = $3
            ) x
            inner join pg_attribute a
            on a.attnum = x.conkey
            inner join pg_class r
            on r.oid = a.attrelid
            inner join pg_namespace n
            on n.oid = r.relnamespace
            where quote_ident(n.nspname) = $1
              and quote_ident(r.relname) = $2
            ), ',')
            $$ language sql;
            select current_database() as "Database",
                   quote_ident(n.nspname) as "Schema",
                   quote_ident(t.relname) as "Table",
                   quote_ident(c.conname) as "Constraint Name",
                   c.oid as "OID",
                   (case c.contype when 'c' then 'Check' when 'f' then 'Foreign Key' when 'p' then 'Primary Key' when 'u' then 'Unique' when 'x' then 'Exclusion' end) as "Constraint Type",
                   pg_temp.fnc_omnidb_constraint_attrs(
                       quote_ident(n.nspname),
                       quote_ident(t.relname),
                       quote_ident(c.conname)
                   ) as "Constrained Columns",
                   pg_temp.fnc_omnidb_constraint_ops(
                       quote_ident(n.nspname),
                       quote_ident(t.relname),
                       quote_ident(c.conname)
                   ) as "Exclusion Operators",
                   c.condeferrable as "Deferrable",
                   c.condeferred as "Deferred by Default",
                   c.convalidated as "Validated",
                   c.conislocal as "Is Local",
                   c.coninhcount as "Number of Ancestors",
                   c.connoinherit as "Non-Inheritable"
            from pg_constraint c
            join pg_class t
            on t.oid = c.conrelid
            join pg_namespace n
            on t.relnamespace = n.oid
            where contype = 'x'
              and quote_ident(n.nspname) = '{0}'
              and quote_ident(t.relname) = '{1}'
              and quote_ident(c.conname) = '{2}'
        '''.format(schema, table, constraint_name))
    
    @lock_required
    def GetPropertiesRule(self, schema, table, rule):
        return self.connection.Query('''
            select current_database() as "Database",
                   quote_ident(schemaname) as "Schema",
                   quote_ident(tablename) as "Table",
                   quote_ident(rulename) as "Rule Name"
            from pg_rules
            where quote_ident(schemaname) = '{0}'
              and quote_ident(tablename) = '{1}'
              and quote_ident(rulename) = '{2}'
        '''.format(schema, table, rule))
    
    @lock_required
    def GetPropertiesForeignTable(self, schema, table):
        return self.connection.Query('''
            select current_database() as "Database",
                    n.nspname as "Schema",
                    c.relname as "Table",
                    c.oid as "OID",
                    r.rolname as "Owner",
                    pg_size_pretty(pg_relation_size(c.oid)) as "Size",
                    coalesce(t1.spcname, t2.spcname) as "Tablespace",
                    c.relacl as "ACL",
                    c.reloptions as "Options",
                    pg_relation_filepath(c.oid) as "Filenode",
                    c.reltuples as "Estimate Count",
                    c.relhasindex as "Has Index",
                    (case c.relpersistence when 'p' then 'Permanent' when 'u' then 'Unlogged' when 't' then 'Temporary' end) as "Persistence",
                    c.relnatts as "Number of Attributes",
                    c.relchecks as "Number of Checks",
                    c.relhasrules as "Has Rules",
                    c.relhastriggers as "Has Triggers",
                    c.relhassubclass as "Has Subclass",
                    c.relkind = 'p' as "Is Partitioned",
                    c.relispartition as "Is Partition",
                    (case when c.relispartition then po.parent_table else '' end) as "Partition Of",
                    array_to_string(f.ftoptions, ',') as "Foreign Table Options",
                    s.srvname as "Foreign Server",
                    w.fdwname as "Foreign Data Wrapper"
            from pg_class c
            inner join pg_namespace n
            on n.oid = c.relnamespace
            inner join pg_roles r
            on r.oid = c.relowner
            left join pg_tablespace t1
            on t1.oid = c.reltablespace
            inner join (
            select t.spcname
            from pg_database d
            inner join pg_tablespace t
            on t.oid = d.dattablespace
            where d.datname = current_database()
            ) t2
            on 1 = 1
            left join (
            select quote_ident(n2.nspname) || '.' || quote_ident(c2.relname) as parent_table
            from pg_inherits i
            inner join pg_class c2
            on c2.oid = i.inhparent
            inner join pg_namespace n2
            on n2.oid = c2.relnamespace
            where i.inhrelid = '{0}.{1}'::regclass
            ) po
            on 1 = 1
            inner join pg_foreign_table f
            on f.ftrelid = c.oid
            inner join pg_foreign_server s
            on s.oid = f.ftserver
            inner join pg_foreign_data_wrapper w
            on w.oid = s.srvfdw
            where quote_ident(n.nspname) = '{0}'
                and quote_ident(c.relname) = '{1}'
        '''.format(schema, table))
    
    @lock_required
    def GetPropertiesUserMapping(self, server, role_name):
        if role_name == 'PUBLIC':
            return self.connection.Query('''
                select current_database() as "Database",
                       u.oid as "OID",
                       'PUBLIC' as "User",
                       array_to_string(u.umoptions, ',') as "Options",
                       s.srvname as "Foreign Server",
                       w.fdwname as "Foreign Wrapper"
                from pg_user_mapping u
                inner join pg_foreign_server s
                on s.oid = u.umserver
                inner join pg_foreign_data_wrapper w
                on w.oid = s.srvfdw
                where u.umuser = 0
                  and quote_ident(s.srvname) = '{0}'
            '''.format(server))
        else:
            return self.connection.Query('''
                select current_database() as "Database",
                       u.oid as "OID",
                       r.rolname as "User",
                       array_to_string(u.umoptions, ',') as "Options",
                       s.srvname as "Foreign Server",
                       w.fdwname as "Foreign Wrapper"
                from pg_user_mapping u
                inner join pg_foreign_server s
                on s.oid = u.umserver
                inner join pg_foreign_data_wrapper w
                on w.oid = s.srvfdw
                inner join pg_roles r
                on r.oid = u.umuser
                where quote_ident(s.srvname) = '{0}'
                  and quote_ident(r.rolname) = '{1}'
            '''.format(server, role_name))
    
    @lock_required
    def GetPropertiesForeignServer(self, server_name):
        return self.connection.Query('''
            select current_database() as "Database",
                   s.srvname as "Name",
                   s.oid as "OID",
                   r.rolname as "Owner",
                   s.srvtype as "Type",
                   s.srvversion as "Version",
                   array_to_string(srvoptions, ',') as "Options",
                   w.fdwname as "Foreign Wrapper"
            from pg_foreign_server s
            inner join pg_foreign_data_wrapper w
            on w.oid = s.srvfdw
            inner join pg_roles r
            on r.oid = s.srvowner
            where quote_ident(s.srvname) = '{0}'
        '''.format(server_name))
    
    @lock_required
    def GetPropertiesForeignDataWrapper(self, fdw_name):
        return self.connection.Query('''
            select current_database() as "Database",
                   w.fdwname as "Name",
                   w.oid as "OID",
                   r.rolname as "Owner",
                   h.proname as "Handler",
                   v.proname as "Validator",
                   array_to_string(w.fdwoptions, ',') as "Options"
            from pg_foreign_data_wrapper w
            inner join pg_roles r
            on r.oid = w.fdwowner
            left join pg_proc h
            on h.oid = w.fdwhandler
            left join pg_proc v
            on v.oid = w.fdwvalidator
            where quote_ident(w.fdwname) = '{0}'
        '''.format(fdw_name))
    
    @lock_required
    def GetPropertiesType(self, schema, type_name):
        return self.connection.Query('''
            select current_database() as "Database",
                   n.nspname as "Schema",
                   t.typname as "Internal Type Name",
                   format_type(t.oid, null) as "SQL Type Name",
                   t.oid as "OID",
                   r.rolname as "Owner",
                   (case when t.typlen = -2 then 'Variable (null-terminated C string)'
                         when t.typlen = -1 then 'Variable (varlena type)'
                         else format('%s bytes', t.typlen)
                    end) as "Size",
                   t.typbyval as "Passed by Value",
                   (case t.typtype
                      when 'b' then 'Base'
                      when 'c' then 'Composite'
                      when 'd' then 'Domain'
                      when 'e' then 'Enum'
                      when 'p' then 'Pseudo'
                      when 'r' then 'Range'
                      else 'Undefined'
                    end) as "Type",
                   (case t.typcategory
                      when 'A' then 'A - Array'
                      when 'B' then 'B - Boolean'
                      when 'C' then 'C - Composite'
                      when 'D' then 'D - Date/Time'
                      when 'E' then 'E - Enum'
                      when 'G' then 'G - Geometric'
                      when 'I' then 'I - Network Address'
                      when 'N' then 'N - Numeric'
                      when 'P' then 'P - Pseudo'
                      when 'R' then 'R - Range'
                      when 'S' then 'S - String'
                      when 'T' then 'T - Timespan'
                      when 'U' then 'U - User-defined'
                      when 'V' then 'V - Bit-string'
                      else 'X - Unknown'
                    end) as "Category",
                   t.typispreferred as "Is Preferred",
                   t.typisdefined as "Is Defined",
                   t.typdelim as "Delimiter",
                   nrelid.nspname || '.' || crelid.relname as "Corresponding Table",
                   nelem.nspname || '.' || telem.typname as "Element Type",
                   narray.nspname || '.' || tarray.typname as "Array Type",
                   ninput.nspname || '.' || pinput.proname as "Input Conversion Function (Text Format)",
                   noutput.nspname || '.' || poutput.proname as "Output Conversion Function (Text Format)",
                   nreceive.nspname || '.' || preceive.proname as "Input Conversion Function (Binary Format)",
                   nsend.nspname || '.' || psend.proname as "Output Conversion Function (Binary Format)",
                   nmodin.nspname || '.' || pmodin.proname as "Type Modifier Input Function",
                   nmodout.nspname || '.' || pmodout.proname as "Type Modifier Input Function",
                   nanalyze.nspname || '.' || panalyze.proname as "Custom Analyze Function",
                   (case t.typalign
                      when 'c' then 'char'
                      when 's' then 'int2'
                      when 'i' then 'int4'
                      when 'd' then 'double'
                    end) as "Alignment",
                   (case t.typstorage
                      when 'p' then 'plain'
                      when 'e' then 'extended'
                      when 'm' then 'main'
                      when 'x' then 'external'
                    end) as "Storage",
                   t.typnotnull as "Not Null",
                   nbase.nspname || '.' || tbase.typname as "Base Type",
                   t.typtypmod as "Type Modifier",
                   t.typndims as "Number of Array Dimensions",
                   coll.collname as "Collation",
                   t.typdefault as "Default Value",
                   t.typacl as "ACL"
            from pg_type t
            inner join pg_roles r on r.oid = t.typowner
            inner join pg_namespace n on n.oid = t.typnamespace
            left join pg_class crelid on crelid.oid = t.typrelid
            left join pg_namespace nrelid on nrelid.oid = crelid.relnamespace
            left join pg_type telem on telem.oid = t.typelem
            left join pg_namespace nelem on nelem.oid = telem.typnamespace
            left join pg_type tarray on tarray.oid = t.typarray
            left join pg_namespace narray on narray.oid = tarray.typnamespace
            left join pg_proc pinput on pinput.oid = t.typinput
            left join pg_namespace ninput on ninput.oid = pinput.pronamespace
            left join pg_proc poutput on poutput.oid = t.typoutput
            left join pg_namespace noutput on noutput.oid = poutput.pronamespace
            left join pg_proc preceive on preceive.oid = t.typreceive
            left join pg_namespace nreceive on nreceive.oid = preceive.pronamespace
            left join pg_proc psend on psend.oid = t.typsend
            left join pg_namespace nsend on nsend.oid = psend.pronamespace
            left join pg_proc pmodin on pmodin.oid = t.typmodin
            left join pg_namespace nmodin on nmodin.oid = pmodin.pronamespace
            left join pg_proc pmodout on pmodout.oid = t.typmodout
            left join pg_namespace nmodout on nmodout.oid = pmodout.pronamespace
            left join pg_proc panalyze on panalyze.oid = t.typanalyze
            left join pg_namespace nanalyze on nanalyze.oid = panalyze.pronamespace
            left join pg_type tbase on tbase.oid = t.typbasetype
            left join pg_namespace nbase on nbase.oid = tbase.typnamespace
            left join pg_collation coll on coll.oid = t.typcollation
            where quote_ident(n.nspname) = '{0}'
              and quote_ident(t.typname) = '{1}'
        '''.format(schema, type_name))

    @lock_required
    def GetPropertiesPublication(self, pub_name):
        if self.version_num < 130000:
            return self.connection.Query('''
                SELECT current_database() as "Database",
                       p.pubname AS "Name",
                       p.oid AS "OID",
                       r.rolname as "Owner",
                       p.puballtables AS "All Tables",
                       p.pubinsert AS "Inserts",
                       p.pubupdate AS "Updates",
                       p.pubdelete AS "Deletes",
                       p.pubtruncate AS "Truncates"
                FROM pg_publication p
                INNER JOIN pg_roles r
                        ON p.pubowner = r.oid
                WHERE quote_ident(p.pubname) = '{0}'
            '''.format(pub_name))
        else:
            return self.connection.Query('''
                SELECT current_database() as "Database",
                       p.pubname AS "Name",
                       p.oid AS "OID",
                       r.rolname as "Owner",
                       p.puballtables AS "All Tables",
                       p.pubinsert AS "Inserts",
                       p.pubupdate AS "Updates",
                       p.pubdelete AS "Deletes",
                       p.pubtruncate AS "Truncates",
                       p.pubviaroot AS "Via Partition Root"
                FROM pg_publication p
                INNER JOIN pg_roles r
                        ON p.pubowner = r.oid
                WHERE quote_ident(p.pubname) = '{0}'
            '''.format(pub_name))

    @lock_required
    def GetPropertiesSubscription(self, sub_name):
        return self.connection.Query('''
            SELECT d.datname AS "Database",
                   s.subname AS "Name",
                   s.oid AS "OID",
                   r.rolname AS "Owner",
                   s.subenabled AS "Enabled",
                   s.subconninfo AS "Connection",
                   s.subslotname AS "Slot Name",
                   s.subslotname AS "Sync Commit",
                   s.subpublications AS "Publications"
            FROM pg_subscription s
            INNER JOIN pg_database d
                    ON s.subdbid = d.oid
            INNER JOIN pg_roles r
                    ON s.subowner = r.oid
            WHERE quote_ident(s.subname) = '{0}'
        '''.format(sub_name))

    @lock_required
    def GetPropertiesStatistic(self, schema, statistic_name):
        return self.connection.Query(
            '''
                SELECT current_database() AS "Database",
                       n.nspname AS "Schema",
                       se.stxname AS "Name",
                       se.oid AS "OID",
                       r.rolname AS "Owner",
                       se.stxstattarget AS "Statistic Target",
                       se.stxkind AS "kinds"
                FROM pg_statistic_ext se
                INNER JOIN pg_namespace n
                        ON se.stxnamespace = n.oid
                INNER JOIN pg_roles r
                        ON se.stxowner = r.oid
                WHERE quote_ident(n.nspname) = '{0}'
                  AND quote_ident(se.stxname) = '{1}'
            '''.format(
                schema,
                statistic_name
            )
        )

    def GetProperties(self, schema, table, object_name, object_type):
        try:
            if object_type == 'role':
                return self.GetPropertiesRole(object_name).Transpose('Property', 'Value')
            elif object_type == 'tablespace':
                return self.GetPropertiesTablespace(object_name).Transpose('Property', 'Value')
            elif object_type == 'database':
                return self.GetPropertiesDatabase(object_name).Transpose('Property', 'Value')
            elif object_type == 'extension':
                return self.GetPropertiesExtension(object_name).Transpose('Property', 'Value')
            elif object_type == 'schema':
                return self.GetPropertiesSchema(schema).Transpose('Property', 'Value')
            elif object_type == 'table':
                return self.GetPropertiesTable(schema, object_name).Transpose('Property', 'Value')
            elif object_type == 'table_field':
                return self.GetPropertiesTableField(schema, table, object_name).Transpose('Property', 'Value')
            elif object_type == 'index':
                return self.GetPropertiesIndex(schema, object_name).Transpose('Property', 'Value')
            elif object_type == 'sequence':
                return self.GetPropertiesSequence(schema, object_name)
            elif object_type == 'view':
                return self.GetPropertiesView(schema, object_name).Transpose('Property', 'Value')
            elif object_type == 'mview':
                return self.GetPropertiesView(schema, object_name).Transpose('Property', 'Value')
            elif object_type == 'function':
                return self.GetPropertiesFunction(object_name).Transpose('Property', 'Value')
            elif object_type == 'procedure':
                return self.GetPropertiesProcedure(object_name).Transpose('Property', 'Value')
            elif object_type == 'trigger':
                return self.GetPropertiesTrigger(schema, table, object_name).Transpose('Property', 'Value')
            elif object_type == 'event_trigger':
                return self.GetPropertiesEventTrigger(object_name).Transpose('Property', 'Value')
            elif object_type == 'trigger_function':
                return self.GetPropertiesFunction(object_name).Transpose('Property', 'Value')
            elif object_type == 'direct_trigger_function':
                return self.GetPropertiesFunction(object_name).Transpose('Property', 'Value')
            elif object_type == 'event_trigger_function':
                return self.GetPropertiesFunction(object_name).Transpose('Property', 'Value')
            elif object_type == 'direct_event_trigger_function':
                return self.GetPropertiesFunction(object_name).Transpose('Property', 'Value')
            elif object_type == 'aggregate':
                return self.GetPropertiesAggregate(object_name).Transpose('Property', 'Value')
            elif object_type == 'pk':
                return self.GetPropertiesPK(schema, table, object_name).Transpose('Property', 'Value')
            elif object_type == 'foreign_key':
                return self.GetPropertiesFK(schema, table, object_name).Transpose('Property', 'Value')
            elif object_type == 'unique':
                return self.GetPropertiesUnique(schema, table, object_name).Transpose('Property', 'Value')
            elif object_type == 'check':
                return self.GetPropertiesCheck(schema, table, object_name).Transpose('Property', 'Value')
            elif object_type == 'exclude':
                return self.GetPropertiesExclude(schema, table, object_name).Transpose('Property', 'Value')
            elif object_type == 'rule':
                return self.GetPropertiesRule(schema, table, object_name).Transpose('Property', 'Value')
            elif object_type == 'foreign_table':
                return self.GetPropertiesForeignTable(schema, object_name).Transpose('Property', 'Value')
            elif object_type == 'user_mapping':
                return self.GetPropertiesUserMapping(schema, object_name).Transpose('Property', 'Value')
            elif object_type == 'foreign_server':
                return self.GetPropertiesForeignServer(object_name).Transpose('Property', 'Value')
            elif object_type == 'foreign_data_wrapper':
                return self.GetPropertiesForeignDataWrapper(object_name).Transpose('Property', 'Value')
            elif object_type == 'type':
                return self.GetPropertiesType(schema, object_name).Transpose('Property', 'Value')
            elif object_type == 'domain':
                return self.GetPropertiesType(schema, object_name).Transpose('Property', 'Value')
            elif object_type == 'publication':
                return self.GetPropertiesPublication(object_name).Transpose('Property', 'Value')
            elif object_type == 'subscription':
                return self.GetPropertiesSubscription(object_name).Transpose('Property', 'Value')
            elif object_type == 'statistic':
                return self.GetPropertiesStatistic(schema, object_name).Transpose('Property', 'Value')
            else:
                return None
        except Spartacus.Database.Exception as exc:
            if str(exc) == 'Can only transpose a table with a single row.':
                raise Exception('Object {0} does not exist anymore. Please refresh the tree view.'.format(object_name))
            else:
                raise exc
    
    @lock_required
    def GetDDLRole(self, role_name):
        return self.connection.ExecuteScalar('''
            with
            q1 as (
             select
               'CREATE ' || case when rolcanlogin then 'USER' else 'GROUP' end
               ||' '||quote_ident(rolname)|| E';\n' ||
               'ALTER ROLE '|| quote_ident(rolname) || E' WITH\n  ' ||
               case when rolcanlogin then 'LOGIN' else 'NOLOGIN' end || E'\n  ' ||
               case when rolsuper then 'SUPERUSER' else 'NOSUPERUSER' end || E'\n  ' ||
               case when rolinherit then 'INHERIT' else 'NOINHERIT' end || E'\n  ' ||
               case when rolcreatedb then 'CREATEDB' else 'NOCREATEDB' end || E'\n  ' ||
               case when rolcreaterole then 'CREATEROLE' else 'NOCREATEROLE' end || E'\n  ' ||
               case when rolreplication then 'REPLICATION' else 'NOREPLICATION' end || E';\n  ' ||
               case
                 when description is not null
                 then E'\n'
                      ||'COMMENT ON ROLE '||quote_ident(rolname)
                      ||' IS '||quote_literal(description)||E';\n'
                 else ''
               end || E'\n' ||
               case when rolpassword is not null
                    then 'ALTER ROLE '|| quote_ident(rolname)||
                         ' ENCRYPTED PASSWORD '||quote_literal(rolpassword)||E';\n'
                    else ''
               end ||
               case when rolvaliduntil is not null
                    then 'ALTER ROLE '|| quote_ident(rolname)||
                         ' VALID UNTIL '||quote_nullable(rolvaliduntil)||E';\n'
                    else ''
               end ||
               case when rolconnlimit>=0
                    then 'ALTER ROLE '|| quote_ident(rolname)||
                         ' CONNECTION LIMIT '||rolconnlimit||E';\n'
                    else ''
               end ||
               E'\n' as ddl
               from pg_roles a
               left join pg_shdescription d on d.objoid=a.oid
              where quote_ident(a.rolname) = '{0}'
             ),
            q2 as (
             select string_agg('ALTER ROLE ' || quote_ident(rolname)
                               ||' SET '||pg_roles.rolconfig[i]||E';\n','')
                as ddl_config
              from pg_roles,
              generate_series(
                 (select array_lower(rolconfig,1) from pg_roles where quote_ident(rolname)='{0}'),
                 (select array_upper(rolconfig,1) from pg_roles where quote_ident(rolname)='{0}')
              ) as generate_series(i)
             where quote_ident(rolname) = '{0}'
             ),
                                               q3 as (
                select string_agg(ddl, E'\n') as ddl_grants from (
                SELECT
                    'GRANT ' || pg_catalog.array_to_string(pg_catalog.array_agg(rolname order by rolname), ', ') || ' TO ' || '{0}' ||
                    CASE WHEN admin_option THEN ' WITH ADMIN OPTION;' ELSE ';' END AS ddl
                FROM
                    (SELECT
                    pg_catalog.quote_ident(r.rolname) AS rolname, m.admin_option AS admin_option, m.member AS member
                    FROM
                        pg_catalog.pg_auth_members m
                    LEFT JOIN pg_catalog.pg_roles r ON (m.roleid = r.oid)
                    LEFT JOIN pg_catalog.pg_roles mem ON (m.member = mem.oid)
                    WHERE
                        quote_ident(mem.rolname) = '{0}'
                    ORDER BY
                    r.rolname
                    ) a
                GROUP BY admin_option, member) b 
                )
            select ddl||coalesce(ddl_config||E'\n','') || coalesce(ddl_grants, '')
              from q1
            left join q2 on true
            left join q3 on true;
        '''.format(role_name))
    
    @lock_required
    def GetDDLTablespace(self, tablespace_name):
        return self.connection.ExecuteScalar('''
            select format(E'CREATE TABLESPACE %s\nLOCATION %s\nOWNER %s;%s',
                         quote_ident(t.spcname),
                         chr(39) || pg_tablespace_location(t.oid) || chr(39),
                         quote_ident(r.rolname),
                         (CASE WHEN shobj_description(t.oid, 'pg_tablespace') IS NOT NULL
                               THEN format(
                                       E'\n\nCOMMENT ON TABLESPACE %s IS %s;',
                                       quote_ident(t.spcname),
                                       quote_literal(shobj_description(t.oid, 'pg_tablespace'))
                                   )
                               ELSE ''
                          END)
                   )
            from pg_tablespace t
            inner join pg_roles r
            on r.oid = t.spcowner
            where quote_ident(t.spcname) = '{0}'
        '''.format(tablespace_name))
    
    @lock_required
    def GetDDLDatabase(self, database_name):
        datcollate = 'datcollate,' if self.version_num >= 80400 else ""
        datctype = 'datctype,' if self.version_num >= 80400 else ""
        # Check if PostgreSQL supports FORMAT (introduced in 9.1)
        supports_format = self.version_num >= 90100

        if supports_format:
            base_query = """
                     format(
                            E'CREATE DATABASE %s\nOWNER %s\nENCODING %s\nLC_COLLATE ''%s''\nLC_CTYPE ''%s''\nTABLESPACE %s\nALLOW_CONNECTIONS %s\nCONNECTION LIMIT %s\nIS_TEMPLATE %s;%s',
                            quote_ident(d.datname),
                            quote_ident(r.rolname),
                            pg_encoding_to_char(encoding),
                            datcollate,
                            datctype,
                            quote_ident(t.spcname),
                            datallowconn::text,
                            datconnlimit,
                            datistemplate::text,
                            (CASE WHEN c.comment IS NOT NULL
                                THEN format(
                                            E'\n\nCOMMENT ON DATABASE %s is %s;',
                                            quote_ident(d.datname),
                                            quote_literal(c.comment)
                                        )
                                ELSE ''
                            END
                            )
                        )
                        """
        else:
            datcollate = 'datcollate ||' if self.version_num >= 80400 else ""
            datctype = 'datctype ||' if self.version_num >= 80400 else ""

            base_query = f"""
                E'CREATE DATABASE ' || quote_ident(d.datname) || 
                      '\nOWNER ' || quote_ident(r.rolname) ||
                      '\nENCODING ' || pg_encoding_to_char(encoding) ||
                      '\nLC_COLLATE ' || {datcollate} '\nLC_CTYPE ' || {datctype} 
                      '\nTABLESPACE ' || quote_ident(t.spcname) || 
                      '\nALLOW_CONNECTIONS ' || CASE WHEN datallowconn THEN 'true' ELSE 'false' END ||
                      '\nCONNECTION LIMIT ' || datconnlimit || 
                      '\nIS_TEMPLATE ' || CASE WHEN datistemplate THEN 'true' ELSE 'false' END ||
                      '; ' || (CASE WHEN c.comment IS NOT NULL
                                THEN 
                                    E'\n\nCOMMENT ON DATABASE ' || quote_ident(d.datname) || ' is ' || quote_literal(c.comment) || ';'
                                ELSE ''
                            END
                            )
"""

        return self.connection.ExecuteScalar(f'''
            WITH comments AS (
                SELECT shobj_description(oid, 'pg_database') AS comment
                FROM pg_database
                WHERE quote_ident(datname) = '{database_name}'
            )
            select {base_query}
            from pg_database d
            inner join pg_roles r
            on r.oid = d.datdba
            inner join pg_tablespace t
            on t.oid = d.dattablespace
            LEFT JOIN comments c
                    ON 1 = 1
            where quote_ident(d.datname) = '{database_name}'
        ''')
    

    @lock_required
    def GetDDLExtension(self, extension_name):
        return self.connection.ExecuteScalar(
            '''
                WITH comments AS (
                    SELECT COALESCE(obj_description(oid, 'pg_extension'), '') AS description
                    FROM pg_extension
                    WHERE quote_ident(extname) = '{0}'
                )
                SELECT format(
                           E'CREATE EXTENSION {0};%s',
                           (CASE WHEN description <> ''
                                 THEN format(
                                          E'\n\nCOMMENT ON EXTENSION {0} IS %s;',
                                          description
                                      )
                                 ELSE ''
                            END)
                       ) AS sql
                FROM comments
            '''.format(
                extension_name
            )
        )

    @lock_required
    def GetDDLSchema(self, schema_name):
        return self.connection.ExecuteScalar('''
            with obj as (
               SELECT n.oid,
                     'pg_namespace'::regclass,
                     n.nspname as name,
                     current_database() as namespace,
                     case
                       when n.nspname like 'pg_%' then 'SYSTEM'
                       when n.nspname = r.rolname then 'AUTHORIZATION'
                       else 'NAMESPACE'
                     end as kind,
                     pg_get_userbyid(n.nspowner) AS owner,
                     'SCHEMA' as sql_kind,
                     quote_ident(n.nspname) as sql_identifier
                FROM pg_namespace n join pg_roles r on r.oid = n.nspowner
               WHERE quote_ident(n.nspname) = '{0}'
            ),
            comment as (
                select format(
                       E'COMMENT ON %s %s IS %L;\n\n',
                       obj.sql_kind, sql_identifier, obj_description(oid)) as text
                from obj
            ),
            alterowner as (
                select format(
                       E'ALTER %s %s OWNER TO %s;\n\n',
                       obj.sql_kind, sql_identifier, quote_ident(owner)) as text
                from obj
            ),
            privileges as (
                select (u_grantor.rolname)::information_schema.sql_identifier as grantor,
                       (grantee.rolname)::information_schema.sql_identifier as grantee,
                       (n.privilege_type)::information_schema.character_data as privilege_type,
                       (case when (pg_has_role(grantee.oid, n.nspowner, 'USAGE'::text) or n.is_grantable)
                             then 'YES'::text
                             else 'NO'::text
                        end)::information_schema.yes_or_no AS is_grantable
                from (
                    select n.nspname,
                           n.nspowner,
                           (aclexplode(COALESCE(n.nspacl, acldefault('n', n.nspowner)))).grantor as grantor,
                           (aclexplode(COALESCE(n.nspacl, acldefault('n', n.nspowner)))).grantee as grantee,
                           (aclexplode(COALESCE(n.nspacl, acldefault('n', n.nspowner)))).privilege_type as privilege_type,
                           (aclexplode(COALESCE(n.nspacl, acldefault('n', n.nspowner)))).is_grantable as is_grantable
                    from pg_namespace n
                    where quote_ident(n.nspname) = '{0}'
                ) n
                inner join pg_roles u_grantor
                on u_grantor.oid = n.grantor
                inner join (
                    select r.oid,
                           r.rolname
                    from pg_roles r
                    union all
                    select (0)::oid AS oid,
                           'PUBLIC'::name
                ) grantee
                on grantee.oid = n.grantee
            ),
            grants as (
                select coalesce(
                        string_agg(format(
                    	E'GRANT %s ON SCHEMA {0} TO %s%s;\n',
                        privilege_type,
                        case grantee
                          when 'PUBLIC' then 'PUBLIC'
                          else quote_ident(grantee)
                        end,
                    	case is_grantable
                          when 'YES' then ' WITH GRANT OPTION'
                          else ''
                        end), ''),
                       '') as text
                from privileges
            )
            select format(E'CREATE SCHEMA %s;\n\n',quote_ident(n.nspname))
            	   || comment.text
                   || alterowner.text
                   || grants.text
              from pg_namespace n
              inner join comment on 1=1
              inner join alterowner on 1=1
              inner join grants on 1=1
             where quote_ident(n.nspname) = '{0}'
        '''.format(schema_name))
    
    @lock_required
    def GetDDLClass(self, schema, class_name):
        return self.connection.ExecuteScalar('''
            with obj as (
                SELECT c.oid,
                        'pg_class'::regclass,
                        c.relname AS name,
                        n.nspname AS namespace,
                        coalesce(cc.column2,c.relkind::text) AS kind,
                        pg_get_userbyid(c.relowner) AS owner,
                        coalesce(cc.column2,c.relkind::text) AS sql_kind,
                        cast('{0}.{1}'::regclass AS text) AS sql_identifier
                FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                LEFT join (
                        values ('r','TABLE'),
                            ('v','VIEW'),
                            ('i','INDEX'),
                            ('I','PARTITIONED INDEX'),
                            ('S','SEQUENCE'),
                            ('s','SPECIAL'),
                            ('m','MATERIALIZED VIEW'),
                            ('c','TYPE'),
                            ('t','TOAST'),
                            ('f','FOREIGN TABLE'),
                            ('p','PARTITIONED TABLE')
                ) as cc on cc.column1 = c.relkind
                WHERE c.oid = '{0}.{1}'::regclass
            ),
            columns as (
                SELECT a.attname AS name, format_type(t.oid, NULL::integer) AS type,
                    CASE
                        WHEN (a.atttypmod - 4) > 0 THEN a.atttypmod - 4
                        ELSE NULL::integer
                    END AS size,
                    a.attnotnull AS not_null,
                    a.attgenerated AS generated,
                    pg_get_expr(def.adbin, def.adrelid) AS "default",
                    col_description(c.oid, a.attnum::integer) AS comment,
                    con.conname AS primary_key,
                    a.attislocal AS is_local,
                    a.attstorage::text AS storage,
                    nullif(col.collcollate::text,'') AS collation,
                    a.attnum AS ord,
                    s.nspname AS namespace,
                    c.relname AS class_name,
                    format('%s.%I',text(c.oid::regclass),a.attname) AS sql_identifier,
                    c.oid,
                    a.attacl,
                    format('%I %s%s%s%s',
                        a.attname::text,
                        format_type(t.oid, a.atttypmod),
                        CASE
                            WHEN length(col.collcollate) > 0
                            THEN ' COLLATE ' || quote_ident(col.collcollate::text)
                            ELSE ''
                        END,
                        CASE
                            WHEN a.attnotnull THEN ' NOT NULL'::text
                            ELSE ''::text
                        END,
                        CASE
                            WHEN a.attidentity = 'a' THEN ' GENERATED ALWAYS AS IDENTITY'::text
                            WHEN a.attidentity = 'd' THEN ' GENERATED BY DEFAULT AS IDENTITY'::text
                            WHEN a.attgenerated = 's' THEN format(' GENERATED ALWAYS AS %s STORED',pg_get_expr(def.adbin, def.adrelid))::text
                            ELSE ''::text
                        END)
                    AS definition
                FROM pg_class c
                JOIN pg_namespace s ON s.oid = c.relnamespace
                JOIN pg_attribute a ON c.oid = a.attrelid
                LEFT JOIN pg_attrdef def ON c.oid = def.adrelid AND a.attnum = def.adnum
                LEFT JOIN pg_constraint con
                    ON con.conrelid = c.oid AND (a.attnum = ANY (con.conkey)) AND con.contype = 'p'
                LEFT JOIN pg_type t ON t.oid = a.atttypid
                LEFT JOIN pg_collation col ON col.oid = a.attcollation
                JOIN pg_namespace tn ON tn.oid = t.typnamespace
                WHERE c.relkind IN ('r','v','c','f','p') AND a.attnum > 0 AND NOT a.attisdropped
                AND has_table_privilege(c.oid, 'select') AND has_schema_privilege(s.oid, 'usage')
                AND c.oid = '{0}.{1}'::regclass
                ORDER BY s.nspname, c.relname, a.attnum
            ),
            comments as (
                select 'COMMENT ON COLUMN ' || text('{0}.{1}') || '.' || quote_ident(name) ||
                        ' IS ' || quote_nullable(comment) || ';' as cc
                    from columns
                where comment IS NOT NULL
            ),
            settings as (
                select 'ALTER ' || obj.kind || ' ' || text('{0}.{1}') || ' SET (' ||
                        quote_ident(option_name)||'='||quote_nullable(option_value) ||');' as ss
                    from pg_options_to_table((select reloptions from pg_class where oid = '{0}.{1}'::regclass))
                    join obj on (true)
            ),
            constraints as (
                SELECT nc.nspname AS namespace,
                    r.relname AS class_name,
                    c.conname AS constraint_name,
                    case c.contype
                        when 'c'::"char" then 'CHECK'::text
                        when 'f'::"char" then 'FOREIGN KEY'::text
                        when 'p'::"char" then 'PRIMARY KEY'::text
                        when 'u'::"char" then 'UNIQUE'::text
                        when 't'::"char" then 'TRIGGER'::text
                        when 'x'::"char" then 'EXCLUDE'::text
                        else c.contype::text
                    end AS constraint_type,
                    pg_get_constraintdef(c.oid,true) AS constraint_definition,
                    c.condeferrable AS is_deferrable,
                    c.condeferred  AS initially_deferred,
                    r.oid as regclass, c.oid AS sysid
                FROM pg_namespace nc, pg_namespace nr, pg_constraint c, pg_class r
                WHERE nc.oid = c.connamespace AND nr.oid = r.relnamespace AND c.conrelid = r.oid
                AND coalesce(r.oid='{0}.{1}'::regclass,true)
            ),
            indexes as (
                SELECT DISTINCT
                    c.oid AS oid,
                    n.nspname::text AS namespace,
                    c.relname::text AS class,
                    i.relname::text AS name,
                    NULL::text AS tablespace,
                    CASE d.refclassid
                        WHEN 'pg_constraint'::regclass
                        THEN 'ALTER TABLE ' || text(c.oid::regclass)
                                || ' ADD CONSTRAINT ' || quote_ident(cc.conname)
                                || ' ' || pg_get_constraintdef(cc.oid)
                        ELSE pg_get_indexdef(i.oid)
                    END AS indexdef,
                    cc.conname::text AS constraint_name
                FROM pg_index x
                JOIN pg_class c ON c.oid = x.indrelid
                JOIN pg_namespace n ON n.oid = c.relnamespace
                JOIN pg_class i ON i.oid = x.indexrelid
                JOIN pg_depend d ON d.objid = x.indexrelid
                LEFT JOIN pg_constraint cc ON cc.oid = d.refobjid
                WHERE c.relkind in ('r','p','m') AND i.relkind in ('i'::"char", 'I'::"char")
                AND coalesce(c.oid = '{0}.{1}'::regclass,true)
                AND NOT x.indisprimary
                AND NOT x.indisexclusion
            ),
            triggers as (
                SELECT
                    CASE t.tgisinternal
                        WHEN true THEN 'CONSTRAINT'::text
                        ELSE NULL::text
                    END AS is_constraint, t.tgname::text AS trigger_name,
                    CASE (t.tgtype::integer & 64) <> 0
                        WHEN true THEN 'INSTEAD'::text
                        ELSE CASE t.tgtype::integer & 2
                            WHEN 2 THEN 'BEFORE'::text
                            WHEN 0 THEN 'AFTER'::text
                            ELSE NULL::text
                        END
                    END AS action_order,
                    array_to_string(array[
                        case when (t.tgtype::integer &  4) <> 0 then 'INSERT'   end,
                        case when (t.tgtype::integer &  8) <> 0 then 'DELETE'   end,
                        case when (t.tgtype::integer & 16) <> 0 then 'UPDATE'   end,
                        case when (t.tgtype::integer & 32) <> 0 then 'TRUNCATE' end
                    ],' OR ') AS event_manipulation,
                    c.oid::regclass::text AS event_object_sql_identifier,
                    p.oid::regprocedure::text AS action_statement,
                    CASE t.tgtype::integer & 1
                        WHEN 1 THEN 'ROW'::text
                        ELSE 'STATEMENT'::text
                    END AS action_orientation,
                    pg_get_triggerdef(t.oid,true) as trigger_definition,
                    c.oid::regclass AS regclass,
                    p.oid::regprocedure AS regprocedure,
                    s.nspname::text AS event_object_schema,
                    c.relname::text AS event_object_table,
                    (quote_ident(t.tgname::text) || ' ON ') || c.oid::regclass::text AS sql_identifier
                FROM pg_trigger t
                LEFT JOIN pg_class c ON c.oid = t.tgrelid
                LEFT JOIN pg_namespace s ON s.oid = c.relnamespace
                LEFT JOIN pg_proc p ON p.oid = t.tgfoid
                LEFT JOIN pg_namespace s1 ON s1.oid = p.pronamespace
                WHERE coalesce(c.oid='{0}.{1}'::regclass,true)
            ),
            rules as (
                SELECT n.nspname::text AS namespace,
                    c.relname::text AS class_name,
                    r.rulename::text AS rule_name,
                    CASE
                        WHEN r.ev_type = '1'::"char" THEN 'SELECT'::text
                        WHEN r.ev_type = '2'::"char" THEN 'UPDATE'::text
                        WHEN r.ev_type = '3'::"char" THEN 'INSERT'::text
                        WHEN r.ev_type = '4'::"char" THEN 'DELETE'::text
                        ELSE 'UNKNOWN'::text
                    END AS rule_event,
                    r.is_instead,
                    pg_get_ruledef(r.oid, true) AS rule_definition,
                    c.oid::regclass AS regclass
                FROM pg_rewrite r
                JOIN pg_class c ON c.oid = r.ev_class
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE coalesce(c.oid='{0}.{1}'::regclass,true)
                AND NOT (r.ev_type = '1'::"char" AND r.rulename = '_RETURN'::name)
                ORDER BY r.oid
            ),
            createview as (
                select
                    'CREATE '||
                    case relkind
                    when 'v' THEN 'OR REPLACE VIEW '
                    when 'm' THEN 'MATERIALIZED VIEW '
                    end || (oid::regclass::text) || E' AS\n'||
                    pg_catalog.pg_get_viewdef(oid,true)||E'\n'||
                    (CASE WHEN obj_description('{0}.{1}'::regclass, 'pg_class') IS NOT NULL
                        THEN (CASE relkind WHEN 'v'
                                            THEN format(
                                                    E'\n\nCOMMENT ON VIEW %s IS %s;',
                                                    '{0}.{1}'::regclass,
                                                    quote_literal(obj_description('{0}.{1}'::regclass, 'pg_class'))
                                                )
                                            WHEN 'm'
                                            THEN format(
                                                    E'\n\nCOMMENT ON MATERIALIZED VIEW %s IS %s;',
                                                    '{0}.{1}'::regclass,
                                                    quote_literal(obj_description('{0}.{1}'::regclass, 'pg_class'))
                                                )
                                            ELSE ''
                                END)
                        ELSE ''
                    END) as text
                    FROM pg_class t
                    WHERE oid = '{0}.{1}'::regclass
                    AND relkind in ('v','m')
            ),
            createtable as (
                select
                    'CREATE '||
                    case relpersistence
                    when 'u' then 'UNLOGGED '
                    when 't' then 'TEMPORARY '
                    else ''
                    end
                    || case obj.kind when 'PARTITIONED TABLE' then 'TABLE' else obj.kind end || ' ' || obj.sql_identifier
                    || case obj.kind when 'TYPE' then ' AS' else '' end
                    || case when c.relispartition
                    then
                        E'\n' ||
                        (SELECT
                            coalesce(' PARTITION OF ' || string_agg(i.inhparent::regclass::text,', '), '')
                            FROM pg_inherits i WHERE i.inhrelid = '{0}.{1}'::regclass) ||
                        E'\n'||
                        coalesce(' '||(
                            pg_get_expr(c.relpartbound, c.oid, true)
                        ),'')
                    else
                        E' (\n'||
                        coalesce(''||(
                            SELECT coalesce(string_agg('    '||definition,E',\n'),'')
                            FROM columns WHERE is_local
                        )||E'\n','')||')'
                        ||
                        (SELECT
                        coalesce(' INHERITS(' || string_agg(i.inhparent::regclass::text,', ') || ')', '')
                            FROM pg_inherits i WHERE i.inhrelid = '{0}.{1}'::regclass)
                    end
                    ||
                    case when c.relkind = 'p'
                    then E'\n' || ' PARTITION BY ' || pg_get_partkeydef('{0}.{1}'::regclass)
                    else '' end
                    ||
                    coalesce(
                    E'\nSERVER '||quote_ident(fs.srvname)
                    ,'')
                    ||
                    coalesce(
                    E'\nOPTIONS (\n'||
                    (select string_agg(
                                '    '||quote_ident(option_name)||' '||quote_nullable(option_value),
                                E',\n')
                        from pg_options_to_table(ft.ftoptions))||E'\n)'
                    ,'')
                    ||
                    E';\n'||
                    (CASE WHEN obj_description('{0}.{1}'::regclass, 'pg_class') IS NOT NULL
                        THEN (CASE relkind WHEN 'r'
                                            THEN format(
                                                    E'\n\nCOMMENT ON TABLE %s IS %s;',
                                                    '{0}.{1}'::regclass,
                                                    quote_literal(obj_description('{0}.{1}'::regclass, 'pg_class'))
                                                )
                                            WHEN 'p'
                                            THEN format(
                                                    E'\n\nCOMMENT ON TABLE %s IS %s;',
                                                    '{0}.{1}'::regclass,
                                                    quote_literal(obj_description('{0}.{1}'::regclass, 'pg_class'))
                                                )
                                            WHEN 'f'
                                            THEN format(
                                                    E'\n\nCOMMENT ON FOREIGN TABLE %s IS %s;',
                                                    '{0}.{1}'::regclass,
                                                    quote_literal(obj_description('{0}.{1}'::regclass, 'pg_class'))
                                                )
                                            ELSE ''
                                END)
                        ELSE ''
                    END) as text
                    FROM pg_class c JOIN obj ON (true)
                    LEFT JOIN pg_foreign_table  ft ON (c.oid = ft.ftrelid)
                    LEFT JOIN pg_foreign_server fs ON (ft.ftserver = fs.oid)
                    WHERE c.oid = '{0}.{1}'::regclass
                -- AND relkind in ('r','c')
            ),
            createsequence as (
                SELECT 'CREATE SEQUENCE '||(c.oid::regclass::text) || E';\n'
                        ||'ALTER SEQUENCE '||(c.oid::regclass::text)
                        ||E'\n INCREMENT BY '||sp.increment
                        ||E'\n MINVALUE '||sp.minimum_value
                        ||E'\n MAXVALUE '||sp.maximum_value
                        ||E'\n START WITH '||sp.start_value
                        ||E'\n '|| CASE cycle_option WHEN true THEN 'CYCLE' ELSE 'NO CYCLE' END
                        ||E';\n'||
                        (CASE WHEN obj_description('{0}.{1}'::regclass, 'pg_class') IS NOT NULL
                                THEN (CASE relkind WHEN 'S'
                                                THEN format(
                                                            E'\n\nCOMMENT ON SEQUENCE %s IS %s;',
                                                            '{0}.{1}'::regclass,
                                                            quote_literal(obj_description('{0}.{1}'::regclass, 'pg_class'))
                                                        )
                                                ELSE ''
                                    END)
                                ELSE ''
                        END) as text
                FROM pg_class c,
                LATERAL pg_sequence_parameters(c.oid) sp (start_value, minimum_value, maximum_value, increment, cycle_option)
                WHERE c.oid = '{0}.{1}'::regclass
                    AND c.relkind = 'S'
            ),
            createindex as (
                with ii as (
                    SELECT DISTINCT CASE d.refclassid
                            WHEN 'pg_constraint'::regclass
                            THEN 'ALTER TABLE ' || text(c.oid::regclass)
                                    || ' ADD CONSTRAINT ' || quote_ident(cc.conname)
                                    || ' ' || pg_get_constraintdef(cc.oid)
                            ELSE pg_get_indexdef(i.oid) ||
                                    (CASE WHEN obj_description('{0}.{1}'::regclass, 'pg_class') IS NOT NULL
                                        THEN format(
                                                E'\n\nCOMMENT ON INDEX %s IS %s;',
                                                '{0}.{1}'::regclass,
                                                quote_literal(obj_description('{0}.{1}'::regclass, 'pg_class'))
                                            )
                                        ELSE ''
                                    END)
                        END AS indexdef
                    FROM pg_index x
                    JOIN pg_class c ON c.oid = x.indrelid
                    JOIN pg_class i ON i.oid = x.indexrelid
                    JOIN pg_depend d ON d.objid = x.indexrelid
                    LEFT JOIN pg_constraint cc ON cc.oid = d.refobjid
                    WHERE c.relkind in ('r','p','m') AND i.relkind in ('i'::"char", 'I'::"char")
                    AND i.oid = '{0}.{1}'::regclass
                )
                    SELECT indexdef || E';\n' as text
                    FROM ii
            ),
            createclass as (
                select format(E'--\n-- Type: %s ; Name: %s; Owner: %s\n--\n\n', obj.kind,obj.name,obj.owner)
                ||
                    case
                    when obj.kind in ('VIEW','MATERIALIZED VIEW') then (select text from createview)
                    when obj.kind in ('TABLE','TYPE','FOREIGN TABLE','PARTITIONED TABLE') then (select text from createtable)
                    when obj.kind in ('SEQUENCE') then (select text from createsequence)
                    when obj.kind in ('INDEX', 'PARTITIONED INDEX') then (select text from createindex)
                    else '-- UNSUPPORTED CLASS: '||obj.kind
                    end
                    || E'\n' ||
                    coalesce((select string_agg(cc,E'\n')||E'\n' from comments),'')
                    ||
                    coalesce(E'\n'||(select string_agg(ss,E'\n')||E'\n' from settings),'')
                    || E'\n' as text
                from obj
            ),
            altertabledefaults as (
                select
                    coalesce(
                        string_agg(
                        'ALTER TABLE '||text('{0}.{1}')||
                            ' ALTER '||quote_ident(name)||
                            ' SET DEFAULT '||"default",
                        E';\n') || E';\n\n',
                    '') as text
                    from columns
                    where "default" is not null
                    and generated = ''
            ),
            createconstraints as (
                with cs as (
                    select
                    'ALTER TABLE ' || text(regclass(regclass)) ||
                    ' ADD CONSTRAINT ' || quote_ident(constraint_name) ||
                    E'\n  ' || constraint_definition as sql
                    from constraints
                    order by constraint_type desc, sysid
                    )
                    select coalesce(string_agg(sql,E';\n') || E';\n\n','') as text
                    from cs
            ),
            createindexes as (
                with ii as (select * from indexes order by name)
                    SELECT coalesce(string_agg(indexdef||E';\n','') || E'\n' , '') as text
                    FROM ii
                    WHERE constraint_name is null
            ),
            createtriggers as (
                with tg as (
                    select trigger_definition as sql
                    from triggers where is_constraint is null
                    order by trigger_name
                    -- per SQL triggers get called in order created vs name as in PostgreSQL
                    )
                    select coalesce(string_agg(sql,E';\n')||E';\n\n','') as text
                    from tg
            ),
            createrules as (
                select coalesce(string_agg(rule_definition,E'\n')||E'\n\n','') as text
                from rules
                where regclass = '{0}.{1}'::regclass
                    and rule_definition is not null
            ),
            alterowner as (
                select
                    case
                        when obj.kind in ('INDEX', 'PARTITIONED INDEX') then ''
                        when obj.kind = 'PARTITIONED TABLE'
                        then 'ALTER TABLE '||sql_identifier||
                            ' OWNER TO '||quote_ident(owner)||E';\n\n'
                        else 'ALTER '||sql_kind||' '||sql_identifier||
                            ' OWNER TO '||quote_ident(owner)||E';\n\n'
                    end as text
                    from obj
            ),
            privileges as (
                SELECT (u_grantor.rolname)::information_schema.sql_identifier AS grantor,
                        (grantee.rolname)::information_schema.sql_identifier AS grantee,
                        (current_database())::information_schema.sql_identifier AS table_catalog,
                        (nc.nspname)::information_schema.sql_identifier AS table_schema,
                        (c.relname)::information_schema.sql_identifier AS table_name,
                        (c.prtype)::information_schema.character_data AS privilege_type,
                        (
                            CASE
                                WHEN (pg_has_role(grantee.oid, c.relowner, 'USAGE'::text) OR c.grantable) THEN 'YES'::text
                                ELSE 'NO'::text
                            END)::information_schema.yes_or_no AS is_grantable,
                        (
                            CASE
                                WHEN (c.prtype = 'SELECT'::text) THEN 'YES'::text
                                ELSE 'NO'::text
                            END)::information_schema.yes_or_no AS with_hierarchy
                        FROM ( SELECT pg_class.oid,
                                        pg_class.relname,
                                        pg_class.relnamespace,
                                        pg_class.relkind,
                                        pg_class.relowner,
                                        (aclexplode(COALESCE(pg_class.relacl, acldefault('r', pg_class.relowner)))).grantor AS grantor,
                                        (aclexplode(COALESCE(pg_class.relacl, acldefault('r', pg_class.relowner)))).grantee AS grantee,
                                        (aclexplode(COALESCE(pg_class.relacl, acldefault('r', pg_class.relowner)))).privilege_type AS privilege_type,
                                        (aclexplode(COALESCE(pg_class.relacl, acldefault('r', pg_class.relowner)))).is_grantable AS is_grantable
                                FROM pg_class
                                WHERE pg_class.relkind <> 'S'
                                UNION
                                SELECT pg_class.oid,
                                        pg_class.relname,
                                        pg_class.relnamespace,
                                        pg_class.relkind,
                                        pg_class.relowner,
                                        (aclexplode(COALESCE(pg_class.relacl, acldefault('S', pg_class.relowner)))).grantor AS grantor,
                                        (aclexplode(COALESCE(pg_class.relacl, acldefault('S', pg_class.relowner)))).grantee AS grantee,
                                        (aclexplode(COALESCE(pg_class.relacl, acldefault('S', pg_class.relowner)))).privilege_type AS privilege_type,
                                        (aclexplode(COALESCE(pg_class.relacl, acldefault('S', pg_class.relowner)))).is_grantable AS is_grantable
                                FROM pg_class
                                WHERE pg_class.relkind = 'S') c(oid, relname, relnamespace, relkind, relowner, grantor, grantee, prtype, grantable),
                        pg_namespace nc,
                        pg_roles u_grantor,
                        ( SELECT pg_roles.oid,
                                pg_roles.rolname
                                FROM pg_roles
                            UNION ALL
                                SELECT (0)::oid AS oid,
                                'PUBLIC'::name) grantee(oid, rolname)
                        WHERE ((c.relnamespace = nc.oid) AND (c.grantee = grantee.oid) AND (c.grantor = u_grantor.oid)
                        AND (c.prtype = ANY (ARRAY['INSERT'::text, 'SELECT'::text, 'UPDATE'::text, 'DELETE'::text, 'TRUNCATE'::text, 'REFERENCES'::text, 'TRIGGER'::text]))
                        AND (pg_has_role(u_grantor.oid, 'USAGE'::text) OR pg_has_role(grantee.oid, 'USAGE'::text) OR (grantee.rolname = 'PUBLIC'::name)))
            ),
            grants as (
                select
                    coalesce(
                    string_agg(format(
                        E'GRANT %s ON %s TO %s%s;\n',
                        privilege_type,
                        '{0}.{1}',
                        case grantee
                            when 'PUBLIC' then 'PUBLIC'
                            else quote_ident(grantee)
                        end,
                        case is_grantable
                            when 'YES' then ' WITH GRANT OPTION'
                            else ''
                        end), ''),
                    '') as text
                    FROM privileges g
                    join obj on (true)
                    WHERE table_schema=obj.namespace
                    AND table_name=obj.name
                    AND grantee<>obj.owner
            ),
            columnsprivileges as (
                SELECT r.rolname AS grantee,
                        c.name AS column_name,
                        c.privilege_type
                FROM (
                    SELECT name,
                            (aclexplode(attacl)).grantee AS grantee,
                            (aclexplode(attacl)).privilege_type AS privilege_type
                    FROM columns
                ) c
                INNER JOIN pg_roles r
                        ON c.grantee = r.oid
            ),
            columnsgrants as (
                SELECT coalesce(
                            string_agg(
                                format(
                                    E'GRANT %s(%s) ON %s TO %s;\n',
                                    privilege_type,
                                    column_name,
                                    '{0}.{1}',
                                    quote_ident(grantee)
                                ),
                                ''
                            ),
                            ''
                        ) AS text
                    FROM columnsprivileges
            )
            select (select text from createclass) ||
                    (select text from altertabledefaults) ||
                    (select text from createconstraints) ||
                    (select text from createindexes) ||
                    (select text from createtriggers) ||
                    (select text from createrules) ||
                    (select text from alterowner) ||
                    (select text from grants) ||
                    (SELECT text FROM columnsgrants)
        '''.format(schema, class_name))
    
    @lock_required
    def GetDDLTrigger(self, trigger, table, schema):
        return self.connection.ExecuteScalar('''
            select 'CREATE TRIGGER ' || x.trigger_name || chr(10) ||
                   '  ' || x.action_timing || ' ' || x.event_manipulation || (CASE WHEN x.columns IS NOT NULL THEN ' OF ' || x.columns ELSE '' END) || chr(10) ||
                   '  ON {0}.{1}' || chr(10) ||
                   '  FOR EACH ' || x.action_orientation || chr(10) ||
                   (case when length(coalesce(x.action_condition, '')) > 0 then '  WHEN ( ' || x.action_condition || ') ' || chr(10) else '' end) ||
                   '  ' || x.action_statement ||
                   (CASE WHEN obj_description(x.oid, 'pg_trigger') IS NOT NULL
                         THEN format(
                                 E'\n\nCOMMENT ON TRIGGER %s ON %s IS %s;',
                                 quote_ident(x.trigger_name),
                                 quote_ident('{0}.{1}'::regclass::text),
                                 quote_literal(obj_description(x.oid, 'pg_trigger'))
                             )
                         ELSE ''
                    END) as definition
            from (
            select distinct quote_ident(t.trigger_name) as trigger_name,
                   t.action_timing,
                   e.event as event_manipulation,
                   t.action_orientation,
                   t.action_condition,
                   t.action_statement,
                   t2.oid,
                   tuc.columns
            from information_schema.triggers t
            inner join (
            select array_to_string(array(
            select event_manipulation::text
            from information_schema.triggers
            where quote_ident(event_object_schema) = '{0}'
              and quote_ident(event_object_table) = '{1}'
              and quote_ident(trigger_name) = '{2}'
            ), ' OR ') as event
            ) e
            on 1 = 1
            INNER JOIN (
                select oid
                FROM pg_trigger
                WHERE quote_ident(tgname) = '{2}'
                  AND tgrelid = '{0}.{1}'::regclass
            ) t2
                    ON 1 = 1
            LEFT JOIN (
                SELECT string_agg(
                           event_object_column,
                           ', '
                       ) AS columns
                FROM information_schema.triggered_update_columns
                WHERE quote_ident(event_object_schema) = '{0}'
                  AND quote_ident(event_object_table) = '{1}'
                  AND quote_ident(trigger_name) = '{2}'
            ) tuc
                   ON 1 = 1
            where quote_ident(t.event_object_schema) = '{0}'
              and quote_ident(t.event_object_table) = '{1}'
              and quote_ident(t.trigger_name) = '{2}'
            ) x
        '''.format(schema, table, trigger))
    
    @lock_required
    def GetDDLEventTrigger(self, trigger):
        return self.connection.ExecuteScalar('''
            select format(E'CREATE EVENT TRIGGER %s\n  ON %s%s\n  EXECUTE PROCEDURE %s;\n\nALTER EVENT TRIGGER %s OWNER TO %s;\n%s',
                     quote_ident(t.evtname),
                     t.evtevent,
                     (case when t.evttags is not null
                           then E'\n  WHEN TAG IN ( '' || array_to_string(t.evttags, '', '') || '' )'
                           else ''
                      end),
                     quote_ident(np.nspname) || '.' || quote_ident(p.proname) || '()',
                     quote_ident(t.evtname),
                     r.rolname,
                     (CASE WHEN obj_description(t.oid, 'pg_event_trigger') IS NOT NULL
                           THEN format(
                                    E'\nCOMMENT ON EVENT TRIGGER %s IS %s;',
                                    quote_ident(t.evtname),
                                    quote_literal(obj_description(t.oid, 'pg_event_trigger'))
                                )
                           ELSE ''
                      END)
                   )
            from pg_event_trigger t
            inner join pg_proc p
            on p.oid = t.evtfoid
            inner join pg_namespace np
            on np.oid = p.pronamespace
            inner join pg_roles r
            on r.oid = t.evtowner
            where quote_ident(t.evtname) = '{0}'
        '''.format(trigger))
    
    @lock_required
    def GetDDLFunction(self, function_name):
        return self.connection.ExecuteScalar('''
            with obj as (
                SELECT p.oid,
                        p.proname AS name,
                        n.nspname AS namespace,
                        pg_get_userbyid(p.proowner) AS owner,
                        '{0}'::text AS sql_identifier
                FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
                WHERE p.prokind = 'f' AND p.oid = '{0}'::text::regprocedure
            ),
            createfunction as (
                select substring(body from 1 for length(body)-1) || E';\n\n' as text
                from (
                    select pg_get_functiondef(sql_identifier::regprocedure) as body
                    from obj
                ) x
            ),
            alterowner as (
                select
                    'ALTER FUNCTION '||sql_identifier||
                            ' OWNER TO '||quote_ident(owner)||E';\n\n' as text
                    from obj
            ),
            privileges as (
            select (u_grantor.rolname)::information_schema.sql_identifier as grantor,
                    (grantee.rolname)::information_schema.sql_identifier as grantee,
                    (p.privilege_type)::information_schema.character_data as privilege_type,
                    (case when (pg_has_role(grantee.oid, p.proowner, 'USAGE'::text) or p.is_grantable)
                            then 'YES'::text
                            else 'NO'::text
                    end)::information_schema.yes_or_no AS is_grantable
            from (
                select p.pronamespace,
                        p.proowner,
                        (aclexplode(COALESCE(p.proacl, acldefault('f', p.proowner)))).grantor as grantor,
                        (aclexplode(COALESCE(p.proacl, acldefault('f', p.proowner)))).grantee as grantee,
                        (aclexplode(COALESCE(p.proacl, acldefault('f', p.proowner)))).privilege_type as privilege_type,
                        (aclexplode(COALESCE(p.proacl, acldefault('f', p.proowner)))).is_grantable as is_grantable
                from pg_proc p
                where p.prokind = 'f'
                    and p.oid = '{0}'::regprocedure
            ) p
            inner join pg_namespace n
            on n.oid = p.pronamespace
            inner join pg_roles u_grantor
            on u_grantor.oid = p.grantor
            inner join (
                select r.oid,
                        r.rolname
                from pg_roles r
                union all
                select (0)::oid AS oid,
                        'PUBLIC'::name
            ) grantee
            on grantee.oid = p.grantee
            ),
            grants as (
            select coalesce(
                    string_agg(format(
                    E'GRANT %s ON FUNCTION {0} TO %s%s;\n',
                    privilege_type,
                    case grantee
                        when 'PUBLIC' then 'PUBLIC'
                        else quote_ident(grantee)
                    end,
                    case is_grantable
                        when 'YES' then ' WITH GRANT OPTION'
                        else ''
                    end), ''),
                    '') as text
            from privileges
            ),
            comments AS (
                SELECT coalesce(obj_description('{0}'::regprocedure, 'pg_proc'), '') AS description
            ),
            comment_on AS (
                SELECT (CASE WHEN description <> ''
                                THEN format(
                                        E'\n\nCOMMENT ON FUNCTION %s IS %s;',
                                        '{0}'::regprocedure,
                                        quote_literal(description)
                                    )
                                ELSE ''
                        END) AS text
                FROM comments
            )
            select (select text from createfunction) ||
                    (select text from alterowner) ||
                    (select text from grants) ||
                    (SELECT text FROM comment_on)
    '''.format(function_name))
    
    @lock_required
    def GetDDLProcedure(self, procedure):
        return self.connection.ExecuteScalar('''
            with obj as (
                SELECT p.oid,
                       p.proname AS name,
                       n.nspname AS namespace,
                       pg_get_userbyid(p.proowner) AS owner,
                       '{0}'::text AS sql_identifier
                FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
                WHERE p.prokind = 'p' AND p.oid = '{0}'::text::regprocedure
            ),
            createfunction as (
                select substring(body from 1 for length(body)-1) || E';\n\n' as text
                from (
                    select pg_get_functiondef(sql_identifier::regprocedure) as body
                    from obj
                ) x
            ),
            alterowner as (
                select
                   'ALTER PROCEDURE '||sql_identifier||
                          ' OWNER TO '||quote_ident(owner)||E';\n\n' as text
                  from obj
            ),
            privileges as (
            select (u_grantor.rolname)::information_schema.sql_identifier as grantor,
                   (grantee.rolname)::information_schema.sql_identifier as grantee,
                   (p.privilege_type)::information_schema.character_data as privilege_type,
                   (case when (pg_has_role(grantee.oid, p.proowner, 'USAGE'::text) or p.is_grantable)
                         then 'YES'::text
                         else 'NO'::text
                    end)::information_schema.yes_or_no AS is_grantable
            from (
                select p.pronamespace,
                       p.proowner,
                       (aclexplode(COALESCE(p.proacl, acldefault('f', p.proowner)))).grantor as grantor,
                       (aclexplode(COALESCE(p.proacl, acldefault('f', p.proowner)))).grantee as grantee,
                       (aclexplode(COALESCE(p.proacl, acldefault('f', p.proowner)))).privilege_type as privilege_type,
                       (aclexplode(COALESCE(p.proacl, acldefault('f', p.proowner)))).is_grantable as is_grantable
                from pg_proc p
                where p.prokind = 'p'
                  and p.oid = '{0}'::regprocedure
            ) p
            inner join pg_namespace n
            on n.oid = p.pronamespace
            inner join pg_roles u_grantor
            on u_grantor.oid = p.grantor
            inner join (
                select r.oid,
                       r.rolname
                from pg_roles r
                union all
                select (0)::oid AS oid,
                       'PUBLIC'::name
            ) grantee
            on grantee.oid = p.grantee
            ),
            grants as (
            select coalesce(
                    string_agg(format(
                	E'GRANT %s ON FUNCTION {0} TO %s%s;\n',
                    privilege_type,
                    case grantee
                      when 'PUBLIC' then 'PUBLIC'
                      else quote_ident(grantee)
                    end,
                	case is_grantable
                      when 'YES' then ' WITH GRANT OPTION'
                      else ''
                    end), ''),
                   '') as text
            from privileges
            ),
            comments AS (
                SELECT coalesce(obj_description('{0}'::regprocedure, 'pg_proc'), '') AS description
            ),
            comment_on AS (
                SELECT (CASE WHEN description <> ''
                             THEN format(
                                      E'\n\nCOMMENT ON PROCEDURE %s IS %s;',
                                      '{0}'::regprocedure,
                                      quote_literal(description)
                                  )
                             ELSE ''
                        END) AS text
                FROM comments
            )
            select (select text from createfunction) ||
                   (select text from alterowner) ||
                   (select text from grants) ||
                   (SELECT text FROM comment_on)
        '''.format(procedure))
    
    @lock_required
    def GetDDLConstraint(self, schema, table, constraint_name):
        return self.connection.ExecuteScalar('''
            with cs as (
              select
               'ALTER TABLE ' || text(regclass(c.conrelid)) ||
               ' ADD CONSTRAINT ' || quote_ident(c.conname) ||
               E'\n  ' || pg_get_constraintdef(c.oid, true) as sql,
               c.oid,
               c.conname,
               c.conrelid
                from pg_constraint c
               join pg_class t
               on t.oid = c.conrelid
               join pg_namespace n
               on t.relnamespace = n.oid
               where quote_ident(n.nspname) = '{0}'
                 and quote_ident(t.relname) = '{1}'
                 and quote_ident(c.conname) = '{2}'
            ),
            comments AS (
                SELECT format(
                           E'\n\nCOMMENT ON CONSTRAINT %s ON %s is %s;',
                           conname,
                           conrelid::regclass,
                           quote_literal(x.description)
                       ) AS sql
                FROM (
                    SELECT oid,
                           conname,
                           conrelid,
                           obj_description(oid, 'pg_constraint') AS description
                    FROM cs
                ) x
                WHERE x.description IS NOT NULL
            )
            select format(
                       E'%s%s',
                       coalesce(string_agg(cs.sql,E';\n') || E';\n\n',''),
                       coalesce(c.sql, '')
                   ) as text
            from cs cs
            LEFT JOIN comments c
                   ON 1 = 1
            GROUP BY cs.sql,
                     c.sql
        '''.format(schema, table, constraint_name))
    
    @lock_required
    def GetDDLUserMapping(self, server, role_name):
        if role_name == 'PUBLIC':
            return self.connection.ExecuteScalar('''
                select format(E'CREATE USER MAPPING FOR PUBLIC\n  SERVER %s%s;\n',
                         quote_ident(s.srvname),
                         (select (case when s is not null and s <> ''
                                       then format(E'\n  OPTIONS (%s)', s)
                                       else ''
                                  end)
                          from (
                          select array_to_string(array(
                          select format('%s %s', a[1], quote_literal(a[2]))
                          from (
                          select string_to_array(unnest(u.umoptions), '=') as a
                          from pg_user_mapping u
                          inner join pg_foreign_server s
                          on s.oid = u.umserver
                          where u.umuser = 0
                            and quote_ident(s.srvname) = '{0}'
                          ) x
                          ), ', ') as s) x))
                from pg_user_mapping u
                inner join pg_foreign_server s
                on s.oid = u.umserver
                where u.umuser = 0
                  and quote_ident(s.srvname) = '{0}'
            '''.format(server))
        else:
            return self.connection.ExecuteScalar('''
                select format(E'CREATE USER MAPPING FOR %s\n  SERVER %s%s;\n',
                         quote_ident(r.rolname),
                         quote_ident(s.srvname),
                         (select (case when s is not null and s <> ''
                                       then format(E'\n  OPTIONS (%s)', s)
                                       else ''
                                  end)
                          from (
                          select array_to_string(array(
                          select format('%s %s', a[1], quote_literal(a[2]))
                          from (
                          select string_to_array(unnest(u.umoptions), '=') as a
                          from pg_user_mapping u
                          inner join pg_foreign_server s
                          on s.oid = u.umserver
                          inner join pg_roles r
                          on r.oid = u.umuser
                          where quote_ident(s.srvname) = '{0}'
                            and quote_ident(r.rolname) = '{1}'
                          ) x
                          ), ', ') as s) x))
                from pg_user_mapping u
                inner join pg_foreign_server s
                on s.oid = u.umserver
                inner join pg_roles r
                on r.oid = u.umuser
                where quote_ident(s.srvname) = '{0}'
                  and quote_ident(r.rolname) = '{1}'
            '''.format(server, role_name))
    
    @lock_required
    def GetDDLForeignServer(self, server_name):
        return self.connection.ExecuteScalar('''
            WITH privileges AS (
                SELECT (u_grantor.rolname)::information_schema.sql_identifier AS grantor,
                       (grantee.rolname)::information_schema.sql_identifier AS grantee,
                       (current_database())::information_schema.sql_identifier AS srv_catalog,
                       (c.srvname)::information_schema.sql_identifier AS srv_name,
                       (c.prtype)::information_schema.character_data AS privilege_type,
                       (
                           CASE
                               WHEN (pg_has_role(grantee.oid, c.srvowner, 'USAGE'::text) OR c.grantable) THEN 'YES'::text
                               ELSE 'NO'::text
                           END)::information_schema.yes_or_no AS is_grantable,
                       (
                           CASE
                               WHEN (c.prtype = 'SELECT'::text) THEN 'YES'::text
                               ELSE 'NO'::text
                           END)::information_schema.yes_or_no AS with_hierarchy
                FROM ( SELECT s.oid,
                              s.srvname,
                              s.srvowner,
                              (aclexplode(COALESCE(s.srvacl, acldefault('r', s.srvowner)))).grantor AS grantor,
                              (aclexplode(COALESCE(s.srvacl, acldefault('r', s.srvowner)))).grantee AS grantee,
                              (aclexplode(COALESCE(s.srvacl, acldefault('r', s.srvowner)))).privilege_type AS privilege_type,
                              (aclexplode(COALESCE(s.srvacl, acldefault('r', s.srvowner)))).is_grantable AS is_grantable
                      FROM pg_foreign_server s
                      WHERE s.srvname = '{0}') c(oid, srvname, srvowner, grantor, grantee, prtype, grantable),
                     pg_roles u_grantor,
                     ( SELECT pg_roles.oid,
                              pg_roles.rolname
                       FROM pg_roles
                       UNION ALL
                       SELECT (0)::oid AS oid,
                              'PUBLIC'::name) grantee(oid, rolname)
                WHERE (c.grantee = grantee.oid) AND (c.grantor = u_grantor.oid)
                  AND (pg_has_role(u_grantor.oid, 'USAGE'::text) OR pg_has_role(grantee.oid, 'USAGE'::text) OR (grantee.rolname = 'PUBLIC'::name))
            ),
            grants as (
                SELECT
                  coalesce(
                   string_agg(format(
                   	E'GRANT %s ON %s TO %s%s;\n',
                       privilege_type,
                       'FOREIGN SERVER {0}',
                       case grantee
                         when 'PUBLIC' then 'PUBLIC'
                         else quote_ident(grantee)
                       end,
                	   case is_grantable
                         when 'YES' then ' WITH GRANT OPTION'
                         else ''
                       end), ''),
                    '') as text
                FROM privileges g
                INNER JOIN pg_foreign_server s
                ON s.srvname = g.srv_name
                INNER JOIN pg_roles r
                ON r.oid = s.srvowner
                WHERE g.grantee <> r.rolname
            )
            select format(E'CREATE SERVER %s%s%s\n  FOREIGN DATA WRAPPER %s%s;\n\nALTER SERVER %s OWNER TO %s;\n\n%s%s',
                     quote_ident(s.srvname),
                     (case when s.srvtype is not null
                           then format(E'\n  TYPE %s\n', quote_literal(s.srvtype))
                           else ''
                      end),
                     (case when s.srvversion is not null
                           then format(E'\n  VERSION %s\n', quote_literal(s.srvversion))
                           else ''
                      end),
                     w.fdwname,
                     (case when (select array_to_string(array(
                                 select format('%s %s', a[1], quote_literal(a[2]))
                                 from (
                                 select string_to_array(unnest(s.srvoptions), '=') as a
                                 from pg_foreign_server s
                                 inner join pg_foreign_data_wrapper w
                                 on w.oid = s.srvfdw
                                 inner join pg_roles r
                                 on r.oid = s.srvowner
                                 where quote_ident(s.srvname) = '{0}'
                                 ) x
                                 ), ', ')) != ''
                           then format('\n  OPTIONS ( %s )',
                                (select array_to_string(array(
                                 select format('%s %s', a[1], quote_literal(a[2]))
                                 from (
                                 select string_to_array(unnest(s.srvoptions), '=') as a
                                 from pg_foreign_server s
                                 inner join pg_foreign_data_wrapper w
                                 on w.oid = s.srvfdw
                                 inner join pg_roles r
                                 on r.oid = s.srvowner
                                 where quote_ident(s.srvname) = '{0}'
                                 ) x
                                 ), ', ')))
                           else ''
                      end),
                     quote_ident(s.srvname),
                     quote_ident(r.rolname),
                     g.text,
                     (CASE WHEN obj_description(s.oid, 'pg_foreign_server') IS NOT NULL
                           THEN format(
                                   E'\nCOMMENT ON SERVER %s IS %s;',
                                   quote_ident(s.srvname),
                                   quote_literal(obj_description(s.oid, 'pg_foreign_server'))
                               )
                           ELSE ''
                      END)
                   )
            from pg_foreign_server s
            inner join pg_foreign_data_wrapper w
            on w.oid = s.srvfdw
            inner join pg_roles r
            on r.oid = s.srvowner
            inner join grants g on 1=1
            where quote_ident(s.srvname) = '{0}'
        '''.format(server_name))
    
    @lock_required
    def GetDDLForeignDataWrapper(self, fdw):
        return self.connection.ExecuteScalar('''
            WITH privileges AS (
                SELECT (u_grantor.rolname)::information_schema.sql_identifier AS grantor,
                       (grantee.rolname)::information_schema.sql_identifier AS grantee,
                       (current_database())::information_schema.sql_identifier AS fdw_catalog,
                       (c.fdwname)::information_schema.sql_identifier AS fdw_name,
                       (c.prtype)::information_schema.character_data AS privilege_type,
                       (
                           CASE
                               WHEN (pg_has_role(grantee.oid, c.fdwowner, 'USAGE'::text) OR c.grantable) THEN 'YES'::text
                               ELSE 'NO'::text
                           END)::information_schema.yes_or_no AS is_grantable,
                       (
                           CASE
                               WHEN (c.prtype = 'SELECT'::text) THEN 'YES'::text
                               ELSE 'NO'::text
                           END)::information_schema.yes_or_no AS with_hierarchy
                FROM ( SELECT w.oid,
                              w.fdwname,
                              w.fdwowner,
                              (aclexplode(COALESCE(w.fdwacl, acldefault('r', w.fdwowner)))).grantor AS grantor,
                              (aclexplode(COALESCE(w.fdwacl, acldefault('r', w.fdwowner)))).grantee AS grantee,
                              (aclexplode(COALESCE(w.fdwacl, acldefault('r', w.fdwowner)))).privilege_type AS privilege_type,
                              (aclexplode(COALESCE(w.fdwacl, acldefault('r', w.fdwowner)))).is_grantable AS is_grantable
                      FROM pg_foreign_data_wrapper w
                      WHERE w.fdwname = '{0}') c(oid, fdwname, fdwowner, grantor, grantee, prtype, grantable),
                     pg_roles u_grantor,
                     ( SELECT pg_roles.oid,
                              pg_roles.rolname
                       FROM pg_roles
                       UNION ALL
                       SELECT (0)::oid AS oid,
                              'PUBLIC'::name) grantee(oid, rolname)
                WHERE (c.grantee = grantee.oid) AND (c.grantor = u_grantor.oid)
                  AND (pg_has_role(u_grantor.oid, 'USAGE'::text) OR pg_has_role(grantee.oid, 'USAGE'::text) OR (grantee.rolname = 'PUBLIC'::name))
            ),
            grants as (
                SELECT
                  coalesce(
                   string_agg(format(
                   	E'GRANT %s ON %s TO %s%s;\n',
                       privilege_type,
                       'FOREIGN DATA WRAPPER {0}',
                       case grantee
                         when 'PUBLIC' then 'PUBLIC'
                         else quote_ident(grantee)
                       end,
                	   case is_grantable
                         when 'YES' then ' WITH GRANT OPTION'
                         else ''
                       end), ''),
                    '') as text
                FROM privileges g
                INNER JOIN pg_foreign_data_wrapper w
                ON w.fdwname = g.fdw_name
                INNER JOIN pg_roles r
                ON r.oid = w.fdwowner
                WHERE g.grantee <> r.rolname
            )
            select format(E'CREATE FOREIGN DATA WRAPPER %s%s%s%s;\n\nALTER FOREIGN DATA WRAPPER %s OWNER TO %s;\n\n%s%s',
                     w.fdwname,
                     (case when w.fdwhandler <> 0
                           then format(E'\n  HANDLER %s', quote_literal(h.proname))
                           else E'\n  NO HANDLER'
                      end),
                     (case when w.fdwvalidator <> 0
                           then format(E'\n  VALIDATOR %s', quote_literal(v.proname))
                           else E'\n  NO VALIDATOR'
                      end),
                     (case when (select array_to_string(array(
                                 select format('%s %s', a[1], quote_literal(a[2]))
                                 from (
                                 select string_to_array(unnest(w.fdwoptions), '=') as a
                                 from pg_foreign_data_wrapper w
                                 inner join pg_roles r
                                 on r.oid = w.fdwowner
                                 where w.fdwname = '{0}'
                                 ) x
                                 ), ', ')) <> ''::text
                           then format('\n  OPTIONS ( %s )',
                                (select array_to_string(array(
                                 select format('%s %s', a[1], quote_literal(a[2]))
                                 from (
                                 select string_to_array(unnest(w.fdwoptions), '=') as a
                                 from pg_foreign_data_wrapper w
                                 inner join pg_roles r
                                 on r.oid = w.fdwowner
                                 where w.fdwname = '{0}'
                                 ) x
                                 ), ', ')))
                           else ''
                      end),
                     w.fdwname,
                     quote_ident(r.rolname),
                     g.text,
                     (CASE WHEN obj_description(w.oid, 'pg_foreign_data_wrapper') IS NOT NULL
                           THEN format(
                                    E'\n\nCOMMENT ON FOREIGN DATA WRAPPER %s IS %s;',
                                    quote_ident(w.fdwname),
                                    quote_literal(obj_description(w.oid, 'pg_foreign_data_wrapper'))
                                )
                           ELSE ''
                      END)
                   )
            from pg_foreign_data_wrapper w
            left join pg_proc h
            on h.oid = w.fdwhandler
            left join pg_proc v
            on v.oid = w.fdwvalidator
            inner join pg_roles r
            on r.oid = w.fdwowner
            inner join grants g on 1=1
            where quote_ident(w.fdwname) = '{0}'
        '''.format(fdw))
    
    @lock_required
    def GetDDLType(self, schema, type_name):
        typtype = self.connection.ExecuteScalar('''
            select t.typtype
            from pg_type t
            inner join pg_namespace n
            on n.oid = t.typnamespace
            where quote_ident(n.nspname) = '{0}'
              and quote_ident(t.typname) = '{1}'
        '''.format(schema, type_name))
        if typtype == 'c':
            return self.GetDDLClass(schema, type_name)
        elif typtype == 'e':
            return self.connection.ExecuteScalar('''
                select format(
                           E'CREATE TYPE %s.%s AS ENUM (\n%s\n);\n\nALTER TYPE %s.%s OWNER TO %s;\n%s',
                           quote_ident(n.nspname),
                           quote_ident(t.typname),
                           string_agg(format('    ' || chr(39) || '%s' || chr(39), e.enumlabel), E',\n'),
                           quote_ident(n.nspname),
                           quote_ident(t.typname),
                           quote_ident(r.rolname),
                           (CASE WHEN obj_description(t.oid, 'pg_type') IS NOT NULL
                                 THEN format(
                                         E'\n\nCOMMENT ON TYPE %s IS %s;',
                                         quote_ident(t.oid::regtype::text),
                                         quote_literal(obj_description(t.oid, 'pg_type'))
                                     )
                                 ELSE ''
                            END)
                       )
                from pg_type t
                inner join pg_namespace n on n.oid = t.typnamespace
                inner join pg_enum e on e.enumtypid = t.oid
                inner join pg_roles r on r.oid = t.typowner
                where quote_ident(n.nspname) = '{0}'
                  and quote_ident(t.typname) = '{1}'
                group by n.nspname,
                         t.typname,
                         r.rolname,
                         t.oid
            '''.format(schema, type_name))
        elif typtype == 'r':
            return self.connection.ExecuteScalar('''
                select format(
                         E'CREATE TYPE %s.%s AS RANGE (\n  SUBTYPE = %s.%s\n%s%s%s%s);\n\nALTER TYPE %s.%s OWNER TO %s;\n%s',
                         quote_ident(n.nspname),
                         quote_ident(t.typname),
                         quote_ident(sn.nspname),
                         quote_ident(st.typname),
                         (case when o.opcname is not null then format(E'  , SUBTYPE_OPCLASS = %s\n', quote_ident(o.opcname)) else '' end),
                         (case when c.collname is not null then format(E'  , COLLATION = %s\n', quote_ident(c.collname)) else '' end),
                         (case when pc.proname is not null then format(E'  , CANONICAL = %s.%s\n', quote_ident(nc.nspname), quote_ident(pc.proname)) else '' end),
                         (case when ps.proname is not null then format(E'  , SUBTYPE_DIFF = %s.%s\n', quote_ident(ns.nspname), quote_ident(ps.proname)) else '' end),
                         quote_ident(n.nspname),
                         quote_ident(t.typname),
                         quote_ident(ro.rolname),
                         (CASE WHEN obj_description(t.oid, 'pg_type') IS NOT NULL
                               THEN format(
                                       E'\n\nCOMMENT ON TYPE %s IS %s;',
                                       quote_ident(t.oid::regtype::text),
                                       quote_literal(obj_description(t.oid, 'pg_type'))
                                   )
                               ELSE ''
                          END)
                       )
                from pg_type t
                inner join pg_namespace n on n.oid = t.typnamespace
                inner join pg_range r on r.rngtypid = t.oid
                inner join pg_type st on st.oid = r.rngsubtype
                inner join pg_namespace sn on sn.oid = st.typnamespace
                left join pg_collation c on c.oid = r.rngcollation
                left join pg_opclass o on o.oid = r.rngsubopc
                left join pg_proc pc on pc.oid = r.rngcanonical
                left join pg_namespace nc on nc.oid = pc.pronamespace
                left join pg_proc ps on ps.oid = r.rngsubdiff
                left join pg_namespace ns on ns.oid = ps.pronamespace
                inner join pg_roles ro on ro.oid = t.typowner
                where quote_ident(n.nspname) = '{0}'
                  and quote_ident(t.typname) = '{1}'
            '''.format(schema, type_name))
        else:
            return self.connection.ExecuteScalar('''
                select format(
                         E'CREATE TYPE %s (\n  INPUT = %s,\n  , OUTPUT = %s\n%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s);\n\nALTER TYPE %s OWNER TO %s;\n%s',
                         quote_ident(n.nspname) || '.' || quote_ident(t.typname),
                         quote_ident(ninput.nspname) || '.' || quote_ident(pinput.proname),
                         quote_ident(noutput.nspname) || '.' || quote_ident(poutput.proname),
                         (case when preceive.proname is not null then format(E'  , RECEIVE = %s\n', quote_ident(nreceive.nspname) || '.' || quote_ident(preceive.proname)) else '' end),
                         (case when psend.proname is not null then format(E'  , SEND = %s\n', quote_ident(nsend.nspname) || '.' || quote_ident(psend.proname)) else '' end),
                         (case when pmodin.proname is not null then format(E'  , TYPMOD_IN = %s\n', quote_ident(nmodin.nspname) || '.' || quote_ident(pmodin.proname)) else '' end),
                         (case when pmodout.proname is not null then format(E'  , TYPMOD_OUT = %s\n', quote_ident(nmodout.nspname) || '.' || quote_ident(pmodout.proname)) else '' end),
                         (case when panalyze.proname is not null then format(E'  , ANALYZE = %s\n', quote_ident(nanalyze.nspname) || '.' || quote_ident(panalyze.proname)) else '' end),
                         (case when t.typlen > 0 then format(E'  , INTERNALLENGTH = %s\n', t.typlen) else '' end),
                         (case when t.typbyval then E'  , PASSEDBYVALUE\n' else '' end),
                         (case t.typalign
                            when 'c' then E'  , ALIGNMENT = char\n'
                            when 's' then E'  , ALIGNMENT = int2\n'
                            when 'i' then E'  , ALIGNMENT = int4\n'
                            when 'd' then E'  , ALIGNMENT = double\n'
                            else ''
                          end),
                         (case t.typstorage
                            when 'p' then E'  , STORAGE = plain\n'
                            when 'e' then E'  , STORAGE = extended\n'
                            when 'm' then E'  , STORAGE = main\n'
                            when 'x' then E'  , STORAGE = external\n'
                          end),
                         format(E'  , CATEGORY = ' || chr(39) || '%s' || chr(39) || E'\n', t.typcategory),
                         (case when t.typispreferred then E'  , PREFERRED = true\n' else '' end),
                         (case when t.typdefault is not null then format('  , DEFAULT = ' || chr(39) || '%s' || chr(39) || E'\n', t.typdefault) else '' end),
                         (case when telem.typname is not null then format(E'  , ELEMENT = %s\n', nelem.nspname || '.' || telem.typname) else '' end),
                         (case when t.typdelim is not null then format(E'  , DELIMITER = ' || chr(39) || '%s' || chr(39) || E'\n', t.typdelim) else '' end),
                         (case when coll.collname is not null then E'  , COLLATABLE = true\n' else '' end),
                         quote_ident(n.nspname) || '.' || quote_ident(t.typname),
                         quote_ident(r.rolname),
                         (CASE WHEN obj_description(t.oid, 'pg_type') IS NOT NULL
                               THEN format(
                                       E'\n\nCOMMENT ON TYPE %s IS %s;',
                                       quote_ident(t.oid::regtype::text),
                                       quote_literal(obj_description(t.oid, 'pg_type'))
                                   )
                               ELSE ''
                          END)
                       )
                from pg_type t
                inner join pg_roles r on r.oid = t.typowner
                inner join pg_namespace n on n.oid = t.typnamespace
                left join pg_type telem on telem.oid = t.typelem
                left join pg_namespace nelem on nelem.oid = telem.typnamespace
                left join pg_proc pinput on pinput.oid = t.typinput
                left join pg_namespace ninput on ninput.oid = pinput.pronamespace
                left join pg_proc poutput on poutput.oid = t.typoutput
                left join pg_namespace noutput on noutput.oid = poutput.pronamespace
                left join pg_proc preceive on preceive.oid = t.typreceive
                left join pg_namespace nreceive on nreceive.oid = preceive.pronamespace
                left join pg_proc psend on psend.oid = t.typsend
                left join pg_namespace nsend on nsend.oid = psend.pronamespace
                left join pg_proc pmodin on pmodin.oid = t.typmodin
                left join pg_namespace nmodin on nmodin.oid = pmodin.pronamespace
                left join pg_proc pmodout on pmodout.oid = t.typmodout
                left join pg_namespace nmodout on nmodout.oid = pmodout.pronamespace
                left join pg_proc panalyze on panalyze.oid = t.typanalyze
                left join pg_namespace nanalyze on nanalyze.oid = panalyze.pronamespace
                left join pg_collation coll on coll.oid = t.typcollation
                where quote_ident(n.nspname) = '{0}'
                  and quote_ident(t.typname) = '{1}'
            '''.format(schema, type_name))
    
    @lock_required
    def GetDDLDomain(self, schema, type_name):
        return self.connection.ExecuteScalar('''
            with domain as (
                select t.oid,
                       quote_ident(n.nspname) || '.' || quote_ident(t.typname) as name,
                       format_type(t.typbasetype, null) as basetype,
                       quote_ident(cn.nspname) || '.' || quote_ident(c.collname) as collation,
                       t.typdefault as defaultvalue,
                       t.typnotnull as notnull,
                       quote_ident(r.rolname) as domainowner
                from pg_type t
                inner join pg_namespace n on n.oid = t.typnamespace
                left join pg_collation c on c.oid = t.typcollation
                left join pg_namespace cn on cn.oid = c.collnamespace
                inner join pg_roles r on r.oid = t.typowner
                where quote_ident(n.nspname) = '{0}'
                  and quote_ident(t.typname) = '{1}'
            ),
            constraints as (
                select d.oid,
                       quote_ident(c.conname) as name,
                       pg_get_constraintdef(c.oid, true) as def
                from domain d
                inner join pg_constraint c on c.contypid = d.oid
            ),
            comments AS (
                SELECT obj_description('{0}.{1}'::regtype, 'pg_type') AS description
            ),
            create_domain as (
                select format(
                         E'CREATE DOMAIN %s\n  AS %s\n%s%s%s\n', d.name, d.basetype,
                         (case when d.collation is not null then format(E'  COLLATE %s', d.collation) else '' end),
                         (case when d.defaultvalue is not null then format(E'  DEFAULT %s\n', d.defaultvalue) else '' end),
                         (case when d.notnull then E'  NOT NULL' else '' end)
                       ) as sql
                from domain d
            ),
            create_constraints as (
                select string_agg(format(E'  CONSTRAINT %s %s\n', c.name, c.def), '') as sql
                from constraints c
            ),
            alter_domain as (
                select format(E'ALTER DOMAIN %s OWNER TO %s;\n', d.name, d.domainowner) as sql
                from domain d
            ),
            comment_on AS (
                SELECT format(
                           E'\n\COMMENT ON DOMAIN {0}.{1} IS %s',
                           quote_literal(description)
                       ) AS sql
                FROM comments
                WHERE description IS NOT NULL
            )
            select format(E'%s%s;\n\n%s%s',
                     (select sql from create_domain),
                     (select substring(sql from 1 for length(sql)-1) from create_constraints),
                     (select sql from alter_domain),
                     (SELECT sql FROM comment_on)
                   )
        '''.format(schema, type_name))

    @lock_required
    def GetDDLPublication(self, pub_name):
        if self.version_num < 130000:
            return self.connection.ExecuteScalar("""
                WITH publication AS (
                    SELECT oid,
                           pubname,
                           pubowner,
                           puballtables,
                           pubinsert,
                           pubupdate,
                           pubdelete,
                           pubtruncate
                    FROM pg_publication
                    WHERE quote_ident(pubname) = '{0}'
                ),
                tables AS (
                    SELECT string_agg(x.pubtable, ', ' ORDER BY x.pubtable) AS pubtables
                    FROM (
                        SELECT format(
                                   '%s.%s',
                                   quote_ident(n.nspname),
                                   quote_ident(c.relname)
                               )::regclass::text AS pubtable
                        FROM publication p
                        INNER JOIN pg_publication_rel pr
                                ON p.oid = pr.prpubid
                        INNER JOIN pg_class c
                                ON pr.prrelid = c.oid
                        INNER JOIN pg_namespace n
                                ON c.relnamespace = n.oid
                    ) x
                ),
                for_tables AS (
                    SELECT (CASE WHEN puballtables
                                 THEN E'  FOR ALL TABLES\n'
                                 WHEN coalesce(t.pubtables, '') <> ''
                                 THEN format(E'  FOR TABLES %s\n', t.pubtables)
                                 ELSE E''
                            END) AS text
                    FROM publication p
                    LEFT JOIN tables t
                           ON 1 = 1
                ),
                options AS (
                    SELECT (CASE WHEN z.puboptions <> ''
                                 THEN format(E'  WITH ( %s )', z.puboptions)
                                 ELSE ''
                            END) AS text
                    FROM (
                        SELECT string_agg(y.puboption, ', ') AS puboptions
                        FROM (
                            SELECT format('publish = ''%s''', x.publish) AS puboption
                            FROM (
                                SELECT array_to_string(
                                           array[
                                               (CASE WHEN pubinsert THEN 'insert' ELSE NULL END),
                                               (CASE WHEN pubupdate THEN 'update' ELSE NULL END),
                                               (CASE WHEN pubdelete THEN 'delete' ELSE NULL END),
                                               (CASE WHEN pubtruncate THEN 'truncate' ELSE NULL END)
                                           ]::text[],
                                           ', '
                                        ) AS publish
                                FROM publication
                            ) x
                            WHERE x.publish <> ''
                        ) y
                    ) z
                ),
                comments AS (
                    SELECT coalesce(obj_description(oid, 'pg_publication'), '') AS description,
                           pubname
                    FROM publication
                ),
                comment_on AS (
                    SELECT (CASE WHEN description <> ''
                                 THEN format(
                                          E'\n\nCOMMENT ON PUBLICATION %s IS %s;',
                                          quote_ident(pubname),
                                          quote_literal(description)
                                      )
                                 ELSE ''
                            END) AS text
                    FROM comments
                )
                SELECT format(E'CREATE PUBLICATION %s\n%s%s;\n\nALTER PUBLICATION %s OWNER TO %s;%s',
                         quote_ident(p.pubname),
                         ft.text,
                         o.text,
                         quote_ident(p.pubname),
                         quote_ident(r.rolname),
                         c.text
                       )
                FROM publication p
                INNER JOIN pg_roles r
                        ON r.oid = p.pubowner
                INNER JOIN for_tables ft
                        ON 1 = 1
                INNER JOIN options o
                        ON 1 = 1
                INNER JOIN comment_on c
                        ON 1 = 1
            """.format(pub_name))
        else:
            return self.connection.ExecuteScalar("""
                WITH publication AS (
                    SELECT oid,
                           pubname,
                           pubowner,
                           puballtables,
                           pubinsert,
                           pubupdate,
                           pubdelete,
                           pubtruncate,
                           pubviaroot
                    FROM pg_publication
                    WHERE quote_ident(pubname) = '{0}'
                ),
                tables AS (
                    SELECT string_agg(x.pubtable, ', ' ORDER BY x.pubtable) AS pubtables
                    FROM (
                        SELECT format(
                                   '%s.%s',
                                   quote_ident(n.nspname),
                                   quote_ident(c.relname)
                               )::regclass::text AS pubtable
                        FROM publication p
                        INNER JOIN pg_publication_rel pr
                                ON p.oid = pr.prpubid
                        INNER JOIN pg_class c
                                ON pr.prrelid = c.oid
                        INNER JOIN pg_namespace n
                                ON c.relnamespace = n.oid
                    ) x
                ),
                for_tables AS (
                    SELECT (CASE WHEN puballtables
                                 THEN E'  FOR ALL TABLES\n'
                                 WHEN coalesce(t.pubtables, '') <> ''
                                 THEN format(E'  FOR TABLES %s\n', t.pubtables)
                                 ELSE E''
                            END) AS text
                    FROM publication p
                    LEFT JOIN tables t
                           ON 1 = 1
                ),
                options AS (
                    SELECT (CASE WHEN z.puboptions <> ''
                                 THEN format(E'  WITH ( %s )', z.puboptions)
                                 ELSE ''
                            END) AS text
                    FROM (
                        SELECT string_agg(y.puboption, ', ') AS puboptions
                        FROM (
                            SELECT format('publish = ''%s''', x.publish) AS puboption
                            FROM (
                                SELECT array_to_string(
                                           array[
                                               (CASE WHEN pubinsert THEN 'insert' ELSE NULL END),
                                               (CASE WHEN pubupdate THEN 'update' ELSE NULL END),
                                               (CASE WHEN pubdelete THEN 'delete' ELSE NULL END),
                                               (CASE WHEN pubtruncate THEN 'truncate' ELSE NULL END)
                                           ]::text[],
                                           ', '
                                        ) AS publish
                                FROM publication
                            ) x
                            WHERE x.publish <> ''

                            UNION ALL

                            SELECT format('publish_via_partition_root = %s', pubviaroot::text) AS puboption
                            FROM publication
                        ) y
                    ) z
                ),
                comments AS (
                    SELECT coalesce(obj_description(oid, 'pg_publication'), '') AS description,
                           pubname
                    FROM publication
                ),
                comment_on AS (
                    SELECT (CASE WHEN description <> ''
                                 THEN format(
                                          E'\n\nCOMMENT ON PUBLICATION %s IS %s;',
                                          quote_ident(pubname),
                                          quote_literal(description)
                                      )
                                 ELSE ''
                            END) AS text
                    FROM comments
                )
                SELECT format(E'CREATE PUBLICATION %s\n%s%s;\n\nALTER PUBLICATION %s OWNER TO %s;%s',
                         quote_ident(p.pubname),
                         ft.text,
                         o.text,
                         quote_ident(p.pubname),
                         quote_ident(r.rolname),
                         c.text
                       )
                FROM publication p
                INNER JOIN pg_roles r
                        ON r.oid = p.pubowner
                INNER JOIN for_tables ft
                        ON 1 = 1
                INNER JOIN options o
                        ON 1 = 1
                INNER JOIN comment_on c
                        ON 1 = 1
            """.format(pub_name))

    @lock_required
    def GetDDLSubscription(self, sub_name):
        return self.connection.ExecuteScalar("""
            WITH subscription AS (
                SELECT oid,
                       subname,
                       subowner,
                       subenabled,
                       subconninfo,
                       subslotname,
                       subsynccommit,
                       subpublications
                FROM pg_subscription
                WHERE quote_ident(subname) = '{0}'
            ),
            options AS (
                SELECT (CASE WHEN z.suboptions <> ''
                             THEN format(E'  WITH ( %s )', z.suboptions)
                             ELSE ''
                        END) AS text
                FROM (
                    SELECT array_to_string(y.suboption, ', ') AS suboptions
                    FROM (
                        SELECT array[
                                   format('enabled = %s', subenabled::text),
                                   format('slot_name = ''%s''', subslotname),
                                   format('synchronous_commit = ''%s''', subsynccommit)
                               ]::text[] AS suboption
                        FROM subscription
                    ) y
                ) z
            ),
            comments AS (
                SELECT coalesce(obj_description(oid, 'pg_subscription'), '') AS description,
                       subname
                FROM subscription
            ),
            comment_on AS (
                SELECT (CASE WHEN description <> ''
                             THEN format(
                                      E'\n\nCOMMENT ON SUBSCRIPTION %s IS %s;',
                                      quote_ident(subname),
                                      quote_literal(description)
                                  )
                             ELSE ''
                        END) AS text
                FROM comments
            )
            SELECT format(E'CREATE SUBSCRIPTION %s\n  CONNECTION ''%s''\n  PUBLICATION %s\n%s;\n\nALTER SUBSCRIPTION %s OWNER TO %s;%s',
                     quote_ident(s.subname),
                     s.subconninfo,
                     array_to_string(s.subpublications, ', '),
                     o.text,
                     quote_ident(s.subname),
                     quote_ident(r.rolname),
                     c.text
                   )
            FROM subscription s
            INNER JOIN pg_roles r
                    ON r.oid = s.subowner
            INNER JOIN options o
                    ON 1 = 1
            INNER JOIN comment_on c
                    ON 1 = 1
        """.format(sub_name))

    @lock_required
    def GetDDLStatistic(self, schema, statistic):
        return self.connection.ExecuteScalar(
            """
                WITH statistics AS (
                    SELECT x.oid,
                           x.statistics_schema,
                           x.stxname,
                           x.table_schema,
                           x.table_name,
                           x.stxowner,
                           x.stxkind,
                           array_agg(x.attname) AS columns
                    FROM (
                        SELECT se.oid,
                               n2.nspname AS statistics_schema,
                               se.stxname,
                               n.nspname AS table_schema,
                               c.relname AS table_name,
                               se.stxowner,
                               se.stxkind,
                               a.attname
                        FROM pg_statistic_ext se
                        INNER JOIN pg_class c
                                ON se.stxrelid = c.oid
                        INNER JOIN pg_namespace n
                                ON c.relnamespace = n.oid
                        INNER JOIN pg_attribute a
                                ON c.oid = a.attrelid
                               AND a.attnum = ANY(se.stxkeys)
                        INNER JOIN pg_namespace n2
                                ON se.stxnamespace = n2.oid
                    ) x
                    WHERE quote_ident(x.statistics_schema) = '{0}'
                      AND quote_ident(x.stxname) = '{1}'
                    GROUP BY x.oid,
                             x.statistics_schema,
                             x.stxname,
                             x.table_schema,
                             x.table_name,
                             x.stxowner,
                             x.stxkind
                ),
                options AS (
                    SELECT format(
                               E'  ( %s )\n',
                               string_agg(y.kind, ', ')
                           ) AS text
                    FROM (
                        SELECT (CASE kind WHEN 'd'
                                          THEN 'dependencies'
                                          WHEN 'f'
                                          THEN 'ndistinct'
                                          WHEN 'm'
                                          THEN 'mcv'
                                END) AS kind
                        FROM (
                            SELECT unnest(stxkind) AS kind
                            FROM statistics
                        ) x
                    ) y
                ),
                comments AS (
                    SELECT coalesce(obj_description(oid, 'pg_statistic_ext'), '') AS description,
                           stxname,
                           statistics_schema
                    FROM statistics
                ),
                comment_on AS (
                    SELECT (CASE WHEN description <> ''
                                 THEN format(
                                          E'\n\nCOMMENT ON STATISTICS %s.%s IS %s;',
                                          quote_ident(statistics_schema),
                                          quote_ident(stxname),
                                          quote_literal(description)
                                      )
                                 ELSE ''
                            END) AS text
                    FROM comments
                )
                SELECT format(
                           E'CREATE STATISTICS %s\n%s  ON %s\n  FROM %s;\n\nALTER STATISTICS %s OWNER TO %s;%s',
                           format(
                               '%s.%s',
                               quote_ident(s.statistics_schema),
                               quote_ident(s.stxname)
                           ),
                           o.text,
                           array_to_string(s.columns, ', '),
                           format(
                               '%s.%s',
                               quote_ident(s.table_schema),
                               quote_ident(s.table_name)
                           )::regclass::text,
                           format(
                               '%s.%s',
                               quote_ident(s.statistics_schema),
                               quote_ident(s.stxname)
                           ),
                           quote_ident(r.rolname),
                           c.text
                       )
                FROM statistics s
                INNER JOIN pg_roles r
                        ON r.oid = s.stxowner
                INNER JOIN options o
                        ON 1 = 1
                INNER JOIN comment_on c
                        ON 1 = 1
            """.format(
                schema,
                statistic
            )
        )

    @lock_required
    def GetDDLAggregate(self, aggregate_name):
        return self.connection.ExecuteScalar(
            '''
                WITH procs AS (
                    SELECT p.oid AS function_oid,
                            quote_ident(n.nspname) || '.' || quote_ident(p.proname) || '(' || oidvectortypes(p.proargtypes) || ')' AS function_id,
                            quote_ident(n.nspname) AS schema_name,
                            quote_ident(p.proname) AS function_name,
                            format(
                                '%s.%s',
                                quote_ident(n.nspname),
                                quote_ident(p.proname)
                            ) AS function_full_name,
                            r.rolname AS function_owner,
                            p.prokind AS function_kind,
                            p.proparallel
                    FROM pg_proc p
                    INNER JOIN pg_namespace n
                            ON p.pronamespace = n.oid
                    INNER JOIN pg_roles r
                            ON p.proowner = r.oid
                ),
                operators AS (
                    SELECT o.oid AS operator_oid,
                            quote_ident(n.nspname) AS schema_name,
                            quote_ident(o.oprname) AS operator_name
                    FROM pg_operator o
                    INNER JOIN pg_namespace n
                            ON o.oprnamespace = n.oid
                ),
                types AS (
                    SELECT t.oid AS type_oid,
                            quote_ident(n.nspname) AS schema_name,
                            quote_ident(t.typname) AS type_name,
                            format(
                                '%s.%s',
                                quote_ident(n.nspname),
                                quote_ident(t.typname)
                            )::regtype AS type_full_name
                    FROM pg_type t
                    INNER JOIN pg_namespace n
                            ON t.typnamespace = n.oid
                ),
                privileges AS (
                    SELECT (u_grantor.rolname)::information_schema.sql_identifier AS grantor,
                            (grantee.rolname)::information_schema.sql_identifier AS grantee,
                            (p.privilege_type)::information_schema.character_data AS privilege_type,
                            (CASE WHEN (pg_has_role(grantee.oid, p.proowner, 'USAGE'::text) OR p.is_grantable)
                                    THEN 'YES'::text
                                    ELSE 'NO'::text
                            END)::information_schema.yes_or_no AS is_grantable
                    FROM (
                        SELECT p.pronamespace,
                                p.proowner,
                                (aclexplode(COALESCE(p.proacl, acldefault('f', p.proowner)))).grantor AS grantor,
                                (aclexplode(COALESCE(p.proacl, acldefault('f', p.proowner)))).grantee AS grantee,
                                (aclexplode(COALESCE(p.proacl, acldefault('f', p.proowner)))).privilege_type AS privilege_type,
                                (aclexplode(COALESCE(p.proacl, acldefault('f', p.proowner)))).is_grantable AS is_grantable
                        FROM pg_proc p
                        WHERE p.prokind = 'a'
                            AND p.oid = '{0}'::regprocedure
                    ) p
                    INNER JOIN pg_namespace n
                            ON n.oid = p.pronamespace
                    INNER JOIN pg_roles u_grantor
                            ON u_grantor.oid = p.grantor
                    INNER JOIN (
                        SELECT r.oid,
                                r.rolname
                        FROM pg_roles r

                        UNION ALL

                        SELECT (0)::oid AS oid,
                                'PUBLIC'::name
                    ) grantee
                            ON grantee.oid = p.grantee
                ),
                grants AS (
                    SELECT coalesce(
                                string_agg(
                                    format(
                                        E'GRANT %s ON FUNCTION {0} TO %s%s;\n',
                                        privilege_type,
                                        (CASE grantee WHEN 'PUBLIC'
                                                        THEN 'PUBLIC'
                                                        ELSE quote_ident(grantee)
                                        END),
                                        (CASE is_grantable WHEN 'YES'
                                                            THEN ' WITH GRANT OPTION'
                                                            ELSE ''
                                        END)
                                    ),
                                    ''
                                ),
                                ''
                            ) AS text
                    FROM privileges
                ),
                comments AS (
                    SELECT format(
                        E'\nCOMMENT ON AGGREGATE {0} is %s;',
                        quote_literal(x.description)
                    ) AS text
                    FROM (
                        SELECT obj_description ('{0}'::regprocedure, 'pg_proc') AS description
                    ) x
                    WHERE x.description IS NOT NULL
                )
                SELECT format(
                            E'CREATE AGGREGATE %s (\n\tSFUNC = %s\n  , STYPE = %s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s\n);\n\nALTER AGGREGATE %s OWNER TO %s;\n\n%s%s',
                            p1.function_id,
                            p2.function_full_name,
                            t1.type_full_name,
                            (CASE WHEN a.aggtransspace <> 0
                                    THEN format(E'\n  , SSPACE = %s', a.aggtransspace)
                                    ELSE ''
                            END),
                            (CASE WHEN p3.function_id IS NOT NULL
                                    THEN format(E'\n  , FINALFUNC = %s', p3.function_full_name)
                                    ELSE ''
                            END),
                            (CASE WHEN aggfinalextra
                                    THEN E'\n  , FINALFUNC_EXTRA'
                                    ELSE ''
                            END),
                            format(
                                E'\n  , FINALFUNC_MODIFY = %s',
                                (CASE aggfinalmodify WHEN 'r'
                                                    THEN 'READ_ONLY'
                                                    WHEN 's'
                                                    THEN 'SHAREABLE'
                                                    WHEN 'w'
                                                    THEN 'READ_WRITE'
                                END)
                            ),
                            (CASE WHEN p4.function_id IS NOT NULL
                                    THEN format(E'\n  , COMBINEFUNC = %s', p4.function_full_name)
                                    ELSE ''
                            END),
                            (CASE WHEN p5.function_id IS NOT NULL
                                    THEN format(E'\n  , SERIALFUNC = %s', p5.function_full_name)
                                    ELSE ''
                            END),
                            (CASE WHEN p6.function_id IS NOT NULL
                                    THEN format(E'\n  , DESERIALFUNC = %s', p6.function_full_name)
                                    ELSE ''
                            END),
                            (CASE WHEN a.agginitval IS NOT NULL
                                    THEN format(E'\n  , INITCOND = %s', a.agginitval)
                                    ELSE ''
                            END),
                            (CASE WHEN p7.function_id IS NOT NULL
                                    THEN format(E'\n  , MSFUNC = %s', p7.function_full_name)
                                    ELSE ''
                            END),
                            (CASE WHEN p8.function_id IS NOT NULL
                                    THEN format(E'\n  , MINVFUNC = %s', p8.function_full_name)
                                    ELSE ''
                            END),
                            (CASE WHEN t2.type_oid IS NOT NULL
                                    THEN format(E'\n  , MSTYPE = %s', t2.type_full_name)
                                    ELSE ''
                            END),
                            (CASE WHEN a.aggmtransspace <> 0
                                    THEN format(E'\n  , MSSPACE = %s', a.aggmtransspace)
                                    ELSE ''
                            END),
                            (CASE WHEN p9.function_id IS NOT NULL
                                    THEN format(E'\n  , MFINALFUNC = %s', p9.function_full_name)
                                    ELSE ''
                            END),
                            (CASE WHEN aggmfinalextra
                                    THEN E'\n  , MFINALFUNC_EXTRA'
                                    ELSE ''
                            END),
                            format(
                                E'\n  , MFINALFUNC_MODIFY = %s',
                                (CASE aggmfinalmodify WHEN 'r'
                                                        THEN 'READ_ONLY'
                                                        WHEN 's'
                                                        THEN 'SHAREABLE'
                                                        WHEN 'w'
                                                        THEN 'READ_WRITE'
                                END)
                            ),
                            (CASE WHEN a.aggminitval IS NOT NULL
                                    THEN format(E'\n  , MINITCOND = %s', a.aggminitval)
                                    ELSE ''
                            END),
                            (CASE WHEN o.operator_oid IS NOT NULL
                                    THEN format(E'\n  , SORTOP = %s', o.operator_oid::regoperator)
                                    ELSE ''
                            END),
                            format(
                                E'\n  , PARALLEL = %s',
                                (CASE p1.proparallel WHEN 's'
                                                    THEN 'SAFE'
                                                    WHEN 'r'
                                                    THEN 'RESTRICTED'
                                                    WHEN 'u'
                                                    THEN 'UNSAFE'
                                END)
                            ),
                            p1.function_id,
                            p1.function_owner,
                            g.text,
                            c.text
                        )
                FROM pg_aggregate a
                INNER JOIN procs p1
                        ON a.aggfnoid = p1.function_oid
                LEFT JOIN procs p2
                        ON a.aggtransfn = p2.function_oid
                LEFT JOIN procs p3
                        ON a.aggfinalfn = p3.function_oid
                LEFT JOIN procs p4
                        ON a.aggcombinefn = p4.function_oid
                LEFT JOIN procs p5
                        ON a.aggserialfn = p5.function_oid
                LEFT JOIN procs p6
                        ON a.aggdeserialfn = p6.function_oid
                LEFT JOIN procs p7
                        ON a.aggmtransfn = p7.function_oid
                LEFT JOIN procs p8
                        ON a.aggminvtransfn = p8.function_oid
                LEFT JOIN procs p9
                        ON a.aggmfinalfn = p9.function_oid
                LEFT JOIN operators o
                        ON a.aggsortop = o.operator_oid
                LEFT JOIN types t1
                        ON a.aggtranstype = t1.type_oid
                LEFT JOIN types t2
                        ON a.aggmtranstype = t2.type_oid
                INNER JOIN grants g
                        ON 1 = 1
                LEFT JOIN comments c
                        ON 1 = 1
                WHERE p1.function_kind = 'a'
                    AND p1.function_id = '{0}'
            '''.format(
                aggregate_name
            )
        )

    @lock_required
    def GetDDLTableField(self, schema, table, table_field):
        if self.version_num < 130000:
            return self.connection.ExecuteScalar(
                '''
                    WITH columns AS (
                        SELECT format(
                                   '%I %s%s%s%s',
                                   a.attname::text,
                                   format_type(t.oid, a.atttypmod),
                                   (CASE WHEN length(col.collcollate) > 0
                                         THEN ' COLLATE ' || quote_ident(col.collcollate::text)
                                         ELSE ''
                                    END),
                                   (CASE WHEN a.attnotnull
                                         THEN ' NOT NULL'::text
                                         ELSE ''::text
                                    END),
                                   (CASE WHEN a.attidentity = 'a'
                                         THEN ' GENERATED ALWAYS AS IDENTITY'::text
                                         WHEN a.attidentity = 'd'
                                         THEN ' GENERATED BY DEFAULT AS IDENTITY'::text
                                         ELSE ''::text
                                    END)
                               ) AS definition,
                               a.attname AS name,
                               col_description(c.oid, a.attnum::integer) AS comment,
                               pg_get_expr(def.adbin, def.adrelid) AS default_value,
                               a.attacl
                        FROM pg_class c
                        INNER JOIN pg_namespace s
                                ON s.oid = c.relnamespace
                        INNER JOIN pg_attribute a
                                ON c.oid = a.attrelid
                        LEFT JOIN pg_attrdef def
                               ON c.oid = def.adrelid
                              AND a.attnum = def.adnum
                        LEFT JOIN pg_constraint con
                               ON con.conrelid = c.oid
                              AND (a.attnum = ANY (con.conkey))
                              AND con.contype = 'p'
                        LEFT JOIN pg_type t
                               ON t.oid = a.atttypid
                        LEFT JOIN pg_collation col
                               ON col.oid = a.attcollation
                        INNER JOIN pg_namespace tn
                                ON tn.oid = t.typnamespace
                        WHERE c.relkind IN ('r', 'p')
                          AND a.attnum > 0
                          AND NOT a.attisdropped
                          AND has_table_privilege(c.oid, 'select')
                          AND has_schema_privilege(s.oid, 'usage')
                          AND c.oid = '{0}.{1}'::regclass
                          AND a.attname = '{2}'
                    ),
                    comments AS (
                        SELECT format(
                                   E'\n\nCOMMENT ON COLUMN %s.%s IS %s;',
                                   '{0}.{1}',
                                   quote_ident(name),
                                   quote_nullable(comment)
                               ) AS definition
                        FROM columns
                        WHERE comment IS NOT NULL
                    ),
                    defaults AS (
                        SELECT format(
                                   E'\n\nALTER TABLE %s\n\tALTER %s SET DEFAULT %s;',
                                   '{0}.{1}'::regclass,
                                   quote_ident(name),
                                   default_value
                               ) AS definition
                        FROM columns
                        WHERE default_value IS NOT NULL
                    ),
                    columnsprivileges as (
                        SELECT r.rolname AS grantee,
                               c.name AS column_name,
                               c.privilege_type
                        FROM (
                            SELECT name,
                                   (aclexplode(attacl)).grantee AS grantee,
                                   (aclexplode(attacl)).privilege_type AS privilege_type
                            FROM columns
                        ) c
                        INNER JOIN pg_roles r
                                ON c.grantee = r.oid
                    ),
                    columnsgrants as (
                        SELECT coalesce(
                                   nullif(
                                       format(
                                           E'\n\n%s',
                                           string_agg(
                                               format(
                                                   E'GRANT %s(%s) ON %s TO %s;\n',
                                                   privilege_type,
                                                   column_name,
                                                   '{0}.{1}',
                                                   quote_ident(grantee)
                                               ),
                                               ''
                                           )
                                       ),
                                       '\n\n'
                                   ),
                                   ''
                               ) AS definition
                         FROM columnsprivileges
                    )
                    SELECT format(
                                E'ALTER TABLE %s\n\tADD COLUMN %s;%s%s%s',
                                '{0}.{1}'::regclass,
                                col.definition,
                                coalesce(com.definition, ''),
                                coalesce(def.definition, ''),
                                coalesce(cg.definition, '')
                           )
                    FROM columns col
                    LEFT JOIN comments com
                           ON 1 = 1
                    LEFT JOIN defaults def
                           ON 1 = 1
                    LEFT JOIN columnsgrants cg
                           ON 1 = 1
                '''.format(
                    schema,
                    table,
                    table_field
                )
            )
        else:
            return self.connection.ExecuteScalar(
                '''
                    WITH columns AS (
                        SELECT format(
                                   '%I %s%s%s%s',
                                   a.attname::text,
                                   format_type(t.oid, a.atttypmod),
                                   (CASE WHEN length(col.collcollate) > 0
                                         THEN ' COLLATE ' || quote_ident(col.collcollate::text)
                                         ELSE ''
                                    END),
                                   (CASE WHEN a.attnotnull
                                         THEN ' NOT NULL'::text
                                         ELSE ''::text
                                    END),
                                   (CASE WHEN a.attidentity = 'a'
                                         THEN ' GENERATED ALWAYS AS IDENTITY'::text
                                         WHEN a.attidentity = 'd'
                                         THEN ' GENERATED BY DEFAULT AS IDENTITY'::text
                                         WHEN a.attgenerated = 's'
                                         THEN format(' GENERATED ALWAYS AS %s STORED', pg_get_expr(def.adbin, def.adrelid))::text
                                         ELSE ''::text
                                    END)
                               ) AS definition,
                               a.attname AS name,
                               col_description(c.oid, a.attnum::integer) AS comment,
                               pg_get_expr(def.adbin, def.adrelid) AS default_value,
                               a.attgenerated AS generated,
                               a.attacl
                        FROM pg_class c
                        INNER JOIN pg_namespace s
                                ON s.oid = c.relnamespace
                        INNER JOIN pg_attribute a
                                ON c.oid = a.attrelid
                        LEFT JOIN pg_attrdef def
                               ON c.oid = def.adrelid
                              AND a.attnum = def.adnum
                        LEFT JOIN pg_constraint con
                               ON con.conrelid = c.oid
                              AND (a.attnum = ANY (con.conkey))
                              AND con.contype = 'p'
                        LEFT JOIN pg_type t
                               ON t.oid = a.atttypid
                        LEFT JOIN pg_collation col
                               ON col.oid = a.attcollation
                        INNER JOIN pg_namespace tn
                                ON tn.oid = t.typnamespace
                        WHERE c.relkind IN ('r', 'p')
                          AND a.attnum > 0
                          AND NOT a.attisdropped
                          AND has_table_privilege(c.oid, 'select')
                          AND has_schema_privilege(s.oid, 'usage')
                          AND c.oid = '{0}.{1}'::regclass
                          AND quote_ident(a.attname) = '{2}'
                    ),
                    comments AS (
                        SELECT format(
                                   E'\n\nCOMMENT ON COLUMN %s.%s IS %s;',
                                   '{0}.{1}',
                                   quote_ident(name),
                                   quote_nullable(comment)
                               ) AS definition
                        FROM columns
                        WHERE comment IS NOT NULL
                    ),
                    defaults AS (
                        SELECT format(
                                   E'\n\nALTER TABLE %s\n\tALTER %s SET DEFAULT %s;',
                                   '{0}.{1}'::regclass,
                                   quote_ident(name),
                                   default_value
                               ) AS definition
                        FROM columns
                        WHERE default_value IS NOT NULL
                          AND generated = ''
                    ),
                    columnsprivileges as (
                        SELECT r.rolname AS grantee,
                               c.name AS column_name,
                               c.privilege_type
                        FROM (
                            SELECT name,
                                   (aclexplode(attacl)).grantee AS grantee,
                                   (aclexplode(attacl)).privilege_type AS privilege_type
                            FROM columns
                        ) c
                        INNER JOIN pg_roles r
                                ON c.grantee = r.oid
                    ),
                    columnsgrants as (
                        SELECT coalesce(
                                   nullif(
                                       format(
                                           E'\n\n%s',
                                           string_agg(
                                               format(
                                                   E'GRANT %s(%s) ON %s TO %s;\n',
                                                   privilege_type,
                                                   column_name,
                                                   '{0}.{1}',
                                                   quote_ident(grantee)
                                               ),
                                               ''
                                           )
                                       ),
                                       '\n\n'
                                   ),
                                   ''
                               ) AS definition
                         FROM columnsprivileges
                    )
                    SELECT format(
                                E'ALTER TABLE %s\n\tADD COLUMN %s;%s%s%s',
                                '{0}.{1}'::regclass,
                                col.definition,
                                coalesce(com.definition, ''),
                                coalesce(def.definition, ''),
                                coalesce(cg.definition, '')
                           )
                    FROM columns col
                    LEFT JOIN comments com
                           ON 1 = 1
                    LEFT JOIN defaults def
                           ON 1 = 1
                    LEFT JOIN columnsgrants cg
                           ON 1 = 1
                '''.format(
                    schema,
                    table,
                    table_field
                )
            )

    def GetDDL(self, schema, table, object_name, object_type):
        if object_type == 'role':
            return self.GetDDLRole(object_name)
        elif object_type == 'tablespace':
            return self.GetDDLTablespace(object_name)
        elif object_type == 'database':
            return self.GetDDLDatabase(object_name)
        elif object_type == 'extension':
            return self.GetDDLExtension(object_name)
        elif object_type == 'schema':
            return self.GetDDLSchema(schema)
        elif object_type == 'table':
            return self.GetDDLClass(schema, object_name)
        elif object_type == 'table_field':
            return self.GetDDLTableField(schema, table, object_name)
        elif object_type == 'index':
            return self.GetDDLClass(schema, object_name)
        elif object_type == 'sequence':
            return self.GetDDLClass(schema, object_name)
        elif object_type == 'view':
            return self.GetDDLClass(schema, object_name)
        elif object_type == 'mview':
            return self.GetDDLClass(schema, object_name)
        elif object_type == 'function':
            return self.GetDDLFunction(object_name)
        elif object_type == 'procedure':
            return self.GetDDLProcedure(object_name)
        elif object_type == 'trigger':
            return self.GetDDLTrigger(object_name, table, schema)
        elif object_type == 'event_trigger':
            return self.GetDDLEventTrigger(object_name)
        elif object_type == 'trigger_function':
            return self.GetDDLFunction(object_name)
        elif object_type == 'direct_trigger_function':
            return self.GetDDLFunction(object_name)
        elif object_type == 'event_trigger_function':
            return self.GetDDLFunction(object_name)
        elif object_type == 'direct_event_trigger_function':
            return self.GetDDLFunction(object_name)
        elif object_type == 'pk':
            return self.GetDDLConstraint(schema, table, object_name)
        elif object_type == 'foreign_key':
            return self.GetDDLConstraint(schema, table, object_name)
        elif object_type == 'unique':
            return self.GetDDLConstraint(schema, table, object_name)
        elif object_type == 'check':
            return self.GetDDLConstraint(schema, table, object_name)
        elif object_type == 'exclude':
            return self.GetDDLConstraint(schema, table, object_name)
        elif object_type == 'rule':
            return self.GetRuleDefinition(object_name, table, schema)
        elif object_type == 'foreign_table':
            return self.GetDDLClass(schema, object_name)
        elif object_type == 'user_mapping':
            return self.GetDDLUserMapping(schema, object_name)
        elif object_type == 'foreign_server':
            return self.GetDDLForeignServer(object_name)
        elif object_type == 'foreign_data_wrapper':
            return self.GetDDLForeignDataWrapper(object_name)
        elif object_type == 'type':
            return self.GetDDLType(schema, object_name)
        elif object_type == 'domain':
            return self.GetDDLDomain(schema, object_name)
        elif object_type == 'publication':
            return self.GetDDLPublication(object_name)
        elif object_type == 'subscription':
            return self.GetDDLSubscription(object_name)
        elif object_type == 'statistic':
            return self.GetDDLStatistic(schema, object_name)
        elif object_type == 'aggregate':
            return self.GetDDLAggregate(object_name)
        else:
            return ''

    @lock_required
    def GetAutocompleteValues(self, columns, query_filter):
        return self.connection.Query('''
            select {0}
            from (
            (select *
            from (select 'database' as type,
                   0 as sequence,
                   0 as num_dots,
                   quote_ident(datname) as result,
                   quote_ident(datname) as result_complete,
                   quote_ident(datname) as select_value,
                   '' as complement,
                   '' as complement_complete,
                   false as is_builtin
            from pg_database) search
            {1}
            LIMIT 500)

            UNION ALL

            (select *
            from (select 'tablespace' as type,
                   2 as sequence,
                   0 as num_dots,
                   quote_ident(spcname) as result,
                   quote_ident(spcname) as result_complete,
                   quote_ident(spcname) as select_value,
                   '' as complement,
                   '' as complement_complete,
                    false as is_builtin
            from pg_tablespace) search
            {1}
            LIMIT 500)

            UNION ALL

            (select *
            from (select 'role' as type,
                   1 as sequence,
                   0 as num_dots,
                   quote_ident(rolname) as result,
                   quote_ident(rolname) as result_complete,
                   quote_ident(rolname) as select_value,
                   '' as complement,
                   '' as complement_complete,
                   false as is_builtin
            from pg_roles) search
            {1}
            LIMIT 500)

            UNION ALL

            (select *
            from (select 'extension' as type,
                   4 as sequence,
                   0 as num_dots,
                   quote_ident(extname) as result,
                   quote_ident(extname) as result_complete,
                   quote_ident(extname) as select_value,
                   '' as complement,
                   '' as complement_complete,
                   false as is_builtin
            from pg_extension) search
            {1}
            LIMIT 500)

            UNION ALL

            (select *
            from (select 'schema' as type,
                   3 as sequence,
                   0 as num_dots,
                   quote_ident(nspname) as result,
                   quote_ident(nspname) as result_complete,
                   quote_ident(nspname) as select_value,
                   '' as complement,
                   '' as complement_complete,
                   false as is_builtin
            from pg_catalog.pg_namespace
            where nspname not in ('pg_toast') and nspname not like 'pg%%temp%%') search
            {1}
            LIMIT 500)

            UNION ALL

            (select *
            from (select 'table' as type,
                   5 as sequence,
                   1 as num_dots,
                   quote_ident(c.relname) as result,
                   quote_ident(n.nspname) || '.' || quote_ident(c.relname) as result_complete,
                   quote_ident(n.nspname) || '.' || quote_ident(c.relname) as select_value,
                   quote_ident(n.nspname) as complement,
                   '' as complement_complete,
                    n.nspname IN ('information_schema', 'pg_catalog') as is_builtin
            from pg_class c
            inner join pg_namespace n
            on n.oid = c.relnamespace
            where c.relkind in ('r', 'p')) search
            {1}
            order by is_builtin ASC, complement, result
            LIMIT 500)

            UNION ALL

            (select *
            from (select 'view' as type,
                   6 as sequence,
                   1 as num_dots,
                   quote_ident(table_name) as result,
                   quote_ident(table_schema) || '.' || quote_ident(table_name) as result_complete,
                   quote_ident(table_schema) || '.' || quote_ident(table_name) as select_value,
                   quote_ident(table_schema) as complement,
                   '' as complement_complete,
                    false as is_builtin
            from information_schema.views) search
            {1}
            LIMIT 500)

            UNION ALL

            (select *
            from (select 'function' as type,
                   8 as sequence,
                   1 as num_dots,
                   quote_ident(p.proname) as result,
                   quote_ident(n.nspname) || '.' || quote_ident(p.proname) as result_complete,
                   quote_ident(n.nspname) || '.' || quote_ident(p.proname) || '(' as select_value,
                   quote_ident(n.nspname) as complement,
                   '' as complement_complete,
                    false as is_builtin
            from pg_proc p
            join pg_namespace n
            on p.pronamespace = n.oid
            where format_type(p.prorettype, null) not in ('trigger', 'event_trigger')) search
            {1}
            LIMIT 500)

            UNION ALL

            (select *
            from (select 'index' as type,
                   9 as sequence,
                   1 as num_dots,
                   quote_ident(i.indexname) as result,
                   quote_ident(i.schemaname) || '.' || quote_ident(i.indexname) as result_complete,
                   quote_ident(i.schemaname) || '.' || quote_ident(i.indexname) as select_value,
                   quote_ident(i.schemaname) || '.' || quote_ident(i.tablename) as complement,
                   quote_ident(i.tablename) as complement_complete,
                   false as is_builtin
            from pg_indexes i) search
            {1}
            LIMIT 500 )) search
            {1}
            order by sequence,result_complete
        '''.format(columns, query_filter), True)

    @lock_required
    def ChangeRolePassword(self, role, password):
        self.connection.Execute(
            '''
                ALTER ROLE {0}
                    WITH PASSWORD '{1}'
            '''.format(
                role,
                password
            )
        )

    @lock_required
    def GetObjectDescriptionAggregate(self, oid):
        row = self.connection.Query(
            '''
                SELECT {0}::regprocedure AS id,
                       coalesce(obj_description({0}, 'pg_proc'), '') AS description
            '''.format(
                oid
            )
        ).Rows[0]

        return "COMMENT ON AGGREGATE {0} is '{1}'".format(
            row['id'],
            row['description']
        )

    @lock_required
    def GetObjectDescriptionTableField(self, oid, position):
        row = self.connection.Query(
            '''
                SELECT format(
                           '%s.%s',
                           {0}::regclass,
                           attname
                       ) AS id,
                       coalesce(col_description({0}, {1}), '') AS description
                FROM pg_attribute
                WHERE attrelid = {0}::regclass
                  AND attnum = {1}
            '''.format(
                oid,
                position
            )
        ).Rows[0]

        return "COMMENT ON COLUMN {0} is '{1}'".format(
            row['id'],
            row['description']
        )

    @lock_required
    def GetObjectDescriptionConstraint(self, oid):
        row = self.connection.Query(
            '''
                SELECT conname AS id,
                       conrelid::regclass AS table_id,
                       coalesce(obj_description({0}, 'pg_constraint'), '') AS description
                FROM pg_constraint c
                WHERE oid = {0}
            '''.format(
                oid
            )
        ).Rows[0]

        return "COMMENT ON CONSTRAINT {0} ON {1} is '{2}'".format(
            row['id'],
            row['table_id'],
            row['description']
        )

    @lock_required
    def GetObjectDescriptionDatabase(self, oid):
        row = self.connection.Query(
            '''
                SELECT quote_ident(datname) AS id,
                       coalesce(shobj_description({0}, 'pg_database'), '') AS description
                FROM pg_database
                WHERE oid = {0}
            '''.format(
                oid
            )
        ).Rows[0]

        return "COMMENT ON DATABASE {0} is '{1}'".format(
            row['id'],
            row['description']
        )

    @lock_required
    def GetObjectDescriptionDomain(self, oid):
        row = self.connection.Query(
            '''
                SELECT '{0}'::regtype AS id,
                       coalesce(obj_description({0}, 'pg_type'), '') AS description
            '''.format(
                oid
            )
        ).Rows[0]

        return "COMMENT ON DOMAIN {0} is '{1}'".format(
            row['id'],
            row['description']
        )

    @lock_required
    def GetObjectDescriptionExtension(self, oid):
        row = self.connection.Query(
            '''
                SELECT quote_ident(extname) AS id,
                       coalesce(obj_description({0}, 'pg_extension'), '') AS description
                FROM pg_extension
                WHERE oid = {0}
            '''.format(
                oid
            )
        ).Rows[0]

        return "COMMENT ON EXTENSION {0} is '{1}'".format(
            row['id'],
            row['description']
        )

    @lock_required
    def GetObjectDescriptionEventTrigger(self, oid):
        row = self.connection.Query(
            '''
                SELECT quote_ident(evtname) AS id,
                       coalesce(obj_description({0}, 'pg_event_trigger'), '') AS description
                FROM pg_event_trigger
                WHERE oid = {0}
            '''.format(
                oid
            )
        ).Rows[0]

        return "COMMENT ON EVENT TRIGGER {0} is '{1}'".format(
            row['id'],
            row['description']
        )

    @lock_required
    def GetObjectDescriptionForeignDataWrapper(self, oid):
        row = self.connection.Query(
            '''
                SELECT quote_ident(fdwname) AS id,
                       coalesce(obj_description({0}, 'pg_foreign_data_wrapper'), '') AS description
                FROM pg_foreign_data_wrapper
                WHERE oid = {0}
            '''.format(
                oid
            )
        ).Rows[0]

        return "COMMENT ON FOREIGN DATA WRAPPER {0} is '{1}'".format(
            row['id'],
            row['description']
        )

    @lock_required
    def GetObjectDescriptionForeignServer(self, oid):
        row = self.connection.Query(
            '''
                SELECT quote_ident(srvname) AS id,
                       coalesce(obj_description({0}, 'pg_foreign_server'), '') AS description
                FROM pg_foreign_server
                WHERE oid = {0}
            '''.format(
                oid
            )
        ).Rows[0]

        return "COMMENT ON SERVER {0} is '{1}'".format(
            row['id'],
            row['description']
        )

    @lock_required
    def GetObjectDescriptionForeignTable(self, oid):
        row = self.connection.Query(
            '''
                SELECT {0}::regclass AS id,
                       coalesce(obj_description({0}, 'pg_class'), '') AS description
            '''.format(
                oid
            )
        ).Rows[0]

        return "COMMENT ON FOREIGN TABLE {0} is '{1}'".format(
            row['id'],
            row['description']
        )

    @lock_required
    def GetObjectDescriptionFunction(self, oid):
        row = self.connection.Query(
            '''
                SELECT {0}::regprocedure AS id,
                       coalesce(obj_description({0}, 'pg_proc'), '') AS description
            '''.format(
                oid
            )
        ).Rows[0]

        return "COMMENT ON FUNCTION {0} is '{1}'".format(
            row['id'],
            row['description']
        )

    @lock_required
    def GetObjectDescriptionIndex(self, oid):
        row = self.connection.Query(
            '''
                SELECT {0}::regclass AS id,
                       coalesce(obj_description({0}, 'pg_class'), '') AS description
            '''.format(
                oid
            )
        ).Rows[0]

        return "COMMENT ON INDEX {0} is '{1}'".format(
            row['id'],
            row['description']
        )

    @lock_required
    def GetObjectDescriptionMaterializedView(self, oid):
        row = self.connection.Query(
            '''
                SELECT {0}::regclass AS id,
                       coalesce(obj_description({0}, 'pg_class'), '') AS description
            '''.format(
                oid
            )
        ).Rows[0]

        return "COMMENT ON MATERIALIZED VIEW {0} is '{1}'".format(
            row['id'],
            row['description']
        )

    @lock_required
    def GetObjectDescriptionProcedure(self, oid):
        row = self.connection.Query(
            '''
                SELECT {0}::regprocedure AS id,
                       coalesce(obj_description({0}, 'pg_proc'), '') AS description
            '''.format(
                oid
            )
        ).Rows[0]

        return "COMMENT ON PROCEDURE {0} is '{1}'".format(
            row['id'],
            row['description']
        )

    @lock_required
    def GetObjectDescriptionPublication(self, oid):
        row = self.connection.Query(
            '''
                SELECT quote_ident(pubname) AS id,
                       coalesce(obj_description({0}, 'pg_publication'), '') AS description
                FROM pg_publication
                WHERE oid = {0}
            '''.format(
                oid
            )
        ).Rows[0]

        return "COMMENT ON PUBLICATION {0} is '{1}'".format(
            row['id'],
            row['description']
        )

    @lock_required
    def GetObjectDescriptionRole(self, oid):
        row = self.connection.Query(
            '''
                SELECT {0}::regrole AS id,
                       coalesce(shobj_description({0}, 'pg_roles'), '') AS description
            '''.format(
                oid
            )
        ).Rows[0]

        return "COMMENT ON ROLE {0} is '{1}'".format(
            row['id'],
            row['description']
        )

    @lock_required
    def GetObjectDescriptionRule(self, oid):
        row = self.connection.Query(
            '''
                SELECT quote_ident(r.rulename) AS id,
                       format('%s.%s', r.schemaname, r.tablename)::regclass AS table_id,
                       coalesce(obj_description({0}, 'pg_rewrite'), '') AS description
                FROM pg_rules r
                INNER JOIN pg_rewrite rw
                        ON r.rulename = rw.rulename
                WHERE rw.oid = {0}
            '''.format(
                oid
            )
        ).Rows[0]

        return "COMMENT ON RULE {0} ON {1} is '{2}'".format(
            row['id'],
            row['table_id'],
            row['description']
        )

    @lock_required
    def GetObjectDescriptionSchema(self, oid):
        row = self.connection.Query(
            '''
                SELECT {0}::regnamespace AS id,
                       coalesce(obj_description({0}, 'pg_namespace'), '') AS description
            '''.format(
                oid
            )
        ).Rows[0]

        return "COMMENT ON SCHEMA {0} is '{1}'".format(
            row['id'],
            row['description']
        )

    @lock_required
    def GetObjectDescriptionSequence(self, oid):
        row = self.connection.Query(
            '''
                SELECT {0}::regclass AS id,
                       coalesce(obj_description({0}, 'pg_class'), '') AS description
            '''.format(
                oid
            )
        ).Rows[0]

        return "COMMENT ON SEQUENCE {0} is '{1}'".format(
            row['id'],
            row['description']
        )

    @lock_required
    def GetObjectDescriptionStatistic(self, oid):
        row = self.connection.Query(
            '''
                SELECT format('%s.%s', quote_ident(stxnamespace::regnamespace::text), quote_ident(stxname)) AS id,
                       coalesce(obj_description({0}, 'pg_statistic_ext'), '') AS description
                FROM pg_statistic_ext
                WHERE oid = {0}
            '''.format(
                oid
            )
        ).Rows[0]

        return "COMMENT ON STATISTICS {0} is '{1}'".format(
            row['id'],
            row['description']
        )

    @lock_required
    def GetObjectDescriptionSubscription(self, oid):
        row = self.connection.Query(
            '''
                SELECT quote_ident(subname) AS id,
                       coalesce(obj_description({0}, 'pg_subscription'), '') AS description
                FROM pg_subscription
                WHERE oid = {0}
            '''.format(
                oid
            )
        ).Rows[0]

        return "COMMENT ON SUBSCRIPTION {0} is '{1}'".format(
            row['id'],
            row['description']
        )

    @lock_required
    def GetObjectDescriptionTable(self, oid):
        row = self.connection.Query(
            '''
                SELECT {0}::regclass AS id,
                       coalesce(obj_description({0}, 'pg_class'), '') AS description
            '''.format(
                oid
            )
        ).Rows[0]

        return "COMMENT ON TABLE {0} is '{1}'".format(
            row['id'],
            row['description']
        )

    @lock_required
    def GetObjectDescriptionTablespace(self, oid):
        row = self.connection.Query(
            '''
                SELECT quote_ident(spcname) AS id,
                       coalesce(shobj_description({0}, 'pg_tablespace'), '') AS description
                FROM pg_tablespace
                WHERE oid = {0}
            '''.format(
                oid
            )
        ).Rows[0]

        return "COMMENT ON TABLESPACE {0} is '{1}'".format(
            row['id'],
            row['description']
        )

    @lock_required
    def GetObjectDescriptionTrigger(self, oid):
        row = self.connection.Query(
            '''
                SELECT tgname AS id,
                       tgrelid::regclass AS table_id,
                       coalesce(obj_description({0}, 'pg_trigger'), '') AS description
                FROM pg_trigger
                WHERE oid = {0}
            '''.format(
                oid
            )
        ).Rows[0]

        return "COMMENT ON TRIGGER {0} ON {1} is '{2}'".format(
            row['id'],
            row['table_id'],
            row['description']
        )

    @lock_required
    def GetObjectDescriptionType(self, oid):
        row = self.connection.Query(
            '''
                SELECT '{0}'::regtype AS id,
                       coalesce(obj_description({0}, 'pg_type'), '') AS description
            '''.format(
                oid
            )
        ).Rows[0]

        return "COMMENT ON TYPE {0} is '{1}'".format(
            row['id'],
            row['description']
        )

    @lock_required
    def GetObjectDescriptionView(self, oid):
        row = self.connection.Query(
            '''
                SELECT {0}::regclass AS id,
                       coalesce(obj_description({0}, 'pg_class'), '') AS description
            '''.format(
                oid
            )
        ).Rows[0]

        return "COMMENT ON VIEW {0} is '{1}'".format(
            row['id'],
            row['description']
        )

    def GetObjectDescription(self, object_type, oid, position):
        if object_type == 'aggregate':
            return self.GetObjectDescriptionAggregate(oid)
        elif object_type == 'table_field':
            return self.GetObjectDescriptionTableField(oid, position)
        elif object_type in ['check', 'foreign_key', 'pk', 'unique', 'exclude']:
            return self.GetObjectDescriptionConstraint(oid)
        elif object_type == 'database':
            return self.GetObjectDescriptionDatabase(oid)
        elif object_type == 'domain':
            return self.GetObjectDescriptionDomain(oid)
        elif object_type == 'extension':
            return self.GetObjectDescriptionExtension(oid)
        elif object_type == 'event_trigger':
            return self.GetObjectDescriptionEventTrigger(oid)
        elif object_type == 'foreign_data_wrapper':
            return self.GetObjectDescriptionForeignDataWrapper(oid)
        elif object_type == 'foreign_server':
            return self.GetObjectDescriptionForeignServer(oid)
        elif object_type == 'foreign_table':
            return self.GetObjectDescriptionForeignTable(oid)
        elif object_type in ['function', 'trigger_function', 'direct_trigger_function', 'event_trigger_function', 'direct_event_trigger_function']:
            return self.GetObjectDescriptionFunction(oid)
        elif object_type == 'index':
            return self.GetObjectDescriptionIndex(oid)
        elif object_type == 'mview':
            return self.GetObjectDescriptionMaterializedView(oid)
        elif object_type == 'procedure':
            return self.GetObjectDescriptionProcedure(oid)
        elif object_type == 'publication':
            return self.GetObjectDescriptionPublication(oid)
        elif object_type == 'role':
            return self.GetObjectDescriptionRole(oid)
        elif object_type == 'rule':
            return self.GetObjectDescriptionRule(oid)
        elif object_type == 'schema':
            return self.GetObjectDescriptionSchema(oid)
        elif object_type == 'sequence':
            return self.GetObjectDescriptionSequence(oid)
        elif object_type == 'statistic':
            return self.GetObjectDescriptionStatistic(oid)
        elif object_type == 'subscription':
            return self.GetObjectDescriptionSubscription(oid)
        elif object_type == 'table':
            return self.GetObjectDescriptionTable(oid)
        elif object_type == 'tablespace':
            return self.GetObjectDescriptionTablespace(oid)
        elif object_type == 'trigger':
            return self.GetObjectDescriptionTrigger(oid)
        elif object_type == 'type':
            return self.GetObjectDescriptionType(oid)
        elif object_type == 'view':
            return self.GetObjectDescriptionView(oid)
        else:
            return ''
