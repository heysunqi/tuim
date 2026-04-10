# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Trelay standalone binary."""
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

PROJECT_ROOT = os.path.abspath('.')
SRC_TRELAY = os.path.join(PROJECT_ROOT, 'src', 'trelay')

# Collect Textual's CSS/templates
textual_datas = collect_data_files('textual')
textual_hidden = collect_submodules('textual')

# Trelay data files
trelay_datas = [
    (os.path.join(SRC_TRELAY, 'styles', 'theme.tcss'), 'trelay/styles'),
    (os.path.join(SRC_TRELAY, 'assets', 'example_connections.yaml'), 'trelay/assets'),
]

a = Analysis(
    [os.path.join(SRC_TRELAY, '__main__.py')],
    pathex=[os.path.join(PROJECT_ROOT, 'src')],
    binaries=[],
    datas=trelay_datas + textual_datas,
    hiddenimports=[
        # trelay modules (lazy imports)
        'trelay', 'trelay.app', 'trelay.config', 'trelay.models', 'trelay.i18n',
        'trelay.protocols', 'trelay.protocols.base', 'trelay.protocols.ssh',
        'trelay.protocols.rdp', 'trelay.protocols.vnc', 'trelay.protocols.telnet',
        'trelay.protocols.k8s',
        'trelay.services', 'trelay.services.session_manager',
        'trelay.services.health_checker', 'trelay.services.k8s_service',
        'trelay.screens', 'trelay.screens.add_connection',
        'trelay.screens.delete_confirm', 'trelay.screens.help_screen',
        'trelay.screens.shell_picker', 'trelay.screens.k8s_picker',
        'trelay.widgets', 'trelay.widgets.header_bar',
        'trelay.widgets.connection_table', 'trelay.widgets.terminal_view',
        'trelay.widgets.k8s_resource_view', 'trelay.widgets.status_bar',
        'trelay.widgets.command_bar', 'trelay.widgets.protocol_badge',
        # dependencies
        'asyncssh', 'telnetlib3', 'pyte', 'yaml', 'textual',
    ] + textual_hidden,
    hookspath=[],
    excludes=['pytest', 'textual_dev', 'tkinter', '_tkinter'],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name='trelay',
    debug=False,
    strip=False,
    upx=True,
    console=True,
)
