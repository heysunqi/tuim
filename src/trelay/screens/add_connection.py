"""Screen for adding or editing a connection."""
from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select, Static

from trelay.models import (
    Connection,
    DEFAULT_PORTS,
    K8sConfig,
    Protocol,
    RDPConfig,
    SSHConfig,
    TelnetConfig,
    VNCConfig,
)


# Protocol choices for the Select widget
PROTOCOL_CHOICES = [
    ("SSH", Protocol.SSH.value),
    ("RDP", Protocol.RDP.value),
    ("VNC", Protocol.VNC.value),
    ("Telnet", Protocol.TELNET.value),
    ("Kubernetes", Protocol.K8S.value),
]


class AddConnectionScreen(ModalScreen[Optional[Connection]]):
    """Modal screen for adding or editing a connection.

    If an existing connection is passed, the form is pre-populated
    for editing.  Dismisses with a Connection object on save, or
    None on cancel.
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False),
    ]

    DEFAULT_CSS = """
    AddConnectionScreen {
        align: center middle;
    }

    AddConnectionScreen > Vertical {
        width: 72;
        max-height: 90%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }

    AddConnectionScreen #form-title {
        text-align: center;
        text-style: bold;
        color: $text;
        width: 100%;
        margin-bottom: 1;
    }

    AddConnectionScreen .form-group {
        width: 100%;
        height: auto;
        margin-bottom: 1;
    }

    AddConnectionScreen .form-group Label {
        margin-bottom: 0;
        color: $text-muted;
    }

    AddConnectionScreen .form-group Input {
        width: 100%;
    }

    AddConnectionScreen .form-group Select {
        width: 100%;
    }

    AddConnectionScreen .protocol-fields {
        width: 100%;
        height: auto;
    }

    AddConnectionScreen .button-row {
        width: 100%;
        height: 3;
        align: center middle;
        margin-top: 1;
    }

    AddConnectionScreen .button-row Button {
        margin: 0 2;
    }

    AddConnectionScreen .hidden {
        display: none;
    }
    """

    def __init__(self, connection=None):
        # type: (Optional[Connection]) -> None
        super().__init__()
        self.editing_connection = connection
        self._is_editing = connection is not None

    def compose(self):
        # type: () -> ComposeResult
        title = "Edit Connection" if self._is_editing else "Add Connection"
        conn = self.editing_connection

        # Determine initial values
        initial_name = conn.name if conn else ""
        initial_host = conn.host if conn else ""
        initial_protocol = conn.protocol.value if conn else Protocol.SSH.value
        initial_port = str(conn.port) if conn else str(DEFAULT_PORTS[Protocol.SSH])
        initial_desc = conn.description if conn else ""

        with Vertical():
            yield Static(title, id="form-title")

            with VerticalScroll():
                # Common fields
                with Vertical(classes="form-group"):
                    yield Label("Name *")
                    yield Input(
                        value=initial_name,
                        placeholder="My Server",
                        id="field-name",
                    )

                with Vertical(classes="form-group"):
                    yield Label("Host *")
                    yield Input(
                        value=initial_host,
                        placeholder="192.168.1.100 or hostname",
                        id="field-host",
                    )

                with Vertical(classes="form-group"):
                    yield Label("Protocol")
                    yield Select(
                        options=PROTOCOL_CHOICES,
                        value=initial_protocol,
                        id="field-protocol",
                    )

                with Vertical(classes="form-group"):
                    yield Label("Port")
                    yield Input(
                        value=initial_port,
                        placeholder="22",
                        id="field-port",
                    )

                with Vertical(classes="form-group"):
                    yield Label("Description")
                    yield Input(
                        value=initial_desc,
                        placeholder="Optional description",
                        id="field-description",
                    )

                # --- SSH fields ---
                with Vertical(id="ssh-fields", classes="protocol-fields"):
                    with Vertical(classes="form-group"):
                        yield Label("Username")
                        yield Input(
                            value=self._get_ssh_val("username"),
                            placeholder="root",
                            id="field-ssh-username",
                        )
                    with Vertical(classes="form-group"):
                        yield Label("Password")
                        yield Input(
                            value=self._get_ssh_val("password"),
                            placeholder="(leave blank for key auth)",
                            password=True,
                            id="field-ssh-password",
                        )
                    with Vertical(classes="form-group"):
                        yield Label("Private Key Path")
                        yield Input(
                            value=self._get_ssh_val("private_key_path"),
                            placeholder="~/.ssh/id_rsa",
                            id="field-ssh-key",
                        )

                # --- RDP fields ---
                with Vertical(id="rdp-fields", classes="protocol-fields hidden"):
                    with Vertical(classes="form-group"):
                        yield Label("Username")
                        yield Input(
                            value=self._get_rdp_val("username"),
                            placeholder="Administrator",
                            id="field-rdp-username",
                        )
                    with Vertical(classes="form-group"):
                        yield Label("Password")
                        yield Input(
                            value=self._get_rdp_val("password"),
                            placeholder="Password",
                            password=True,
                            id="field-rdp-password",
                        )
                    with Vertical(classes="form-group"):
                        yield Label("Domain")
                        yield Input(
                            value=self._get_rdp_val("domain"),
                            placeholder="WORKGROUP",
                            id="field-rdp-domain",
                        )

                # --- VNC fields ---
                with Vertical(id="vnc-fields", classes="protocol-fields hidden"):
                    with Vertical(classes="form-group"):
                        yield Label("Password")
                        yield Input(
                            value=self._get_vnc_val("password"),
                            placeholder="VNC password",
                            password=True,
                            id="field-vnc-password",
                        )

                # --- Telnet fields ---
                with Vertical(
                    id="telnet-fields", classes="protocol-fields hidden"
                ):
                    with Vertical(classes="form-group"):
                        yield Label("Username")
                        yield Input(
                            value=self._get_telnet_val("username"),
                            placeholder="Username",
                            id="field-telnet-username",
                        )
                    with Vertical(classes="form-group"):
                        yield Label("Password")
                        yield Input(
                            value=self._get_telnet_val("password"),
                            placeholder="Password",
                            password=True,
                            id="field-telnet-password",
                        )

                # --- K8s fields ---
                with Vertical(id="k8s-fields", classes="protocol-fields hidden"):
                    with Vertical(classes="form-group"):
                        yield Label("Context")
                        yield Input(
                            value=self._get_k8s_val("context"),
                            placeholder="kubectl context (blank = current)",
                            id="field-k8s-context",
                        )
                    with Vertical(classes="form-group"):
                        yield Label("Namespace")
                        yield Input(
                            value=self._get_k8s_val("namespace", "default"),
                            placeholder="default",
                            id="field-k8s-namespace",
                        )
                    with Vertical(classes="form-group"):
                        yield Label("Pod")
                        yield Input(
                            value=self._get_k8s_val("pod"),
                            placeholder="pod-name-xxxx",
                            id="field-k8s-pod",
                        )
                    with Vertical(classes="form-group"):
                        yield Label("Container")
                        yield Input(
                            value=self._get_k8s_val("container"),
                            placeholder="(optional, blank = default)",
                            id="field-k8s-container",
                        )
                    with Vertical(classes="form-group"):
                        yield Label("Command")
                        yield Input(
                            value=self._get_k8s_val("command", "/bin/sh"),
                            placeholder="/bin/sh",
                            id="field-k8s-command",
                        )

            # Buttons
            with Center():
                with Horizontal(classes="button-row"):
                    yield Button("Cancel", variant="default", id="cancel-btn")
                    yield Button("Save", variant="primary", id="save-btn")

    def on_mount(self):
        # type: () -> None
        """Show the correct protocol fields on mount."""
        if self._is_editing:
            self._show_protocol_fields(self.editing_connection.protocol.value)

    # ---- helpers for pre-populating fields ----

    def _get_ssh_val(self, attr, default=""):
        # type: (str, str) -> str
        conn = self.editing_connection
        if conn and conn.ssh_config:
            return getattr(conn.ssh_config, attr, default) or default
        return default

    def _get_rdp_val(self, attr, default=""):
        # type: (str, str) -> str
        conn = self.editing_connection
        if conn and conn.rdp_config:
            return getattr(conn.rdp_config, attr, default) or default
        return default

    def _get_vnc_val(self, attr, default=""):
        # type: (str, str) -> str
        conn = self.editing_connection
        if conn and conn.vnc_config:
            return getattr(conn.vnc_config, attr, default) or default
        return default

    def _get_telnet_val(self, attr, default=""):
        # type: (str, str) -> str
        conn = self.editing_connection
        if conn and conn.telnet_config:
            return getattr(conn.telnet_config, attr, default) or default
        return default

    def _get_k8s_val(self, attr, default=""):
        # type: (str, str) -> str
        conn = self.editing_connection
        if conn and conn.k8s_config:
            return getattr(conn.k8s_config, attr, default) or default
        return default

    # ---- protocol field visibility ----

    def _show_protocol_fields(self, protocol_value):
        # type: (str) -> None
        """Show only the fields relevant to the selected protocol."""
        field_map = {
            Protocol.SSH.value: "ssh-fields",
            Protocol.RDP.value: "rdp-fields",
            Protocol.VNC.value: "vnc-fields",
            Protocol.TELNET.value: "telnet-fields",
            Protocol.K8S.value: "k8s-fields",
        }
        for proto_val, field_id in field_map.items():
            try:
                widget = self.query_one("#{}".format(field_id))
                if proto_val == protocol_value:
                    widget.remove_class("hidden")
                else:
                    widget.add_class("hidden")
            except Exception:
                pass

    def on_select_changed(self, event):
        # type: (Select.Changed) -> None
        """When protocol changes, update port and visible fields."""
        if event.select.id != "field-protocol":
            return

        protocol_value = event.value
        if protocol_value is None or protocol_value == Select.BLANK:
            return

        # Auto-fill port with protocol default
        try:
            protocol = Protocol(protocol_value)
            default_port = DEFAULT_PORTS.get(protocol, 0)
            port_input = self.query_one("#field-port", Input)
            port_input.value = str(default_port)
        except (ValueError, Exception):
            pass

        # Toggle protocol-specific field visibility
        self._show_protocol_fields(protocol_value)

    def on_button_pressed(self, event):
        # type: (Button.Pressed) -> None
        if event.button.id == "save-btn":
            self._save()
        elif event.button.id == "cancel-btn":
            self.dismiss(None)

    def action_cancel(self):
        # type: () -> None
        self.dismiss(None)

    def _save(self):
        # type: () -> None
        """Validate form inputs and construct a Connection object."""
        name = self.query_one("#field-name", Input).value.strip()
        host = self.query_one("#field-host", Input).value.strip()
        protocol_select = self.query_one("#field-protocol", Select)
        protocol_value = protocol_select.value
        port_str = self.query_one("#field-port", Input).value.strip()
        description = self.query_one("#field-description", Input).value.strip()

        # Validate required fields
        if not name:
            self.notify("Name is required.", severity="error")
            self.query_one("#field-name", Input).focus()
            return

        if protocol_value is None or protocol_value == Select.BLANK:
            self.notify("Please select a protocol.", severity="error")
            return

        try:
            protocol = Protocol(protocol_value)
        except ValueError:
            self.notify("Invalid protocol selected.", severity="error")
            return

        # Host is required for non-K8s protocols
        if protocol != Protocol.K8S and not host:
            self.notify("Host is required for {} connections.".format(
                protocol.value.upper()
            ), severity="error")
            self.query_one("#field-host", Input).focus()
            return

        # Parse port
        try:
            port = int(port_str) if port_str else DEFAULT_PORTS.get(protocol, 0)
        except ValueError:
            self.notify("Port must be a number.", severity="error")
            self.query_one("#field-port", Input).focus()
            return

        # Build protocol-specific config
        ssh_config = None
        rdp_config = None
        vnc_config = None
        telnet_config = None
        k8s_config = None

        if protocol == Protocol.SSH:
            ssh_config = SSHConfig(
                username=self.query_one("#field-ssh-username", Input).value.strip(),
                password=self.query_one("#field-ssh-password", Input).value,
                private_key_path=self.query_one("#field-ssh-key", Input).value.strip(),
            )
        elif protocol == Protocol.RDP:
            rdp_config = RDPConfig(
                username=self.query_one("#field-rdp-username", Input).value.strip(),
                password=self.query_one("#field-rdp-password", Input).value,
                domain=self.query_one("#field-rdp-domain", Input).value.strip(),
            )
        elif protocol == Protocol.VNC:
            vnc_config = VNCConfig(
                password=self.query_one("#field-vnc-password", Input).value,
            )
        elif protocol == Protocol.TELNET:
            telnet_config = TelnetConfig(
                username=self.query_one(
                    "#field-telnet-username", Input
                ).value.strip(),
                password=self.query_one("#field-telnet-password", Input).value,
            )
        elif protocol == Protocol.K8S:
            k8s_config = K8sConfig(
                context=self.query_one("#field-k8s-context", Input).value.strip(),
                namespace=(
                    self.query_one("#field-k8s-namespace", Input).value.strip()
                    or "default"
                ),
                pod=self.query_one("#field-k8s-pod", Input).value.strip(),
                container=self.query_one(
                    "#field-k8s-container", Input
                ).value.strip(),
                command=(
                    self.query_one("#field-k8s-command", Input).value.strip()
                    or "/bin/sh"
                ),
            )

        # Preserve last_connected if editing
        last_connected = None
        if self._is_editing and self.editing_connection is not None:
            last_connected = self.editing_connection.last_connected

        connection = Connection(
            name=name,
            host=host,
            protocol=protocol,
            port=port,
            description=description,
            last_connected=last_connected,
            ssh_config=ssh_config,
            rdp_config=rdp_config,
            vnc_config=vnc_config,
            telnet_config=telnet_config,
            k8s_config=k8s_config,
        )

        self.dismiss(connection)
