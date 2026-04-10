"""K8s help screen showing all resource commands."""
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Static

from trelay.i18n import t

# Organized by category (supports both Chinese and English)
K8S_COMMANDS = [
    ("Workload / \u5de5\u4f5c\u8d1f\u8f7d", [
        (":pod / :po", "pods"),
        (":deploy", "deployments"),
        (":ds / :daemonset", "daemonsets"),
        (":sts / :statefulset", "statefulsets"),
        (":job", "jobs"),
        (":cj / :cronjob", "cronjobs"),
        (":rs / :replicaset", "replicasets"),
    ]),
    ("Service / \u670d\u52a1", [
        (":svc / :service", "services"),
        (":ing / :ingress", "ingresses"),
        (":ep / :endpoint", "endpoints"),
        (":netpol / :networkpolicy", "networkpolicies"),
    ]),
    ("Storage / \u5b58\u50a8", [
        (":cm / :configmap", "configmaps"),
        (":secret", "secrets"),
        (":pv / :persistentvolume", "persistentvolumes"),
        (":pvc / :persistentvolumeclaim", "persistentvolumeclaims"),
        (":sc / :storageclass", "storageclasses"),
    ]),
    ("Cluster / \u96c6\u7fa4", [
        (":ns / :namespace", "namespaces"),
        (":node", "nodes"),
        (":ev / :event", "events"),
        (":hpa / :horizontalpodautoscaler", "horizontalpodautoscalers"),
        (":rq / :resourcequota", "resourcequotas"),
        (":pdb / :poddisruptionbudget", "poddisruptionbudgets"),
        (":limitrange", "limitranges"),
    ]),
    ("Actions / \u64cd\u4f5c", [
        ("?:", "k8s_help"),
        (":ns <name>", "switch_namespace"),
        (":q", "back"),
        (":q!", "quit_force"),
    ]),
]

class K8sHelpScreen(ModalScreen):
    """Modal screen displaying K8s resource commands."""

    BINDINGS = [
        Binding("escape", "dismiss", "", show=False),
        Binding("question_mark", "dismiss", "", show=False),
    ]

    DEFAULT_CSS = """
    K8sHelpScreen {
        align: center middle;
    }

    K8sHelpScreen > Vertical {
        width: 80;
        max-height: 90%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }

    K8sHelpScreen #help-title {
        text-align: center;
        text-style: bold;
        color: $text;
        margin-bottom: 1;
    }

    K8sHelpScreen .section-header {
        color: $accent;
        text-style: bold;
        margin-top: 1;
    }

    K8sHelpScreen .command-row {
        width: 100%;
        height: 1;
        margin: 0 1;
    }

    K8sHelpScreen .command-key {
        width: 30;
        color: $primary;
        text-style: bold;
    }

    K8sHelpScreen .command-desc {
        color: $text;
    }

    K8sHelpScreen #help-hint {
        text-align: center;
        text-style: dim;
        margin-top: 1;
    }
    """

    def compose(self):
        # type: () -> ComposeResult
        with Vertical():
            yield Static(t("title_k8s_help"), id="help-title")
            yield Static("")
            for section, commands in K8S_COMMANDS:
                # Extract section name (split by " / ")
                section_name = section.split(" / ")[0]
                yield Static(section_name, classes="section-header")
                for cmd, desc in commands:
                    # Translate description
                    desc_text = t(desc)
                    # Format with cyan color for command
                    yield Static("  [bold cyan]{}[/]  {}".format(cmd.ljust(30), desc_text))
            yield Static("")
            yield Static(t("k8s_help_hint"), id="help-hint")

    def on_key(self, event):
        # type: (object) -> None
        # Press any key to close
        self.dismiss()

    def action_dismiss(self):
        # type: () -> None
        self.dismiss()
