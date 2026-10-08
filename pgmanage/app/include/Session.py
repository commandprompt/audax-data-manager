import io
import logging
import threading
from collections import OrderedDict
from datetime import datetime, timedelta

import paramiko
from app.include import OmniDatabase
from app.models.main import Connection, UserDetails
from app.utils.auth_methods import uses_iam_auth
from app.utils.crypto import decrypt
from app.utils.key_manager import key_manager
from django.contrib.sessions.backends.db import SessionStore
from django.db.models import Q
from sshtunnel import SSHTunnelForwarder

from pgmanage import settings

logger = logging.getLogger("app.Session")

tunnels = {}

tunnel_locks = {}

"""
------------------------------------------------------------------------
Session
------------------------------------------------------------------------
"""


class Session(object):
    def __init__(
        self,
        user_id,
        user_name,
        theme,
        font_size,
        super_user,
        user_key,
        csv_encoding,
        csv_delimiter,
    ):
        self.user_id = user_id
        self.user_name = user_name
        self.theme = theme
        self.font_size = font_size
        self.super_user = super_user
        self.database_index = -1
        self.databases = OrderedDict()
        self.user_key = user_key
        self.csv_encoding = csv_encoding
        self.csv_delimiter = csv_delimiter
        self.tabs_databases = {}

    def AddDatabase(
        self,
        conn_id=None,
        technology=None,
        database=None,
        prompt_password=True,
        tunnel_information=None,
        alias=None,
        public=None,
        decryption_failed=False,
    ):
        if len(self.databases) == 0:
            self.database_index = 0

        self.databases[conn_id] = {
            "database": database,
            "prompt_password": prompt_password,
            "prompt_timeout": None,
            "tunnel": tunnel_information,
            "tunnel_object": None,
            "alias": alias,
            "technology": technology,
            "public": public,
            "decryption_failed": decryption_failed,
        }

    def RemoveDatabase(self, conn_id=None):
        self.databases.pop(conn_id, None)

    def DatabaseReachPasswordTimeout(self, database_index):
        return_data = {"timeout": False, "message": "", "kind": "database"}
        # This region of the code cannot be accessed by multiple threads, so locking is required
        try:
            lock_object = tunnel_locks[
                self.databases[database_index]["database"].conn_id
            ]
        except Exception:
            lock_object = threading.Lock()
            tunnel_locks[self.databases[database_index]["database"].conn_id] = (
                lock_object
            )

        try:
            lock_object.acquire()
        except Exception:
            pass

        try:
            # Create tunnel if enabled
            if self.databases[database_index]["tunnel"]["enabled"]:
                create_tunnel = False
                if self.databases[database_index]["tunnel_object"] is not None:

                    try:
                        tunnel_object = tunnels[
                            self.databases[database_index]["database"].conn_id
                        ]
                        if not tunnel_object.is_active:
                            tunnel_object.stop()
                            create_tunnel = True
                    except Exception:
                        create_tunnel = True

                if (
                    self.databases[database_index]["tunnel_object"] is None
                    or create_tunnel
                ):
                    try:
                        if (
                            self.databases[database_index]["tunnel"]["key"].strip()
                            != ""
                        ):
                            key = paramiko.RSAKey.from_private_key(
                                io.StringIO(
                                    self.databases[database_index]["tunnel"]["key"]
                                ),
                                password=self.databases[database_index]["tunnel"][
                                    "password"
                                ],
                            )
                            server = SSHTunnelForwarder(
                                (
                                    self.databases[database_index]["tunnel"]["server"],
                                    int(
                                        self.databases[database_index]["tunnel"]["port"]
                                    ),
                                ),
                                ssh_username=self.databases[database_index]["tunnel"][
                                    "user"
                                ],
                                ssh_private_key_password=self.databases[database_index][
                                    "tunnel"
                                ]["password"],
                                ssh_pkey=key,
                                remote_bind_address=(
                                    self.databases[database_index][
                                        "database"
                                    ].active_server,
                                    int(
                                        self.databases[database_index][
                                            "database"
                                        ].active_port
                                    ),
                                ),
                                logger=logger,
                            )
                        else:
                            server = SSHTunnelForwarder(
                                (
                                    self.databases[database_index]["tunnel"]["server"],
                                    int(
                                        self.databases[database_index]["tunnel"]["port"]
                                    ),
                                ),
                                ssh_username=self.databases[database_index]["tunnel"][
                                    "user"
                                ],
                                ssh_password=self.databases[database_index]["tunnel"][
                                    "password"
                                ],
                                remote_bind_address=(
                                    self.databases[database_index][
                                        "database"
                                    ].active_server,
                                    int(
                                        self.databases[database_index][
                                            "database"
                                        ].active_port
                                    ),
                                ),
                                logger=logger,
                            )
                        server.set_keepalive = 120
                        server.start()

                        s = SessionStore(session_key=self.user_key)
                        tunnels[self.databases[database_index]["database"].conn_id] = (
                            server
                        )

                        self.databases[database_index]["tunnel_object"] = str(
                            server.local_bind_port
                        )
                        self.databases[database_index][
                            "database"
                        ].connection.host = "127.0.0.1"
                        self.databases[database_index][
                            "database"
                        ].connection.port = server.local_bind_port

                        s["pgmanage_session"] = self
                        s.save()

                    except Exception as exc:
                        # release the lock on failure, so the subsequent call can acquire it
                        lock_object.release()
                        msg = str(exc)
                        if "checkints" in msg:
                            msg = "Unable to decrypt SSH Key. Wrong passphrase?"
                        return {"timeout": True, "message": msg, "kind": "tunnel"}

            if self.databases[database_index]["prompt_password"]:
                # Reached timeout, must request password
                if not self.databases[database_index][
                    "prompt_timeout"
                ] or datetime.now() > self.databases[database_index][
                    "prompt_timeout"
                ] + timedelta(
                    0, settings.PWD_TIMEOUT_TOTAL
                ):
                    # Try passwordless connection
                    self.databases[database_index]["database"].connection.password = ""
                    test_response, status = self.databases[database_index][
                        "database"
                    ].TestConnection()

                    if status:
                        s = SessionStore(session_key=self.user_key)
                        s["pgmanage_session"].databases[database_index][
                            "prompt_timeout"
                        ] = datetime.now()
                        s["pgmanage_session"].databases[database_index][
                            "database"
                        ].connection.password = ""
                        s.save()
                        return_data = {
                            "timeout": False,
                            "message": "",
                            "kind": "database",
                        }
                    else:
                        return_data = {
                            "timeout": True,
                            "message": test_response,
                            "kind": "database",
                        }
                # Reached half way to timeout, update prompt_timeout
                if datetime.now() > self.databases[database_index][
                    "prompt_timeout"
                ] + timedelta(0, settings.PWD_TIMEOUT_REFRESH):
                    s = SessionStore(session_key=self.user_key)
                    s["pgmanage_session"].databases[database_index][
                        "prompt_timeout"
                    ] = datetime.now()
                    s.save()
        except Exception:
            pass

        try:
            lock_object.release()
        except Exception:
            pass

        return return_data

    def GetSelectedDatabase(self):
        return self.databases(self.database_index)

    def RefreshDatabaseList(self):
        self.databases = {}

        try:
            decryption_failed = False
            current_user = (
                UserDetails.objects.filter(user__id=self.user_id)
                .select_related("user")
                .first()
            )
            key = key_manager.get(current_user.user)
            connections = Connection.objects.filter(
                Q(user=current_user.user) | Q(public=True)
            ).prefetch_related("technology")
            for conn in connections:
                try:
                    tunnel_information = {
                        "enabled": conn.use_tunnel,
                        "server": conn.ssh_server,
                        "port": conn.ssh_port,
                        "user": conn.ssh_user,
                        "password": (
                            decrypt(conn.ssh_password, key) if conn.ssh_password else ""
                        ),
                        "key": decrypt(conn.ssh_key, key) if conn.ssh_key else "",
                    }
                    # this is for sqlite3 db connection because it has now password
                    password = decrypt(conn.password, key) if conn.password else ""
                    credentials_extra = conn.get_credentials_extra(key)
                except UnicodeDecodeError:
                    password = "wrong decrypted password"
                    credentials_extra = {}
                    decryption_failed = True
                # in case of decrypt error, set up bad_decrypt variable as True.
                database = OmniDatabase.Generic.InstantiateDatabase(
                    conn.technology.name,
                    conn.server,
                    conn.port,
                    conn.database,
                    conn.username,
                    password,
                    conn.id,
                    conn.alias,
                    conn_string=conn.conn_string,
                    parse_conn_string=True,
                    connection_params=conn.connection_params,
                    credentials_extra=credentials_extra,
                )

                # IAM authentication gets a token for each connection, thus never ask a password
                prompt_password = conn.password == "" and not uses_iam_auth(
                    credentials_extra
                )

                self.AddDatabase(
                    conn.id,
                    conn.technology.name,
                    database,
                    prompt_password,
                    tunnel_information,
                    conn.alias,
                    conn.public,
                    decryption_failed=decryption_failed,
                )
        # No connections
        except Exception as exc:
            logger.error(str(exc))

    def Execute(self, database, sql, log_history):
        table = database.connection.Execute(sql)

        return table

    def Query(self, database, sql, log_history):
        table = database.connection.Query(sql, True)

        return table

    def QueryDataLimited(self, database, sql, count, log_history):
        table = database.QueryDataLimited(sql, count)

        return table
