"""Async health checker service for Tuim connections."""
import asyncio
from typing import Callable, List, Optional

from tuim.models import Connection, ConnectionStatus, Protocol


class HealthChecker:
    """Periodically checks connection health via TCP or kubectl reachability."""

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

    async def _check_k8s(self, conn):
        # type: (Connection) -> ConnectionStatus
        """Check a K8s connection via kubectl."""
        cfg = conn.k8s_config
        if cfg is None:
            return ConnectionStatus.UNKNOWN
        auth_args = cfg.kubectl_auth_args(conn.host, conn.port)
        if cfg.pod:
            cmd = ["kubectl"] + auth_args + ["get", "pod", cfg.pod]
            if cfg.namespace:
                cmd.extend(["-n", cfg.namespace])
            cmd.extend(["-o", "jsonpath={.status.phase}"])
        else:
            cmd = ["kubectl"] + auth_args + ["cluster-info"]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10.0)
            if cfg.pod:
                phase = stdout.decode("utf-8", errors="replace").strip()
                return ConnectionStatus.ONLINE if phase == "Running" else ConnectionStatus.OFFLINE
            else:
                return ConnectionStatus.ONLINE if proc.returncode == 0 else ConnectionStatus.OFFLINE
        except asyncio.TimeoutError:
            return ConnectionStatus.ERROR
        except Exception:
            return ConnectionStatus.ERROR

    async def check_one(self, conn):
        # type: (Connection) -> ConnectionStatus
        """Check a single connection's health."""
        if conn.protocol == Protocol.K8S:
            return await self._check_k8s(conn)
        if not conn.host or conn.port == 0:
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
        """Run a single health check pass across all connections concurrently."""
        async def _check(conn):
            # type: (Connection) -> None
            try:
                status = await self.check_one(conn)
                if self.on_update is not None:
                    self.on_update(conn.name, status)
            except Exception:
                pass

        await asyncio.gather(*[_check(c) for c in self.connections])

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
