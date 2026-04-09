"""Async health checker service for Trelay connections."""
import asyncio
from typing import Callable, List, Optional

from trelay.models import Connection, ConnectionStatus, Protocol


class HealthChecker:
    """Periodically checks connection health via TCP reachability."""

    def __init__(
        self,
        connections,  # type: List[Connection]
        interval=30,  # type: int
        on_update=None,  # type: Optional[Callable[[str, ConnectionStatus], None]]
    ):
        # type: (...) -> None
        self.connections = connections
        self.interval = interval
        self.on_update = on_update
        self._task = None  # type: Optional[asyncio.Task]

    async def check_one(self, conn):
        # type: (Connection) -> ConnectionStatus
        """Check a single connection's health via TCP connect.

        Skips K8s connections and connections without a valid host/port.
        Returns ConnectionStatus indicating reachability.
        """
        if conn.protocol == Protocol.K8S or not conn.host or conn.port == 0:
            return ConnectionStatus.UNKNOWN
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(conn.host, conn.port), timeout=5
            )
            writer.close()
            await writer.wait_closed()
            return ConnectionStatus.ONLINE
        except (asyncio.TimeoutError, OSError, ConnectionRefusedError, Exception):
            return ConnectionStatus.OFFLINE

    async def check_all(self):
        # type: () -> None
        """Run a single health check pass across all connections."""
        for conn in self.connections:
            try:
                status = await self.check_one(conn)
                if self.on_update is not None:
                    self.on_update(conn.name, status)
            except Exception:
                pass

    async def _run(self):
        # type: () -> None
        """Internal loop that periodically checks all connections."""
        while True:
            await self.check_all()
            await asyncio.sleep(self.interval)

    def start(self):
        # type: () -> None
        """Start the periodic health check task."""
        if self._task is None:
            self._task = asyncio.ensure_future(self._run())

    def stop(self):
        # type: () -> None
        """Stop the periodic health check task."""
        if self._task is not None:
            self._task.cancel()
            self._task = None

    def update_connections(self, connections):
        # type: (List[Connection]) -> None
        """Replace the list of connections to monitor."""
        self.connections = connections
