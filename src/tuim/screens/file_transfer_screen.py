"""SFTP dual-panel file transfer screen (Midnight Commander style)."""
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import DataTable, Input, Static

from tuim.i18n import t
from tuim.models import Connection
from tuim.services.sftp_service import SFTPService, FileEntry, list_local_dir, _format_size
from tuim.widgets.header_bar import _build_shortcuts


async def _async_list_local(path):
    # type: (str) -> list
    """Wrap synchronous local listing for the panel callback interface."""
    return list_local_dir(path)


def _find_rename_path(base_path):
    # type: (str) -> str
    """Find next available path: base_path.1, .2, .3, ..."""
    n = 1
    while True:
        candidate = "{}.{}".format(base_path, n)
        if not os.path.exists(candidate):
            return candidate
        n += 1


class FileTransferScreen(ModalScreen[None]):
    """Full-screen modal for SFTP file browsing and transfer.

    Keys that DataTable also binds (enter, left, right, backspace) are
    registered as Screen-level BINDINGS so they take priority over the
    DataTable's own bindings.  Character keys (j/k/l/h/g/G/r/./q//)
    are handled in on_key since DataTable does not bind them.
    """

    # Screen bindings with priority=True override DataTable's own bindings.
    BINDINGS = [
        Binding("escape", "close_transfer", show=False, priority=True),
        Binding("tab", "switch_panel", show=False, priority=True),
        Binding("enter", "enter_dir", show=False, priority=True),
        Binding("right", "transfer_right", show=False, priority=True),
        Binding("left", "transfer_left", show=False, priority=True),
        Binding("backspace", "go_parent", show=False, priority=True),
    ]

    DEFAULT_CSS = """
    FileTransferScreen {
        align: center middle;
    }

    FileTransferScreen > Vertical {
        width: 100%;
        height: 100%;
        background: #0d1117;
    }

    FileTransferScreen #ft-header {
        height: auto;
        min-height: 2;
        background: #161b22;
        color: #e6edf3;
        padding: 0 1;
    }

    FileTransferScreen #ft-header Horizontal {
        width: 1fr;
        height: auto;
    }

    FileTransferScreen #ft-header-info {
        width: 1fr;
        content-align: left middle;
        height: auto;
    }

    FileTransferScreen #ft-header-shortcuts {
        width: auto;
        text-align: right;
    }

    FileTransferScreen #ft-panels {
        height: 1fr;
    }

    FileTransferScreen #ft-progress {
        height: auto;
        max-height: 2;
        background: #161b22;
        color: #39c5cf;
        padding: 0 1;
    }

    FileTransferScreen #ft-status {
        height: 1;
        background: #161b22;
        color: #8b949e;
        padding: 0 1;
    }

    FileTransferScreen FileBrowserPanel {
        width: 1fr;
        height: 1fr;
        border: solid #30363d;
    }

    FileTransferScreen FileBrowserPanel.-active {
        border: solid #39c5cf;
    }

    FileTransferScreen .panel-title {
        height: 1;
        background: #21262d;
        color: #39c5cf;
        padding: 0 1;
    }

    FileTransferScreen #ft-search {
        height: 1;
        background: #161b22;
        color: #e6edf3;
        display: none;
    }

    FileTransferScreen #ft-search.visible {
        display: block;
    }

    FileTransferScreen #ft-search Input {
        width: 1fr;
        height: 1;
        border: none;
        background: #161b22;
        color: #e6edf3;
    }

    FileTransferScreen .panel-path {
        height: 1;
        background: #161b22;
        color: #8b949e;
        padding: 0 1;
    }
    """

    _SFTP_SHORTCUT_ROWS = [
        [("↑↓", "nav"), ("Enter", "sftp_key_enter"), ("Tab", "sftp_key_switch"), ("→/l", "sftp_key_upload"), ("←/h", "sftp_key_download")],
        [("n", "sftp_key_mkdir"), ("/", "search"), ("r", "refresh"), (".", "sftp_key_hidden"), ("q", "sftp_key_close")],
    ]

    def __init__(self, connection):
        # type: (Connection) -> None
        super().__init__()
        self._connection = connection
        self._sftp = None  # type: Optional[SFTPService]
        self._active_panel = "local"  # "local" | "remote"
        self._transfer_in_progress = False
        self._confirm_pending = False
        # Progress tracking
        self._progress_file = ""
        self._progress_bytes_done = 0
        self._progress_bytes_total = 0
        self._progress_start_time = 0.0
        self._progress_last_bytes = 0
        self._progress_last_time = 0.0
        self._progress_speed = 0.0
        self._search_active = False

    def compose(self):
        # type: () -> ComposeResult
        from tuim.widgets.file_panel import FileBrowserPanel

        with Vertical():
            with Horizontal(id="ft-header"):
                yield Static(
                    "[bold #39c5cf]⬡ Tuim[/]",
                    id="ft-header-info",
                    markup=True,
                )
                yield Static(
                    _build_shortcuts(self._SFTP_SHORTCUT_ROWS),
                    id="ft-header-shortcuts",
                    markup=True,
                )
            with Horizontal(id="ft-panels"):
                yield FileBrowserPanel(
                    panel_id="local-panel",
                    title="[{}] {}".format(t("sftp_local"), "~"),
                    list_dir_fn=_async_list_local,
                )
                yield FileBrowserPanel(
                    panel_id="remote-panel",
                    title="[{}]".format(t("sftp_remote")),
                    list_dir_fn=self._remote_listdir,
                )
            yield Static("", id="ft-progress")
            with Horizontal(id="ft-search"):
                yield Static("/", classes="search-prefix")
                yield Input(id="ft-search-input", placeholder="filter...")
            yield Static(t("sftp_connecting"), id="ft-status")

    async def on_mount(self):
        # type: () -> None
        from tuim.widgets.file_panel import FileBrowserPanel

        # Mark the local panel as active
        local_panel = self.query_one("#local-panel", FileBrowserPanel)
        local_panel.add_class("-active")

        # Navigate local panel to home
        home = str(Path.home())
        await local_panel.navigate_to(home)

        # Connect SFTP
        self._sftp = SFTPService(self._connection)
        try:
            await self._sftp.connect()
        except Exception as exc:
            status = self.query_one("#ft-status", Static)
            status.update(t("sftp_connect_failed", error=str(exc)))
            self.app.notify(t("sftp_connect_failed", error=str(exc)), severity="error")
            # Dismiss after showing error briefly
            self.set_timer(2.0, self._dismiss_on_error)
            return

        # Get remote home and navigate
        remote_home = await self._sftp.get_home_dir()
        remote_panel = self.query_one("#remote-panel", FileBrowserPanel)
        await remote_panel.navigate_to(remote_home)

        # Update status
        cfg = self._connection.ssh_config
        user = cfg.username if cfg else ""
        host = self._connection.host
        port = self._connection.port
        label = "{}@{}:{}".format(user, host, port) if user else "{}:{}".format(host, port)
        status = self.query_one("#ft-status", Static)
        status.update("{} | {}".format(t("sftp_connected"), label))

        # Focus local panel table
        local_panel.focus_table()

        # Progress refresh timer
        self.set_interval(0.1, self._update_progress_display)

    def _dismiss_on_error(self):
        # type: () -> None
        self.dismiss(None)

    async def _remote_listdir(self, path):
        # type: (str) -> list
        """Remote directory listing via SFTP."""
        if self._sftp is None:
            return []
        return await self._sftp.listdir(path)

    # ---- Screen-level actions (BINDINGS) ----
    # These override DataTable's own enter/left/right/backspace bindings.

    def action_close_transfer(self):
        # type: () -> None
        """Escape key — close (blocked during transfer)."""
        if self._search_active:
            self._deactivate_search(clear=True)
            return
        if self._transfer_in_progress:
            self.app.notify(t("sftp_in_progress"), severity="warning")
            return
        self.run_worker(self._do_close(), exclusive=False)

    def action_switch_panel(self):
        # type: () -> None
        """Tab key — toggle active panel."""
        if self._search_active:
            return
        self._toggle_panel()

    def action_enter_dir(self):
        # type: () -> None
        """Enter key — navigate into directory or confirm search."""
        if self._search_active:
            self._deactivate_search(clear=False)
            return
        self.run_worker(self._enter_selected(), exclusive=False)

    def action_transfer_right(self):
        # type: () -> None
        """Right arrow — upload (local panel only)."""
        if self._search_active:
            return
        if self._active_panel == "local" and not self._transfer_in_progress:
            self.run_worker(self._do_upload(), exclusive=False)

    def action_transfer_left(self):
        # type: () -> None
        """Left arrow — download (remote panel only)."""
        if self._search_active:
            return
        if self._active_panel == "remote" and not self._transfer_in_progress:
            self.run_worker(self._do_download(), exclusive=False)

    def action_go_parent(self):
        # type: () -> None
        """Backspace — navigate to parent directory."""
        if self._search_active:
            return
        self.run_worker(self._go_up(), exclusive=False)

    # ---- on_key: character keys (not bound by DataTable) ----

    def on_key(self, event):
        # type: (object) -> None
        char = event.character

        # Search mode — let Input handle everything, block other keys
        if self._search_active:
            return

        # q: close
        if char == "q":
            event.prevent_default()
            event.stop()
            if self._transfer_in_progress:
                self.app.notify(t("sftp_in_progress"), severity="warning")
                return
            self.run_worker(self._do_close(), exclusive=False)
            return

        # j/k: vim navigation
        if char in ("j", "k"):
            event.prevent_default()
            event.stop()
            panel = self._get_active_panel()
            try:
                dt = panel.query_one(DataTable)
                if char == "j":
                    dt.action_cursor_down()
                else:
                    dt.action_cursor_up()
            except Exception:
                pass
            return

        # l: upload (local panel only)
        if char == "l":
            event.prevent_default()
            event.stop()
            if self._active_panel == "local" and not self._transfer_in_progress:
                self.run_worker(self._do_upload(), exclusive=False)
            return

        # h: download (remote panel only)
        if char == "h":
            event.prevent_default()
            event.stop()
            if self._active_panel == "remote" and not self._transfer_in_progress:
                self.run_worker(self._do_download(), exclusive=False)
            return

        # /: search filter
        if char == "/":
            event.prevent_default()
            event.stop()
            self._activate_search()
            return

        # g: jump to top
        if char == "g":
            event.prevent_default()
            event.stop()
            panel = self._get_active_panel()
            panel.move_cursor_top()
            return

        # G: jump to bottom
        if char == "G":
            event.prevent_default()
            event.stop()
            panel = self._get_active_panel()
            panel.move_cursor_bottom()
            return

        # r: refresh
        if char == "r":
            event.prevent_default()
            event.stop()
            self.run_worker(self._refresh_active(), exclusive=False)
            return

        # .: toggle hidden files
        if char == ".":
            event.prevent_default()
            event.stop()
            panel = self._get_active_panel()
            panel.toggle_hidden()
            return

        # n: new folder
        if char == "n":
            event.prevent_default()
            event.stop()
            if not self._transfer_in_progress:
                self._do_mkdir()
            return

    # ---- Panel management ----

    def _get_active_panel(self):
        from tuim.widgets.file_panel import FileBrowserPanel
        if self._active_panel == "local":
            return self.query_one("#local-panel", FileBrowserPanel)
        return self.query_one("#remote-panel", FileBrowserPanel)

    def _get_inactive_panel(self):
        from tuim.widgets.file_panel import FileBrowserPanel
        if self._active_panel == "local":
            return self.query_one("#remote-panel", FileBrowserPanel)
        return self.query_one("#local-panel", FileBrowserPanel)

    def _toggle_panel(self):
        # type: () -> None
        from tuim.widgets.file_panel import FileBrowserPanel

        old_panel = self._get_active_panel()
        old_panel.remove_class("-active")

        if self._active_panel == "local":
            self._active_panel = "remote"
        else:
            self._active_panel = "local"

        new_panel = self._get_active_panel()
        new_panel.add_class("-active")
        new_panel.focus_table()

    # ---- Search ----

    def _activate_search(self):
        # type: () -> None
        self._search_active = True
        try:
            search_bar = self.query_one("#ft-search")
            search_bar.add_class("visible")
            inp = self.query_one("#ft-search-input", Input)
            inp.value = ""
            inp.focus()
        except Exception:
            pass

    def _deactivate_search(self, clear=False):
        # type: (bool) -> None
        self._search_active = False
        try:
            search_bar = self.query_one("#ft-search")
            search_bar.remove_class("visible")
        except Exception:
            pass
        if clear:
            panel = self._get_active_panel()
            panel.set_filter("")
        panel = self._get_active_panel()
        panel.focus_table()

    def on_input_changed(self, event):
        # type: (Input.Changed) -> None
        """Real-time search filter as user types."""
        if self._search_active and event.input.id == "ft-search-input":
            panel = self._get_active_panel()
            panel.set_filter(event.value)

    # ---- Navigation ----

    async def _enter_selected(self):
        # type: () -> None
        panel = self._get_active_panel()
        if panel.is_on_dotdot():
            await self._go_up()
            return
        entry = panel.get_selected_entry()
        if entry is not None and entry.is_dir:
            await panel.navigate_to(entry.full_path)

    async def _go_up(self):
        # type: () -> None
        panel = self._get_active_panel()
        current = panel.get_current_path()
        parent = os.path.dirname(current.rstrip("/"))
        if not parent:
            parent = "/"
        await panel.navigate_to(parent)

    async def _refresh_active(self):
        # type: () -> None
        panel = self._get_active_panel()
        await panel.navigate_to(panel.get_current_path())

    # ---- Mkdir ----

    def _do_mkdir(self):
        # type: () -> None
        from tuim.screens.mkdir_screen import MkdirScreen

        if self._confirm_pending:
            return
        self._confirm_pending = True

        def on_result(name):
            # type: (str | None) -> None
            self._confirm_pending = False
            if name:
                self.run_worker(self._execute_mkdir(name), exclusive=False)

        self.app.push_screen(MkdirScreen(), on_result)

    async def _execute_mkdir(self, name):
        # type: (str) -> None
        panel = self._get_active_panel()
        current_path = panel.get_current_path()

        try:
            if self._active_panel == "local":
                new_path = os.path.join(current_path, name)
                os.makedirs(new_path, exist_ok=False)
            else:
                new_path = current_path.rstrip("/") + "/" + name
                await self._sftp.mkdir(new_path)
            self.app.notify(t("sftp_mkdir_done", name=name), severity="information")
            await panel.navigate_to(current_path)
        except Exception as exc:
            self.app.notify(t("sftp_mkdir_failed", error=str(exc)), severity="error")

    # ---- Transfer ----

    async def _do_upload(self):
        # type: () -> None
        from tuim.widgets.file_panel import FileBrowserPanel
        from tuim.screens.transfer_confirm import TransferConfirmScreen

        local_panel = self.query_one("#local-panel", FileBrowserPanel)
        remote_panel = self.query_one("#remote-panel", FileBrowserPanel)
        entry = local_panel.get_selected_entry()
        if entry is None or entry.is_dir:
            return
        if self._confirm_pending:
            return

        remote_dir = remote_panel.get_current_path()
        self._confirm_pending = True

        def on_result(result):
            # type: (str | None) -> None
            self._confirm_pending = False
            if result == "confirm":
                self.run_worker(
                    self._execute_upload(entry, remote_dir), exclusive=False,
                )

        self.app.push_screen(
            TransferConfirmScreen("upload", entry.name, remote_dir),
            on_result,
        )

    async def _execute_upload(self, entry, remote_dir):
        # type: (object, str) -> None
        from tuim.widgets.file_panel import FileBrowserPanel

        remote_panel = self.query_one("#remote-panel", FileBrowserPanel)

        self._transfer_in_progress = True
        self._progress_file = entry.name
        self._progress_bytes_done = 0
        self._progress_bytes_total = entry.size
        self._progress_start_time = time.time()
        self._progress_last_time = time.time()
        self._progress_last_bytes = 0
        self._progress_speed = 0.0

        status = self.query_one("#ft-status", Static)
        status.update(t("sftp_uploading", name=entry.name))

        remote_dest = remote_dir.rstrip("/") + "/" + entry.name
        try:
            await self._sftp.upload(entry.full_path, remote_dest, self._on_progress)
            self.app.notify(t("sftp_upload_done", name=entry.name), severity="information")
            await remote_panel.navigate_to(remote_panel.get_current_path())
        except Exception as exc:
            self.app.notify(t("sftp_transfer_failed", error=str(exc)), severity="error")
        finally:
            self._transfer_in_progress = False
            self._clear_progress()

    async def _do_download(self):
        # type: () -> None
        from tuim.widgets.file_panel import FileBrowserPanel
        from tuim.screens.transfer_confirm import TransferConfirmScreen

        local_panel = self.query_one("#local-panel", FileBrowserPanel)
        remote_panel = self.query_one("#remote-panel", FileBrowserPanel)
        entry = remote_panel.get_selected_entry()
        if entry is None or entry.is_dir:
            return
        if self._confirm_pending:
            return

        local_dir = local_panel.get_current_path()
        local_dest = os.path.join(local_dir, entry.name)
        file_exists = os.path.exists(local_dest)
        mode = "download_exists" if file_exists else "download"
        self._confirm_pending = True

        def on_result(result):
            # type: (str | None) -> None
            self._confirm_pending = False
            if result is None:
                return
            if result == "rename":
                dest = _find_rename_path(local_dest)
            else:
                # "confirm" or "overwrite"
                dest = local_dest
            self.run_worker(
                self._execute_download(entry, dest), exclusive=False,
            )

        self.app.push_screen(
            TransferConfirmScreen(mode, entry.name, local_dir),
            on_result,
        )

    async def _execute_download(self, entry, local_dest):
        # type: (object, str) -> None
        from tuim.widgets.file_panel import FileBrowserPanel

        local_panel = self.query_one("#local-panel", FileBrowserPanel)

        self._transfer_in_progress = True
        self._progress_file = entry.name
        self._progress_bytes_done = 0
        self._progress_bytes_total = entry.size
        self._progress_start_time = time.time()
        self._progress_last_time = time.time()
        self._progress_last_bytes = 0
        self._progress_speed = 0.0

        status = self.query_one("#ft-status", Static)
        status.update(t("sftp_downloading", name=entry.name))

        try:
            await self._sftp.download(entry.full_path, local_dest, self._on_progress)
            self.app.notify(t("sftp_download_done", name=entry.name), severity="information")
            await local_panel.navigate_to(local_panel.get_current_path())
        except Exception as exc:
            self.app.notify(t("sftp_transfer_failed", error=str(exc)), severity="error")
        finally:
            self._transfer_in_progress = False
            self._clear_progress()

    def _on_progress(self, srcpath, dstpath, bytes_done, bytes_total):
        # type: (str, str, int, int) -> None
        """asyncssh progress_handler callback."""
        self._progress_bytes_done = bytes_done
        self._progress_bytes_total = bytes_total
        now = time.time()
        dt = now - self._progress_last_time
        if dt >= 0.5:
            db = bytes_done - self._progress_last_bytes
            self._progress_speed = db / dt if dt > 0 else 0
            self._progress_last_bytes = bytes_done
            self._progress_last_time = now

    def _update_progress_display(self):
        # type: () -> None
        """Timer callback: render the progress bar."""
        if not self._transfer_in_progress:
            return
        try:
            progress_widget = self.query_one("#ft-progress", Static)
        except Exception:
            return

        total = self._progress_bytes_total
        done = self._progress_bytes_done
        if total <= 0:
            pct = 0
        else:
            pct = min(int(done * 100 / total), 100)

        bar_width = 24
        filled = int(bar_width * pct / 100)
        bar = "\u2588" * filled + "\u2591" * (bar_width - filled)

        speed_str = _format_size(int(self._progress_speed)) + "/s"
        done_str = _format_size(done)
        total_str = _format_size(total)

        text = " {} {}% ({}/{}) {}  {}".format(
            bar, pct, done_str, total_str, self._progress_file, speed_str,
        )
        progress_widget.update(text)

    def _clear_progress(self):
        # type: () -> None
        try:
            progress_widget = self.query_one("#ft-progress", Static)
            progress_widget.update("")
        except Exception:
            pass
        # Restore status
        cfg = self._connection.ssh_config
        user = cfg.username if cfg else ""
        host = self._connection.host
        port = self._connection.port
        label = "{}@{}:{}".format(user, host, port) if user else "{}:{}".format(host, port)
        try:
            status = self.query_one("#ft-status", Static)
            status.update("{} | {}".format(t("sftp_connected"), label))
        except Exception:
            pass

    # ---- Close ----

    async def _do_close(self):
        # type: () -> None
        if self._sftp is not None:
            await self._sftp.disconnect()
            self._sftp = None
        self.dismiss(None)
