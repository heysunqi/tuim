"""Vim-style command bar widget for the Tuim TUI."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Static


class CommandBar(Widget):
    """A single-line command input bar (vim-style : / ? prefix).

    The bar is hidden by default and shown via ``activate(prefix)``.
    All keystrokes are handled manually so we get real-time search
    without needing a Textual Input (which adds borders/padding).
    """

    can_focus = True
    can_focus_children = False

    class Submitted(Message):
        """Fired when the user presses Enter."""

        def __init__(self, prefix, value):
            # type: (str, str) -> None
            super().__init__()
            self.prefix = prefix
            self.value = value

    class Changed(Message):
        """Fired on every keystroke (for real-time search)."""

        def __init__(self, prefix, value):
            # type: (str, str) -> None
            super().__init__()
            self.prefix = prefix
            self.value = value

    class Cancelled(Message):
        """Fired when the user presses Escape or clears the bar."""

        def __init__(self):
            # type: () -> None
            super().__init__()

    def __init__(self, **kwargs):
        # type: (...) -> None
        super().__init__(id="command-bar", **kwargs)
        self._prefix = ""
        self._buffer = ""
        self._active = False

    @property
    def is_active(self):
        # type: () -> bool
        return self._active

    def compose(self):
        # type: () -> ComposeResult
        yield Static("", id="command-bar-text", markup=True)

    def activate(self, prefix):
        # type: (str) -> None
        """Show the command bar with the given prefix character."""
        self._prefix = prefix
        self._buffer = ""
        self._active = True
        self.can_focus = True
        self.remove_class("hidden")
        self._render_bar()
        self.focus()

    def deactivate(self):
        # type: () -> None
        """Hide the command bar and reset state."""
        self._active = False
        self._prefix = ""
        self._buffer = ""
        self.can_focus = False
        self.add_class("hidden")

    def _render_bar(self):
        # type: () -> None
        try:
            label = self.query_one("#command-bar-text", Static)
            cursor = "[reverse] [/]"
            label.update(
                "[bold #39c5cf]{}[/][#e6edf3]{}[/]{}".format(
                    self._prefix, self._buffer, cursor
                )
            )
        except Exception:
            pass

    def on_key(self, event):
        # type: (object) -> None
        if not self._active:
            return

        key = event.key
        char = event.character

        event.prevent_default()
        event.stop()

        if key == "escape":
            self.deactivate()
            self.post_message(self.Cancelled())
            return

        if key == "enter":
            self.post_message(self.Submitted(self._prefix, self._buffer))
            return

        if key == "backspace":
            if self._buffer:
                self._buffer = self._buffer[:-1]
                self._render_bar()
                self.post_message(self.Changed(self._prefix, self._buffer))
            else:
                # Empty buffer + backspace → cancel
                self.deactivate()
                self.post_message(self.Cancelled())
            return

        # Printable character
        if char and len(char) >= 1 and ord(char[0]) >= 32:
            self._buffer += char
            self._render_bar()
            self.post_message(self.Changed(self._prefix, self._buffer))
            return

        if key == "space":
            self._buffer += " "
            self._render_bar()
            self.post_message(self.Changed(self._prefix, self._buffer))
