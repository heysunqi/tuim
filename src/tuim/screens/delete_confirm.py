"""Confirmation dialog for deleting a connection."""
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from tuim.i18n import t


class DeleteConfirmScreen(ModalScreen[bool]):
    """Modal screen asking the user to confirm deletion of a connection.

    Dismisses with True if the user confirms, False otherwise.
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False),
    ]

    DEFAULT_CSS = """
    DeleteConfirmScreen {
        align: center middle;
    }

    DeleteConfirmScreen > Vertical {
        width: 56;
        height: auto;
        background: $surface;
        border: thick $error;
        padding: 1 2;
    }

    DeleteConfirmScreen #delete-title {
        text-align: center;
        text-style: bold;
        color: $error;
        width: 100%;
        margin-bottom: 1;
    }

    DeleteConfirmScreen #delete-message {
        text-align: center;
        color: $text;
        width: 100%;
        margin-bottom: 1;
    }

    DeleteConfirmScreen .button-row {
        width: 100%;
        height: 3;
        align: center middle;
        margin-top: 1;
    }

    DeleteConfirmScreen .button-row Button {
        margin: 0 2;
    }
    """

    def __init__(self, connection_name):
        # type: (str) -> None
        super().__init__()
        self.connection_name = connection_name

    def compose(self):
        # type: () -> ComposeResult
        with Vertical():
            yield Static(t("title_delete"), id="delete-title")
            yield Static(
                t("msg_delete_confirm", name=self.connection_name),
                id="delete-message",
            )
            with Center():
                with Horizontal(classes="button-row"):
                    yield Button(t("btn_cancel"), variant="default", id="cancel-btn")
                    yield Button(t("btn_delete"), variant="error", id="delete-btn")

    def on_button_pressed(self, event):
        # type: (Button.Pressed) -> None
        if event.button.id == "delete-btn":
            self.dismiss(True)
        else:
            self.dismiss(False)

    def action_cancel(self):
        # type: () -> None
        self.dismiss(False)
