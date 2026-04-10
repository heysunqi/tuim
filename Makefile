VERSION := 0.0.1-beta
IMAGE_NAME := trelay-build
DOCKERFILE := Dockerfile.build

# ============================================================
# Local build
# ============================================================
build:
	@bash scripts/build.sh

build-amd64:
	@bash scripts/build-linux-amd64.sh

test:
	.venv/bin/pytest tests/ -v

# ============================================================
# Auto-detect container runtime (podman > docker)
# ============================================================
build-container:
	@bash scripts/docker-build.sh

# ============================================================
# Podman commands
# ============================================================
podman-build-amd64:
	podman build --arch amd64 -f $(DOCKERFILE) --tag $(IMAGE_NAME)-amd64:latest --progress=plain .
	podman create --name trelay-extract-amd64 $(IMAGE_NAME)-amd64:latest
	mkdir -p dist
	podman cp trelay-extract-amd64:/app/dist/trelay dist/trelay-v$(VERSION)-linux-amd64
	podman rm trelay-extract-amd64 >/dev/null 2>&1 || true
	podman rmi $(IMAGE_NAME)-amd64:latest >/dev/null 2>&1 || true
	@echo "==> dist/trelay-v$(VERSION)-linux-amd64"

podman-build-arm64:
	podman build --arch arm64 -f $(DOCKERFILE) --tag $(IMAGE_NAME)-arm64:latest --progress=plain .
	podman create --name trelay-extract-arm64 $(IMAGE_NAME)-arm64:latest
	mkdir -p dist
	podman cp trelay-extract-arm64:/app/dist/trelay dist/trelay-v$(VERSION)-linux-arm64
	podman rm trelay-extract-arm64 >/dev/null 2>&1 || true
	podman rmi $(IMAGE_NAME)-arm64:latest >/dev/null 2>&1 || true
	@echo "==> dist/trelay-v$(VERSION)-linux-arm64"

podman-build-all: podman-build-amd64 podman-build-arm64
	@echo "=== Podman build complete ==="
	@ls -lh dist/trelay-v$(VERSION)-linux-*

podman-clean:
	-podman rm trelay-extract-amd64 trelay-extract-arm64 2>/dev/null || true
	-podman rmi $(IMAGE_NAME)-amd64:latest $(IMAGE_NAME)-arm64:latest 2>/dev/null || true

# ============================================================
# Docker Desktop commands (uses buildx)
# ============================================================
docker-build-amd64:
	docker buildx build --platform linux/amd64 -f $(DOCKERFILE) \
		--output type=local,dest=dist-linux-amd64 --progress=plain .
	mkdir -p dist
	cp dist-linux-amd64/app/dist/trelay dist/trelay-v$(VERSION)-linux-amd64
	rm -rf dist-linux-amd64
	@echo "==> dist/trelay-v$(VERSION)-linux-amd64"

docker-build-arm64:
	docker buildx build --platform linux/arm64 -f $(DOCKERFILE) \
		--output type=local,dest=dist-linux-arm64 --progress=plain .
	mkdir -p dist
	cp dist-linux-arm64/app/dist/trelay dist/trelay-v$(VERSION)-linux-arm64
	rm -rf dist-linux-arm64
	@echo "==> dist/trelay-v$(VERSION)-linux-arm64"

docker-build-all: docker-build-amd64 docker-build-arm64
	@echo "=== Docker Desktop build complete ==="
	@ls -lh dist/trelay-v$(VERSION)-linux-*

docker-clean:
	rm -rf dist-linux-amd64 dist-linux-arm64

# ============================================================
# Common
# ============================================================
dist-clean:
	rm -rf dist dist-linux-*

clean: podman-clean docker-clean dist-clean

.PHONY: build build-amd64 test build-container \
        podman-build-amd64 podman-build-arm64 podman-build-all podman-clean \
        docker-build-amd64 docker-build-arm64 docker-build-all docker-clean \
        dist-clean clean
