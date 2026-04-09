"""K8s resource browser widget for the Trelay TUI."""
from __future__ import annotations

from typing import List, Optional

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import DataTable, Static

from trelay.services.k8s_service import K8sService, RESOURCE_ALIASES


class K8sResourceView(Widget):
    """A widget that displays Kubernetes resources in a DataTable."""

    def __init__(self, **kwargs):
        # type: (...) -> None
        super().__init__(**kwargs)
        self._service = None  # type: Optional[K8sService]
        self._current_resource_type = "pods"
        self._all_rows = []  # type: List[List[str]]
        self._headers = []  # type: List[str]
        self._filter_text = ""

    def compose(self):
        # type: () -> ComposeResult
        yield Static("", id="k8s-header")
        yield DataTable(id="k8s-data-table", cursor_type="row")

    def set_k8s_context(self, kubeconfig, context, namespace):
        # type: (str, str, str) -> None
        """Set the cluster connection info."""
        self._service = K8sService(
            kubeconfig=kubeconfig,
            context=context,
            namespace=namespace,
        )
        self._update_header()

    def set_namespace(self, ns):
        # type: (str) -> None
        """Switch to a different namespace."""
        if self._service is not None:
            self._service.namespace = ns
        self._update_header()

    def get_namespace(self):
        # type: () -> str
        if self._service is not None:
            return self._service.namespace
        return "default"

    async def load_resources(self, resource_type):
        # type: (str) -> None
        """Load resources of the given type and refresh the table."""
        canonical = RESOURCE_ALIASES.get(resource_type, resource_type)
        self._current_resource_type = canonical
        self._filter_text = ""
        self._update_header()

        if self._service is None:
            return

        self._headers, self._all_rows = await self._service.get_resources(canonical)
        self._rebuild_table()

    def get_selected_resource_name(self):
        # type: () -> Optional[str]
        """Return the NAME column value of the currently selected row."""
        try:
            table = self.query_one("#k8s-data-table", DataTable)
            if table.row_count == 0:
                return None
            row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
            return str(row_key.value)
        except Exception:
            return None

    def get_current_resource_type(self):
        # type: () -> str
        return self._current_resource_type

    def set_filter(self, text):
        # type: (str) -> None
        """Filter rows by text (case-insensitive substring match)."""
        self._filter_text = text.lower()
        self._rebuild_table()

    def clear_filter(self):
        # type: () -> None
        self._filter_text = ""
        self._rebuild_table()

    def _update_header(self):
        # type: () -> None
        try:
            header = self.query_one("#k8s-header", Static)
        except Exception:
            return
        ctx = ""
        ns = "default"
        if self._service is not None:
            ctx = self._service.context or "default"
            ns = self._service.namespace or "default"
        header.update(
            "[bold #39c5cf]ctx:[/][#e6edf3]{}[/]  "
            "[bold #39c5cf]ns:[/][#e6edf3]{}[/]  "
            "[bold #d29922]{}[/]".format(ctx, ns, self._current_resource_type)
        )

    def _rebuild_table(self):
        # type: () -> None
        try:
            table = self.query_one("#k8s-data-table", DataTable)
        except Exception:
            return

        old_cursor = table.cursor_coordinate.row if table.row_count > 0 else 0
        table.clear(columns=True)

        for h in self._headers:
            table.add_column(h, key=h)

        for row in self._all_rows:
            if self._filter_text:
                haystack = " ".join(row).lower()
                if self._filter_text not in haystack:
                    continue
            name = row[0] if row else ""
            table.add_row(*row, key=name)

        if table.row_count > 0:
            restored = min(old_cursor, table.row_count - 1)
            table.move_cursor(row=restored)

    def focus_table(self):
        # type: () -> None
        """Focus the inner DataTable."""
        try:
            table = self.query_one("#k8s-data-table", DataTable)
            table.focus()
        except Exception:
            pass
