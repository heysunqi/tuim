#!/usr/bin/env bash
set -euo pipefail

VERSION="0.0.1-beta"
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

# Optional: force runtime via argument (podman or docker)
FORCE_RUNTIME="${1:-auto}"

# Detect container runtime: podman or docker
detect_runtime() {
    if [[ "$FORCE_RUNTIME" == "podman" ]]; then
        RUNTIME="podman"
        RUNTIME_BUILD="build"
        PLATFORM_FLAG="--arch"
        USE_OUTPUT="false"
    elif [[ "$FORCE_RUNTIME" == "docker" ]]; then
        RUNTIME="docker"
        RUNTIME_BUILD="buildx build"
        PLATFORM_FLAG="--platform"
        USE_OUTPUT="true"
    elif command -v podman &> /dev/null; then
        RUNTIME="podman"
        RUNTIME_BUILD="build"
        PLATFORM_FLAG="--arch"
        USE_OUTPUT="false"
    elif command -v docker &> /dev/null; then
        RUNTIME="docker"
        RUNTIME_BUILD="buildx build"
        PLATFORM_FLAG="--platform"
        USE_OUTPUT="true"
    else
        echo "Error: Neither podman nor docker found"
        exit 1
    fi
}

# Build for a specific architecture
build_arch() {
    local arch="$1"
    local img_name="tuim-build-${arch}:latest"
    local container_name="tuim-extract-${arch}"

    echo "--- Building linux-${arch} ---"

    if [[ "$USE_OUTPUT" == "true" ]]; then
        # Docker buildx with direct output
        ${RUNTIME} ${RUNTIME_BUILD} ${PLATFORM_FLAG} linux/${arch} \
            -f Dockerfile.build \
            --output type=local,dest="dist-linux-${arch}" \
            --progress=plain \
            .
        # Extract and rename
        mkdir -p dist
        cp "dist-linux-${arch}/app/dist/tuim" "dist/tuim-v${VERSION}-linux-${arch}"
        rm -rf "dist-linux-${arch}"
    else
        # Podman (no --output support in remote mode)
        # Build image
        ${RUNTIME} ${RUNTIME_BUILD} ${PLATFORM_FLAG} ${arch} \
            -f Dockerfile.build \
            --tag "${img_name}" \
            --progress=plain \
            .

        # Create container (no run) to extract files
        ${RUNTIME} create --name "${container_name}" "${img_name}"

        # Copy binary from container
        mkdir -p dist
        ${RUNTIME} cp "${container_name}:/app/dist/tuim" "dist/tuim-v${VERSION}-linux-${arch}"

        # Cleanup
        ${RUNTIME} rm "${container_name}" >/dev/null 2>&1 || true
        ${RUNTIME} rmi "${img_name}" >/dev/null 2>&1 || true
    fi
}

# Initialize runtime
detect_runtime

echo "=== Tuim Multi-Arch Build using ${RUNTIME} ==="

mkdir -p dist

# Build for Linux amd64
build_arch amd64

# Build for Linux arm64
build_arch arm64

echo ""
echo "=== Build Complete ==="
ls -lh dist/tuim-v*
