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
from trelay.i18n import t, t_en
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
        self._last_k8s_exec_conn = None  # type: Optional[object]
        self._shell_retry_pending = False
        self._k8s_on_disconnect = None  # type: Optional[str]  # None/"stay"/"return"

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
                "assets", "example_connections.yaml"
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
            status_bar.update_mode(t("mode_list"))
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
            status_bar.update_mode(t_en("mode_k8s"))
            status_bar.stop_timer()
            header_bar.set_k8s_mode()
            try:
                k8s_view = self.query_one(K8sResourceView)
                self.set_timer(0.1, k8s_view.focus_table)
            except Exception:
                pass
        else:
            switcher.current = "terminal-container"
            status_bar.update_mode(t("mode_terminal"))

    # ---- Key handling: mode dispatchers ----

    def _key_to_terminal(self, event):
        """Map a Textual key event to terminal escape data. Returns None to skip."""
        key = event.key
        char = event.character

        if key == "escape":
            return "\x1b"

        if key.startswith("ctrl+") and len(key) == 6:
            letter = key[-1]
            if 'a' <= letter <= 'z':
                return chr(ord(letter) - ord('a') + 1)

        if key in _KEY_MAP:
            return _KEY_MAP[key]

        if char and len(char) >= 1 and ord(char[0]) >= 32:
            return char

        if key == "space":
            return " "

        return None

    async def on_key(self, event):
        """Route key events to the active mode handler."""
        if self._current_view == "terminal":
            await self._handle_key_terminal(event)
        elif self._current_view == "k8s":
            self._handle_key_k8s(event)
        elif self._current_view == "list":
            self._handle_key_list(event)

    async def _handle_key_terminal(self, event):
        """Terminal mode: forward all keystrokes to the remote session."""
        if self._shell_retry_pending:
            return
        if not self.session_manager.is_connected:
            # Disconnected - check if we should return on this key
            if self._k8s_return:
                if self._k8s_on_disconnect == "stay":
                    # View mode (describe) — Ctrl+C to return, others allow scrolling
                    if event.key == "ctrl+c":
                        event.prevent_default()
                        event.stop()
                        self._auto_return_to_list()
                    return
                # Other K8s modes - any key returns
            # Normal connection - any key returns
            # But allow scroll keys to work first
            key = event.key
            if key not in ("shift+up", "shift+down", "shift+pageup", "shift+pagedown"):
                event.prevent_default()
                event.stop()
                self._auto_return_to_list()
            return
        # Shift+Up/Down or Shift+PageUp/PageDown → scroll terminal history
        key = event.key
        if key in ("shift+up", "shift+down", "shift+pageup", "shift+pagedown"):
            event.prevent_default()
            event.stop()
            terminal = self.query_one(TerminalView)
            if key == "shift+up":
                terminal.scroll_up(1)
            elif key == "shift+down":
                terminal.scroll_down(1)
            elif key == "shift+pageup":
                terminal.scroll_up(terminal.get_terminal_size()[1])
            else:
                terminal.scroll_down(terminal.get_terminal_size()[1])
            return
        data = self._key_to_terminal(event)
        if data is not None:
            event.prevent_default()
            event.stop()
            await self.session_manager.send_input(data)

    def _handle_key_k8s(self, event):
        """K8s resource browser mode: command bar, search, and navigation."""
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
        if char == "d":
            event.prevent_default()
            event.stop()
            self.run_worker(self._k8s_describe(), exclusive=False)
            return
        if char == "e":
            event.prevent_default()
            event.stop()
            self.run_worker(self._k8s_edit(), exclusive=False)
            return
        if char == "l":
            event.prevent_default()
            event.stop()
            self.run_worker(self._k8s_logs(), exclusive=False)
            return
        if char == "r":
            event.prevent_default()
            event.stop()
            self.run_worker(self._k8s_refresh(), exclusive=False)
            return

    def _handle_key_list(self, event):
        """List mode: command bar, search, and vim-style navigation."""
        cmd_bar = self.query_one(CommandBar)
        if cmd_bar.is_active:
            return
        key = event.key
        char = event.character
        if char in (":", "/", "?"):
            event.prevent_default()
            event.stop()
            cmd_bar.activate(char)
            return
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

        terminal.write_line(t("connecting_to", name=conn.name, proto=conn.protocol.value.upper()))

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
            terminal.write_line(t("connection_failed", error=str(exc)))

        handler = self.session_manager.current_handler
        if handler is not None and not handler.is_interactive:
            terminal.write_line(t("connection_launched"))
            terminal.write_line(t("will_return"))

    async def action_do_disconnect(self):
        # type: () -> None
        if self._current_view != "terminal":
            return
        terminal = self.query_one(TerminalView)
        terminal.set_on_resize(None)
        terminal.write_line("\n" + t("disconnecting"))
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

        # Show help screen
        if cmd == "?" or cmd == "help":
            from trelay.screens.k8s_help_screen import K8sHelpScreen
            self.push_screen(K8sHelpScreen())
            return

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
            self._last_k8s_exec_conn = exec_conn
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

            terminal.write_line(t("exec_into_pod", name=name))
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
                terminal.write_line(t("exec_failed", error=str(exc)))
            return

        # Other resource types: no action on Enter

    def action_quit_app(self):
        # type: () -> None
        self.exit()

    # ---- Command bar: mode dispatchers ----

    def on_command_bar_submitted(self, event):
        # type: (CommandBar.Submitted) -> None
        """Handle command bar submission — dispatch by mode."""
        cmd_bar = self.query_one(CommandBar)
        prefix = event.prefix
        value = event.value.strip()

        if prefix == ":":
            cmd_bar.deactivate()
            if self._current_view == "k8s":
                self._on_cmd_submit_k8s(value)
            else:
                self._on_cmd_submit_list(value)
        elif prefix in ("/", "?"):
            cmd_bar.deactivate()
        self._restore_focus()

    def _on_cmd_submit_k8s(self, value):
        # type: (str) -> None
        """Handle : command in K8s mode."""
        self.run_worker(self._execute_k8s_command(value), exclusive=False)

    def _on_cmd_submit_list(self, value):
        # type: (str) -> None
        """Handle : command in List mode."""
        self._execute_command(value)

    def on_command_bar_changed(self, event):
        # type: (CommandBar.Changed) -> None
        """Handle real-time search — dispatch by mode."""
        if event.prefix in ("/", "?"):
            if self._current_view == "k8s":
                self._on_cmd_search_k8s(event.value)
            else:
                self._on_cmd_search_list(event.value)

    def _on_cmd_search_k8s(self, text):
        # type: (str) -> None
        k8s_view = self.query_one(K8sResourceView)
        k8s_view.set_filter(text)

    def _on_cmd_search_list(self, text):
        # type: (str) -> None
        table = self.query_one(ConnectionTable)
        table.set_filter(text)

    def on_command_bar_cancelled(self, event):
        # type: (CommandBar.Cancelled) -> None
        """Handle command bar cancel — dispatch by mode."""
        if self._current_view == "k8s":
            self._on_cmd_cancel_k8s()
        else:
            self._on_cmd_cancel_list()
        self._restore_focus()

    def _on_cmd_cancel_k8s(self):
        # type: () -> None
        k8s_view = self.query_one(K8sResourceView)
        k8s_view.clear_filter()

    def _on_cmd_cancel_list(self):
        # type: () -> None
        table = self.query_one(ConnectionTable)
        table.clear_filter()

    def _execute_command(self, cmd):
        # type: (str) -> None
        """Execute a : command."""
        if cmd in ("q", "quit", "q!"):
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
        handler = self.session_manager.current_handler
        quick_failure = (
            self._k8s_return
            and handler is not None
            and hasattr(handler, "was_quick_failure")
            and handler.was_quick_failure
        )
        try:
            terminal = self.query_one(TerminalView)
            terminal.set_on_resize(None)
            terminal.write_line("\n" + t("connection_closed"))
        except Exception:
            pass
        if quick_failure:
            # Shell likely doesn't exist — offer alternatives
            self.call_later(self._prompt_shell_retry)
        elif self._k8s_return:
            if self._k8s_on_disconnect == "stay":
                # View mode (describe) — stay on terminal, Ctrl+C to return
                pass
            elif self._k8s_on_disconnect == "return":
                # Edit mode — return immediately after vim exits
                self.call_later(self._auto_return_to_list)
            else:
                # K8s exec ended — wait for any key to return
                try:
                    terminal = self.query_one(TerminalView)
                    terminal.write_line(t("press_any_key_return"))
                except Exception:
                    pass
        else:
            # Normal connection — wait for any key to return
            try:
                terminal = self.query_one(TerminalView)
                terminal.write_line(t("press_any_key_return"))
            except Exception:
                pass

    def _prompt_shell_retry(self):
        # type: () -> None
        """Show ShellPickerScreen after a quick K8s exec failure."""
        from trelay.screens.shell_picker import ShellPickerScreen

        self._shell_retry_pending = True

        def on_result(shell_cmd):
            self._shell_retry_pending = False
            if shell_cmd:
                self.run_worker(
                    self._retry_k8s_exec(shell_cmd), exclusive=False
                )
            else:
                # User cancelled — return to K8s browser
                self._auto_return_to_list()

        self.push_screen(ShellPickerScreen(), on_result)

    async def _retry_k8s_exec(self, shell_command):
        # type: (str) -> None
        """Retry K8s exec with a different shell command."""
        import copy
        from trelay.models import K8sConfig

        conn = self._last_k8s_exec_conn
        if conn is None:
            self._auto_return_to_list()
            return

        # Disconnect existing session
        await self.session_manager.disconnect()

        exec_conn = copy.deepcopy(conn)
        if exec_conn.k8s_config is None:
            exec_conn.k8s_config = K8sConfig()
        exec_conn.k8s_config.command = shell_command
        self._last_k8s_exec_conn = exec_conn

        terminal = self.query_one(TerminalView)
        terminal.clear_output()

        terminal.set_on_resize(self._on_terminal_resize)

        pod_name = exec_conn.k8s_config.pod
        terminal.write_line(t("retrying_exec", shell=shell_command, name=pod_name))
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
            terminal.write_line(t("exec_failed", error=str(exc)))

    def _auto_return_to_list(self):
        # type: () -> None
        if self._shell_retry_pending:
            return
        if self._current_view == "terminal":
            self._k8s_on_disconnect = None
            if self._k8s_return:
                self._k8s_return = False
                status_bar = self.query_one(StatusBar)
                status_bar.stop_timer()
                status_bar.update_connection("", "", "", 0)
                self._switch_to_view("k8s")
            else:
                self._return_to_list()

    # ---- K8s shortcut commands (d/e/l) ----

    async def _k8s_run_command(self, kubectl_args, status_label, message, on_disconnect=None):
        # type: (list, str, str, str) -> None
        """Run an arbitrary kubectl command in the terminal (triggered from K8s browser).

        kubectl_args: sub-command arguments appended after base kubectl flags.
        status_label: label shown in the status bar.
        message: message printed in the terminal before the command runs.
        on_disconnect: disconnect behavior — None (prompt+5s), "stay" (Ctrl+C),
                       "return" (immediate).
        """
        conn = self._k8s_connection
        if conn is None:
            return

        import copy
        import os as _os
        from trelay.models import K8sConfig

        exec_conn = copy.deepcopy(conn)
        if exec_conn.k8s_config is None:
            exec_conn.k8s_config = K8sConfig()

        k8s_view = self.query_one(K8sResourceView)
        exec_conn.k8s_config.namespace = k8s_view.get_namespace()

        self._k8s_return = True
        self._k8s_on_disconnect = on_disconnect
        self._last_k8s_exec_conn = exec_conn

        terminal = self.query_one(TerminalView)
        terminal.clear_output()
        self._switch_to_view("terminal")
        terminal.set_on_resize(self._on_terminal_resize)

        status_bar = self.query_one(StatusBar)
        status_bar.update_connection(status_label, "K8S", "", 0)
        status_bar.start_timer()

        terminal.write_line(message)
        term_size = terminal.get_terminal_size()

        # Build full kubectl command
        cfg = exec_conn.k8s_config
        base_cmd = ["kubectl"]
        if cfg.kubeconfig:
            base_cmd.extend(["--kubeconfig", _os.path.expanduser(cfg.kubeconfig)])
        if cfg.context:
            base_cmd.extend(["--context", cfg.context])
        if cfg.namespace:
            base_cmd.extend(["-n", cfg.namespace])
        full_cmd = base_cmd + kubectl_args

        try:
            await self.session_manager.connect(
                exec_conn,
                on_output=self._on_session_output,
                on_disconnect=self._on_session_disconnect,
                term_size=term_size,
                override_command=full_cmd,
            )
            self.set_timer(0.3, self._sync_terminal_size)
        except Exception as exc:
            terminal.write_line(t("exec_failed", error=str(exc)))

    async def _k8s_describe(self):
        # type: () -> None
        """d key: kubectl get <type> <name> -o yaml"""
        k8s_view = self.query_one(K8sResourceView)
        resource_type = k8s_view.get_current_resource_type()
        name = k8s_view.get_selected_resource_name()
        if not name:
            return
        ns = k8s_view.get_namespace()
        await self._k8s_run_command(
            ["get", resource_type, name, "-o", "yaml"],
            "{}:{}".format(ns, name),
            t("k8s_describing", name=name),
            on_disconnect="stay",
        )

    async def _k8s_edit(self):
        # type: () -> None
        """e key: kubectl edit <type> <name>"""
        k8s_view = self.query_one(K8sResourceView)
        resource_type = k8s_view.get_current_resource_type()
        name = k8s_view.get_selected_resource_name()
        if not name:
            return
        ns = k8s_view.get_namespace()
        await self._k8s_run_command(
            ["edit", resource_type, name],
            "{}:{}".format(ns, name),
            t("k8s_editing", name=name),
            on_disconnect="return",
        )

    async def _k8s_logs(self):
        # type: () -> None
        """l key: kubectl logs -f <pod> (pods only)"""
        k8s_view = self.query_one(K8sResourceView)
        resource_type = k8s_view.get_current_resource_type()
        name = k8s_view.get_selected_resource_name()
        if not name or resource_type != "pods":
            return
        ns = k8s_view.get_namespace()
        await self._k8s_run_command(
            ["logs", "-f", name],
            "{}:{}".format(ns, name),
            t("k8s_tailing_logs", name=name),
        )

    async def _k8s_refresh(self):
        # type: () -> None
        """r key: refresh K8s resource list."""
        k8s_view = self.query_one(K8sResourceView)
        k8s_view.reload_resources()

    # ---- Table events ----

    async def on_data_table_row_selected(self, event):
        # type: (object) -> None
        """Triggered when user presses Enter on a DataTable row."""
        if self._current_view == "list":
            await self.action_do_connect()
        elif self._current_view == "k8s":
            await self._k8s_exec_pod()
