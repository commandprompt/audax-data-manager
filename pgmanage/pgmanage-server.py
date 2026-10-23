#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import shutil
import sys
import platform
import random
import string
import importlib

#Parameters
import optparse
import configparser
import threading

import psutil
import pgmanage.custom_settings

pgmanage.custom_settings.DEV_MODE = False
pgmanage.custom_settings.DESKTOP_MODE = False

parser = optparse.OptionParser(version=pgmanage.custom_settings.PGMANAGE_VERSION)

group = optparse.OptionGroup(parser, "General Options")

group.add_option("-d", "--homedir", dest="homedir",
                  default='', type=str,
                  help="home directory containing config and log files")

group.add_option("-C", "--configfile", dest="conf",
                  default='', type=str,
                  help="configuration file")

group.add_option("-i", "--init", dest="init",
                  action="store_true",
                  default=False,
                  help="Create home directory containing config and log files")

parser.add_option_group(group)

group = optparse.OptionGroup(parser, "Webserver Options")

group.add_option("-H", "--host", dest="host",
                  default=None, type=str,
                  help="listening address")

group.add_option("-p", "--port", dest="port",
                  default=None, type=int,
                  help="listening port")

group.add_option("-t", "--threads", dest="threads",
                  default=None, type=int,
                  help="listening thread count")

group.add_option("-q", "--queuesize", dest="queue_size",
                  default=None, type=int,
                  help="socket queue size")

group.add_option("-A", "--app", dest="app",
                  action="store_true",
                  default=False,
                  help=optparse.SUPPRESS_HELP)

group.add_option("-P", "--path", dest="path",
                  default='', type=str,
                  help="path to access the application, other than /")

parser.add_option_group(group)

group = optparse.OptionGroup(parser, "Management Options",
                             "Options to list, create and drop users and connections.")
group.add_option("-r", "--resetdatabase", dest="reset",
                  default=False, action="store_true",
                  help="reset user and session databases")
group.add_option("-j", "--jsonoutput", dest="jsonoutput",
                  default=False, action="store_true",
                  help="format list output as json")
group.add_option("-l", "--listusers", dest="listusers",
                  default=False, action="store_true",
                  help="list users")
group.add_option("-u", "--createuser", dest="createuser",
                  nargs=2,metavar="username password",
                  help="create user: -u username password")
group.add_option("-s", "--createsuperuser", dest="createsuperuser",
                  nargs=2,metavar="username password",
                  help="create super user: -s username password")
group.add_option("-x", "--dropuser", dest="dropuser",
                  nargs=1,metavar="username",
                  help="drop user: -x username")
group.add_option("-m", "--listconnections", dest="listconnections",
                  nargs=1,metavar="username",
                  help="list connections: -m username")
group.add_option("-c", "--createconnection", dest="createconnection",
                  nargs=8,metavar="username technology title host port database dbuser dbpassword",
                  help="create connection: -c username technology host port database dbuser dbpassword")
group.add_option("-z", "--dropconnection", dest="dropconnection",
                  nargs=1,metavar="connid",
                  help="drop connection: -z connid")
parser.add_option_group(group)

(options, args) = parser.parse_args()

#Generate random token if in app mode
if options.app:
    pgmanage.custom_settings.DESKTOP_MODE = True
    pgmanage.custom_settings.APP_TOKEN = ''.join(random.choice(string.ascii_lowercase + string.digits) for i in range(50))
    app_version = True
else:
    app_version = False

if options.homedir!='':
    if not os.path.exists(options.homedir):
        print("Home directory does not exist. Please specify a directory that exists.",flush=True)
        sys.exit()
    else:
        pgmanage.custom_settings.HOME_DIR = options.homedir
else:
    if pgmanage.custom_settings.DESKTOP_MODE:
        pgmanage.custom_settings.HOME_DIR = os.path.join(os.path.expanduser('~'), '.audaxdm', 'audaxdm-app')
        LEGACY_HOME_DIR = os.path.join(os.path.expanduser('~'), '.pgmanage', 'pgmanage-app')
    else:
        pgmanage.custom_settings.HOME_DIR = os.path.join(os.path.expanduser('~'), '.audaxdm', 'audaxdm-server')
        LEGACY_HOME_DIR = os.path.join(os.path.expanduser('~'), '.pgmanage', 'pgmanage-server')

    if not os.path.exists(pgmanage.custom_settings.HOME_DIR):
        if os.path.exists(LEGACY_HOME_DIR):
            # Migrate legact pgmanage application data from ~.pgmanage
            # TODO: this code can be safely removed in 2027, once most of the people stopped using audax < 1.5
            import shutil
            import glob

            print("Migrating legacy pgmanage user data to a new home directory:",flush=True)
            shutil.copytree(LEGACY_HOME_DIR, pgmanage.custom_settings.HOME_DIR, dirs_exist_ok=True)
            import pgmanage.settings
            new_db = pgmanage.settings.SQLITE_PATH

            db_dir = os.path.dirname(new_db)
            new_filename = os.path.basename(new_db)
            old_filename = new_filename.replace('audaxdm', 'pgmanage', 1)
            old_db = os.path.join(db_dir, old_filename)

            if os.path.exists(old_db):
                os.rename(old_db, new_db)
                print(f"Migrated {old_db} {new_db}", flush=True)

            log_pattern = os.path.join(pgmanage.custom_settings.HOME_DIR, 'pgmanage*.log*')
            for old_log_path in glob.glob(log_pattern):
                # Extract the filename, replace the prefix, and rebuild the path
                filename = os.path.basename(old_log_path)
                new_filename = filename.replace('pgmanage', 'audaxdm', 1)
                new_log_path = os.path.join(pgmanage.custom_settings.HOME_DIR, new_filename)

                os.rename(old_log_path, new_log_path)
                print(f"Migrated {old_log_path} {new_log_path}", flush=True)
        else:
            print("Creating home directory.",flush=True)
            os.makedirs(pgmanage.custom_settings.HOME_DIR)


if options.conf!='':
    if not os.path.exists(options.conf):
        print("Config file not found. Please specify a file that exists.",flush=True)
        sys.exit()
    else:
        config_file = options.conf
else:
    config_file = os.path.join(pgmanage.custom_settings.HOME_DIR, 'config.py')
    if not os.path.exists(config_file):
        print("Copying config file to home directory.",flush=True)
        shutil.copyfile(os.path.join(pgmanage.custom_settings.BASE_DIR, 'config.py'), config_file)

if options.init:
    sys.exit()

# Loading config file
spec = importlib.util.spec_from_file_location("pgmanage_settings", config_file)
module = importlib.util.module_from_spec(spec)
sys.modules['pgmanage_settings'] = module
spec.loader.exec_module(module)
pgmanage_settings = module

if options.host!=None:
    listening_address = options.host
else:
    if hasattr(pgmanage_settings,'LISTENING_ADDRESS'):
        listening_address = pgmanage_settings.LISTENING_ADDRESS
    else:
        listening_address = '127.0.0.1'

if options.port!=None:
    listening_port = options.port
else:
    if options.app:
        listening_port = random.randint(25000,32676)
    else:
        if hasattr(pgmanage_settings,'LISTENING_PORT'):
            listening_port = pgmanage_settings.LISTENING_PORT
        else:
            listening_port = 8000

if options.queue_size!=None:
    queue_size = options.queue_size
else:
    if hasattr(pgmanage_settings,'QUEUE_SIZE'):
        queue_size = pgmanage_settings.QUEUE_SIZE
    else:
        queue_size = 5

if options.threads!=None:
    threads = options.threads
else:
    if hasattr(pgmanage_settings,'THREADS'):
        threads = pgmanage_settings.THREADS
    else:
        threads = 10

if options.path!='':
    pgmanage.custom_settings.PATH = options.path
else:
    if hasattr(pgmanage_settings,'CUSTOM_PATH'):
        pgmanage.custom_settings.PATH = pgmanage_settings.CUSTOM_PATH

if hasattr(pgmanage_settings,'IS_SSL'):
    is_ssl = pgmanage_settings.IS_SSL
    if is_ssl:
        pgmanage.custom_settings.SESSION_COOKIE_SECURE = True
        pgmanage.custom_settings.CSRF_COOKIE_SECURE = True
else:
    is_ssl = False

if hasattr(pgmanage_settings,'SSL_CERTIFICATE_FILE'):
    ssl_certificate_file = pgmanage_settings.SSL_CERTIFICATE_FILE

    if is_ssl and not os.path.exists(ssl_certificate_file):
        print("Certificate file not found. Please specify a file that exists.",flush=True)
        sys.exit()
else:
    ssl_certificate_file = ''

if hasattr(pgmanage_settings,'SSL_KEY_FILE'):
    ssl_key_file = pgmanage_settings.SSL_KEY_FILE

    if is_ssl and not os.path.exists(ssl_key_file):
        print("Key file not found. Please specify a file that exists.",flush=True)
        sys.exit()
else:
    ssl_key_file = ''


#importing settings after setting HOME_DIR and other required parameters
import pgmanage.settings
import pgmanage.logging_filter

# the app directory can be read-only, keep export files in the home directory
pgmanage.settings.TEMP_DIR = os.path.join(pgmanage.custom_settings.HOME_DIR, 'temp')

# Adjust pgmanage settings based on the content of the config file
for attribute, value in pgmanage_settings.__dict__.items():
    setattr(pgmanage.settings,attribute,value)

# OmniDatabase import looks unused, this is a trick to force pyinstaller to include it into bundle
# TODO: implement custom hooks and move any such imports there

import app.include.OmniDatabase as OmniDatabase
from app.include.Spartacus.Database import supported_rdbms

if 'SQLite' in supported_rdbms and not pgmanage.custom_settings.DESKTOP_MODE:
    supported_rdbms.remove('SQLite')

import logging
import logging.config

logger = logging.getLogger('app.Init')

import pgmanage
import app
import app.apps
os.environ['DJANGO_SETTINGS_MODULE'] = 'pgmanage.settings'
import django
from django.core.management import call_command
django.setup()
from app.models.main import *
from django.contrib.auth.models import User
from django.utils import timezone

print('''Running database migrations...''',flush=True)
logger.info('''Running Database Migrations...''')

from os import devnull
try:
    call_command("migrate", interactive=False)
    call_command("clearsessions")
except Exception as exc:
    print(str(exc),flush=True)
    logger.error(str(exc))
    sys.exit()


maintenance_action = False

def create_user(p_user,p_pwd,p_superuser):
    User.objects.create_user(username=p_user,
                             password=p_pwd,
                             email='',
                             last_login=timezone.now(),
                             is_superuser=p_superuser,
                             first_name='',
                             last_name='',
                             is_staff=False,
                             is_active=True,
                             date_joined=timezone.now())

if options.reset:
    maintenance_action = True
    print('*** ATENTION *** ALL USERS DATA WILL BE LOST')
    try:
        value = input('Would you like to continue? (y/n) ')
        if value.lower()=='y':
            # Removing users
            User.objects.all().delete()
            # Create default admin user
            create_user('admin', 'admin', True)
    except Exception as exc:
        print('Error:')
        print(exc)

if options.listusers:
    from app.include.Spartacus.Database import DataTable
    table = DataTable(simple=True)
    table.AddColumn('id')
    table.AddColumn('username')
    table.AddColumn('superuser')

    maintenance_action = True
    users = User.objects.all()
    for user in users:
        table.AddRow([user.id,user.username,user.is_superuser])
    if options.jsonoutput:
        print(table.Jsonify())
    else:
        print(table.Pretty())

if options.createuser:
    maintenance_action = True
    create_user(options.createuser[0], options.createuser[1], False)

if options.createsuperuser:
    maintenance_action = True
    create_user(options.createsuperuser[0], options.createsuperuser[1], True)

if options.dropuser:
    maintenance_action = True
    User.objects.get(username=options.dropuser).delete()

if options.listconnections:
    maintenance_action = True

    from app.include.Spartacus.Database import DataTable
    table = DataTable(simple=True)
    table.AddColumn('id')
    table.AddColumn('technology')
    table.AddColumn('alias')
    table.AddColumn('connstring')
    table.AddColumn('host')
    table.AddColumn('port')
    table.AddColumn('database')
    table.AddColumn('user')
    table.AddColumn('tunnel enabled')
    table.AddColumn('tunnel server')
    table.AddColumn('tunnel port')
    table.AddColumn('tunnel user')

    maintenance_action = True

    for conn in Connection.objects.filter(user=User.objects.get(username=options.listconnections)):
        table.AddRow(
            [
                conn.id,
                conn.technology.name,
                conn.alias,
                conn.conn_string,
                conn.server,
                conn.port,
                conn.database,
                conn.username,
                conn.use_tunnel,
                conn.ssh_server,
                conn.ssh_port,
                conn.ssh_user
            ]
        )

    if options.jsonoutput:
        print(table.Jsonify())
    else:
        print(table.Pretty())

if options.createconnection:
    maintenance_action = True

    connection = Connection(
        user=User.objects.get(username=options.createconnection[0]),
        technology=Technology.objects.get(name=options.createconnection[1]),
        server=options.createconnection[3],
        port=options.createconnection[4],
        database=options.createconnection[5],
        username=options.createconnection[6],
        password=options.createconnection[7],
        alias=options.createconnection[2],
        ssh_server='',
        ssh_port='',
        ssh_user='',
        ssh_password='',
        ssh_key='',
        use_tunnel=False,
        conn_string='',

    )
    connection.save()

if options.dropconnection:
    maintenance_action = True
    Connection.objects.get(id=options.dropconnection).delete()


# Maintenance performed, exit before starting webserver
if maintenance_action == True:
    sys.exit()

# This line was reached, so not a maintenance run, lock HOME DIR if not on Windows

if platform.system() != 'Windows':
    import fcntl
    try:
        lockfile_pointer = os.open(pgmanage.custom_settings.HOME_DIR, os.O_RDONLY)
        fcntl.flock(lockfile_pointer, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except Exception as exc:
        print("Audax Data Manager is already running pointing to directoy '{0}'.".format(pgmanage.custom_settings.HOME_DIR))
        sys.exit()

import html.parser
import http.cookies

import django.template.defaulttags
import django.template.loader_tags
import django.contrib.staticfiles
import django.contrib.staticfiles.apps
import django.contrib.auth.apps
import django.contrib.contenttypes.apps
import django.contrib.sessions.apps
import django.contrib.messages.apps
import app.urls
import django.contrib.messages.middleware
import django.contrib.auth.middleware
import django.contrib.sessions.middleware
import django.contrib.sessions.serializers
import django.template.loaders
import django.contrib.auth.context_processors
import django.contrib.messages.context_processors
import django.views.defaults
import django.contrib.auth.password_validation

from django.core.handlers.wsgi import WSGIHandler
from pgmanage import startup

import time
import cherrypy

from django.contrib.sessions.backends.db import SessionStore

import socket
import random
import urllib.request


def check_parent_process():
    # Get the initial parent process ID using psutil
    parent_pid = psutil.Process(os.getpid()).parent().parent().pid

    # Check if the parent process ID exists
    while True:
        if not psutil.pid_exists(parent_pid):
            # If the parent process ID doesn't exist, exit the thread and close the Django app
            cherrypy.engine.exit()
        time.sleep(5)

if options.app:
    # Start the check_parent_process function in a separate thread
    t = threading.Thread(target=check_parent_process)
    t.daemon = True
    t.start()

def check_port(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR, 1)
    try:
        s.bind(("127.0.0.1", port))
    except socket.error as e:
        print(str(e))
        return False
    s.close()
    return True

class DjangoApplication(object):

    def mount_static(self, url, root):
        config = {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': root,
            'tools.expires.on': True,
            'tools.expires.secs': 86400
        }
        cherrypy.tree.mount(None, url, {'/': config})

    def run(self,parameters):
        #cherrypy.engine.unsubscribe('graceful', cherrypy.log.reopen_files)
        logging.config.dictConfig(pgmanage.settings.LOGGING)
        #cherrypy.log.error_log.propagate = False
        cherrypy.log.access_log.propagate = False
        self.mount_static(pgmanage.settings.STATIC_URL, pgmanage.settings.STATIC_ROOT)
        self.mount_static(pgmanage.settings.STATIC_URL + 'temp', pgmanage.settings.TEMP_DIR)

        cherrypy.tree.graft(WSGIHandler())

        port = parameters['listening_port']
        num_attempts = 0

        print('''Checking port availability...''',flush=True)
        logger.info('''Checking port availability...''')

        while not check_port(port):
            print("Port {0} is busy, trying another port...".format(port),flush=True)
            logger.info("Port {0} is busy, trying another port...".format(port))
            port = random.randint(25000,32676)
            num_attempts = num_attempts + 1

            if num_attempts == 20:
                break

        if num_attempts < 20:

            v_cherrypy_config = {
                'server.socket_host': parameters['listening_address'],
                'server.socket_port': port,
                'server.socket_queue_size': parameters['queue_size'],
                'server.thread_pool': parameters['threads'],
                'engine.autoreload_on': False,
                'log.screen': False,
                'log.access_file': '',
                'log.error_file': ''
            }

            if parameters['is_ssl']:
                import ssl
                ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
                ssl_ctx.minimum_version = ssl.TLSVersion.TLSv1_2
                ssl_ctx.load_cert_chain(parameters['ssl_certificate_file'],
                                       parameters['ssl_key_file'])
                v_cherrypy_config['server.ssl_module'] = 'builtin'
                v_cherrypy_config['server.ssl_certificate'] = parameters['ssl_certificate_file']
                v_cherrypy_config['server.ssl_private_key'] = parameters['ssl_key_file']
                v_cherrypy_config['server.ssl_context'] = ssl_ctx

            cherrypy.config.update({
                'global': {
                    'engine.autoreload.on': False
                }
            })

            cherrypy.config.update(v_cherrypy_config)

            print ("Starting server {0} at {1}:{2}{3}.".format(pgmanage.settings.PGMANAGE_VERSION,parameters['listening_address'],str(port),pgmanage.settings.PATH),flush=True)
            logger.info("Starting server {0} at {1}:{2}.".format(pgmanage.settings.PGMANAGE_VERSION,parameters['listening_address'],str(port)))

            # Startup
            startup.startup_procedure()

            cherrypy.engine.start()

            if not app_version:
                print ("Open Audax Data Manager in your favorite browser",flush=True)
                if platform.system() != 'Windows':
                    print ("Press Ctrl+C to exit",flush=True)
            else:
                #Sending response to electron app
                print ("http://localhost:{0}/pgmanage_login/?user=admin&pwd=admin&token={1}".format(str(port),pgmanage.custom_settings.APP_TOKEN),flush=True)

            cherrypy.engine.block()
            cherrypy.engine.exit()
        else:
            print('Tried 20 different ports without success, closing...',flush=True)
            logger.info('Tried 20 different ports without success, closing...')

print('''Starting Audax Data Manager server...''',flush=True)
logger.info('''Starting Audax Data Manager server...''')

#Removing Expired Sessions
SessionStore.clear_expired()

try:
    DjangoApplication().run(
        {
            'listening_address'   : listening_address,
            'listening_port'      : listening_port,
            'is_ssl'              : is_ssl,
            'ssl_certificate_file': ssl_certificate_file,
            'ssl_key_file'        : ssl_key_file,
            'queue_size'          : queue_size,
            'threads'             : threads
        }
    )
except KeyboardInterrupt:
    cherrypy.engine.exit()
    print("")
    print("Bye!")
