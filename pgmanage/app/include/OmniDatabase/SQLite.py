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
from pathlib import Path
from collections import OrderedDict
from enum import Enum

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
SQLite
------------------------------------------------------------------------
'''
class SQLite:
    def __init__(self, service, conn_id=0, alias='', foreign_keys=True):
        self.alias = alias
        self.db_type = 'sqlite'
        self.conn_string = ''
        self.conn_id = conn_id
        self.server = ''
        self.port = ''
        self.service = service
        self.active_service = service
        self.user = ''
        self.active_user = ''
        self.schema = ''
        self.connection = Spartacus.Database.SQLite(service, foreign_keys)

        self.has_schema = False
        self.has_functions = False
        self.has_procedures = False
        self.has_packages = False
        self.has_sequences = False
        self.has_primary_keys = True
        self.has_foreign_keys = True
        self.has_uniques = True
        self.has_indexes = True
        self.has_checks = False
        self.has_excludes = False
        self.has_rules = False
        self.has_triggers = True
        self.has_partitions = True
        self.has_statistics = False

        self.has_update_rule = True
        self.can_rename_table = True
        self.rename_table_command = "alter table #p_table_name# rename to #p_new_table_name#"
        self.create_pk_command = "constraint #p_constraint_name# primary key (#p_columns#)"
        self.create_fk_command = "constraint #p_constraint_name# foreign key (#p_columns#) references #p_r_table_name# (#p_r_columns#) #p_delete_update_rules#"
        self.create_unique_command = "constraint #p_constraint_name# unique (#p_columns#)"
        self.can_alter_type = False
        self.can_alter_nullable = False
        self.can_rename_column = False
        self.can_add_column = True
        self.add_column_command = "alter table #p_table_name# add column #p_column_name# #p_data_type# #p_nullable#"
        self.can_drop_column = False
        self.can_add_constraint = False
        self.can_drop_constraint = False
        self.create_index_command = "create index #p_index_name# on #p_table_name# (#p_columns#)";
        self.create_unique_index_command = "create unique index #p_index_name# on #p_table_name# (#p_columns#)"
        self.drop_index_command = "drop index #p_index_name#"
        self.console_help = "Console tab."
        self.use_server_cursor = False
        self.version = ''
        self.version_num = ''

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

    @lock_required
    def GetVersion(self):
        self.version = self.connection.ExecuteScalar('SELECT sqlite_version()')
        splitted_version = self.version.split('.')
        self.version_num = '{0}{1}{2}'.format(
            splitted_version[0].zfill(2),
            splitted_version[1].zfill(2),
            splitted_version[2].zfill(2)
        )
        return 'SQLite ' + self.version

    def GetName(self):
        return self.service

    def PrintDatabaseInfo(self):
        if '/' in self.service:
            strings = self.service.split('/')
            return strings[len(strings)-1]
        else:
            return self.service

    def PrintDatabaseDetails(self):
        return 'Local File'

    def HandleUpdateDeleteRules(self, update_rule, delete_rule):
        rules = ''
        if update_rule.strip() != "":
            rules += " on update " + update_rule + " "
        if delete_rule.strip() != "":
            rules += " on delete " + delete_rule + " "
        return rules

    def TestConnection(self):
        message = ''
        status = False
        try:
            if Path(self.service).expanduser().is_file():
                self.connection.Query("PRAGMA schema_version;")
                message = 'Connection successful.'
                status = True
            else:
                message = 'File does not exist, if you try to manage this connection a database file will be created.'
        except Exception as exc:
            message = str(exc)
        return message, status

    @lock_required
    def QueryTables(self, *args):
        return self.connection.Query('''
            select name as table_name,
                quote(name) as name_raw
		    from sqlite_master
			where type = 'table'
            order by table_name ASC
        ''', True)

    @lock_required
    def QueryTablesFields(self, table_name=None, *args):
        table_columns_all = Spartacus.Database.DataTable()
        table_columns_all.Columns = [
            'column_name',
            'data_type',
            'nullable',
            'data_length',
            'data_precision',
            'data_scale',
            'table_name'
        ]
        if table_name:
            tables = Spartacus.Database.DataTable()
            tables.Columns.append('table_name')
            tables.Rows.append(OrderedDict(zip(tables.Columns, [table_name])))
        else:
            tables = self.connection.Query('''
                select name as table_name
                from sqlite_master
                where type = 'table'
                order by table_name ASC
                ''', True)
        for table in tables.Rows:
            quoted_table_name = '"{0}"'.format(table['table_name'].lstrip("\'").rstrip("\'"))
            table_columns_tmp = self.connection.Query('pragma table_info({0})'.format(quoted_table_name), True)
            table_columns = Spartacus.Database.DataTable()
            table_columns.Columns = [
                'column_name',
                'data_type',
                'nullable',
                'data_length',
                'data_precision',
                'data_scale',
                'table_name'
            ]
            for r in table_columns_tmp.Rows:
                row = []
                row.append(r['name'])
                if '(' in r['type']:
                    index = r['type'].find('(')
                    data_type = r['type'].lower()[0 : index]
                    if ',' in r['type']:
                        sizes = r['type'][index + 1 : r['type'].find(')')].split(',')
                        data_length = ''
                        data_precision = sizes[0]
                        data_scale = sizes[1]
                    else:
                        data_length = r['type'][index + 1 : r['type'].find(')')]
                        data_precision = ''
                        data_scale = ''
                else:
                    data_type = r['type'].lower()
                    data_length = ''
                    data_precision = ''
                    data_scale = ''
                row.append(data_type)
                if r['notnull'] == '1':
                    row.append('NO')
                else:
                    row.append('YES')
                row.append(data_length)
                row.append(data_precision)
                row.append(data_scale)
                row.append(table['table_name'])
                table_columns.Rows.append(OrderedDict(zip(table_columns.Columns, row)))
            table_columns_all.Merge(table_columns)
        return table_columns_all

    @lock_required
    def QueryTablesForeignKeys(self, table_name=None, *args):
        fks_all = Spartacus.Database.DataTable()
        fks_all.Columns = [
            'r_table_name',
            'table_name',
            'r_column_name',
            'column_name',
            'constraint_name',
            'update_rule',
            'delete_rule',
            'table_schema',
            'r_table_schema'
        ]
        if table_name:
            tables = Spartacus.Database.DataTable()
            tables.Columns.append('table_name')
            tables.Rows.append(OrderedDict(zip(tables.Columns, [table_name])))
        else:
            tables = self.connection.Query('''
                select name as table_name
                from sqlite_master
                where type = 'table'
                ''', True)

        for table in tables.Rows:
            fks_tmp = self.connection.Query("pragma foreign_key_list('{0}')".format(table['table_name']), True)
            fks = Spartacus.Database.DataTable()
            fks.Columns = [
                'r_table_name',
                'table_name',
                'r_column_name',
                'column_name',
                'constraint_name',
                'update_rule',
                'delete_rule',
                'table_schema',
                'r_table_schema'
            ]
            for r in fks_tmp.Rows:
                row = []
                row.append(r['table'])
                row.append(table['table_name'])
                row.append(r['to'])
                row.append(r['from'])
                row.append(table['table_name'] + '_fk_' + str(r['id']))
                row.append(r['on_update'])
                row.append(r['on_delete'])
                row.append('')
                row.append('')
                fks.Rows.append(OrderedDict(zip(fks.Columns, row)))
            fks_all.Merge(fks)
        return fks_all

    @lock_required
    def QueryTablesForeignKeysColumns(self, fkey, table_name=None, *args):
        fk = Spartacus.Database.DataTable()
        fk.Columns = [
            'r_table_name',
            'table_name',
            'r_column_name',
            'column_name',
            'constraint_name',
            'update_rule',
            'delete_rule',
            'table_schema',
            'r_table_schema'
        ]

        if table_name:
            q = "select * from pragma_foreign_key_list('{0}')".format(table_name)
        else:
            q = '''SELECT
                    m.name,
                    p.*
                    FROM
                        sqlite_master m
                        JOIN pragma_foreign_key_list(m.name) p
                    WHERE m.type = 'table'
                    ORDER BY m.name
                '''

        fkeys = fkey if isinstance(fkey, list) else [fkey]

        fks_tmp = self.connection.Query(q, True)
        for row in fks_tmp.Rows:
            constraint_name = row.get('name', table_name) + '_fk_' + str(row['id'])
            if constraint_name in fkeys:
                result_row = OrderedDict(zip(fk.Columns, [
                    row['table'],
                    row.get('name', table_name),
                    row['to'],
                    row['from'],
                    constraint_name,
                    row['on_update'],
                    row['on_delete'],
                    '',
                    ''
                ]))

                fk.Rows.append(result_row)

        return fk

    @lock_required
    def QueryTablesPrimaryKeys(self, table_name=None):
        pks_all = Spartacus.Database.DataTable()
        pks_all.Columns = [
            'constraint_name',
            'column_name',
            'table_name'
        ]
        if table_name:
            tables = Spartacus.Database.DataTable()
            tables.Columns.append('table_name')
            tables.Rows.append(OrderedDict(zip(tables.Columns, [table_name])))
        else:
            tables = self.QueryTables()
        for table in tables.Rows:
            pks_tmp = self.connection.Query("pragma table_info('{0}')".format(table['table_name']), True)
            pks = Spartacus.Database.DataTable()
            pks.Columns = [
                'constraint_name',
                'column_name',
                'table_name'
            ]
            for r in pks_tmp.Rows:
                if r['pk'] != '0':
                    row = []
                    row.append('pk_' + table['table_name'])
                    row.append(r['name'])
                    row.append(table['table_name'])
                    pks.Rows.append(OrderedDict(zip(pks.Columns, row)))
            pks_all.Merge(pks)
        return pks_all

    @lock_required
    def QueryTablesPrimaryKeysColumns(self, table=None):
        pk_tmp = self.connection.Query("pragma table_info('{0}')".format(table), True)

        pk = Spartacus.Database.DataTable()
        pk.Columns = ['column_name']

        for row in pk_tmp.Rows:
            if row['pk'] != '0':
                row = [row['name']]
                pk.Rows.append(OrderedDict(zip(pk.Columns, row)))

        return pk

    @lock_required
    def QueryTablesUniques(self, table_name=None):
        uniques_all = Spartacus.Database.DataTable()

        uniques_all.Columns = [
            'constraint_name',
            'table_name'
        ]

        if table_name:
            tables = self.connection.Query('''
                select name
                from sqlite_master
                where type = 'table'
                  and name = '{0}'
            '''.format(table_name), True)
        else:
            tables = self.connection.Query('''
                select name
                from sqlite_master
                where type = 'table'
            ''', True)

        for table in tables.Rows:
            uniques = self.connection.Query('''
                PRAGMA index_list('{0}')
            '''.format(
                table['name']
            ), True)

            for unique in uniques.Rows:
                if unique['origin'] == 'u':
                    uniques_all.AddRow([
                        unique['name'],
                        table['name']
                    ])

        return uniques_all

    @lock_required
    def QueryTablesUniquesColumns(self, unique_name, table_name=None):
        uniques_all = Spartacus.Database.DataTable()

        uniques_all.Columns = [
            'constraint_name',
            'column_name',
            'table_name'
        ]

        if table_name:
            tables = self.connection.Query('''
                select name
                from sqlite_master
                where type = 'table'
                  and name = '{0}'
            '''.format(table_name), True)
        else:
            tables = self.connection.Query('''
                select name
                from sqlite_master
                where type = 'table'
            ''', True)

        for table in tables.Rows:
            uniques = self.connection.Query('''
                PRAGMA index_list('{0}')
            '''.format(
                table['name']
            ), True)

            for unique in uniques.Rows:
                if unique['origin'] == 'u':
                    if unique['name'] == unique_name:
                        unique_columns = self.connection.Query('''
                            PRAGMA index_info('{0}')
                        '''.format(
                            unique['name']
                        ), True)

                        for unique_column in unique_columns.Rows:
                            uniques_all.AddRow([
                                unique['name'],
                                unique_column['name'],
                                table['name']
                            ])

        return uniques_all

    @lock_required
    def QueryTablesIndexes(self, table_name=None):
        indexes_all = Spartacus.Database.DataTable()

        indexes_all.Columns = [
            "index_name",
            "table_name",
            "unique",
            "is_primary",
            "columns",
            "constraint",
        ]

        if table_name:
            tables = self.connection.Query(
                """
                select name
                from sqlite_master
                where type = 'table'
                  and name = '{0}'
            """.format(
                    table_name
                ),
                True,
            )
        else:
            tables = self.connection.Query(
                """
                select name
                from sqlite_master
                where type = 'table'
            """,
                True,
            )

        for table in tables.Rows:
            indexes = self.connection.Query(
                """
                PRAGMA index_list('{0}')
            """.format(
                    table["name"]
                ),
                True,
            )

            for index in indexes.Rows:
                if index["origin"] == "c":
                    # Get columns associated with the index
                    index_columns = self.connection.Query(
                        """
                        PRAGMA index_info('{0}')
                    """.format(
                            index["name"]
                        ),
                        True,
                    )

                    # Collect column names
                    column_names = [col["name"] for col in index_columns.Rows]

                    create_stmt = self.connection.Query(
                        """
                        SELECT sql
                        FROM sqlite_master
                        WHERE type = 'index'
                        AND name = '{0}'
                    """.format(
                            index["name"]
                        ),
                        True,
                    )

                    constraint = None
                    if create_stmt.Rows and "WHERE" in create_stmt.Rows[0]["sql"]:
                        constraint = (
                            create_stmt.Rows[0]["sql"].split("WHERE", 1)[1].strip()
                        )

                    indexes_all.AddRow(
                        [
                            index["name"],
                            table["name"],
                            index["unique"] == "1",
                            index["origin"] == "pk",
                            column_names,
                            constraint,
                        ]
                    )

        return indexes_all

    @lock_required
    def QueryTablesIndexesColumns(self, index_name, table_name=None):
        indexes_all = Spartacus.Database.DataTable()

        indexes_all.Columns = [
            'index_name',
            'column_name',
            'table_name'
        ]

        if table_name:
            tables = self.connection.Query('''
                select name
                from sqlite_master
                where type = 'table'
                  and name = '{0}'
            '''.format(table_name), True)
        else:
            tables = self.connection.Query('''
                select name
                from sqlite_master
                where type = 'table'
            ''', True)

        for table in tables.Rows:
            indexes = self.connection.Query('''
                PRAGMA index_list('{0}')
            '''.format(
                table['name']
            ), True)

            for index in indexes.Rows:
                if index['origin'] == 'c':
                    if index['name'] == index_name:
                        index_columns = self.connection.Query('''
                            PRAGMA index_info('{0}')
                        '''.format(
                            index['name']
                        ), True)

                        for index_column in index_columns.Rows:
                            indexes_all.AddRow([
                                index['name'],
                                index_column['name'],
                                table['name']
                            ])

        return indexes_all

    @lock_required
    def QueryViews(self):
        return self.connection.Query('''
            select name as table_name,
                   quote(name) as name_raw
		    from sqlite_master
			where type = 'view'
            order by table_name ASC
        ''', True)

    @lock_required
    def QueryViewFields(self, table=None, all_schemas=False, schema=None):
        table_columns_all = Spartacus.Database.DataTable()
        table_columns_all.Columns = [
            'column_name',
            'data_type',
            'nullable',
            'data_length',
            'data_precision',
            'data_scale',
            'table_name'
        ]
        if table:
            tables = Spartacus.Database.DataTable()
            tables.Columns.append('table_name')
            tables.Rows.append(OrderedDict(zip(tables.Columns, [table])))
        else:
            tables = self.connection.Query('''
                select name as table_name
                from sqlite_master
                where type = 'view'
                order by table_name ASC
                ''', True)
        for table in tables.Rows:
            table_columns_tmp = self.connection.Query("pragma table_info({0})".format(table['table_name']), True)
            table_columns = Spartacus.Database.DataTable()
            table_columns.Columns = [
                'column_name',
                'data_type',
                'nullable',
                'data_length',
                'data_precision',
                'data_scale',
                'table_name'
            ]
            for r in table_columns_tmp.Rows:
                row = []
                row.append(r['name'])
                if '(' in r['type']:
                    index = r['type'].find('(')
                    data_type = r['type'].lower()[0 : index]
                    if ',' in r['type']:
                        sizes = r['type'][index + 1 : r['type'].find(')')].split(',')
                        data_length = ''
                        data_precision = sizes[0]
                        data_scale = sizes[1]
                    else:
                        data_length = r['type'][index + 1 : r['type'].find(')')]
                        data_precision = ''
                        data_scale = ''
                else:
                    data_type = r['type'].lower()
                    data_length = ''
                    data_precision = ''
                    data_scale = ''
                row.append(data_type)
                if r['notnull'] == '1':
                    row.append('NO')
                else:
                    row.append('YES')
                row.append(data_length)
                row.append(data_precision)
                row.append(data_scale)
                row.append(table['table_name'])
                table_columns.Rows.append(OrderedDict(zip(table_columns.Columns, row)))
            table_columns_all.Merge(table_columns)
        return table_columns_all

    @lock_required
    def QueryTablesTriggers(self, p_table=None):
        return self.connection.Query('''
            SELECT name AS trigger_name,
                   tbl_name AS table_name
            FROM sqlite_master
            WHERE type = 'trigger'
              AND tbl_name = '{0}'
        '''.format(
            p_table
        ), True)

    @lock_required
    def Execute(self, sql):
        return self.connection.Execute(sql)

    def TemplateSelect(self, p_table, p_kind):
        # table
        if p_kind == 't':
            sql = 'SELECT t.'
            fields = self.QueryTablesFields(p_table)

            if len(fields.Rows) > 0:
                sql += '\n     , t.'.join([r['column_name'] for r in fields.Rows])

            sql += "\nFROM '{0}' t".format(p_table)

            pk = self.QueryTablesPrimaryKeys(p_table)

            if len(pk.Rows) > 0:
                fields = self.QueryTablesPrimaryKeysColumns(p_table)

                if len(fields.Rows) > 0:
                    sql += '\nORDER BY t.'
                    sql += '\n       , t.'.join([r['column_name'] for r in fields.Rows])
        # view
        elif p_kind == 'v':
            sql = 'SELECT t.'
            fields = self.QueryViewFields(p_table)

            if len(fields.Rows) > 0:
                sql += '\n     , t.'.join([r['column_name'] for r in fields.Rows])

            sql += "\nFROM '{0}' t".format(p_table)

        return Template(sql)

    def TemplateInsert(self, table_name):
        fields = self.QueryTablesFields(table_name)

        if len(fields.Rows) > 0:
            sql = "INSERT INTO '{0}' (\n".format(table_name)
            pk = self.QueryTablesPrimaryKeys(table_name)

            if len(pk.Rows) > 0:
                table_pk_fields = self.QueryTablesPrimaryKeysColumns(table_name)
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

    def TemplateUpdate(self, table_name):
        fields = self.QueryTablesFields(table_name)

        if len(fields.Rows) > 0:
            sql = "UPDATE '{0}' \nSET ".format(table_name)
            pk = self.QueryTablesPrimaryKeys(table_name)

            if len(pk.Rows) > 0:
                table_pk_fields = self.QueryTablesPrimaryKeysColumns(table_name)
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
        else:
            sql = ''

        return Template(sql)

    @lock_required
    def QueryDataLimited(self, query, count=-1):
        if count != -1:
            self.connection.Open()
            data = self.connection.QueryBlock(query, count, True)
            self.connection.Close()
            return data
        return self.connection.Query(query, True)

    @lock_required
    def QueryTableRecords(self, column_list, table, query_filter, count=-1):
        limit = ''
        if count != -1:
            limit = ' limit ' + count
        return self.connection.Query('''
            select {0}
            from '{1}' t
            {2}
            {3}
        '''.format(
                column_list,
                table,
                query_filter,
                limit
            ), True
        )

    def TemplateCreateView(self):
        template = get_template("sqlite", "create_view")
        return template.template

    def TemplateDropView(self):
        template = get_template("sqlite", "drop_view")
        return template.template

    def TemplateCreateTable(self):
        template = get_template("sqlite", "create_table")
        return template.template

    def TemplateAlterTable(self):
        template = get_template("sqlite", "alter_table")
        return template.template

    def TemplateDropTable(self):
        template = get_template("sqlite", "drop_table")
        return template.template

    def TemplateCreateColumn(self):
        template = get_template("sqlite", "create_column")
        return template.template

    def TemplateCreateIndex(self):
        template = get_template("sqlite", "create_index")
        return template.template

    def TemplateReindex(self):
        template = get_template("sqlite", "reindex")
        return template.template

    def TemplateDropIndex(self):
        template = get_template("sqlite", "drop_index")
        return template.template

    def TemplateDelete(self):
        template = get_template("sqlite", "delete")
        return template.template

    def TemplateCreateTrigger(self):
        template = get_template("sqlite", "create_trigger")
        return template.template

    def TemplateDropTrigger(self):
        template = get_template("sqlite", "drop_trigger")
        return template.template

    def TemplateAlterTrigger(self):
        template = get_template("sqlite", "alter_trigger")
        return template.template

    def GetAutocompleteValues(self, p_columns, p_filter):
        return None

    def GetErrorPosition(self, p_error_message, sql_cmd):
        ret = None
        try:
            err_token = re.search('.*near "(.*)".*', p_error_message).group(1)
            if err_token:
                row = sql_cmd.count('\n', 0, sql_cmd.find(err_token)) + 1
                ret = {'row': row, 'col': 0}
        except AttributeError:
            pass

        return ret

    def GetPropertiesTable(self, p_object):
        return self.connection.Query('''
            SELECT type AS "Type",
                   name AS "Name",
                   rootpage AS "Root Page"
            FROM sqlite_master
            WHERE type = 'table'
              AND name = '{0}'
        '''.format(p_object))

    def GetPropertiesTableField(self, p_table, object_name):
        return self.connection.Query('''
            SELECT 'Column' AS "Type",
                   '{0}' AS "Name"
        '''.format(object_name))

    def GetPropertiesIndex(self, object_name):
        return self.connection.Query('''
            SELECT type AS "Type",
                   name AS "Name",
                   rootpage AS "Root Page"
            FROM sqlite_master
            WHERE type = 'index'
              AND name = '{0}'
        '''.format(object_name))

    def GetPropertiesView(self, object_name):
        return self.connection.Query('''
            SELECT type AS "Type",
                   name AS "Name",
                   rootpage AS "Root Page"
            FROM sqlite_master
            WHERE type = 'view'
              AND name = '{0}'
        '''.format(object_name))

    def GetPropertiesTrigger(self, table_name, object_name):
        return self.connection.Query('''
            SELECT type AS "Type",
                   name AS "Name",
                   rootpage AS "Root Page"
            FROM sqlite_master
            WHERE type = 'trigger'
              AND name = '{0}'
              AND tbl_name = '{1}'
        '''.format(object_name, table_name))

    def GetPropertiesPK(self, table_name, object_name):
        return self.connection.Query('''
            SELECT 'PK' AS "Type",
                   '{0}' AS "Name"
        '''.format(object_name))

    def GetPropertiesFK(self, table_name, object_name):
        return self.connection.Query('''
            SELECT 'FK' AS "Type",
                   '{0}' AS "Name"
        '''.format(object_name))

    def GetPropertiesUnique(self, table_name, object_name):
        return self.connection.Query('''
            SELECT 'Unique' AS "Type",
                   '{0}' AS "Name"
        '''.format(object_name))

    def GetProperties(self, p_table, p_object, p_type):
        try:
            if p_type == 'table':
                return self.GetPropertiesTable(p_object).Transpose('Property', 'Value')
            elif p_type == 'table_field':
                return self.GetPropertiesTableField(p_table, p_object).Transpose('Property', 'Value')
            elif p_type == 'index':
                return self.GetPropertiesIndex(p_object).Transpose('Property', 'Value')
            elif p_type == 'view':
                return self.GetPropertiesView(p_object).Transpose('Property', 'Value')
            elif p_type == 'trigger':
                return self.GetPropertiesTrigger(p_table, p_object).Transpose('Property', 'Value')
            elif p_type == 'pk':
                return self.GetPropertiesPK(p_table, p_object).Transpose('Property', 'Value')
            elif p_type == 'foreign_key':
                return self.GetPropertiesFK(p_table, p_object).Transpose('Property', 'Value')
            elif p_type == 'unique':
                return self.GetPropertiesUnique(p_table, p_object).Transpose('Property', 'Value')
            else:
                return None
        except Spartacus.Database.Exception as exc:
            if str(exc) == 'Can only transpose a table with a single row.':
                raise Exception('Object {0} does not exist anymore. Please refresh the tree view.'.format(p_object))
            raise exc

    def GetDDLTable(self, object_name):
        return self.connection.ExecuteScalar('''
            SELECT sql
            FROM sqlite_master
            WHERE type = 'table'
              AND name = '{0}'
        '''.format(object_name))

    def GetDDLIndex(self, object_name):
        return self.connection.ExecuteScalar('''
            SELECT sql
            FROM sqlite_master
            WHERE type = 'index'
              AND name = '{0}'
        '''.format(object_name))

    def GetDDLView(self, object_name):
        return self.connection.ExecuteScalar('''
            SELECT sql
            FROM sqlite_master
            WHERE type = 'view'
              AND name = '{0}'
        '''.format(object_name))

    def GetDDLTrigger(self, object_name, table_name):
        return self.connection.ExecuteScalar('''
            SELECT sql
            FROM sqlite_master
            WHERE type = 'trigger'
              AND name = '{0}'
              AND tbl_name = '{1}'
        '''.format(object_name, table_name))

    def GetDDL(self, table_name, object_name, object_type):
        if object_type == 'table':
            return self.GetDDLTable(object_name)
        elif object_type == 'index':
            return self.GetDDLIndex(object_name)
        elif object_type == 'view':
            return self.GetDDLView(object_name)
        elif object_type == 'trigger':
            return self.GetDDLTrigger(object_name, table_name)
        else:
            return ''

    @lock_required
    def QueryTableDefinition(self, table_name=None):
        return self.connection.Query("PRAGMA table_info('{0}')".format(table_name), False)

    @lock_required
    def GetViewDefinition(self, view):
        return self.connection.ExecuteScalar(f"SELECT sql from sqlite_master WHERE type = 'view' AND name = '{view}'")
