# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Tuim standalone binary."""
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

PROJECT_ROOT = os.path.abspath('.')
SRC_TUIM = os.path.join(PROJECT_ROOT, 'src', 'tuim')

# Collect Textual's CSS/templates
textual_datas = collect_data_files('textual')
textual_hidden = collect_submodules('textual')

# Tuim data files
tuim_datas = [
    (os.path.join(SRC_TUIM, 'styles', 'theme.tcss'), 'tuim/styles'),
    (os.path.join(SRC_TUIM, 'assets', 'example_connections.yaml'), 'tuim/assets'),
]

a = Analysis(
    [os.path.join(SRC_TUIM, '__main__.py')],
    pathex=[os.path.join(PROJECT_ROOT, 'src')],
    binaries=[],
    datas=tuim_datas + textual_datas,
    hiddenimports=[
        # tuim modules (lazy imports)
        'tuim', 'tuim.app', 'tuim.config', 'tuim.models', 'tuim.i18n',
        'tuim.protocols', 'tuim.protocols.base', 'tuim.protocols.ssh',
        'tuim.protocols.rdp', 'tuim.protocols.vnc', 'tuim.protocols.telnet',
        'tuim.protocols.k8s',
        'tuim.services', 'tuim.services.session_manager',
        'tuim.services.health_checker', 'tuim.services.k8s_service',
        'tuim.screens', 'tuim.screens.add_connection',
        'tuim.screens.delete_confirm', 'tuim.screens.help_screen',
        'tuim.screens.shell_picker', 'tuim.screens.k8s_picker',
        'tuim.widgets', 'tuim.widgets.header_bar',
        'tuim.widgets.connection_table', 'tuim.widgets.terminal_view',
        'tuim.widgets.k8s_resource_view', 'tuim.widgets.status_bar',
        'tuim.widgets.command_bar', 'tuim.widgets.protocol_badge',
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
    name='tuim',
    debug=False,
    strip=False,
    upx=True,
    console=True,
)
