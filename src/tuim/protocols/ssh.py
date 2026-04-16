"""SSH protocol handler using asyncssh."""
import asyncio
import logging
from typing import Optional

import asyncssh

from tuim.models import Connection, ConnectionStatus
from tuim.protocols.base import ProtocolHandler
from tuim.i18n import t

logger = logging.getLogger(__name__)


class SSHHandler(ProtocolHandler):
    """Handles SSH connections via asyncssh with a PTY session."""

    def __init__(self, connection: Connection) -> None:
        super().__init__(connection)
        self._jump_conn = None  # type: Optional[asyncssh.SSHClientConnection]
        self._conn = None  # type: Optional[asyncssh.SSHClientConnection]
        self._process = None  # type: Optional[asyncssh.SSHClientProcess]
        self._reader_task = None  # type: Optional[asyncio.Task]
        self._term_size = (120, 40)  # type: tuple  # (cols, rows)

    @property
    def is_interactive(self) -> bool:
        return True

    def set_term_size(self, cols, rows):
        # type: (int, int) -> None
        """Set the initial terminal size before connect()."""
        self._term_size = (cols, rows)

    async def connect(self) -> None:
        cfg = self.connection.ssh_config
        host = self.connection.host
        port = self.connection.port

        connect_kwargs = {
            "host": host,
            "port": port,
            "known_hosts": None,
        }

        if cfg is not None:
            if cfg.username:
                connect_kwargs["username"] = cfg.username
            if cfg.private_key_path:
                connect_kwargs["client_keys"] = [cfg.private_key_path]
            if cfg.password:
                connect_kwargs["password"] = cfg.password

        try:
            # If jump host is configured, establish tunnel first
            if cfg is not None and cfg.jump_host:
                jump_kwargs = {
                    "host": cfg.jump_host,
                    "port": cfg.jump_port,
                    "known_hosts": None,
                }
                if cfg.jump_username:
                    jump_kwargs["username"] = cfg.jump_username
                if cfg.jump_private_key_path:
                    jump_kwargs["client_keys"] = [cfg.jump_private_key_path]
                if cfg.jump_password:
                    jump_kwargs["password"] = cfg.jump_password
                self._emit_output(
                    t("ssh_jump_connecting", jump=cfg.jump_host) + "\r\n"
                )
                self._jump_conn = await asyncssh.connect(**jump_kwargs)
                connect_kwargs["tunnel"] = self._jump_conn

            self._conn = await asyncssh.connect(**connect_kwargs)
            self._process = await self._conn.create_process(
                term_type="xterm-256color",
                term_size=self._term_size,
            )
            self.is_connected = True
            self._reader_task = asyncio.ensure_future(self._read_loop())
            self._emit_output(
                t("ssh_connected", host=host, port=str(port))
            )
        except Exception as exc:
            msg = t("ssh_failed", host=host, port=str(port), error=str(exc))
            logger.error(msg)
            self._emit_output(msg + "\r\n")
            self._emit_disconnect()

    async def resize_terminal(self, cols, rows):
        # type: (int, int) -> None
        """Resize the remote PTY."""
        self._term_size = (cols, rows)
        if self._process is not None and not self._process.is_closing():
            try:
                self._process.change_terminal_size(cols, rows)
            except Exception as exc:
                logger.debug("Failed to resize terminal: %s", exc)

    async def _read_loop(self) -> None:
        """Background task that reads stdout from the SSH process."""
        try:
            assert self._process is not None
            while True:
                data = await self._process.stdout.read(4096)
                if not data:
                    break
                self._emit_output(data)
        except asyncssh.BreakReceived:
            pass
        except asyncssh.SignalReceived:
            pass
        except Exception as exc:
            logger.debug("SSH read loop ended: %s", exc)
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

        if self._process is not None:
            try:
                self._process.close()
            except Exception:
                pass
            self._process = None

        if self._conn is not None:
            try:
                self._conn.close()
                await self._conn.wait_closed()
            except Exception:
                pass
            self._conn = None

        if self._jump_conn is not None:
            try:
                self._jump_conn.close()
                await self._jump_conn.wait_closed()
            except Exception:
                pass
            self._jump_conn = None

        self.is_connected = False

    async def send_input(self, data: str) -> None:
        if self._process is not None and not self._process.is_closing():
            try:
                self._process.stdin.write(data)
            except Exception as exc:
                logger.error("Failed to send SSH input: %s", exc)

    async def check_health(self) -> ConnectionStatus:
        cfg = self.connection.ssh_config
        if cfg and cfg.jump_host:
            host = cfg.jump_host
            port = cfg.jump_port
        else:
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
