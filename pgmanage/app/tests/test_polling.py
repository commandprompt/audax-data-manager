import os
import re
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from functools import partial
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.client_manager.client_manager import Client, client_manager
from app.include import OmniDatabase
from app.include.OmniDatabase.PostgreSQL import PostgreSQL
from app.include.Session import Session
from app.models import Connection, ConsoleHistory, QueryHistory, Tab, Technology
from app.tests.utils_testing import USERS, execute_client_login
from app.utils.crypto import encrypt
from app.views import polling
from app.views.polling import (
    ConsoleModes,
    QueryModes,
    RequestType,
    ResponseType,
    StoppableThread,
    clear_client,
    client_keep_alive,
    create_request,
    get_duration,
    log_history,
    long_polling,
    queue_response,
)
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import resolve, reverse

User = get_user_model()


def run_thread_function(function, cancel=False, **args):
    client = Client("test-client")
    args.setdefault("context_code", 7)
    args["client_object"] = client
    function(SimpleNamespace(cancel=cancel), args)
    return list(client.returning_data)


class PollingTests(TestCase):
    """Tests that do not need a live database server."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.get(username=USERS["ADMIN"]["USER"])
        cls.connection = Connection.objects.create(
            user=cls.user,
            technology=Technology.objects.get(name="postgresql"),
            server="127.0.0.1",
            port="5432",
            database="dellstore",
            username="postgres",
            alias="Polling Tests",
        )

    def setUp(self):
        execute_client_login(
            p_client=self.client,
            p_username=USERS["ADMIN"]["USER"],
            p_password=USERS["ADMIN"]["PASSWORD"],
        )
        self.client_id = self.client.session.session_key
        self.addCleanup(client_manager.remove_client, self.client_id)
        self.client.post = partial(self.client.post, content_type="application/json")

    def post_request(self, request_type, data, context_code=1):
        return self.client.post(
            reverse("create_request"),
            data={"request_type": request_type, "context_code": context_code, "data": data},
        )

    def test_urls_resolve_to_expected_views(self):
        for path, view in [
            ("/long_polling/", long_polling),
            ("/create_request/", create_request),
            ("/clear_client/", clear_client),
            ("/client_keep_alive/", client_keep_alive),
        ]:
            with self.subTest(path=path):
                self.assertEqual(resolve(path).func.__name__, view.__name__)

    def test_views_require_a_session(self):
        self.client.logout()
        for name in ["long_polling", "create_request", "clear_client", "client_keep_alive"]:
            with self.subTest(name=name):
                response = self.client.post(reverse(name), data={})
                self.assertEqual(response.status_code, 401)

    def test_get_duration_in_milliseconds(self):
        start = datetime(2026, 1, 1, 12, 0, 0, 0)
        self.assertEqual(get_duration(start, start + timedelta(microseconds=2500)), "2.5 ms")

    def test_get_duration_in_hours_minutes_seconds(self):
        start = datetime(2026, 1, 1, 12, 0, 0)
        self.assertEqual(get_duration(start, start + timedelta(seconds=3725)), "01:02:05")
        self.assertEqual(get_duration(start, start + timedelta(days=1, seconds=61)), "24:01:01")

    def test_stoppable_thread(self):
        thread = StoppableThread(lambda thread, args: None, {"tab_id": "tab-1"})

        self.assertEqual(thread.name, "<lambda>-tab-1")
        self.assertFalse(thread.cancel)
        thread.stop()
        self.assertTrue(thread.cancel)

    def test_queue_response_adds_data_and_releases_the_polling_lock(self):
        client = Client("queue-test")
        client.polling_lock.acquire()

        queue_response(client, {"value": 1})

        self.assertEqual(list(client.returning_data), [{"value": 1}])
        self.assertTrue(client.polling_lock.acquire(blocking=False))
        self.assertTrue(client.returning_data_lock.acquire(blocking=False))

    def test_log_history_adds_an_entry(self):
        start = datetime.now(timezone.utc)
        log_history(self.user.id, "select 1", start, start, "1 ms", "success", self.connection.id, "dellstore")

        entry = QueryHistory.objects.get(connection=self.connection)
        self.assertEqual(entry.snippet, "select 1")
        self.assertEqual(entry.status, "success")
        self.assertEqual(entry.database, "dellstore")

    def test_log_history_updates_the_last_entry_for_the_same_query(self):
        start = datetime.now(timezone.utc)
        log_history(self.user.id, "select 1", start, start, "1 ms", "success", self.connection.id, "dellstore")
        log_history(self.user.id, "select 1", start, start, "9 ms", "error", self.connection.id, "dellstore")

        entry = QueryHistory.objects.get(connection=self.connection)
        self.assertEqual(entry.duration, "9 ms")
        self.assertEqual(entry.status, "error")

    def test_log_history_adds_a_new_entry_for_a_different_query(self):
        start = datetime.now(timezone.utc)
        log_history(self.user.id, "select 1", start, start, "1 ms", "success", self.connection.id, "dellstore")
        log_history(self.user.id, "select 2", start, start, "1 ms", "success", self.connection.id, "dellstore")

        self.assertEqual(QueryHistory.objects.filter(connection=self.connection).count(), 2)

    def test_log_history_does_not_raise_for_an_unknown_connection(self):
        start = datetime.now(timezone.utc)
        with self.assertLogs("app.QueryServer", level="ERROR"):
            log_history(self.user.id, "select 1", start, start, "1 ms", "success", 999999, "dellstore")

        self.assertFalse(QueryHistory.objects.exists())

    def test_clear_client_flags_the_tabs_for_removal(self):
        client = client_manager.get_or_create_client(self.client_id)
        tab = client.create_tab(workspace_id="ws", tab_id="tab", tab={"thread": None})

        response = self.client.post(reverse("clear_client"), data={})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(tab["to_be_removed"])

    def test_client_keep_alive_updates_the_last_update_time(self):
        client = client_manager.get_or_create_client(self.client_id)
        client.last_update = datetime(2000, 1, 1)

        response = self.client.post(reverse("client_keep_alive"), data={})

        self.assertEqual(response.status_code, 200)
        self.assertGreater(client.last_update, datetime(2000, 1, 1))

    def test_long_polling_returns_the_queued_data(self):
        client = client_manager.get_or_create_client(self.client_id)
        queue_response(client, {"value": 1})
        queue_response(client, {"value": 2})

        response = self.client.post(reverse("long_polling"), data={"startup": False})

        self.assertEqual(response.json(), {"returning_rows": [{"value": 1}, {"value": 2}]})
        self.assertEqual(len(client.returning_data), 0)

    def test_long_polling_at_startup_does_not_wait_for_new_data(self):
        client = client_manager.get_or_create_client(self.client_id)
        client.polling_lock.acquire()

        response = self.client.post(reverse("long_polling"), data={"startup": True})

        self.assertEqual(response.json(), {"returning_rows": []})

    def test_create_request_close_tab_removes_the_saved_tab(self):
        saved_tab = Tab.objects.create(user=self.user, connection=self.connection, title="Query")
        client = client_manager.get_or_create_client(self.client_id)
        client.create_tab(workspace_id="ws", tab_id="tab", tab={"thread": None})

        response = self.post_request(
            RequestType.CLOSE_TAB,
            [{"workspace_id": "ws", "tab_id": "tab", "tab_db_id": saved_tab.id}],
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Tab.objects.filter(id=saved_tab.id).exists())
        self.assertIsNone(client.get_tab(workspace_id="ws", tab_id="tab"))

    def test_create_request_cancel_thread_stops_the_running_query(self):
        client = client_manager.get_or_create_client(self.client_id)
        thread = MagicMock()
        database = MagicMock()
        client.create_tab(
            workspace_id="ws",
            tab_id="tab",
            tab={"thread": thread, "omnidatabase": database, "type": "query"},
        )

        response = self.post_request(
            RequestType.CANCEL_THREAD, {"workspace_id": "ws", "tab_id": "tab"}, context_code=5
        )

        self.assertEqual(response.status_code, 200)
        thread.stop.assert_called_once()
        database.connection.Cancel.assert_called_once_with(keep_connection=True)
        self.assertEqual(
            list(client.returning_data),
            [{"response_type": ResponseType.OPERATION_CANCELLED, "context_code": 5}],
        )

    def test_create_request_asks_for_the_password_after_the_timeout(self):
        timeout = {"timeout": True, "message": "Password required"}
        with patch.object(Session, "DatabaseReachPasswordTimeout", return_value=timeout):
            response = self.post_request(RequestType.QUERY, {"db_index": 0}, context_code=3)

        self.assertEqual(response.status_code, 200)
        client = client_manager.get_client(self.client_id)
        self.assertEqual(
            list(client.returning_data),
            [
                {
                    "response_type": ResponseType.PASSWORD_REQUIRED,
                    "context_code": 3,
                    "data": "Password required",
                }
            ],
        )

    def test_create_request_asks_for_the_password_when_the_connection_fails(self):
        with patch.object(Session, "DatabaseReachPasswordTimeout", return_value={"timeout": False}), \
                patch.object(Client, "get_database", side_effect=Exception("password authentication failed")):
            self.post_request(
                RequestType.QUERY, {"db_index": 0, "workspace_id": "ws", "tab_id": "tab"}, context_code=4
            )

        client = client_manager.get_client(self.client_id)
        self.assertEqual(
            list(client.returning_data),
            [
                {
                    "response_type": ResponseType.PASSWORD_REQUIRED,
                    "context_code": 4,
                    "data": "password authentication failed",
                }
            ],
        )
        self.assertIsNone(client.get_tab(workspace_id="ws", tab_id="tab")["thread"])

    def test_create_request_starts_the_matching_thread(self):
        cases = [
            (RequestType.CONSOLE, "thread_console", "console"),
            (RequestType.QUERY_EDIT_DATA, "thread_query_edit_data", "edit"),
            (RequestType.SAVE_EDIT_DATA, "thread_save_edit_data", "edit"),
            (RequestType.SCHEMA_EDIT_DATA, "thread_schema_edit_data", "schema_edit"),
        ]
        for request_type, function_name, tab_type in cases:
            with self.subTest(function=function_name):
                started = []

                def fake_thread(thread, args):
                    started.append(args["sql_cmd"])

                with patch.object(Session, "DatabaseReachPasswordTimeout", return_value={"timeout": False}), \
                        patch.object(Client, "get_database"), \
                        patch.object(polling, function_name, fake_thread):
                    self.post_request(
                        request_type,
                        {"db_index": 0, "workspace_id": "ws", "tab_id": function_name, "sql_cmd": "select 1"},
                    )
                    tab = client_manager.get_client(self.client_id).get_tab(
                        workspace_id="ws", tab_id=function_name
                    )
                    tab["thread"].join(timeout=10)

                self.assertEqual(started, ["select 1"])
                self.assertEqual(tab["type"], tab_type)


class PollingDatabaseTests(TestCase):
    """Tests against the live PostgreSQL server with the dellstore fixture (see
    docker-compose.yml). The whole class is skipped when that server is down.
    """

    HOST = "127.0.0.1"
    PORT = "5433"
    SERVICE = "dellstore"
    ROLE = "postgres"
    PASSWORD = "postgres"
    SCRATCH_TABLE = "pgm_polling_scratch"

    @classmethod
    def setUpClass(cls):
        probe = cls.make_database()
        probe.GetVersion()
        if probe.major_version is None:
            raise unittest.SkipTest(
                f"Postgres test database is not reachable at {cls.HOST}:{cls.PORT} - "
                f"start it with `docker compose up` in app/tests."
            )

        super().setUpClass()

        cls.user = User.objects.get(username=USERS["ADMIN"]["USER"])
        cls.connection = Connection.objects.create(
            user=cls.user,
            technology=Technology.objects.get(name="postgresql"),
            server=cls.HOST,
            port=cls.PORT,
            database=cls.SERVICE,
            username=cls.ROLE,
            password=encrypt(cls.PASSWORD, key=USERS["ADMIN"]["PASSWORD"]),
            alias="Polling Database Tests",
        )
        cls.session = SimpleNamespace(user_id=cls.user.id, csv_encoding="utf-8", csv_delimiter=";")

    @classmethod
    def make_database(cls):
        database = OmniDatabase.Generic.InstantiateDatabase(
            "postgresql", cls.HOST, cls.PORT, cls.SERVICE, cls.ROLE, 0, 0
        )
        database.connection.password = cls.PASSWORD
        return database

    def setUp(self):
        self.make_database().connection.Execute(
            f"drop table if exists {self.SCRATCH_TABLE};"
            f"create table {self.SCRATCH_TABLE} (id int primary key, name text);"
            f"insert into {self.SCRATCH_TABLE} values (1, 'a'), (2, 'b');"
        )
        self.addCleanup(
            self.make_database().connection.Execute,
            f"drop table if exists {self.SCRATCH_TABLE}",
        )

    def database(self):
        database = self.make_database()
        database.conn_id = self.connection.id
        self.addCleanup(self.close_quietly, database)
        return database

    def close_quietly(self, database):
        try:
            database.connection.Close()
        except Exception:
            pass

    def query(self, sql, mode=QueryModes.DATA_OPERATION, database=None, **args):
        args.setdefault("workspace_context", {})
        args.setdefault("log_query", False)
        args.setdefault("autocommit", True)
        args.setdefault("all_data", False)
        return run_thread_function(
            polling.thread_query,
            sql_cmd=sql,
            mode=mode,
            session=self.session,
            database=database or self.database(),
            **args,
        )

    def test_query_returns_columns_types_and_rows(self):
        responses = self.query("select customerid, firstname from customers order by customerid limit 3")

        self.assertEqual(len(responses), 1)
        response = responses[0]
        self.assertEqual(response["response_type"], ResponseType.QUERY_RESULT)
        self.assertFalse(response["error"])
        data = response["data"]
        self.assertEqual(data["col_names"], ["customerid", "firstname"])
        self.assertEqual(data["col_types"], ["integer", "character varying"])
        self.assertEqual(data["data"], [["1", "VKUUXF"], ["2", "HQNMZH"], ["3", "JTNRNB"]])
        self.assertTrue(data["last_block"])

    def test_query_sends_the_first_block_of_fifty_rows(self):
        responses = self.query("select generate_series(1, 120)")

        self.assertEqual(len(responses[0]["data"]["data"]), 50)

    def test_fetch_more_continues_from_the_last_row(self):
        database = self.database()
        self.query("select generate_series(1, 120)", database=database)

        responses = self.query("", mode=QueryModes.FETCH_MORE, database=database, block_size=30)

        rows = responses[0]["data"]["data"]
        self.assertEqual(len(rows), 30)
        self.assertEqual(rows[0], ["51"])

    def test_fetch_all_returns_the_remaining_rows(self):
        database = self.database()
        self.query("select generate_series(1, 120)", database=database)

        responses = self.query("", mode=QueryModes.FETCH_ALL, database=database)

        self.assertEqual(len(responses), 1)
        self.assertEqual(len(responses[0]["data"]["data"]), 70)
        self.assertTrue(responses[0]["data"]["last_block"])

    def test_query_with_all_data_returns_every_row(self):
        responses = self.query("select generate_series(1, 120)", all_data=True)

        self.assertEqual(len(responses[0]["data"]["data"]), 120)

    def test_rollback_discards_the_open_transaction(self):
        database = self.database()
        self.query(f"insert into {self.SCRATCH_TABLE} values (3, 'c')", database=database, autocommit=False)

        responses = self.query("", mode=QueryModes.ROLLBACK, database=database)

        self.assertEqual(responses[0]["data"]["status"], "ROLLBACK")
        rows = self.query(f"select count(*) from {self.SCRATCH_TABLE}")[0]["data"]["data"]
        self.assertEqual(rows, [["2"]])

    def test_commit_keeps_the_open_transaction(self):
        database = self.database()
        self.query(f"insert into {self.SCRATCH_TABLE} values (3, 'c')", database=database, autocommit=False)

        responses = self.query("", mode=QueryModes.COMMIT, database=database)

        self.assertEqual(responses[0]["data"]["status"], "COMMIT")
        rows = self.query(f"select count(*) from {self.SCRATCH_TABLE}")[0]["data"]["data"]
        self.assertEqual(rows, [["3"]])

    def test_query_error_returns_the_message(self):
        responses = self.query("select * from no_such_table")

        response = responses[0]
        self.assertTrue(response["error"])
        self.assertIn('relation "no_such_table" does not exist', response["data"]["message"])
        self.assertIn("position", response["data"])

    def test_cancelled_query_sends_no_response(self):
        responses = run_thread_function(
            polling.thread_query,
            cancel=True,
            sql_cmd="select 1",
            mode=QueryModes.DATA_OPERATION,
            workspace_context={},
            log_query=False,
            autocommit=True,
            all_data=False,
            session=self.session,
            database=self.database(),
        )

        self.assertEqual(responses, [])

    def test_logged_query_saves_the_tab_and_the_history(self):
        workspace_context = {"sql_save": "select 1"}

        self.query("select 1", log_query=True, tab_title="My Query", workspace_context=workspace_context)

        tab = Tab.objects.get(connection=self.connection)
        self.assertEqual(tab.title, "My Query")
        self.assertEqual(tab.snippet, "select 1")
        self.assertTrue(workspace_context["inserted_tab"])
        self.assertEqual(QueryHistory.objects.get(connection=self.connection).snippet, "select 1")

    def test_logged_query_updates_an_existing_tab(self):
        tab = Tab.objects.create(user=self.user, connection=self.connection, title="Old")

        self.query(
            "select 2",
            log_query=True,
            tab_title="New",
            workspace_context={"tab_db_id": tab.id, "sql_save": "select 2"},
        )

        tab.refresh_from_db()
        self.assertEqual(tab.title, "New")
        self.assertEqual(tab.snippet, "select 2")

    def test_export_writes_a_csv_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("pgmanage.settings.TEMP_DIR", temp_dir):
                responses = self.query(
                    "select customerid, firstname from customers order by customerid limit 2",
                    cmd_type="export_csv",
                )

            data = responses[0]["data"]
            self.assertTrue(data["download_name"].endswith(".csv"))
            file_name = os.path.basename(data["file_name"])
            with open(os.path.join(temp_dir, file_name)) as exported:
                self.assertEqual(exported.read(), "customerid;firstname\n1;VKUUXF\n2;HQNMZH\n")

    def test_export_without_headers(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("pgmanage.settings.TEMP_DIR", temp_dir):
                responses = self.query(
                    "select customerid from customers order by customerid limit 2",
                    cmd_type="export_csv-no_headers",
                )

            file_name = os.path.basename(responses[0]["data"]["file_name"])
            with open(os.path.join(temp_dir, file_name)) as exported:
                self.assertEqual(exported.read(), "1\n2\n")

    def test_export_renames_duplicate_column_names(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("pgmanage.settings.TEMP_DIR", temp_dir):
                responses = self.query("select 1 as id, 2 as id", cmd_type="export_csv")

            file_name = os.path.basename(responses[0]["data"]["file_name"])
            with open(os.path.join(temp_dir, file_name)) as exported:
                self.assertEqual(exported.readline(), "id;id_2\n")

    def console(self, sql, mode=ConsoleModes.DATA_OPERATION, database=None, **args):
        args.setdefault("workspace_context", {})
        return run_thread_function(
            polling.thread_console,
            sql_cmd=sql,
            mode=mode,
            autocommit=True,
            session=self.session,
            database=database or self.database(),
            **args,
        )

    def test_console_runs_each_statement(self):
        responses = self.console("select 1 as a; select 2 as b;")

        response = responses[-1]
        self.assertEqual(response["response_type"], ResponseType.CONSOLE_RESULT)
        self.assertFalse(response["error"])
        output = "".join(item["data"]["data"] for item in responses)
        self.assertIn("dellstore=# select 1 as a", output)
        self.assertIn("dellstore=# select 2 as b", output)
        self.assertIn("\r\n", output)
        self.assertEqual(response["data"]["active_database"], self.SERVICE)

    def test_console_error_is_part_of_the_output(self):
        responses = self.console("select * from no_such_table")

        self.assertTrue(responses[0]["error"])
        self.assertIn('relation "no_such_table" does not exist', responses[0]["data"]["data"])

    def test_console_saves_the_history(self):
        self.console("select 1")
        self.console("select 1")

        entry = ConsoleHistory.objects.get(connection=self.connection)
        self.assertEqual(entry.snippet, "select 1")

    def test_console_strips_the_oracle_and_mssql_terminators(self):
        cases = [
            ("oracle", "select 1 from dual\n/"),
            ("mssql", "select 1\nGO"),
            ("mssql", "select 1\ngo 5 -- run it\n"),
        ]
        for db_type, sql in cases:
            with self.subTest(db_type=db_type, sql=sql):
                database = MagicMock(
                    db_type=db_type,
                    active_service="db",
                    use_server_cursor=False,
                    conn_id=self.connection.id,
                )
                database.connection.service = "db"
                database.connection.Special.return_value = "ok"
                database.connection.GetNotices.return_value = []

                self.console(sql, database=database)

                executed = database.connection.Special.call_args[0][0]
                self.assertNotIn("/", executed)
                self.assertNotIn("go", executed.lower())

    def test_export_formats(self):
        cases = [
            ("export_xlsx", "xlsx"),
            ("export_xlsx-no_headers", "xlsx"),
            ("export_json", "json"),
        ]
        for cmd_type, extension in cases:
            with self.subTest(cmd_type=cmd_type):
                with tempfile.TemporaryDirectory() as temp_dir:
                    with patch("pgmanage.settings.TEMP_DIR", temp_dir):
                        responses = self.query("select 1 as id", cmd_type=cmd_type)

                    data = responses[0]["data"]
                    self.assertTrue(data["download_name"].endswith(f".{extension}"))
                    self.assertTrue(data["file_name"].endswith(f".{extension}"))
                    self.assertTrue(os.path.isfile(os.path.join(temp_dir, os.path.basename(data["file_name"]))))

    def test_export_writes_every_block(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("pgmanage.settings.TEMP_DIR", temp_dir):
                responses = self.query("select customerid from customers", cmd_type="export_csv")

            file_name = os.path.basename(responses[0]["data"]["file_name"])
            with open(os.path.join(temp_dir, file_name)) as exported:
                self.assertEqual(len(exported.readlines()), 20001)

    def test_console_pages_a_long_result(self):
        database = self.database()
        workspace_context = {}

        first = self.console(
            "select generate_series(1, 120) as n; select 'after'",
            database=database,
            workspace_context=workspace_context,
        )
        self.assertEqual(self.console_rows(first), list(range(1, 51)))
        self.assertTrue(first[-1]["data"]["show_fetch_button"])
        self.assertEqual(workspace_context["remaining_commands"], ["select 'after'"])

        more = self.console(
            "", mode=ConsoleModes.FETCH_MORE, database=database, workspace_context=workspace_context
        )
        self.assertEqual(self.console_rows(more), list(range(51, 101)))

        rest = self.console(
            "", mode=ConsoleModes.FETCH_ALL, database=database, workspace_context=workspace_context
        )
        self.assertEqual(self.console_rows(rest), list(range(101, 121)))
        self.assertTrue(rest[-1]["data"]["last_block"])

    def test_console_skip_fetch_runs_the_remaining_commands(self):
        database = self.database()
        workspace_context = {}
        self.console(
            "select generate_series(1, 120) as n; select 'after' as word",
            database=database,
            workspace_context=workspace_context,
        )

        responses = self.console(
            "", mode=ConsoleModes.SKIP_FETCH, database=database, workspace_context=workspace_context
        )

        self.assertFalse(responses[-1]["error"])
        self.assertIn("| after |", responses[-1]["data"]["data"])
        self.assertEqual(workspace_context["remaining_commands"], [])

    def console_rows(self, responses):
        output = "".join(response["data"]["data"] for response in responses)
        return [int(value) for value in re.findall(r"^\|\s*(\d+)\s*\|", output.replace("\r", ""), re.M)]

    def test_query_edit_data_returns_the_rows(self):
        responses = run_thread_function(
            polling.thread_query_edit_data,
            database=self.database(),
            table=self.SCRATCH_TABLE,
            schema="public",
            query_filter="order by id",
            count=10,
        )

        self.assertEqual(responses[0]["response_type"], ResponseType.QUERY_EDIT_DATA_RESULT)
        self.assertEqual(responses[0]["data"], {"rows": [["1", "a"], ["2", "b"]]})

    def test_query_edit_data_keeps_a_null_value(self):
        records = SimpleNamespace(Columns=["id", "name"], Rows=[{"id": 1, "name": None}])
        with patch.object(PostgreSQL, "QueryTableRecords", return_value=records):
            responses = run_thread_function(
                polling.thread_query_edit_data,
                database=self.database(),
                table=self.SCRATCH_TABLE,
                schema="public",
                query_filter="",
                count=10,
            )

        self.assertEqual(responses[0]["data"], {"rows": [["1", None]]})

    def test_query_edit_data_error(self):
        responses = run_thread_function(
            polling.thread_query_edit_data,
            database=self.database(),
            table="no_such_table",
            schema="public",
            query_filter="",
            count=10,
        )

        self.assertTrue(responses[0]["error"])
        self.assertIn("does not exist", responses[0]["data"])

    def test_save_edit_data_writes_the_change(self):
        responses = run_thread_function(
            polling.thread_save_edit_data,
            database=self.database(),
            sql_cmd=f"update {self.SCRATCH_TABLE} set name = 'z' where id = 2",
        )

        self.assertEqual(responses[0]["response_type"], ResponseType.SAVE_EDIT_DATA_RESULT)
        self.assertFalse(responses[0]["error"])
        rows = self.query(f"select name from {self.SCRATCH_TABLE} where id = 2")[0]["data"]["data"]
        self.assertEqual(rows, [["z"]])

    def test_save_edit_data_error(self):
        responses = run_thread_function(
            polling.thread_save_edit_data,
            database=self.database(),
            sql_cmd="update no_such_table set x = 1",
        )

        self.assertTrue(responses[0]["error"])
        self.assertIn("does not exist", responses[0]["data"])

    def test_schema_edit_data_changes_the_table(self):
        responses = run_thread_function(
            polling.thread_schema_edit_data,
            database=self.database(),
            sql_cmd=f"alter table {self.SCRATCH_TABLE} add column note text",
            autocommit=True,
        )

        self.assertEqual(responses[0]["response_type"], ResponseType.SCHEMA_EDIT_RESULT)
        self.assertEqual(responses[0]["data"], {"status": "ALTER TABLE"})
        columns = self.query(
            f"select column_name from information_schema.columns "
            f"where table_name = '{self.SCRATCH_TABLE}' order by ordinal_position"
        )[0]["data"]["data"]
        self.assertEqual(columns, [["id"], ["name"], ["note"]])

    def test_schema_edit_data_error(self):
        responses = run_thread_function(
            polling.thread_schema_edit_data,
            database=self.database(),
            sql_cmd="alter table no_such_table add column x int",
            autocommit=True,
        )

        self.assertTrue(responses[0]["error"])
        self.assertIn("does not exist", responses[0]["data"]["message"])

    def test_create_request_runs_the_query_and_long_polling_returns_it(self):
        database = self.database()
        execute_client_login(
            p_client=self.client,
            p_username=USERS["ADMIN"]["USER"],
            p_password=USERS["ADMIN"]["PASSWORD"],
        )
        session = self.client.session
        session["pgmanage_session"].databases = [
            {
                "database": database,
                "prompt_password": False,
                "prompt_timeout": datetime.now() + timedelta(seconds=60000),
            }
        ]
        session.save()
        client_id = session.session_key
        self.addCleanup(client_manager.remove_client, client_id)

        response = self.client.post(
            reverse("create_request"),
            data={
                "request_type": RequestType.QUERY,
                "context_code": 9,
                "data": {
                    "db_index": 0,
                    "workspace_id": "ws",
                    "tab_id": "tab",
                    "tab_db_id": None,
                    "sql_cmd": "select 42 as answer",
                    "sql_save": "select 42 as answer",
                    "mode": QueryModes.DATA_OPERATION,
                    "all_data": False,
                    "log_query": False,
                    "autocommit": True,
                },
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

        tab = client_manager.get_client(client_id).get_tab(workspace_id="ws", tab_id="tab")
        tab["thread"].join(timeout=30)
        self.addCleanup(self.close_quietly, tab["omnidatabase"])

        response = self.client.post(
            reverse("long_polling"), data={"startup": False}, content_type="application/json"
        )

        rows = response.json()["returning_rows"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["context_code"], 9)
        self.assertEqual(rows[0]["data"]["col_names"], ["answer"])
        self.assertEqual(rows[0]["data"]["data"], [["42"]])
