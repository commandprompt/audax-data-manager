from datetime import datetime, timedelta
from functools import partial

from app.include import OmniDatabase
from app.models import Connection, Technology
from app.tests.utils_testing import USERS, execute_client_login
from app.utils.crypto import encrypt
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

DROP_TEST_OBJECTS = (
    "DROP TABLE IF EXISTS erd_b.orders",
    "DROP TABLE IF EXISTS erd_b.customers",
    "DROP TABLE IF EXISTS erd_a.customers",
    "DROP SCHEMA IF EXISTS erd_b",
    "DROP SCHEMA IF EXISTS erd_a",
)


class MSSQLERDGraphTests(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.test_connection = Connection.objects.create(
            user=User.objects.get(username="admin"),
            technology=Technology.objects.filter(name="mssql").first(),
            server="127.0.0.1",
            port="1434",
            database="northwind_test",
            username="sa",
            password=encrypt("Audax_2026!", key=USERS["ADMIN"]["PASSWORD"]),
            alias="MSSQL ERD Tests",
        )

        cls.database = OmniDatabase.Generic.InstantiateDatabase(
            "mssql", "127.0.0.1", "1434", "northwind_test", "sa", 0, cls.test_connection.id
        )
        cls.database.connection.password = "Audax_2026!"
        for sql in DROP_TEST_OBJECTS + (
            "CREATE SCHEMA erd_a",
            "CREATE SCHEMA erd_b",
            "CREATE TABLE erd_a.customers (id int PRIMARY KEY, name nvarchar(50))",
            "CREATE TABLE erd_b.customers (code int PRIMARY KEY)",
            "CREATE TABLE erd_b.orders (id int PRIMARY KEY, customer_id int "
            "CONSTRAINT orders_customer_fk FOREIGN KEY REFERENCES erd_a.customers(id))",
        ):
            cls.database.connection.Execute(sql)

    @classmethod
    def tearDownClass(cls):
        for sql in DROP_TEST_OBJECTS:
            cls.database.connection.Execute(sql)
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
        session["pgmanage_session"].tabs_databases = {"erd": "northwind_test"}
        session.save()

        self.client.post = partial(self.client.post, content_type="application/json")
        self.request_data = {
            "database_index": self.test_connection.id,
            "database_name": "northwind_test",
            "workspace_id": "erd",
            "schema": "",
        }

    def draw_graph(self, **data):
        response = self.client.post(reverse("draw_graph"), data={**self.request_data, **data})
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def tables_by_name(self, graph):
        return {f"{node['schema']}.{node['label']}": node for node in graph["nodes"]}

    def test_offers_only_user_schemas(self):
        graph = self.draw_graph()
        names = [schema["name"] for schema in graph["available_schemas"]]

        self.assertEqual(names, ["dbo", "erd_a", "erd_b"])
        self.assertEqual(graph["schemas"], names)

    def test_selects_own_schema_for_schema_tab(self):
        graph = self.draw_graph(schema="erd_b")

        self.assertEqual(graph["schemas"], ["erd_b"])

    def test_uses_object_id_as_node_id(self):
        object_id = self.database.connection.ExecuteScalar("SELECT OBJECT_ID('erd_b.orders')")

        tables = self.tables_by_name(self.draw_graph())

        self.assertEqual(tables["erd_b.orders"]["id"], str(object_id))

    def test_shows_edge_between_schemas(self):
        graph = self.draw_graph()
        tables = self.tables_by_name(graph)
        orders = tables["erd_b.orders"]
        customers = tables["erd_a.customers"]
        edges = [e for e in graph["edges"] if e["from"] == orders["id"]]

        self.assertEqual(
            [(e["to"], e["from_col"], e["to_col"], e["cgid"]) for e in edges],
            [(customers["id"], "customer_id", "id", "erd_b.orders_customer_fk")],
        )
        self.assertEqual(
            [(c["name"], c["is_pk"], c["is_fk"]) for c in orders["columns"]],
            [("id", True, False), ("customer_id", False, True)],
        )
