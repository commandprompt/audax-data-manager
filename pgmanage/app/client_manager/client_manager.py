import threading
import time
from collections import deque
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union

from app.include import OmniDatabase
from app.include.Session import Session
from django.conf import settings


class Client:
    """
    Represents a client object that manages connection sessions and tabs.

    Attributes:
        _to_be_removed (List[Any]): A list of tabs to be removed.
        id (str): The unique identifier of the client.
        polling_lock (threading.Lock): A lock used for synchronization during polling.
        returning_data_lock (threading.Lock): A lock used for synchronization while accessing returning_data.
        returning_data (deque): A list-like container containing data returned by the client.
        _connection_sessions (dict): A dictionary storing connection sessions for the client.
        last_update (datetime.datetime): The timestamp of the client's last update.
        terminated (bool): True when the cleanup thread must close all tabs and remove the client.
    """

    to_be_removed = []

    def __init__(self, client_id: str) -> None:
        self.id = client_id
        self.polling_lock = threading.Lock()
        self.returning_data_lock = threading.Lock()
        self.returning_data = deque()
        self._connection_sessions = {}
        self.last_update = datetime.now()
        self.terminated = False

    @property
    def connection_sessions(self) -> Union[Dict[str, Any], Dict]:
        """
        Property to access the connection sessions of the client.

        Returns:
            Union[Dict[str, Any], Dict]: The connection sessions dictionary.
        """
        return self._connection_sessions

    def release_polling_lock(self) -> None:
        """
        Releases the polling lock if acquired.
        """
        try:
            self.polling_lock.release()
        except RuntimeError:
            pass

    def release_returning_data_lock(self) -> None:
        """
        Releases the returning data lock if acquired.
        """
        try:
            self.returning_data_lock.release()
        except RuntimeError:
            pass

    def get_tab(
        self, workspace_id: str, tab_id: Optional[str] = None
    ) -> Union[Dict[str, Any], None]:
        """Retrieves the tab with the given IDs from the client.

        Args:
            workspace_id (str): The ID of the connection workspace.
            tab_id (Optional[str], None): The ID of the tab. Defaults to None.

        Returns:
            Union[Dict[str, Any], None]: The tab object if found, otherwise None.
        """

        main_tab = self.connection_sessions.get(workspace_id)

        if tab_id is None:
            return main_tab

        if main_tab:
            return main_tab["tab_list"].get(tab_id)
        return None

    def create_tab(
        self,
        workspace_id: str,
        tab: Dict[str, Any],
        tab_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Creates a new tab with the given details and
        adds it to the tab_list of client's connection session.

        Args:
            workspace_id (str): The ID of the connection workspace.
            tab (Dict[str, Any]): The details of the tab.
            tab_id (Optional[str], optional): The ID of the tab. Defaults to None.

        Returns:
            Dict[str, Any]: The created tab object.
        """

        tab = self._create_tab_internal(
            workspace_id=workspace_id,
            tab=tab,
            tab_id=tab_id,
            is_main_tab=False,
        )
        return tab

    def create_main_tab(self, workspace_id: str, tab: Dict[str, Any]) -> Dict[str, Any]:
        """Creates a new main tab with the given details and
        adds it to the client's connection sessions.

        Args:
            workspace_id (str): The ID of the connection workspace.
            tab (Dict[str, Any]): The details of the main tab.

        Returns:
            Dict[str, Any]: The created main tab object.
        """
        tab = self._create_tab_internal(
            workspace_id=workspace_id, tab=tab, is_main_tab=True
        )
        return tab

    def _create_tab_internal(
        self,
        workspace_id: str,
        tab: Dict[str, Any],
        tab_id: Optional[str] = None,
        is_main_tab: bool = False,
    ) -> Dict[str, Any]:
        """Internal method to create a new tab with the given details and
        add it to the client's connection sessions.

        Args:
            workspace_id (str): The ID of the connection workspace.
            tab (Dict[str, Any]): The details of the tab.
            tab_id (Optional[str], optional): The ID of the tab. Defaults to None.
            is_main_tab (bool, optional): Specifies if the tab is a main tab. Defaults to False.

        Returns:
            Dict[str, Any]: The created tab object.
        """

        tab["last_update"] = datetime.now()
        tab["to_be_removed"] = False

        if is_main_tab:
            self._connection_sessions[workspace_id] = tab
        else:
            main_tab = self.get_tab(workspace_id=workspace_id)
            if not main_tab:
                self.create_main_tab(
                    tab={"omnidatabase": None, "type": "connection", "tab_list": {}},
                    workspace_id=workspace_id,
                )

            self._connection_sessions[workspace_id]["tab_list"][tab_id] = tab

        return tab

    def close_tab(self, workspace_id: str, tab_id: Optional[str] = None) -> None:
        """Closes the tab with the given IDs by removing it from the client's connection sessions
        and closing associated connections.

        Args:
            workspace_id (str): The ID of the connection workspace.
            tab_id (Optional[str], optional): The ID of the tab. Defaults to None.

        Returns:
            None
        """

        tab = self.get_tab(tab_id=tab_id, workspace_id=workspace_id)
        if tab is None:
            return

        if tab_id:
            del self._connection_sessions[workspace_id]["tab_list"][tab_id]
        else:
            del self._connection_sessions[workspace_id]

        if tab.get("type") in ["query", "console", "connection", "edit", "schema_edit"]:
            try:
                tab["thread"].stop()
                tab["omnidatabase"].connection.Cancel(False)
            except Exception:
                pass
            try:
                tab["omnidatabase"].connection.Close()
            except Exception:
                pass

        elif tab.get("type") == "debug":
            self._close_debug_tab(tab)

        elif tab.get("type") == "terminal":
            self._close_terminal_tab(tab)

    def _close_debug_tab(self, tab: Dict[str, Any]) -> None:
        """Closes a debug tab by canceling, terminating, and closing the associated connections.

        Args:
            tab (Dict[str, Any]): The debug tab dictionary.

        Returns:
            None
        """
        tab["cancelled"] = True
        try:
            tab["omnidatabase_control"].connection.Cancel(False)
        except Exception:
            pass
        try:
            tab["omnidatabase_control"].connection.Terminate(tab["debug_pid"])
        except Exception:
            pass
        try:
            tab["omnidatabase_control"].connection.Close()
        except Exception:
            pass
        try:
            tab["omnidatabase_debug"].connection.Close()
        except Exception:
            pass

    def _close_terminal_tab(self, tab: Dict[str, Any]) -> None:
        """Closes a terminal tab by stopping the associated thread and closing the connections.

        Args:
            tab (Dict[str, Any]): The terminal tab dictionary.

        Returns:
            None
        """

        if tab["thread"] is not None:
            tab["thread"].stop()
        if tab["terminal_type"] == "local":
            tab["terminal_object"].terminate()
        else:
            tab["terminal_object"].close()
            tab["terminal_ssh_client"].close()

    def _should_update_database(
        self, tab: Dict[str, Any], current_tab_database: str, main_tab_database
    ) -> bool:
        """
        Determines whether the database for a given tab should be updated.

        Args:
            tab (Dict[str, Any]): The tab dictionary representing a client tab.
            current_tab_database (str): The name of the current database associated with the tab.
            main_tab_database: The main tab's database object to compare with.

        Returns:
            bool: True if the database should be updated, False otherwise.
        """
        omni_database = tab["omnidatabase"]
        connection = main_tab_database.connection
        return (
            omni_database is None
            or main_tab_database.db_type != omni_database.db_type
            or connection.host != omni_database.connection.host
            or str(connection.port) != str(omni_database.connection.port)
            or current_tab_database != omni_database.active_service
            or connection.password != omni_database.connection.password
        )

    def _replace_database(
        self,
        tab: Dict[str, Any],
        current_tab_database: str,
        main_tab_database,
        use_lock: bool,
    ) -> None:
        """
        Replaces the database for a given tab with a new database object.

        Args:
            tab (Dict[str, Any]): The tab dictionary representing a client tab.
            current_tab_database (str): The name of the current database associated with the tab.
            main_tab_database: The main tab's database object to use for replacement.
            use_lock (bool): Flag indicating whether to assign a lock to the new database.

        Returns:
            None.
        """
        connection_params = (
            main_tab_database.connection_params
            if hasattr(main_tab_database, "connection_params")
            else None
        )

        database_new = OmniDatabase.Generic.InstantiateDatabase(
            db_type=main_tab_database.db_type,
            server=main_tab_database.connection.host,
            port=str(main_tab_database.connection.port),
            service=current_tab_database,
            user=main_tab_database.active_user,
            password=main_tab_database.connection.password,
            conn_id=main_tab_database.conn_id,
            alias=main_tab_database.alias,
            conn_string=main_tab_database.conn_string,
            parse_conn_string=False,
            connection_params=connection_params,
        )

        # check if database connection is valid
        try:
            database_new.connection.Open()
        except Exception:
            # otherwise revert to main connection
            database_new = main_tab_database

        if use_lock:
            database_new.lock = threading.Lock()

        if tab["omnidatabase"]:
            self.to_be_removed.append(tab["omnidatabase"])

        tab["omnidatabase"] = database_new

    def get_database(
        self,
        session: Session,
        tab: Dict[str, Any],
        workspace_id: str,
        database_index: int,
        current_database: str = None,
        attempt_to_open_connection: bool = False,
        use_lock: bool = False,
    ):
        """Retrieves the database for the specified session and tab,
        and performs necessary updates if the database object has changed.

        Args:
            session (Session): The session object.
            tab (Dict[str, Any]): The tab object.
            workspace_id (str): The ID of the connection workspace.
            database_index (int): The index of the database.
            current_database (str, optional): The current database. Defaults to None.
            attempt_to_open_connection (bool, optional): Specifies whether
            to attempt opening the connection if not already open. Defaults to False.
            use_lock (bool, optional): Specifies whether
            to use a lock for thread safety. Defaults to False.

        Returns:
            The tab's database object.
        """
        main_tab_database = session.databases[database_index]["database"]
        current_tab_database = current_database or session.tabs_databases.get(
            workspace_id
        )

        # Updating time
        tab["last_update"] = datetime.now()

        if self._should_update_database(
            tab=tab,
            current_tab_database=current_tab_database,
            main_tab_database=main_tab_database,
        ):
            self._replace_database(
                tab=tab,
                current_tab_database=current_tab_database,
                main_tab_database=main_tab_database,
                use_lock=use_lock,
            )

        # Try to open connection if not opened yet
        if attempt_to_open_connection and (
            not tab["omnidatabase"].connection.con
            or tab["omnidatabase"].connection.GetConStatus() == 0
        ):
            tab["omnidatabase"].connection.Open()

        return tab["omnidatabase"]

    def get_tab_database(
        self,
        session: Session,
        workspace_id: str,
        database_index: int,
        tab_id: str = None,
        database_name: str = None,
        attempt_to_open_connection: bool = False,
    ):
        """Retrieves the database for the specified session, connection workspace and tab.

        Args:
            session (Session): The session object.
            workspace_id (str): The ID of the connection workspace.
            database_index (int): The index of the database.
            tab_id (str, optional): The ID of the tab. If provided, will retrieve the specified tab.
            database_name (str, optional): The name of the database to be used.
            attempt_to_open_connection (bool, optional): Specifies whether to attempt opening
                the connection if not already open. Defaults to False.

        Returns:
            The database object associated with the specified session and tab.
        """

        if tab_id and workspace_id:
            tab = self.get_tab(workspace_id=workspace_id, tab_id=tab_id)
            if tab is None:
                tab = self.create_tab(
                    workspace_id=workspace_id,
                    tab_id=tab_id,
                    tab={
                        "thread": None,
                        "omnidatabase": None,
                        "inserted_tab": False,
                        "type": "query",
                    },
                )
        else:
            tab = self.get_tab(workspace_id=workspace_id)
            if tab is None:
                tab = self.create_main_tab(
                    tab={"omnidatabase": None, "type": "connection", "tab_list": {}},
                    workspace_id=workspace_id,
                )

        return self.get_database(
            session=session,
            tab=tab,
            workspace_id=workspace_id,
            database_index=database_index,
            current_database=database_name,
            attempt_to_open_connection=attempt_to_open_connection,
            use_lock=True,
        )


class ClientManager:
    """
    The ClientManager class manages the clients.

    Attributes:
        _clients (Dict[str, Client]): A dictionary of clients, where the client ID is the key.
        _instance (ClientManager): The singleton instance of the ClientManager class.
        _lock (threading.Lock): A lock for thread safety.
    """

    _clients = {}
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if not cls._instance:
                cls._instance = super().__new__(cls)

        return cls._instance

    @property
    def clients(self) -> Union[Dict[str, Client], Dict]:
        """
        Get the dictionary of clients.

        Returns:
            Union[Dict[str, Any], Dict]: The dictionary of clients.
        """

        return self._clients

    def get_client(self, client_id: str) -> Union[Client, None]:
        """
        Get the client with the specified client ID.

        Args:
            client_id (str): The ID of the client.

        Returns:
            Union[Dict[str, Client], None]: The client object if found, None otherwise.
        """
        client = self._clients.get(client_id)
        return client

    def create_client(self, client_id: str) -> Client:
        """
        Create a new client with the specified client ID.

        Args:
            client_id (str): The ID of the client.

        Returns:
            Dict[str, Client]: The newly created client object.
        """

        client = Client(client_id=client_id)

        self._clients[client_id] = client

        return client

    def get_or_create_client(self, client_id: str) -> Client:
        """Retrieves the client with the given client_id. If the client does not exist,
        creates a new client with the given client_id.

        Args:
            client_id (str): The ID of the client.

        Returns:
            Dict[str, Client]: The client object.
        """

        client = self.get_client(client_id=client_id)

        if client is None:
            client = self.create_client(client_id=client_id)

        return client

    def clear_client(self, client_id: str) -> None:
        """Clears the client with the given client_id by removing
        all associated connection sessions and releasing locks.

        Args:
            client_id (str): The ID of the client.

        Returns:
            None
        """

        client = self.get_or_create_client(client_id=client_id)

        for conn_tab in client.connection_sessions.values():
            for tab in conn_tab.get("tab_list", {}).values():
                tab["to_be_removed"] = True
            conn_tab["to_be_removed"] = True

        client.release_polling_lock()

        client.release_returning_data_lock()

    def remove_client(self, client_id: str) -> None:
        """Removes the client with the specified client_id.

        Args:
            client_id (str): The ID of the client to be removed.

        Returns:
            None
        """
        self.clients.pop(client_id, None)

    def terminate_client(self, client_id: str) -> None:
        """Ends the client with the specified client_id.

        The method flags the client and its tabs, and releases the locks.
        The cleanup thread then closes all tabs and removes the client.
        The method does not wait for the cleanup thread.

        Args:
            client_id (str): The ID of the client to be terminated.

        Returns:
            None
        """
        client = self.get_client(client_id=client_id)
        if client is None:
            return

        self.clear_client(client_id=client_id)
        client.terminated = True


client_manager = ClientManager()


def cleanup_thread():
    """Thread function that continuously cleans up inactive client connections and tabs.

    The function runs in an infinite loop and periodically checks
    for inactive client connections and tabs. If a client or tab has exceeded
    the timeout period or flagged for removal,
    it will be closed and removed from the client manager.

    Returns:
        None
    """
    while True:
        while Client.to_be_removed:
            conn = Client.to_be_removed.pop(0)
            conn.connection.Close()

        for client_id in list(client_manager.clients):
            client = client_manager.get_client(client_id=client_id)
            client_timeout_reached = datetime.now() > client.last_update + timedelta(
                0, settings.CLIENT_TIMEOUT
            )
            if client.terminated:
                client_timeout_reached = True

            for workspace_id in list(client.connection_sessions):
                for tab_id in list(
                    client.connection_sessions[workspace_id].get("tab_list", [])
                ):
                    tab = client.get_tab(workspace_id=workspace_id, tab_id=tab_id)

                    if is_tab_expired(tab, client_timeout_reached):
                        client.close_tab(tab_id=tab_id, workspace_id=workspace_id)

                if not client.connection_sessions[workspace_id].get("tab_list"):
                    tab = client.get_tab(workspace_id=workspace_id)
                    if is_tab_expired(tab, client_timeout_reached):
                        client.close_tab(workspace_id=workspace_id)

            if client_timeout_reached:
                client_manager.remove_client(client_id=client_id)
        time.sleep(30)


def is_tab_expired(tab: Dict[str, Any], client_timeout_reached: bool) -> bool:
    """Check if a tab has expired based on the timeout and removal flags.

    Args:
        tab: Dictionary representing a tab object.
        client_timeout_reached: Boolean indicating if the client timeout has been reached.

    Returns:
        bool: True if the tab has expired, False otherwise.
    """
    tab_timeout_reached = datetime.now() > tab["last_update"] + timedelta(0, 3600)
    return (
        client_timeout_reached or tab_timeout_reached or tab.get("to_be_removed", False)
    )


t = threading.Thread(name="cleanup_thread", target=cleanup_thread)
t.setDaemon(True)
t.start()
