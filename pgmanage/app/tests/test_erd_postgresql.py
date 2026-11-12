from datetime import datetime, timedelta
from functools import partial

from app.include import OmniDatabase
from app.models import Connection, ERDLayout, Technology
from app.tests.utils_testing import USERS, execute_client_login
from app.utils.crypto import encrypt
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class PostgreSQLERDGraphTests(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.test_connection = Connection.objects.create(
            user=User.objects.get(username="admin"),
            technology=Technology.objects.filter(name="postgresql").first(),
            server="127.0.0.1",
            port="5433",
            database="dellstore",
            username="postgres",
            password=encrypt("postgres", key=USERS["ADMIN"]["PASSWORD"]),
            alias="PostgreSQL ERD Tests",
        )

        cls.database = OmniDatabase.Generic.InstantiateDatabase(
            "postgresql", "127.0.0.1", "5433", "dellstore", "postgres", 0, cls.test_connection.id
        )
        cls.database.connection.password = "postgres"
        cls.database.GetVersion()
        cls.database.connection.Execute(
            """
            DROP SCHEMA IF EXISTS erd_a, erd_b, erd_c CASCADE;
            CREATE SCHEMA erd_a;
            CREATE SCHEMA erd_b;
            CREATE SCHEMA erd_c;
            CREATE TABLE erd_a.customers (id integer PRIMARY KEY);
            CREATE TABLE erd_b.customers (id integer PRIMARY KEY);
            CREATE TABLE erd_b.orders (
                id integer PRIMARY KEY,
                customer_id integer CONSTRAINT orders_customer_fk REFERENCES erd_a.customers(id)
            );
            CREATE TABLE erd_c.parent (id integer PRIMARY KEY);
            CREATE TABLE erd_c.ok_child (id integer PRIMARY KEY, parent_id integer REFERENCES erd_c.parent(id));
            CREATE TABLE erd_c.quoted_child (
                id integer PRIMARY KEY,
                parent_id integer CONSTRAINT "Quoted_Fk" REFERENCES erd_c.parent(id)
            );
            CREATE TABLE erd_c.same_name_1 (
                id integer PRIMARY KEY,
                parent_id integer CONSTRAINT same_fk REFERENCES erd_c.parent(id)
            );
            CREATE TABLE erd_c.same_name_2 (
                id integer PRIMARY KEY,
                other_id integer CONSTRAINT same_fk REFERENCES erd_c.parent(id)
            );
            """
        )

    @classmethod
    def tearDownClass(cls):
        cls.database.connection.Execute("DROP SCHEMA erd_a, erd_b, erd_c CASCADE")
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
        session["pgmanage_session"].tabs_databases = {"erd": "dellstore"}
        session.save()

        self.client.post = partial(self.client.post, content_type="application/json")
        self.request_data = {
            "database_index": self.test_connection.id,
            "workspace_id": "erd",
            "schema": "",
        }

    def draw_graph(self, **data):
        response = self.client.post(reverse("draw_graph"), data={**self.request_data, **data})
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def test_selects_all_user_schemas_by_default(self):
        graph = self.draw_graph()
        names = [schema["name"] for schema in graph["available_schemas"]]

        self.assertTrue({"public", "erd_a", "erd_b"} <= set(names))
        self.assertNotIn("pg_catalog", names)
        self.assertNotIn("information_schema", names)
        self.assertEqual(graph["schemas"], [schema["name_raw"] for schema in graph["available_schemas"]])

    def test_qualifies_node_ids_and_sends_schema_apart_from_label(self):
        nodes = self.draw_graph(schemas=["erd_a", "erd_b"])["nodes"]

        self.assertEqual(
            sorted((node["id"], node["schema"], node["label"]) for node in nodes),
            [
                ("erd_a.customers", "erd_a", "customers"),
                ("erd_b.customers", "erd_b", "customers"),
                ("erd_b.orders", "erd_b", "orders"),
            ],
        )

    def test_shows_edge_between_selected_schemas(self):
        edges = self.draw_graph(schemas=["erd_a", "erd_b"])["edges"]

        self.assertEqual(
            [(e["from"], e["to"], e["cgid"], e["from_col"], e["to_col"]) for e in edges],
            [("erd_b.orders", "erd_a.customers", "erd_b.orders_customer_fk", "customer_id", "id")],
        )

    def test_drops_edge_to_unselected_schema(self):
        graph = self.draw_graph(schemas=["erd_b"])

        self.assertEqual(graph["schemas"], ["erd_b"])
        self.assertEqual(graph["edges"], [])

    def test_ignores_unknown_schema(self):
        graph = self.draw_graph(schemas=["erd_a", "no_such_schema"])

        self.assertEqual(graph["schemas"], ["erd_a"])

    def test_uses_schemas_from_saved_layout(self):
        ERDLayout.objects.create(
            connection=self.test_connection,
            name="dellstore@",
            layout={"nodes": [], "edges": [], "schemas": ["erd_a"]},
        )

        graph = self.draw_graph()

        self.assertEqual(graph["schemas"], ["erd_a"])
        self.assertEqual([node["id"] for node in graph["new_nodes"]], ["erd_a.customers"])

    def test_saved_layout_gets_fk_flag_when_referenced_schema_is_added(self):
        saved_nodes = []
        for node in self.draw_graph(schemas=["erd_b"])["nodes"]:
            saved_nodes.append({"id": node["id"], "type": "table", "data": {"label": node["label"]}})
            for column in node["columns"]:
                saved_nodes.append({
                    "id": f"{node['id']}_{column['name']}",
                    "type": "column",
                    "parentNode": node["id"],
                    "data": {"label": column["name"], "is_pk": column["is_pk"], "is_fk": column["is_fk"]},
                })
        ERDLayout.objects.create(
            connection=self.test_connection,
            name="dellstore@",
            layout={"nodes": saved_nodes, "edges": [], "schemas": ["erd_b"]},
        )

        graph = self.draw_graph(schemas=["erd_a", "erd_b"])

        self.assertEqual(
            sorted(node["id"] for node in graph["new_nodes"]),
            ["erd_a.customers", "erd_b.orders"],
        )

    def test_keeps_single_schema_graph_when_schema_is_given(self):
        graph = self.draw_graph(schema="erd_b")

        self.assertNotIn("available_schemas", graph)
        self.assertEqual(sorted(node["id"] for node in graph["nodes"]), ["customers", "orders"])
        self.assertFalse(any("schema" in node for node in graph["nodes"]))
        self.assertEqual(graph["edges"], [])

    def test_drops_edges_that_do_not_connect_two_columns(self):
        multi_schema_edges = self.draw_graph(schemas=["erd_c"])["edges"]
        single_schema_edges = self.draw_graph(schema="erd_c")["edges"]

        self.assertEqual(
            [(e["from"], e["to"]) for e in multi_schema_edges],
            [("erd_c.ok_child", "erd_c.parent")],
        )
        self.assertEqual(
            [(e["from"], e["to"]) for e in single_schema_edges],
            [("ok_child", "parent")],
        )
