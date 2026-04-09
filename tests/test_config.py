"""Tests for YAML configuration loading and saving."""
import os
import tempfile

import yaml

from trelay.config import load_connections, save_connections
from trelay.models import Connection, Protocol, SSHConfig


def test_load_nonexistent_file():
    connections, settings = load_connections("/tmp/nonexistent_trelay_test.yaml")
    assert connections == []
    assert "health_check_interval" in settings


def test_save_and_load_roundtrip():
    with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
        path = f.name

    try:
        connections = [
            Connection(
                name="test-server",
                host="10.0.0.1",
                protocol=Protocol.SSH,
                port=22,
                description="A test server",
                ssh_config=SSHConfig(username="admin", private_key_path="~/.ssh/key"),
            ),
        ]
        settings = {"health_check_interval": 60}

        save_connections(connections, settings, path)

        # Verify the file was written
        assert os.path.exists(path)
        with open(path, "r") as f:
            raw = yaml.safe_load(f)
        assert raw["version"] == 1
        assert len(raw["connections"]) == 1
        assert raw["connections"][0]["name"] == "test-server"

        # Load back
        loaded_conns, loaded_settings = load_connections(path)
        assert len(loaded_conns) == 1
        assert loaded_conns[0].name == "test-server"
        assert loaded_conns[0].host == "10.0.0.1"
        assert loaded_conns[0].protocol == Protocol.SSH
        assert loaded_conns[0].port == 22
        assert loaded_conns[0].ssh_config is not None
        assert loaded_conns[0].ssh_config.username == "admin"
        assert loaded_settings["health_check_interval"] == 60
    finally:
        if os.path.exists(path):
            os.unlink(path)


def test_save_empty_connections():
    with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
        path = f.name

    try:
        save_connections([], config_path=path)
        loaded_conns, _ = load_connections(path)
        assert loaded_conns == []
    finally:
        if os.path.exists(path):
            os.unlink(path)
