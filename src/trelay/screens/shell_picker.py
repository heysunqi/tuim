"""Shell picker dialog for retrying K8s exec with a different shell."""
from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Static


_COMMON_SHELLS = ["/bin/bash", "/bin/sh", "/bin/ash", "/bin/zsh"]


class ShellPickerScreen(ModalScreen[Optional[str]]):
    """Modal screen for choosing an alternative shell after exec failure.

    Dismisses with a shell command string, or None if cancelled.
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False),
    ]

    DEFAULT_CSS = """
    ShellPickerScreen {
        align: center middle;
    }

    ShellPickerScreen > Vertical {
        width: 60;
        height: auto;
        background: $surface;
        border: thick $warning;
        padding: 1 2;
    }

    ShellPickerScreen #sp-title {
        text-align: center;
        text-style: bold;
        color: $warning;
        width: 100%;
        margin-bottom: 1;
    }

    ShellPickerScreen #sp-message {
        text-align: center;
        color: $text;
        width: 100%;
        margin-bottom: 1;
    }

    ShellPickerScreen .shell-row {
        width: 100%;
        height: 3;
        align: center middle;
        margin-bottom: 1;
    }

    ShellPickerScreen .shell-row Button {
        margin: 0 1;
    }

    ShellPickerScreen .custom-row {
        width: 100%;
        height: 3;
        align: center middle;
    }

    ShellPickerScreen .custom-row Input {
        width: 30;
        margin: 0 1;
    }

    ShellPickerScreen .custom-row Button {
        margin: 0 1;
    }

    ShellPickerScreen .cancel-row {
        width: 100%;
        height: 3;
        align: center middle;
        margin-top: 1;
    }
    """

    def compose(self):
        # type: () -> ComposeResult
        with Vertical():
            yield Static("Shell Not Found", id="sp-title")
            yield Static(
                "The default shell failed to start.\n"
                "Choose an alternative shell to try:",
                id="sp-message",
            )
            with Center():
                with Horizontal(classes="shell-row"):
                    for shell in _COMMON_SHELLS:
                        yield Button(shell, id="shell-{}".format(
                            shell.replace("/", "-").lstrip("-")
                        ))
            with Center():
                with Horizontal(classes="custom-row"):
                    yield Input(
                        placeholder="Custom shell path...",
                        id="custom-shell-input",
                    )
                    yield Button("Try", variant="primary", id="try-custom-btn")
            with Center():
                with Horizontal(classes="cancel-row"):
                    yield Button("Cancel", variant="default", id="cancel-btn")

    def on_button_pressed(self, event):
        # type: (Button.Pressed) -> None
        btn_id = event.button.id
        if btn_id == "cancel-btn":
            self.dismiss(None)
        elif btn_id == "try-custom-btn":
            inp = self.query_one("#custom-shell-input", Input)
            value = inp.value.strip()
            if value:
                self.dismiss(value)
        elif btn_id and btn_id.startswith("shell-"):
            # Reconstruct the shell path from the button label
            self.dismiss(event.button.label.plain)

    def action_cancel(self):
        # type: () -> None
        self.dismiss(None)
