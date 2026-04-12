"""Main screen for the Tuim TUI application."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import ContentSwitcher, Input

from tuim.config import load_connections, save_connections
from tuim.models import Connection, ConnectionStatus, Protocol
from tuim.screens.add_connection import AddConnectionScreen
from tuim.screens.delete_confirm import DeleteConfirmScreen
from tuim.screens.help_screen import HelpScreen
from tuim.services.health_checker import HealthChecker
from tuim.services.session_manager import SessionManager
from tuim.widgets.connection_table import ConnectionTable
from tuim.widgets.header_bar import HeaderBar
from tuim.widgets.status_bar import StatusBar
from tuim.widgets.terminal_view import TerminalView


class MainScreen(Screen):
    """Primary screen with connection list and terminal view."""

    BINDINGS = [
        Binding("a", "add_connection", "Add", show=False),
        Binding("d", "delete_connection", "Delete", show=False),
        Binding("e", "edit_connection", "Edit", show=False),
        Binding("question_mark", "show_help", "Help", show=False),
        Binding("enter", "connect", "Connect", show=False),
        Binding("escape", "disconnect", "Back", show=False),
        Binding("q", "quit_app", "Quit", show=False),
    ]

    def __init__(
        self,
        connections=None,  # type: Optional[List[Connection]]
        settings=None,  # type: Optional[dict]
        config_path=None,  # type: Optional[str]
    ):
        super().__init__()
        self.connections = connections or []  # type: List[Connection]
        self.settings = settings or {}
        self.config_path = config_path
        self.session_manager = SessionManager()
        self.health_checker = None  # type: Optional[HealthChecker]
        self._current_view = "list"  # "list" or "terminal"

    def compose(self):
        # type: () -> ComposeResult
        yield HeaderBar()
        with ContentSwitcher(initial="list-view", id="content-switcher"):
            with Vertical(id="list-view"):
                yield ConnectionTable()
            with Vertical(id="terminal-container"):
                yield TerminalView()
        yield StatusBar()

    def on_mount(self):
        # type: () -> None
        self._refresh_table()
        self._start_health_checker()

    def _refresh_table(self):
        # type: () -> None
        """Refresh the connection table with current data."""
        try:
            table = self.query_one(ConnectionTable)
            table.refresh_data(self.connections)
        except Exception:
            pass

    def _start_health_checker(self):
        # type: () -> None
        """Start the background health checker."""
        interval = self.settings.get("health_check_interval", 30)
        self.health_checker = HealthChecker(
            connections=self.connections,
            interval=interval,
            on_update=self._on_health_update,
        )
        self.health_checker.start()

    def _on_health_update(self, name, status):
        # type: (str, ConnectionStatus) -> None
        """Handle health check update for a connection."""
        for conn in self.connections:
            if conn.name == name:
                conn.status = status
                break
        # Schedule UI refresh on the main thread
        self.call_from_thread(self._refresh_table)

    def _save_connections(self):
        # type: () -> None
        """Persist connections to YAML."""
        save_connections(self.connections, self.settings, self.config_path)

    def _find_connection(self, name):
        # type: (str) -> Optional[Connection]
        """Find a connection by name."""
        for conn in self.connections:
            if conn.name == name:
                return conn
        return None

    def _switch_to_view(self, view):
        # type: (str) -> None
        """Switch between 'list' and 'terminal' views."""
        self._current_view = view
        switcher = self.query_one(ContentSwitcher)
        status_bar = self.query_one(StatusBar)

        if view == "list":
            switcher.current = "list-view"
            status_bar.update_mode("List Mode")
            status_bar.stop_timer()
        else:
            switcher.current = "terminal-container"
            status_bar.update_mode("Terminal Mode")

    # ---- Actions ----

    def action_add_connection(self):
        # type: () -> None
        if self._current_view != "list":
            return

        def on_result(result):
            # type: (Optional[Connection]) -> None
            if result is not None:
                self.connections.append(result)
                self._save_connections()
                self._refresh_table()
                if self.health_checker:
                    self.health_checker.update_connections(self.connections)

        self.app.push_screen(AddConnectionScreen(), on_result)

    def action_edit_connection(self):
        # type: () -> None
        if self._current_view != "list":
            return

        table = self.query_one(ConnectionTable)
        name = table.get_selected_connection_name()
        if name is None:
            return

        conn = self._find_connection(name)
        if conn is None:
            return

        def on_result(result):
            # type: (Optional[Connection]) -> None
            if result is not None:
                # Replace the old connection
                for i, c in enumerate(self.connections):
                    if c.name == conn.name:
                        self.connections[i] = result
                        break
                self._save_connections()
                self._refresh_table()

        self.app.push_screen(AddConnectionScreen(connection=conn), on_result)

    def action_delete_connection(self):
        # type: () -> None
        if self._current_view != "list":
            return

        table = self.query_one(ConnectionTable)
        name = table.get_selected_connection_name()
        if name is None:
            return

        def on_result(confirmed):
            # type: (bool) -> None
            if confirmed:
                self.connections = [c for c in self.connections if c.name != name]
                self._save_connections()
                self._refresh_table()
                if self.health_checker:
                    self.health_checker.update_connections(self.connections)

        self.app.push_screen(DeleteConfirmScreen(name), on_result)

    def action_show_help(self):
        # type: () -> None
        self.app.push_screen(HelpScreen())

    async def action_connect(self):
        # type: () -> None
        if self._current_view != "list":
            return

        table = self.query_one(ConnectionTable)
        name = table.get_selected_connection_name()
        if name is None:
            return

        conn = self._find_connection(name)
        if conn is None:
            return

        terminal = self.query_one(TerminalView)
        terminal.clear_output()

        # Determine username for display
        username = ""
        if conn.protocol == Protocol.SSH and conn.ssh_config:
            username = conn.ssh_config.username
        elif conn.protocol == Protocol.TELNET and conn.telnet_config:
            username = conn.telnet_config.username
        elif conn.protocol == Protocol.RDP and conn.rdp_config:
            username = conn.rdp_config.username

        terminal.set_host_info(conn.host or conn.name, conn.protocol.value, username)

        # Switch to terminal view
        self._switch_to_view("terminal")

        # Update status bar
        status_bar = self.query_one(StatusBar)
        status_bar.update_connection(conn.name, conn.protocol.value.upper(), conn.host, conn.port)
        status_bar.start_timer()

        # Connect
        terminal.write_line("Connecting to {} ({})...".format(conn.name, conn.protocol.value.upper()))

        try:
            await self.session_manager.connect(
                conn,
                on_output=self._on_session_output,
                on_disconnect=self._on_session_disconnect,
            )
            # Update last_connected
            conn.last_connected = datetime.now()
            self._save_connections()
        except Exception as exc:
            terminal.write_line("Connection failed: {}".format(exc))

        # For non-interactive protocols, show a message
        handler = self.session_manager.current_handler
        if handler is not None and not handler.is_interactive:
            terminal.write_line("Connection launched via external client.")
            terminal.write_line("Press Esc to return to the connection list.")

    async def action_disconnect(self):
        # type: () -> None
        if self._current_view != "terminal":
            return

        terminal = self.query_one(TerminalView)
        terminal.write_line("\nDisconnecting...")

        await self.session_manager.disconnect()

        status_bar = self.query_one(StatusBar)
        status_bar.stop_timer()
        status_bar.update_connection("", "", "", 0)

        self._switch_to_view("list")
        self._refresh_table()

    def action_quit_app(self):
        # type: () -> None
        self.app.exit()

    # ---- Session callbacks ----

    def _on_session_output(self, data):
        # type: (str) -> None
        """Called when the protocol handler produces output."""
        try:
            terminal = self.query_one(TerminalView)
            self.call_from_thread(terminal.write_output, data)
        except Exception:
            pass

    def _on_session_disconnect(self):
        # type: () -> None
        """Called when the remote session disconnects unexpectedly."""
        try:
            terminal = self.query_one(TerminalView)
            self.call_from_thread(terminal.write_line, "\n[Connection closed]")
        except Exception:
            pass

    # ---- Terminal input ----

    async def on_input_submitted(self, event):
        # type: (Input.Submitted) -> None
        """Handle Enter in the terminal input."""
        if event.input.id != "terminal-input":
            return
        if self._current_view != "terminal":
            return

        data = event.value
        event.input.value = ""

        if self.session_manager.is_connected:
            await self.session_manager.send_input(data)

    # ---- Button handlers ----

    async def on_button_pressed(self, event):
        """Handle button presses in the terminal view."""
        if event.button.id == "btn-reconnect":
            # Disconnect and reconnect
            conn = self.session_manager.current_connection
            if conn:
                await self.session_manager.disconnect()
                terminal = self.query_one(TerminalView)
                terminal.clear_output()
                terminal.write_line("Reconnecting to {}...".format(conn.name))
                try:
                    await self.session_manager.connect(
                        conn,
                        on_output=self._on_session_output,
                        on_disconnect=self._on_session_disconnect,
                    )
                except Exception as exc:
                    terminal.write_line("Reconnection failed: {}".format(exc))
        elif event.button.id == "btn-disconnect":
            await self.action_disconnect()
