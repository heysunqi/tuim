"""Header bar widget for the Trelay TUI."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widget import Widget
from textual.widgets import Static


class HeaderBar(Widget):
    """Top header bar with logo and keyboard shortcut hints."""

    _LIST_SHORTCUTS = (
        "[#8b949e]"
        "\\[[#6e7681]\u2191\u2193[/]] 导航  "
        "\\[[#6e7681]Enter[/]] 连接  "
        "\\[[#6e7681]Ctrl+D[/]] 断开  "
        "\\[[#6e7681]a[/]] 新增  "
        "\\[[#6e7681]e[/]] 编辑  "
        "\\[[#6e7681]d[/]] 删除  "
        "\\[[#6e7681]/[/]] 搜索  "
        "\\[[#6e7681]:q[/]] 退出"
        "[/]"
    )

    _K8S_SHORTCUTS = (
        "[#8b949e]"
        "\\[[#6e7681]j/k[/]] 导航  "
        "\\[[#6e7681]Enter[/]] Exec  "
        "\\[[#6e7681]:pod[/]] Pods  "
        "\\[[#6e7681]:svc[/]] 服务  "
        "\\[[#6e7681]:deploy[/]] 部署  "
        "\\[[#6e7681]:ns[/]] 命名空间  "
        "\\[[#6e7681]:q[/]] 返回  "
        "\\[[#6e7681]:q![/]] 退出"
        "[/]"
    )

    def __init__(self, **kwargs):
        # type: (...) -> None
        super().__init__(id="header-bar", **kwargs)

    def compose(self):
        # type: () -> ComposeResult
        with Horizontal():
            yield Static(
                "[bold #39c5cf]\u2b21 Trelay[/]",
                id="header-info",
                markup=True,
            )
            yield Static(
                self._LIST_SHORTCUTS,
                id="header-shortcuts",
                markup=True,
            )

    def set_k8s_mode(self):
        # type: () -> None
        try:
            shortcuts = self.query_one("#header-shortcuts", Static)
            shortcuts.update(self._K8S_SHORTCUTS)
        except Exception:
            pass

    def set_list_mode(self):
        # type: () -> None
        try:
            shortcuts = self.query_one("#header-shortcuts", Static)
            shortcuts.update(self._LIST_SHORTCUTS)
        except Exception:
            pass
