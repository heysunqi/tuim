"""Help screen showing keyboard shortcuts for Trelay."""
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static


SHORTCUTS = [
    ("Up / Down  or  k / j", "Navigate connections"),
    ("Enter", "Connect to selected"),
    ("Esc", "Disconnect / Back to list"),
    ("a", "Add new connection"),
    ("e", "Edit selected connection"),
    ("d", "Delete connection"),
    ("?", "Show this help"),
    ("q", "Quit application"),
]


class HelpScreen(ModalScreen):
    """Modal screen displaying available keyboard shortcuts."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close", show=False),
        Binding("question_mark", "dismiss", "Close", show=False),
    ]

    DEFAULT_CSS = """
    HelpScreen {
        align: center middle;
    }

    HelpScreen > Vertical {
        width: 64;
        max-height: 80%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }

    HelpScreen #help-title {
        text-align: center;
        text-style: bold;
        color: $text;
        width: 100%;
        margin-bottom: 1;
    }

    HelpScreen .shortcut-row {
        width: 100%;
        height: 1;
        margin: 0 1;
    }

    HelpScreen .shortcut-key {
        width: 28;
        color: $accent;
        text-style: bold;
    }

    HelpScreen .shortcut-desc {
        color: $text;
    }

    HelpScreen #help-divider {
        width: 100%;
        height: 1;
        margin: 1 0;
        color: $primary-lighten-2;
    }

    HelpScreen #close-btn {
        margin-top: 1;
        width: 100%;
    }
    """

    def compose(self):
        # type: () -> ComposeResult
        with Vertical():
            yield Static("Keyboard Shortcuts", id="help-title")
            yield Static(
                "----------------------------------------"
                "--------------------",
                id="help-divider",
            )
            for key, desc in SHORTCUTS:
                with Vertical(classes="shortcut-row"):
                    yield Static(
                        "  [bold cyan]{key}[/]  {desc}".format(
                            key=key.ljust(24), desc=desc
                        )
                    )
            yield Static("")
            with Center():
                yield Button("Close", variant="primary", id="close-btn")

    def on_button_pressed(self, event):
        # type: (Button.Pressed) -> None
        if event.button.id == "close-btn":
            self.dismiss()

    def action_dismiss(self):
        # type: () -> None
        self.dismiss()
