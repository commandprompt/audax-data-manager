from datetime import datetime, timedelta
from functools import partial

from app.include import OmniDatabase
from app.models import Connection, ERDLayout, Technology
from app.tests.utils_testing import USERS, execute_client_login
from app.utils.crypto import encrypt
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class ERDGraphMySQLMixin:
    db_type = None
    port = None
    password = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.test_connection = Connection.objects.create(
            user=User.objects.get(username="admin"),
            technology=Technology.objects.filter(name=cls.db_type).first(),
            server="127.0.0.1",
            port=cls.port,
            database="classicmodels",
            username="root",
            password=encrypt(cls.password, key=USERS["ADMIN"]["PASSWORD"]),
            alias=f"{cls.db_type} ERD Tests",
        )

        cls.database = OmniDatabase.Generic.InstantiateDatabase(
            cls.db_type, "127.0.0.1", cls.port, "classicmodels", "root", 0, cls.test_connection.id
        )
        cls.database.connection.password = cls.password
        for sql in (
            "DROP DATABASE IF EXISTS erd_a",
            "DROP DATABASE IF EXISTS erd_b",
            "CREATE DATABASE erd_a",
            "CREATE DATABASE erd_b",
            "CREATE TABLE erd_a.customers (id int PRIMARY KEY, name varchar(50))",
            "CREATE TABLE erd_b.customers (code int PRIMARY KEY)",
            "CREATE TABLE erd_a.orders (number int PRIMARY KEY, customer_id int, "
            "CONSTRAINT orders_ibfk_1 FOREIGN KEY (customer_id) REFERENCES erd_a.customers(id))",
            "CREATE TABLE erd_b.orders (id int PRIMARY KEY, customer_id int, "
            "CONSTRAINT orders_ibfk_1 FOREIGN KEY (customer_id) REFERENCES erd_a.customers(id))",
        ):
            cls.database.connection.Execute(sql)

    @classmethod
    def tearDownClass(cls):
        cls.database.connection.Execute("DROP DATABASE IF EXISTS erd_b")
        cls.database.connection.Execute("DROP DATABASE IF EXISTS erd_a")
        super().tearDownClass()

    def setUp(self):
        execute_client_login(
            p_client=self.client,
            p_username=USERS["ADMIN"]["USER"],
            p_password=USERS["ADMIN"]["PASSWORD"],
        )
        session = self.client.session
        session["pgmanage_session"].databases = {
            self.test_connection.id: {
                "database": self.database,
                "prompt_password": False,
                "prompt_timeout": datetime.now() + timedelta(seconds=60000),
            }
        }
        session["pgmanage_session"].tabs_databases = {"erd": "classicmodels"}
        session.save()

        self.client.post = partial(self.client.post, content_type="application/json")
        self.request_data = {
            "database_index": self.test_connection.id,
            "database_name": "",
            "workspace_id": "erd",
            "schema": "",
        }

    def draw_graph(self, **data):
        response = self.client.post(reverse("draw_graph"), data={**self.request_data, **data})
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def erd_tables(self, graph):
        return {
            node["id"]: node for node in graph["nodes"]
            if node["schema"] in ("erd_a", "erd_b")
        }

    def test_offers_only_user_databases(self):
        graph = self.draw_graph()
        names = [schema["name"] for schema in graph["available_schemas"]]

        self.assertTrue({"classicmodels", "erd_a", "erd_b"} <= set(names))
        for system_schema in ("information_schema", "mysql", "performance_schema", "sys"):
            self.assertNotIn(system_schema, names)
        self.assertEqual(graph["schemas"], names)

    def test_selects_own_database_for_database_tab(self):
        graph = self.draw_graph(schema="erd_b")

        self.assertEqual(graph["schemas"], ["erd_b"])

    def test_keeps_tables_of_each_database_apart(self):
        tables = self.erd_tables(self.draw_graph())

        self.assertEqual(
            {
                node_id: [(c["name"], c["is_pk"]) for c in node["columns"]]
                for node_id, node in tables.items()
            },
            {
                "erd_a.customers": [("id", True), ("name", False)],
                "erd_a.orders": [("number", True), ("customer_id", False)],
                "erd_b.customers": [("code", True)],
                "erd_b.orders": [("id", True), ("customer_id", False)],
            },
        )

    def test_shows_edges_between_databases(self):
        edges = [e for e in self.draw_graph()["edges"] if e["from"].startswith("erd_")]

        self.assertEqual(
            sorted((e["from"], e["from_col"], e["to"], e["to_col"], e["cgid"]) for e in edges),
            [
                ("erd_a.orders", "customer_id", "erd_a.customers", "id", "erd_a.orders_ibfk_1"),
                ("erd_b.orders", "customer_id", "erd_a.customers", "id", "erd_b.orders_ibfk_1"),
            ],
        )

    def test_saves_layout_for_connection_not_for_active_database(self):
        response = self.client.post(reverse("save_graph_state"), data={
            **self.request_data,
            "layout": {"nodes": [], "edges": [], "schemas": ["erd_a"]},
        })
        self.assertEqual(response.status_code, 200, response.content)

        graph = self.draw_graph()

        self.assertTrue(ERDLayout.objects.filter(connection=self.test_connection, name="@").exists())
        self.assertEqual(graph["schemas"], ["erd_a"])


class MySQLERDGraphTests(ERDGraphMySQLMixin, TestCase):
    db_type = "mysql"
    port = "3307"
    password = "mysql"


class MariaDBERDGraphTests(ERDGraphMySQLMixin, TestCase):
    db_type = "mariadb"
    port = "3308"
    password = "mariadb"
