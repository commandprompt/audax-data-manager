import io
import logging
from typing import Optional

import paramiko
from app.include import OmniDatabase
from app.include.Session import Session
from app.include.Spartacus.Database import supported_rdbms
from app.models import Connection, Group, GroupConnection, Tab, Technology
from app.utils.auth_methods import uses_iam_auth
from app.utils.crypto import decrypt, encrypt
from app.utils.decorators import session_required, user_authenticated
from app.utils.key_manager import key_manager
from django.db.models import Q, Prefetch
from django.http import HttpResponse, JsonResponse
from sshtunnel import SSHTunnelForwarder

logger = logging.getLogger(__name__)

@user_authenticated
@session_required
def get_connections(request, session: Session):
    response_data = {'data': [], 'status': 'success'}

    tech_list = list(
        Technology.objects.filter(
            Q(name__in=[rdbms.lower() for rdbms in supported_rdbms])
            | Q(name="terminal")
        ).values_list("name", flat=True)
    )

    connection_list = []
    connections = Connection.objects.filter(
        Q(user=request.user) | Q(public=True)
    ).select_related('user', 'technology').prefetch_related(
        Prefetch('groupconnection_set', queryset=GroupConnection.objects.select_related('group'))
    )

    if connections and key_manager.get(request.user):
        for conn in connections:
            conn_object = {
                'id': conn.id,
                'locked': False,
                'public': conn.public,
                'is_mine': conn.user.id == request.user.id,
                'technology': conn.technology.name,
                'group': conn.groupconnection_set.first().group.id if conn.groupconnection_set.exists() else None,
                'alias': conn.alias,
                'conn_string': '',
                'server': '',
                'port': '',
                'service': '',
                'user': '',
                'password': '',
                'password_set': False,
                'color_label': conn.color_label,
                'tunnel': {
                    'enabled': conn.use_tunnel,
                    'server': conn.ssh_server,
                    'port': conn.ssh_port,
                    'user': conn.ssh_user,
                    'password': '',
                    'password_set': False if conn.ssh_password.strip() == '' else True,
                    'key': '',
                    'key_set': False if conn.ssh_key.strip() == '' else True
                },
                'connection_params': conn.connection_params,
                'credentials_extra': conn.masked_credentials_extra(),
                'last_used_database': conn.last_used_database,
                'last_access_date': conn.last_access_date,
                'autocomplete': conn.autocomplete,
            }
            database_object = session.databases.get(conn.id)

            if conn.technology.name == 'terminal':
                details = (
                    database_object["tunnel"]["user"]
                    + "@"
                    + database_object["tunnel"]["server"]
                    + ":"
                    + database_object["tunnel"]["port"]
                )
                conn_object['details1'] = details

            if conn.technology.name != 'terminal':
                database = database_object.get('database')
                # don't crash when omnidatabase interface is not available
                # this may happen if previously created db connection
                # is not supported in the current variant of pgmanage
                if database is None:
                    logger.error(f"Failed to initialize obtain OmniDatabase instance for {conn.technology.name}")
                    continue

                details = database.PrintDatabaseDetails()
                if database_object["tunnel"]["enabled"]:
                    details += f" ({database_object['tunnel']['server']}:{database_object['tunnel']['port']})"
                conn_object['console_help'] = database.console_help
                conn_object['details1'] = database.PrintDatabaseInfo()
                conn_object['details2'] = details
                conn_object['conn_string'] = conn.conn_string
                conn_object['server'] = conn.server
                conn_object['port'] = conn.port
                conn_object['service'] = conn.database
                conn_object['user'] = conn.username
                conn_object['password'] = ''
                conn_object['password_set'] = False if conn.password.strip() == '' else True
                conn_object['decryption_failed'] = database_object.get("decryption_failed", False)

            connection_list.append(conn_object)

    response_data['data'] = {
        'connections': connection_list,
        'technologies': tech_list
    }

    return JsonResponse(response_data)


@user_authenticated
@session_required(include_session=False)
def get_groups(request):
    response_data = {'data': [], 'status': 'success'}

    groups = Group.objects.filter(user=request.user)

    for group in groups:
        current_group_data = {
            'id': group.id,
            'name': group.name,
            'conn_list': list(GroupConnection.objects.filter(group=group).values_list('connection__id', flat=True))
        }

        response_data['data'].append(current_group_data)

    return JsonResponse(response_data)


@user_authenticated
def delete_group(request):
    group_id: Optional[int] = request.data.get('id')

    group = Group.objects.filter(id=group_id).select_related("user").first()
        
    if group:
        if group.user.id != request.user.id:
            return JsonResponse(data={"data": 'This group does not belong to you.'}, status=403)

        group.delete()

    return HttpResponse(status=204)


@user_authenticated
def save_group(request):
    group_object = request.data
    group_id = group_object.get('id', None)
    group_name = group_object.get('name')

    if not group_name or not group_name.strip():
        return JsonResponse(data={"data": "Group name can not be empty."}, status=400)

    try:
        # New group
        if group_id is None:
            db_group = Group.objects.filter(user=request.user, name=group_name)
            if db_group:
                return JsonResponse(data={"data": "Group with this name already exists."}, status=400)

            group = Group(user=request.user, name=group_name)
            group.save()
        # update
        else:
            group = Group.objects.filter(id=group_id).select_related("user").first()
            if not group:
                return JsonResponse(data={"data": "Group not found."}, status=404)

            if group.user.id != request.user.id:
                return JsonResponse(data={"data": "This group does not belong to you."}, status=403)

            group.name = group_name
            group.save()

        # cleanup other group relations which reference same connection ids
        # sanitize incoming conn ids vs request.user
        conns = Connection.objects.filter(user=request.user, id__in=group_object['conn_list'])
        # delete all group members, then recreate from conns
        GroupConnection.objects.filter(group=group).delete()
        GroupConnection.objects.bulk_create(
            [GroupConnection(group=group, connection=conn) for conn in conns]
        )
        # create new group relations with group.id

    except Exception as exc:
        return JsonResponse(data={"data": str(exc)}, status=400)


    return HttpResponse(status=200)


@user_authenticated
@session_required(include_session=False)
def test_connection(request):
    conn_object = request.data
    conn_id = conn_object['id']
    conn_type = conn_object['technology']

    conn_params = conn_object['connection_params']

    password = conn_object.get('password','').strip()
    ssh_password = conn_object['tunnel']['password'].strip()
    ssh_key = conn_object['tunnel']['key']
    key = key_manager.get(request.user)
    credentials_extra = dict(conn_object.get('credentials_extra') or {})

    if conn_id:
        conn = Connection.objects.filter(id=conn_id).first()
        if not conn:
                return JsonResponse(data={"data": "Connection not found."}, status=404)

        if conn.user.id != request.user.id:
                return JsonResponse(data={"data": 'This connection does not belong to you.'}, status=403)
        try:
            if password == '' and conn_type != 'terminal' and conn_object.get("password_set") is True:
                password = decrypt(conn.password, key) if conn.password else ''
            if ssh_password == '' and conn_object['tunnel']['password_set'] is True:
                ssh_password = decrypt(conn.ssh_password, key) if conn.ssh_password else ''
            if conn_object['tunnel']['key'].strip() == '':
                ssh_key = decrypt(conn.ssh_key, key) if conn.ssh_key else ''
            credentials_extra = conn.resolve_credentials_extra(credentials_extra, key)
        except UnicodeDecodeError:
            return JsonResponse(data={"data": "There was an error decrypting the passwords. Please try re-saving them to encrypt with the new key."}, status=400)
    if conn_type == 'terminal':

        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            # ssh key provided
            if ssh_key.strip() != '':
                key = paramiko.RSAKey.from_private_key(io.StringIO(ssh_key), password=ssh_password or None)
                client.connect(hostname=conn_object['tunnel']['server'], username=conn_object['tunnel']['user'],
                               pkey=key, passphrase=ssh_password,
                               port=int(conn_object['tunnel']['port']), timeout=5)
            else:
                client.connect(hostname=conn_object['tunnel']['server'], username=conn_object['tunnel']['user'],
                               password=ssh_password, port=int(conn_object['tunnel']['port']), timeout=5)

            client.close()
        except Exception as exc:
            msg = str(exc)
            if "checkints" in msg:
                msg = "Unable to decrypt SSH Key. Wrong passphrase?"
            return JsonResponse({"data": msg}, status=400)
    else:

        database = OmniDatabase.Generic.InstantiateDatabase(
            conn_type,
            conn_object['server'],
            conn_object['port'],
            conn_object['service'],
            conn_object['user'],
            password,
            -1,
            '',
            conn_string=conn_object['conn_string'],
            parse_conn_string=True,
            connection_params=conn_params,
            credentials_extra=credentials_extra
        )

        # create tunnel if enabled
        if conn_object['tunnel']['enabled']:

            try:
                if ssh_key.strip() != '':
                    key = paramiko.RSAKey.from_private_key(io.StringIO(ssh_key), password=ssh_password or None)
                    server = SSHTunnelForwarder(
                        (conn_object['tunnel']['server'], int(conn_object['tunnel']['port'])),
                        ssh_username=conn_object['tunnel']['user'],
                        ssh_private_key_password=ssh_password,
                        ssh_pkey=key,
                        remote_bind_address=(database.active_server, int(database.active_port)),
                        logger=None,
                        set_keepalive=120,
                    )
                else:
                    server = SSHTunnelForwarder(
                        (conn_object['tunnel']['server'], int(conn_object['tunnel']['port'])),
                        ssh_username=conn_object['tunnel']['user'],
                        ssh_password=ssh_password,
                        remote_bind_address=(database.active_server, int(database.active_port)),
                        logger=None,
                        set_keepalive=120
                    )
                server.start()

                database.connection.host = '127.0.0.1'
                database.connection.port = server.local_bind_port

                message, status = database.TestConnection()
                server.close()
                if not status:
                    return JsonResponse({"data": message}, status=400)

            except Exception as exc:
                msg = str(exc)
                if "checkints" in msg:
                    msg = "Unable to decrypt SSH Key. Wrong passphrase?"
                return JsonResponse({"data": msg}, status=400)

        else:
            message, status = database.TestConnection()
            if not status:
                return JsonResponse({"data": message}, status=400)

    return JsonResponse({"data": message})


@user_authenticated
@session_required
def save_connection(request, session: Session):
    response_data = {'data': '', 'status': 'success'}
    key = key_manager.get(request.user)

    conn_object = request.data
    conn_id = conn_object['id']

    try:
        # New connection
        if conn_id is None:
            password = ''
            tunnel_password = ''
            tunnel_key = ''
            if conn_object['password']:
                password = encrypt(conn_object['password'], key)
            if conn_object['tunnel']['password'] != '':
                tunnel_password = encrypt(conn_object['tunnel']['password'], key)
            if conn_object['tunnel']['key'] != '':
                tunnel_key = encrypt(conn_object['tunnel']['key'], key)
            conn = Connection(
                user=request.user,
                technology=Technology.objects.get(name=conn_object['technology']),
                server=conn_object['server'],
                port=conn_object['port'],
                database=conn_object['service'],
                username=conn_object['user'],
                password=password,
                alias=conn_object['alias'],
                ssh_server=conn_object['tunnel']['server'],
                ssh_port=conn_object['tunnel']['port'],
                ssh_user=conn_object['tunnel']['user'],
                ssh_password=tunnel_password,
                ssh_key=tunnel_key,
                use_tunnel=conn_object['tunnel']['enabled'],
                conn_string=conn_object['conn_string'],
                public=False,
                connection_params=conn_object['connection_params'],
                color_label= conn_object['color_label']
            )
            conn.set_credentials_extra(conn_object.get('credentials_extra'), key)
            conn.save()
        # update
        else:
            conn = Connection.objects.filter(id=conn_id).select_related('user').first()

            if conn.user.id != request.user.id:
                response_data['data'] = 'This connection does not belong to you.'
                response_data['status'] = 'failed'
                return JsonResponse(response_data, status=403)

            conn.technology = Technology.objects.get(name=conn_object['technology'])
            conn.server = conn_object['server']
            conn.port = conn_object['port']
            if conn.database != conn_object['service']:
                conn.last_used_database = conn_object['service']
            conn.database = conn_object['service']
            conn.username = conn_object['user']

            if conn.technology.name != 'terminal':
                if conn_object['password'] is not None:
                    if conn_object['password'].strip() != '':
                        conn.password = encrypt(conn_object['password'], key)
                # clear password if password_set false AND the password is empty
                if conn_object['password_set'] is False and conn_object['password'] == '':
                    conn.password = ''

            conn.alias = conn_object['alias']
            conn.ssh_server = conn_object['tunnel']['server']
            conn.ssh_port = conn_object['tunnel']['port']
            conn.ssh_user = conn_object['tunnel']['user']
            if conn_object['tunnel']['password'] is not None:
                if conn_object['tunnel']['password'].strip() != '':
                    conn.ssh_password = encrypt(conn_object['tunnel']['password'], key)

            if conn_object['tunnel']['password_set'] is False and conn_object['tunnel']['password'] == '':
                conn.ssh_password = ''

            if conn_object['tunnel']['key'].strip() != '':
                conn.ssh_key = encrypt(conn_object['tunnel']['key'], key)

            if conn_object['tunnel']['key_set'] is False and conn_object['tunnel']['key'].strip() == '':
                conn.ssh_key = ''

            if conn.technology.name in ['mariadb', 'mysql']:
                conn.connection_params = {}

            for k, v in conn_object["connection_params"].items():
                conn.connection_params[k] = v

            conn.set_credentials_extra(conn_object.get('credentials_extra'), key)

            conn.use_tunnel = conn_object['tunnel']['enabled']
            conn.conn_string = conn_object['conn_string']
            conn.autocomplete = conn_object.get('autocomplete')
            conn.color_label= conn_object['color_label']
            conn.save()


        # cleanup existing references (if any)
        GroupConnection.objects.filter(connection=conn).delete()

        if conn_object['group']:
            conn_group = Group.objects.filter(id=conn_object['group'], user=request.user).first()
            if conn_group:
                gc = GroupConnection(connection=conn, group=conn_group)
                gc.save()

        tunnel_information = {
            'enabled': conn.use_tunnel,
            'server': conn.ssh_server,
            'port': conn.ssh_port,
            'user': conn.ssh_user,
            'password': decrypt(conn.ssh_password, key) if conn.ssh_password else '',
            'key': decrypt(conn.ssh_key, key) if conn.ssh_key else ''
        }
        # this is for sqlite3 db connection because it has no password
        password = decrypt(conn.password, key) if conn.password else ''
        credentials_extra = conn.get_credentials_extra(key)
        database = OmniDatabase.Generic.InstantiateDatabase(
            conn.technology.name,
            conn.server,
            conn.port,
            conn.database,
            conn.username,
            password,
            conn.id,
            conn.alias,
            conn_string=conn.conn_string,
            parse_conn_string=True,
            connection_params=conn.connection_params,
            credentials_extra=credentials_extra
        )

        # IAM authentication gets a token for each connection, thus never ask a password
        prompt_password = conn.password == '' and not uses_iam_auth(credentials_extra)

        session.AddDatabase(conn.id, conn.technology.name, database, prompt_password, tunnel_information, conn.alias,
                              conn_object['public'])

    except Exception as exc:
        response_data['data'] = str(exc)
        response_data['status'] = 'failed'
        return JsonResponse(response_data, status=400)

    request.session['pgmanage_session'] = session

    return JsonResponse(response_data)


@user_authenticated
@session_required
def delete_connection(request, session: Session):
    conn_id: Optional[int] = request.data.get('id')

    conn = Connection.objects.filter(id=conn_id).first()
    if conn:
        if conn.user.id != request.user.id:
            return JsonResponse(data={"data": "This connection does not belong to you."}, status=403)

        conn.delete()
        session.RemoveDatabase(conn_id)
        request.session['pgmanage_session'] = session

    return HttpResponse(status=204)


@user_authenticated
@session_required
def get_existing_tabs(request, session: Session):

    existing_tabs = []
    for tab in Tab.objects.filter(user=request.user).order_by("connection"):
        if tab.connection.public or tab.connection.user.id == request.user.id:
            existing_tabs.append(
                {
                    "index": tab.connection.id,
                    "snippet": tab.snippet,
                    "title": tab.title,
                    "tab_db_id": tab.id,
                    "database_name": tab.database
                }
            )

    request.session["pgmanage_session"] = session

    return JsonResponse({"existing_tabs": existing_tabs})
