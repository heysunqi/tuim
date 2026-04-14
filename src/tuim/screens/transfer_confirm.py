"""Confirmation dialog for SFTP file transfers."""
from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from tuim.i18n import t


class TransferConfirmScreen(ModalScreen[Optional[str]]):
    """Modal screen asking the user to confirm a file transfer.

    Modes:
      - "upload": simple confirm/cancel for uploading
      - "download": simple confirm/cancel for downloading
      - "download_exists": overwrite/rename/cancel when file already exists

    Dismisses with:
      - "confirm" — proceed with transfer
      - "overwrite" — overwrite existing file
      - "rename" — download with a renamed path
      - None — cancelled
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False),
    ]

    DEFAULT_CSS = """
    TransferConfirmScreen {
        align: center middle;
    }

    TransferConfirmScreen > Vertical {
        width: 64;
        height: auto;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }

    TransferConfirmScreen #tc-title {
        text-align: center;
        text-style: bold;
        color: $primary;
        width: 100%;
        margin-bottom: 1;
    }

    TransferConfirmScreen #tc-message {
        text-align: center;
        color: $text;
        width: 100%;
        margin-bottom: 1;
    }

    TransferConfirmScreen .button-row {
        width: 100%;
        height: 3;
        align: center middle;
        margin-top: 1;
    }

    TransferConfirmScreen .button-row Button {
        margin: 0 2;
    }
    """

    def __init__(self, mode, filename, directory):
        # type: (str, str, str) -> None
        super().__init__()
        self._mode = mode  # "upload" | "download" | "download_exists"
        self._filename = filename
        self._directory = directory

    def compose(self):
        # type: () -> ComposeResult
        if self._mode == "upload":
            title = t("sftp_confirm_upload_title")
            message = t("sftp_confirm_upload_msg",
                        filename=self._filename, directory=self._directory)
        elif self._mode == "download_exists":
            title = t("sftp_confirm_download_title")
            message = t("sftp_confirm_download_exists_msg",
                        filename=self._filename, directory=self._directory)
        else:
            title = t("sftp_confirm_download_title")
            message = t("sftp_confirm_download_msg",
                        filename=self._filename, directory=self._directory)

        with Vertical():
            yield Static(title, id="tc-title")
            yield Static(message, id="tc-message")
            with Center():
                with Horizontal(classes="button-row"):
                    yield Button(t("sftp_btn_no"), variant="default", id="tc-no")
                    if self._mode == "download_exists":
                        yield Button(t("sftp_btn_overwrite"), variant="warning",
                                     id="tc-overwrite")
                        yield Button(t("sftp_btn_rename"), variant="primary",
                                     id="tc-rename")
                    else:
                        yield Button(t("sftp_btn_yes"), variant="primary",
                                     id="tc-yes")

    def on_button_pressed(self, event):
        # type: (Button.Pressed) -> None
        btn_id = event.button.id
        if btn_id == "tc-yes":
            self.dismiss("confirm")
        elif btn_id == "tc-overwrite":
            self.dismiss("overwrite")
        elif btn_id == "tc-rename":
            self.dismiss("rename")
        else:
            self.dismiss(None)

    def action_cancel(self):
        # type: () -> None
        self.dismiss(None)
