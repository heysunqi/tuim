"""Helper functions to render protocol badges and status indicators as Rich Text."""
from __future__ import annotations

from rich.text import Text

from trelay.models import (
    ConnectionStatus,
    Protocol,
    PROTOCOL_COLORS,
    STATUS_COLORS,
)


def render_protocol_badge(protocol: Protocol) -> Text:
    """Render a colored protocol badge like [SSH] with protocol-specific color."""
    color = PROTOCOL_COLORS.get(protocol, "#8b949e")
    text = Text(protocol.value.upper(), style="bold " + color)
    return text


def render_status_indicator(status: ConnectionStatus) -> Text:
    """Render status as colored dot: online=green, offline=gray, error=red, unknown=gray."""
    color = STATUS_COLORS.get(status, "#6e7681")
    if status == ConnectionStatus.ERROR:
        return Text("\u25cf", style="bold " + color)
    else:
        return Text("\u25cf", style=color)
