from datetime import datetime, timedelta
from functools import partial
from unittest.mock import patch

from app.include import OmniDatabase
from app.include.OmniDatabase import PostgreSQL
from app.models.main import Connection, Group, Tab, Technology
from app.tests.utils_testing import USERS, execute_client_login
from app.utils.crypto import encrypt
from app.views.connections import (
    delete_group,
    get_connections,
    get_existing_tabs,
    get_groups,
    save_connection,
    save_group,
    test_connection,
)
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import resolve, reverse

User = get_user_model()


class ConnectionsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.host = "127.0.0.1"
        cls.port = "5433"
        cls.service = "dellstore"
        cls.role = "postgres"
        cls.password = "postgres"
        cls.encrypted_password = encrypt(cls.password, key=USERS["ADMIN"]["PASSWORD"])
        cls.db_type = "postgresql"
        cls.admin_user = User.objects.get(username="admin")
        cls.test_connection = Connection.objects.create(
            user=cls.admin_user,
            technology=Technology.objects.filter(name=cls.db_type).first(),
            server=cls.host,
            port=cls.port,
            database=cls.service,
            username=cls.role,
            password=cls.encrypted_password,
            alias="Pgmanage Tests",
        )

        cls.database = OmniDatabase.Generic.InstantiateDatabase(
            db_type=cls.db_type,
            server=cls.host,
            port=cls.port,
            service=cls.service,
            user=cls.role,
            password=cls.password,
            conn_id=cls.test_connection.id,
            application_name="Pgmanage Tests",
        )
        cls.test_group1 = Group.objects.create(user=cls.admin_user, name="test group 1")
        cls.test_group2 = Group.objects.create(user=cls.admin_user, name="test group 2")
        cls.test_user = User.objects.create_user(
            username="test_user",
        )
        cls.test_user_group = Group.objects.create(
            user=cls.test_user, name="Test user group"
        )

        cls.test_user_connection = Connection.objects.create(
            user=cls.test_user,
            technology=Technology.objects.filter(name="sqlite").first(),
            alias="Pgmanage Sqlite Tests",
        )

        cls.test_tab = Tab.objects.create(
            user=cls.admin_user,
            connection=Connection.objects.get(id=cls.test_connection.id),
            title="Title",
            snippet="snippet",
            database="test db",
        )

    def setUp(self):
        self.test_connection_data = {
            "id": self.test_connection.id,
            "technology": self.db_type,
            "server": "127.0.0.1",
            "port": "5432",
            "service": "dellstore",
            "user": "postgres",
            "password": "postgres",
            "alias": "Test Connection",
            "tunnel": {
                "enabled": False,
                "server": "",
                "port": "",
                "user": "",
                "password": "",
                "key": "",
                "password_set": False,
                "key_set": False,
            },
            "conn_string": "",
            "connection_params": {},
            "credentials_extra": {},
            "password_set": True,
            "color_label": 0,
            "autocomplete": False,
            "group": None,
            "public": True,
        }
        self.user = {
            "user": USERS["ADMIN"]["USER"],
            "password": USERS["ADMIN"]["PASSWORD"],
        }
        execute_client_login(
            p_client=self.client,
            p_username=self.user["user"],
            p_password=self.user["password"],
        )
        session = self.client.session

        session["pgmanage_session"].databases = {
            self.test_connection.id: {
                "database": self.database,
                "prompt_password": False,
                "prompt_timeout": datetime.now() + timedelta(0, 60000),
                "tunnel": {"enabled": False},
            }
        }
        session["pgmanage_session"].tabs_databases = {0: "dellstore"}
        session.save()

        self.client.post = partial(self.client.post, content_type="application/json")

    def test_get_connections_view_authorized(self):
        response = self.client.get(reverse("get_connections"))

        self.assertEqual(response.status_code, 200)

        response_data = response.json().get("data")

        self.assertListEqual(
            response_data.get("technologies"),
            [tech.name for tech in Technology.objects.all()],
        )
        self.assertEqual(len(response_data.get("connections")), 1)
        self.assertDictContainsSubset(
            {"id": self.test_connection.id, "alias": self.test_connection.alias},
            response_data.get("connections")[0],
        )

    def test_get_connections_view_unauthorized(self):
        self.client.logout()
        response = self.client.get(reverse("get_connections"))

        self.assertEqual(response.status_code, 401)

        with self.assertRaises(ValueError):
            response.json()

    def test_get_connections_url_resolves_get_connections_view(self):
        view = resolve("/get_connections/")
        self.assertEqual(view.func.__name__, get_connections.__name__)

    def test_get_groups_view_authorized(self):
        response = self.client.get(reverse("get_groups"))
        response_data = response.json().get("data")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            len(response_data), len(Group.objects.filter(user=User.objects.get(id=1)))
        )

    def test_get_groups_view_unauthorized(self):
        self.client.logout()
        response = self.client.get(reverse("get_groups"))
        self.assertEqual(response.status_code, 401)

        with self.assertRaises(ValueError):
            response.json()

    def test_get_groups_url_resolves_get_groups_view(self):
        view = resolve("/get_groups/")
        self.assertEqual(view.func.__name__, get_groups.__name__)

    def test_delete_group_view_authorized(self):
        response = self.client.post(
            reverse("delete_group"), data={"id": self.test_group1.id}
        )

        self.assertEqual(response.status_code, 204)

    def test_delete_group_view_unauthorized(self):
        self.client.logout()
        response = self.client.post(
            reverse("delete_group"), data={"id": self.test_group1.id}
        )

        self.assertEqual(response.status_code, 401)

        with self.assertRaises(ValueError):
            response.json()

    def test_delete_group_view_of_another_user(self):
        response = self.client.post(
            reverse("delete_group"), data={"id": self.test_user_group.id}
        )
        response_data = response.json()
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response_data.get("data"), "This group does not belong to you."
        )

    def test_delete_group_view_with_non_existent_id(self):
        response = self.client.post(reverse("delete_group"), data={"id": 999})
        self.assertEqual(response.status_code, 204)

    def test_delete_group_url_resolves_delete_group_view(self):
        view = resolve("/delete_group/")
        self.assertEqual(view.func.__name__, delete_group.__name__)

    def test_save_group_view_authorized(self):
        response = self.client.post(
            reverse("save_group"), data={"name": "test group", "conn_list": []}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Group.objects.filter(name="test group").exists())

    def test_save_group_view_unauthorized(self):
        self.client.logout()
        response = self.client.post(
            reverse("save_group"), data={"name": "test group", "conn_list": []}
        )
        self.assertEqual(response.status_code, 401)

        with self.assertRaises(ValueError):
            response.json()

    def test_save_group_view_create_group_with_duplicate_name(self):
        response = self.client.post(
            reverse("save_group"), data={"name": self.test_group1.name, "conn_list": []}
        )
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertEqual(
            response_data.get("data"), "Group with this name already exists."
        )

    def test_save_group_view_create_group_with_empty_name(self):
        response = self.client.post(
            reverse("save_group"), data={"name": "", "conn_list": []}
        )
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertEqual(response_data.get("data"), "Group name can not be empty.")

    def test_save_group_view_update(self):
        response = self.client.post(
            reverse("save_group"),
            data={"id": self.test_group1.id, "name": "changed name", "conn_list": []},
        )
        self.assertEqual(response.status_code, 200)

        group_db = Group.objects.get(id=self.test_group1.id)
        self.assertNotEqual(self.test_group1.name, group_db.name)
        self.assertEqual(group_db.name, "changed name")

    def test_save_group_view_update_another_user_group(self):
        response = self.client.post(
            reverse("save_group"),
            data={
                "id": self.test_user_group.id,
                "name": "changed name",
                "conn_list": [],
            },
        )

        response_data = response.json()
        self.assertEqual(response.status_code, 403)
        group_db = Group.objects.get(id=self.test_user_group.id)
        self.assertEqual(group_db.name, self.test_user_group.name)
        self.assertEqual(
            response_data.get("data"), "This group does not belong to you."
        )

    def test_save_group_view_update_with_non_existent_id(self):
        response = self.client.post(
            reverse("save_group"),
            data={"id": 999, "name": "changed name", "conn_list": []},
        )
        self.assertEqual(response.status_code, 404)
        response_data = response.json()

        self.assertEqual(response_data.get("data"), "Group not found.")

    def test_save_group_view_update_with_invalid_data(self):
        response = self.client.post(
            reverse("save_group"),
            data={"id": self.test_group1.id, "namse": "changed name", "conn_list": []},
        )
        self.assertEqual(response.status_code, 400)

    def test_save_group_url_resolves_save_group_view(self):
        view = resolve("/save_group/")
        self.assertEqual(view.func.__name__, save_group.__name__)

    @patch.object(PostgreSQL, "TestConnection")
    def test_test_connection_view_authorized(self, testConnection_mock):
        testConnection_mock.return_value = ("Connection successful.", True)
        response = self.client.post(
            reverse("test_connection"), data=self.test_connection_data
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"], "Connection successful.")

    @patch.object(PostgreSQL, "TestConnection")
    def test_test_connection_view_reports_a_failure(self, testConnection_mock):
        testConnection_mock.return_value = ("No such host.", False)
        response = self.client.post(
            reverse("test_connection"), data=self.test_connection_data
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["data"], "No such host.")

    def test_test_connection_view_unauthorized(self):
        self.client.logout()
        response = self.client.post(
            reverse("test_connection"), data=self.test_connection_data
        )

        self.assertEqual(response.status_code, 401)

    def test_test_connection_view_without_permission(self):
        self.test_connection_data.update({"id": self.test_user_connection.id})
        response = self.client.post(
            reverse("test_connection"), data=self.test_connection_data
        )

        self.assertEqual(response.status_code, 403)
        response_data = response.json()

        self.assertEqual(
            response_data.get("data"), "This connection does not belong to you."
        )

    def test_test_connection_view_with_non_existent_connection_id(self):
        self.test_connection_data.update({"id": 999})
        response = self.client.post(
            reverse("test_connection"), data=self.test_connection_data
        )
        self.assertEqual(response.status_code, 404)

        response_data = response.json()
        self.assertEqual(response_data.get("data"), "Connection not found.")

    def test_test_connection_url_resolves_test_connection_view(self):
        view = resolve("/test_connection/")
        self.assertEqual(view.func.__name__, test_connection.__name__)

    def test_save_connection_view_authorized(self):
        self.test_connection_data["id"] = None
        response = self.client.post(
            reverse("save_connection"), self.test_connection_data
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Connection.objects.filter(alias="Test Connection").exists())

    def test_save_connection_view_unauthorized(self):
        self.client.logout()
        response = self.client.post(reverse("save_connection"))
        self.assertEqual(response.status_code, 401)

    def test_save_connection_view_create_with_invalid_data(self):
        self.test_connection_data.update({"id": None, "color_label": "#FF0000"})

        response = self.client.post(
            reverse("save_connection"), self.test_connection_data
        )

        response_data = response.json()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response_data.get("data"),
            "Field 'color_label' expected a number but got '#FF0000'.",
        )

    def test_save_connection_view_update(self):
        self.test_connection_data.update({"alias": "Updated Connection"})

        response = self.client.post(
            reverse("save_connection"), self.test_connection_data
        )

        self.assertEqual(response.status_code, 200)

        self.test_connection.refresh_from_db()
        self.assertEqual(self.test_connection.alias, "Updated Connection")

    def test_save_connection_view_update_without_permission(self):
        self.test_connection_data.update(
            {"id": self.test_user_connection.id, "alias": "Updated Connection"}
        )

        response = self.client.post(
            reverse("save_connection"), self.test_connection_data
        )

        self.assertEqual(response.status_code, 403)

        response_data = response.json()
        self.assertEqual(
            response_data.get("data"), "This connection does not belong to you."
        )

        self.test_user_connection.refresh_from_db()

        self.assertNotEqual(self.test_user_connection.alias, "Updated Connection")

    def test_save_connection_view_update_with_invalid_data(self):
        self.test_connection_data.update(
            {
                "alias": "Updated Connection",
                "color_label": "#FF0000",
            }
        )

        response = self.client.post(
            reverse("save_connection"), self.test_connection_data
        )

        response_data = response.json()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response_data.get("data"),
            "Field 'color_label' expected a number but got '#FF0000'.",
        )

    def test_save_connection_view_stores_encrypted_iam_credentials(self):
        self.test_connection_data.update(
            {
                "password": "",
                "password_set": False,
                "credentials_extra": {
                    "aws_region": "us-east-1",
                    "access_key_id": "key-id",
                    "secret_access_key": "secret",
                },
            }
        )

        response = self.client.post(
            reverse("save_connection"), self.test_connection_data
        )

        self.assertEqual(response.status_code, 200)

        self.test_connection.refresh_from_db()
        stored = self.test_connection.credentials_extra
        self.assertNotEqual(stored["access_key_id"], "key-id")
        self.assertNotEqual(stored["secret_access_key"], "secret")

        key = USERS["ADMIN"]["PASSWORD"]
        self.assertEqual(
            self.test_connection.get_credentials_extra(key),
            {
                "aws_region": "us-east-1",
                "access_key_id": "key-id",
                "secret_access_key": "secret",
            },
        )

    def test_save_connection_view_keeps_a_public_credential_readable(self):
        self.test_connection_data.update(
            {
                "credentials_extra": {
                    "aws_region": "us-east-1",
                    "access_key_id": "key-id",
                }
            }
        )

        with patch.object(
            Connection, "PUBLIC_CREDENTIALS_EXTRA_KEYS", ("aws_region",)
        ):
            response = self.client.post(
                reverse("save_connection"), self.test_connection_data
            )

        self.assertEqual(response.status_code, 200)

        self.test_connection.refresh_from_db()
        self.assertEqual(
            self.test_connection.credentials_extra["aws_region"], "us-east-1"
        )
        self.assertNotEqual(
            self.test_connection.credentials_extra["access_key_id"], "key-id"
        )

    def test_save_connection_view_does_not_prompt_password_with_iam(self):
        self.test_connection_data.update(
            {
                "password": "",
                "password_set": False,
                "credentials_extra": {
                    "aws_region": "us-east-1",
                    "access_key_id": "key-id",
                    "secret_access_key": "secret",
                },
            }
        )

        response = self.client.post(
            reverse("save_connection"), self.test_connection_data
        )

        self.assertEqual(response.status_code, 200)

        session = self.client.session["pgmanage_session"]
        self.assertFalse(
            session.databases[self.test_connection.id]["prompt_password"]
        )

    def test_save_connection_view_keeps_stored_iam_secret(self):
        key = USERS["ADMIN"]["PASSWORD"]
        self.test_connection.credentials_extra = {
            "aws_region": encrypt("us-east-1", key),
            "access_key_id": encrypt("key-id", key),
            "secret_access_key": encrypt("secret", key),
        }
        self.test_connection.save()

        self.test_connection_data.update(
            {
                "password": "",
                "password_set": False,
                "credentials_extra": {
                    "aws_region": "eu-west-1",
                    "access_key_id": "",
                    "secret_access_key": "",
                },
            }
        )

        response = self.client.post(
            reverse("save_connection"), self.test_connection_data
        )

        self.assertEqual(response.status_code, 200)

        self.test_connection.refresh_from_db()
        credentials = self.test_connection.get_credentials_extra(key)
        self.assertEqual(credentials["aws_region"], "eu-west-1")
        self.assertEqual(credentials["access_key_id"], "key-id")
        self.assertEqual(credentials["secret_access_key"], "secret")

    def test_get_connections_view_masks_iam_secrets(self):
        key = USERS["ADMIN"]["PASSWORD"]
        self.test_connection.credentials_extra = {
            "aws_region": "us-east-1",
            "access_key_id": encrypt("key-id", key),
            "secret_access_key": encrypt("secret", key),
        }
        self.test_connection.save()

        with patch.object(
            Connection, "PUBLIC_CREDENTIALS_EXTRA_KEYS", ("aws_region",)
        ):
            response = self.client.get(reverse("get_connections"))

        self.assertEqual(response.status_code, 200)

        connection = response.json()["data"]["connections"][0]
        self.assertEqual(
            connection["credentials_extra"],
            {
                "aws_region": "us-east-1",
                "access_key_id": "",
                "secret_access_key": "",
            },
        )


    def test_save_connection_url_resolves_save_connection_view(self):
        view = resolve("/save_connection/")
        self.assertEqual(view.func.__name__, save_connection.__name__)

    def test_delete_connection_view_authorized(self):
        response = self.client.post(
            reverse("delete_connection"), data={"id": self.test_connection.id}
        )
        self.assertEqual(response.status_code, 204)

        conn_db = Connection.objects.filter(id=self.test_connection.id).exists()

        self.assertFalse(conn_db)

        with self.assertRaises(ValueError):
            response.json()

    def test_delete_connection_view_unauthorized(self):
        self.client.logout()
        response = self.client.post(
            reverse("delete_connection"), data={"id": self.test_connection.id}
        )
        self.assertEqual(response.status_code, 401)

        conn_db = Connection.objects.filter(id=self.test_connection.id).exists()

        self.assertTrue(conn_db)

    def test_delete_connection_view_with_non_existent_id(self):
        response = self.client.post(reverse("delete_connection"), data={"id": 999})
        self.assertEqual(response.status_code, 204)

    def test_delete_connection_view_of_another_user(self):
        response = self.client.post(
            reverse("delete_connection"), data={"id": self.test_user_connection.id}
        )
        self.assertEqual(response.status_code, 403)

        response_data = response.json()
        self.assertEqual(
            response_data.get("data"), "This connection does not belong to you."
        )

    def test_get_existing_tabs_view_authorized(self):
        response = self.client.get(reverse("get_existing_tabs"))

        response_data = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response_data.get("existing_tabs")), 1)

    def test_get_existing_tabs_view_unauthorized(self):
        self.client.logout()
        response = self.client.get(reverse("get_existing_tabs"))

        self.assertEqual(response.status_code, 401)

        with self.assertRaises(ValueError):
            response.json()

    def test_get_exiting_tabs_url_resolves_get_existing_tabs_view(self):
        view = resolve("/get_existing_tabs/")
        self.assertEqual(view.func.__name__, get_existing_tabs.__name__)
