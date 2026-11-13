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

    def saved_nodes(self, graph):
        saved_nodes = []
        for node in graph["nodes"]:
            saved_nodes.append({
                "id": node["id"],
                "type": "table",
                "data": {"label": node["label"], "schema": node["schema"]},
            })
            for column in node["columns"]:
                saved_nodes.append({
                    "id": f"{node['id']}_{column['name']}",
                    "type": "column",
                    "parentNode": node["id"],
                    "data": {"label": column["name"], "is_pk": column["is_pk"], "is_fk": column["is_fk"]},
                })
        return saved_nodes

    def table_names(self, nodes):
        return {node["id"]: f"{node['schema']}.{node['label']}" for node in nodes}

    def table_id(self, nodes, name):
        return next(id_ for id_, table_name in self.table_names(nodes).items() if table_name == name)

    def test_selects_all_user_schemas_by_default(self):
        graph = self.draw_graph()
        names = [schema["name"] for schema in graph["available_schemas"]]

        self.assertTrue({"public", "erd_a", "erd_b"} <= set(names))
        self.assertNotIn("pg_catalog", names)
        self.assertNotIn("information_schema", names)
        self.assertEqual(graph["schemas"], [schema["name_raw"] for schema in graph["available_schemas"]])

    def test_selects_own_schema_by_default_for_schema_tab(self):
        graph = self.draw_graph(schema="erd_b")

        self.assertEqual(graph["schemas"], ["erd_b"])

    def test_offers_own_system_schema_for_schema_tab(self):
        graph = self.draw_graph(schema="information_schema")
        names = [schema["name"] for schema in graph["available_schemas"]]

        self.assertIn("information_schema", names)
        self.assertNotIn("pg_catalog", names)
        self.assertEqual(graph["schemas"], ["information_schema"])

    def test_loads_tables_of_all_schemas_whatever_is_selected(self):
        names = self.table_names(self.draw_graph(schema="erd_b")["nodes"]).values()

        self.assertTrue({"erd_a.customers", "erd_b.customers", "erd_b.orders"} <= set(names))

    def test_uses_table_oid_as_node_id(self):
        oid = self.database.connection.ExecuteScalar("SELECT 'erd_b.orders'::regclass::oid")

        names = self.table_names(self.draw_graph()["nodes"])

        self.assertEqual(names[str(oid)], "erd_b.orders")

    def test_shows_edge_between_schemas(self):
        graph = self.draw_graph(schema="erd_b")
        names = self.table_names(graph["nodes"])
        edges = [e for e in graph["edges"] if names[e["from"]] == "erd_b.orders"]

        self.assertEqual(
            [(names[e["from"]], names[e["to"]], e["cgid"], e["from_col"], e["to_col"]) for e in edges],
            [("erd_b.orders", "erd_a.customers", "erd_b.orders_customer_fk", "customer_id", "id")],
        )

    def test_uses_schemas_from_saved_layout(self):
        ERDLayout.objects.create(
            connection=self.test_connection,
            name="dellstore@erd_b",
            layout={"nodes": [], "edges": [], "schemas": ["erd_a", "erd_b"]},
        )

        graph = self.draw_graph(schema="erd_b")

        self.assertEqual(graph["schemas"], ["erd_a", "erd_b"])
        self.assertIn("erd_a.customers", self.table_names(graph["new_nodes"]).values())

    def test_ignores_unknown_schema_in_saved_layout(self):
        ERDLayout.objects.create(
            connection=self.test_connection,
            name="dellstore@",
            layout={"nodes": [], "edges": [], "schemas": ["erd_a", "no_such_schema"]},
        )

        graph = self.draw_graph()

        self.assertEqual(graph["schemas"], ["erd_a"])

    def test_saved_layout_gets_changed_fk_flags_again(self):
        graph = self.draw_graph()
        orders_id = self.table_id(graph["nodes"], "erd_b.orders")
        saved_nodes = self.saved_nodes(graph)
        next(n for n in saved_nodes if n["id"] == f"{orders_id}_customer_id")["data"]["is_fk"] = False
        ERDLayout.objects.create(
            connection=self.test_connection,
            name="dellstore@",
            layout={"nodes": saved_nodes, "edges": []},
        )

        graph = self.draw_graph()

        self.assertEqual([node["id"] for node in graph["new_nodes"]], [orders_id])

    def test_keeps_saved_table_after_rename(self):
        self.database.connection.Execute("CREATE TABLE erd_c.old_name (id integer PRIMARY KEY)")
        self.addCleanup(self.database.connection.Execute, "DROP TABLE IF EXISTS erd_c.old_name, erd_c.new_name")
        graph = self.draw_graph()
        table_id = self.table_id(graph["nodes"], "erd_c.old_name")
        ERDLayout.objects.create(
            connection=self.test_connection,
            name="dellstore@",
            layout={"nodes": self.saved_nodes(graph), "edges": []},
        )
        self.database.connection.Execute("ALTER TABLE erd_c.old_name RENAME TO new_name")

        graph = self.draw_graph()

        self.assertIn(table_id, [node["id"] for node in graph["layout"]["nodes"]])
        self.assertEqual([(node["id"], node["label"]) for node in graph["new_nodes"]], [(table_id, "new_name")])

    def test_drops_edges_that_do_not_connect_two_columns(self):
        graph = self.draw_graph()
        names = self.table_names(graph["nodes"])
        edges = [(names[e["from"]], names[e["to"]]) for e in graph["edges"]]

        self.assertEqual(
            [edge for edge in edges if edge[0].startswith("erd_c.")],
            [("erd_c.ok_child", "erd_c.parent")],
        )
