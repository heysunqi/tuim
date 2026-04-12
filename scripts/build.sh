#!/usr/bin/env bash
set -euo pipefail

VERSION="0.0.1-beta"
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

# Detect OS/arch
OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
ARCH="$(uname -m)"
case "$OS" in linux) OS="linux" ;; darwin) OS="macos" ;; *) echo "Unsupported OS"; exit 1 ;; esac
case "$ARCH" in x86_64|amd64) ARCH="amd64" ;; aarch64|arm64) ARCH="arm64" ;; *) echo "Unsupported arch"; exit 1 ;; esac

OUTPUT="tuim-v${VERSION}-${OS}-${ARCH}"
echo "=== Building for ${OS}-${ARCH} ==="

# Setup venv
if [[ ! -d ".venv" ]]; then python3 -m venv .venv; fi
.venv/bin/pip install -e . --quiet
.venv/bin/pip install pyinstaller --quiet

# Build
.venv/bin/pyinstaller tuim.spec --noconfirm --clean
mv dist/tuim "dist/${OUTPUT}"

echo "Binary: dist/${OUTPUT}"
