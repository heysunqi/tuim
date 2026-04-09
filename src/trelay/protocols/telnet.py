"""Telnet protocol handler using telnetlib3."""
import asyncio
import logging
from typing import Any, Optional

import telnetlib3

from trelay.models import Connection, ConnectionStatus
from trelay.protocols.base import ProtocolHandler
from trelay.i18n import t

logger = logging.getLogger(__name__)


class TelnetHandler(ProtocolHandler):
    """Handles Telnet connections via telnetlib3."""

    def __init__(self, connection: Connection) -> None:
        super().__init__(connection)
        self._reader = None  # type: Optional[Any]
        self._writer = None  # type: Optional[Any]
        self._reader_task = None  # type: Optional[asyncio.Task]

    @property
    def is_interactive(self) -> bool:
        return True

    async def connect(self) -> None:
        host = self.connection.host
        port = self.connection.port

        try:
            reader, writer = await telnetlib3.open_connection(
                host=host,
                port=port,
            )
            self._reader = reader
            self._writer = writer
            self.is_connected = True
            self._reader_task = asyncio.ensure_future(self._read_loop())
            self._emit_output(
                t("telnet_connected", host=host, port=str(port))
            )
        except Exception as exc:
            msg = t("telnet_failed", host=host, port=str(port), error=str(exc))
            logger.error(msg)
            self._emit_output(msg + "\r\n")
            self._emit_disconnect()

    async def _read_loop(self) -> None:
        """Background task that reads incoming data from the Telnet connection."""
        try:
            assert self._reader is not None
            while True:
                data = await self._reader.read(4096)
                if not data:
                    break
                self._emit_output(data)
        except Exception as exc:
            logger.debug("Telnet read loop ended: %s", exc)
        finally:
            self._emit_disconnect()

    async def disconnect(self) -> None:
        if self._reader_task is not None and not self._reader_task.done():
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass
            self._reader_task = None

        if self._writer is not None:
            try:
                self._writer.close()
            except Exception:
                pass
            self._writer = None

        self._reader = None
        self.is_connected = False

    async def send_input(self, data: str) -> None:
        if self._writer is not None:
            try:
                self._writer.write(data)
            except Exception as exc:
                logger.error("Failed to send Telnet input: %s", exc)

    async def check_health(self) -> ConnectionStatus:
        host = self.connection.host
        port = self.connection.port
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=5.0,
            )
            writer.close()
            await writer.wait_closed()
            return ConnectionStatus.ONLINE
        except Exception:
            return ConnectionStatus.OFFLINE
