"""Session lifecycle manager for Trelay."""
from typing import Callable, Optional

from trelay.models import Connection, Protocol
from trelay.i18n import t


class SessionManager:
    """Manages a single active remote session at a time.

    Creates the appropriate protocol handler based on connection type,
    handles connect/disconnect lifecycle, and routes input/output.
    """

    def __init__(self):
        # type: () -> None
        self._handler = None  # type: Optional[object]
        self._connection = None  # type: Optional[Connection]

    @property
    def current_connection(self):
        # type: () -> Optional[Connection]
        """Return the currently active connection, or None."""
        return self._connection

    @property
    def current_handler(self):
        # type: () -> Optional[object]
        """Return the currently active protocol handler, or None."""
        return self._handler

    @property
    def is_connected(self):
        # type: () -> bool
        """Return True if there is an active, connected session."""
        return self._handler is not None and self._handler.is_connected

    def _create_handler(self, connection):
        # type: (Connection) -> object
        """Instantiate the correct ProtocolHandler for the given connection.

        Imports are deferred to avoid circular import issues and to
        allow protocol modules to be loaded only when needed.
        """
        from trelay.protocols.ssh import SSHHandler
        from trelay.protocols.rdp import RDPHandler
        from trelay.protocols.vnc import VNCHandler
        from trelay.protocols.telnet import TelnetHandler
        from trelay.protocols.k8s import K8sHandler

        handlers = {
            Protocol.SSH: SSHHandler,
            Protocol.RDP: RDPHandler,
            Protocol.VNC: VNCHandler,
            Protocol.TELNET: TelnetHandler,
            Protocol.K8S: K8sHandler,
        }
        handler_cls = handlers.get(connection.protocol)
        if handler_cls is None:
            raise ValueError(t("err_unsupported_protocol", proto=str(connection.protocol)))
        return handler_cls(connection)

    async def connect(self, connection, on_output, on_disconnect, term_size=None, override_command=None):
        # type: (Connection, Callable, Callable, object, object) -> object
        """Connect to a remote host using the appropriate protocol handler.

        If already connected, disconnects the current session first.

        Args:
            connection: The Connection to establish.
            on_output: Callback invoked with output data (str) from the
                remote session.
            on_disconnect: Callback invoked when the session ends
                unexpectedly.
            term_size: Optional (cols, rows) tuple for terminal dimensions.
            override_command: Optional list of strings to override the default
                command (e.g. for kubectl get/edit/logs).

        Returns:
            The ProtocolHandler instance that is now connected.
        """
        if self._handler is not None and self._handler.is_connected:
            await self.disconnect()

        self._connection = connection
        self._handler = self._create_handler(connection)
        self._handler.on_output(on_output)
        self._handler.on_disconnect(on_disconnect)
        # Pass terminal size to handlers that support it
        if term_size is not None and hasattr(self._handler, 'set_term_size'):
            self._handler.set_term_size(*term_size)
        if override_command is not None and hasattr(self._handler, 'set_override_command'):
            self._handler.set_override_command(override_command)
        await self._handler.connect()
        return self._handler

    async def disconnect(self):
        # type: () -> None
        """Disconnect the current session, if any."""
        if self._handler is not None:
            try:
                await self._handler.disconnect()
            except Exception:
                pass
            self._handler = None
            self._connection = None

    async def send_input(self, data):
        # type: (str) -> None
        """Send user input to the active session.

        Does nothing if no session is active or connected.
        """
        if self._handler is not None and self._handler.is_connected:
            await self._handler.send_input(data)

    async def resize_terminal(self, cols, rows):
        # type: (int, int) -> None
        """Resize the remote terminal, if the handler supports it."""
        if self._handler is not None and hasattr(self._handler, 'resize_terminal'):
            await self._handler.resize_terminal(cols, rows)
