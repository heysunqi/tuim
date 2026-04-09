"""VNC protocol handler — launches an external VNC client."""
import asyncio
import logging
import platform
import shutil
from typing import Optional

from trelay.models import Connection, ConnectionStatus
from trelay.protocols.base import ProtocolHandler
from trelay.i18n import t

logger = logging.getLogger(__name__)


class VNCHandler(ProtocolHandler):
    """Launches an external VNC client (non-interactive within the TUI)."""

    def __init__(self, connection: Connection) -> None:
        super().__init__(connection)
        self._process = None  # type: Optional[asyncio.subprocess.Process]

    @property
    def is_interactive(self) -> bool:
        return False

    async def connect(self) -> None:
        host = self.connection.host
        port = self.connection.port
        cfg = self.connection.vnc_config
        system = platform.system()

        try:
            if system == "Darwin":
                # macOS — use the built-in Screen Sharing via vnc:// URL
                vnc_url = "vnc://{}:{}".format(host, port)
                self._process = await asyncio.create_subprocess_exec(
                    "open", vnc_url,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )

            elif system == "Linux":
                vncviewer = shutil.which("vncviewer")

                if vncviewer:
                    cmd = [vncviewer, "{}::{}".format(host, port)]
                    if cfg and cfg.password:
                        cmd.extend(["-passwd", cfg.password])

                    self._process = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.DEVNULL,
                        stderr=asyncio.subprocess.DEVNULL,
                    )
                else:
                    msg = t("vnc_no_client")
                    logger.error(msg)
                    self._emit_output(msg + "\r\n")
                    self._emit_disconnect()
                    return

            else:
                msg = t("vnc_unsupported", system=system)
                logger.error(msg)
                self._emit_output(msg + "\r\n")
                self._emit_disconnect()
                return

            self.is_connected = True
            self._emit_output(
                t("vnc_launched", host=host, port=str(port))
            )
        except Exception as exc:
            msg = t("vnc_launch_failed", error=str(exc))
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
        # External client — input is handled by the VNC window itself.
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
