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

import re
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
MySQL
------------------------------------------------------------------------
'''
class MySQL:
    def __init__(self, server, port, service, user, password, conn_id=0, alias='', conn_string='', parse_conn_string = False, connection_params=None):
        self.lock = None
        self.connection_params = connection_params if connection_params else {}
        self.alias = alias
        self.db_type = 'mysql'
        self.conn_string = conn_string
        self.conn_string_error = ''
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
        if port is None or port == '':
            self.active_port = '3306'
        else:
            self.active_port = port

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


        self.connection = Spartacus.Database.MySQL(self.active_server, self.active_port, self.active_service, self.active_user, self.password, conn_string, connection_params=self.connection_params)

        self.has_schema = True
        self.has_functions = True
        self.has_procedures = True
        self.has_packages = False
        self.has_sequences = False
        self.has_primary_keys = True
        self.has_foreign_keys = True
        self.has_uniques = True
        self.has_indexes = True
        self.has_checks = False
        self.has_excludes = False
        self.has_rules = False
        self.has_triggers = False
        self.has_partitions = False
        self.has_statistics = False

        self.has_update_rule = True
        self.can_rename_table = True
        self.rename_table_command = "alter table #p_table_name# rename to #p_new_table_name#"
        self.create_pk_command = "constraint #p_constraint_name# primary key (#p_columns#)"
        self.create_fk_command = "constraint #p_constraint_name# foreign key (#p_columns#) references #p_r_table_name# (#p_r_columns#) #p_delete_update_rules#"
        self.create_unique_command = "constraint #p_constraint_name# unique (#p_columns#)"
        self.can_alter_type = True
        self.alter_type_command = "alter table #p_table_name# modify #p_column_name# #p_new_data_type#"
        self.can_alter_nullable = True
        self.set_nullable_command = "alter table #p_table_name# modify #p_column_name# null"
        self.drop_nullable_command = "alter table #p_table_name# modify #p_column_name# not null"
        self.can_rename_column = True
        self.rename_column_command = "alter table #p_table_name# rename column #p_column_name# to #p_new_column_name#"
        self.can_add_column = True
        self.add_column_command = "alter table #p_table_name# add #p_column_name# #p_data_type# #p_nullable#"
        self.can_drop_column = True
        self.drop_column_command = "alter table #p_table_name# drop column #p_column_name#"
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

        self.console_help = "Console tab. Type the commands in the editor below this box. \? to view command list."
        self.use_server_cursor = False

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

    def GetVersion(self):
        return 'MySQL ' + self.ExecuteScalar('select version()')

    def GetUserName(self):
        return self.user

    def GetUserSuper(self):
        try:
            super_user = self.ExecuteScalar('''
                select super_priv as "super_priv"
                from mysql.user
                where user = '{0}'
            '''.format(self.user))
            if super_user == 'Y':
                return True
            else:
                return False
        except Exception as exc:
            return False

    def PrintDatabaseInfo(self):
        if self.conn_string=='':
            return self.active_user + '@' + self.active_service
        else:
            return self.active_user + '@' + self.active_service

    def PrintDatabaseDetails(self):
        return self.active_server + ':' + self.active_port

    def HandleUpdateDeleteRules(self, update_rule, delete_rule):
        rules = ''
        if update_rule.strip() != '':
            rules += ' on update ' + update_rule + ' '
        if delete_rule.strip() != '':
            rules += ' on delete ' + delete_rule + ' '
        return rules

    def TestConnection(self):
        message = ''
        status = False
        if self.conn_string and self.conn_string_error!='':
            return self.conn_string_error, status

        try:
            self.connection.Open()
            self.connection.Close()
            message = 'Connection successful.'
            status = True
        except Exception as exc:
            message = str(exc)
        return message, status

    def GetErrorPosition(self, error_message, sql_cmd):
        ret = None
        try:
            row = re.search('.*\sat line (\d+)', error_message).group(1)
            ret = {'row': row, 'col': 0}
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

    @lock_required
    def Terminate(self, pid):
        return self.connection.Terminate(pid)

    def QueryRoles(self):
        return self.Query("""
            select concat('''',user,'''','@','''',host,'''') as "role_name"
            from mysql.user
            order by 1
        """, True)

    def QueryDatabases(self):
        return self.Query('show databases', True, True)

    def QuerySchemas(self):
        return self.connection.Query('select schema_name as schema_name from information_schema.schemata', True)

    def QueryTables(self, all_schemas=False, schema=None):
        query_filter = ''
        if not all_schemas:
            if schema:
                query_filter = "and table_schema = '{0}' ".format(schema)
            else:
                query_filter = "and table_schema = '{0}' ".format(self.schema)
        return self.Query('''
            select table_name as "table_name",
                   table_schema as "table_schema"
            from information_schema.tables
            where table_type in ('BASE TABLE', 'SYSTEM VIEW')
            {0}
            order by 2, 1
        '''.format(query_filter), True)

    def QueryTablesFields(self, table=None, all_schemas=False, schema=None):
        query_filter = ''
        if not all_schemas:
            if table and schema:
                query_filter = "and t.table_schema = '{0}' and t.table_name = '{1}' ".format(schema, table)
            elif table:
                query_filter = "and t.table_schema = '{0}' and t.table_name = '{1}' ".format(self.schema, table)
            elif schema:
                query_filter = "and t.table_schema = '{0}' ".format(schema)
            else:
                query_filter = "and t.table_schema = '{0}' ".format(self.schema)
        else:
            if table:
                query_filter = "and t.table_name = '{0}' ".format(table)
        return self.Query('''
            select distinct c.table_name as "table_name",
                   c.column_name as "column_name",
                   c.data_type as "data_type",
                   c.is_nullable as "nullable",
                   c.character_maximum_length as "data_length",
                   c.numeric_precision as "data_precision",
                   c.numeric_scale as "data_scale",
                   c.ordinal_position as "ordinal_position"
            from information_schema.columns c,
                 information_schema.tables t
            where t.table_name = c.table_name
              and t.table_type in ('BASE TABLE', 'SYSTEM VIEW')
            {0}
            order by c.table_name,
                     c.ordinal_position
        '''.format(query_filter), True)

    def QueryTablesForeignKeys(self, table=None, all_schemas=False, schema=None):
        query_filter = ''
        if not all_schemas:
            if table and schema:
                query_filter = "and i.table_schema = '{0}' and i.table_name = '{1}' ".format(schema, table)
            elif table:
                query_filter = "and i.table_schema = '{0}' and i.table_name = '{1}' ".format(self.schema, table)
            elif schema:
                query_filter = "and i.table_schema = '{0}' ".format(schema)
            else:
                query_filter = "and i.table_schema = '{0}' ".format(self.schema)
        else:
            if table:
                query_filter = "and i.table_name = '{0}' ".format(table)
        return self.Query('''
            select distinct i.constraint_name as "constraint_name",
                   i.table_name as "table_name",
                   k.referenced_table_name as "r_table_name",
                   k.column_name as "column_name",
                   k.referenced_column_name as "r_column_name",
                   k.table_schema as "table_schema",
                   k.referenced_table_schema as "r_table_schema",
                   r.update_rule as "update_rule",
                   r.delete_rule as "delete_rule"
            from information_schema.table_constraints i
            left join information_schema.key_column_usage k on i.constraint_name = k.constraint_name
            left join information_schema.referential_constraints r on i.constraint_name = r.constraint_name
            where i.constraint_type = 'FOREIGN KEY'
            {0}
            order by i.constraint_name,
                     i.table_name
        '''.format(query_filter), True)

    def QueryTablesForeignKeysColumns(self, fkey, table=None, all_schemas=False, schema=None):
        query_filter = ''
        if not all_schemas:
            if table and schema:
                query_filter = "and i.table_schema = '{0}' and i.table_name = '{1}' ".format(schema, table)
            elif table:
                query_filter = "and i.table_schema = '{0}' and i.table_name = '{1}' ".format(self.schema, table)
            elif schema:
                query_filter = "and i.table_schema = '{0}' ".format(schema)
            else:
                query_filter = "and i.table_schema = '{0}' ".format(self.schema)
        else:
            if table:
                query_filter = "and i.table_name = '{0}' ".format(table)

        if type(fkey) == list:
            fkeys = fkey
        else:
            fkeys = [fkey]

        fkey_list = ', '.join(list(f'\'{str(e)}\'' for e in fkeys))

        if fkey_list:
            query_filter = query_filter + "and i.constraint_name in ({0}) ".format(fkey_list)

        return self.Query('''
            select distinct i.constraint_name as "constraint_name",
                   i.table_name as "table_name",
                   k.referenced_table_name as "r_table_name",
                   k.column_name as "column_name",
                   k.referenced_column_name as "r_column_name",
                   k.table_schema as "table_schema",
                   k.referenced_table_schema as "r_table_schema",
                   r.update_rule as "update_rule",
                   r.delete_rule as "delete_rule",
                   k.ordinal_position as "ordinal_position"
            from information_schema.table_constraints i
            left join information_schema.key_column_usage k on i.constraint_name = k.constraint_name
            left join information_schema.referential_constraints r on i.constraint_name = r.constraint_name
            where i.constraint_type = 'FOREIGN KEY'
            {0}
            order by i.constraint_name,
                     i.table_name,
                     k.ordinal_position
        '''.format(query_filter), True)

    def QueryTablesPrimaryKeys(self, table=None, all_schemas=False, schema=None):
        query_filter = ''
        if not all_schemas:
            if table and schema:
                query_filter = "and t.table_schema = '{0}' and t.table_name = '{1}' ".format(schema, table)
            elif table:
                query_filter = "and t.table_schema = '{0}' and t.table_name = '{1}' ".format(self.schema, table)
            elif schema:
                query_filter = "and t.table_schema = '{0}' ".format(schema)
            else:
                query_filter = "and t.table_schema = '{0}' ".format(self.schema)
        else:
            if table:
                query_filter = "and t.table_name = '{0}' ".format(table)
        return self.Query('''
            select distinct concat('pk_', t.table_name) as "constraint_name",
                   t.table_name as "table_name",
                   t.table_schema as "table_schema"
            from information_schema.table_constraints t
            where t.constraint_type = 'PRIMARY KEY'
            {0}
            order by t.table_schema,
                     t.table_name
        '''.format(query_filter), True)

    def QueryTablesPrimaryKeysColumns(self, pkey, table=None, all_schemas=False, schema=None):
        query_filter = ''
        if not all_schemas:
            if table and schema:
                query_filter = "and t.table_schema = '{0}' and t.table_name = '{1}' ".format(schema, table)
            elif table:
                query_filter = "and t.table_schema = '{0}' and t.table_name = '{1}' ".format(self.schema, table)
            elif schema:
                query_filter = "and t.table_schema = '{0}' ".format(schema)
            else:
                query_filter = "and t.table_schema = '{0}' ".format(self.schema)
        else:
            if table:
                query_filter = "and t.table_name = '{0}' ".format(table)
        query_filter = "and concat('pk_', t.table_name) = '{0}' ".format(pkey)
        return self.Query('''
            select distinct k.column_name as "column_name",
                   k.ordinal_position as "ordinal_position"
            from information_schema.table_constraints t
            join information_schema.key_column_usage k
            using (constraint_name, table_schema, table_name)
            where t.constraint_type = 'PRIMARY KEY'
            {0}
            order by k.ordinal_position
        '''.format(query_filter), True)

    def QueryTablesUniques(self, table=None, all_schemas=False, schema=None):
        query_filter = ''
        if not all_schemas:
            if table and schema:
                query_filter = "and t.table_schema = '{0}' and t.table_name = '{1}' ".format(schema, table)
            elif table:
                query_filter = "and t.table_schema = '{0}' and t.table_name = '{1}' ".format(self.schema, table)
            elif schema:
                query_filter = "and t.table_schema = '{0}' ".format(schema)
            else:
                query_filter = "and t.table_schema = '{0}' ".format(self.schema)
        else:
            if table:
                query_filter = "and t.table_name = '{0}' ".format(table)
        return self.Query('''
            select distinct t.constraint_name as "constraint_name",
                   t.table_name as "table_name",
                   t.table_schema as "table_schema"
            from information_schema.table_constraints t
            where t.constraint_type = 'UNIQUE'
            {0}
            order by t.table_schema,
                     t.table_name
        '''.format(query_filter), True)

    def QueryTablesUniquesColumns(self, unique_name, table=None, all_schemas=False, schema=None):
        query_filter = ''
        if not all_schemas:
            if table and schema:
                query_filter = "and t.table_schema = '{0}' and t.table_name = '{1}' ".format(schema, table)
            elif table:
                query_filter = "and t.table_schema = '{0}' and t.table_name = '{1}' ".format(self.schema, table)
            elif schema:
                query_filter = "and t.table_schema = '{0}' ".format(schema)
            else:
                query_filter = "and t.table_schema = '{0}' ".format(self.schema)
        else:
            if table:
                query_filter = "and t.table_name = '{0}' ".format(table)
        query_filter = "and t.constraint_name = '{0}' ".format(unique_name)
        return self.Query('''
            select distinct k.column_name as "column_name",
                   k.ordinal_position as "ordinal_position"
            from information_schema.table_constraints t
            join information_schema.key_column_usage k
            using (constraint_name, table_schema, table_name)
            where t.constraint_type = 'UNIQUE'
            {0}
            order by k.ordinal_position
        '''.format(query_filter), True)

    def QueryTablesIndexes(self, table=None, all_schemas=False, schema=None):
        query_filter = ''
        if not all_schemas:
            if table and schema:
                query_filter = "and t.table_schema = '{0}' and t.table_name = '{1}' ".format(schema, table)
            elif table:
                query_filter = "and t.table_schema = '{0}' and t.table_name = '{1}' ".format(self.schema, table)
            elif schema:
                query_filter = "and t.table_schema = '{0}' ".format(schema)
            else:
                query_filter = "and t.table_schema = '{0}' ".format(self.schema)
        else:
            if table:
                query_filter = "and t.table_name = '{0}' ".format(table)
        return self.Query('''
            select t.table_schema as "schema_name",
                   t.table_name as "table_name",
                   t.index_name as "index_name",
                   case when t.non_unique = 1 then 'Non Unique' else 'Unique' end as "uniqueness",
                    JSON_ARRAYAGG(t.column_name) as columns,
                    case 
                        when tc.constraint_type = 'PRIMARY KEY' then 'TRUE' 
                        else 'FALSE' 
                    end as is_primary,
                    t.index_type AS index_type
            from information_schema.statistics t
            left join 
                information_schema.table_constraints tc
                ON t.table_schema = tc.table_schema 
                AND t.table_name = tc.table_name 
                AND t.index_name = tc.constraint_name
            where 1 = 1
            {0}
            GROUP BY t.table_schema, t.table_name, t.index_name, t.non_unique, tc.constraint_type, t.index_type
            ORDER BY t.table_schema, t.table_name, t.index_name;
        '''.format(query_filter), True)

    def QueryTablesIndexesColumns(self, index_name, table=None, all_schemas=False, schema=None):
        query_filter = ''
        if not all_schemas:
            if table and schema:
                query_filter = "and t.table_schema = '{0}' and t.table_name = '{1}' ".format(schema, table)
            elif table:
                query_filter = "and t.table_schema = '{0}' and t.table_name = '{1}' ".format(self.schema, table)
            elif schema:
                query_filter = "and t.table_schema = '{0}' ".format(schema)
            else:
                query_filter = "and t.table_schema = '{0}' ".format(self.schema)
        else:
            if table:
                query_filter = "and t.table_name = '{0}' ".format(table)
        query_filter += "and t.index_name = '{0}' ".format(index_name)
        return self.Query('''
            select distinct t.column_name as "column_name",
                   t.seq_in_index as "seq_in_index"
            from information_schema.statistics t
            where 1 = 1
            {0}
            order by t.seq_in_index
        '''.format(query_filter), True)

    def QueryDataLimited(self, query, count=-1):
        if count != -1:
            try:
                self.connection.Open()
                data = self.connection.QueryBlock('select * from ( {0} ) t limit {1}'.format(query, count), count, True, True)
                self.connection.Close()
                return data
            except Spartacus.Database.Exception as exc:
                try:
                    self.connection.Cancel()
                except:
                    pass
                raise exc
        else:
            return self.Query(query, True)

    def QueryTableRecords(self, column_list, table, schema, query_filter, count=-1):
        limit = ''
        if count != -1:
            limit = ' limit ' + count
        return self.Query('''
            select *
            from (
            select {0}
            from {1} t
            {2}
            ) t
            {3}
        '''.format(
                column_list,
                table,
                query_filter,
                limit
            ), True
        )

    def QueryFunctions(self, all_schemas=False, schema=None):
        query_filter = ''
        if not all_schemas:
            if schema:
                query_filter = "and t.routine_schema = '{0}' ".format(schema)
            else:
                query_filter = "and t.routine_schema = '{0}' ".format(self.schema)
        return self.Query('''
            select t.routine_schema as "schema_name",
                   t.routine_name as "id",
                   t.routine_name as "name"
            from information_schema.routines t
            where t.routine_type = 'FUNCTION'
            {0}
            order by 2
        '''.format(query_filter), True)

    def QueryFunctionFields(self, function_name, schema):
        if schema:
            schema_name = schema
        else:
            schema_name = self.schema
        return self.Query('''
            select 'O' as "type",
                   concat('returns ', t.data_type) as "name",
                   0 as "seq"
            from information_schema.routines t
            where t.routine_type = 'FUNCTION'
              and t.routine_schema = '{0}'
              and t.specific_name = '{1}'
            union
            select (case t.parameter_mode
                      when 'IN' then 'I'
                      when 'OUT' then 'O'
                      else 'R'
                    end) as "type",
                   concat(t.parameter_name, ' ', t.data_type) as "name",
                   t.ordinal_position+1 as "seq"
            from information_schema.parameters t
            where t.ordinal_position > 0
              and t.specific_schema = '{0}'
              and t.specific_name = '{1}'
            order by 3 desc
        '''.format(schema_name, function_name), True)

    def GetFunctionDefinition(self, function_name):
        body = '--DROP FUNCTION {0};\n'.format(function_name)
        body = body + self.Query('show create function {0}.{1}'.format(self.schema, function_name), True, True).Rows[0][2]
        return body

    def QueryProcedures(self, all_schemas=False, schema=None):
        query_filter = ''
        if not all_schemas:
            if schema:
                query_filter = "and t.routine_schema = '{0}' ".format(schema)
            else:
                query_filter = "and t.routine_schema = '{0}' ".format(self.schema)
        return self.Query('''
            select t.routine_schema as "schema_name",
                   t.routine_name as "id",
                   t.routine_name as "name"
            from information_schema.routines t
            where t.routine_type = 'PROCEDURE'
            {0}
            order by 2
        '''.format(query_filter), True)

    def QueryProcedureFields(self, procedure, schema):
        if schema:
            schema_name = schema
        else:
            schema_name = self.schema
        return self.Query('''
            select (case t.parameter_mode
                      when 'IN' then 'I'
                      when 'OUT' then 'O'
                      else 'R'
                    end) as "type",
                   concat(t.parameter_name, ' ', t.data_type) as "name",
                   t.ordinal_position+1 as "seq"
            from information_schema.parameters t
            where t.specific_schema = '{0}'
              and t.specific_name = '{1}'
            order by 3 desc
        '''.format(schema_name, procedure), True)

    def GetProcedureDefinition(self, procedure):
        body = '--DROP PROCEDURE {0};\n'.format(procedure)
        body = body + self.Query('show create procedure {0}.{1}'.format(self.schema, procedure), True, True).Rows[0][2]
        return body

    def QueryViews(self, all_schemas=False, schema=None):
        query_filter = ''
        if not all_schemas:
            if schema:
                query_filter = "and table_schema = '{0}' ".format(schema)
            else:
                query_filter = "and table_schema = '{0}' ".format(self.schema)
        return self.Query('''
            select table_name as "table_name",
                   table_schema as "table_schema"
            from information_schema.views
            where 1=1
            {0}
            order by 2, 1
        '''.format(query_filter), True)

    def QueryViewFields(self, table=None, all_schemas=False, schema=None):
        query_filter = ''
        if not all_schemas:
            if table and schema:
                query_filter = "and c.table_schema = '{0}' and c.table_name = '{1}' ".format(schema, table)
            elif table:
                query_filter = "and c.table_schema = '{0}' and c.table_name = '{1}' ".format(self.schema, table)
            elif schema:
                query_filter = "and c.table_schema = '{0}' ".format(schema)
            else:
                query_filter = "and c.table_schema = '{0}' ".format(self.schema)
        else:
            if table:
                query_filter = "and c.table_name = '{0}' ".format(table)
        return self.Query('''
            select distinct c.table_name as "table_name",
                   c.column_name as "column_name",
                   c.data_type as "data_type",
                   c.is_nullable as "nullable",
                   c.character_maximum_length as "data_length",
                   c.numeric_precision as "data_precision",
                   c.numeric_scale as "data_scale",
                   c.ordinal_position as "ordinal_position"
            from information_schema.columns c,
                 information_schema.tables t
            where t.table_name = c.table_name
              and t.table_type = 'VIEW'
            {0}
            order by c.table_name,
                     c.ordinal_position
        '''.format(query_filter), True)

    def GetViewDefinition(self, view, schema):
        if schema:
            schema_name = schema
        else:
            schema_name = self.schema
        return self.Query('show create view {0}.{1}'.format(schema_name, view), True, True).Rows[0][1]

    def TemplateCreateRole(self):
        template = get_template("mysql", "create_role")
        return template.template

    def TemplateAlterRole(self):
        template = get_template("mysql", "alter_role")
        return template.template

    def TemplateDropRole(self):
        template = get_template("mysql", "drop_role")
        return template.template

    def TemplateCreateDatabase(self):
        template = get_template("mysql", "create_database")
        return template.template

    def TemplateAlterDatabase(self):
        template = get_template("mysql", "alter_database")
        return template.template

    def TemplateDropDatabase(self):
        template = get_template("mysql", "drop_database")
        return template.template

    def TemplateCreateFunction(self):
        template = get_template("mysql", "create_function")
        return template.template

    def TemplateDropFunction(self):
        template = get_template("mysql", "drop_function")
        return template.template

    def TemplateCreateProcedure(self):
        template = get_template("mysql", "create_procedure")
        return template.template

    def TemplateDropProcedure(self):
        template = get_template("mysql", "drop_procedure")
        return template.template

    def TemplateCreateTable(self):
        template = get_template("mysql", "create_table")
        return template.template

    def TemplateAlterTable(self):
        template = get_template("mysql", "alter_table")
        return template.template

    def TemplateDropTable(self):
        template = get_template("mysql", "drop_table")
        return template.template

    def TemplateCreateColumn(self):
        template = get_template("mysql", "create_column")
        return template.template

    def TemplateAlterColumn(self):
        template = get_template("mysql", "alter_column")
        return template.template

    def TemplateDropColumn(self):
        template = get_template("mysql", "drop_column")
        return template.template

    def TemplateCreatePrimaryKey(self):
        template = get_template("mysql", "create_primarykey")
        return template.template

    def TemplateDropPrimaryKey(self):
        template = get_template("mysql", "drop_primarykey")
        return template.template

    def TemplateCreateUnique(self):
        template = get_template("mysql", "create_unique")
        return template.template

    def TemplateDropUnique(self):
        template = get_template("mysql", "drop_unique")
        return template.template

    def TemplateCreateForeignKey(self):
        template = get_template("mysql", "create_foreignkey")
        return template.template

    def TemplateDropForeignKey(self):
        template = get_template("mysql", "drop_foreignkey")
        return template.template

    def TemplateCreateIndex(self):
        template = get_template("mysql", "create_index")
        return template.template

    def TemplateDropIndex(self):
        template = get_template("mysql", "drop_index")
        return template.template

    def TemplateCreateView(self):
        template = get_template("mysql", "create_view")
        return template.template

    def TemplateDropView(self):
        template = get_template("mysql", "drop_view")
        return template.template

    def TemplateSelect(self, schema, table):
        sql = 'SELECT t.'
        fields = self.QueryTablesFields(table, False, schema)
        if len(fields.Rows) > 0:
            sql += '\n     , t.'.join([r['column_name'] for r in fields.Rows])
        sql += '\nFROM {0}.{1} t'.format(schema, table)
        pk = self.QueryTablesPrimaryKeys(table, False, schema)
        if len(pk.Rows) > 0:
            fields = self.QueryTablesPrimaryKeysColumns(pk.Rows[0]['constraint_name'], table, False, schema)
            if len(fields.Rows) > 0:
                sql += '\nORDER BY t.'
                sql += '\n       , t.'.join([r['column_name'] for r in fields.Rows])
        return Template(sql)

    def TemplateInsert(self, schema, table):
        fields = self.QueryTablesFields(table, False, schema)
        if len(fields.Rows) > 0:
            sql = 'INSERT INTO {0}.{1} (\n'.format(schema, table)
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
        else:
            sql = ''
        return Template(sql)

    def TemplateUpdate(self, schema, table):
        fields = self.QueryTablesFields(table, False, schema)
        if len(fields.Rows) > 0:
            sql = 'UPDATE {0}.{1}\nSET '.format(schema, table)
            pk = self.QueryTablesPrimaryKeys(table, False, schema)
            if len(pk.Rows) > 0:
                table_pk_fields = self.QueryTablesPrimaryKeysColumns(pk.Rows[0]['constraint_name'], table, False, schema)
                pk_fields = [r['column_name'] for r in table_pk_fields.Rows]
                values = []
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
                values = []
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
        else:
            sql = ''
        return Template(sql)

    def TemplateDelete(self):
        template = get_template("mysql", "delete")
        return template.template

    def GetProperties(self, schema, table, object_name, object_type):
        if object_type == 'table':
            return self.Query('''
                select table_schema as "Table Schema",
                       table_name as "Table Name",
                       table_type as "Table Type",
                       engine as "Engine",
                       version as "Version",
                       row_format as "Row Format",
                       table_rows as "Table Rows",
                       avg_row_length as "Average Row Length",
                       data_length as "Data Length",
                       max_data_length as "Max Data Length",
                       index_length as "Index Length",
                       data_free as "Data Free",
                       auto_increment as "Auto Increment",
                       create_time as "Create Time",
                       update_time as "Update Time",
                       check_time as "Check Time",
                       table_collation as "Table Collaction",
                       checksum as "Checksum"
                from information_schema.tables
                where table_schema = '{0}'
                  and table_name = '{1}'
            '''.format(schema, object_name), True).Transpose('Property', 'Value')
        elif object_type == 'view':
            return self.Query('''
                select table_schema as "View Schema",
                       table_name as "View Name",
                       check_option as "Check Option",
                       is_updatable as "Is Updatable",
                       security_type as "Security Type",
                       character_set_client as "Character Set Client",
                       collation_connection as "Collation Connection"
                from information_schema.views
                where table_schema = '{0}'
                  and table_name = '{1}'
            '''.format(schema, object_name), True).Transpose('Property', 'Value')
        elif object_type == 'function':
            return self.Query('''
                select routine_schema as "Routine Schema",
                       routine_name as "Routine Name",
                       routine_type as "Routine Type",
                       data_type as "Data Type",
                       character_maximum_length as "Character Maximum Length",
                       character_octet_length as "Character Octet Length",
                       numeric_precision as "Numeric Precision",
                       numeric_scale as "Numeric Scale",
                       datetime_precision as "Datetime Precision",
                       character_set_name as "Character Set Name",
                       collation_name as "Collation Name",
                       routine_body as "Routine Body",
                       external_name as "External Name",
                       external_language as "External Language",
                       parameter_style as "Parameter Style",
                       is_deterministic as "Is Deterministic",
                       sql_data_access as "SQL Data Access",
                       sql_path as "SQL Path",
                       security_type as "Security Type",
                       created as "Created",
                       last_altered as "Last Altered",
                       character_set_client as "Character Set Client",
                       collation_connection as "Collation Connection",
                       database_collation as "Database Collation"
                from information_schema.routines
                where routine_type = 'FUNCTION'
                  and routine_schema = '{0}'
                  and routine_name = '{1}'
            '''.format(schema, object_name), True).Transpose('Property', 'Value')
        elif object_type == 'procedure':
            return self.Query('''
                select routine_schema as "Routine Schema",
                       routine_name as "Routine Name",
                       routine_type as "Routine Type",
                       data_type as "Data Type",
                       character_maximum_length as "Character Maximum Length",
                       character_octet_length as "Character Octet Length",
                       numeric_precision as "Numeric Precision",
                       numeric_scale as "Numeric Scale",
                       datetime_precision as "Datetime Precision",
                       character_set_name as "Character Set Name",
                       collation_name as "Collation Name",
                       routine_body as "Routine Body",
                       external_name as "External Name",
                       external_language as "External Language",
                       parameter_style as "Parameter Style",
                       is_deterministic as "Is Deterministic",
                       sql_data_access as "SQL Data Access",
                       sql_path as "SQL Path",
                       security_type as "Security Type",
                       created as "Created",
                       last_altered as "Last Altered",
                       character_set_client as "Character Set Client",
                       collation_connection as "Collation Connection",
                       database_collation as "Database Collation"
                from information_schema.routines
                where routine_type = 'PROCEDURE'
                  and routine_schema = '{0}'
                  and routine_name = '{1}'
            '''.format(schema, object_name), True).Transpose('Property', 'Value')
        elif object_type == 'index':
            return self.Query('''SELECT
                        table_schema,
                        table_name,
                        index_name,
                        GROUP_CONCAT(column_name ORDER BY seq_in_index) AS columns,
                        GROUP_CONCAT(seq_in_index ORDER BY seq_in_index) AS seq_in_index_list,
                        GROUP_CONCAT(cardinality ORDER BY seq_in_index) AS cardinality_list,
                        GROUP_CONCAT(non_unique ORDER BY seq_in_index) AS non_unique,
                        GROUP_CONCAT(index_type ORDER BY seq_in_index) AS index_type
                    FROM information_schema.statistics
                    WHERE index_name = '{0}'
                    AND table_schema = '{1}'
                    AND table_name = '{2}'
                    GROUP BY table_schema, table_name, index_name'''.format(object_name, schema, table)).Transpose('Property', 'Value')
        else:
            return None

    def GetDDL(self, schema, table, object_name, object_type):
        if object_type == 'function' or object_type == 'procedure':
            return self.Query('show create {0} {1}.{2}'.format(object_type, schema, object_name), True, True).Rows[0][2]
        elif object_type in ["table", "view"]:
            return self.Query('show create {0} {1}.{2}'.format(object_type, schema, object_name), True, True).Rows[0][1]

    def GetAutocompleteValues(self, p_columns, p_filter):
        return None
    
    def QueryTableDefinition(self, table=None):
        return self.connection.Query("SHOW FULL COLUMNS FROM {0}".format(table), False)
