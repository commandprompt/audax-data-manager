import csv
import json
import os
import re
import secrets
import shutil
import string
import sys
from abc import abstractmethod
from datetime import datetime
from io import StringIO
from pickle import dumps, loads
from subprocess import Popen

import psutil
from app.models.main import Connection, Job
from app.views.polling import get_duration
from django.db.models import F
from django.utils.timezone import make_aware
from pgmanage.settings import HOME_DIR

PROCESS_NOT_STARTED = 0
PROCESS_STARTED = 1
PROCESS_FINISHED = 2
PROCESS_TERMINATED = 3
PROCESS_NOT_FOUND = "Could not find a process with the specified ID."


class IJobDesc:
    @property
    @abstractmethod
    def message(self):
        pass

    @abstractmethod
    def details(self, cmd):
        pass


class BatchJob:
    def __init__(self, **kwargs):
        self.id = (
            self.description
        ) = (
            self.command
        ) = (
            self.args
        ) = (
            self.log_dir
        ) = (
            self.stdout
        ) = self.stderr = self.start_time = self.end_time = self.exit_code = None
        self.env = dict()
        self.user = kwargs.get("user", None)
        if "id" in kwargs:
            self._retrieve_job(kwargs["id"])
        else:
            self._create_job(kwargs["description"], kwargs["cmd"], kwargs["args"])

    def _retrieve_job(self, job_id):
        job = Job.objects.filter(id=job_id).select_related("user").first()

        if job is None:
            raise LookupError(PROCESS_NOT_FOUND)

        try:
            tmp_desc = loads(bytes.fromhex(job.description))
        except Exception:
            tmp_desc = loads(job.description)

        self.id = job_id
        self.description = tmp_desc
        self.command = job.command
        self.args = job.arguments
        self.log_dir = job.logdir
        self.stdout = os.path.join(job.logdir, "out")
        self.stderr = os.path.join(job.logdir, "err")
        self.start_time = job.start_time
        self.end_time = job.end_time
        self.exit_code = job.exit_code
        self.process_state = job.process_state
        self.user = job.user

    def _create_job(self, description, command, args):
        current_time = datetime.now().strftime("%Y%m%d%H%M%S%f")
        log_dir = os.path.join(HOME_DIR, "process_logs", str(self.user.id))

        def random_number(size):
            return "".join(
                secrets.choice(string.ascii_uppercase + string.digits)
                for _ in range(size)
            )

        created = False
        size = 0
        uid = current_time
        while not created:
            try:
                uid += random_number(size)
                log_dir = os.path.join(log_dir, uid)
                size += 1
                if not os.path.exists(log_dir):
                    os.makedirs(log_dir, int("700", 8))
                    created = True
            except OSError as error:
                raise

        self.id = current_time
        self.description = description
        self.command = command
        self.log_dir = log_dir
        self.stdout = os.path.join(log_dir, "out")
        self.stderr = os.path.join(log_dir, "err")
        self.start_time = None
        self.end_time = None
        self.exit_code = None
        self.process_state = PROCESS_NOT_STARTED

        # Arguments
        self.args = args
        args_csv_io = StringIO()
        csv_writer = csv.writer(
            args_csv_io, delimiter=str(","), quoting=csv.QUOTE_MINIMAL
        )
        csv_writer.writerow(args)

        args_val = args_csv_io.getvalue().strip("\r\n")
        tmp_desc = dumps(self.description).hex()
        connection = Connection.objects.filter(id=description.conn_id).first()
        job = Job(
            id=int(current_time),
            command=command,
            arguments=args_val,
            logdir=log_dir,
            description=tmp_desc,
            user=self.user,
            connection=connection,
        )
        job.save()

    def _get_execution_command(self):
        if os.environ.get("STATICX_PROG_PATH", False):
            directory = os.path.dirname(os.environ.get("STATICX_PROG_PATH", ""))
            executor = os.path.join(directory, "process_executor")
            return [executor, self.command]
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            executor = os.path.join(os.path.dirname(sys.executable), "process_executor")
            return [executor, self.command]

        executor = os.path.join(os.path.dirname(__file__), "process_executor.py")
        interpreter = sys.executable
        return [interpreter, executor, self.command]

    def start(self):
        cmd = self._get_execution_command()

        cmd.extend(self.args)

        env = os.environ.copy()

        env["JOB_ID"] = self.id
        env["OUTDIR"] = self.log_dir
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            env.pop("LD_LIBRARY_PATH", None)

        if self.env:
            env.update(self.env)

        if os.name == "nt":
            DETACHED_PROCESS = 0x00000008
            from subprocess import CREATE_NEW_PROCESS_GROUP

            # We need to redirect the standard input, standard output, and
            # standard error to devnull in order to allow it start in detached
            # mode on
            stdin = open(os.devnull, "r")
            stdout = open(os.devnull, "a")
            stderr = open(os.devnull, "a")

            p = Popen(
                cmd,
                close_fds=False,
                env=env,
                stdout=stdout.fileno(),
                stderr=stderr.fileno(),
                stdin=stdin.fileno(),
                creationflags=(CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS),
            )
        else:
            p = Popen(
                cmd,
                close_fds=True,
                stdout=None,
                stderr=None,
                stdin=None,
                start_new_session=True,
                env=env,
            )

        self.exit_code = p.poll()

        if self.exit_code is not None and self.exit_code != 0:
            job = Job.objects.filter(id=self.id, user=self.user).first()
            job.start_time = job.end_time = datetime.now().strftime("%Y%m%d%H%M%S%f")
            if not job.exit_code:
                job.exit_code = self.exit_code
            job.process_state = PROCESS_FINISHED
            job.save()
        else:
            job = Job.objects.filter(id=self.id, user=self.user).first()
            job.process_state = PROCESS_STARTED
            job.save()

    def read_log(
        self, logfile, log, pos, ctime, ecode=None, enc="utf-8", all_records=False
    ):
        completed = True
        idx = 0
        c = re.compile(r"(\d+),(.*$)")

        # If file is not present then
        if not os.path.isfile(logfile):
            return 0, True

        with open(logfile, "rb") as f:
            eofs = os.fstat(f.fileno()).st_size
            f.seek(pos, 0)
            if pos == eofs and ecode is None:
                completed = False

            while pos < eofs:
                idx += 1
                line = f.readline()
                line = line.decode(enc, "replace")
                r = c.split(line)
                if len(r) < 3:
                    # ignore this line
                    pos = f.tell()
                    continue
                if r[1] > ctime:
                    completed = False
                    break
                log.append([r[1], r[2]])
                pos = f.tell()
                if idx >= 1024 and not all_records:
                    completed = False
                    break
                if pos == eofs:
                    if ecode is None:
                        completed = False
                    break

        return pos, completed

    def status(self, out=0, err=0):
        ctime = datetime.now().strftime("%Y%m%d%H%M%S%f")

        stdout = []
        stderr = []
        out_completed = err_completed = False
        process_output = out != -1 and err != -1

        job = Job.objects.filter(id=self.id, user=self.user).first()
        enc = sys.getdefaultencoding()
        if enc == "ascii":
            enc = "utf-8"

        duration = None

        if job is not None:
            all_records = (out == 0 and err == 0) and job.end_time
            status, updated = BatchJob.update_job_info(job)
            if updated:
                job.save()
            self.start_time = job.start_time
            self.end_time = job.end_time
            self.exit_code = job.exit_code

            if self.start_time is not None:
                stime = self.start_time
                etime = self.end_time or make_aware(datetime.now())

                duration = get_duration(stime, etime)

            if process_output:
                out, out_completed = self.read_log(
                    self.stdout, stdout, out, ctime, self.exit_code, enc, all_records
                )
                err, err_completed = self.read_log(
                    self.stderr, stderr, err, ctime, self.exit_code, enc, all_records
                )
        else:
            out_completed = err_completed = False

        return {
            "out": {"pos": out, "lines": stdout, "done": out_completed},
            "err": {"pos": err, "lines": stderr, "done": err_completed},
            "start_time": self.start_time,
            "exit_code": self.exit_code,
            "duration": duration,
        }

    @staticmethod
    def _check_start_time(job, data):
        """
        Check start time and its related other timing checks.
        :param job: Job.
        :param data: Data
        :return:
        """
        changed = False
        if "start_time" in data and data.get("start_time", None):
            new_start_time = make_aware(
                datetime.strptime(data["start_time"], "%Y%m%d%H%M%S%f")
            )
            if job.start_time != new_start_time:
                job.start_time = new_start_time
                changed = True
            if "exit_code" in data and data.get("exit_code", None) is not None:
                job.exit_code = data["exit_code"]
                changed = True

                if "end_time" in data and data.get("end_time", None):
                    job.end_time = make_aware(
                        datetime.strptime(data["end_time"], "%Y%m%d%H%M%S%f")
                    )
                    changed = True
        return changed

    @staticmethod
    def update_job_info(job):
        if job.start_time is None or job.end_time is None:
            status = os.path.join(job.logdir, "status")
            if not os.path.isfile(status):
                return False, False

            with open(status, "r") as fp:
                try:
                    data = json.load(fp)

                    changed = BatchJob._check_start_time(job, data)

                    if "pid" in data and job.utility_pid != data["pid"]:
                        job.utility_pid = data["pid"]
                        changed = True

                    return True, changed

                except ValueError as e:
                    return False, False

        return True, False

    @staticmethod
    def _check_job_description(job):
        """
        Check job desc instance and return data according to job.
        :param job: job
        :return: return value for details, type_desc and desc related
        to job
        """
        try:
            description = loads(bytes.fromhex(job.description))
        except Exception:
            description = loads(job.description)

        details = ""
        type_desc = ""

        if isinstance(description, IJobDesc):
            args = []
            args_csv = StringIO(
                job.arguments.encode("utf-8")
                if hasattr(job.arguments, "decode")
                else job.arguments
            )
            args_reader = csv.reader(args_csv, delimiter=str(","))
            for arg in args_reader:
                args = args + arg

            # Determine if the description is an old version
            if not hasattr(description, '_connection_name'):
                # Manually set the necessary attributes for old versions
                description._connection_name = description.get_connection_name()
                job.description = dumps(description).hex()
                job.save()

            details = description.details(job.command)
            type_desc = description.type_desc
            description = description.message

        return description, details, type_desc

    @staticmethod
    def list(user):
        jobs = Job.objects.filter(user=user).select_related("connection").order_by(F("start_time").desc(nulls_first=True))

        res = []
        for job in jobs:
            status, updated = BatchJob.update_job_info(job)
            if not status:
                continue

            start_time = job.start_time
            end_time = job.end_time or make_aware(datetime.now())
            duration = get_duration(start_time, end_time)

            (
                description,
                details,
                type_desc,
            ) = BatchJob._check_job_description(job)
            res.append(
                {
                    "id": job.id,
                    "description": description,
                    "type_desc": type_desc,
                    "details": details,
                    "start_time": start_time,
                    "end_time": job.end_time,
                    "exit_code": job.exit_code,
                    "duration": duration,
                    "process_state": job.process_state,
                    "utility_pid": job.utility_pid,
                    "conn_id": job.connection.id,
                }
            )

            if updated:
                job.save()

        return res

    @staticmethod
    def delete(job_id, user):
        job = Job.objects.filter(user=user, id=job_id).first()

        if job is None:
            raise LookupError(PROCESS_NOT_FOUND)

        logdir = job.logdir

        try:
            process = psutil.Process(job.utility_pid)
            process.terminate()
        except psutil.NoSuchProcess:
            job.process_state = PROCESS_TERMINATED
        except psutil.Error as error:
            raise

        job.delete()

        shutil.rmtree(logdir, True)

    @staticmethod
    def stop_job(job_id, user):
        job = Job.objects.filter(user=user, id=job_id).first()

        if job is None:
            raise LookupError(PROCESS_NOT_FOUND)

        try:
            process = psutil.Process(job.utility_pid)
            process.terminate()

            job.process_state = PROCESS_TERMINATED
        except psutil.NoSuchProcess:
            job.process_state = PROCESS_TERMINATED
        except psutil.Error as error:
            raise

        job.save()


def escape_dquotes_process_arg(arg):
    # Double quotes has special meaning for shell command line and they are
    # run without the double quotes. Add extra quotes to save our double
    # quotes from stripping.

    dq_id = "#DQ#"

    if arg.startswith('"') and arg.endswith('"'):
        return r"{0}{1}{0}".format(dq_id, arg)
    else:
        return arg
