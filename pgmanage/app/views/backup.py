import functools
import operator
import shlex
from abc import ABC, abstractmethod

from app.bgjob.jobs import BatchJob, IJobDesc, escape_dquotes_process_arg
from app.file_manager.file_manager import FileManager
from app.models.main import Connection
from app.utils.decorators import database_required, user_authenticated
from app.utils.postgresql_utilities import get_utility_path
from django.http import JsonResponse


class Backup(ABC):
    """
    A base class representing backup type
    """

    GLOBALS = 1
    SERVER = 2
    OBJECT = 3

    TYPE_MAPPING = {
        "globals": GLOBALS,
        "server": SERVER,
        "objects": OBJECT,
    }

    @classmethod
    def create(cls, backup_type: int):
        if backup_type == cls.GLOBALS:
            return GlobalsBackup()
        if backup_type == cls.SERVER:
            return ServerBackup()
        if backup_type == cls.OBJECT:
            return ObjectBackup()

    @classmethod
    def get_backup_type(cls, backup_type_str):
        backup_type = cls.TYPE_MAPPING.get(backup_type_str)
        if backup_type is None:
            raise ValueError(f"Invalid backup type: {backup_type_str}")
        return backup_type

    @property
    @abstractmethod
    def type_desc(self):
        pass

    @property
    @abstractmethod
    def backup_type(self):
        pass

    @abstractmethod
    def get_message(self, connection_name, database):
        pass


class GlobalsBackup(Backup):
    @property
    def type_desc(self):
        return "Backing up the global objects"

    @property
    def backup_type(self):
        return "Backup Globals"

    def get_message(self, connection_name: str, database=None):
        return f"Backing up the global objects on the server '{connection_name}'"


class ServerBackup(Backup):
    @property
    def type_desc(self):
        return "Backing up the server"

    @property
    def backup_type(self):
        return "Backup Server"

    def get_message(self, connection_name: str, database=None):
        return f"Backing up the server '{connection_name}'"


class ObjectBackup(Backup):
    @property
    def type_desc(self):
        return "Backing up an object on the server"

    @property
    def backup_type(self):
        return "Backup Object"

    def get_message(self, connection_name: str, database=None):
        return f"Backing up an object on the server '{connection_name}' from database '{database}'"


class BackupMessage(IJobDesc):
    """
    BackupMessage(IJobDesc)

    Defines the message shown for the backup operation.
    """

    def __init__(self, backup_type: Backup, conn_id, backup_file, *args, **kwargs):
        self.backup_type = backup_type
        self.conn_id = conn_id
        self.bfile = backup_file
        self.database = kwargs.get("database")
        self.cmd = ""
        self.args_str = "{0} ({1}:{2})"
        self._connection_name = self.get_connection_name()

        # check to we need this?
        def cmd_arg(x):
            if x:
                x = x.replace("\\", "\\\\")
                x = x.replace('"', '\\"')
                x = x.replace('""', '\\"')
                return ' "' + x + '"'
            return ""

        for arg in args:
            if arg and len(arg) >= 2 and arg[:2] == "--":
                self.cmd += " " + arg
            elif arg.startswith("| "):
                self.cmd += f" {arg}"
            else:
                self.cmd += cmd_arg(arg)

    def get_connection_name(self):
        conn = Connection.objects.filter(id=self.conn_id).first()

        if conn is None:
            return "Not available"

        host = conn.ssh_server if conn.use_tunnel else conn.server
        port = conn.ssh_port if conn.use_tunnel else conn.port

        return f"{conn.database} ({host}:{port})"

    @property
    def type_desc(self):
        return self.backup_type.type_desc

    @property
    def message(self):
        return self.backup_type.get_message(self._connection_name, self.database)

    def details(self, cmd):
        backup_type = self.backup_type.backup_type
        return {
            "message": self.message,
            "cmd": cmd + self.cmd,
            "server": self._connection_name,
            "object": self.database,
            "type": backup_type,
        }


def get_args_params_values(data, conn, backup_obj_type, backup_file):
    """
    Used internally by create_backup_objects_job. This function will create
    the required args and params for the job.
    :param data: input data
    :param conn: connection obj
    :param backup_obj_type: object type
    :param backup_file: file name
    :return: args array
    """

    host, port = (conn.server, str(conn.port))
    args = [
        "--file",
        backup_file,
        "--host",
        host,
        "--port",
        port,
        "--username",
        conn.user,
        "--no-password",
    ]

    def set_param(key, param, assertion=True):
        if not assertion:
            return
        if data.get(key, None):
            args.append(param)

    def set_value(key, param, default_value=None, assertion=True):
        if not assertion:
            return
        val = data.get(key, default_value)
        if isinstance(val, int):
            val = str(val)
        if val:
            args.append(param)
            args.append(val)

    if backup_obj_type != "objects":
        args.append("--database")
        args.append(conn.active_service)

    set_param("verbose", "--verbose")
    set_param("dqoute", "--quote-all-identifiers")
    set_value("role", "--role")

    if backup_obj_type == "objects" and data.get("format", None):
        args.extend(
            [
                "--format={0}".format(
                    {"custom": "c", "tar": "t", "plain": "p", "directory": "d"}[
                        data["format"]
                    ]
                )
            ]
        )

        set_param("blobs", "--blobs", data["format"] in ["custom", "tar"])
        set_value(
            "compression_ratio",
            "--compress",
            None,
            data.get("format") in ["custom", "plain", "directory"] and not data.get("pigz"),
        )

    set_param("only_data", "--data-only", data.get("only_data", None))
    set_param(
        "disable_trigger",
        "--disable-triggers",
        data.get("only_data", None) and data.get("format", "") == "plain",
    )

    set_param(
        "only_schema",
        "--schema-only",
        data.get("only_schema", None) and not data.get("only_data", None),
    )
    set_param("only_globals", "--globals-only", backup_obj_type != "objects")
    set_param("only_tablespaces", "--tablespaces-only", backup_obj_type != "objects")
    set_param("only_roles", "--roles-only", backup_obj_type != "objects")

    set_param("owner", "--no-owner")
    set_param("include_create_database", "--create")
    set_param("include_drop_commands", "--clean")
    set_param("pre_data", "--section=pre-data")
    set_param("data", "--section=data")
    set_param("post_data", "--section=post-data")
    set_param("privilege", "--no-privileges")
    set_param("tablespace", "--no-tablespaces")
    set_param("unlogged_tbl_data", "--no-unlogged-table-data")
    set_param("use_insert_commands", "--inserts")
    set_param("use_column_inserts", "--column-inserts")
    set_param("disable_quoting", "--disable-dollar-quoting")
    set_param("use_set_session_auth", "--use-set-session-authorization")

    set_param("comments", "--no-comments")
    set_param(
        "load_via_partition_root",
        "--load-via-partition-root",
    )

    set_value("encoding", "--encoding")
    set_value("number_of_jobs", "--jobs", None, data.get("format") == "directory" and not data.get("pigz"))

    args.extend(
        functools.reduce(
            operator.iconcat,
            map(lambda s: ["--schema", s], data.get("schemas", [])),
            [],
        )
    )

    args.extend(
        functools.reduce(
            operator.iconcat, map(lambda t: ["--table", t], data.get("tables", [])), []
        )
    )
    if backup_obj_type == "objects":
        if not data.get("database"):
            raise ValueError("Missing required field: database")
        set_value("database", "--dbname")

    if data.get("pigz"):
        file_name = args[1]

        if not file_name.endswith(".gz"):
            file_name += ".gz"

        number_of_jobs = data.get("number_of_jobs")
        pigz_number_of_jobs = ""
        if number_of_jobs and number_of_jobs != "auto":
            pigz_number_of_jobs = f"-p{number_of_jobs}"

        pigz_compression_ratio = f"-{data.get('compression_ratio')}"
        pigz_path = data.get("pigz_path", "pigz")

        pigz_line = [
            f"| {shlex.quote(pigz_path)} {pigz_number_of_jobs} {pigz_compression_ratio} > {shlex.quote(file_name)}"
        ]
        new_args = args[2:] + pigz_line
        return new_args
    return args


@database_required(check_timeout=True, open_connection=True)
@user_authenticated
def create_backup(request, database):
    """
    Creates a new job for backup task
    (Backup Database(s)/Schema(s)/Table(s))
    """

    backup_type_str = request.data.get("backup_type", "objects")

    data = request.data.get("data", {})

    backup_file = data.get("fileName")

    file_manager = FileManager(request.user)

    try:
        resolved_path = file_manager.resolve_path(backup_file)
        file_manager.check_access_permission(resolved_path)
    except Exception as exc:
        return JsonResponse(data={"data": str(exc)}, status=403)

    utility = "pg_dump" if backup_type_str == "objects" else "pg_dumpall"

    utility_path = None
    try:
        utility_path = get_utility_path(utility, request.user, data.get("pg_version"))
    except FileNotFoundError as exc:
        return JsonResponse(
            data={"data": str(exc)},
            status=400,
        )

    if data.get("pigz"):
        try:
            pigz_path = get_utility_path("pigz", request.user)
            data["pigz_path"] = pigz_path
        except FileNotFoundError as exc:
            return JsonResponse(
                data={"data": str(exc)},
                status=400,
            )

    try:
        backup_type = Backup.get_backup_type(backup_type_str)

        args = get_args_params_values(data, database, backup_type_str, resolved_path)
        escaped_args = [escape_dquotes_process_arg(arg) for arg in args]

        if backup_type_str == "objects":
            job = BatchJob(
                description=BackupMessage(
                    Backup.create(backup_type),
                    database.conn_id,
                    resolved_path,
                    *args,
                    database=data.get("database"),
                ),
                cmd=utility_path,
                args=escaped_args,
                user=request.user,
            )
        else:
            job = BatchJob(
                description=BackupMessage(
                    Backup.create(backup_type),
                    database.conn_id,
                    resolved_path,
                    *args,
                ),
                cmd=utility_path,
                args=escaped_args,
                user=request.user,
            )

        job.env["PGPASSWORD"] = database.connection.GetPassword()

        job.start()
    except Exception as exc:
        return JsonResponse(data={"data": str(exc)}, status=410)

    return JsonResponse(
        data={"job_id": job.id, "description": job.description.message, "Success": 1}
    )


@database_required(check_timeout=True, open_connection=True)
@user_authenticated
def preview_command(request, database):
    backup_type_str = request.data.get("backup_type", "objects")

    data = request.data.get("data", {})

    backup_file = data.get("fileName")

    file_manager = FileManager(request.user)

    try:
        resolved_path = file_manager.resolve_path(backup_file)
        file_manager.check_access_permission(resolved_path)
    except Exception as exc:
        return JsonResponse(data={"data": str(exc)}, status=403)

    utility = "pg_dump" if backup_type_str == "objects" else "pg_dumpall"

    utility_path = None
    try:
        utility_path = get_utility_path(utility, request.user, data.get("pg_version"))
    except FileNotFoundError as exc:
        return JsonResponse(
            data={"data": str(exc)},
            status=400,
        )

    if data.get("pigz"):
        try:
            pigz_path = get_utility_path("pigz", request.user)
            data["pigz_path"] = pigz_path
        except FileNotFoundError as exc:
            return JsonResponse(data={"data": str(exc)}, status=400)
    try:
        backup_type = Backup.get_backup_type(backup_type_str)

        args = get_args_params_values(data, database, backup_type_str, resolved_path)

        backup_message = BackupMessage(
            Backup.create(backup_type),
            database.conn_id,
            resolved_path,
            *args,
            database=data.get("database"),
        )
    except Exception as exc:
        return JsonResponse(data={"data": str(exc)}, status=400)

    return JsonResponse(data={"command": backup_message.details(utility_path)})
