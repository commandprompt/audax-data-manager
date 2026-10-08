from datetime import datetime, timedelta
from functools import partial

from app.include import OmniDatabase
from app.models.main import Connection, MonWidgets, MonWidgetsConnections, Technology
from app.tests.utils_testing import USERS, execute_client_login
from app.utils.crypto import encrypt
from app.views.monitoring_dashboard import (
    create_dashboard_monitoring_widget,
    create_widget,
    dialect_of,
    monitoring_widgets,
    monitoring_widgets_list,
    refresh_monitoring_widget,
    test_monitoring_widget,
    user_created_widget_detail,
    widget_detail,
    widget_template,
)
from app.views.monitoring_widgets.postgresql import (
    monitoring_widgets as postgresql_widgets,
)
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import resolve, reverse

User = get_user_model()


class MonitoringDashboardTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.host = "127.0.0.1"
        cls.port = "5433"
        cls.service = "dellstore"
        cls.role = "postgres"
        cls.password = "postgres"
        cls.encrypted_password = encrypt(cls.password, key=USERS["ADMIN"]["PASSWORD"])
        cls.db_type = "postgresql"
        cls.test_connection = Connection.objects.create(
            user=User.objects.get(username="admin"),
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

        cls.valid_widget_data = {
            "widget_name": "Test widget",
            "widget_type": "grid",
            "widget_interval": 10,
            "widget_script_chart": "Test chart",
            "widget_script_data": "Test data",
        }

        cls.invalid_widget_data = {
            "widget_name": "",
            "widget_type": "grid",
            "widget_interval": None,
            "widget_script_data": None,
        }

        cls.widget_mock = MonWidgets.objects.create(
            user=User.objects.get(username="admin"),
            technology=Technology.objects.filter(name=cls.db_type).first(),
            title="Mock widget",
            script_chart=postgresql_widgets[0].get("script_chart"),
            script_data=postgresql_widgets[0].get("script_data"),
            type="timeseries",
            interval=15,
        )

        cls.dashboard_widget_mock = MonWidgetsConnections.objects.create(
            unit=cls.widget_mock.id,
            user=User.objects.get(username="admin"),
            connection=cls.test_connection,
            interval=10,
            plugin_name="",
        )

        cls.tab_data = {"database_index": cls.test_connection.id, "tab_id": 0}

    def setUp(self):
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
            }
        }
        session["pgmanage_session"].tab_connections = {
            self.test_connection.id: self.database
        }
        session["pgmanage_session"].tabs_databases = {0: "dellstore"}
        session.save()

        self.client.post = partial(self.client.post, content_type="application/json")
        self.client.put = partial(self.client.put, content_type="application/json")
        self.client.patch = partial(self.client.patch, content_type="application/json")

    def test_get_monitoring_widgets_list(self):
        response = self.client.post(
            reverse("monitoring-widgets-list"), data=self.tab_data
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json().get("data")[0],
            {
                "id": -1,
                "editable": False,
                "title": "Transaction Rate",
                "type": "timeseries",
                "interval": 10,
                "plugin_name": "postgresql",
            },
        )
        # len of builtin widgets + custom widget
        self.assertEqual(len(response.json().get("data")), len(postgresql_widgets) + 1)

    def test_monitoring_widgets_list_resolves_monitoring_widgets_list_view(self):
        """
        Ensure that monitoring_widgets_list url resolves monitoring_widgets_list view.
        """
        view = resolve("/monitoring-widgets/list")

        self.assertEqual(view.func.__name__, monitoring_widgets_list.__name__)

    def test_create_widget_with_valid_data(self):
        """
        Ensure that widget can be created with valid data.
        """

        response = self.client.post(
            reverse("create-custom-widget"),
            data={**self.tab_data, **self.valid_widget_data},
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.json().get("title"), self.valid_widget_data.get("widget_name")
        )

    def test_create_widget_with_invalid_data(self):
        response = self.client.post(
            reverse("create-custom-widget"),
            data={**self.tab_data, **self.invalid_widget_data},
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response, "'title': ['This field cannot be blank.']", status_code=400
        )

    def test_create_widget_resolves_create_widget_view(self):
        """
        Ensure that create_widget url resolves create_widget view.
        """
        view = resolve("/monitoring-widgets/user-created")

        self.assertEqual(view.func.__name__, create_widget.__name__)

    def test_widget_detail_resolves_widget_detail_view(self):
        view = resolve(f"/monitoring-widgets/user-created/{self.widget_mock.id}")

        self.assertEqual(view.func.__name__, user_created_widget_detail.__name__)

    def test_get_widget_with_existing_widget_id(self):
        response = self.client.get(
            reverse("widget-detail", args=[self.widget_mock.id]),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.widget_mock.title, response.json().get("title"))
        self.assertIsNone(response.json().get("user"))

    def test_get_widget_with_non_existing_widget_id(self):
        response = self.client.get(
            reverse("widget-detail", args=[999]),
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json().get("data"), "Widget not found.")

    def test_update_widget_with_existing_id_and_valid_data(self):
        response = self.client.put(
            reverse("widget-detail", args=[self.widget_mock.id]),
            data={**self.valid_widget_data, "widget_name": "Updated Title"},
        )

        self.assertEqual(response.status_code, 200)

        widget_db = MonWidgets.objects.get(id=self.widget_mock.id)

        self.assertEqual(widget_db.title, "Updated Title")

    def test_update_widget_with_existing_id_and_invalid_data(self):
        response = self.client.put(
            reverse("widget-detail", args=[self.widget_mock.id]),
            data={**self.invalid_widget_data, "widget_name": "Updated Title"},
        )

        self.assertEqual(response.status_code, 400)

        widget_db = MonWidgets.objects.get(id=self.widget_mock.id)

        self.assertNotEqual(widget_db.title, "Updated Title")

    def test_update_widget_with_non_existent_id(self):
        response = self.client.put(
            reverse("widget-detail", args=[999]), data=self.valid_widget_data
        )

        self.assertEqual(response.status_code, 404)

        self.assertEqual(response.json().get("data"), "Widget not found.")

    def test_delete_widget_with_existing_id(self):
        response = self.client.delete(
            reverse("widget-detail", args=[self.widget_mock.id])
        )

        widget_db = MonWidgets.objects.filter(id=self.widget_mock.id).first()

        self.assertEqual(response.status_code, 204)
        self.assertIsNone(widget_db)

    def test_delete_widget_with_non_existing_id(self):
        response = self.client.delete(reverse("widget-detail", args=[999]))

        widget_db = MonWidgets.objects.filter(id=self.widget_mock.id).first()

        self.assertEqual(response.status_code, 404)
        self.assertIsNotNone(widget_db)
        self.assertEqual(response.json().get("data"), "Widget not found.")

    def test_get_monitoring_widgets(self):
        response = self.client.post(reverse("monitoring-widgets"), data=self.tab_data)

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            len(response.json().get("widgets")), len(postgresql_widgets) + 1
        )

    def test_monitoring_widgets_resolves_monitoring_widgets_view(self):
        view = resolve("/monitoring-widgets")

        self.assertEqual(view.func.__name__, monitoring_widgets.__name__)

    def test_widget_template_with_existing_id_and_empty_plugin_name(self):
        response = self.client.post(
            reverse("widget-template", args=[self.widget_mock.id]),
            data={"plugin_name": ""},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json().get("script_chart"), self.widget_mock.script_chart
        )

    def test_widget_template_with_existing_id_and_plugin_name(self):
        response = self.client.post(
            reverse("widget-template", args=[-1]),
            data={"plugin_name": self.db_type},
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(response.json().get("type"), "timeseries")

    def test_widget_template_with_non_existing_id_and_empty_plugin_name(self):
        response = self.client.post(
            reverse("widget-template", args=[999]), data={"plugin_name": ""}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {})

    def test_widget_template_with_non_existing_id_and_plugin_name(self):
        response = self.client.post(
            reverse("widget-template", args=[999]), data={"plugin_name": self.db_type}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {})

    def test_widget_template_resolved_widget_template_view(self):
        view = resolve(f"/monitoring-widgets/{self.widget_mock.id}/template")

        self.assertEqual(view.func.__name__, widget_template.__name__)

    def test_create_dashboard_widget_with_valid_data(self):
        response = self.client.post(
            reverse("create-dashboard-widget"),
            data={
                **self.tab_data,
                "widget_data": {
                    "id": self.widget_mock.id,
                    "plugin_name": "",
                    "interval": 11,
                },
            },
        )

        dashboard_widget_db = MonWidgetsConnections.objects.get(
            id=response.json().get("user_widget", {}).get("id")
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(dashboard_widget_db.interval, 11)

    def test_create_dashboard_widget_with_invalid_data(self):
        response = self.client.post(
            reverse("create-dashboard-widget"),
            data={
                **self.tab_data,
                "widget_data": {"id": None, "plugin_name": "", "interval": None},
            },
        )

        dashboard_widget_db = MonWidgetsConnections.objects.filter(
            id=response.json().get("user_widget", {}).get("id")
        ).first()

        self.assertEqual(response.status_code, 400)
        self.assertIsNone(dashboard_widget_db)

    def test_create_dashboard_widget_resolves_create_dashboard_widget_view(self):
        view = resolve("/monitoring-widgets/create")

        self.assertEqual(
            view.func.__name__, create_dashboard_monitoring_widget.__name__
        )

    def test_delete_dashboard_widget_detail_with_existing_id(self):
        response = self.client.delete(
            reverse("dashboard-widget-detail", args=[self.dashboard_widget_mock.id])
        )

        self.assertEqual(response.status_code, 204)
        dashboard_widget_db = MonWidgetsConnections.objects.filter(
            id=self.dashboard_widget_mock.id
        ).first()
        self.assertIsNone(dashboard_widget_db)

    def test_delete_dashboard_widget_detail_with_non_existing_id(self):
        response = self.client.delete(reverse("dashboard-widget-detail", args=[999]))

        self.assertEqual(response.status_code, 404)
        dashboard_widget_db = MonWidgetsConnections.objects.filter(
            id=self.dashboard_widget_mock.id
        ).first()
        self.assertIsNotNone(dashboard_widget_db)

    def test_delete_dashboard_widget_detail_resolves_detete_dashboard_widget_detail_view(
        self,
    ):
        view = resolve(f"/monitoring-widgets/{self.dashboard_widget_mock.id}")

        self.assertEqual(view.func.__name__, widget_detail.__name__)

    def test_patch_dashboard_widget_detail_with_existing_id_and_non_empty_interval(
        self,
    ):
        response = self.client.patch(
            reverse("dashboard-widget-detail", args=[self.dashboard_widget_mock.id]),
            data={"interval": 13},
        )

        self.assertEqual(response.status_code, 204)
        dashboard_widget_db = MonWidgetsConnections.objects.filter(
            id=self.dashboard_widget_mock.id
        ).first()
        self.assertEqual(dashboard_widget_db.interval, 13)

    def test_patch_dashboard_widget_detail_with_non_existing_id(self):
        response = self.client.patch(
            reverse("dashboard-widget-detail", args=[999]), data={"interval": 13}
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json().get("data"), "Widget not found.")

    def test_refresh_monitoring_widget(self):
        response = self.client.post(
            reverse("refresh-monitoring-widget", args=[self.dashboard_widget_mock.id]),
            {**self.tab_data, "widget": {"id": self.widget_mock.id, "plugin_name": ""}},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "object")

    def test_refresh_monitoring_widget_resolves_refresh_monitoring_widget_view(self):
        view = resolve(f"/monitoring-widgets/{self.dashboard_widget_mock.id}/refresh")

        self.assertEqual(view.func.__name__, refresh_monitoring_widget.__name__)

    def test_test_monitoring_widget_with_invalid_data(self):
        response = self.client.post(
            reverse("test-monitoring-widget"),
            data={
                **self.tab_data,
                "widget": {"script_chart": None, "script_data": None, "type": "test"},
            },
        )

        self.assertEqual(response.status_code, 400)

    def test_test_monitoring_widget_with_valid_data(self):
        response = self.client.post(
            reverse("test-monitoring-widget"),
            data={
                **self.tab_data,
                "widget": {
                    "script_chart": self.widget_mock.script_chart,
                    "script_data": self.widget_mock.script_data,
                    "type": "timeseries",
                },
            },
        )

        self.assertEqual(response.status_code, 200)

    def test_test_monitoring_widget_resolves_test_monitoring_widget_view(self):
        view = resolve("/monitoring-widgets/test")

        self.assertEqual(view.func.__name__, test_monitoring_widget.__name__)


class WidgetDialectTests(TestCase):
    def test_a_technology_without_an_alias(self):
        self.assertEqual(dialect_of("postgresql"), "postgresql")

    def test_mariadb_reuses_the_mysql_widgets(self):
        self.assertEqual(dialect_of("mariadb"), "mysql")

    def test_rdspostgresql_reuses_the_postgresql_widgets(self):
        self.assertEqual(dialect_of("rdspostgresql"), "postgresql")
