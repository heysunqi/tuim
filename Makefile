VERSION := 0.0.1-beta

build:
	@bash scripts/build.sh

build-docker:
	@bash scripts/docker-build.sh

build-amd64:
	@bash scripts/build-linux-amd64.sh

test:
	.venv/bin/pytest tests/ -v
