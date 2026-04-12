#!/usr/bin/env bash
set -euo pipefail

VERSION="0.0.1-beta"
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

# Check for docker
if ! command -v docker &> /dev/null; then
    echo "Error: docker not found. Please install docker first."
    exit 1
fi

# Check docker daemon
if ! docker info &> /dev/null; then
    echo "Error: docker daemon is not running. Please start docker first."
    exit 1
fi

echo "=== Tuim Linux AMD64 Build ==="
echo ""

# Build for Linux amd64 using docker buildx
echo "--- Building linux-amd64 ---"
docker buildx build \
    --platform linux/amd64 \
    -f Dockerfile.build \
    --output type=local,dest=dist-linux-amd64 \
    --progress=plain \
    .

# Extract and rename
mkdir -p dist
cp dist-linux-amd64/app/dist/tuim "dist/tuim-v${VERSION}-linux-amd64"
rm -rf dist-linux-amd64

echo ""
echo "=== Build Complete ==="
ls -lh dist/tuim-v${VERSION}-linux-amd64
echo ""
echo "Binary location: dist/tuim-v${VERSION}-linux-amd64"
