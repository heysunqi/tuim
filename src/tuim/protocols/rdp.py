"""RDP protocol handler — launches an external RDP client."""
import asyncio
import logging
import platform
import shutil
from typing import Optional

from tuim.models import Connection, ConnectionStatus
from tuim.protocols.base import ProtocolHandler
from tuim.i18n import t

logger = logging.getLogger(__name__)


class RDPHandler(ProtocolHandler):
    """Launches an external RDP client (non-interactive within the TUI)."""

    def __init__(self, connection: Connection) -> None:
        super().__init__(connection)
        self._process = None  # type: Optional[asyncio.subprocess.Process]

    @property
    def is_interactive(self) -> bool:
        return False

    async def connect(self) -> None:
        host = self.connection.host
        port = self.connection.port
        cfg = self.connection.rdp_config
        username = cfg.username if cfg else ""
        system = platform.system()

        try:
            if system == "Darwin":
                # macOS — use the built-in Microsoft RDP URL scheme
                rdp_url = "rdp://full%20address=s:{}:{}&username=s:{}".format(
                    host, port, username,
                )
                self._process = await asyncio.create_subprocess_exec(
                    "open", rdp_url,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )

            elif system == "Linux":
                xfreerdp = shutil.which("xfreerdp")
                rdesktop = shutil.which("rdesktop")

                if xfreerdp:
                    cmd = [
                        xfreerdp,
                        "/v:{}:{}".format(host, port),
                    ]
                    if username:
                        cmd.append("/u:{}".format(username))
                    if cfg and cfg.domain:
                        cmd.append("/d:{}".format(cfg.domain))
                    if cfg and cfg.password:
                        cmd.append("/p:{}".format(cfg.password))

                    self._process = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.DEVNULL,
                        stderr=asyncio.subprocess.DEVNULL,
                    )
                elif rdesktop:
                    cmd = [rdesktop, "-u", username or "admin", "{}:{}".format(host, port)]
                    self._process = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.DEVNULL,
                        stderr=asyncio.subprocess.DEVNULL,
                    )
                else:
                    msg = t("rdp_no_client")
                    logger.error(msg)
                    self._emit_output(msg + "\r\n")
                    self._emit_disconnect()
                    return

            else:
                msg = t("rdp_unsupported", system=system)
                logger.error(msg)
                self._emit_output(msg + "\r\n")
                self._emit_disconnect()
                return

            self.is_connected = True
            self._emit_output(
                t("rdp_launched", host=host, port=str(port))
            )
        except Exception as exc:
            msg = t("rdp_launch_failed", error=str(exc))
            logger.error(msg)
            self._emit_output(msg + "\r\n")
            self._emit_disconnect()

    async def disconnect(self) -> None:
        if self._process is not None:
            try:
                self._process.terminate()
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self._process.kill()
                await self._process.wait()
            except Exception:
                pass
            self._process = None

        self.is_connected = False

    async def send_input(self, data: str) -> None:
        # External client — input is handled by the RDP window itself.
        pass

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
