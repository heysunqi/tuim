"""Help screen showing keyboard shortcuts for Trelay."""
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from trelay.i18n import t


SHORTCUTS = [
    ("Up / Down  or  k / j", "help_navigate"),
    ("Enter", "help_connect"),
    ("Esc", "help_disconnect"),
    ("a", "help_add"),
    ("e", "help_edit"),
    ("d", "help_delete"),
    ("?", "help_show_help"),
    ("q", "help_quit"),
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
            yield Static(t("title_help"), id="help-title")
            yield Static(
                "----------------------------------------"
                "--------------------",
                id="help-divider",
            )
            for key, desc_key in SHORTCUTS:
                with Vertical(classes="shortcut-row"):
                    yield Static(
                        "  [bold cyan]{key}[/]  {desc}".format(
                            key=key.ljust(24), desc=t(desc_key)
                        )
                    )
            yield Static("")
            with Center():
                yield Button(t("btn_close"), variant="primary", id="close-btn")

    def on_button_pressed(self, event):
        # type: (Button.Pressed) -> None
        if event.button.id == "close-btn":
            self.dismiss()

    def action_dismiss(self):
        # type: () -> None
        self.dismiss()
