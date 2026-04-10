#!/usr/bin/env bash
set -euo pipefail

VERSION="0.0.1-beta"
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

# Detect container runtime: podman or docker
if command -v podman &> /dev/null; then
    RUNTIME="podman"
    RUNTIME_BUILD="build"
    PLATFORM_FLAG="--arch"
    OUTPUT_FLAG="--output"
elif command -v docker &> /dev/null; then
    RUNTIME="docker"
    RUNTIME_BUILD="buildx build"
    PLATFORM_FLAG="--platform"
    OUTPUT_FLAG="--output"
else
    echo "Error: Neither podman nor docker found"
    exit 1
fi

echo "=== Trelay Multi-Arch Build using ${RUNTIME} ==="

# Build for Linux amd64
echo ""
echo "--- Building linux-amd64 ---"
${RUNTIME} ${RUNTIME_BUILD} ${PLATFORM_FLAG} amd64 \
    -f Dockerfile.build \
    ${OUTPUT_FLAG} type=local,dest=dist-linux-amd64 \
    --progress=plain \
    .

# Extract and rename
mkdir -p dist
cp dist-linux-amd64/app/dist/trelay "dist/trelay-v${VERSION}-linux-amd64"
rm -rf dist-linux-amd64

# Build for Linux arm64
echo ""
echo "--- Building linux-arm64 ---"
${RUNTIME} ${RUNTIME_BUILD} ${PLATFORM_FLAG} arm64 \
    -f Dockerfile.build \
    ${OUTPUT_FLAG} type=local,dest=dist-linux-arm64 \
    --progress=plain \
    .

# Extract and rename
cp dist-linux-arm64/app/dist/trelay "dist/trelay-v${VERSION}-linux-arm64"
rm -rf dist-linux-arm64

echo ""
echo "=== Build Complete ==="
ls -lh dist/trelay-v*
