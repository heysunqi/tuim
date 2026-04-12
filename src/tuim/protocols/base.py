"""Abstract base class for protocol handlers."""
from abc import ABC, abstractmethod
from typing import Callable, Optional

from tuim.models import Connection, ConnectionStatus


class ProtocolHandler(ABC):
    """Base class that all protocol handlers must extend."""

    def __init__(self, connection: Connection) -> None:
        self.connection = connection
        self.is_connected = False
        self._on_output = None  # type: Optional[Callable[[str], None]]
        self._on_disconnect = None  # type: Optional[Callable[[], None]]

    @property
    @abstractmethod
    def is_interactive(self) -> bool:
        """True for TUI-internal terminal (SSH/Telnet/K8s), False for external (RDP/VNC)."""
        ...

    @abstractmethod
    async def connect(self) -> None:
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        ...

    @abstractmethod
    async def send_input(self, data: str) -> None:
        ...

    @abstractmethod
    async def check_health(self) -> ConnectionStatus:
        ...

    def on_output(self, callback: Callable[[str], None]) -> None:
        """Register a callback invoked when output data arrives."""
        self._on_output = callback

    def on_disconnect(self, callback: Callable[[], None]) -> None:
        """Register a callback invoked when the connection drops."""
        self._on_disconnect = callback

    def _emit_output(self, data: str) -> None:
        if self._on_output:
            self._on_output(data)

    def _emit_disconnect(self) -> None:
        self.is_connected = False
        if self._on_disconnect:
            self._on_disconnect()
