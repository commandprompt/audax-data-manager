"""
The MIT License (MIT)

Copyright (c) 2014-2019 William Ivanski

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
"""

import base64
import datetime
import decimal
import json
import math
import re
from abc import ABC, abstractmethod
from collections import OrderedDict
from pathlib import Path
from urllib.parse import urlparse

import app.include.Spartacus as Spartacus
from prettytable import PrettyTable, from_db_cursor

supported_rdbms = []

try:
    import sqlite3

    supported_rdbms.append("SQLite")
    supported_rdbms.append("Memory")
except ImportError:
    pass
try:
    import uuid

    import psycopg2
    import psycopg2.extras
    import sqlparse
    from pgspecial.help.commands import helpcommands as HelpCommands
    from pgspecial.main import PGSpecial

    supported_rdbms.append("PostgreSQL")
except ImportError:
    pass
try:
    import pymysql
    from pymysql.constants import CLIENT, ER

    supported_rdbms.append("MySQL")
    supported_rdbms.append("MariaDB")
except ImportError:
    pass
try:
    import fdb

    supported_rdbms.append("Firebird")
except ImportError:
    pass
try:
    import oracledb

    supported_rdbms.append("Oracle")
except ImportError:
    pass
try:
    import pymssql

    supported_rdbms.append("MSSQL")
except ImportError:
    pass
try:
    import ibm_db
    import ibm_db_dbi

    supported_rdbms.append("IBMDB2")
except ImportError:
    pass
try:
    import boto3

    supported_rdbms.append("RDSPostgreSQL")
except ImportError:
    pass


class Exception(Exception):
    pass


class InvalidPasswordException(Exception):
    pass


class DataTable(object):
    def __init__(self, name=None, alltypesstr=False, simple=False):
        self.Name = name
        self.Columns = []
        self.ColumnTypeCodes = []
        self.Rows = []
        self.AllTypesStr = alltypesstr
        self.Simple = simple

    def AddColumn(self, column_name):
        self.Columns.append(column_name)

    def AddColumnTypeCode(self, typecode):
        self.ColumnTypeCodes.append(typecode)

    def AddRow(self, row):
        if not self.Columns and row:
            raise Spartacus.Database.Exception(
                "Can not add row to a table with no columns."
            )

        if len(self.Columns) != len(row):
            raise Spartacus.Database.Exception(
                "Can not add row to a table with different columns."
            )

        if not isinstance(row, list):
            row = list(row)

        if self.AllTypesStr:
            row = [str(x) if x is not None else "" for x in row]

        self.Rows.append(
            row if self.Simple else OrderedDict(zip(self.Columns, row))
        )

    def Select(self, key, value):
        if not isinstance(key, list):
            key = [key]

        if not isinstance(value, list):
            value = [value]

        if len(key) == len(value):
            try:
                table = Spartacus.Database.DataTable(
                    None, alltypesstr=self.AllTypesStr, simple=self.Simple
                )
                for c in self.Columns:
                    table.AddColumn(c)
                if self.Simple:
                    key_tmp = key
                    key = []
                    for x in key_tmp:
                        k = 0
                        found = False
                        while not found and k < len(self.Columns):
                            if self.Columns[k] == x:
                                found = True
                                key.append(k)
                            else:
                                k = k + 1
                for r in self.Rows:
                    match = True
                    for k in range(len(key)):
                        if not self.Equal(r[key[k]], value[k]):
                            match = False
                    if match:
                        table.Rows.append(r)
                return table
            except Exception as exc:
                raise Spartacus.Database.Exception(str(exc))
        else:
            raise Spartacus.Database.Exception(
                "Can not select with different key-value dimension."
            )

    def Merge(self, datatable):
        if len(self.Columns) > 0 and len(datatable.Columns) > 0:
            if self.Columns == datatable.Columns:
                for r in datatable.Rows:
                    self.Rows.append(r)
            else:
                raise Spartacus.Database.Exception(
                    "Can not merge tables with different columns."
                )
        else:
            raise Spartacus.Database.Exception("Can not merge tables with no columns.")

    def Equal(self, val1, val2):
        def normalize(value):
            if isinstance(value, float):
                return decimal.Decimal(repr(value))
            return value
        a, b = normalize(val1), normalize(val2)

        if a is None and b == "":
            a = ""
        elif a == "" and b is None:
            b = ""
        return a == b

    def Compare(
        self,
        datatable,
        pkcols,
        status_colname,
        diff_colname,
        ordered=False,
        keep_equal=False,
        debug_updates=False,
    ):
        if len(self.Columns) > 0 and len(datatable.Columns) > 0:
            if self.Columns == datatable.Columns:
                table = DataTable()
                for c in self.Columns:
                    table.AddColumn(c)
                table.AddColumn(status_colname)
                table.AddColumn(diff_colname)
                pk_cols = []
                if len(pkcols) > 0:
                    for c in pkcols:
                        pk_cols.append(c)
                else:
                    for c in self.Columns:
                        pk_cols.append(c)
                if ordered:
                    k1 = 0
                    k2 = 0
                    while k1 < len(self.Rows) and k2 < len(datatable.Rows):
                        r1 = self.Rows[k1]
                        r2 = datatable.Rows[k2]
                        pklist1 = []
                        pklist2 = []
                        for pk_col in pk_cols:
                            pklist1.append(str(r1[pk_col]))
                            pklist2.append(str(r2[pk_col]))
                        pk1 = "_".join(pklist1)
                        pk2 = "_".join(pklist2)
                        if pk1 == pk2:
                            all_match = True
                            row = []
                            diff = []
                            for c in self.Columns:
                                if not self.Equal(r1[c], r2[c]):
                                    if debug_updates:
                                        row.append(
                                            "[{0}]({1}) --> [{2}]({3})".format(
                                                repr(r1[c]),
                                                type(r1[c]),
                                                repr(r2[c]),
                                                type(r2[c]),
                                            )
                                        )
                                    else:
                                        row.append(
                                            "{0} --> {1}".format(
                                                repr(r1[c]), repr(r2[c])
                                            )
                                        )
                                    diff.append(c)
                                    all_match = False
                                else:
                                    row.append(r1[c])
                            if all_match:
                                row.append("E")
                                row.append("")
                                if keep_equal:
                                    table.AddRow(row)
                            else:
                                row.append("U")
                                row.append(",".join(diff))
                                table.AddRow(row)
                            k1 = k1 + 1
                            k2 = k2 + 1
                        elif pk1 < pk2:
                            row = []
                            for c in self.Columns:
                                row.append(r1[c])
                            row.append("D")
                            row.append("")
                            table.AddRow(row)
                            k1 = k1 + 1
                        else:
                            row = []
                            for c in datatable.Columns:
                                row.append(r2[c])
                            row.append("I")
                            row.append("")
                            table.AddRow(row)
                            k2 = k2 + 1
                    while k1 < len(self.Rows):
                        r1 = self.Rows[k1]
                        row = []
                        for c in self.Columns:
                            row.append(r1[c])
                        row.append("D")
                        row.append("")
                        table.AddRow(row)
                        k1 = k1 + 1
                    while k2 < len(datatable.Rows):
                        r2 = datatable.Rows[k2]
                        row = []
                        for c in datatable.Columns:
                            row.append(r2[c])
                        row.append("I")
                        row.append("")
                        table.AddRow(row)
                        k2 = k2 + 1
                else:
                    for r1 in self.Rows:
                        pk_match = False
                        for r2 in datatable.Rows:
                            pk_match = True
                            for pk_col in pk_cols:
                                if not self.Equal(r1[pk_col], r2[pk_col]):
                                    pk_match = False
                                    break
                            if pk_match:
                                break
                        if pk_match:
                            all_match = True
                            row = []
                            diff = []
                            for c in self.Columns:
                                if not self.Equal(r1[c], r2[c]):
                                    row.append("{0} --> {1}".format(r1[c], r2[c]))
                                    diff.append(c)
                                    all_match = False
                                else:
                                    row.append(r1[c])
                            if all_match:
                                row.append("E")
                                row.append("")
                                if keep_equal:
                                    table.AddRow(row)
                            else:
                                row.append("U")
                                row.append(",".join(diff))
                                table.AddRow(row)
                        else:
                            row = []
                            for c in self.Columns:
                                row.append(r1[c])
                            row.append("D")
                            row.append("")
                            table.AddRow(row)
                    for r2 in datatable.Rows:
                        pk_match = False
                        for r1 in self.Rows:
                            pk_match = True
                            for pk_col in pk_cols:
                                if not self.Equal(r1[pk_col], r2[pk_col]):
                                    pk_match = False
                                    break
                            if pk_match:
                                break
                        if not pk_match:
                            row = []
                            for c in datatable.Columns:
                                row.append(r2[c])
                            row.append("I")
                            row.append("")
                            table.AddRow(row)
                return table
            else:
                raise Spartacus.Database.Exception(
                    "Can not compare tables with different columns."
                )
        else:
            raise Spartacus.Database.Exception(
                "Can not compare tables with no columns."
            )

    def Jsonify(self):
        if self.Simple:
            if len(self.Rows) > 0:
                if isinstance(self.Rows[0], OrderedDict):
                    return json.dumps(self.Rows)
                else:
                    table = []
                    for r in self.Rows:
                        row = []
                        for c in range(0, len(self.Columns)):
                            row.append(r[c])
                        table.append(OrderedDict(zip(self.Columns, tuple(row))))
                    return json.dumps(table)
            else:
                return json.dumps(self.Rows)
        else:
            if len(self.Rows) > 0:
                if isinstance(self.Rows[0], OrderedDict):
                    return json.dumps(self.Rows)
                else:
                    table = []
                    for r in self.Rows:
                        row = []
                        for c in self.Columns:
                            row.append(r[c])
                        table.append(OrderedDict(zip(self.Columns, tuple(row))))
                    return json.dumps(table)
            else:
                return json.dumps(self.Rows)

    def Pretty(self, transpose=False):
        if self.Simple:
            if transpose:
                maxc = 0
                for c in self.Columns:
                    if len(c) > maxc:
                        maxc = len(c)
                if maxc < (14 + len(str(len(self.Rows)))):
                    maxc = 14 + len(str(len(self.Rows)))
                else:
                    maxc = maxc + 1
                k = 0
                s = 0
                maxf = 0
                for r in self.Rows:
                    for c in range(0, len(self.Columns)):
                        for snippet in str(r[c]).split("\n"):
                            k = k + 1
                            s = s + len(snippet)
                            if len(str(r[c])) > maxf:
                                maxf = len(snippet)
                if maxf > 30:
                    maxf = int(s / k) + int((maxf - int(s / k)) / 2)
                maxf = maxf + 10
                return_string = ""
                row = 1
                for r in self.Rows:
                    aux = "-[ RECORD {0} ]".format(row)
                    for k in range(len(aux), maxc):
                        aux = aux + "-"
                    return_string = return_string + aux + "+"
                    for k in range(0, maxf):
                        return_string = return_string + "-"
                    return_string = return_string + "\n"
                    for c in range(0, len(self.Columns)):
                        first = True
                        for snippet in str(r[c]).split("\n"):
                            n = math.ceil(len(snippet) / (maxf - 2))
                            j = 0
                            for i in range(0, n):
                                if first:
                                    x = self.Columns[c].ljust(maxc)
                                    first = False
                                else:
                                    x = " ".ljust(maxc)
                                if i < n - 1:
                                    y = " " + snippet[j : j + maxf - 2] + "+"
                                    j = j + maxf - 2
                                else:
                                    y = " " + snippet[j:]
                                return_string = return_string + "{0}|{1}\n".format(x, y)
                    row = row + 1
                return return_string
            else:
                table = PrettyTable()
                table.field_names = self.Columns
                table.align = "l"
                table.add_rows(self.Rows)
                table_string = table.get_string()
                return table_string
        else:
            if transpose:
                maxc = 0
                for c in self.Columns:
                    if len(c) > maxc:
                        maxc = len(c)
                if maxc < (14 + len(str(len(self.Rows)))):
                    maxc = 14 + len(str(len(self.Rows)))
                else:
                    maxc = maxc + 1
                k = 0
                s = 0
                maxf = 0
                for r in self.Rows:
                    for c in self.Columns:
                        for snippet in str(r[c]).split("\n"):
                            k = k + 1
                            s = s + len(snippet)
                            if len(str(r[c])) > maxf:
                                maxf = len(snippet)
                if maxf > 30:
                    maxf = int(s / k) + int((maxf - int(s / k)) / 2)
                maxf = maxf + 10
                return_string = ""
                row = 1
                for r in self.Rows:
                    aux = "-[ RECORD {0} ]".format(row)
                    for k in range(len(aux), maxc):
                        aux = aux + "-"
                    return_string = return_string + aux + "+"
                    for k in range(0, maxf):
                        return_string = return_string + "-"
                    return_string = return_string + "\n"
                    for c in self.Columns:
                        first = True
                        for snippet in str(r[c]).split("\n"):
                            n = math.ceil(len(snippet) / (maxf - 2))
                            j = 0
                            for i in range(0, n):
                                if first:
                                    x = c.ljust(maxc)
                                    first = False
                                else:
                                    x = " ".ljust(maxc)
                                if i < n - 1:
                                    y = " " + snippet[j : j + maxf - 2] + "+"
                                    j = j + maxf - 2
                                else:
                                    y = " " + snippet[j:]
                                return_string = return_string + "{0}|{1}\n".format(x, y)
                    row = row + 1
                return return_string
            else:
                table = PrettyTable()
                table.field_names = self.Columns
                table.align = "l"
                table.add_rows(self.Rows)
                table_string = table.get_string()
                return table_string

    def Transpose(self, column_1, column_2):
        if len(self.Rows) == 1:
            table = Spartacus.Database.DataTable()
            table.AddColumn(column_1)
            table.AddColumn(column_2)
            if self.Simple:
                for k in range(len(self.Columns)):
                    table.AddRow([self.Columns[k], self.Rows[0][k]])
            else:
                for c in self.Columns:
                    table.AddRow([c, self.Rows[0][c]])
            return table
        else:
            raise Spartacus.Database.Exception(
                "Can only transpose a table with a single row."
            )

    def Distinct(self, pkcols):
        table = Spartacus.Database.DataTable(
            None, alltypesstr=self.AllTypesStr, simple=self.Simple
        )
        for c in self.Columns:
            table.AddColumn(c)
        a = 0
        for r in self.Rows:
            value = []
            if self.Simple:
                for x in pkcols:
                    k = 0
                    found = False
                    while not found and k < len(self.Columns):
                        if self.Columns[k] == x:
                            found = True
                            value.append(r[k])
                        else:
                            k = k + 1
            else:
                for x in pkcols:
                    value.append(r[x])
            tmp = table.Select(pkcols, value)
            if len(tmp.Rows) == 0:
                table.AddRow(r)
            a = a + 1
        return table


class DataField(object):
    def __init__(self, name, field_type=None, db_type=None, mask="#"):
        self.name = name
        self.truename = name
        self.type = field_type
        self.dbtype = db_type
        self.mask = mask


class DataTransferReturn(object):
    def __init__(self):
        self.numrecords = 0
        self.log = None


class DataList(object):
    def __init__(self):
        self.list = []

    def append(self, item):
        self.list.append(item)


"""
------------------------------------------------------------------------
Generic
------------------------------------------------------------------------
"""


class Generic(ABC):
    @abstractmethod
    def GetConnectionString(self):
        pass

    @abstractmethod
    def Open(self, autocommit=True):
        pass

    @abstractmethod
    def Query(self, sql, alltypesstr=False, simple=False):
        pass

    @abstractmethod
    def Execute(self, sql):
        pass

    @abstractmethod
    def ExecuteScalar(self, sql):
        pass

    @abstractmethod
    def Close(self, commit=True):
        pass

    @abstractmethod
    def Commit(self):
        pass

    @abstractmethod
    def Rollback(self):
        pass

    @abstractmethod
    def Cancel(self, usesameconn=True, keep_connection=False):
        pass

    @abstractmethod
    def GetPID(self):
        pass

    @abstractmethod
    def Terminate(self, pid):
        pass

    @abstractmethod
    def GetFields(self, sql):
        pass

    @abstractmethod
    def GetNotices(self):
        pass

    @abstractmethod
    def ClearNotices(self):
        pass

    @abstractmethod
    def GetStatus(self):
        pass

    @abstractmethod
    def GetRowsAffected(self):
        pass

    @abstractmethod
    def GetConStatus(self):
        pass

    @abstractmethod
    def QueryBlock(self, sql, blocksize, alltypesstr=False, simple=False):
        pass

    @abstractmethod
    def InsertBlock(self, block, tablename, fields=None):
        pass

    @abstractmethod
    def Special(self, sql):
        pass

    def String(self, value):
        if type(value) == type(list()):
            ret = self.MogrifyArray(value)
        elif type(value) == memoryview:
            ret = base64.b64encode(value.tobytes()).decode()
        else:
            ret = str(value)
        return ret

    def MogrifyValue(self, value):
        if type(value) == type(list()):
            ret = self.MogrifyArray(value)
        elif type(value) == type(None):
            ret = "null"
        elif type(value) == type(str()):
            ret = "'{0}'".format(value.replace("'", "''"))
        elif type(value) == datetime.datetime:
            ret = "'{0}'".format(value)
        else:
            ret = "{0}".format(value)
        return ret

    def MogrifyArray(self, array):
        ret = "{"
        if len(array) > 0:
            ret = ret + self.MogrifyArrayValue(array[0])
            for i in range(1, len(array)):
                ret = ret + ", " + self.MogrifyArrayValue(array[i])
        ret = ret + "}"
        return ret

    def MogrifyArrayValue(self, value):
        if type(value) == type(list()):
            ret = self.MogrifyArray(value)
        elif type(value) == type(None):
            ret = "null"
        elif type(value) == type(str()):
            ret = '"{0}"'.format(value.replace('"', '""'))
        elif type(value) == datetime.datetime:
            ret = '"{0}"'.format(value)
        else:
            ret = "{0}".format(value)
        return ret

    def Mogrify(self, row, fields):
        if len(row) == len(fields):
            mog = []
            for k in range(0, len(row)):
                mog.append(
                    fields[k].mask.replace(
                        "#", self.MogrifyValue(row[fields[k].name])
                    )
                )
            return "(" + ",".join(mog) + ")"
        else:
            raise Spartacus.Database.Exception(
                "Can not mogrify with different number of parameters."
            )

    def Transfer(
        self,
        sql=None,
        table=None,
        target_database=None,
        tablename=None,
        blocksize=1000,
        fields=None,
        alltypesstr=False,
    ):
        """Method used to transfer data from one database to another one.

        Args:
            sql (str): the sql query to be executed in the current database, in order to provide data to be inserted into target database. Defaults to None.
            table (Spartacus.Database.DataTable): the data table containing data to be inserted into target database. Defaults to None.
            target_database (Spartacus.Database.Generic): any object that inherits from Spartacus.Database.Generic. It is the target database connection. Defaults to None.
            tablename (str): the target table name. Defaults to None.
            blocksize (int): number of rows to be read at a time from source database. Defaults to 1000.
            fields (list): list of fields to be considered while inserting into target database table. Defaults to None.
            alltypesstr (bool): if all fields should be queried as str instances.

        Notes:
            Either sql or table must be provided. If sql is provided, a query will be executed in source database. Otherwise, will use table data.
            tablename may also contain schema name, if target database supports it, e.g., 'my_schema.my_table'.
            blocksize and alltypesstr are used just in case of sql being used too.
            If fields is None, will consider all target table columns while transfering data.

        Returns:
            Spartacus.Database.DataTransferReturn.

        Raises:
            Spartacus.Database.Exception.
        """

        if sql is None and table is None:
            raise Spartacus.Database.Exception(
                "Either sql or table parameter must be provided."
            )
        data = DataTransferReturn()
        try:
            table = (
                self.QueryBlock(sql, blocksize, alltypesstr)
                if sql is not None
                else table
            )
            if len(table.Rows) > 0:
                target_database.InsertBlock(table, tablename, fields)
            data.numrecords = len(table.Rows)
            data.hasmorerecords = not self.start
        except Spartacus.Database.Exception as exc:
            data.log = str(exc)
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))
        return data

    def GetIdentifiersDML(sql):
        try:
            dict_object = {"all": [], "readonly": [], "writeonly": [], "readwrite": []}
            statement = sqlparse.split(sql)
            analysis = sqlparse.parse(sql)
            if len(statement) == len(analysis):
                for i in range(0, len(statement)):
                    next_is_into = False
                    next_is_from = False
                    next_is_read_table = False
                    next_is_write_table = False
                    for token in analysis[i].flatten():
                        if token.ttype != sqlparse.tokens.Token.Text.Whitespace:
                            if next_is_into:
                                next_is_write_table = True
                                next_is_into = False
                            elif next_is_from:
                                next_is_write_table = True
                                next_is_from = False
                            elif next_is_read_table:
                                dict_object["readonly"].append(token.value)
                                next_is_read_table = False
                            elif next_is_write_table:
                                dict_object["writeonly"].append(token.value)
                                next_is_write_table = False
                            elif token.is_keyword and token.value.lower() in [
                                "from",
                                "join",
                                "inner join",
                                "left join",
                                "left outer join",
                                "right join",
                                "right outer join",
                                "full join",
                                "full outer join",
                                "cross join",
                                "natural join",
                            ]:
                                next_is_read_table = True
                            elif (
                                token.is_keyword and token.value.lower() == "insert"
                            ):
                                next_is_into = True
                            elif (
                                token.is_keyword and token.value.lower() == "delete"
                            ):
                                next_is_from = True
                            elif (
                                token.is_keyword and token.value.lower() == "update"
                            ):
                                next_is_write_table = True
                            elif (
                                token.is_keyword
                                and token.value.lower() == "truncate"
                            ):
                                next_is_write_table = True
            dict_object["readonly"] = list(dict.fromkeys(dict_object["readonly"]))
            dict_object["writeonly"] = list(dict.fromkeys(dict_object["writeonly"]))
            dict_object["readwrite"] = list(
                dict.fromkeys(
                    [
                        value
                        for value in dict_object["readonly"]
                        if value in dict_object["writeonly"]
                    ]
                    + [
                        value
                        for value in dict_object["writeonly"]
                        if value in dict_object["readonly"]
                    ]
                )
            )
            for value in dict_object["readwrite"]:
                dict_object["readonly"].remove(value)
                dict_object["writeonly"].remove(value)
            dict_object["all"] = list(
                dict.fromkeys(
                    dict_object["readonly"] + dict_object["writeonly"] + dict_object["readwrite"]
                )
            )
            for k in list(dict_object.keys()):
                dict_object[k].sort()
            return dict_object
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def GetIdentifiersDDL(sql):
        try:
            dict_object = {"all": [], "create": [], "alter": [], "drop": []}
            statement = sqlparse.split(sql)
            analysis = sqlparse.parse(sql)
            if len(statement) == len(analysis):
                for i in range(0, len(statement)):
                    identifier_type = analysis[i].get_type()
                    obj_type = None
                    next_is_class = False
                    next_is_object = False
                    if identifier_type in ["CREATE", "CREATE OR REPLACE", "ALTER", "DROP"]:
                        for token in analysis[i].flatten():
                            if token.ttype != sqlparse.tokens.Token.Text.Whitespace:
                                if (
                                    token.is_keyword
                                    and token.value.upper() == identifier_type
                                ):
                                    next_is_class = True
                                elif next_is_class:
                                    obj_type = token.value.lower()
                                    next_is_class = False
                                    next_is_object = True
                                elif next_is_object:
                                    if identifier_type == "CREATE OR REPLACE":
                                        dict_object["create"].append(
                                            (obj_type, token.value)
                                        )
                                    else:
                                        dict_object[identifier_type.lower()].append(
                                            (obj_type, token.value)
                                        )
                                    if obj_type in dict_object:
                                        dict_object[obj_type].append(token.value)
                                    else:
                                        dict_object[obj_type] = [token.value]
                                    next_is_object = False
            dict_object["create"] = list(dict.fromkeys(dict_object["create"]))
            dict_object["alter"] = list(dict.fromkeys(dict_object["alter"]))
            dict_object["drop"] = list(dict.fromkeys(dict_object["drop"]))
            dict_object["all"] = list(
                dict.fromkeys(dict_object["create"] + dict_object["alter"] + dict_object["drop"])
            )
            for k in list(dict_object.keys()):
                dict_object[k].sort()
            return dict_object
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))


"""
------------------------------------------------------------------------
SQLite
------------------------------------------------------------------------
"""


class SQLite(Generic):
    def __init__(self, service, foreign_keys=True, timeout=30, encoding=None):
        if "SQLite" in supported_rdbms:
            self.host = None
            self.port = None
            self.service = service
            self.user = None
            self.password = ""
            self.con = None
            self.cur = None
            self.foreign_keys = foreign_keys
            self.timeout = timeout
            self.encoding = encoding
        else:
            raise Spartacus.Database.Exception(
                "SQLite is not supported. Please install it."
            )

    def GetConnectionString(self):
        return None

    def Open(self, autocommit=True):
        try:
            full_path = Path(self.service).expanduser()
            if autocommit:
                self.con = sqlite3.connect(
                    full_path,
                    self.timeout,
                    isolation_level=None,
                    check_same_thread=False,
                )
            else:
                self.con = sqlite3.connect(
                    full_path, self.timeout, check_same_thread=False
                )
            # self.con.row_factory = sqlite3.Row
            self.cur = self.con.cursor()
            if self.foreign_keys:
                self.cur.execute("PRAGMA foreign_keys = ON")
            self.start = True
        except sqlite3.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def Query(self, sql, alltypesstr=False, simple=False):
        try:
            keep = None
            if self.con is None:
                self.Open()
                keep = False
            else:
                keep = True
            self.cur.execute(sql)
            table = DataTable(None, alltypesstr, simple)
            if self.cur.description:
                for c in self.cur.description:
                    table.AddColumn(c[0])
                row = self.cur.fetchone()
                while row is not None:
                    table.AddRow(list(row))
                    row = self.cur.fetchone()
            return table
        except Spartacus.Database.Exception as exc:
            raise exc
        except sqlite3.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))
        finally:
            if not keep:
                self.Close()

    def Execute(self, sql):
        try:
            keep = None
            if self.con is None:
                self.Open()
                keep = False
            else:
                keep = True

            self.cur.execute(sql)
        except Spartacus.Database.Exception as exc:
            raise exc
        except sqlite3.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))
        finally:
            if not keep:
                self.Close()

    def ExecuteScalar(self, sql):
        try:
            keep = None
            if self.con is None:
                self.Open()
                keep = False
            else:
                keep = True
            self.cur.execute(sql)
            r = self.cur.fetchone()
            if r != None:
                s = r[0]
            else:
                s = None
            return s
        except Spartacus.Database.Exception as exc:
            raise exc
        except sqlite3.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))
        finally:
            if not keep:
                self.Close()

    def Close(self, commit=True):
        try:
            if self.con:
                self.con.commit()
                if self.cur:
                    self.cur.close()
                    self.cur = None
                self.con.close()
                self.con = None
        except sqlite3.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def Commit(self):
        self.Close(True)

    def Rollback(self):
        self.Close(False)

    def Cancel(self, usesameconn=True, keep_connection=False):
        try:
            if self.con:
                self.con.cancel()
                if self.cur:
                    self.cur.close()
                    self.cur = None
                self.con.close()
                self.con = None
        except sqlite3.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def GetPID(self):
        return None

    def Terminate(self, pid):
        pass

    def GetFields(self, sql):
        try:
            keep = None
            if self.con is None:
                self.Open()
                keep = False
            else:
                keep = True
            fields = []
            self.cur.execute("select * from ( " + sql + " ) t limit 1")
            r = self.cur.fetchone()
            if r != None:
                k = 0
                for c in self.cur.description:
                    fields.append(
                        DataField(c[0], field_type=type(r[k]), db_type=type(r[k]))
                    )
                    k = k + 1
            else:
                k = 0
                for c in self.cur.description:
                    fields.append(
                        DataField(c[0], field_type=type(None), db_type=type(None))
                    )
                    k = k + 1
            return fields
        except Spartacus.Database.Exception as exc:
            raise exc
        except sqlite3.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))
        finally:
            if not keep:
                self.Close()

    def GetNotices(self):
        return []

    def ClearNotices(self):
        pass

    def GetStatus(self):
        return None

    def GetRowsAffected(self):
        try:
            if self.con is None:
                raise Spartacus.Database.Exception(
                    "This method should be called in the middle of Open() and Close() calls."
                )
            else:
                # operations like DELETE, INSERT, UPDATE don't set cur.description
                # unless ... RETURNING X is used, so we can assume that if description
                # no rows affected should be returned
                if self.cur.description:
                    return None
                rowcount = self.cur.rowcount
                return rowcount if rowcount is not None and rowcount >= 0 else None
        except Spartacus.Database.Exception as exc:
            raise exc
        except sqlite3.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def GetConStatus(self):
        try:
            if self.con is None:
                return 0
            else:
                return 1
        except Spartacus.Database.Exception as exc:
            raise exc
        except sqlite3.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def QueryBlock(self, sql, blocksize, alltypesstr=False, simple=False):
        try:
            if self.con is None:
                raise Spartacus.Database.Exception(
                    "This method should be called in the middle of Open() and Close() calls."
                )
            else:
                if self.start:
                    self.cur.execute(sql)
                table = DataTable(None, alltypesstr, simple)
                if self.cur.description:
                    for c in self.cur.description:
                        table.AddColumn(c[0])
                    row = self.cur.fetchone()
                    if blocksize > 0:
                        k = 0
                        while row is not None and k < blocksize:
                            table.AddRow(list(row))
                            k = k + 1
                            if k < blocksize:
                                row = self.cur.fetchone()
                    else:
                        while row is not None:
                            table.AddRow(list(row))
                            row = self.cur.fetchone()
                if self.start:
                    self.start = False
                if len(table.Rows) < blocksize:
                    self.start = True
                return table
        except Spartacus.Database.Exception as exc:
            raise exc
        except sqlite3.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def InsertBlock(self, block, tablename, fields=None):
        try:
            column_names = []
            if fields is None:
                fields = []
                for c in block.Columns:
                    column_names.append(c)
                    fields.append(DataField(c))
            else:
                for p in fields:
                    column_names.append(p.name)
            insert_sql = "begin; "
            for r in block.Rows:
                insert_sql = (
                    insert_sql
                    + "insert into "
                    + tablename
                    + "("
                    + ",".join(column_names)
                    + ") values "
                    + self.Mogrify(r, fields)
                    + "; "
                )
            insert_sql = insert_sql + "commit;"
            self.Execute(insert_sql)
        except Spartacus.Database.Exception as exc:
            raise exc
        except sqlite3.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def Special(self, sql):
        try:
            keep = None
            if self.con is None:
                self.Open()
                keep = False
            else:
                keep = True
            self.cur.execute(sql)
            table = from_db_cursor(self.cur)
            table_string = table.get_formatted_string()
            return table_string
        except Spartacus.Database.Exception as exc:
            raise exc
        except sqlite3.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))
        finally:
            if not keep:
                self.Close()


"""
------------------------------------------------------------------------
Memory
------------------------------------------------------------------------
"""


class Memory(Generic):
    def __init__(self, foreign_keys=True, timeout=30, encoding=None):
        if "Memory" in supported_rdbms:
            self.host = None
            self.port = None
            self.service = ":memory:"
            self.user = None
            self.password = None
            self.con = None
            self.cur = None
            self.foreign_keys = foreign_keys
            self.timeout = timeout
            self.encoding = encoding
        else:
            raise Spartacus.Database.Exception(
                "SQLite is not supported. Please install it."
            )

    def GetConnectionString(self):
        return None

    def Open(self, autocommit=True):
        try:
            self.con = sqlite3.connect(self.service, self.timeout)
            # self.con.row_factory = sqlite3.Row
            self.cur = self.con.cursor()
            if self.foreign_keys:
                self.cur.execute("PRAGMA foreign_keys = ON")
            self.start = True
        except sqlite3.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def Query(self, sql, alltypesstr=False, simple=False):
        try:
            if self.con is None:
                raise Spartacus.Database.Exception(
                    "This method should be called in the middle of Open() and Close() calls."
                )
            else:
                self.cur.execute(sql)
                table = DataTable(None, alltypesstr, simple)
                if self.cur.description:
                    for c in self.cur.description:
                        table.AddColumn(c[0])
                    row = self.cur.fetchone()
                    while row is not None:
                        table.AddRow(list(row))
                        row = self.cur.fetchone()
                return table
        except Spartacus.Database.Exception as exc:
            raise exc
        except sqlite3.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def Execute(self, sql):
        try:
            if self.con is None:
                raise Spartacus.Database.Exception(
                    "This method should be called in the middle of Open() and Close() calls."
                )
            else:
                self.cur.execute(sql)
        except Spartacus.Database.Exception as exc:
            raise exc
        except sqlite3.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def ExecuteScalar(self, sql):
        try:
            if self.con is None:
                raise Spartacus.Database.Exception(
                    "This method should be called in the middle of Open() and Close() calls."
                )
            else:
                self.cur.execute(sql)
                r = self.cur.fetchone()
                if r != None:
                    s = r[0]
                else:
                    s = None
                return s
        except Spartacus.Database.Exception as exc:
            raise exc
        except sqlite3.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def Close(self, commit=True):
        try:
            if self.con:
                self.con.commit()
                if self.cur:
                    self.cur.close()
                    self.cur = None
                self.con.close()
                self.con = None
        except sqlite3.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def Commit(self):
        self.Close(True)

    def Rollback(self):
        self.Close(False)

    def Cancel(self, usesameconn=True, keep_connection=False):
        try:
            if self.con:
                self.con.cancel()
                if self.cur:
                    self.cur.close()
                    self.cur = None
                self.con.close()
                self.con = None
        except sqlite3.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def GetPID(self):
        return None

    def Terminate(self, pid):
        pass

    def GetFields(self, sql):
        try:
            if self.con is None:
                raise Spartacus.Database.Exception(
                    "This method should be called in the middle of Open() and Close() calls."
                )
            else:
                fields = []
                self.cur.execute("select * from ( " + sql + " ) t limit 1")
                r = self.cur.fetchone()
                if r != None:
                    k = 0
                    for c in self.cur.description:
                        fields.append(
                            DataField(c[0], field_type=type(r[k]), db_type=type(r[k]))
                        )
                        k = k + 1
                else:
                    k = 0
                    for c in self.cur.description:
                        fields.append(
                            DataField(c[0], field_type=type(None), db_type=type(None))
                        )
                        k = k + 1
                return fields
        except Spartacus.Database.Exception as exc:
            raise exc
        except sqlite3.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def GetNotices(self):
        return []

    def ClearNotices(self):
        pass

    def GetStatus(self):
        return None

    def GetRowsAffected(self):
        return None

    def GetConStatus(self):
        try:
            if self.con is None:
                return 0
            else:
                return 1
        except Spartacus.Database.Exception as exc:
            raise exc
        except sqlite3.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def QueryBlock(self, sql, blocksize, alltypesstr=False, simple=False):
        try:
            if self.con is None:
                raise Spartacus.Database.Exception(
                    "This method should be called in the middle of Open() and Close() calls."
                )
            else:
                if self.start:
                    self.cur.execute(sql)
                table = DataTable(None, alltypesstr, simple)
                if self.cur.description:
                    for c in self.cur.description:
                        table.AddColumn(c[0])
                    row = self.cur.fetchone()
                    if blocksize > 0:
                        k = 0
                        while row is not None and k < blocksize:
                            table.AddRow(list(row))
                            k = k + 1
                            if k < blocksize:
                                row = self.cur.fetchone()
                    else:
                        while row is not None:
                            table.AddRow(list(row))
                            row = self.cur.fetchone()
                if self.start:
                    self.start = False
                return table
        except Spartacus.Database.Exception as exc:
            raise exc
        except sqlite3.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def InsertBlock(self, block, tablename, fields=None):
        try:
            column_names = []
            if fields is None:
                fields = []
                for c in block.Columns:
                    column_names.append(c)
                    fields.append(DataField(c))
            else:
                for p in fields:
                    column_names.append(p.name)
            insert_sql = "begin; "
            for r in block.Rows:
                insert_sql = (
                    insert_sql
                    + "insert into "
                    + tablename
                    + "("
                    + ",".join(column_names)
                    + ") values "
                    + self.Mogrify(r, fields)
                    + "; "
                )
            insert_sql = insert_sql + "commit;"
            self.Execute(insert_sql)
        except Spartacus.Database.Exception as exc:
            raise exc
        except sqlite3.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def Special(self, sql):
        return self.Query(sql).Pretty()


"""
------------------------------------------------------------------------
PostgreSQL
------------------------------------------------------------------------
"""


class PostgreSQL(Generic):
    def __init__(
        self,
        host,
        port,
        service,
        user,
        password,
        application_name="spartacus",
        conn_string="",
        encoding=None,
        connection_params=None,
    ):
        if "PostgreSQL" in supported_rdbms:
            self.host = host
            if port is None or port == "":
                self.port = 5432
            else:
                self.port = port
            if service is None or service == "":
                self.service = "postgres"
            else:
                self.service = service
            self.conn_string = conn_string
            self.conn_string_parsed = urlparse(conn_string)
            self.connection_params = connection_params if connection_params else {}
            self.user = user
            self.password = password
            self.application_name = application_name
            self.con = None
            self.cur = None
            self.start = True
            self.cursor = None
            self.autocommit = True
            self.last_fetched_size = 0
            self.special = PGSpecial()
            self.help = DataTable(simple=True)
            self.help.Columns = ["Command", "Syntax", "Description"]
            for command_key, command in self.special.commands.items():
                if command_key in ["\\z", "\\dp", "\\n", "\\np", "\\ns", "\\nd", "\\pager", "\\!", "\\e", "\\ev", "\\ef", "\\copy"]: # these commands either not working or not needed
                    continue
                self.help.AddRow([command_key, command.syntax, command.description])
            self.help.AddRow(["\\c", "\\c[onnect] [dbname]", "connect to new database"])

            self.help_commands = DataTable(simple=True)
            self.help_commands.Columns = ["SQL Command"]
            for s in list(HelpCommands.keys()):
                self.help_commands.AddRow([s])
            self.expanded = False
            self.timing = False
            self.types = None
            psycopg2.extras.register_default_json(loads=lambda x: x)
            psycopg2.extras.register_default_jsonb(loads=lambda x: x)
            psycopg2.extensions.register_type(
                psycopg2.extensions.new_type(
                    psycopg2.extensions.INTERVAL.values, "INTERVAL_STR", psycopg2.STRING
                ),
                self.cur,
            )
            self.encoding = encoding
        else:
            raise Spartacus.Database.Exception(
                "PostgreSQL is not supported. Please install it with 'pip install Spartacus[postgresql]'."
            )

    def GetPassword(self):
        """
        Returns the password to authenticate with. An authentication method which
        generates a temporary credential replaces this.
        """
        return self.password

    def GetConnectionString(self, service=None):
        service = service or self.service
        password = self.GetPassword()
        if self.conn_string != "":
            if self.conn_string_parsed.query == "":
                new_query = "?dbname={0}&port={1}".format(
                    service.replace("'", "\\'"), self.port
                )
            else:
                new_query = "&dbname={0}&port={1}".format(
                    service.replace("'", "\\'"), self.port
                )
            if self.host is None or self.host == "":
                None
            else:
                new_query = "{0}&host={1}".format(
                    new_query, self.host.replace("'", "\\'")
                )
            if password is None or password == "":
                return_string = "{0}{1}".format(self.conn_string, new_query)
            else:
                return_string = "{0}{1}&password={2}".format(
                    self.conn_string, new_query, password.replace("'", "\\'")
                )
            return return_string
        elif self.host is None or self.host == "":
            if password is None or password == "":
                return """port={0} dbname='{1}' user='{2}' application_name='{3}'""".format(
                    self.port,
                    service.replace("'", "\\'"),
                    self.user.replace("'", "\\'"),
                    self.application_name.replace("'", "\\'"),
                )
            else:
                return """port={0} dbname='{1}' user='{2}' password='{3}' application_name='{4}'""".format(
                    self.port,
                    service.replace("'", "\\'"),
                    self.user.replace("'", "\\'"),
                    password.replace("'", "\\'"),
                    self.application_name.replace("'", "\\'"),
                )
        else:
            if password is None or password == "":
                return """host='{0}' port={1} dbname='{2}' user='{3}' application_name='{4}'""".format(
                    self.host.replace("'", "\\'"),
                    self.port,
                    service.replace("'", "\\'"),
                    self.user.replace("'", "\\'"),
                    self.application_name.replace("'", "\\'"),
                )
            else:
                return """host='{0}' port={1} dbname='{2}' user='{3}' password='{4}' application_name='{5}'""".format(
                    self.host.replace("'", "\\'"),
                    self.port,
                    service.replace("'", "\\'"),
                    self.user.replace("'", "\\'"),
                    password.replace("'", "\\'"),
                    self.application_name.replace("'", "\\'"),
                )

    def Handler(self, value, cursor):
        return value

    def Open(self, autocommit=True):
        try:
            self.connection_params.setdefault("connect_timeout", 10)
            self.con = psycopg2.connect(
                self.GetConnectionString(),
                cursor_factory=psycopg2.extras.DictCursor,
                **self.connection_params
            )
            self.con.autocommit = autocommit
            self.cur = self.con.cursor()
            self.start = True
            self.cursor = None
            # PostgreSQL types
            if self.types is None:
                self.cur.execute("select oid, typname from pg_type")
                self.types = dict(
                    [(r["oid"], r["typname"]) for r in self.cur.fetchall()]
                )
                tmp = []
                for oid, name in self.types.items():
                    if name == "date" or name == "timestamp" or name == "timestamptz":
                        tmp.append(oid)
                oids = tuple(tmp)
                new_date_type = psycopg2.extensions.new_type(
                    oids, "DATE", self.Handler
                )
                psycopg2.extensions.register_type(new_date_type)
                if not autocommit:
                    self.con.commit()
            self.con.notices = DataList()
        except Spartacus.Database.Exception as exc:
            raise exc
        except psycopg2.Error as exc:
            msg = str(exc)
            if "FATAL:  password authentication failed for user" in msg:
                raise InvalidPasswordException(msg) from exc
            raise Spartacus.Database.Exception(msg)
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def Query(self, sql, alltypesstr=False, simple=False):
        try:
            keep = None
            if self.con is None:
                self.Open()
                keep = False
            else:
                keep = True
            self.cur.execute(sql)
            table = DataTable()
            if self.cur.description:
                for c in self.cur.description:
                    table.AddColumn(c[0])
                table.Rows = self.cur.fetchall()
                if alltypesstr:
                    for i in range(0, len(table.Rows)):
                        for j in range(0, len(table.Columns)):
                            if table.Rows[i][j] is not None:
                                if isinstance(table.Rows[i][j], memoryview):
                                    table.Rows[i][j] = "\\x" + table.Rows[i][j].tobytes().hex()
                                else:
                                    table.Rows[i][j] = self.String(table.Rows[i][j])
                            else:
                                table.Rows[i][j] = ""
            return table
        except Spartacus.Database.Exception as exc:
            raise exc
        except psycopg2.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))
        finally:
            if not keep:
                self.Close()

    def Execute(self, sql):
        try:
            keep = None
            if self.con is None:
                self.Open()
                keep = False
            else:
                keep = True
            self.cur.execute(sql)
        except Spartacus.Database.Exception as exc:
            raise exc
        except psycopg2.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))
        finally:
            if not keep:
                self.Close()

    def ExecuteScalar(self, sql):
        try:
            keep = None
            if self.con is None:
                self.Open()
                keep = False
            else:
                keep = True
            self.cur.execute(sql)
            r = self.cur.fetchone()
            if r != None:
                s = r[0]
            else:
                s = None
            return s
        except Spartacus.Database.Exception as exc:
            raise exc
        except psycopg2.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))
        finally:
            if not keep:
                self.Close()

    def Close(self, commit=True):
        try:
            if self.con:
                if commit:
                    self.con.commit()
                else:
                    self.con.rollback()
                if self.cur:
                    self.cur.close()
                    self.cur = None
                self.con.close()
                self.con = None
        except psycopg2.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def Commit(self):
        try:
            if self.con is None:
                raise Spartacus.Database.Exception(
                    "This method should be called in the middle of Open() and Close() calls."
                )
            else:
                return self.con.commit()
        except psycopg2.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def Rollback(self):
        try:
            if self.con is None:
                raise Spartacus.Database.Exception(
                    "This method should be called in the middle of Open() and Close() calls."
                )
            else:
                return self.con.rollback()
        except psycopg2.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def Cancel(self, usesameconn=True, keep_connection=False):
        current_con = self.con
        current_cur = self.cur
        self.con = None
        self.cur = None
        try:
            if current_con:
                if usesameconn:
                    current_con.cancel()
                else:
                    self.connection_params.setdefault("connect_timeout", 10)
                    con2 = psycopg2.connect(
                        self.GetConnectionString(),
                        cursor_factory=psycopg2.extras.DictCursor,
                        **self.connection_params
                    )
                    cur2 = con2.cursor()
                    pid = current_con.get_backend_pid()
                    cur2.execute("select pg_terminate_backend({0})".format(pid))
                    cur2.close()
                    con2.close()
                if current_cur:
                    current_cur.close()
                    current_cur = None

                if keep_connection:
                    self.con = current_con
                    self.cur = self.con.cursor()
                else:
                    current_con.close()
                    current_con = None
        except psycopg2.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def GetPID(self):
        try:
            if self.con is None:
                raise Spartacus.Database.Exception(
                    "This method should be called in the middle of Open() and Close() calls."
                )
            else:
                return self.con.get_backend_pid()
        except psycopg2.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def Terminate(self, pid):
        try:
            self.Execute("select pg_terminate_backend({0})".format(pid))
        except Spartacus.Database.Exception as exc:
            raise exc
        except psycopg2.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def GetFields(self, sql):
        try:
            keep = None
            if self.con is None:
                self.Open()
                keep = False
            else:
                keep = True
            fields = []
            self.cur.execute("select * from ( " + sql + " ) t limit 1")
            r = self.cur.fetchone()
            query_sql = "select "
            first = True
            if r != None:
                k = 0
                for c in self.cur.description:
                    fields.append(
                        DataField(c[0], field_type=type(r[k]), db_type=self.types[c[1]])
                    )
                    if first:
                        query_sql = query_sql + "quote_ident('{0}')".format(c[0])
                        first = False
                    else:
                        query_sql = query_sql + ",quote_ident('{0}')".format(c[0])
                    k = k + 1
            else:
                k = 0
                for c in self.cur.description:
                    fields.append(
                        DataField(c[0], field_type=type(None), db_type=self.types[c[1]])
                    )
                    if first:
                        query_sql = query_sql + "quote_ident('{0}')".format(c[0])
                        first = False
                    else:
                        query_sql = query_sql + ",quote_ident('{0}')".format(c[0])
                    k = k + 1
            self.cur.execute(query_sql)
            r = self.cur.fetchone()
            for k in range(0, len(self.cur.description)):
                fields[k].truename = r[k]
            return fields
        except Spartacus.Database.Exception as exc:
            raise exc
        except psycopg2.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))
        finally:
            if not keep:
                self.Close()

    def GetNotices(self):
        try:
            if self.con is None:
                raise Spartacus.Database.Exception(
                    "This method should be called in the middle of Open() and Close() calls."
                )
            else:
                return self.con.notices.list
        except Spartacus.Database.Exception as exc:
            raise exc
        except psycopg2.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def ClearNotices(self):
        try:
            if self.con is None:
                raise Spartacus.Database.Exception(
                    "This method should be called in the middle of Open() and Close() calls."
                )
            else:
                del self.con.notices.list[:]
        except Spartacus.Database.Exception as exc:
            raise exc
        except psycopg2.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def GetStatus(self):
        try:
            if self.con is None:
                raise Spartacus.Database.Exception(
                    "This method should be called in the middle of Open() and Close() calls."
                )
            else:
                return self.cur.statusmessage
        except Spartacus.Database.Exception as exc:
            raise exc
        except psycopg2.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def GetRowsAffected(self):
        try:
            if self.con is None:
                raise Spartacus.Database.Exception(
                    "This method should be called in the middle of Open() and Close() calls."
                )
            else:
                # operations like DELETE, INSERT, UPDATE don't set cur.description
                # unless ... RETURNING X is used, so we can assume that if description
                # no rows affected should be returned
                if self.cur.description:
                    return None
                rowcount = self.cur.rowcount
                return rowcount if rowcount is not None and rowcount >= 0 else None
        except Spartacus.Database.Exception as exc:
            raise exc
        except psycopg2.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def GetConStatus(self):
        try:
            if self.con is None:
                return 0
            else:
                if self.con.closed == 0:
                    status = self.con.get_transaction_status()
                    if status == 4:
                        return 0
                    else:
                        return status + 1
                else:
                    return 0
        except Spartacus.Database.Exception as exc:
            raise exc
        except psycopg2.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def Parse(self, sql):
        try:
            statement = sqlparse.split(sql)
            analysis = sqlparse.parse(sql)
            if len(statement) == len(analysis):
                cursors = []
                for i in range(0, len(statement)):
                    if analysis[i].get_type() == "SELECT":
                        found_cte = False
                        found_dml = False
                        found_into = False
                        for token in analysis[i].flatten():
                            if token.ttype == sqlparse.tokens.Token.Keyword.CTE:
                                found_cte = True
                            if (
                                token.ttype == sqlparse.tokens.Token.Keyword.DML
                                and token.value.upper() != "SELECT"
                            ):
                                found_dml = True
                            if token.is_keyword and token.value.upper() == "INTO":
                                found_into = True
                        if not (found_cte and found_dml) and not found_into:
                            cursors.append(
                                "{0}_{1}".format(
                                    self.application_name, uuid.uuid4().hex
                                )
                            )
                if len(cursors) > 0:
                    cursor_sql = ""
                    j = 0
                    for i in range(0, len(statement)):
                        if analysis[i].get_type() == "SELECT":
                            if j < len(cursors) - 1:
                                cursor_sql = cursor_sql + statement[i]
                            else:
                                if self.autocommit:
                                    cursor_sql = (
                                        cursor_sql
                                        + " DECLARE {0} CURSOR WITH HOLD FOR {1}".format(
                                            cursors[j], statement[i]
                                        )
                                    )
                                else:
                                    cursor_sql = (
                                        cursor_sql
                                        + " DECLARE {0} CURSOR WITHOUT HOLD FOR {1}".format(
                                            cursors[j], statement[i]
                                        )
                                    )
                                self.cursor = cursors[j]
                            j = j + 1
                        else:
                            cursor_sql = cursor_sql + statement[i]
                    return cursor_sql
                else:
                    self.cursor = None
                    return sql
            else:
                self.cursor = None
                return sql
        except Exception as exc:
            self.cursor = None
            return sql

    def ResolveType(self, type_code):
        try:
            res = self.Query("select format_type({0}, NULL)".format(type_code))
            return res.Rows[0][0]
        except:
            return "???"

    def QueryBlock(self, sql, blocksize, alltypesstr=False, simple=False):
        try:
            if self.con is None:
                raise Spartacus.Database.Exception(
                    "This method should be called in the middle of Open() and Close() calls."
                )
            else:
                if self.start:
                    if self.cursor:
                        try:
                            self.cur.execute("CLOSE {0}".format(self.cursor))
                        except:
                            None
                    parsed_sql = self.Parse(sql)
                    if (
                        not self.autocommit
                        and not self.GetConStatus() == 3
                        and not self.GetConStatus() == 4
                    ):
                        self.cur.execute("BEGIN;")
                    self.cur.execute(parsed_sql)
                table = DataTable()
                if self.cursor:
                    if blocksize > 0:
                        self.cur.execute(
                            "FETCH {0} FROM {1}".format(blocksize, self.cursor)
                        )
                    else:
                        self.cur.execute("FETCH ALL FROM {0}".format(self.cursor))
                if self.cur.description:
                    for c in self.cur.description:
                        table.AddColumn(c[0])
                        table.AddColumnTypeCode(c.type_code)
                    if blocksize > 0:
                        table.Rows = self.cur.fetchmany(blocksize)
                    else:
                        table.Rows = self.cur.fetchall()
                    if alltypesstr:
                        for i in range(0, len(table.Rows)):
                            for j in range(0, len(table.Columns)):
                                if table.Rows[i][j] != None:
                                    if isinstance(table.Rows[i][j], memoryview):
                                        table.Rows[i][j] = "\\x" + table.Rows[i][j].tobytes().hex()
                                    else:
                                        table.Rows[i][j] = self.String(table.Rows[i][j])

                if self.start:
                    self.start = False
                if len(table.Rows) < blocksize:
                    self.start = True
                    if self.cursor:
                        self.cur.execute("CLOSE {0}".format(self.cursor))
                        self.cursor = None
                return table
        except Spartacus.Database.Exception as exc:
            self.start = True
            self.cursor = None
            raise exc
        except psycopg2.Error as exc:
            self.start = True
            self.cursor = None
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            self.start = True
            self.cursor = None
            raise Spartacus.Database.Exception(str(exc))

    def InsertBlock(self, block, tablename, fields=None):
        try:
            column_names = []
            if fields is None:
                fields = []
                for c in block.Columns:
                    column_names.append(c)
                    fields.append(DataField(c))
            else:
                for p in fields:
                    column_names.append(p.name)
            values = []
            for r in block.Rows:
                values.append(self.Mogrify(r, fields))
            self.Execute(
                "insert into "
                + tablename
                + "("
                + ",".join(column_names)
                + ") values "
                + ",".join(values)
                + ""
            )
        except Spartacus.Database.Exception as exc:
            raise exc
        except psycopg2.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def special_handle_connect(self, sql):
        """
        Implements psql-like \c [dbname]` special command
        Returns a confirmation string on success. Raises
        Spartacus.Database.Exception on failure without touching
        self.con/self.cur/self.service - the old connection is left intact.
        """
        args = sql.strip().rstrip(";").split(maxsplit=1)[1:]
        target_service = args[0].strip() if args else ""
        if (
            len(target_service) > 1
            and target_service[0] == target_service[-1]
            and target_service[0] in "\"'"
        ):
            target_service = target_service[1:-1]
        target_service = target_service or self.service

        if target_service == self.service and self.con is not None:
            # Bare "\c" or "\c samedb" while already connected - just reconfirm
            return 'You are now connected to database "{0}" as user "{1}".'.format(
                self.service, self.user
            )

        try:
            new_con = psycopg2.connect(
                self.GetConnectionString(service=target_service),
                cursor_factory=psycopg2.extras.DictCursor,
                **self.connection_params
            )
        except psycopg2.Error as exc:
            raise Spartacus.Database.Exception(
                "connection to server failed: {0}\nPrevious connection kept".format(
                    str(exc).strip()
                )
            )
        except Exception as exc:
            raise Spartacus.Database.Exception(
                "connection to server failed: {0}\nPrevious connection kept".format(exc)
            )

        # New connection verified - now safe to retire the old one.
        new_con.autocommit = self.autocommit
        if self.con is not None:
            try:
                if self.cur:
                    self.cur.close()
                self.con.close()
            except Exception:
                pass

        self.con = new_con
        self.cur = new_con.cursor()
        self.con.notices = DataList()
        self.service = target_service
        self.start = True
        self.cursor = None

        return 'You are now connected to database "{0}" as user "{1}".'.format(
            target_service, self.user
        )

    def Special(self, sql):
        try:
            keep = None
            if self.con is None:
                self.Open()
                keep = False
            else:
                keep = True
            command = sql.lstrip().split(" ")[0].rstrip("+")
            heading = None
            table = None
            status = None
            self.last_fetched_size = 0
            if command == "\\?":
                table = self.help
            elif command == "\\h" and len(sql.lstrip().split(" ")[1:]) == 0:
                heading = 'Type "\h [parameter]" where "parameter" is a SQL Command from the list below:'
                table = self.help_commands
            elif command in ("\\c", "\\connect"):
                return self.special_handle_connect(sql)
            else:
                aux = self.help.Select("Command", command)
                if len(aux.Rows) > 0:
                    for title, rows, headers, status in self.special.execute(
                        self.cur, sql
                    ):
                        if title:
                            heading = title
                        if rows:
                            table = DataTable(simple=True)
                            table.Columns = headers
                            if isinstance(rows, type(self.cur)):
                                if rows.description:
                                    table.Rows = rows.fetchall()
                            else:
                                for r in rows:
                                    table.AddRow(r)
                        if status:
                            if status.strip() == "Expanded display is on.":
                                self.expanded = True
                            elif status.strip() == "Expanded display is off.":
                                self.expanded = False
                            elif status.strip() == "Timing is on.":
                                self.timing = True
                            elif status.strip() == "Timing is off.":
                                self.timing = False
                else:
                    if self.timing:
                        start_time = datetime.datetime.now()
                    table = self.QueryBlock(sql, 50, True, True)
                    self.last_fetched_size = len(table.Rows)
                    status = self.GetStatus()
                    if self.timing:
                        status = status + "\nTime: {0}".format(
                            datetime.datetime.now() - start_time
                        )
            if heading and table and len(table.Rows) > 0 and status:
                return (
                    heading + "\n" + table.Pretty(self.expanded) + "\n" + status
                )
            elif heading and table and len(table.Rows) > 0:
                return heading + "\n" + table.Pretty(self.expanded)
            elif heading and status:
                return heading + "\n" + status
            elif heading:
                return heading
            elif table and len(table.Rows) > 0 and status:
                return table.Pretty(self.expanded) + "\n" + status
            elif table and len(table.Rows) > 0:
                return table.Pretty(self.expanded)
            elif status:
                return status
            else:
                return ""
        except Spartacus.Database.Exception as exc:
            raise exc
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))
        finally:
            if not keep:
                self.Close()


"""
------------------------------------------------------------------------
MySQL
------------------------------------------------------------------------
"""


class MySQL(Generic):
    def __init__(
        self,
        host,
        port,
        service,
        user,
        password,
        conn_string="",
        encoding=None,
        connection_params=None,
    ):
        if "MySQL" in supported_rdbms:
            self.host = host
            if re.match(r"^\/$|(^(?=\/))(\/(?=[^/\0])[^/\0]+)*\/?$", host):
                self.server_params = {"unix_socket": host}
            else:
                self.server_params = {"host": host}

            if port is None or port == "":
                self.port = 3306
            else:
                self.port = port
            self.conn_string = conn_string
            self.conn_string_parsed = urlparse(conn_string)
            self.connection_params = connection_params if connection_params else {}
            self.service = service
            self.user = user
            self.password = password
            self.con = None
            self.cur = None
            self.help = DataTable(simple=True)
            self.help.Columns = ["Command", "Syntax", "Description"]
            self.help.AddRow(["\\?", "\\?", "Show Commands."])
            self.help.AddRow(["\\x", "\\x", "Toggle expanded output."])
            self.help.AddRow(["\\timing", "\\timing", "Toggle timing of commands."])
            self.expanded = False
            self.timing = False
            self.status = 0
            self.con_id = 0
            self.types = {
                0: "DECIMAL",
                1: "TINY",
                2: "SHORT",
                3: "LONG",
                4: "FLOAT",
                5: "DOUBLE",
                6: "NULL",
                7: "TIMESTAMP",
                8: "LONGLONG",
                9: "INT24",
                10: "DATE",
                11: "TIME",
                12: "DATETIME",
                13: "YEAR",
                14: "NEWDATE",
                15: "VARCHAR",
                16: "BIT",
                245: "JSON",
                246: "NEWDECIMAL",
                247: "ENUM",
                248: "SET",
                249: "TINY_BLOB",
                250: "MEDIUM_BLOB",
                251: "LONG_BLOB",
                252: "BLOB",
                253: "VAR_STRING",
                254: "STRING",
                255: "GEOMETRY",
            }
            self.encoding = encoding
        else:
            raise Spartacus.Database.Exception(
                "MySQL is not supported. Please install it with 'pip install Spartacus[mysql]'."
            )

    def GetConnectionString(self):
        return None

    def Open(self, autocommit=True):
        try:
            self.con = pymysql.connect(
                port=int(self.port),
                db=self.service,
                user=self.user,
                password=self.password,
                autocommit=autocommit,
                read_default_file="~/.my.cnf",
                client_flag=CLIENT.MULTI_STATEMENTS,
                **self.connection_params,
                **self.server_params
            )
            self.cur = self.con.cursor()
            self.start = True
            self.status = 0
            self.con_id = self.ExecuteScalar("select connection_id()")
        except pymysql.Error as exc:
            code, msg = exc.args
            if code == ER.ACCESS_DENIED_ERROR:
                raise InvalidPasswordException(msg) from exc
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def Query(self, sql, alltypesstr=False, simple=False):
        try:
            keep = None
            if self.con is None:
                self.Open()
                keep = False
            else:
                keep = True
            self.status = self.cur.execute(sql)
            table = DataTable(None, alltypesstr, simple)
            if self.cur.description:
                for c in self.cur.description:
                    table.AddColumn(c[0])
                row = self.cur.fetchone()
                while row is not None:
                    table.AddRow(list(row))
                    row = self.cur.fetchone()
            return table
        except Spartacus.Database.Exception as exc:
            raise exc
        except pymysql.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))
        finally:
            if not keep:
                self.Close()

    def Execute(self, sql):
        try:
            keep = None
            if self.con is None:
                self.Open()
                keep = False
            else:
                keep = True
            self.status = self.cur.execute(sql)
        except Spartacus.Database.Exception as exc:
            raise exc
        except pymysql.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))
        finally:
            if not keep:
                self.Close()

    def ExecuteScalar(self, sql):
        try:
            keep = None
            if self.con is None:
                self.Open()
                keep = False
            else:
                keep = True
            self.status = self.cur.execute(sql)
            r = self.cur.fetchone()
            if r != None:
                s = r[0]
            else:
                s = None
            return s
        except Spartacus.Database.Exception as exc:
            raise exc
        except pymysql.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))
        finally:
            if not keep:
                self.Close()

    def Close(self, commit=True):
        try:
            if self.con:
                self.con.commit()
                if self.cur:
                    self.cur.close()
                    self.cur = None
                self.con.close()
                self.con = None
        except pymysql.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def Commit(self):
        self.Close(True)

    def Rollback(self):
        self.Close(False)

    def Cancel(self, usesameconn=True, keep_connection=False):
        try:
            if self.con:
                con2 = pymysql.connect(
                    host=self.host,
                    port=int(self.port),
                    db=self.service,
                    user=self.user,
                    password=self.password,
                )
                cur2 = con2.cursor()
                self.status = cur2.execute("kill {0}".format(self.con_id))
                cur2.close()
                con2.close()
                if self.cur:
                    self.cur.close()
                    self.cur = None
                self.con.close()
                self.con = None
        except pymysql.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def GetPID(self):
        return self.con_id

    def Terminate(self, pid):
        try:
            self.Execute("kill {0}".format(pid))
        except Spartacus.Database.Exception as exc:
            raise exc
        except pymysql.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def GetFields(self, sql):
        try:
            keep = None
            if self.con is None:
                self.Open()
                keep = False
            else:
                keep = True
            fields = []
            self.status = self.cur.execute(
                "select * from ( " + sql + " ) t limit 1"
            )
            r = self.cur.fetchone()
            if r != None:
                k = 0
                for c in self.cur.description:
                    fields.append(
                        DataField(c[0], field_type=type(r[k]), db_type=self.types[c[1]])
                    )
                    k = k + 1
            else:
                k = 0
                for c in self.cur.description:
                    fields.append(
                        DataField(c[0], field_type=type(None), db_type=self.types[c[1]])
                    )
                    k = k + 1
            return fields
        except Spartacus.Database.Exception as exc:
            raise exc
        except pymysql.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))
        finally:
            if not keep:
                self.Close()

    def GetNotices(self):
        return []

    def ClearNotices(self):
        pass

    def GetStatus(self):
        try:
            if self.con is None:
                raise Spartacus.Database.Exception(
                    "This method should be called in the middle of Open() and Close() calls."
                )
            else:
                return self.status
        except Spartacus.Database.Exception as exc:
            raise exc
        except pymysql.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def GetRowsAffected(self):
        try:
            if self.con is None:
                raise Spartacus.Database.Exception(
                    "This method should be called in the middle of Open() and Close() calls."
                )
            else:
                if self.cur.description:
                    return None
                rowcount = self.status
                return rowcount if rowcount is not None and rowcount >= 0 else None
        except Spartacus.Database.Exception as exc:
            raise exc
        except pymysql.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def GetConStatus(self):
        try:
            if self.con is None or not self.con.open:
                return 0
            else:
                return 1
        except Spartacus.Database.Exception as exc:
            raise exc
        except pymysql.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def ResolveType(self, type_code):
        return self.types.get(type_code, "???").lower()

    def QueryBlock(self, sql, blocksize, alltypesstr=False, simple=False):
        try:
            if self.con is None:
                raise Spartacus.Database.Exception(
                    "This method should be called in the middle of Open() and Close() calls."
                )
            else:
                if self.start:
                    self.status = self.cur.execute(sql)
                table = DataTable(None, alltypesstr, simple)
                if self.cur.description:
                    for c in self.cur.description:
                        table.AddColumn(c[0])
                        table.AddColumnTypeCode(c[1])
                    row = self.cur.fetchone()
                    if blocksize > 0:
                        k = 0
                        while row is not None and k < blocksize:
                            table.AddRow(list(row))
                            k = k + 1
                            if k < blocksize:
                                row = self.cur.fetchone()
                    else:
                        while row is not None:
                            table.AddRow(list(row))
                            row = self.cur.fetchone()
                if self.start:
                    self.start = False
                if len(table.Rows) < blocksize:
                    self.start = True
                return table
        except Spartacus.Database.Exception as exc:
            raise exc
        except pymysql.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def InsertBlock(self, block, tablename, fields=None):
        try:
            column_names = []
            if fields is None:
                fields = []
                for c in block.Columns:
                    column_names.append(c)
                    fields.append(DataField(c))
            else:
                for p in fields:
                    column_names.append(p.name)
            values = []
            for r in block.Rows:
                values.append(self.Mogrify(r, fields))
            self.Execute(
                "insert into "
                + tablename
                + "("
                + ",".join(column_names)
                + ") values "
                + ",".join(values)
                + ""
            )
        except Spartacus.Database.Exception as exc:
            raise exc
        except pymysql.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def Special(self, sql):
        try:
            keep = None
            if self.con is None:
                self.Open()
                keep = False
            else:
                keep = True
            command = sql.lstrip().split(" ")[0].rstrip("+")
            title = None
            table = None
            status = None
            if command == "\\?":
                table = self.help
            else:
                aux = self.help.Select("Command", command)
                if len(aux.Rows) > 0:
                    if command == "\\x" and not self.expanded:
                        status = "Expanded display is on."
                        self.expanded = True
                    elif command == "\\x" and self.expanded:
                        status = "Expanded display is off."
                        self.expanded = False
                    elif command == "\\timing" and not self.timing:
                        status = "Timing is on."
                        self.timing = True
                    elif command == "\\timing" and self.timing:
                        status = "Timing is off."
                        self.timing = False
                else:
                    if self.timing:
                        start_time = datetime.datetime.now()
                    table = self.Query(sql, True, True)
                    tmp = self.GetStatus()
                    if tmp == 1:
                        status = "1 row "
                    else:
                        status = "{0} rows ".format(tmp)
                    if command.lower() == "select":
                        status = status + "in set"
                    else:
                        status = status + "affected"
                    if self.timing:
                        status = status + "\nTime: {0}".format(
                            datetime.datetime.now() - start_time
                        )
            if title and table and len(table.Rows) > 0 and status:
                return (
                    title + "\n" + table.Pretty(self.expanded) + "\n" + status
                )
            elif title and table and len(table.Rows) > 0:
                return title + "\n" + table.Pretty(self.expanded)
            elif title and status:
                return title + "\n" + status
            elif title:
                return title
            elif table and len(table.Rows) > 0 and status:
                return table.Pretty(self.expanded) + "\n" + status
            elif table and len(table.Rows) > 0:
                return table.Pretty(self.expanded)
            elif status:
                return status
            else:
                return ""
        except Spartacus.Database.Exception as exc:
            raise exc
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))
        finally:
            if not keep:
                self.Close()


"""
------------------------------------------------------------------------
MariaDB
------------------------------------------------------------------------
"""


class MariaDB(Generic):
    def __init__(
        self,
        host,
        port,
        service,
        user,
        password,
        conn_string="",
        encoding=None,
        connection_params=None,
    ):
        if "MariaDB" in supported_rdbms:
            self.host = host
            if re.match(r"^\/$|(^(?=\/))(\/(?=[^/\0])[^/\0]+)*\/?$", host):
                self.server_params = {"unix_socket": host}
            else:
                self.server_params = {"host": host}

            if port is None or port == "":
                self.port = 3306
            else:
                self.port = port
            self.conn_string = conn_string
            self.connection_params = connection_params if connection_params else {}
            self.conn_string_parsed = urlparse(conn_string)
            self.service = service
            self.user = user
            self.password = password
            self.con = None
            self.cur = None
            self.help = DataTable(simple=True)
            self.help.Columns = ["Command", "Syntax", "Description"]
            self.help.AddRow(["\\?", "\\?", "Show Commands."])
            self.help.AddRow(["\\x", "\\x", "Toggle expanded output."])
            self.help.AddRow(["\\timing", "\\timing", "Toggle timing of commands."])
            self.expanded = False
            self.timing = False
            self.status = 0
            self.con_id = 0
            self.types = {
                0: "DECIMAL",
                1: "TINY",
                2: "SHORT",
                3: "LONG",
                4: "FLOAT",
                5: "DOUBLE",
                6: "NULL",
                7: "TIMESTAMP",
                8: "LONGLONG",
                9: "INT24",
                10: "DATE",
                11: "TIME",
                12: "DATETIME",
                13: "YEAR",
                14: "NEWDATE",
                15: "VARCHAR",
                16: "BIT",
                245: "JSON",
                246: "NEWDECIMAL",
                247: "ENUM",
                248: "SET",
                249: "TINY_BLOB",
                250: "MEDIUM_BLOB",
                251: "LONG_BLOB",
                252: "BLOB",
                253: "VAR_STRING",
                254: "STRING",
                255: "GEOMETRY",
            }
            self.encoding = encoding
        else:
            raise Spartacus.Database.Exception(
                "MariaDB is not supported. Please install it with 'pip install Spartacus[mariadb]'."
            )

    def GetConnectionString(self):
        return None

    def Open(self, autocommit=True):
        try:
            self.con = pymysql.connect(
                port=int(self.port),
                db=self.service,
                user=self.user,
                password=self.password,
                autocommit=autocommit,
                read_default_file="~/.my.cnf",
                client_flag=CLIENT.MULTI_STATEMENTS,
                **self.connection_params,
                **self.server_params
            )
            self.cur = self.con.cursor()
            self.start = True
            self.status = 0
            self.con_id = self.ExecuteScalar("select connection_id()")
        except pymysql.Error as exc:
            code, msg = exc.args
            if code == ER.ACCESS_DENIED_ERROR:
                raise InvalidPasswordException(msg) from exc
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def Query(self, sql, alltypesstr=False, simple=False):
        try:
            keep = None
            if self.con is None:
                self.Open()
                keep = False
            else:
                keep = True
            self.status = self.cur.execute(sql)
            table = DataTable(None, alltypesstr, simple)
            if self.cur.description:
                for c in self.cur.description:
                    table.AddColumn(c[0])
                row = self.cur.fetchone()
                while row is not None:
                    table.AddRow(list(row))
                    row = self.cur.fetchone()
            return table
        except Spartacus.Database.Exception as exc:
            raise exc
        except pymysql.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))
        finally:
            if not keep:
                self.Close()

    def Execute(self, sql):
        try:
            keep = None
            if self.con is None:
                self.Open()
                keep = False
            else:
                keep = True
            self.status = self.cur.execute(sql)
        except Spartacus.Database.Exception as exc:
            raise exc
        except pymysql.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))
        finally:
            if not keep:
                self.Close()

    def ExecuteScalar(self, sql):
        try:
            keep = None
            if self.con is None:
                self.Open()
                keep = False
            else:
                keep = True
            self.status = self.cur.execute(sql)
            r = self.cur.fetchone()
            if r != None:
                s = r[0]
            else:
                s = None
            return s
        except Spartacus.Database.Exception as exc:
            raise exc
        except pymysql.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))
        finally:
            if not keep:
                self.Close()

    def Close(self, commit=True):
        try:
            if self.con:
                self.con.commit()
                if self.cur:
                    self.cur.close()
                    self.cur = None
                self.con.close()
                self.con = None
        except pymysql.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def Commit(self):
        self.Close(True)

    def Rollback(self):
        self.Close(False)

    def Cancel(self, usesameconn=True, keep_connection=False):
        try:
            if self.con:
                con2 = pymysql.connect(
                    host=self.host,
                    port=int(self.port),
                    db=self.service,
                    user=self.user,
                    password=self.password,
                )
                cur2 = con2.cursor()
                self.status = cur2.execute("kill {0}".format(self.con_id))
                cur2.close()
                con2.close()
                if self.cur:
                    self.cur.close()
                    self.cur = None
                self.con.close()
                self.con = None
        except pymysql.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def GetPID(self):
        return self.con_id

    def Terminate(self, pid):
        try:
            self.Execute("kill {0}".format(pid))
        except Spartacus.Database.Exception as exc:
            raise exc
        except pymysql.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def GetFields(self, sql):
        try:
            keep = None
            if self.con is None:
                self.Open()
                keep = False
            else:
                keep = True
            fields = []
            self.status = self.cur.execute(
                "select * from ( " + sql + " ) t limit 1"
            )
            r = self.cur.fetchone()
            if r != None:
                k = 0
                for c in self.cur.description:
                    fields.append(
                        DataField(c[0], field_type=type(r[k]), db_type=self.types[c[1]])
                    )
                    k = k + 1
            else:
                k = 0
                for c in self.cur.description:
                    fields.append(
                        DataField(c[0], field_type=type(None), db_type=self.types[c[1]])
                    )
                    k = k + 1
            return fields
        except Spartacus.Database.Exception as exc:
            raise exc
        except pymysql.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))
        finally:
            if not keep:
                self.Close()

    def GetNotices(self):
        return []

    def ClearNotices(self):
        pass

    def GetStatus(self):
        try:
            if self.con is None:
                raise Spartacus.Database.Exception(
                    "This method should be called in the middle of Open() and Close() calls."
                )
            else:
                return self.status
        except Spartacus.Database.Exception as exc:
            raise exc
        except pymysql.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def GetRowsAffected(self):
        try:
            if self.con is None:
                raise Spartacus.Database.Exception(
                    "This method should be called in the middle of Open() and Close() calls."
                )
            else:
                if self.cur.description:
                    return None
                rowcount = self.status
                return rowcount if rowcount is not None and rowcount >= 0 else None
        except Spartacus.Database.Exception as exc:
            raise exc
        except pymysql.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def GetConStatus(self):
        try:
            if self.con is None:
                return 0
            else:
                return 1
        except Spartacus.Database.Exception as exc:
            raise exc
        except pymysql.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def ResolveType(self, type_code):
        return self.types.get(type_code, "???").lower()

    def QueryBlock(self, sql, blocksize, alltypesstr=False, simple=False):
        try:
            if self.con is None:
                raise Spartacus.Database.Exception(
                    "This method should be called in the middle of Open() and Close() calls."
                )
            else:
                if self.start:
                    self.status = self.cur.execute(sql)
                table = DataTable(None, alltypesstr, simple)
                if self.cur.description:
                    for c in self.cur.description:
                        table.AddColumn(c[0])
                        table.AddColumnTypeCode(c[1])
                    row = self.cur.fetchone()
                    if blocksize > 0:
                        k = 0
                        while row is not None and k < blocksize:
                            table.AddRow(list(row))
                            k = k + 1
                            if k < blocksize:
                                row = self.cur.fetchone()
                    else:
                        while row is not None:
                            table.AddRow(list(row))
                            row = self.cur.fetchone()
                if self.start:
                    self.start = False
                if len(table.Rows) < blocksize:
                    self.start = True
                return table
        except Spartacus.Database.Exception as exc:
            raise exc
        except pymysql.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def InsertBlock(self, block, tablename, fields=None):
        try:
            column_names = []
            if fields is None:
                fields = []
                for c in block.Columns:
                    column_names.append(c)
                    fields.append(DataField(c))
            else:
                for p in fields:
                    column_names.append(p.name)
            values = []
            for r in block.Rows:
                values.append(self.Mogrify(r, fields))
            self.Execute(
                "insert into "
                + tablename
                + "("
                + ",".join(column_names)
                + ") values "
                + ",".join(values)
                + ""
            )
        except Spartacus.Database.Exception as exc:
            raise exc
        except pymysql.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def Special(self, sql):
        try:
            keep = None
            if self.con is None:
                self.Open()
                keep = False
            else:
                keep = True
            command = sql.lstrip().split(" ")[0].rstrip("+")
            title = None
            table = None
            status = None
            if command == "\\?":
                table = self.help
            else:
                aux = self.help.Select("Command", command)
                if len(aux.Rows) > 0:
                    if command == "\\x" and not self.expanded:
                        status = "Expanded display is on."
                        self.expanded = True
                    elif command == "\\x" and self.expanded:
                        status = "Expanded display is off."
                        self.expanded = False
                    elif command == "\\timing" and not self.timing:
                        status = "Timing is on."
                        self.timing = True
                    elif command == "\\timing" and self.timing:
                        status = "Timing is off."
                        self.timing = False
                else:
                    if self.timing:
                        start_time = datetime.datetime.now()
                    table = self.Query(sql, True, True)
                    tmp = self.GetStatus()
                    if tmp == 1:
                        status = "1 row "
                    else:
                        status = "{0} rows ".format(tmp)
                    if command.lower() == "select":
                        status = status + "in set"
                    else:
                        status = status + "affected"
                    if self.timing:
                        status = status + "\nTime: {0}".format(
                            datetime.datetime.now() - start_time
                        )
            if title and table and len(table.Rows) > 0 and status:
                return (
                    title + "\n" + table.Pretty(self.expanded) + "\n" + status
                )
            elif title and table and len(table.Rows) > 0:
                return title + "\n" + table.Pretty(self.expanded)
            elif title and status:
                return title + "\n" + status
            elif title:
                return title
            elif table and len(table.Rows) > 0 and status:
                return table.Pretty(self.expanded) + "\n" + status
            elif table and len(table.Rows) > 0:
                return table.Pretty(self.expanded)
            elif status:
                return status
            else:
                return ""
        except Spartacus.Database.Exception as exc:
            raise exc
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))
        finally:
            if not keep:
                self.Close()


"""
------------------------------------------------------------------------
Firebird
------------------------------------------------------------------------
"""


class Firebird(Generic):
    def __init__(
        self,
        host,
        port,
        service,
        user,
        password,
        conn_string="",
        encoding=None,
    ):
        if "Firebird" in supported_rdbms:
            self.host = host
            if port is None or port == "":
                self.port = 3050
            else:
                self.port = port
            self.conn_string = conn_string
            self.conn_string_parsed = urlparse(conn_string)
            self.service = service
            self.user = user
            self.password = password
            self.con = None
            self.cur = None
            if encoding is not None:
                self.encoding = encoding
            else:
                self.encoding = "UTF8"
        else:
            raise Spartacus.Database.Exception(
                "Firebird is not supported. Please install it with 'pip install Spartacus[firebird]'."
            )

    def GetConnectionString(self):
        return None

    def Open(self, autocommit=True):
        try:
            self.con = fdb.connect(
                host=self.host,
                port=int(self.port),
                database=self.service,
                user=self.user,
                password=self.password,
                charset=self.encoding,
            )
            self.cur = self.con.cursor()
            self.start = True
        except fdb.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def Query(self, sql, alltypesstr=False, simple=False):
        try:
            keep = None
            if self.con is None:
                self.Open()
                keep = False
            else:
                keep = True
            self.cur.execute(sql)
            table = DataTable(None, alltypesstr, simple)
            if self.cur.description:
                for c in self.cur.description:
                    table.AddColumn(c[0])
                row = self.cur.fetchone()
                while row is not None:
                    table.AddRow(list(row))
                    row = self.cur.fetchone()
            return table
        except Spartacus.Database.Exception as exc:
            raise exc
        except fdb.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))
        finally:
            if not keep:
                self.Close()

    def Execute(self, sql):
        try:
            keep = None
            if self.con is None:
                self.Open()
                keep = False
            else:
                keep = True
            self.cur.execute(sql)
        except Spartacus.Database.Exception as exc:
            raise exc
        except fdb.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))
        finally:
            if not keep:
                self.Close()

    def ExecuteScalar(self, sql):
        try:
            keep = None
            if self.con is None:
                self.Open()
                keep = False
            else:
                keep = True
            self.cur.execute(sql)
            r = self.cur.fetchone()
            if r != None:
                s = r[0]
            else:
                s = None
            return s
        except Spartacus.Database.Exception as exc:
            raise exc
        except fdb.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))
        finally:
            if not keep:
                self.Close()

    def Close(self, commit=True):
        try:
            if self.con:
                self.con.commit()
                if self.cur:
                    self.cur.close()
                    self.cur = None
                self.con.close()
                self.con = None
        except fdb.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def Commit(self):
        self.Close(True)

    def Rollback(self):
        self.Close(False)

    def Cancel(self, usesameconn=True, keep_connection=False):
        try:
            if self.con:
                self.con.cancel()
                if self.cur:
                    self.cur.close()
                    self.cur = None
                self.con.close()
                self.con = None
        except fdb.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def GetPID(self):
        return None

    def Terminate(self, pid):
        pass

    def GetFields(self, sql):
        try:
            keep = None
            if self.con is None:
                self.Open()
                keep = False
            else:
                keep = True
            fields = []
            self.cur.execute("select first 1 * from ( " + sql + " )")
            r = self.cur.fetchone()
            if r != None:
                k = 0
                for c in self.cur.description:
                    fields.append(
                        DataField(c[0], field_type=type(r[k]), db_type=type(r[k]))
                    )
                    k = k + 1
            else:
                k = 0
                for c in self.cur.description:
                    fields.append(
                        DataField(c[0], field_type=type(None), db_type=type(None))
                    )
                    k = k + 1
            return fields
        except Spartacus.Database.Exception as exc:
            raise exc
        except fdb.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))
        finally:
            if not keep:
                self.Close()

    def GetNotices(self):
        return []

    def ClearNotices(self):
        pass

    def GetStatus(self):
        return None

    def GetRowsAffected(self):
        return None

    def GetConStatus(self):
        try:
            if self.con is None:
                return 0
            else:
                return 1
        except Spartacus.Database.Exception as exc:
            raise exc
        except fdb.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def QueryBlock(self, sql, blocksize, alltypesstr=False, simple=False):
        try:
            if self.con is None:
                raise Spartacus.Database.Exception(
                    "This method should be called in the middle of Open() and Close() calls."
                )
            else:
                if self.start:
                    self.cur.execute(sql)
                table = DataTable(None, alltypesstr, simple)
                if self.cur.description:
                    for c in self.cur.description:
                        table.AddColumn(c[0])
                    row = self.cur.fetchone()
                    if blocksize > 0:
                        k = 0
                        while row is not None and k < blocksize:
                            table.AddRow(list(row))
                            k = k + 1
                            if k < blocksize:
                                row = self.cur.fetchone()
                    else:
                        while row is not None:
                            table.AddRow(list(row))
                            row = self.cur.fetchone()
                if self.start:
                    self.start = False
                return table
        except Spartacus.Database.Exception as exc:
            raise exc
        except fdb.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def InsertBlock(self, block, tablename, fields=None):
        try:
            column_names = []
            if fields is None:
                fields = []
                for c in block.Columns:
                    column_names.append(c)
                    fields.append(DataField(c))
            else:
                for p in fields:
                    column_names.append(p.name)
            values = []
            for r in block.Rows:
                values.append(self.Mogrify(r, fields))
            self.Execute(
                "insert into "
                + tablename
                + "("
                + ",".join(column_names)
                + ") values "
                + ",".join(values)
                + ""
            )
        except Spartacus.Database.Exception as exc:
            raise exc
        except fdb.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def Special(self, sql):
        return self.Query(sql).Pretty()


"""
------------------------------------------------------------------------
Oracle
------------------------------------------------------------------------
"""


class Oracle(Generic):
    def __init__(
        self,
        host,
        port,
        service,
        user,
        password,
        conn_string="",
        encoding=None,
        connection_params=None,
    ):
        if "Oracle" in supported_rdbms:
            self.host = host
            if host is not None and (port is None or port == ""):
                self.port = 1521
            else:
                self.port = port
            self.conn_string = conn_string
            self.conn_string_parsed = urlparse(conn_string)
            self.connection_params = connection_params if connection_params else {}
            if service is None or service == "":
                self.service = "xe"
            else:
                self.service = service
            self.user = user
            self.password = password
            self.con = None
            self.cur = None
            self.autocommit = True
            self.help = DataTable(simple=True)
            self.help.Columns = ["Command", "Syntax", "Description"]
            self.help.AddRow(["\\?", "\\?", "Show Commands."])
            self.help.AddRow(["\\x", "\\x", "Toggle expanded output."])
            self.help.AddRow(["\\timing", "\\timing", "Toggle timing of commands."])
            self.expanded = False
            self.timing = False
            self.encoding = encoding
        else:
            raise Spartacus.Database.Exception(
                "Oracle is not supported. Please install it with 'pip install Spartacus[oracle]'."
            )

    def GetConnectionString(self):
        if self.host is None and self.port is None:  # tnsnames.ora
            if self.password is None or self.password == "":
                return """{0}/@{1}""".format(
                    self.user.replace("'", "\\'"), self.service.replace("'", "\\'")
                )
            else:
                return """{0}/{1}@{2}""".format(
                    self.user.replace("'", "\\'"),
                    self.password.replace("'", "\\'"),
                    self.service.replace("'", "\\'"),
                )
        else:
            if self.password is None or self.password == "":
                return """{0}/@{1}:{2}/{3}""".format(
                    self.user.replace("'", "\\'"),
                    self.host.replace("'", "\\'"),
                    self.port,
                    self.service.replace("'", "\\'"),
                )
            else:
                return """{0}/{1}@{2}:{3}/{4}""".format(
                    self.user.replace("'", "\\'"),
                    self.password.replace("'", "\\'"),
                    self.host.replace("'", "\\'"),
                    self.port,
                    self.service.replace("'", "\\'"),
                )

    def Open(self, autocommit=True):
        try:
            self.con = oracledb.connect(
                self.GetConnectionString(), **self.connection_params
            )
            self.con.autocommit = autocommit
            self.cur = self.con.cursor()
            self.start = True
        except oracledb.Error as exc:
            (error_obj,) = exc.args
            if (
                error_obj.code == 1017
            ):  # ORA-01017 invalid credential or not authorized; logon denied:
                raise InvalidPasswordException(str(exc)) from exc
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def Query(self, sql, alltypesstr=False, simple=False):
        try:
            keep = None
            if self.con is None:
                self.Open()
                keep = False
            else:
                keep = True
            self.cur.execute(sql)
            table = DataTable(None, alltypesstr, simple)
            if self.cur.description:
                for c in self.cur.description:
                    table.AddColumn(c.name)
                row = self.cur.fetchone()
                while row is not None:
                    table.AddRow(list(row))
                    row = self.cur.fetchone()
            return table
        except Spartacus.Database.Exception as exc:
            raise exc
        except oracledb.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))
        finally:
            if not keep:
                self.Close()

    def Execute(self, sql):
        try:
            keep = None
            if self.con is None:
                self.Open()
                keep = False
            else:
                keep = True
            self.cur.execute(sql)
        except Spartacus.Database.Exception as exc:
            raise exc
        except oracledb.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))
        finally:
            if not keep:
                self.Close()

    def ExecuteScalar(self, sql):
        try:
            keep = None
            if self.con is None:
                self.Open()
                keep = False
            else:
                keep = True
            self.cur.execute(sql)
            r = self.cur.fetchone()
            if r != None:
                s = r[0]
            else:
                s = None
            return s
        except Spartacus.Database.Exception as exc:
            raise exc
        except oracledb.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))
        finally:
            if not keep:
                self.Close()

    def Close(self, commit=True):
        try:
            if self.con:
                self.con.commit()
                if self.cur:
                    self.cur.close()
                    self.cur = None
                self.con.close()
                self.con = None
        except oracledb.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def Commit(self):
        self.Close(True)

    def Rollback(self):
        self.Close(False)

    def Cancel(self, usesameconn=True, keep_connection=False):
        try:
            if self.con:
                self.con.cancel()
                if self.cur:
                    self.cur.close()
                    self.cur = None
                self.con.close()
                self.con = None
        except oracledb.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def GetPID(self):
        return None

    def Terminate(self, pid):
        try:
            self.Execute("alter system kill session '{0}' immediate".format(pid))
        except Spartacus.Database.Exception as exc:
            raise exc
        except oracledb.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def GetFields(self, sql):
        try:
            keep = None
            if self.con is None:
                self.Open()
                keep = False
            else:
                keep = True
            fields = []
            self.cur.execute("select * from ( " + sql + " ) t where rownum <= 1")
            r = self.cur.fetchone()
            if r != None:
                k = 0
                for c in self.cur.description:
                    fields.append(
                        DataField(c.name, field_type=type(r[k]), db_type=c.type.name)
                    )
                    k = k + 1
            else:
                k = 0
                for c in self.cur.description:
                    fields.append(
                        DataField(c.name, field_type=type(None), db_type=c.type.name)
                    )
                    k = k + 1
            return fields
        except Spartacus.Database.Exception as exc:
            raise exc
        except oracledb.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))
        finally:
            if not keep:
                self.Close()

    def GetNotices(self):
        return []

    def ClearNotices(self):
        pass

    def GetStatus(self):
        try:
            if self.con is None:
                raise Spartacus.Database.Exception(
                    "This method should be called in the middle of Open() and Close() calls."
                )
            else:
                return self.cur.rowcount
        except Spartacus.Database.Exception as exc:
            raise exc
        except oracledb.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def GetRowsAffected(self):
        try:
            if self.con is None:
                raise Spartacus.Database.Exception(
                    "This method should be called in the middle of Open() and Close() calls."
                )
            else:
                if self.cur.description:
                    return None
                rowcount = self.cur.rowcount
                return rowcount if rowcount is not None and rowcount >= 0 else None
        except Spartacus.Database.Exception as exc:
            raise exc
        except oracledb.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def GetConStatus(self):
        try:
            if self.con is None:
                return 0
            else:
                try:
                    self.con.ping()
                    return 1
                except:
                    return 0
        except Spartacus.Database.Exception as exc:
            raise exc
        except oracledb.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def ResolveType(self, type_code):
        TYPEMAP = {
            2020: "BFILE",
            2008: "DOUBLE",
            2007: "FLOAT",
            2009: "INTEGER",
            2019: "BLOB",
            2022: "BOOLEAN",
            2003: "CHAR",
            2017: "CLOB",
            2021: "CURSOR",
            2011: "DATE",
            2015: "INTERVALDS",
            2016: "INTERVALYM",
            2027: "LONG NVARCHAR",
            2025: "LONG RAW",
            2024: "LONG VARCHAR",
            2004: "NCHAR",
            2018: "NCLOB",
            2010: "NUMBER",
            2002: "NVARCHAR",
            2023: "OBJECT",
            2006: "RAW",
            2005: "ROWID",
            2012: "TIMESTAMP",
            2014: "TIMESTAMP LTZ",
            2013: "TIMESTAMP TZ",
            0: "UNKNOWN",
            2030: "UROWID",
            2001: "VARCHAR",
            2033: "VECTOR",
            2032: "XMLTYPE",
        }
        return TYPEMAP.get(type_code, "UNKNOWN").lower()

    def QueryBlock(self, sql, blocksize, alltypesstr=False, simple=False):
        try:
            if self.con is None:
                raise Spartacus.Database.Exception(
                    "This method should be called in the middle of Open() and Close() calls."
                )
            else:
                if self.start:
                    self.con.autocommit = self.autocommit
                    self.cur.execute(sql)
                table = DataTable(None, alltypesstr, simple)
                if self.cur.description:
                    for c in self.cur.description:
                        table.AddColumn(c.name)
                        table.AddColumnTypeCode(c.type_code.num)
                    row = self.cur.fetchone()
                    if blocksize > 0:
                        k = 0
                        while row is not None and k < blocksize:
                            table.AddRow(list(row))
                            k = k + 1
                            if k < blocksize:
                                row = self.cur.fetchone()
                    else:
                        while row is not None:
                            table.AddRow(list(row))
                            row = self.cur.fetchone()
                if self.start:
                    self.start = False
                if len(table.Rows) < blocksize:
                    self.start = True
                return table
        except Spartacus.Database.Exception as exc:
            raise exc
        except oracledb.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))
        finally:
            self.autocommit = True

    def InsertBlock(self, block, tablename, fields=None):
        try:
            column_names = []
            if fields is None:
                fields = []
                for c in block.Columns:
                    column_names.append(c)
                    fields.append(DataField(c))
            else:
                for p in fields:
                    column_names.append(p.name)
            values = []
            for r in block.Rows:
                values.append(self.Mogrify(r, fields))
            self.Execute(
                "insert into "
                + tablename
                + "("
                + ",".join(column_names)
                + ") values "
                + ",".join(values)
                + ""
            )
        except Spartacus.Database.Exception as exc:
            raise exc
        except oracledb.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def Special(self, sql):
        try:
            keep = None
            if self.con is None:
                self.Open()
                keep = False
            else:
                keep = True
            command = sql.lstrip().split(" ")[0].rstrip("+")
            title = None
            table = None
            status = None
            if command == "\\?":
                table = self.help
            else:
                aux = self.help.Select("Command", command)
                if len(aux.Rows) > 0:
                    if command == "\\x" and not self.expanded:
                        status = "Expanded display is on."
                        self.expanded = True
                    elif command == "\\x" and self.expanded:
                        status = "Expanded display is off."
                        self.expanded = False
                    elif command == "\\timing" and not self.timing:
                        status = "Timing is on."
                        self.timing = True
                    elif command == "\\timing" and self.timing:
                        status = "Timing is off."
                        self.timing = False
                else:
                    if self.timing:
                        start_time = datetime.datetime.now()
                    table = self.Query(sql, True, True)
                    tmp = self.GetStatus()
                    if tmp == 1:
                        status = "1 row "
                    else:
                        status = "{0} rows ".format(tmp)
                    if command.lower() == "select":
                        status = status + "in set"
                    else:
                        status = status + "affected"
                    if self.timing:
                        status = status + "\nTime: {0}".format(
                            datetime.datetime.now() - start_time
                        )
            if title and table and len(table.Rows) > 0 and status:
                return (
                    title + "\n" + table.Pretty(self.expanded) + "\n" + status
                )
            elif title and table and len(table.Rows) > 0:
                return title + "\n" + table.Pretty(self.expanded)
            elif title and status:
                return title + "\n" + status
            elif title:
                return title
            elif table and len(table.Rows) > 0 and status:
                return table.Pretty(self.expanded) + "\n" + status
            elif table and len(table.Rows) > 0:
                return table.Pretty(self.expanded)
            elif status:
                return status
            else:
                return ""
        except Spartacus.Database.Exception as exc:
            raise exc
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))
        finally:
            if not keep:
                self.Close()


"""
------------------------------------------------------------------------
MSSQL
------------------------------------------------------------------------
"""


class MSSQL(Generic):
    def __init__(
        self,
        host,
        port,
        service,
        user,
        password,
        conn_string="",
        encoding=None,
        connection_params=None,
    ):
        if "MSSQL" in supported_rdbms:
            self.host = host
            if port is None or port == "":
                self.port = 1433
            else:
                self.port = port
            self.conn_string = conn_string
            self.conn_string_parsed = urlparse(conn_string)
            self.service = service
            self.user = user
            self.password = password
            self.con = None
            self.cur = None
            self.encoding = encoding
            self.connection_params = connection_params if connection_params else {}
        else:
            raise Spartacus.Database.Exception(
                "MSSQL is not supported. Please install it with 'pip install Spartacus[mssql]'."
            )

    def GetConnectionString(self):
        return None

    def Open(self, autocommit=True):
        try:
            self.con = pymssql.connect(
                host=self.host,
                port=self.port,
                database=self.service,
                user=self.user,
                password=self.password,
                **self.connection_params
            )
            self.con.autocommit(autocommit)
            self.cur = self.con.cursor()
            self.start = True
        except pymssql.Error as exc:
            raise Spartacus.Database.Exception(self.FormatException(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def Query(self, sql, alltypesstr=False, simple=False):
        try:
            keep = None
            if self.con is None:
                self.Open()
                keep = False
            else:
                keep = True
            self.cur.execute(sql)
            table = DataTable(None, alltypesstr, simple)
            if self.cur.description:
                for c in self.cur.description:
                    table.AddColumn(c[0])
                row = self.cur.fetchone()
                while row is not None:
                    table.AddRow(list(row))
                    row = self.cur.fetchone()
            return table
        except Spartacus.Database.Exception as exc:
            raise exc
        except pymssql.Error as exc:
            raise Spartacus.Database.Exception(self.FormatException(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))
        finally:
            if not keep:
                self.Close()

    def Execute(self, sql):
        try:
            keep = None
            if self.con is None:
                self.Open()
                keep = False
            else:
                keep = True
            self.cur.execute(sql)
        except Spartacus.Database.Exception as exc:
            raise exc
        except pymssql.Error as exc:
            raise Spartacus.Database.Exception(self.FormatException(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))
        finally:
            if not keep:
                self.Close()

    def ExecuteScalar(self, sql):
        try:
            keep = None
            if self.con is None:
                self.Open()
                keep = False
            else:
                keep = True
            self.cur.execute(sql)
            r = self.cur.fetchone()
            if r != None:
                s = r[0]
            else:
                s = None
            return s
        except Spartacus.Database.Exception as exc:
            raise exc
        except pymssql.Error as exc:
            raise Spartacus.Database.Exception(self.FormatException(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))
        finally:
            if not keep:
                self.Close()

    def Close(self, commit=True):
        try:
            if self.con:
                self.con.commit()
                if self.cur:
                    self.cur.close()
                    self.cur = None
                self.con.close()
                self.con = None
        except pymssql.Error as exc:
            raise Spartacus.Database.Exception(self.FormatException(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def Commit(self):
        self.Close(True)

    def Rollback(self):
        self.Close(False)

    def Cancel(self, usesameconn=True, keep_connection=False):
        try:
            if self.con:
                self.con.cancel()
                if self.cur:
                    self.cur.close()
                    self.cur = None
                self.con.close()
                self.con = None
        except pymssql.Error as exc:
            raise Spartacus.Database.Exception(self.FormatException(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def GetPID(self):
        return None

    def Terminate(self, pid):
        pass

    def GetFields(self, sql):
        try:
            keep = None
            if self.con is None:
                self.Open()
                keep = False
            else:
                keep = True
            fields = []
            self.cur.execute(
                "select top 1 limit_alias.* from ( " + sql + " ) limit_alias"
            )
            r = self.cur.fetchone()
            if r != None:
                k = 0
                for c in self.cur.description:
                    fields.append(
                        DataField(c[0], field_type=type(r[k]), db_type=type(r[k]))
                    )
                    k = k + 1
            else:
                k = 0
                for c in self.cur.description:
                    fields.append(
                        DataField(c[0], field_type=type(None), db_type=type(None))
                    )
                    k = k + 1
            return fields
        except Spartacus.Database.Exception as exc:
            raise exc
        except pymssql.Error as exc:
            raise Spartacus.Database.Exception(self.FormatException(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))
        finally:
            if not keep:
                self.Close()

    def GetNotices(self):
        return []

    def ClearNotices(self):
        pass

    def GetStatus(self):
        return None

    def GetRowsAffected(self):
        try:
            if self.con is None:
                raise Spartacus.Database.Exception(
                    "This method should be called in the middle of Open() and Close() calls."
                )
            else:
                if self.cur.description:
                    return None
                rowcount = self.cur.rowcount
                return rowcount if rowcount is not None and rowcount >= 0 else None
        except Spartacus.Database.Exception as exc:
            raise exc
        except pymssql.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def GetConStatus(self):
        try:
            if self.con is None:
                return 0
            else:
                return 1
        except Spartacus.Database.Exception as exc:
            raise exc
        except pymssql.Error as exc:
            raise Spartacus.Database.Exception(self.FormatException(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def QueryBlock(self, sql, blocksize, alltypesstr=False, simple=False):
        try:
            if self.con is None:
                raise Spartacus.Database.Exception(
                    "This method should be called in the middle of Open() and Close() calls."
                )
            else:
                if self.start:
                    self.cur.execute(sql)
                table = DataTable(None, alltypesstr, simple)
                if self.cur.description:
                    for c in self.cur.description:
                        table.AddColumn(c[0])
                    row = self.cur.fetchone()
                    if blocksize > 0:
                        k = 0
                        while row is not None and k < blocksize:
                            table.AddRow(list(row))
                            k = k + 1
                            if k < blocksize:
                                row = self.cur.fetchone()
                    else:
                        while row is not None:
                            table.AddRow(list(row))
                            row = self.cur.fetchone()
                if self.start:
                    self.start = False
                if len(table.Rows) < blocksize:
                    self.start = True
                return table
        except Spartacus.Database.Exception as exc:
            raise exc
        except pymssql.Error as exc:
            raise Spartacus.Database.Exception(self.FormatException(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def InsertBlock(self, block, tablename, fields=None):
        try:
            column_names = []
            if fields is None:
                fields = []
                for c in block.Columns:
                    column_names.append(c)
                    fields.append(DataField(c))
            else:
                for p in fields:
                    column_names.append(p.name)
            values = []
            for r in block.Rows:
                values.append(self.Mogrify(r, fields))
            self.Execute(
                "insert into "
                + tablename
                + "("
                + ",".join(column_names)
                + ") values "
                + ",".join(values)
                + ""
            )
        except Spartacus.Database.Exception as exc:
            raise exc
        except pymssql.Error as exc:
            raise Spartacus.Database.Exception(self.FormatException(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def Special(self, sql):
        return self.Query(sql, True, True).Pretty()

    def FormatException(self, exc):
        try:
            # sometimes pymssql.Error may have the data we need in a nested tuple
            if isinstance(exc.args[0], tuple):
                args_unpacked = exc.args[0]
            else:
                args_unpacked = exc.args

            err_code, raw_msg = args_unpacked[:2]

        except Exception:
            err_code, raw_msg = None, str(exc)

        if isinstance(raw_msg, (bytes, bytearray)):
            try:
                decoded_msg = raw_msg.decode('utf-8', errors='replace')
            except Exception:
                decoded_msg = str(raw_msg)
        else:
            decoded_msg = str(raw_msg)

        lines = [l.strip() for l in decoded_msg.splitlines() if l.strip()]

        err_str = '\n'.join(lines)
        return f"{err_code}: {err_str}"

"""
------------------------------------------------------------------------
IBM DB2
------------------------------------------------------------------------
"""


class IBMDB2(Generic):
    def __init__(
        self,
        host,
        port,
        service,
        user,
        password,
        conn_string="",
        encoding=None,
    ):
        if "IBMDB2" in supported_rdbms:
            self.host = host
            if port is None or port == "":
                self.port = 50000
            else:
                self.port = port
            self.conn_string = conn_string
            self.conn_string_parsed = urlparse(conn_string)
            self.service = service
            self.user = user
            self.password = password
            self.con = None
            self.cur = None
            self.encoding = encoding
        else:
            raise Spartacus.Database.Exception(
                "IBM DB2 is not supported. Please install it with 'pip install Spartacus[ibmdb2]'."
            )

    def GetConnectionString(self):
        return """DATABASE={0};HOSTNAME={1};PORT={2};PROTOCOL=TCPIP;UID={3};PWD={4}""".format(
            self.service.replace("'", "\\'"),
            self.host.replace("'", "\\'"),
            self.port,
            self.user.replace("'", "\\'"),
            self.password.replace("'", "\\'"),
        )

    def Open(self, autocommit=True):
        try:
            c = ibm_db.connect(self.GetConnectionString(), "", "")
            self.con = ibm_db_dbi.Connection(c)
            self.cur = self.con.cursor()
            self.start = True
        except ibm_db.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except ibm_db_dbi.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def Query(self, sql, alltypesstr=False, simple=False):
        try:
            keep = None
            if self.con is None:
                self.Open()
                keep = False
            else:
                keep = True
            self.cur.execute(sql)
            table = DataTable(None, alltypesstr, simple)
            if self.cur.description:
                for c in self.cur.description:
                    table.AddColumn(c[0])
                row = self.cur.fetchone()
                while row is not None:
                    table.AddRow(list(row))
                    row = self.cur.fetchone()
            return table
        except Spartacus.Database.Exception as exc:
            raise exc
        except ibm_db_dbi.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))
        finally:
            if not keep:
                self.Close()

    def Execute(self, sql):
        try:
            keep = None
            if self.con is None:
                self.Open()
                keep = False
            else:
                keep = True
            self.cur.execute(sql)
        except Spartacus.Database.Exception as exc:
            raise exc
        except ibm_db_dbi.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))
        finally:
            if not keep:
                self.Close()

    def ExecuteScalar(self, sql):
        try:
            keep = None
            if self.con is None:
                self.Open()
                keep = False
            else:
                keep = True
            self.cur.execute(sql)
            r = self.cur.fetchone()
            if r != None:
                s = r[0]
            else:
                s = None
            return s
        except Spartacus.Database.Exception as exc:
            raise exc
        except ibm_db_dbi.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))
        finally:
            if not keep:
                self.Close()

    def Close(self, commit=True):
        try:
            if self.con:
                self.con.commit()
                if self.cur:
                    self.cur.close()
                    self.cur = None
                self.con.close()
                self.con = None
        except ibm_db_dbi.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def Commit(self):
        self.Close(True)

    def Rollback(self):
        self.Close(False)

    def Cancel(self, usesameconn=True, keep_connection=False):
        try:
            if self.con:
                self.con.cancel()
                if self.cur:
                    self.cur.close()
                    self.cur = None
                self.con.close()
                self.con = None
        except ibm_db_dbi.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def GetPID(self):
        return None

    def Terminate(self, pid):
        pass

    def GetFields(self, sql):
        try:
            keep = None
            if self.con is None:
                self.Open()
                keep = False
            else:
                keep = True
            fields = []
            self.cur.execute("select * from ( " + sql + " ) t limit 1")
            r = self.cur.fetchone()
            if r != None:
                k = 0
                for c in self.cur.description:
                    fields.append(
                        DataField(c[0], field_type=type(r[k]), db_type=type(r[k]))
                    )
                    k = k + 1
            else:
                k = 0
                for c in self.cur.description:
                    fields.append(
                        DataField(c[0], field_type=type(None), db_type=type(None))
                    )
                    k = k + 1
            return fields
        except Spartacus.Database.Exception as exc:
            raise exc
        except ibm_db_dbi.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))
        finally:
            if not keep:
                self.Close()

    def GetNotices(self):
        return []

    def ClearNotices(self):
        pass

    def GetStatus(self):
        return None

    def GetRowsAffected(self):
        return None

    def GetConStatus(self):
        try:
            if self.con is None:
                return 0
            else:
                return 1
        except Spartacus.Database.Exception as exc:
            raise exc
        except ibm_db_dbi.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def QueryBlock(self, sql, blocksize, alltypesstr=False, simple=False):
        try:
            if self.con is None:
                raise Spartacus.Database.Exception(
                    "This method should be called in the middle of Open() and Close() calls."
                )
            else:
                if self.start:
                    self.cur.execute(sql)
                table = DataTable(None, alltypesstr, simple)
                if self.cur.description:
                    for c in self.cur.description:
                        table.AddColumn(c[0])
                    row = self.cur.fetchone()
                    if blocksize > 0:
                        k = 0
                        while row is not None and k < blocksize:
                            table.AddRow(list(row))
                            k = k + 1
                            if k < blocksize:
                                row = self.cur.fetchone()
                    else:
                        while row is not None:
                            table.AddRow(list(row))
                            row = self.cur.fetchone()
                if self.start:
                    self.start = False
                return table
        except Spartacus.Database.Exception as exc:
            raise exc
        except ibm_db_dbi.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def InsertBlock(self, block, tablename, fields=None):
        try:
            column_names = []
            if fields is None:
                fields = []
                for c in block.Columns:
                    column_names.append(c)
                    fields.append(DataField(c))
            else:
                for p in fields:
                    column_names.append(p.name)
            values = []
            for r in block.Rows:
                values.append(self.Mogrify(r, fields))
            self.Execute(
                "insert into "
                + tablename
                + "("
                + ",".join(column_names)
                + ") values "
                + ",".join(values)
                + ""
            )
        except Spartacus.Database.Exception as exc:
            raise exc
        except ibm_db_dbi.Error as exc:
            raise Spartacus.Database.Exception(str(exc))
        except Exception as exc:
            raise Spartacus.Database.Exception(str(exc))

    def Special(self, sql):
        return self.Query(sql).Pretty()
