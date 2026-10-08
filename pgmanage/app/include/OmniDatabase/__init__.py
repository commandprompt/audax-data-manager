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

from app.include.OmniDatabase.SQLite import SQLite
from app.include.OmniDatabase.Oracle import Oracle
from app.include.OmniDatabase.MariaDB import MariaDB
from app.include.OmniDatabase.MySQL import MySQL
from app.include.OmniDatabase.MSSQL import MSSQL
from app.include.OmniDatabase.PostgreSQL import PostgreSQL


'''
------------------------------------------------------------------------
Generic
------------------------------------------------------------------------
'''
class Generic:
    @staticmethod
    def InstantiateDatabase(db_type,
                            server,
                            port,
                            service,
                            user,
                            password,
                            conn_id=0,
                            alias='',
                            foreign_keys=True,
                            application_name='PgManage',
                            conn_string='',
                            parse_conn_string = False,
                            connection_params=None,
                            credentials_extra=None):

        if db_type == 'postgresql':
            return PostgreSQL(server, port, service, user, password, conn_id, alias, application_name, conn_string, parse_conn_string, connection_params)
        if db_type == 'oracle':
            return Oracle(server, port, service, user, password, conn_id, alias, conn_string, parse_conn_string, connection_params)
        if db_type == 'mariadb':
            return MariaDB(server, port, service, user, password, conn_id, alias, conn_string, parse_conn_string, connection_params)
        if db_type == 'mysql':
            return MySQL(server, port, service, user, password, conn_id, alias, conn_string, parse_conn_string, connection_params)
        if db_type == 'sqlite':
            return SQLite(service, conn_id, alias, foreign_keys)
        if db_type == 'mssql':
            return MSSQL(server, port, service, user, password, conn_id, alias, conn_string, parse_conn_string, connection_params)
