import threading
import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from app.client_manager import client_manager
from app.client_manager.client_manager import cleanup_thread
from django.conf import settings
from django.test import SimpleTestCase


class StopCleanup(Exception):
    """Raised by the patched sleep. It ends the endless loop of the cleanup thread."""


def run_one_cleanup_pass():
    test_thread = threading.current_thread()
    real_sleep = time.sleep

    def fake_sleep(seconds):
        # The patch is global. Other threads must keep the real sleep.
        if threading.current_thread() is test_thread:
            raise StopCleanup
        real_sleep(seconds)

    with patch("app.client_manager.client_manager.time.sleep", side_effect=fake_sleep):
        try:
            cleanup_thread()
        except StopCleanup:
            pass


class ClientManagerTestCase(SimpleTestCase):
    def setUp(self):
        client_manager.clients.clear()
        self.addCleanup(client_manager.clients.clear)

    def add_query_tab(self, client):
        """Add a query tab with a mocked database. Return the mocked database."""
        omnidatabase = MagicMock()
        client.create_tab(
            workspace_id="workspace",
            tab_id="tab",
            tab={"thread": MagicMock(), "omnidatabase": omnidatabase, "type": "query"},
        )
        return omnidatabase


class TerminateClientTests(ClientManagerTestCase):
    def test_terminate_client_flags_the_client_and_its_tabs(self):
        client = client_manager.create_client("client-1")
        self.add_query_tab(client)

        client_manager.terminate_client("client-1")

        self.assertTrue(client.terminated)
        self.assertTrue(client.get_tab("workspace", "tab")["to_be_removed"])
        self.assertTrue(client.get_tab("workspace")["to_be_removed"])

    def test_terminate_client_releases_the_polling_lock(self):
        client = client_manager.create_client("client-1")
        client.polling_lock.acquire()

        client_manager.terminate_client("client-1")

        # A long polling request that waits for the lock can return now.
        self.assertTrue(client.polling_lock.acquire(blocking=False))
        client.polling_lock.release()

    def test_terminate_client_does_not_create_a_client(self):
        client_manager.terminate_client("unknown")

        self.assertIsNone(client_manager.get_client("unknown"))


class CleanupThreadTests(ClientManagerTestCase):
    def test_cleanup_closes_the_tabs_of_a_terminated_client_and_removes_it(self):
        client = client_manager.create_client("client-1")
        omnidatabase = self.add_query_tab(client)
        client_manager.terminate_client("client-1")

        run_one_cleanup_pass()

        omnidatabase.connection.Close.assert_called_once()
        self.assertIsNone(client_manager.get_client("client-1"))

    def test_cleanup_removes_a_client_that_reached_the_timeout(self):
        client = client_manager.create_client("client-1")
        omnidatabase = self.add_query_tab(client)
        client.last_update = datetime.now() - timedelta(
            seconds=settings.CLIENT_TIMEOUT + 1
        )

        run_one_cleanup_pass()

        omnidatabase.connection.Close.assert_called_once()
        self.assertIsNone(client_manager.get_client("client-1"))

    def test_cleanup_keeps_a_client_that_did_not_reach_the_timeout(self):
        client = client_manager.create_client("client-1")
        omnidatabase = self.add_query_tab(client)

        run_one_cleanup_pass()

        omnidatabase.connection.Close.assert_not_called()
        self.assertIs(client_manager.get_client("client-1"), client)
