"""Kubernetes protocol handler using kubectl subprocess with PTY."""
import asyncio
import fcntl
import logging
import os
import pty
import shutil
import struct
import termios
import time
from typing import List, Optional

from trelay.models import Connection, ConnectionStatus
from trelay.protocols.base import ProtocolHandler
from trelay.i18n import t

logger = logging.getLogger(__name__)


class K8sHandler(ProtocolHandler):
    """Handles Kubernetes pod exec sessions via kubectl subprocess with PTY."""

    def __init__(self, connection: Connection) -> None:
        super().__init__(connection)
        self._pid = None  # type: Optional[int]
        self._master_fd = None  # type: Optional[int]
        self._reader_task = None  # type: Optional[asyncio.Task]
        self._term_size = (120, 40)  # (cols, rows)
        self._connect_time = None  # type: Optional[float]
        self._exit_status = None  # type: Optional[int]

    @property
    def is_interactive(self) -> bool:
        return True

    @property
    def was_quick_failure(self) -> bool:
        """True if the subprocess exited quickly with a non-zero status."""
        if self._connect_time is None or self._exit_status is None:
            return False
        elapsed = time.monotonic() - self._connect_time
        return elapsed < 3.0 and self._exit_status != 0

    def set_term_size(self, cols, rows):
        # type: (int, int) -> None
        self._term_size = (cols, rows)

    def _build_exec_command(self) -> List[str]:
        """Build the kubectl exec command from connection config."""
        cfg = self.connection.k8s_config
        if cfg is None:
            raise ValueError("K8sConfig is required for K8s connections")

        cmd = ["kubectl"]
        if cfg.kubeconfig:
            cmd.extend(["--kubeconfig", os.path.expanduser(cfg.kubeconfig)])
        if cfg.context:
            cmd.extend(["--context", cfg.context])
        if cfg.namespace:
            cmd.extend(["-n", cfg.namespace])

        cmd.extend(["exec", "-it", cfg.pod])

        if cfg.container:
            cmd.extend(["-c", cfg.container])

        cmd.append("--")
        cmd.append(cfg.command or "/bin/sh")
        return cmd

    def _set_pty_size(self, fd, cols, rows):
        # type: (int, int, int) -> None
        """Set the terminal size on a PTY file descriptor."""
        try:
            winsize = struct.pack("HHHH", rows, cols, 0, 0)
            fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)
        except Exception as exc:
            logger.debug("Failed to set PTY size: %s", exc)

    async def resize_terminal(self, cols, rows):
        # type: (int, int) -> None
        """Resize the PTY."""
        self._term_size = (cols, rows)
        if self._master_fd is not None:
            self._set_pty_size(self._master_fd, cols, rows)

    async def connect(self) -> None:
        self._connect_time = time.monotonic()
        self._exit_status = None
        kubectl_path = shutil.which("kubectl")
        if kubectl_path is None:
            msg = t("k8s_kubectl_not_found")
            logger.error(msg)
            self._emit_output(msg + "\r\n")
            self._emit_disconnect()
            return

        try:
            cmd = self._build_exec_command()

            # Create a PTY pair so kubectl sees a real terminal
            master_fd, slave_fd = pty.openpty()
            self._master_fd = master_fd

            # Set initial terminal size
            cols, rows = self._term_size
            self._set_pty_size(master_fd, cols, rows)

            # Fork the kubectl process with the slave PTY as its terminal
            pid = os.fork()
            if pid == 0:
                # Child process
                os.close(master_fd)
                os.setsid()
                # Set slave as controlling terminal
                fcntl.ioctl(slave_fd, termios.TIOCSCTTY, 0)
                os.dup2(slave_fd, 0)
                os.dup2(slave_fd, 1)
                os.dup2(slave_fd, 2)
                if slave_fd > 2:
                    os.close(slave_fd)
                os.execvp(cmd[0], cmd)
                os._exit(1)
            else:
                # Parent process
                os.close(slave_fd)
                self._pid = pid
                self.is_connected = True

                # Keep master_fd in blocking mode — reads happen in
                # a thread executor, so blocking is correct here.
                self._reader_task = asyncio.ensure_future(self._read_loop())

                cfg = self.connection.k8s_config
                label = "{}:{}".format(
                    cfg.namespace if cfg else "default",
                    cfg.pod if cfg else "unknown",
                )
                self._emit_output(
                    t("k8s_connected", label=label)
                )
        except Exception as exc:
            msg = t("k8s_exec_failed", error=str(exc))
            logger.error(msg)
            self._emit_output(msg + "\r\n")
            self._emit_disconnect()

    async def _read_loop(self) -> None:
        """Background task that reads from the PTY master fd."""
        loop = asyncio.get_event_loop()
        try:
            while True:
                data = await loop.run_in_executor(None, self._blocking_read)
                if data is None:
                    break
                self._emit_output(data)
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.debug("K8s read loop ended: %s", exc)
        finally:
            # Try to collect exit status from the child process
            if self._pid is not None:
                try:
                    pid_result, status = os.waitpid(self._pid, os.WNOHANG)
                    if pid_result != 0:
                        if os.WIFEXITED(status):
                            self._exit_status = os.WEXITSTATUS(status)
                        else:
                            self._exit_status = -1
                except ChildProcessError:
                    pass
                except Exception:
                    pass
            self.is_connected = False
            self._emit_disconnect()

    def _blocking_read(self):
        # type: () -> Optional[str]
        """Blocking read from the PTY master fd. Returns None on EOF/error."""
        if self._master_fd is None:
            return None
        try:
            data = os.read(self._master_fd, 4096)
            if not data:
                return None
            return data.decode("utf-8", errors="replace")
        except OSError:
            return None

    async def disconnect(self) -> None:
        if self._reader_task is not None and not self._reader_task.done():
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass
            self._reader_task = None

        if self._pid is not None:
            try:
                os.kill(self._pid, 15)  # SIGTERM
                # Wait for the child to exit
                await asyncio.get_event_loop().run_in_executor(
                    None, lambda: os.waitpid(self._pid, 0)
                )
            except ChildProcessError:
                pass
            except Exception:
                try:
                    os.kill(self._pid, 9)  # SIGKILL
                    os.waitpid(self._pid, 0)
                except Exception:
                    pass
            self._pid = None

        if self._master_fd is not None:
            try:
                os.close(self._master_fd)
            except Exception:
                pass
            self._master_fd = None

        self.is_connected = False

    async def send_input(self, data: str) -> None:
        if self._master_fd is not None and self.is_connected:
            try:
                os.write(self._master_fd, data.encode("utf-8"))
            except Exception as exc:
                logger.error("Failed to send K8s input: %s", exc)

    async def check_health(self) -> ConnectionStatus:
        cfg = self.connection.k8s_config
        if cfg is None:
            return ConnectionStatus.ERROR

        if cfg.pod:
            cmd = ["kubectl", "get", "pod", cfg.pod]
            if cfg.namespace:
                cmd.extend(["-n", cfg.namespace])
            if cfg.context:
                cmd.extend(["--context", cfg.context])
            if cfg.kubeconfig:
                cmd.extend(["--kubeconfig", os.path.expanduser(cfg.kubeconfig)])
            cmd.extend(["-o", "jsonpath={.status.phase}"])
        else:
            # No pod specified — do a cluster-level health check
            cmd = ["kubectl", "cluster-info"]
            if cfg.context:
                cmd.extend(["--context", cfg.context])
            if cfg.kubeconfig:
                cmd.extend(["--kubeconfig", os.path.expanduser(cfg.kubeconfig)])

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10.0)
            if cfg.pod:
                phase = stdout.decode("utf-8", errors="replace").strip()
                if phase == "Running":
                    return ConnectionStatus.ONLINE
                else:
                    return ConnectionStatus.OFFLINE
            else:
                if proc.returncode == 0:
                    return ConnectionStatus.ONLINE
                else:
                    return ConnectionStatus.OFFLINE
        except asyncio.TimeoutError:
            return ConnectionStatus.ERROR
        except Exception:
            return ConnectionStatus.ERROR
