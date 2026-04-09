"""Trelay TUI Application."""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import ContentSwitcher, DataTable

from trelay.config import load_connections, save_connections, get_config_path
from trelay.widgets.header_bar import HeaderBar
from trelay.widgets.connection_table import ConnectionTable
from trelay.widgets.terminal_view import TerminalView
from trelay.widgets.k8s_resource_view import K8sResourceView
from trelay.widgets.status_bar import StatusBar
from trelay.widgets.command_bar import CommandBar

# Key-to-terminal escape sequence mapping
_KEY_MAP = {
    "enter": "\r",
    "tab": "\t",
    "backspace": "\x7f",
    "delete": "\x1b[3~",
    "up": "\x1b[A",
    "down": "\x1b[B",
    "right": "\x1b[C",
    "left": "\x1b[D",
    "home": "\x1b[H",
    "end": "\x1b[F",
    "pageup": "\x1b[5~",
    "pagedown": "\x1b[6~",
    "insert": "\x1b[2~",
    "f1": "\x1bOP",
    "f2": "\x1bOQ",
    "f3": "\x1bOR",
    "f4": "\x1bOS",
    "f5": "\x1b[15~",
    "f6": "\x1b[17~",
    "f7": "\x1b[18~",
    "f8": "\x1b[19~",
    "f9": "\x1b[20~",
    "f10": "\x1b[21~",
    "f11": "\x1b[23~",
    "f12": "\x1b[24~",
}


class TrelayApp(App):
    """Trelay - TUI Remote Connection Manager."""

    TITLE = "Trelay"
    SUB_TITLE = "Remote Connection Manager"

    CSS_PATH = "styles/theme.tcss"

    BINDINGS = [
        Binding("a", "add_connection", "Add", show=False),
        Binding("d", "delete_connection", "Delete", show=False),
        Binding("e", "edit_connection", "Edit", show=False),
    ]

    def __init__(self, config_path=None):
        # type: (Optional[str]) -> None
        super().__init__()
        self.config_path = config_path
        self.connections = []
        self.settings = {}
        self._current_view = "list"
        self._k8s_return = False
        self._k8s_connection = None  # type: Optional[object]

        # Lazy imports to avoid circular deps
        from trelay.services.session_manager import SessionManager
        from trelay.services.health_checker import HealthChecker
        self.session_manager = SessionManager()
        self.health_checker = None  # type: Optional[HealthChecker]

    def compose(self):
        # type: () -> ComposeResult
        yield HeaderBar()
        yield CommandBar()
        with ContentSwitcher(initial="list-view", id="content-switcher"):
            yield ConnectionTable(id="list-view")
            yield K8sResourceView(id="k8s-view")
            yield TerminalView(id="terminal-container")
        yield StatusBar()

    def on_mount(self):
        # type: () -> None
        self._ensure_config()
        self.connections, self.settings = load_connections(self.config_path)
        self._refresh_table()
        # Hide command bar on startup
        cmd_bar = self.query_one(CommandBar)
        cmd_bar.add_class("hidden")
        cmd_bar.can_focus = False
        # Focus the connection table
        try:
            table = self.query_one(ConnectionTable)
            dt = table.query_one(DataTable)
            dt.focus()
        except Exception:
            pass
        # Delay health checker start so it doesn't block initial render
        self.set_timer(2.0, self._start_health_checker)

    def check_action(self, action, parameters):
        """Disable app-level bindings in terminal, k8s, or command mode."""
        # Only block app-level bindings (add/edit/delete), not widget bindings
        app_actions = {"add_connection", "delete_connection", "edit_connection"}
        if action not in app_actions:
            return True
        if self._current_view in ("terminal", "k8s"):
            return False
        cmd_bar = self.query_one(CommandBar)
        if cmd_bar.is_active:
            return False
        return True

    def _ensure_config(self):
        # type: () -> None
        """If no config file exists, copy the example config."""
        path = get_config_path(self.config_path)
        if not os.path.exists(path):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            example = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "..", "..", "config", "connections.example.yaml"
            )
            if os.path.exists(example):
                shutil.copy2(example, path)
            else:
                save_connections([], self.settings, self.config_path)

    # ---- Table / Health ----

    def _refresh_table(self):
        # type: () -> None
        try:
            table = self.query_one(ConnectionTable)
            table.refresh_data(self.connections)
        except Exception:
            pass

    def _start_health_checker(self):
        # type: () -> None
        from trelay.services.health_checker import HealthChecker
        interval = self.settings.get("health_check_interval", 30)
        self.health_checker = HealthChecker(
            connections=self.connections,
            interval=interval,
            on_update=self._on_health_update,
        )
        # Use Textual's set_interval to drive health checks
        self._health_timer = self.set_interval(interval, self._run_health_check)
        # Run first check immediately
        self.run_worker(self._do_health_check, exclusive=False)

    async def _do_health_check(self):
        # type: () -> None
        if self.health_checker is not None:
            await self.health_checker.check_all()

    def _run_health_check(self):
        # type: () -> None
        self.run_worker(self._do_health_check, exclusive=False)

    def _on_health_update(self, name, status):
        # type: (str, object) -> None
        for conn in self.connections:
            if conn.name == name:
                conn.status = status
                break
        self._refresh_table()

    def _save_connections(self):
        # type: () -> None
        save_connections(self.connections, self.settings, self.config_path)

    def _find_connection(self, name):
        # type: (str) -> object
        for conn in self.connections:
            if conn.name == name:
                return conn
        return None

    def _switch_to_view(self, view):
        # type: (str) -> None
        self._current_view = view
        switcher = self.query_one(ContentSwitcher)
        status_bar = self.query_one(StatusBar)
        header_bar = self.query_one(HeaderBar)
        if view == "list":
            switcher.current = "list-view"
            status_bar.update_mode("列表模式")
            status_bar.stop_timer()
            header_bar.set_list_mode()
            # Restore focus to DataTable
            try:
                table = self.query_one(ConnectionTable)
                dt = table.query_one(DataTable)
                self.set_timer(0.1, dt.focus)
            except Exception:
                pass
        elif view == "k8s":
            switcher.current = "k8s-view"
            status_bar.update_mode("K8s 资源浏览")
            status_bar.stop_timer()
            header_bar.set_k8s_mode()
            try:
                k8s_view = self.query_one(K8sResourceView)
                self.set_timer(0.1, k8s_view.focus_table)
            except Exception:
                pass
        else:
            switcher.current = "terminal-container"
            status_bar.update_mode("终端模式")

    # ---- Key handling for terminal mode ----

    def _key_to_terminal(self, event):
        """Map a Textual key event to terminal escape data. Returns None to skip."""
        key = event.key
        char = event.character

        # Ctrl+D → send to terminal (EOF); SSH shell will exit on its own
        # and trigger _on_session_disconnect automatically

        # Escape → send ESC to terminal (needed for vim etc.)
        if key == "escape":
            return "\x1b"

        # Ctrl+key combinations → control characters
        if key.startswith("ctrl+") and len(key) == 6:
            letter = key[-1]
            if 'a' <= letter <= 'z':
                return chr(ord(letter) - ord('a') + 1)

        # Known special keys
        if key in _KEY_MAP:
            return _KEY_MAP[key]

        # Regular printable character
        if char and len(char) >= 1 and ord(char[0]) >= 32:
            return char

        # Space
        if key == "space":
            return " "

        return None

    async def on_key(self, event):
        """Handle global key events."""
        # In terminal mode, forward keystrokes to SSH
        if self._current_view == "terminal":
            if not self.session_manager.is_connected:
                # Session ended — any key returns immediately
                if self._k8s_return:
                    event.prevent_default()
                    event.stop()
                    self._auto_return_to_list()
                return
            data = self._key_to_terminal(event)
            if data is not None:
                event.prevent_default()
                event.stop()
                await self.session_manager.send_input(data)
            return

        # In K8s resource browser mode
        if self._current_view == "k8s":
            cmd_bar = self.query_one(CommandBar)
            if cmd_bar.is_active:
                return
            key = event.key
            char = event.character
            if char in (":", "/"):
                event.prevent_default()
                event.stop()
                cmd_bar.activate(char)
                return
            # j/k/up/down — cursor navigation
            if char in ("j", "k") or key in ("up", "down"):
                event.prevent_default()
                event.stop()
                try:
                    k8s_view = self.query_one(K8sResourceView)
                    dt = k8s_view.query_one("#k8s-data-table", DataTable)
                    if char == "j" or key == "down":
                        dt.action_cursor_down()
                    else:
                        dt.action_cursor_up()
                except Exception:
                    pass
                return
            # Let other keys (Enter, etc.) propagate to DataTable
            return

        # In list mode, intercept : / ? to activate command bar
        if self._current_view == "list":
            cmd_bar = self.query_one(CommandBar)
            if cmd_bar.is_active:
                return  # CommandBar handles its own keys
            key = event.key
            char = event.character
            if char in (":", "/", "?"):
                event.prevent_default()
                event.stop()
                cmd_bar.activate(char)
                return
            # j/k/up/down vim-style navigation
            if char in ("j", "k") or key in ("up", "down"):
                event.prevent_default()
                event.stop()
                try:
                    table = self.query_one(ConnectionTable)
                    dt = table.query_one(DataTable)
                    if char == "j" or key == "down":
                        dt.action_cursor_down()
                    else:
                        dt.action_cursor_up()
                except Exception:
                    pass
                return

    # ---- Actions ----

    def action_add_connection(self):
        # type: () -> None
        if self._current_view != "list":
            return
        from trelay.screens.add_connection import AddConnectionScreen

        def on_result(result):
            if result is not None:
                self.connections.append(result)
                self._save_connections()
                self._refresh_table()
                if self.health_checker:
                    self.health_checker.update_connections(self.connections)

        self.push_screen(AddConnectionScreen(), on_result)

    def action_edit_connection(self):
        # type: () -> None
        if self._current_view != "list":
            return
        from trelay.screens.add_connection import AddConnectionScreen

        table = self.query_one(ConnectionTable)
        name = table.get_selected_connection_name()
        if not name:
            return
        conn = self._find_connection(name)
        if not conn:
            return

        def on_result(result):
            if result is not None:
                for i, c in enumerate(self.connections):
                    if c.name == conn.name:
                        self.connections[i] = result
                        break
                self._save_connections()
                self._refresh_table()

        self.push_screen(AddConnectionScreen(connection=conn), on_result)

    def action_delete_connection(self):
        # type: () -> None
        if self._current_view != "list":
            return
        from trelay.screens.delete_confirm import DeleteConfirmScreen

        table = self.query_one(ConnectionTable)
        name = table.get_selected_connection_name()
        if not name:
            return

        def on_result(confirmed):
            if confirmed:
                self.connections = [c for c in self.connections if c.name != name]
                self._save_connections()
                self._refresh_table()
                if self.health_checker:
                    self.health_checker.update_connections(self.connections)

        self.push_screen(DeleteConfirmScreen(name), on_result)

    async def action_do_connect(self):
        # type: () -> None
        if self._current_view != "list":
            return
        from trelay.models import Protocol
        from datetime import datetime

        table = self.query_one(ConnectionTable)
        name = table.get_selected_connection_name()
        if not name:
            return
        conn = self._find_connection(name)
        if not conn:
            return

        # K8s without pod → enter resource browser
        if conn.protocol == Protocol.K8S:
            k8s_cfg = conn.k8s_config
            if k8s_cfg and not k8s_cfg.pod:
                await self._enter_k8s_browser(conn)
                return

        terminal = self.query_one(TerminalView)
        terminal.clear_output()
        self._switch_to_view("terminal")

        # Register resize callback so SSH PTY follows terminal size
        terminal.set_on_resize(self._on_terminal_resize)

        status_bar = self.query_one(StatusBar)
        status_bar.update_connection(conn.name, conn.protocol.value.upper(), conn.host, conn.port)
        status_bar.start_timer()

        terminal.write_line("Connecting to {} ({})...".format(conn.name, conn.protocol.value.upper()))

        # Pass actual terminal dimensions to the protocol handler
        term_size = terminal.get_terminal_size()

        try:
            await self.session_manager.connect(
                conn,
                on_output=self._on_session_output,
                on_disconnect=self._on_session_disconnect,
                term_size=term_size,
            )
            conn.last_connected = datetime.now()
            self._save_connections()
            # Re-sync terminal size after connection is up (layout may
            # have settled to a different size while we were connecting)
            self.set_timer(0.3, self._sync_terminal_size)
        except Exception as exc:
            terminal.write_line("Connection failed: {}".format(exc))

        handler = self.session_manager.current_handler
        if handler is not None and not handler.is_interactive:
            terminal.write_line("Connection launched via external client.")
            terminal.write_line("Will return to list when session ends.")

    async def action_do_disconnect(self):
        # type: () -> None
        if self._current_view != "terminal":
            return
        terminal = self.query_one(TerminalView)
        terminal.set_on_resize(None)
        terminal.write_line("\nDisconnecting...")
        await self.session_manager.disconnect()
        self._return_to_list()

    def _return_to_list(self):
        # type: () -> None
        """Switch back to list view and clean up status bar."""
        status_bar = self.query_one(StatusBar)
        status_bar.stop_timer()
        status_bar.update_connection("", "", "", 0)
        self._switch_to_view("list")
        self._refresh_table()

    # ---- K8s resource browser ----

    async def _enter_k8s_browser(self, conn):
        """Enter K8s resource browser mode for a connection without pod."""
        self._k8s_connection = conn
        k8s_cfg = conn.k8s_config
        k8s_view = self.query_one(K8sResourceView)
        k8s_view.set_k8s_context(
            kubeconfig=k8s_cfg.kubeconfig if k8s_cfg else "",
            context=k8s_cfg.context if k8s_cfg else "",
            namespace=k8s_cfg.namespace if k8s_cfg else "default",
        )
        self._switch_to_view("k8s")

        status_bar = self.query_one(StatusBar)
        status_bar.update_connection(conn.name, "K8S", "", 0)

        await k8s_view.load_resources("pods")

    async def _execute_k8s_command(self, cmd):
        # type: (str) -> None
        """Execute a : command in K8s resource browser mode."""
        from trelay.services.k8s_service import RESOURCE_ALIASES

        if cmd == "q" or cmd == "quit":
            self._k8s_connection = None
            self._return_to_list()
            return

        if cmd == "q!":
            self.exit()
            return

        k8s_view = self.query_one(K8sResourceView)

        # :ns (no args) → show namespaces
        # :ns <name> → switch namespace
        if cmd == "ns":
            await k8s_view.load_resources("namespaces")
            return
        if cmd.startswith("ns "):
            ns_name = cmd[3:].strip()
            if ns_name:
                k8s_view.set_namespace(ns_name)
                await k8s_view.load_resources("pods")
            return

        # Resource type alias
        if cmd in RESOURCE_ALIASES:
            await k8s_view.load_resources(cmd)
            return

    async def _k8s_exec_pod(self):
        # type: () -> None
        """Handle Enter on a row in K8s resource browser."""
        import copy
        from trelay.models import K8sConfig

        k8s_view = self.query_one(K8sResourceView)
        resource_type = k8s_view.get_current_resource_type()
        name = k8s_view.get_selected_resource_name()
        if not name:
            return

        if resource_type == "namespaces":
            # Enter on a namespace → switch to that namespace, show pods
            k8s_view.set_namespace(name)
            await k8s_view.load_resources("pods")
            return

        if resource_type == "pods":
            # Enter on a pod → exec into it via terminal
            conn = self._k8s_connection
            if conn is None:
                return
            exec_conn = copy.deepcopy(conn)
            if exec_conn.k8s_config is None:
                exec_conn.k8s_config = K8sConfig()
            exec_conn.k8s_config.pod = name
            exec_conn.k8s_config.namespace = k8s_view.get_namespace()

            self._k8s_return = True
            terminal = self.query_one(TerminalView)
            terminal.clear_output()
            self._switch_to_view("terminal")

            terminal.set_on_resize(self._on_terminal_resize)

            status_bar = self.query_one(StatusBar)
            ns = exec_conn.k8s_config.namespace
            status_bar.update_connection(
                "{}:{}".format(ns, name), "K8S", "", 0,
            )
            status_bar.start_timer()

            terminal.write_line("Exec into pod {}...".format(name))
            term_size = terminal.get_terminal_size()

            try:
                await self.session_manager.connect(
                    exec_conn,
                    on_output=self._on_session_output,
                    on_disconnect=self._on_session_disconnect,
                    term_size=term_size,
                )
                self.set_timer(0.3, self._sync_terminal_size)
            except Exception as exc:
                terminal.write_line("Exec failed: {}".format(exc))
            return

        # Other resource types: no action on Enter

    def action_quit_app(self):
        # type: () -> None
        self.exit()

    # ---- Command bar events ----

    def on_command_bar_submitted(self, event):
        # type: (CommandBar.Submitted) -> None
        """Handle command bar submission."""
        cmd_bar = self.query_one(CommandBar)
        prefix = event.prefix
        value = event.value.strip()

        if prefix == ":":
            cmd_bar.deactivate()
            if self._current_view == "k8s":
                self.run_worker(self._execute_k8s_command(value), exclusive=False)
            else:
                self._execute_command(value)
        elif prefix in ("/", "?"):
            # Enter confirms the search and closes the bar
            cmd_bar.deactivate()
            # Keep the filter active — table stays filtered
        self._restore_focus()

    def on_command_bar_changed(self, event):
        # type: (CommandBar.Changed) -> None
        """Handle real-time search as user types."""
        if event.prefix in ("/", "?"):
            if self._current_view == "k8s":
                k8s_view = self.query_one(K8sResourceView)
                k8s_view.set_filter(event.value)
            else:
                table = self.query_one(ConnectionTable)
                table.set_filter(event.value)

    def on_command_bar_cancelled(self, event):
        # type: (CommandBar.Cancelled) -> None
        """Handle Escape / empty backspace — cancel command bar."""
        if self._current_view == "k8s":
            k8s_view = self.query_one(K8sResourceView)
            k8s_view.clear_filter()
        else:
            table = self.query_one(ConnectionTable)
            table.clear_filter()
        self._restore_focus()

    def _execute_command(self, cmd):
        # type: (str) -> None
        """Execute a : command."""
        if cmd in ("q", "quit"):
            self.exit()

    def _restore_focus(self):
        # type: () -> None
        """Restore focus to the active view's DataTable after command bar closes."""
        if self._current_view == "k8s":
            try:
                k8s_view = self.query_one(K8sResourceView)
                self.set_timer(0.05, k8s_view.focus_table)
            except Exception:
                pass
        else:
            try:
                table = self.query_one(ConnectionTable)
                dt = table.query_one(DataTable)
                self.set_timer(0.05, dt.focus)
            except Exception:
                pass

    # ---- Session callbacks ----

    def _sync_terminal_size(self):
        # type: () -> None
        """Re-sync terminal size after layout settles."""
        if self._current_view != "terminal" or not self.session_manager.is_connected:
            return
        try:
            terminal = self.query_one(TerminalView)
            cols, rows = terminal.get_terminal_size()
            self.run_worker(
                self.session_manager.resize_terminal(cols, rows),
                exclusive=False,
            )
        except Exception:
            pass

    def _on_terminal_resize(self, cols, rows):
        # type: (int, int) -> None
        """Called when the terminal view resizes — update remote PTY."""
        if self._current_view == "terminal" and self.session_manager.is_connected:
            self.run_worker(self.session_manager.resize_terminal(cols, rows), exclusive=False)

    def _on_session_output(self, data):
        # type: (str) -> None
        try:
            terminal = self.query_one(TerminalView)
            terminal.write_output(data)
        except Exception:
            pass

    def _on_session_disconnect(self):
        # type: () -> None
        try:
            terminal = self.query_one(TerminalView)
            terminal.set_on_resize(None)
            terminal.write_line("\n[Connection closed]")
        except Exception:
            pass
        if self._k8s_return:
            # K8s exec ended — wait 5s or press any key to return
            try:
                terminal = self.query_one(TerminalView)
                terminal.write_line("[Press any key to return, or wait 5s...]")
            except Exception:
                pass
            self.set_timer(5.0, self._auto_return_to_list)
        else:
            # Normal connection — auto-return after 1s
            self.set_timer(1.0, self._auto_return_to_list)

    def _auto_return_to_list(self):
        # type: () -> None
        if self._current_view == "terminal":
            if self._k8s_return:
                self._k8s_return = False
                status_bar = self.query_one(StatusBar)
                status_bar.stop_timer()
                status_bar.update_connection("", "", "", 0)
                self._switch_to_view("k8s")
            else:
                self._return_to_list()

    # ---- Table events ----

    async def on_data_table_row_selected(self, event):
        # type: (object) -> None
        """Triggered when user presses Enter on a DataTable row."""
        if self._current_view == "list":
            await self.action_do_connect()
        elif self._current_view == "k8s":
            await self._k8s_exec_pod()
