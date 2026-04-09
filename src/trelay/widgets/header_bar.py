"""Header bar widget for the Trelay TUI."""
from __future__ import annotations

import unicodedata

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widget import Widget
from textual.widgets import Static

from trelay.i18n import t


def _display_width(s):
    # type: (str) -> int
    """Calculate the terminal display width of a string (CJK chars count as 2)."""
    w = 0
    for ch in s:
        if unicodedata.east_asian_width(ch) in ("W", "F"):
            w += 2
        else:
            w += 1
    return w


def _build_shortcuts(rows):
    # type: (list) -> str
    """Render shortcut rows into a Rich markup string with column-aligned items.

    Each item is padded to a uniform column width so that items in the
    same column across different rows are aligned, even when CJK
    characters are present (which occupy 2 terminal columns).
    """
    # 1) Find the maximum visible width across all items
    max_w = 0
    for row in rows:
        for key, label_key in row:
            label = t(label_key)
            # visible width: "[" + key + "] " + label
            w = 1 + len(key) + 2 + _display_width(label)
            if w > max_w:
                max_w = w
    col_w = max_w + 2  # add spacing between columns

    # 2) Format each item, padding to col_w
    lines = []
    for row in rows:
        parts = []
        for key, label_key in row:
            label = t(label_key)
            visible_w = 1 + len(key) + 2 + _display_width(label)
            pad = " " * max(0, col_w - visible_w)
            parts.append("\\[[#6e7681]{}[/]] {}{}".format(key, label, pad))
        lines.append("".join(parts))
    return "[dim #8b949e]" + "\n".join(lines) + "[/]"


class HeaderBar(Widget):
    """Top header bar with logo and keyboard shortcut hints."""

    _LIST_ROWS = [
        [("↑↓", "nav"), ("Enter", "connect"), ("Ctrl+D", "disconnect_btn"), ("a", "add")],
        [("e", "edit"), ("d", "delete_btn"), ("/", "search"), (":q", "quit")],
    ]

    _K8S_ROWS = [
        [("j/k", "nav"), ("Enter", "exec"), (":pod", "pods"), (":svc", "services")],
        [(":deploy", "deployments"), (":ns", "namespaces"), (":q", "back"), (":q!", "quit_force")],
    ]

    def __init__(self, **kwargs):
        # type: (...) -> None
        super().__init__(id="header-bar", **kwargs)

    def compose(self):
        # type: () -> ComposeResult
        with Horizontal():
            yield Static(
                "[bold #39c5cf]⬡ Trelay[/]",
                id="header-info",
                markup=True,
            )
            yield Static(
                _build_shortcuts(self._LIST_ROWS),
                id="header-shortcuts",
                markup=True,
            )

    def set_k8s_mode(self):
        # type: () -> None
        try:
            shortcuts = self.query_one("#header-shortcuts", Static)
            shortcuts.update(_build_shortcuts(self._K8S_ROWS))
        except Exception:
            pass

    def set_list_mode(self):
        # type: () -> None
        try:
            shortcuts = self.query_one("#header-shortcuts", Static)
            shortcuts.update(_build_shortcuts(self._LIST_ROWS))
        except Exception:
            pass
