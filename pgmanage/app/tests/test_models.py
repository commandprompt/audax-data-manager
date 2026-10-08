from datetime import datetime
from unittest.mock import Mock, patch

from app.models import (
    ConfigHistory,
    Connection,
    ConsoleHistory,
    Group,
    Job,
    MonWidgets,
    MonWidgetsConnections,
    QueryHistory,
    Shortcut,
    SnippetFile,
    SnippetFolder,
    Tab,
    Technology,
    UserDetails,
)
from django.contrib.auth import get_user_model
from django.db import DatabaseError
from django.test import TestCase
from django.utils.timezone import make_aware

User = get_user_model()


def mock_encrypt(value, key):
    return f"encrypted_{value}_with_{key}"


def mock_decrypt(value, key):
    if "encrypted" in value:
        return value.replace("encrypted_", "").replace(f"_with_{key}", "")
    raise ValueError("Decryption failed")


class TechnologyModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        Technology.objects.create(name="postgresql")

    def test_name_max_length(self):
        technology = Technology.objects.get(id=1)
        max_length = technology._meta.get_field("name").max_length
        self.assertEqual(max_length, 50)

    def test_name_blank(self):
        technology = Technology.objects.get(id=1)
        blank = technology._meta.get_field("name").blank
        self.assertFalse(blank)


class UserDetailsModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        UserDetails.objects.create(user=User.objects.get(id=1))

    def test_theme_max_length(self):
        user_details = UserDetails.objects.get(id=1)
        max_length = user_details._meta.get_field("theme").max_length
        self.assertEqual(max_length, 50)

    def test_theme_default(self):
        user_details = UserDetails.objects.get(id=1)
        theme_default = user_details._meta.get_field("theme").default
        self.assertEqual(theme_default, "light")

    def test_font_size_default(self):
        user_details = UserDetails.objects.get(id=1)
        font_size_default = user_details._meta.get_field("font_size").default
        self.assertEqual(font_size_default, 16)

    def test_csv_encoding_max_length(self):
        user_details = UserDetails.objects.get(id=1)
        max_length = user_details._meta.get_field("csv_encoding").max_length
        self.assertEqual(max_length, 50)

    def test_csv_encoding_default(self):
        user_details = UserDetails.objects.get(id=1)
        csv_encoding_default = user_details._meta.get_field("csv_encoding").default
        self.assertEqual(csv_encoding_default, "utf-8")

    def test_csv_delimiter_max_length(self):
        user_details = UserDetails.objects.get(id=1)
        max_length = user_details._meta.get_field("csv_delimiter").max_length
        self.assertEqual(max_length, 10)

    def test_csv_delimiter_default(self):
        user_details = UserDetails.objects.get(id=1)
        csv_delimiter_default = user_details._meta.get_field("csv_delimiter").default
        self.assertEqual(csv_delimiter_default, ",")

    def test_masterpass_check_max_length(self):
        user_details = UserDetails.objects.get(id=1)
        max_length = user_details._meta.get_field("masterpass_check").max_length
        self.assertEqual(max_length, 256)

    def test_masterpass_check_default(self):
        user_details = UserDetails.objects.get(id=1)
        masterpass_check_default = user_details._meta.get_field(
            "masterpass_check"
        ).default
        self.assertEqual(masterpass_check_default, "")

    def test_date_format_max_length(self):
        user_details = UserDetails.objects.get(id=1)
        max_length = user_details._meta.get_field("date_format").max_length
        self.assertEqual(max_length, 200)

    def test_date_format_null(self):
        user_details = UserDetails.objects.get(id=1)
        date_format_null = user_details._meta.get_field("date_format").null
        self.assertTrue(date_format_null)

    def test_pigz_path_max_length(self):
        user_details = UserDetails.objects.get(id=1)
        max_length = user_details._meta.get_field("pigz_path").max_length
        self.assertEqual(max_length, 256)

    def test_pigz_path_null(self):
        user_details = UserDetails.objects.get(id=1)
        pigz_path_null = user_details._meta.get_field("pigz_path").null
        self.assertTrue(pigz_path_null)

    def test_restore_tabs_default(self):
        user_details = UserDetails.objects.get(id=1)
        restore_tabs_default = user_details._meta.get_field("restore_tabs").default
        self.assertTrue(restore_tabs_default)

    def test_scroll_tree_default(self):
        user_details = UserDetails.objects.get(id=1)
        scroll_tree_default = user_details._meta.get_field("scroll_tree").default
        self.assertTrue(scroll_tree_default)

    def test_get_pigz_path_with_pigz_path(self):
        user_details = UserDetails.objects.get(id=1)
        user_details.pigz_path = "/test/path/to/pigz"
        self.assertEqual(user_details.get_pigz_path(), "/test/path/to/pigz")

    def test_get_pigz_path_without_pigz_path(self):
        user_details = UserDetails.objects.get(id=1)
        with patch("shutil.which", return_value="/test/path/pigz"):
            self.assertEqual(user_details.get_pigz_path(), "/test/path")

    def test_get_pigz_path_without_pigz_installed(self):
        user_details = UserDetails.objects.get(id=1)
        with patch("shutil.which", return_value=None):
            self.assertEqual(user_details.get_pigz_path(), "")

    def test_get_editor_theme_light_theme(self):
        user_details = UserDetails.objects.get(id=1)
        user_details.theme = "light"
        self.assertEqual(user_details.get_editor_theme(), "omnidb")

    def test_get_editor_theme_dark_theme(self):
        user_details = UserDetails.objects.get(id=1)
        user_details.theme = "dark"
        self.assertEqual(user_details.get_editor_theme(), "omnidb_dark")


class ShortcutModelTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        Shortcut.objects.create(user=User.objects.get(id=1))

    def test_code_max_length(self):
        shortcut = Shortcut.objects.get(id=1)
        max_length = shortcut._meta.get_field("code").max_length
        self.assertEqual(max_length, 200)

    def test_os_max_length(self):
        shortcut = Shortcut.objects.get(id=1)
        max_length = shortcut._meta.get_field("os").max_length
        self.assertEqual(max_length, 200)

    def test_ctrl_pressed_default(self):
        shortcut = Shortcut.objects.get(id=1)
        ctrl_pressed_default = shortcut._meta.get_field("ctrl_pressed").default
        self.assertFalse(ctrl_pressed_default)

    def test_shift_pressed_default(self):
        shortcut = Shortcut.objects.get(id=1)
        shift_pressed_default = shortcut._meta.get_field("shift_pressed").default
        self.assertFalse(shift_pressed_default)

    def test_alt_pressed_default(self):
        shortcut = Shortcut.objects.get(id=1)
        alt_pressed_default = shortcut._meta.get_field("alt_pressed").default
        self.assertFalse(alt_pressed_default)

    def test_meta_pressed_default(self):
        shortcut = Shortcut.objects.get(id=1)
        meta_pressed_default = shortcut._meta.get_field("meta_pressed").default
        self.assertFalse(meta_pressed_default)

    def test_key_max_length(self):
        shortcut = Shortcut.objects.get(id=1)
        max_length = shortcut._meta.get_field("key").max_length
        self.assertEqual(max_length, 200)


class ConnectionModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Connection.objects.create(
            user=User.objects.get(id=1), technology=Technology.objects.get(id=1)
        )

    def test_server_max_length(self):
        connection = Connection.objects.get(id=1)
        max_length = connection._meta.get_field("server").max_length
        self.assertEqual(max_length, 200)

    def test_server_default(self):
        connection = Connection.objects.get(id=1)
        server_default = connection._meta.get_field("server").default
        self.assertEqual(server_default, "")

    def test_port_max_length(self):
        connection = Connection.objects.get(id=1)
        max_length = connection._meta.get_field("port").max_length
        self.assertEqual(max_length, 50)

    def test_port_default(self):
        connection = Connection.objects.get(id=1)
        port_default = connection._meta.get_field("port").default
        self.assertEqual(port_default, "")

    def test_database_max_length(self):
        connection = Connection.objects.get(id=1)
        max_length = connection._meta.get_field("database").max_length
        self.assertEqual(max_length, 200)

    def test_database_default(self):
        connection = Connection.objects.get(id=1)
        database_default = connection._meta.get_field("database").default
        self.assertEqual(database_default, "")

    def test_username_max_length(self):
        connection = Connection.objects.get(id=1)
        max_length = connection._meta.get_field("username").max_length
        self.assertEqual(max_length, 200)

    def test_username_default(self):
        connection = Connection.objects.get(id=1)
        username_default = connection._meta.get_field("username").default
        self.assertEqual(username_default, "")

    def test_password_max_length(self):
        connection = Connection.objects.get(id=1)
        max_length = connection._meta.get_field("password").max_length
        self.assertEqual(max_length, 200)

    def test_password_default(self):
        connection = Connection.objects.get(id=1)
        password_default = connection._meta.get_field("password").default
        self.assertEqual(password_default, "")

    def test_alias_max_length(self):
        connection = Connection.objects.get(id=1)
        max_length = connection._meta.get_field("alias").max_length
        self.assertEqual(max_length, 200)

    def test_alias_default(self):
        connection = Connection.objects.get(id=1)
        alias_default = connection._meta.get_field("alias").default
        self.assertEqual(alias_default, "")

    def test_ssh_server_max_length(self):
        connection = Connection.objects.get(id=1)
        max_length = connection._meta.get_field("ssh_server").max_length
        self.assertEqual(max_length, 200)

    def test_ssh_server_default(self):
        connection = Connection.objects.get(id=1)
        ssh_server_default = connection._meta.get_field("ssh_server").default
        self.assertEqual(ssh_server_default, "")

    def test_ssh_port_max_length(self):
        connection = Connection.objects.get(id=1)
        max_length = connection._meta.get_field("ssh_port").max_length
        self.assertEqual(max_length, 50)

    def test_ssh_port_default(self):
        connection = Connection.objects.get(id=1)
        ssh_port_default = connection._meta.get_field("ssh_port").default
        self.assertEqual(ssh_port_default, "")

    def test_ssh_user_max_length(self):
        connection = Connection.objects.get(id=1)
        max_length = connection._meta.get_field("ssh_user").max_length
        self.assertEqual(max_length, 200)

    def test_ssh_user_default(self):
        connection = Connection.objects.get(id=1)
        ssh_user_default = connection._meta.get_field("ssh_user").default
        self.assertEqual(ssh_user_default, "")

    def test_ssh_password_max_length(self):
        connection = Connection.objects.get(id=1)
        max_length = connection._meta.get_field("ssh_user").max_length
        self.assertEqual(max_length, 200)

    def test_ssh_password_default(self):
        connection = Connection.objects.get(id=1)
        ssh_password_default = connection._meta.get_field("ssh_password").default
        self.assertEqual(ssh_password_default, "")

    def test_ssh_key_default(self):
        connection = Connection.objects.get(id=1)
        ssh_key_default = connection._meta.get_field("ssh_password").default
        self.assertEqual(ssh_key_default, "")

    def test_use_tunnel_default(self):
        connection = Connection.objects.get(id=1)
        use_tunnel_default = connection._meta.get_field("use_tunnel").default
        self.assertFalse(use_tunnel_default)

    def test_conn_string_default(self):
        connection = Connection.objects.get(id=1)
        conn_string_default = connection._meta.get_field("conn_string").default
        self.assertEqual(conn_string_default, "")

    def test_public_default(self):
        connection = Connection.objects.get(id=1)
        public_default = connection._meta.get_field("public").default
        self.assertFalse(public_default)

    def test_connection_params_default(self):
        connection = Connection.objects.get(id=1)
        connection_params_default = connection._meta.get_field(
            "connection_params"
        ).default
        self.assertEqual(connection_params_default, dict)

    def test_last_used_database_max_length(self):
        connection = Connection.objects.get(id=1)
        max_length = connection._meta.get_field("last_used_database").max_length
        self.assertEqual(max_length, 200)

    def test_last_used_database_null(self):
        connection = Connection.objects.get(id=1)
        last_used_database_null = connection._meta.get_field("last_used_database").null
        self.assertTrue(last_used_database_null)

    def test_last_access_date_null(self):
        connection = Connection.objects.get(id=1)
        last_access_date_null = connection._meta.get_field("last_access_date").null
        self.assertTrue(last_access_date_null)

    def test_autocomplete_default(self):
        connection = Connection.objects.get(id=1)
        autocomplete_default = connection._meta.get_field("autocomplete").default
        self.assertTrue(autocomplete_default)

    def test_color_label_default(self):
        connection = Connection.objects.get(id=1)
        color_label_default = connection._meta.get_field("color_label").default
        self.assertEqual(color_label_default, 0)

    def test_credentials_extra_default(self):
        connection = Connection.objects.get(id=1)
        credentials_extra_default = connection._meta.get_field(
            "credentials_extra"
        ).default
        self.assertEqual(credentials_extra_default, dict)

    @patch("app.models.main.decrypt", side_effect=mock_decrypt)
    def test_get_credentials_extra_decrypts_every_value(self, mock_decrypt):
        connection = Connection(
            user_id=1,
            credentials_extra={
                "access_key_id": "encrypted_key_id_with_key",
                "secret_access_key": "encrypted_secret_with_key",
            },
        )

        self.assertEqual(
            connection.get_credentials_extra("key"),
            {"access_key_id": "key_id", "secret_access_key": "secret"},
        )

    @patch("app.models.main.decrypt", side_effect=mock_decrypt)
    def test_get_credentials_extra_keeps_a_public_value(self, mock_decrypt):
        connection = Connection(
            user_id=1,
            credentials_extra={
                "aws_region": "us-east-1",
                "access_key_id": "encrypted_key_id_with_key",
            },
        )

        with patch.object(Connection, "PUBLIC_CREDENTIALS_EXTRA_KEYS", ("aws_region",)):
            self.assertEqual(
                connection.get_credentials_extra("key"),
                {"aws_region": "us-east-1", "access_key_id": "key_id"},
            )

    @patch("app.models.main.decrypt", side_effect=mock_decrypt)
    def test_resolve_credentials_extra_fills_in_empty_secrets(self, mock_decrypt):
        connection = Connection(
            user_id=1,
            credentials_extra={
                "access_key_id": "encrypted_key_id_with_key",
                "secret_access_key": "encrypted_secret_with_key",
            },
        )

        resolved = connection.resolve_credentials_extra(
            {"access_key_id": "", "secret_access_key": "typed-secret"}, "key"
        )

        self.assertEqual(
            resolved,
            {"access_key_id": "key_id", "secret_access_key": "typed-secret"},
        )

    def test_masked_credentials_extra_hides_every_value(self):
        connection = Connection(
            user_id=1,
            credentials_extra={
                "aws_region": "us-east-1",
                "access_key_id": "encrypted_key_id_with_key",
            },
        )

        self.assertEqual(
            connection.masked_credentials_extra(),
            {"aws_region": "", "access_key_id": ""},
        )

    def test_masked_credentials_extra_shows_a_public_value(self):
        connection = Connection(
            user_id=1,
            credentials_extra={
                "aws_region": "us-east-1",
                "access_key_id": "encrypted_key_id_with_key",
            },
        )

        with patch.object(Connection, "PUBLIC_CREDENTIALS_EXTRA_KEYS", ("aws_region",)):
            self.assertEqual(
                connection.masked_credentials_extra(),
                {"aws_region": "us-east-1", "access_key_id": ""},
            )

    @patch("app.models.main.encrypt", side_effect=mock_encrypt)
    def test_set_credentials_extra_encrypts_every_value(self, mock_encrypt):
        connection = Connection(user_id=1)

        connection.set_credentials_extra(
            {"aws_region": "us-east-1", "access_key_id": "key_id"}, "key"
        )

        self.assertEqual(
            connection.credentials_extra,
            {
                "aws_region": "encrypted_us-east-1_with_key",
                "access_key_id": "encrypted_key_id_with_key",
            },
        )

    @patch("app.models.main.encrypt", side_effect=mock_encrypt)
    def test_set_credentials_extra_stores_a_public_value_as_it_is(self, mock_encrypt):
        connection = Connection(user_id=1)

        with patch.object(Connection, "PUBLIC_CREDENTIALS_EXTRA_KEYS", ("aws_region",)):
            connection.set_credentials_extra(
                {"aws_region": "us-east-1", "access_key_id": "key_id"}, "key"
            )

        self.assertEqual(
            connection.credentials_extra,
            {
                "aws_region": "us-east-1",
                "access_key_id": "encrypted_key_id_with_key",
            },
        )

    @patch("app.models.main.encrypt", side_effect=mock_encrypt)
    def test_set_credentials_extra_keeps_stored_secret(self, mock_encrypt):
        connection = Connection(
            user_id=1,
            credentials_extra={"access_key_id": "encrypted_key_id_with_key"},
        )

        connection.set_credentials_extra({"access_key_id": ""}, "key")

        self.assertEqual(
            connection.credentials_extra,
            {"access_key_id": "encrypted_key_id_with_key"},
        )

    @patch("app.models.main.encrypt", side_effect=mock_encrypt)
    @patch("app.models.main.decrypt", side_effect=mock_decrypt)
    def test_reencrypt_credentials_extra(self, mock_decrypt, mock_encrypt):
        connection = Connection(
            user_id=1,
            credentials_extra={
                "access_key_id": "encrypted_key_id_with_old_key",
                "secret_access_key": "encrypted_secret_with_old_key",
            },
        )

        connection.reencrypt_credentials_extra("old_key", "new_key")

        self.assertEqual(
            connection.credentials_extra,
            {
                "access_key_id": "encrypted_key_id_with_new_key",
                "secret_access_key": "encrypted_secret_with_new_key",
            },
        )

    @patch("app.models.main.encrypt", side_effect=mock_encrypt)
    @patch("app.models.main.decrypt", side_effect=mock_decrypt)
    def test_reencrypt_credentials_extra_keeps_a_public_value(
        self, mock_decrypt, mock_encrypt
    ):
        connection = Connection(
            user_id=1,
            credentials_extra={
                "aws_region": "us-east-1",
                "access_key_id": "encrypted_key_id_with_old_key",
            },
        )

        with patch.object(Connection, "PUBLIC_CREDENTIALS_EXTRA_KEYS", ("aws_region",)):
            connection.reencrypt_credentials_extra("old_key", "new_key")

        self.assertEqual(
            connection.credentials_extra,
            {
                "aws_region": "us-east-1",
                "access_key_id": "encrypted_key_id_with_new_key",
            },
        )


    @patch("app.models.Connection.objects.filter")
    @patch("app.models.main.encrypt", side_effect=mock_encrypt)
    @patch("app.models.main.decrypt", side_effect=mock_decrypt)
    def test_reencrypt_credentials_success(
        self, mock_decrypt, mock_encrypt, mock_filter
    ):
        connection = Connection.objects.get(id=1)
        mock_conn = Mock(spec=connection)
        mock_filter.return_value = [mock_conn]

        Connection.reencrypt_credentials(
            user_id=1, old_key="old_key", new_key="new_key"
        )

        mock_conn.reencrypt_field.assert_any_call("password", "old_key", "new_key")
        mock_conn.reencrypt_field.assert_any_call("ssh_password", "old_key", "new_key")
        mock_conn.reencrypt_field.assert_any_call("ssh_key", "old_key", "new_key")
        mock_conn.reencrypt_credentials_extra.assert_called_once_with(
            "old_key", "new_key"
        )
        mock_conn.save.assert_called_once()

    @patch("app.models.Connection.objects.filter")
    @patch("app.models.transaction.atomic")
    def test_reencrypt_credentials_transaction_rollback(self, mock_atomic, mock_filter):
        mock_conn = Mock(spec=Connection)
        mock_conn.reencrypt_field.side_effect = Exception("Encryption failed")
        mock_filter.return_value = [mock_conn]

        with self.assertRaises(DatabaseError):
            Connection.reencrypt_credentials(
                user_id=1, old_key="old_key", new_key="new_key"
            )

        mock_atomic.assert_called_once()
        mock_conn.save.assert_not_called()


class SnippetFolderModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        new_date = make_aware(datetime.now())
        SnippetFolder.objects.create(
            user=User.objects.get(id=1),
            create_date=new_date,
            modify_date=new_date,
        )

    def test_name_max_length(self):
        snippet_folder = SnippetFolder.objects.get(id=1)
        max_length = snippet_folder._meta.get_field("name").max_length
        self.assertEqual(max_length, 200)

    def test_name_default(self):
        snippet_folder = SnippetFolder.objects.get(id=1)
        name_default = snippet_folder._meta.get_field("name").default
        self.assertEqual(name_default, "")


class SnippetFileModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        new_date = make_aware(datetime.now())
        SnippetFile.objects.create(
            user=User.objects.get(id=1),
            create_date=new_date,
            modify_date=new_date,
        )

    def test_parent_null(self):
        snippet_file = SnippetFile.objects.get(id=1)
        parent_null = snippet_file._meta.get_field("parent").null
        self.assertTrue(parent_null)

    def test_name_max_length(self):
        snippet_file = SnippetFile.objects.get(id=1)
        max_length = snippet_file._meta.get_field("name").max_length
        self.assertEqual(max_length, 200)

    def test_name_default(self):
        snippet_file = SnippetFile.objects.get(id=1)
        name_default = snippet_file._meta.get_field("name").default
        self.assertEqual(name_default, "")

    def test_text_default(self):
        snippet_file = SnippetFile.objects.get(id=1)
        text_default = snippet_file._meta.get_field("text").default
        self.assertEqual(text_default, "")


class TabModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Connection.objects.create(
            user=User.objects.get(id=1), technology=Technology.objects.get(id=1)
        )
        Tab.objects.create(
            user=User.objects.get(id=1), connection=Connection.objects.get(id=1)
        )

    def test_title_max_length(self):
        tab = Tab.objects.get(id=1)
        max_length = tab._meta.get_field("title").max_length
        self.assertEqual(max_length, 200)

    def test_title_default(self):
        tab = Tab.objects.get(id=1)
        title_default = tab._meta.get_field("title").default
        self.assertEqual(title_default, "")

    def test_snippet_default(self):
        tab = Tab.objects.get(id=1)
        snippet_default = tab._meta.get_field("snippet").default
        self.assertEqual(snippet_default, "")

    def test_database_max_length(self):
        tab = Tab.objects.get(id=1)
        max_length = tab._meta.get_field("database").max_length
        self.assertEqual(max_length, 200)

    def test_database_null(self):
        tab = Tab.objects.get(id=1)
        database_null = tab._meta.get_field("database").null
        self.assertTrue(database_null)


class QueryHistoryModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        new_date = make_aware(datetime.now())
        Connection.objects.create(
            user=User.objects.get(id=1), technology=Technology.objects.get(id=1)
        )
        QueryHistory.objects.create(
            user=User.objects.get(id=1),
            connection=Connection.objects.get(id=1),
            start_time=new_date,
            end_time=new_date,
        )

    def test_duration_default(self):
        query_history = QueryHistory.objects.get(id=1)
        duration_default = query_history._meta.get_field("duration").default
        self.assertEqual(duration_default, "")

    def test_status_default(self):
        query_history = QueryHistory.objects.get(id=1)
        status_default = query_history._meta.get_field("status").default
        self.assertEqual(status_default, "")

    def test_snippet_default(self):
        query_history = QueryHistory.objects.get(id=1)
        snippet_default = query_history._meta.get_field("snippet").default
        self.assertEqual(snippet_default, "")

    def test_database_max_length(self):
        query_history = QueryHistory.objects.get(id=1)
        max_length = query_history._meta.get_field("database").max_length
        self.assertEqual(max_length, 200)

    def test_database_null(self):
        query_history = QueryHistory.objects.get(id=1)
        database_null = query_history._meta.get_field("database").null
        self.assertTrue(database_null)


class ConsoleHistoryModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        new_date = make_aware(datetime.now())
        Connection.objects.create(
            user=User.objects.get(id=1), technology=Technology.objects.get(id=1)
        )
        ConsoleHistory.objects.create(
            user=User.objects.get(id=1),
            connection=Connection.objects.get(id=1),
            start_time=new_date,
        )

    def test_snippet_default(self):
        console_history = ConsoleHistory.objects.get(id=1)
        snippet_default = console_history._meta.get_field("snippet").default
        self.assertEqual(snippet_default, "")

    def test_database_max_length(self):
        console_history = ConsoleHistory.objects.get(id=1)
        max_length = console_history._meta.get_field("database").max_length
        self.assertEqual(max_length, 200)

    def test_database_null(self):
        console_history = ConsoleHistory.objects.get(id=1)
        database_null = console_history._meta.get_field("database").null
        self.assertTrue(database_null)


class GroupModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Group.objects.create(user=User.objects.get(id=1))

    def test_name_max_length(self):
        group = Group.objects.get(id=1)
        max_length = group._meta.get_field("name").max_length
        self.assertEqual(max_length, 50)

    def test_name_default(self):
        group = Group.objects.get(id=1)
        name_default = group._meta.get_field("name").default
        self.assertEqual(name_default, "")


class MonWidgetModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        MonWidgets.objects.create(
            user=User.objects.get(id=1), technology=Technology.objects.get(id=1)
        )

    def test_user_null(self):
        mon_widget = MonWidgets.objects.get(id=1)
        user_null = mon_widget._meta.get_field("user").null
        self.assertTrue(user_null)

    def test_script_chart_default(self):
        mon_widget = MonWidgets.objects.get(id=1)
        script_chart_default = mon_widget._meta.get_field("script_chart").default
        self.assertEqual(script_chart_default, "")

    def test_script_data_default(self):
        mon_widget = MonWidgets.objects.get(id=1)
        script_data_default = mon_widget._meta.get_field("script_data").default
        self.assertEqual(script_data_default, "")

    def test_type_default(self):
        mon_widget = MonWidgets.objects.get(id=1)
        type_default = mon_widget._meta.get_field("type").default
        self.assertEqual(type_default, "")

    def test_title_default(self):
        mon_widget = MonWidgets.objects.get(id=1)
        title_default = mon_widget._meta.get_field("title").default
        self.assertEqual(title_default, "")

    def test_interval_default(self):
        mon_widget = MonWidgets.objects.get(id=1)
        interval_default = mon_widget._meta.get_field("interval").default
        self.assertEqual(interval_default, 60)

    def test_editable_default(self):
        mon_widget = MonWidgets.objects.get(id=1)
        editable_default = mon_widget._meta.get_field("editable").default
        self.assertTrue(editable_default)


class MonWidgetsConnectionsModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Connection.objects.create(
            user=User.objects.get(id=1), technology=Technology.objects.get(id=1)
        )
        MonWidgetsConnections.objects.create(
            user=User.objects.get(id=1), connection=Connection.objects.get(id=1), unit=1
        )

    def test_unit_default(self):
        mon_widget_conn = MonWidgetsConnections.objects.get(id=1)
        unit_default = mon_widget_conn._meta.get_field("unit").default
        self.assertIsNone(unit_default)

    def test_interval_default(self):
        mon_widget_conn = MonWidgetsConnections.objects.get(id=1)
        interval_default = mon_widget_conn._meta.get_field("interval").default
        self.assertEqual(interval_default, 60)

    def test_plugin_name_default(self):
        mon_widget_conn = MonWidgetsConnections.objects.get(id=1)
        plugin_name_default = mon_widget_conn._meta.get_field("plugin_name").default
        self.assertEqual(plugin_name_default, "")


class ConfigHistoryModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        new_date = make_aware(datetime.now())
        Connection.objects.create(
            user=User.objects.get(id=1), technology=Technology.objects.get(id=1)
        )
        ConfigHistory.objects.create(
            user=User.objects.get(id=1),
            connection=Connection.objects.get(id=1),
            start_time=new_date,
        )

    def test_user_null(self):
        config_history = ConfigHistory.objects.get(id=1)
        user_null = config_history._meta.get_field("user").null
        self.assertTrue(user_null)

    def test_commit_comment_blank(self):
        config_history = ConfigHistory.objects.get(id=1)
        commit_comment_blank = config_history._meta.get_field("commit_comment").blank
        self.assertTrue(commit_comment_blank)


class JobModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Connection.objects.create(
            user=User.objects.get(id=1), technology=Technology.objects.get(id=1)
        )
        Job.objects.create(
            id=1, user=User.objects.get(id=1), connection=Connection.objects.get(id=1)
        )

    def test_id_null(self):
        job = Job.objects.get(id=1)
        id_null = job._meta.get_field("id").null
        self.assertFalse(id_null)

    def test_user_null(self):
        job = Job.objects.get(id=1)
        user_null = job._meta.get_field("user").null
        self.assertTrue(user_null)

    def test_arguments_blank(self):
        job = Job.objects.get(id=1)
        arguments_blank = job._meta.get_field("arguments").blank
        self.assertTrue(arguments_blank)

    def test_start_time_null(self):
        job = Job.objects.get(id=1)
        start_time_null = job._meta.get_field("start_time").null
        self.assertTrue(start_time_null)

    def test_end_time_null(self):
        job = Job.objects.get(id=1)
        end_time_null = job._meta.get_field("end_time").null
        self.assertTrue(end_time_null)

    def test_exit_code_null(self):
        job = Job.objects.get(id=1)
        exit_code_null = job._meta.get_field("exit_code").null
        self.assertTrue(exit_code_null)

    def test_utility_pid_null(self):
        job = Job.objects.get(id=1)
        utility_pid_null = job._meta.get_field("utility_pid").null
        self.assertTrue(utility_pid_null)

    def test_process_state_null(self):
        job = Job.objects.get(id=1)
        process_state_null = job._meta.get_field("process_state").null
        self.assertTrue(process_state_null)

    def test_connection_null(self):
        job = Job.objects.get(id=1)
        connection_null = job._meta.get_field("process_state").null
        self.assertTrue(connection_null)
