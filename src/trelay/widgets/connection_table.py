"""Connection table widget for the Trelay TUI."""
from __future__ import annotations

from typing import List, Optional

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import DataTable

from trelay.models import Connection
from trelay.widgets.protocol_badge import render_protocol_badge, render_status_indicator


class ConnectionTable(Widget):
    """A widget wrapping a DataTable to display connections."""

    def __init__(self, **kwargs):
        # type: (...) -> None
        super().__init__(**kwargs)
        self._all_connections = []  # type: List[Connection]
        self._filter_text = ""

    def compose(self):
        # type: () -> ComposeResult
        yield DataTable(id="connections-data-table", cursor_type="row")

    def on_mount(self):
        # type: () -> None
        table = self.query_one(DataTable)
        table.add_columns(
            "Status",
            "Name",
            "Host",
            "Protocol",
            "Port",
            "Description",
            "Last Connected",
        )

    def refresh_data(self, connections):
        # type: (List[Connection]) -> None
        self._all_connections = list(connections)
        self._apply_filter()

    def set_filter(self, text):
        # type: (str) -> None
        """Set the search filter and re-render the table."""
        self._filter_text = text.lower()
        self._apply_filter()

    def clear_filter(self):
        # type: () -> None
        """Clear the search filter and show all connections."""
        self._filter_text = ""
        self._apply_filter()

    def _apply_filter(self):
        # type: () -> None
        table = self.query_one(DataTable)
        old_cursor_row = table.cursor_coordinate.row if table.row_count > 0 else 0
        table.clear()

        for conn in self._all_connections:
            if self._filter_text:
                haystack = " ".join([
                    conn.name,
                    conn.host,
                    conn.protocol.value,
                    str(conn.port),
                    conn.description,
                ]).lower()
                if self._filter_text not in haystack:
                    continue
            table.add_row(
                render_status_indicator(conn.status),
                conn.name,
                conn.host,
                render_protocol_badge(conn.protocol),
                str(conn.port),
                conn.description,
                conn.display_last_connected(),
                key=conn.name,
            )

        if table.row_count > 0:
            restored_row = min(old_cursor_row, table.row_count - 1)
            table.move_cursor(row=restored_row)

    def get_selected_connection_name(self):
        # type: () -> Optional[str]
        table = self.query_one(DataTable)
        if table.row_count == 0:
            return None
        try:
            row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
            return str(row_key.value)
        except Exception:
            return None
