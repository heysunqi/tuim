"""Terminal view widget using pyte for full terminal emulation.

Supports full-screen applications (vim, htop, etc.) by maintaining a
virtual terminal screen buffer via pyte.
"""
from __future__ import annotations

import pyte
from rich.text import Text

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static

# Map pyte named colors to k9s-theme hex values
_COLOR_MAP = {
    "black": "#000000",
    "red": "#f85149",
    "green": "#3fb950",
    "brown": "#d29922",
    "blue": "#58a6ff",
    "magenta": "#a371f7",
    "cyan": "#39c5cf",
    "white": "#e6edf3",
}
_BRIGHT_COLOR_MAP = {
    "black": "#6e7681",
    "red": "#ff7b72",
    "green": "#7ee787",
    "brown": "#e3b341",
    "blue": "#79c0ff",
    "magenta": "#d2a8ff",
    "cyan": "#56d4dd",
    "white": "#ffffff",
}


def _pyte_color(color, bold=False):
    # type: (object, bool) -> object
    """Convert a pyte color value to a Rich color string, or None."""
    if color == "default":
        return None
    if isinstance(color, str):
        if bold and color in _BRIGHT_COLOR_MAP:
            return _BRIGHT_COLOR_MAP[color]
        if color in _COLOR_MAP:
            return _COLOR_MAP[color]
        # 256-color / 24-bit: pyte gives hex string like "ff0000"
        if len(color) == 6:
            try:
                int(color, 16)
                return "#" + color
            except ValueError:
                pass
    return None


def _char_style(char):
    # type: (object) -> object
    """Build a Rich style string for a pyte Char, or None."""
    parts = []
    if char.bold:
        parts.append("bold")
    if char.italics:
        parts.append("italic")
    if char.underscore:
        parts.append("underline")
    if char.strikethrough:
        parts.append("strike")

    fg = _pyte_color(char.fg, bold=char.bold)
    bg = _pyte_color(char.bg)

    if char.reverse:
        fg, bg = bg, fg

    if fg:
        parts.append(fg)
    if bg:
        parts.append("on " + bg)

    return " ".join(parts) if parts else None


class TerminalView(Widget):
    """Terminal view backed by a pyte virtual terminal.

    All raw SSH/Telnet/K8s data is fed through pyte, which handles
    cursor positioning, scrolling, colors, and full-screen apps.
    """

    DEFAULT_COLS = 120
    DEFAULT_ROWS = 40

    def __init__(self, **kwargs):
        # type: (...) -> None
        super().__init__(**kwargs)
        self._screen = pyte.Screen(self.DEFAULT_COLS, self.DEFAULT_ROWS)
        self._stream = pyte.Stream(self._screen)
        self._render_pending = False
        self._cursor_visible = True
        self._cached_text = None   # type: object  # Rich Text or None
        self._last_content_row = 0
        self._on_resize_cb = None  # type: object  # optional callback(cols, rows)

    def compose(self):
        # type: () -> ComposeResult
        yield Static("", id="terminal-content")

    def on_mount(self):
        # type: () -> None
        self._cursor_timer = self.set_interval(0.53, self._blink_cursor)

    def on_resize(self, event):
        # type: (object) -> None
        """Resize the virtual terminal to match the widget dimensions."""
        # Static child has padding: 0 1 → text area is 2 columns narrower
        w = event.size.width - 2
        h = event.size.height
        if w < 2 or h < 1:
            return
        if w != self._screen.columns or h != self._screen.lines:
            self._screen.resize(h, w)
            self._schedule_render()
            if self._on_resize_cb is not None:
                self._on_resize_cb(w, h)

    # ---- cursor ----

    def _blink_cursor(self):
        # type: () -> None
        self._cursor_visible = not self._cursor_visible
        if self._cached_text is not None:
            self._update_display()

    def _update_display(self):
        # type: () -> None
        """Render cached text + blinking cursor to the Static widget."""
        if self._cached_text is None:
            return
        rendered = self._cached_text.copy()

        # Apply cursor as reverse-video at the cursor position
        if self._cursor_visible:
            cy = self._screen.cursor.y
            cx = self._screen.cursor.x
            if cy <= self._last_content_row:
                # Each row has `columns` chars; rows separated by \n (+1)
                offset = cy * (self._screen.columns + 1) + cx
                if 0 <= offset < len(rendered):
                    rendered.stylize("reverse", offset, offset + 1)

        try:
            widget = self.query_one("#terminal-content", Static)
            widget.update(rendered)
        except Exception:
            pass

    # ---- rendering ----

    def _schedule_render(self):
        # type: () -> None
        if not self._render_pending:
            self._render_pending = True
            self.set_timer(0.03, self._do_render)

    def _do_render(self):
        # type: () -> None
        self._render_pending = False
        self._render_content()

    def _is_row_empty(self, row):
        # type: (int) -> bool
        line = self._screen.buffer[row]
        for col in range(self._screen.columns):
            ch = line[col].data
            if ch and ch != " ":
                return False
        return True

    def _render_content(self):
        # type: () -> None
        cursor_y = self._screen.cursor.y
        cols = self._screen.columns

        # Find last non-empty row, but always include cursor row
        last_row = self._screen.lines - 1
        while last_row > cursor_y and self._is_row_empty(last_row):
            last_row -= 1
        self._last_content_row = last_row

        text = Text()
        for row in range(last_row + 1):
            if row > 0:
                text.append("\n")
            line_buf = self._screen.buffer[row]
            for col in range(cols):
                char = line_buf[col]
                ch = char.data if char.data else " "
                style = _char_style(char)
                text.append(ch, style=style)

        self._cached_text = text
        self._cursor_visible = True
        self._update_display()

    # ---- public API ----

    def set_on_resize(self, callback):
        # type: (object) -> None
        """Register a callback(cols, rows) invoked on terminal resize."""
        self._on_resize_cb = callback

    def get_terminal_size(self):
        # type: () -> tuple
        """Return (cols, rows) of the virtual terminal."""
        return (self._screen.columns, self._screen.lines)

    def write_output(self, text):
        # type: (str) -> None
        """Feed raw terminal data through pyte."""
        self._stream.feed(text)
        self._schedule_render()

    def write_line(self, text):
        # type: (str) -> None
        """Write a system message as a line in the terminal."""
        self._stream.feed(text + "\r\n")
        self._schedule_render()

    def clear_output(self):
        # type: () -> None
        """Reset the virtual terminal screen."""
        self._screen.reset()
        self._cached_text = None
        self._render_pending = False
        try:
            widget = self.query_one("#terminal-content", Static)
            widget.update("")
        except Exception:
            pass
