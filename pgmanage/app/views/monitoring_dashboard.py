import json

from app.models.main import Connection, MonWidgets, MonWidgetsConnections, Technology
from app.utils.decorators import (
    database_required,
    session_required,
    user_authenticated,
)
from app.views.monitoring_widgets import mysql as mysql_widgets
from app.views.monitoring_widgets import postgresql as postgresql_widgets
from django.core.exceptions import ValidationError
from django.forms.models import model_to_dict
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from RestrictedPython import compile_restricted, safe_builtins
from RestrictedPython.Eval import default_guarded_getitem
from RestrictedPython.Guards import safer_getattr

WIDGET_DIALECT_ALIASES = {
    "mariadb": "mysql",
    "rdspostgresql": "postgresql",
}


def dialect_of(technology):
    """Returns the technology whose widgets the given technology reuses."""
    return WIDGET_DIALECT_ALIASES.get(technology, technology)


builtin_monitoring_widgets = {}


def get_widgets_data():
    try:
        for mon_widget in postgresql_widgets.monitoring_widgets:
            builtin_monitoring_widgets[
                (mon_widget["plugin_name"], mon_widget["id"])
            ] = mon_widget
    except Exception:
        pass

    try:
        for mon_widget in mysql_widgets.monitoring_widgets:
            builtin_monitoring_widgets[
                (mon_widget["plugin_name"], mon_widget["id"])
            ] = mon_widget
    except Exception:
        pass


get_widgets_data()


def _hook_import(name, *args, **kwargs):
    if name not in ["datetime", "random", "decimal", "time"]:
        raise ImportError(f"You cannot import {name} module in this sandbox.")
    return __import__(name, *args, **kwargs)

# lists all available widgets with the same db type , used in widget config modal
# list consist from builtin widgets with the same technology + user customized widgets
@user_authenticated
@database_required(check_timeout=False, open_connection=False)
def monitoring_widgets_list(request, database):
    widget_list = []
    db_type = dialect_of(database.db_type)
    try:
        for _, mon_widget in builtin_monitoring_widgets.items():
            if mon_widget.get("dbms") == db_type:
                widget_list.append(
                    {
                        "id": mon_widget.get("id"),
                        "editable": False,
                        "title": mon_widget.get("title"),
                        "type": mon_widget.get("type"),
                        "interval": mon_widget.get("interval"),
                        "plugin_name": mon_widget.get("plugin_name"),
                    }
                )

        technology = Technology.objects.filter(name=database.db_type).first()

        custom_monitoring_widgets = MonWidgets.objects.filter(
            user=request.user, technology=technology.id
        )

        custom_monitoring_widgets_list = [
            model_to_dict(
                widget, fields=["id", "editable", "type", "interval", "title"]
            )
            for widget in custom_monitoring_widgets
        ]

        widget_list.extend(custom_monitoring_widgets_list)
    except Exception as exc:
        return JsonResponse(data={"data": str(exc)}, status=400)
    return JsonResponse(data={"data": widget_list})


@require_http_methods(["GET", "DELETE", "PUT"])
@user_authenticated
@session_required(include_session=False)
def user_created_widget_detail(request, widget_id):
    if request.method == "GET":
        widget = MonWidgets.objects.filter(user=request.user, id=widget_id).first()
        if not widget:
            return JsonResponse(data={"data": "Widget not found."}, status=404)
        return JsonResponse(
            model_to_dict(widget, exclude=["user", "technology", "editable"])
        )
    if request.method == "PUT":
        data = json.loads(request.body or "{}")
        widget = MonWidgets.objects.filter(user=request.user, id=widget_id).first()
        if not widget:
            return JsonResponse(data={"data": "Widget not found."}, status=404)

        widget.script_chart = data.get("widget_script_chart")
        widget.script_data = data.get("widget_script_data")
        widget.type = data.get("widget_type")
        widget.title = data.get("widget_name")
        widget.interval = data.get("widget_interval")
        try:
            widget.full_clean()
        except ValidationError as exc:
            return JsonResponse(data={"data": str(exc)}, status=400)

        widget.save()

        return JsonResponse(model_to_dict(widget))
    if request.method == "DELETE":
        widget = MonWidgets.objects.filter(user=request.user, id=widget_id).first()

        if not widget:
            return JsonResponse(data={"data": "Widget not found."}, status=404)

        widget.delete()

        return HttpResponse(status=204)


@user_authenticated
@database_required(check_timeout=False, open_connection=False)
def create_widget(request, database):
    data = request.data
    database_index = data.get("database_index")
    widget_name = data.get("widget_name")
    widget_type = data.get("widget_type")
    widget_interval = data.get("widget_interval")
    widget_script_chart = data.get("widget_script_chart")
    widget_script_data = data.get("widget_script_data")

    widget = MonWidgets(
        user=request.user,
        technology=Technology.objects.filter(name=database.db_type).first(),
        script_chart=widget_script_chart,
        script_data=widget_script_data,
        type=widget_type,
        title=widget_name,
        interval=widget_interval,
    )

    try:
        widget.full_clean()
    except ValidationError as exc:
        return JsonResponse(data={"data": str(exc)}, status=400)

    widget.save()
    # create widget configuration for current database connection
    conn_object = Connection.objects.get(id=database_index)
    lastconfig = MonWidgetsConnections.objects.filter(connection_id=database_index).order_by('-position').first()
    position = 0
    if lastconfig:
        position = lastconfig.position + 1
    widget_config = MonWidgetsConnections(
        unit=widget.id,
        user=request.user,
        connection=conn_object,
        interval=widget.interval,
        plugin_name='',
        visible = True,
        position = position
    )
    widget_config.save()
    data = model_to_dict(widget)
    data['visible'] = widget_config.visible
    data['saved_id'] = widget_config.id
    data['position'] = widget_config.position

    return JsonResponse(data=data, status=201)

# lists widgets available on the dashboard
# gets widget configs, creates if no configs found
@user_authenticated
@database_required(check_timeout=False, open_connection=False)
def monitoring_widgets(request, database):
    database_index = request.data.get("database_index")
    widgets = []
    try:
        technology = Technology.objects.filter(name=database.db_type).first()
        conn_object = Connection.objects.get(id=database_index)
        custom_widget_ids = list(MonWidgets.objects.filter(
            user=request.user, technology=technology.id
        ).values_list('id', flat=True))
        # get widget configs for the curernt connection

        builtin_widget_ids = [
            k[1] for k,v in builtin_monitoring_widgets.items()
            if v.get("dbms") == dialect_of(technology.name)
        ]
        available_widget_ids = builtin_widget_ids + custom_widget_ids
        widget_configs = MonWidgetsConnections.objects.filter(
            user=request.user, connection=database_index
        )
        widget_config_ids = list(widget_configs.values_list('unit', flat=True))
        # go over available widget ids and create widget configs for current connection
        for idx, widget_id in enumerate(available_widget_ids):
            # check if the current widget does not have config 
            if(widget_id not in widget_config_ids):
                # builtin widgets have negative ids
                if(widget_id < 0 ):
                    widget = next((
                        w for w in builtin_monitoring_widgets.values()
                        if w.get('dbms') == dialect_of(technology.name)
                        and w.get('id') == widget_id
                    ), None)
                    if widget:
                        widget_config = MonWidgetsConnections(
                            unit=widget.get("id"),
                            user=request.user,
                            connection=conn_object,
                            interval=widget.get("interval"),
                            plugin_name=widget.get("plugin_name"),
                            visible = widget.get("default"),
                            position = idx
                        )
                        widget_config.save()
                else:
                    widget = MonWidgets.objects.filter(pk=widget_id).first()
                    widget_config = MonWidgetsConnections(
                            unit=widget.id,
                            user=request.user,
                            connection=conn_object,
                            interval=widget.interval,
                            plugin_name='',
                            visible = False,
                            position = idx
                        )
                    widget_config.save()

        # reload widget configs
        widget_configs = MonWidgetsConnections.objects.filter(
            user=request.user, connection=database_index
        )

        for widget_config in widget_configs:
            # custom widget
            if widget_config.plugin_name == "":
                try:

                    default_widget = MonWidgets.objects.get(id=widget_config.unit)
                    widget = {
                        "saved_id": widget_config.id,
                        "id": default_widget.id,
                        "title": default_widget.title,
                        "plugin_name": "",
                        "interval": widget_config.interval,
                        "type": default_widget.type,
                        "widget_data": None,
                        "position": widget_config.position,
                        "visible": widget_config.visible,
                        "editable": True
                    }
                    widgets.append(widget)
                except Exception:
                    widget_config.delete()
            else:
                # builtin widget
                # search plugin data
                found = False

                for _, mon_widget in builtin_monitoring_widgets.items():
                    if (
                        mon_widget.get("id") == widget_config.unit
                        and mon_widget.get("plugin_name") == widget_config.plugin_name
                        and mon_widget.get("dbms") == dialect_of(database.db_type)
                    ):
                        found = True
                        widget = {
                            "saved_id": widget_config.id,
                            "id": widget_config.unit,
                            "title": mon_widget.get("title"),
                            "plugin_name": widget_config.plugin_name,
                            "interval": widget_config.interval,
                            "type": mon_widget.get("type"),
                            "widget_data": None,
                            "position": widget_config.position,
                            "visible": widget_config.visible,
                            "editable": False
                        }
                        widgets.append(widget)
                        break
                if not found:
                    widget_config.delete()
    # No mon widgets connections
    except Exception as exc:
        return JsonResponse(data={"data": str(exc)}, status=400)
    return JsonResponse(data={"widgets": widgets})


@user_authenticated
@session_required(include_session=False)
def widget_template(request, widget_id):
    data = request.data

    widget_plugin_name = data.get("plugin_name")
    widget_data = {}

    if not widget_plugin_name:
        widget = MonWidgets.objects.filter(id=widget_id, user_id=request.user.id).first()

        if widget:
            widget_data = {
                "script_chart": widget.script_chart,
                "script_data": widget.script_data,
                "type": widget.type,
                "interval": widget.interval,
            }

    else:
        mon_widget = builtin_monitoring_widgets.get((widget_plugin_name, widget_id))

        if mon_widget:
            widget_data = {
                "interval": mon_widget.get("interval"),
                "script_chart": mon_widget.get("script_chart"),
                "script_data": mon_widget.get("script_data"),
                "type": mon_widget.get("type"),
            }
    return JsonResponse(data=widget_data)


@require_http_methods(["DELETE", "PATCH"])
@user_authenticated
@session_required(include_session=False)
def widget_detail(request, widget_id):
    if request.method == "DELETE":
        widget = MonWidgetsConnections.objects.filter(
            user=request.user, id=widget_id
        ).first()
        if not widget:
            return JsonResponse(data={"data": "Widget not found."}, status=404)
        widget.delete()

        return HttpResponse(status=204)
    if request.method == "PATCH":
        data = json.loads(request.body or "{}")
        interval = data.get("interval")
        position = data.get("posistion")
        visible = data.get("visible")
        widget = MonWidgetsConnections.objects.filter(
            user=request.user, id=widget_id
        ).first()
        if not widget:
            return JsonResponse(data={"data": "Widget not found."}, status=404)

        if interval is not None:
            widget.interval = interval
        if position is not None:
            widget.position = position
        if visible is not None:
            widget.visible = visible
        widget.save()

        return HttpResponse(status=204)


@user_authenticated
@database_required(check_timeout=True, open_connection=True)
def refresh_monitoring_widget(request, database, widget_saved_id):
    widget = request.data.get("widget")

    if widget.get("plugin_name") == "":
        widget_data = MonWidgets.objects.get(id=widget.get("id"))

        script_data = widget_data.script_data
        script_chart = widget_data.script_chart

        widget_data = {
            "saved_id": widget_saved_id,
            "id": widget.get("id"),
            "type": widget_data.type,
            "title": widget_data.title,
            "interval": widget_data.interval,
        }

    else:
        # default widget
        widget_data = builtin_monitoring_widgets.get(
            (widget.get("plugin_name"), widget.get("id"))
        )

        script_data = widget_data["script_data"]
        script_chart = widget_data["script_chart"]

        widget_data = {
            "saved_id": widget_saved_id,
            "id": widget_data["id"],
            "type": widget_data["type"],
            "title": widget_data["title"],
            "interval": widget_data["interval"],
        }

    try:
        loc1 = {"connection": database, "previous_data": widget.get("widget_data")}

        loc2 = {"connection": database, "previous_data": widget.get("widget_data")}

        restricted_globals = dict(__builtins__=safe_builtins)
        restricted_globals["_getiter_"] = iter
        restricted_globals["_getattr_"] = safer_getattr
        restricted_globals["_getitem_"] = default_guarded_getitem
        restricted_globals["__builtins__"]["__import__"] = _hook_import

        byte_code = compile_restricted(script_data, "<inline>", "exec")
        exec(byte_code, restricted_globals, loc1)
        data = loc1["result"]

        if not widget.get("initial") and widget_data["type"] in ["chart", "timeseries"]:
            widget_data["object"] = data
        elif widget_data["type"] == "grid":
            widget_data["data"] = [dict(row) for row in data.get("data", [])]
        elif widget_data["type"] == "graph":
            byte_code = compile_restricted(script_chart, "<inline>", "exec")
            exec(byte_code, restricted_globals, loc2)
            result = loc2["result"]
            result["elements"] = data
            widget_data["object"] = result
        else:
            byte_code = compile_restricted(script_chart, "<inline>", "exec")
            exec(byte_code, restricted_globals, loc2)
            result = loc2["result"]
            result["data"] = data
            widget_data["object"] = result

    except Exception as exc:
        response = {"data": str(exc), "saved_id": widget_data.get("saved_id")}
        return JsonResponse(data=response, status=400)

    return JsonResponse(widget_data)


@user_authenticated
@database_required(check_timeout=False, open_connection=False)
def create_dashboard_monitoring_widget(request, database):
    widget_data = request.data.get("widget_data")

    conn_object = Connection.objects.get(id=database.conn_id)

    try:
        user_widget = MonWidgetsConnections(
            unit=widget_data.get("id"),
            user=request.user,
            connection=conn_object,
            interval=widget_data.get("interval", 5),
            plugin_name=widget_data.get("plugin_name"),
        )
        user_widget.full_clean(exclude=["plugin_name"])
        user_widget.save()
    except Exception as exc:
        return JsonResponse(data={"data": str(exc)}, status=400)

    return JsonResponse(data={"user_widget": model_to_dict(user_widget)}, status=201)


@user_authenticated
@database_required(check_timeout=True, open_connection=True)
def test_monitoring_widget(request, database):
    widget = request.data.get("widget")
    script_chart = widget.get("script_chart")
    script_data = widget.get("script_data")
    widget_type = widget.get("type")
    widget_data = {}
    try:
        loc1 = {"connection": database, "previous_data": None}

        loc2 = {"connection": database, "previous_data": None}

        restricted_globals = dict(__builtins__=safe_builtins)
        restricted_globals["_getiter_"] = iter
        restricted_globals["_getattr_"] = safer_getattr
        restricted_globals["_getitem_"] = default_guarded_getitem
        restricted_globals["__builtins__"]["__import__"] = _hook_import

        byte_code = compile_restricted(script_data, "<inline>", "exec")
        exec(byte_code, restricted_globals, loc1)
        data = loc1["result"]

        if widget_type == "grid":
            widget_data["data"] = [dict(row) for row in data.get("data", [])]
        else:
            byte_code = compile_restricted(script_chart, "<inline>", "exec")
            exec(byte_code, restricted_globals, loc2)
            result = loc2["result"]
            result["data"] = data
            widget_data["object"] = result
    except Exception as exc:
        response = {
            "data": str(exc),
        }
        return JsonResponse(data=response, status=400)
    return JsonResponse(widget_data)
