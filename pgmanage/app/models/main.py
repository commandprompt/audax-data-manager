import os
import shutil

from pathlib import Path
from app.utils.crypto import decrypt, encrypt
from django.contrib.auth.models import User
from django.db import models, transaction, DatabaseError
from django.conf import settings


class Technology(models.Model):
    name = models.CharField(max_length=50, blank=False)


class UserDetails(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    theme = models.CharField(max_length=50, blank=False,default='light')
    font_size = models.IntegerField(blank=False,default=16)
    csv_encoding = models.CharField(max_length=50, blank=False, default='utf-8')
    csv_delimiter = models.CharField(max_length=10, blank=False, default=',')
    masterpass_check = models.CharField(max_length=256, default='')
    binary_paths = models.JSONField(default=dict)
    date_format = models.CharField(max_length=200, null=True)
    pigz_path = models.CharField(max_length=256, null=True)
    restore_tabs = models.BooleanField(default=True)
    scroll_tree = models.BooleanField(default=True)

    def get_pigz_path(self):

        if self.pigz_path:
            pigz_path = self.pigz_path
        else:
            pigz_path = (
                os.path.dirname(shutil.which("pigz")) if shutil.which("pigz") else ""
            )
        return pigz_path

    def get_binary_paths(self, reset: bool = False):
        supported = settings.SUPPORTED_POSTGRES_VERSIONS
        bp = {} if reset else self.binary_paths

        save = False
        
        bin_dir_template = None

        for v in supported:
            key = f"pg-{v}"
            if key not in bp:
                if not bin_dir_template:
                    candidates = [
                        f"/usr/lib/postgresql/{v}/bin",     # Ubuntu/Debian
                        f"/usr/pgsql-{v}/bin",              # RHEL/CentOS
                        f"/usr/lib/postgresql-{v}/bin",     # Gentoo
                        f"/usr/lib/postgresql{v}/bin",      # openSUSE/SLES
                    ]

                    for p in candidates:
                        if Path(p).exists():
                            bin_dir_template = p.replace(str(v), "{v}")
                            break
                bin_dir = bin_dir_template.format(v=v) if bin_dir_template else None

                if bin_dir and Path(bin_dir).exists():
                    bp[key] = bin_dir
                else:
                    bp[key] = None
                save = True

        self.binary_paths = bp

        if save:
            self.save(update_fields=["binary_paths"])

        return bp

    def get_pg_bin(self, version: int = None) -> str:
        bp = self.get_binary_paths()

        key = f"pg-{version}"

        binary_path = bp.get(key)

        if binary_path:
            return binary_path

        psql = shutil.which("psql")
        return os.path.dirname(psql) if psql else ""

    def get_editor_theme(self):
        if self.theme == "light":
            return "omnidb"
        return "omnidb_dark"


class Shortcut(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    code = models.CharField(max_length=200)
    os = models.CharField(max_length=200)
    ctrl_pressed = models.BooleanField(default=False)
    shift_pressed = models.BooleanField(default=False)
    alt_pressed = models.BooleanField(default=False)
    meta_pressed = models.BooleanField(default=False)
    key = models.CharField(max_length=200)


class Connection(models.Model):
    PUBLIC_CREDENTIALS_EXTRA_KEYS = ()

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    technology = models.ForeignKey(Technology, on_delete=models.CASCADE)
    server = models.CharField(max_length=200, default="")
    port = models.CharField(max_length=50, default="")
    database = models.CharField(max_length=200, default="")
    username = models.CharField(max_length=200, default="")
    password = models.CharField(max_length=200, default="")
    alias = models.CharField(max_length=200, default="")
    ssh_server = models.CharField(max_length=200, default="")
    ssh_port = models.CharField(max_length=50, default="")
    ssh_user = models.CharField(max_length=200, default="")
    ssh_password = models.CharField(max_length=200, default="")
    ssh_key = models.TextField(default="")
    use_tunnel = models.BooleanField(default=False)
    conn_string = models.TextField(default="")
    public = models.BooleanField(default=False)
    connection_params = models.JSONField(default=dict)
    credentials_extra = models.JSONField(default=dict)
    last_used_database = models.CharField(max_length=200, null=True)
    last_access_date = models.DateTimeField(null=True)
    autocomplete = models.BooleanField(default=True)
    color_label = models.IntegerField(default=0)
    pinned_databases = models.JSONField(default=list)

    @classmethod
    def reencrypt_credentials(cls, user_id: int, old_key: str, new_key: str) -> None:
        """
        Re-encrypts the credentials (password, ssh_password, ssh_key and the secrets
        in credentials_extra) of all connections for the specified user using a new
        encryption key.

        This method operates within an atomic transaction. If any error occurs during the
        re-encryption process, no changes are saved to the database and the error is raised.

        Args:
            user_id (int): The ID of the user whose connections should be re-encrypted.
            old_key (str): The old encryption key used to decrypt the current values.
            new_key (str): The new encryption key used to encrypt the values.

        Raises:
            DatabaseError: If an error occurs during the transaction.
        """
        try:
            with transaction.atomic():
                for conn in cls.objects.filter(user_id=user_id):
                    conn.reencrypt_field("password", old_key, new_key)
                    conn.reencrypt_field("ssh_password", old_key, new_key)
                    conn.reencrypt_field("ssh_key", old_key, new_key)
                    conn.reencrypt_credentials_extra(old_key, new_key)
                    conn.save()
        except Exception as exc:
            raise DatabaseError(f"Failed to re-encrypt credentials: {exc}") from exc

    def reencrypt_field(self, field_name: str, old_key: str, new_key: str) -> None:
        """
        Re-encrypts a specific field of a connection using the provided new encryption key.

        Args:
            field_name (str): The name of the field to be re-encrypted.
            old_key (str): The old encryption key used to decrypt the current value.
            new_key (str): The new encryption key used to encrypt the value.
        """
        field_value = getattr(self, field_name, "")
        if field_value:
            decrypted_value = decrypt(field_value, old_key)
            if isinstance(decrypted_value, bytes):
                decrypted_value = decrypted_value.decode()
            encrypted_value = encrypt(decrypted_value, new_key)
            setattr(self, field_name, encrypted_value)

    def is_public_credential(self, name: str) -> bool:
        """Tells if a credentials_extra key is sent to the client as it is."""
        return name in self.PUBLIC_CREDENTIALS_EXTRA_KEYS

    def reencrypt_credentials_extra(self, old_key: str, new_key: str) -> None:
        """
        Re-encrypts the secret values of credentials_extra with the provided new
        encryption key. The public values stay unchanged.

        Args:
            old_key (str): The old encryption key used to decrypt the current values.
            new_key (str): The new encryption key used to encrypt the values.
        """
        credentials = {}
        for name, value in (self.credentials_extra or {}).items():
            if self.is_public_credential(name) or not value:
                credentials[name] = value
                continue
            decrypted_value = decrypt(value, old_key)
            if isinstance(decrypted_value, bytes):
                decrypted_value = decrypted_value.decode()
            credentials[name] = encrypt(decrypted_value, new_key)
        self.credentials_extra = credentials

    def get_credentials_extra(self, key: str) -> dict:
        """
        Returns credentials_extra with the secret values decrypted, ready to be given
        to a database interface.

        Args:
            key (str): The encryption key used to decrypt the secret values.
        """
        credentials = {}
        for name, value in (self.credentials_extra or {}).items():
            if self.is_public_credential(name) or not value:
                credentials[name] = value
                continue
            decrypted_value = decrypt(value, key)
            if isinstance(decrypted_value, bytes):
                decrypted_value = decrypted_value.decode()
            credentials[name] = decrypted_value
        return credentials

    def resolve_credentials_extra(self, credentials: dict, key: str) -> dict:
        """
        Returns credentials_extra ready for a database interface. Each secret which the
        client left empty is taken from the stored connection.

        Args:
            credentials (dict): The credentials sent by the client.
            key (str): The encryption key used to decrypt the stored secrets.
        """
        resolved = dict(credentials or {})
        for name, value in self.get_credentials_extra(key).items():
            if self.is_public_credential(name) or not value:
                continue
            if not resolved.get(name):
                resolved[name] = value
        return resolved

    def masked_credentials_extra(self) -> dict:
        """
        Returns credentials_extra for the client, with each secret value replaced by an
        empty string.
        """
        return {
            name: value if self.is_public_credential(name) else ""
            for name, value in (self.credentials_extra or {}).items()
        }

    def set_credentials_extra(self, credentials: dict, key: str) -> None:
        """
        Stores credentials_extra, encrypting the secret values. The client only gets
        empty secrets back, thus an empty secret keeps the stored value.

        Args:
            credentials (dict): The credentials sent by the client.
            key (str): The encryption key used to encrypt the secret values.
        """
        stored = dict(self.credentials_extra or {})
        new_credentials = {}
        for name, value in (credentials or {}).items():
            if self.is_public_credential(name):
                new_credentials[name] = value
            elif value:
                new_credentials[name] = encrypt(value, key)
            else:
                new_credentials[name] = stored.get(name, "")
        self.credentials_extra = new_credentials


class SnippetFolder(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True)
    name = models.CharField(max_length=200, default="")
    create_date = models.DateTimeField()
    modify_date = models.DateTimeField()


class SnippetFile(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    parent = models.ForeignKey(SnippetFolder, on_delete=models.CASCADE, null=True)
    name = models.CharField(max_length=200, default="")
    create_date = models.DateTimeField()
    modify_date = models.DateTimeField()
    text = models.TextField(default="")


class Tab(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    connection = models.ForeignKey(Connection, on_delete=models.CASCADE)
    title = models.CharField(max_length=200, default="")
    snippet = models.TextField(default="")
    database = models.CharField(max_length=200, null=True)


class QueryHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    connection = models.ForeignKey(Connection, on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    duration = models.TextField(default="")
    status = models.TextField(default="")
    snippet = models.TextField(default="")
    database = models.CharField(max_length=200, null=True)


class ConsoleHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    connection = models.ForeignKey(Connection, on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    snippet = models.TextField(default="")
    database = models.CharField(max_length=200, null=True)


class Group(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=50, default="")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "name"], name="unique_user_group_name"
            )
        ]


class GroupConnection(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    connection = models.ForeignKey(Connection, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["group", "connection"], name="unique_group_connection"
            )
        ]


class MonWidgets(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    technology = models.ForeignKey(Technology, on_delete=models.CASCADE)
    script_chart = models.TextField(default="", blank=True)
    script_data = models.TextField(default="")
    type = models.TextField(default="")
    title = models.TextField(default="")
    interval = models.IntegerField(default=60)
    editable = models.BooleanField(default=True)


class MonWidgetsConnections(models.Model):
    unit = models.IntegerField(default=None)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    connection = models.ForeignKey(Connection, on_delete=models.CASCADE)
    interval = models.IntegerField(default=60)
    plugin_name = models.TextField(default="")
    position = models.IntegerField(default=0)
    visible = models.BooleanField(default=True)


class ConfigHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    connection = models.ForeignKey(Connection, on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    config_snapshot = models.TextField()
    commit_comment = models.TextField(blank=True)


class Job(models.Model):
    id = models.TextField(null=False, primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    command = models.TextField()
    description = models.TextField()
    arguments = models.TextField(blank=True)
    logdir = models.TextField()
    start_time = models.DateTimeField(null=True)
    end_time = models.DateTimeField(null=True)
    exit_code = models.IntegerField(null=True)
    utility_pid = models.IntegerField(null=True)
    process_state = models.IntegerField(null=True)
    connection = models.ForeignKey(Connection, on_delete=models.CASCADE, null=True)


class ERDLayout(models.Model):
    connection = models.ForeignKey(Connection, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    layout = models.JSONField()

    class Meta:
        unique_together = ["connection", "name"]
