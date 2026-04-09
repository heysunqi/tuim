"""Trelay widgets package."""
from trelay.widgets.protocol_badge import render_protocol_badge, render_status_indicator
from trelay.widgets.header_bar import HeaderBar
from trelay.widgets.connection_table import ConnectionTable
from trelay.widgets.terminal_view import TerminalView
from trelay.widgets.status_bar import StatusBar

__all__ = [
    "render_protocol_badge",
    "render_status_indicator",
    "HeaderBar",
    "ConnectionTable",
    "TerminalView",
    "StatusBar",
]
