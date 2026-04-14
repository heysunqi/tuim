"""Reusable file browser panel widget for the SFTP file transfer screen."""
from __future__ import annotations

from typing import Callable, List, Optional

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widget import Widget
from textual.widgets import DataTable, Static

from tuim.i18n import t
from tuim.services.sftp_service import FileEntry, _format_size


class FileBrowserPanel(Widget):
    """A single file browser panel (local or remote).

    The I/O callback ``list_dir_fn`` is injected so both local and remote
    panels share the same widget code.
    """

    def __init__(
        self,
        panel_id,   # type: str
        title,      # type: str
        list_dir_fn,  # type: Callable
        **kwargs,
    ):
        # type: (...) -> None
        super().__init__(id=panel_id, **kwargs)
        self._title = title
        self._list_dir_fn = list_dir_fn  # async callable(path) -> List[FileEntry]
        self._current_path = ""
        self._entries = []  # type: List[FileEntry]
        self._all_entries = []  # type: List[FileEntry]
        self._filter_text = ""
        self._show_hidden = False

    def compose(self):
        # type: () -> ComposeResult
        with Vertical():
            yield Static(self._title, classes="panel-title")
            yield Static("", classes="panel-path")
            yield DataTable(cursor_type="row", id="{}-table".format(self.id))

    def on_mount(self):
        # type: () -> None
        table = self.query_one(DataTable)
        table.add_columns(
            t("sftp_col_name"),
            t("sftp_col_size"),
            t("sftp_col_modified"),
        )

    async def navigate_to(self, path):
        # type: (str) -> None
        """Load a directory and display its contents."""
        self._current_path = path
        self._filter_text = ""
        try:
            path_label = self.query_one(".panel-path", Static)
            path_label.update(" " + path)
        except Exception:
            pass
        try:
            self._all_entries = await self._list_dir_fn(path)
        except Exception:
            self._all_entries = []
        self._apply_filter()

    def _apply_filter(self):
        # type: () -> None
        """Apply hidden-file and text filter, then refresh the table."""
        entries = self._all_entries
        if not self._show_hidden:
            entries = [e for e in entries if not e.name.startswith(".")]
        if self._filter_text:
            ft = self._filter_text.lower()
            entries = [e for e in entries if ft in e.name.lower()]
        self._entries = entries
        self._refresh_table()

    def _refresh_table(self):
        # type: () -> None
        table = self.query_one(DataTable)
        table.clear()
        # Always add ".." as first row
        table.add_row("..", t("sftp_dir_label"), "-", key="row-dotdot")
        if not self._entries:
            table.add_row(t("sftp_empty_dir"), "", "", key="row-empty")
        else:
            for i, entry in enumerate(self._entries):
                size_str = t("sftp_dir_label") if entry.is_dir else _format_size(entry.size)
                table.add_row(
                    entry.name,
                    size_str,
                    entry.modified,
                    key="row-{}".format(i),
                )

    def get_selected_entry(self):
        # type: () -> Optional[FileEntry]
        """Return the FileEntry at the cursor, or None for '..' / empty rows."""
        table = self.query_one(DataTable)
        try:
            row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
        except Exception:
            return None
        key_str = row_key.value
        if key_str == "row-dotdot" or key_str == "row-empty":
            return None
        if key_str.startswith("row-"):
            try:
                idx = int(key_str[4:])
                if 0 <= idx < len(self._entries):
                    return self._entries[idx]
            except ValueError:
                pass
        return None

    def is_on_dotdot(self):
        # type: () -> bool
        """Return True if cursor is on the '..' row."""
        table = self.query_one(DataTable)
        try:
            row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
            return row_key.value == "row-dotdot"
        except Exception:
            return False

    def get_current_path(self):
        # type: () -> str
        return self._current_path

    def set_filter(self, text):
        # type: (str) -> None
        self._filter_text = text
        self._apply_filter()

    def toggle_hidden(self):
        # type: () -> None
        self._show_hidden = not self._show_hidden
        self._apply_filter()

    def focus_table(self):
        # type: () -> None
        try:
            table = self.query_one(DataTable)
            table.focus()
        except Exception:
            pass

    def move_cursor_top(self):
        # type: () -> None
        try:
            table = self.query_one(DataTable)
            table.move_cursor(row=0)
        except Exception:
            pass

    def move_cursor_bottom(self):
        # type: () -> None
        try:
            table = self.query_one(DataTable)
            table.move_cursor(row=table.row_count - 1)
        except Exception:
            pass
