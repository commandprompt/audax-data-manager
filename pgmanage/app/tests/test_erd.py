import os
import sqlite3
import tempfile
from datetime import datetime, timedelta
from functools import partial

from app.include import OmniDatabase
from app.models import Connection, ERDLayout, Technology
from app.tests.utils_testing import USERS, execute_client_login
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class ERDGraphTests(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls._tmpdir = tempfile.TemporaryDirectory()
        cls.sqlite_path = os.path.join(cls._tmpdir.name, "erd_tests.db")

        con = sqlite3.connect(cls.sqlite_path)
        try:
            con.executescript(
                """
                CREATE TABLE orders (id INTEGER PRIMARY KEY, placed_at TEXT);
                CREATE TABLE products (id INTEGER PRIMARY KEY);
                CREATE TABLE product_tags (
                    product_id INTEGER REFERENCES products(id),
                    tag TEXT,
                    PRIMARY KEY (product_id, tag)
                );
                CREATE TABLE order_lines (
                    note TEXT,
                    order_id INTEGER REFERENCES orders(id),
                    line_no INTEGER,
                    PRIMARY KEY (line_no, order_id)
                );
                CREATE TABLE shipments (
                    id INTEGER PRIMARY KEY,
                    line_no INTEGER,
                    order_id INTEGER,
                    FOREIGN KEY (order_id, line_no) REFERENCES order_lines(order_id, line_no)
                );
                """
            )
            con.commit()
        finally:
            con.close()

        cls.test_connection = Connection.objects.create(
            user=User.objects.get(username="admin"),
            technology=Technology.objects.filter(name="sqlite").first(),
            server="",
            port="",
            database=cls.sqlite_path,
            alias="SQLite ERD Tests",
        )

        cls.database = OmniDatabase.Generic.InstantiateDatabase(
            "sqlite", "", "", cls.sqlite_path, "", 0, cls.test_connection.id
        )
        cls.database.GetVersion()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls._tmpdir.cleanup()

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
        session.save()

        self.client.post = partial(self.client.post, content_type="application/json")
        self.request_data = {
            "database_index": self.test_connection.id,
            "workspace_id": "erd",
            "schema": "",
        }

    def draw_graph(self):
        response = self.client.post(reverse("draw_graph"), data=self.request_data)
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def pk_flags(self, nodes, label):
        node = next(node for node in nodes if node["label"] == label)
        return {column["name"]: column["is_pk"] for column in node["columns"]}

    def find_edge(self, edges, from_label, to_label):
        return next(
            edge for edge in edges
            if edge["from"] == f"'{from_label}'" and edge["to"] == f"'{to_label}'"
        )

    def test_marks_all_composite_pk_columns(self):
        nodes = self.draw_graph()["nodes"]

        self.assertEqual(
            self.pk_flags(nodes, "order_lines"),
            {"note": False, "order_id": True, "line_no": True},
        )
        self.assertEqual(
            self.pk_flags(nodes, "product_tags"),
            {"product_id": True, "tag": True},
        )

    def test_routes_composite_fk_edge_to_topmost_pk_column_and_its_fk_pair(self):
        edge = self.find_edge(self.draw_graph()["edges"], "shipments", "order_lines")

        self.assertEqual((edge["from_col"], edge["to_col"]), ("order_id", "order_id"))

    def test_sends_all_column_pairs_of_composite_fk(self):
        edge = self.find_edge(self.draw_graph()["edges"], "shipments", "order_lines")

        self.assertEqual(
            sorted(zip(edge["from_cols"], edge["to_cols"])),
            [("line_no", "line_no"), ("order_id", "order_id")],
        )

    def test_saved_layout_keeps_current_edges(self):
        edge = self.find_edge(self.draw_graph()["edges"], "shipments", "order_lines")
        saved_edge = {
            "id": "saved",
            "cgid": edge["cgid"],
            "data": {"sourceColumns": edge["from_cols"], "targetColumns": edge["to_cols"]},
        }
        ERDLayout.objects.create(
            connection=self.test_connection,
            name="sqlite3@",
            layout={"nodes": [], "edges": [saved_edge]},
        )

        graph = self.draw_graph()

        self.assertEqual(graph["layout"]["edges"], [saved_edge])
        self.assertNotIn(edge["cgid"], [e["cgid"] for e in graph["new_edges"]])

    def test_saved_layout_gets_changed_pk_flags_and_edges_again(self):
        graph = self.draw_graph()
        edge = self.find_edge(graph["edges"], "shipments", "order_lines")

        saved_nodes = []
        for node in graph["nodes"]:
            saved_nodes.append({"id": node["id"], "type": "table", "data": {"label": node["label"]}})
            for column in node["columns"]:
                saved_nodes.append({
                    "id": f"{node['id']}_{column['name']}",
                    "type": "column",
                    "parentNode": node["id"],
                    "data": {"label": column["name"], "is_pk": column["is_pk"]},
                })

        # old layout: no PK flag on product_tags.tag, edge without column lists
        next(n for n in saved_nodes if n["id"] == "'product_tags'_tag")["data"]["is_pk"] = False
        saved_edges = [{"id": "stale", "cgid": edge["cgid"], "data": {}}]

        ERDLayout.objects.create(
            connection=self.test_connection,
            name="sqlite3@",
            layout={"nodes": saved_nodes, "edges": saved_edges},
        )

        graph = self.draw_graph()

        self.assertEqual([node["label"] for node in graph["new_nodes"]], ["product_tags"])
        self.assertEqual(graph["layout"]["edges"], [])
        self.assertIn(edge["cgid"], [e["cgid"] for e in graph["new_edges"]])
