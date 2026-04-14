"""Input dialog for creating a new folder in SFTP mode."""
from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Static

from tuim.i18n import t


class MkdirScreen(ModalScreen[Optional[str]]):
    """Modal screen that prompts the user for a new folder name.

    Dismisses with the folder name string, or None if cancelled.
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False),
    ]

    DEFAULT_CSS = """
    MkdirScreen {
        align: center middle;
    }

    MkdirScreen > Vertical {
        width: 56;
        height: auto;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }

    MkdirScreen #mkdir-title {
        text-align: center;
        text-style: bold;
        color: $primary;
        width: 100%;
        margin-bottom: 1;
    }

    MkdirScreen #mkdir-input {
        width: 100%;
        margin-bottom: 1;
    }

    MkdirScreen .button-row {
        width: 100%;
        height: 3;
        align: center middle;
        margin-top: 1;
    }

    MkdirScreen .button-row Button {
        margin: 0 2;
    }
    """

    def compose(self):
        # type: () -> ComposeResult
        with Vertical():
            yield Static(t("sftp_mkdir_title"), id="mkdir-title")
            yield Input(
                placeholder=t("sftp_mkdir_placeholder"),
                id="mkdir-input",
            )
            with Center():
                with Horizontal(classes="button-row"):
                    yield Button(t("btn_cancel"), variant="default", id="mkdir-cancel")
                    yield Button(t("btn_confirm"), variant="primary", id="mkdir-confirm")

    def on_mount(self):
        # type: () -> None
        self.query_one("#mkdir-input", Input).focus()

    def on_button_pressed(self, event):
        # type: (Button.Pressed) -> None
        if event.button.id == "mkdir-confirm":
            self._submit()
        else:
            self.dismiss(None)

    def on_input_submitted(self, event):
        # type: (Input.Submitted) -> None
        self._submit()

    def _submit(self):
        # type: () -> None
        name = self.query_one("#mkdir-input", Input).value.strip()
        if name:
            self.dismiss(name)

    def action_cancel(self):
        # type: () -> None
        self.dismiss(None)
