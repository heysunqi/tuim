"""Kubernetes resource picker screen for Trelay."""
import asyncio
import shutil
from typing import List, Optional, Tuple

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Select, Static


# Result type: (context, namespace, pod, container)
K8sSelection = Tuple[str, str, str, str]


async def _run_kubectl(*args):
    # type: (*str) -> Tuple[int, str, str]
    """Run a kubectl command asynchronously and return (returncode, stdout, stderr)."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "kubectl",
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_bytes, stderr_bytes = await proc.communicate()
        stdout = stdout_bytes.decode("utf-8", errors="replace") if stdout_bytes else ""
        stderr = stderr_bytes.decode("utf-8", errors="replace") if stderr_bytes else ""
        return (proc.returncode or 0, stdout, stderr)
    except FileNotFoundError:
        return (1, "", "kubectl not found")
    except Exception as exc:
        return (1, "", str(exc))


def _parse_table_column(output, column=0):
    # type: (str, int) -> List[str]
    """Parse a column from kubectl tabular output, skipping the header row."""
    lines = output.strip().splitlines()
    results = []  # type: List[str]
    for line in lines[1:]:  # skip header
        parts = line.split()
        if len(parts) > column:
            results.append(parts[column])
    return results


class K8sPickerScreen(ModalScreen[Optional[K8sSelection]]):
    """Modal screen for interactively selecting K8s resources.

    Provides a three-step cascade:
      1. Select a kubectl context
      2. Select a namespace
      3. Select a pod
      4. Optionally select a container

    Dismisses with a (context, namespace, pod, container) tuple, or
    None on cancel.
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False),
    ]

    DEFAULT_CSS = """
    K8sPickerScreen {
        align: center middle;
    }

    K8sPickerScreen > Vertical {
        width: 68;
        max-height: 85%;
        background: $surface;
        border: thick $accent;
        padding: 1 2;
    }

    K8sPickerScreen #picker-title {
        text-align: center;
        text-style: bold;
        color: $text;
        width: 100%;
        margin-bottom: 1;
    }

    K8sPickerScreen #picker-error {
        text-align: center;
        color: $error;
        width: 100%;
        margin-bottom: 1;
    }

    K8sPickerScreen .picker-group {
        width: 100%;
        height: auto;
        margin-bottom: 1;
    }

    K8sPickerScreen .picker-group Label {
        margin-bottom: 0;
        color: $text-muted;
    }

    K8sPickerScreen .picker-group Select {
        width: 100%;
    }

    K8sPickerScreen #picker-status {
        color: $text-muted;
        text-align: center;
        width: 100%;
        height: 1;
        margin-bottom: 1;
    }

    K8sPickerScreen .button-row {
        width: 100%;
        height: 3;
        align: center middle;
        margin-top: 1;
    }

    K8sPickerScreen .button-row Button {
        margin: 0 2;
    }

    K8sPickerScreen .hidden {
        display: none;
    }
    """

    def __init__(self):
        # type: () -> None
        super().__init__()
        self._contexts = []  # type: List[str]
        self._namespaces = []  # type: List[str]
        self._pods = []  # type: List[str]
        self._containers = []  # type: List[str]
        self._selected_context = ""
        self._selected_namespace = ""
        self._selected_pod = ""
        self._selected_container = ""
        self._kubectl_available = True

    def compose(self):
        # type: () -> ComposeResult
        with Vertical():
            yield Static("Kubernetes Resource Picker", id="picker-title")
            yield Static("", id="picker-error")
            yield Static("Loading...", id="picker-status")

            with VerticalScroll():
                # Context selector
                with Vertical(classes="picker-group"):
                    yield Label("Context")
                    yield Select(
                        options=[],
                        prompt="Select a context...",
                        id="select-context",
                    )

                # Namespace selector
                with Vertical(classes="picker-group"):
                    yield Label("Namespace")
                    yield Select(
                        options=[],
                        prompt="Select a namespace...",
                        id="select-namespace",
                    )

                # Pod selector
                with Vertical(classes="picker-group"):
                    yield Label("Pod")
                    yield Select(
                        options=[],
                        prompt="Select a pod...",
                        id="select-pod",
                    )

                # Container selector (optional)
                with Vertical(classes="picker-group"):
                    yield Label("Container (optional)")
                    yield Select(
                        options=[],
                        prompt="Select a container...",
                        id="select-container",
                    )

            # Buttons
            with Center():
                with Horizontal(classes="button-row"):
                    yield Button("Cancel", variant="default", id="cancel-btn")
                    yield Button("Confirm", variant="primary", id="confirm-btn")

    async def on_mount(self):
        # type: () -> None
        """Check for kubectl and load contexts on mount."""
        if shutil.which("kubectl") is None:
            self._kubectl_available = False
            self._show_error("kubectl is not installed or not in PATH.")
            self._set_status("")
            return

        self._set_status("Fetching contexts...")
        await self._load_contexts()

    def _show_error(self, message):
        # type: (str) -> None
        """Display an error message in the error label."""
        try:
            error_widget = self.query_one("#picker-error", Static)
            error_widget.update("[bold red]{}[/]".format(message))
        except Exception:
            pass

    def _clear_error(self):
        # type: () -> None
        """Clear the error message."""
        try:
            error_widget = self.query_one("#picker-error", Static)
            error_widget.update("")
        except Exception:
            pass

    def _set_status(self, message):
        # type: (str) -> None
        """Set the status text."""
        try:
            status_widget = self.query_one("#picker-status", Static)
            status_widget.update(message)
        except Exception:
            pass

    async def _load_contexts(self):
        # type: () -> None
        """Fetch available kubectl contexts."""
        returncode, stdout, stderr = await _run_kubectl(
            "config", "get-contexts", "--no-headers", "-o", "name"
        )
        if returncode != 0:
            self._show_error(
                "Failed to get contexts: {}".format(stderr.strip() or "unknown error")
            )
            self._set_status("")
            return

        self._contexts = [
            line.strip() for line in stdout.strip().splitlines() if line.strip()
        ]
        if not self._contexts:
            self._show_error("No kubectl contexts found.")
            self._set_status("")
            return

        self._clear_error()
        self._set_status("")

        context_select = self.query_one("#select-context", Select)
        options = [(ctx, ctx) for ctx in self._contexts]
        context_select.set_options(options)

    async def _load_namespaces(self, context):
        # type: (str) -> None
        """Fetch namespaces for the given context."""
        self._set_status("Fetching namespaces...")

        cmd_args = ["get", "namespaces", "--no-headers", "-o", "custom-columns=:metadata.name"]
        if context:
            cmd_args.extend(["--context", context])

        returncode, stdout, stderr = await _run_kubectl(*cmd_args)
        if returncode != 0:
            self._show_error(
                "Failed to get namespaces: {}".format(
                    stderr.strip() or "unknown error"
                )
            )
            self._set_status("")
            return

        self._namespaces = [
            line.strip() for line in stdout.strip().splitlines() if line.strip()
        ]
        self._clear_error()
        self._set_status("")

        ns_select = self.query_one("#select-namespace", Select)
        options = [(ns, ns) for ns in self._namespaces]
        ns_select.set_options(options)

        # Clear downstream selectors
        self._clear_select("select-pod")
        self._clear_select("select-container")

    async def _load_pods(self, context, namespace):
        # type: (str, str) -> None
        """Fetch pods for the given context and namespace."""
        self._set_status("Fetching pods...")

        cmd_args = [
            "get", "pods", "-n", namespace,
            "--no-headers", "-o", "custom-columns=:metadata.name",
        ]
        if context:
            cmd_args.extend(["--context", context])

        returncode, stdout, stderr = await _run_kubectl(*cmd_args)
        if returncode != 0:
            self._show_error(
                "Failed to get pods: {}".format(stderr.strip() or "unknown error")
            )
            self._set_status("")
            return

        self._pods = [
            line.strip() for line in stdout.strip().splitlines() if line.strip()
        ]
        if not self._pods:
            self._show_error("No pods found in namespace '{}'.".format(namespace))
            self._set_status("")
            return

        self._clear_error()
        self._set_status("")

        pod_select = self.query_one("#select-pod", Select)
        options = [(pod, pod) for pod in self._pods]
        pod_select.set_options(options)

        # Clear container selector
        self._clear_select("select-container")

    async def _load_containers(self, context, namespace, pod):
        # type: (str, str, str) -> None
        """Fetch containers for the given pod."""
        self._set_status("Fetching containers...")

        cmd_args = [
            "get", "pod", pod, "-n", namespace,
            "-o", "jsonpath={.spec.containers[*].name}",
        ]
        if context:
            cmd_args.extend(["--context", context])

        returncode, stdout, stderr = await _run_kubectl(*cmd_args)
        if returncode != 0:
            self._show_error(
                "Failed to get containers: {}".format(
                    stderr.strip() or "unknown error"
                )
            )
            self._set_status("")
            return

        self._containers = [
            name.strip() for name in stdout.strip().split() if name.strip()
        ]
        self._clear_error()
        self._set_status("")

        container_select = self.query_one("#select-container", Select)
        if len(self._containers) > 1:
            options = [(c, c) for c in self._containers]
            container_select.set_options(options)
        elif len(self._containers) == 1:
            # Single container -- auto-select it
            options = [(self._containers[0], self._containers[0])]
            container_select.set_options(options)
            self._selected_container = self._containers[0]
        else:
            container_select.set_options([])

    def _clear_select(self, select_id):
        # type: (str) -> None
        """Clear a Select widget's options."""
        try:
            select_widget = self.query_one("#{}".format(select_id), Select)
            select_widget.set_options([])
        except Exception:
            pass

    async def on_select_changed(self, event):
        # type: (Select.Changed) -> None
        """Handle cascading selection changes."""
        select_id = event.select.id
        value = event.value

        if value is None or value == Select.BLANK:
            return

        if select_id == "select-context":
            self._selected_context = str(value)
            self._selected_namespace = ""
            self._selected_pod = ""
            self._selected_container = ""
            await self._load_namespaces(self._selected_context)

        elif select_id == "select-namespace":
            self._selected_namespace = str(value)
            self._selected_pod = ""
            self._selected_container = ""
            await self._load_pods(self._selected_context, self._selected_namespace)

        elif select_id == "select-pod":
            self._selected_pod = str(value)
            self._selected_container = ""
            await self._load_containers(
                self._selected_context,
                self._selected_namespace,
                self._selected_pod,
            )

        elif select_id == "select-container":
            self._selected_container = str(value)

    def on_button_pressed(self, event):
        # type: (Button.Pressed) -> None
        if event.button.id == "confirm-btn":
            self._confirm()
        elif event.button.id == "cancel-btn":
            self.dismiss(None)

    def _confirm(self):
        # type: () -> None
        """Validate selection and dismiss with the chosen resources."""
        if not self._selected_context:
            self._show_error("Please select a context.")
            return
        if not self._selected_namespace:
            self._show_error("Please select a namespace.")
            return
        if not self._selected_pod:
            self._show_error("Please select a pod.")
            return

        self.dismiss((
            self._selected_context,
            self._selected_namespace,
            self._selected_pod,
            self._selected_container,
        ))

    def action_cancel(self):
        # type: () -> None
        self.dismiss(None)
