"""Terminal view widget using pyte for full terminal emulation.

Supports full-screen applications (vim, htop, etc.) by maintaining a
virtual terminal screen buffer via pyte.  Scrollback history is kept
so the user can scroll up to review past output.
"""
from __future__ import annotations

from collections import deque

import pyte
from rich.text import Text

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static

from tuim.i18n import t

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

# Maximum number of scrollback lines to keep
_MAX_SCROLLBACK = 5000


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


def _snapshot_history_line(line_dict, cols):
    # type: (dict, int) -> list
    """Snapshot a pyte history line (StaticDefaultDict) into a list of (char, style) tuples."""
    result = []
    for c in range(cols):
        ch = line_dict.get(c)
        if ch is not None:
            style = _char_style(ch)
            result.append((ch.data if ch.data else " ", style))
        else:
            result.append((" ", None))
    return result


class TerminalView(Widget):
    """Terminal view backed by a pyte virtual terminal.

    All raw SSH/Telnet/K8s data is fed through pyte, which handles
    cursor positioning, scrolling, colors, and full-screen apps.

    Scrollback history is maintained so the user can scroll up (mouse
    wheel or Shift+Up/Down) to review past output.
    """

    DEFAULT_COLS = 120
    DEFAULT_ROWS = 40

    def __init__(self, **kwargs):
        # type: (...) -> None
        super().__init__(**kwargs)
        self._screen = pyte.HistoryScreen(
            self.DEFAULT_COLS, self.DEFAULT_ROWS, history=_MAX_SCROLLBACK
        )
        self._stream = pyte.Stream(self._screen)
        self._render_pending = False
        self._cursor_visible = True
        self._cached_text = None   # type: object  # Rich Text or None
        self._last_content_row = 0
        self._on_resize_cb = None  # type: object  # optional callback(cols, rows)

        # Scrollback: list of snapshotted lines (each a list of (char, style))
        self._scrollback = deque(maxlen=_MAX_SCROLLBACK)  # type: deque
        self._prev_history_len = 0  # track how many lines were in history.top

        # Scroll offset: 0 = live (showing current screen), >0 = scrolled up
        self._scroll_offset = 0

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

    # ---- scrollback history capture ----

    def _capture_new_history(self):
        # type: () -> None
        """Capture any new lines that pyte has scrolled into history.top."""
        current_len = len(self._screen.history.top)
        if current_len > self._prev_history_len:
            # New lines were added to history
            new_count = current_len - self._prev_history_len
            cols = self._screen.columns
            # history.top is a deque; new lines are at the end
            start = max(0, current_len - new_count)
            for i in range(start, current_len):
                line = self._screen.history.top[i]
                self._scrollback.append(_snapshot_history_line(line, cols))
        self._prev_history_len = current_len

    # ---- mouse scroll ----

    def on_mouse_scroll_up(self, event):
        # type: (object) -> None
        """Scroll up into history."""
        event.stop()
        max_offset = len(self._scrollback)
        if max_offset == 0:
            return
        self._scroll_offset = min(self._scroll_offset + 3, max_offset)
        self._render_content()

    def on_mouse_scroll_down(self, event):
        # type: (object) -> None
        """Scroll down toward live view."""
        event.stop()
        if self._scroll_offset <= 0:
            return
        self._scroll_offset = max(self._scroll_offset - 3, 0)
        self._render_content()

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

        # Only show cursor when at live view (scroll_offset == 0)
        if self._cursor_visible and self._scroll_offset == 0:
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
        cols = self._screen.columns

        if self._scroll_offset > 0:
            # Scrolled up: render from scrollback + screen buffer
            self._render_scrollback_view(cols)
        else:
            # Live view: render current screen buffer
            self._render_live_view(cols)

    def _render_live_view(self, cols):
        # type: (int) -> None
        """Render the current pyte screen buffer (normal live view)."""
        cursor_y = self._screen.cursor.y

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

    def _render_scrollback_view(self, cols):
        # type: (int) -> None
        """Render a view into scrollback history + screen buffer."""
        visible_rows = self._screen.lines
        sb = self._scrollback
        sb_len = len(sb)

        # Build a combined virtual line list: scrollback + current screen rows
        # Current screen rows
        screen_rows = []
        for row in range(self._screen.lines):
            line_buf = self._screen.buffer[row]
            line_data = []
            for col in range(cols):
                char = line_buf[col]
                ch = char.data if char.data else " "
                style = _char_style(char)
                line_data.append((ch, style))
            screen_rows.append(line_data)

        total_lines = sb_len + len(screen_rows)

        # Viewport: the last `visible_rows` lines at offset
        # viewport_end = total_lines - scroll_offset
        # viewport_start = viewport_end - visible_rows
        viewport_end = total_lines - self._scroll_offset
        viewport_start = max(0, viewport_end - visible_rows)

        text = Text()
        first = True
        for i in range(viewport_start, min(viewport_end, total_lines)):
            if not first:
                text.append("\n")
            first = False
            if i < sb_len:
                # From scrollback
                for ch, style in sb[i]:
                    text.append(ch, style=style)
            else:
                # From current screen buffer
                for ch, style in screen_rows[i - sb_len]:
                    text.append(ch, style=style)

        # Show a scroll indicator
        if viewport_start < sb_len:
            indicator = " [{}] ".format(t("scrollback_indicator", n=str(self._scroll_offset)))
            text.append("\n")
            text.append(indicator, style="bold #d29922 on #21262d")

        self._cached_text = text
        self._last_content_row = -1  # no cursor in scrollback view
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
        self._capture_new_history()
        # New output resets scroll to live view
        if self._scroll_offset > 0:
            self._scroll_offset = 0
        self._schedule_render()

    def write_line(self, text):
        # type: (str) -> None
        """Write a system message as a line in the terminal."""
        self._stream.feed(text + "\r\n")
        self._capture_new_history()
        if self._scroll_offset > 0:
            self._scroll_offset = 0
        self._schedule_render()

    def clear_output(self):
        # type: () -> None
        """Reset the virtual terminal screen."""
        self._screen.reset()
        self._cached_text = None
        self._render_pending = False
        self._scrollback.clear()
        self._prev_history_len = 0
        self._scroll_offset = 0
        try:
            widget = self.query_one("#terminal-content", Static)
            widget.update("")
        except Exception:
            pass

    def scroll_up(self, lines=3):
        # type: (int) -> None
        """Scroll up into history (for key-based scrolling)."""
        max_offset = len(self._scrollback)
        if max_offset == 0:
            return
        self._scroll_offset = min(self._scroll_offset + lines, max_offset)
        self._render_content()

    def scroll_down(self, lines=3):
        # type: (int) -> None
        """Scroll down toward live view (for key-based scrolling)."""
        if self._scroll_offset <= 0:
            return
        self._scroll_offset = max(self._scroll_offset - lines, 0)
        self._render_content()
