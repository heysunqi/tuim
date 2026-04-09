# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is Trelay

Trelay is a k9s-style TUI remote connection manager for SSH, RDP, VNC, Telnet and Kubernetes, built on Python's Textual framework. It uses vim-style keyboard navigation and a dark theme. UI strings are in Chinese.

## Commands

```bash
# Install (dev mode)
pip install -e ".[dev]"

# Run
trelay                          # default config: ~/.config/trelay/connections.yaml
trelay --config path/to.yaml    # custom config
python -m trelay                # alternative

# Tests
pytest tests/ -v                # all tests
pytest tests/test_models.py -v  # single file
pytest tests/test_models.py::test_protocol_values  # single test

# Textual dev console (useful for debugging TUI)
textual console
textual run --dev src/trelay/__main__.py
```

No linter or formatter is configured.

## Architecture

**Three-mode UI** managed by `ContentSwitcher` in `app.py`:
- **List mode** — `ConnectionTable` DataTable with `:` commands and `/` search
- **K8s browser** — `K8sResourceView` for browsing pods/services/deployments/namespaces
- **Terminal mode** — `TerminalView` with pyte-backed terminal emulation and scrollback

`TrelayApp` (`app.py`) is the central orchestrator. All key events flow through `on_key()` which dispatches to the active mode handler. Modal screens (add/edit/delete/help/shell picker) are pushed onto Textual's screen stack.

**Protocol handler pattern** (`protocols/base.py`):
- `ProtocolHandler` ABC defines: `connect()`, `disconnect()`, `send_input()`, `check_health()`, `is_interactive`
- Interactive handlers (SSH, Telnet, K8s) stream output via `_emit_output()` callback into `TerminalView`
- Non-interactive handlers (RDP, VNC) launch external OS clients
- K8s handler uses `os.fork()` + PTY to run kubectl subprocess

**SessionManager** (`services/session_manager.py`): manages one active session at a time, creates the correct handler from `Connection.protocol`, routes callbacks.

**Config**: YAML at `~/.config/trelay/connections.yaml`. First-run copies from `config/connections.example.yaml`.

## Key Conventions

- Python 3.9+ compatible; many methods use comment-style type hints (`# type: (str) -> None`)
- Lazy imports in `app.py` and `session_manager.py` to avoid circular deps
- Screens are `ModalScreen` subclasses that `dismiss()` with a result value; the caller passes a callback to `push_screen()`
- `_k8s_return` flag tracks whether terminal mode was entered from K8s browser (affects return-on-disconnect behavior)
- `_shell_retry_pending` flag prevents auto-return while the shell picker modal is open
- Build backend is hatchling with src-layout (`src/trelay/`)
