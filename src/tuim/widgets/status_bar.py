"""Status bar widget for the Tuim TUI."""
from __future__ import annotations

from typing import Optional

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widget import Widget
from textual.widgets import Static

from tuim.i18n import t


class StatusBar(Widget):
    """Bottom status bar showing connection info, duration, and mode."""

    def __init__(self, **kwargs):
        # type: (...) -> None
        super().__init__(id="status-bar", **kwargs)
        self._elapsed_seconds = 0
        self._timer = None  # type: Optional[object]
        self._mode = t("mode_list")

    def compose(self):
        # type: () -> ComposeResult
        with Horizontal():
            yield Static("", id="status-name")
            yield Static("", id="status-sep-1", classes="status-sep")
            yield Static("", id="status-protocol")
            yield Static("", id="status-sep-2", classes="status-sep")
            yield Static("", id="status-duration")
            yield Static("", id="status-sep-3", classes="status-sep")
            yield Static("", id="status-host")
            yield Static(" | ", classes="status-sep")
            yield Static(self._mode, id="status-mode")

    def update_connection(self, name, protocol, host, port):
        # type: (str, str, str, int) -> None
        try:
            self.query_one("#status-name", Static).update(name)
            self.query_one("#status-protocol", Static).update(protocol)
            host_str = "{}:{}".format(host, port) if host else ""
            self.query_one("#status-host", Static).update(host_str)
            # Show/hide separators based on whether we have connection info
            if name:
                self.query_one("#status-sep-1", Static).update(" | ")
                self.query_one("#status-sep-2", Static).update(" | ")
                self.query_one("#status-sep-3", Static).update(" | ")
            else:
                self.query_one("#status-sep-1", Static).update("")
                self.query_one("#status-sep-2", Static).update("")
                self.query_one("#status-sep-3", Static).update("")
        except Exception:
            pass

    def update_mode(self, mode):
        # type: (str) -> None
        self._mode = mode
        try:
            self.query_one("#status-mode", Static).update(mode)
        except Exception:
            pass

    def start_timer(self):
        # type: () -> None
        self.stop_timer()
        self._elapsed_seconds = 0
        self._update_duration_display()
        self._timer = self.set_interval(1.0, self._tick)

    def stop_timer(self):
        # type: () -> None
        if self._timer is not None:
            self._timer.stop()
            self._timer = None
        # Clear duration display when not connected
        try:
            self.query_one("#status-duration", Static).update("")
        except Exception:
            pass

    def _tick(self):
        # type: () -> None
        self._elapsed_seconds += 1
        self._update_duration_display()

    def _update_duration_display(self):
        # type: () -> None
        h = self._elapsed_seconds // 3600
        m = (self._elapsed_seconds % 3600) // 60
        s = self._elapsed_seconds % 60
        try:
            self.query_one("#status-duration", Static).update(
                "{:02d}:{:02d}:{:02d}".format(h, m, s)
            )
        except Exception:
            pass
