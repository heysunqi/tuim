"""Tests for YAML configuration loading and saving."""
import os
import tempfile

import yaml

from tuim.config import load_connections, save_connections
from tuim.models import Connection, K8sConfig, Protocol, SSHConfig


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


def test_save_and_load_k8s_token_roundtrip():
    """K8s connection with token auth should survive save/load round-trip."""
    with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
        path = f.name

    try:
        connections = [
            Connection(
                name="k8s-token-test",
                host="10.0.0.100",
                protocol=Protocol.K8S,
                port=6443,
                description="Token auth cluster",
                k8s_config=K8sConfig(
                    token="my-secret-token",
                    insecure_skip_tls_verify=True,
                    namespace="kube-system",
                    command="/bin/bash",
                ),
            ),
        ]

        save_connections(connections, config_path=path)

        # Verify raw YAML
        with open(path, "r") as f:
            raw = yaml.safe_load(f)
        k8s_data = raw["connections"][0]["k8s"]
        assert k8s_data["token"] == "my-secret-token"
        assert k8s_data["insecure_skip_tls_verify"] is True

        # Load back
        loaded_conns, _ = load_connections(path)
        assert len(loaded_conns) == 1
        conn = loaded_conns[0]
        assert conn.name == "k8s-token-test"
        assert conn.host == "10.0.0.100"
        assert conn.port == 6443
        assert conn.protocol == Protocol.K8S
        assert conn.k8s_config is not None
        assert conn.k8s_config.token == "my-secret-token"
        assert conn.k8s_config.insecure_skip_tls_verify is True
        assert conn.k8s_config.namespace == "kube-system"
    finally:
        if os.path.exists(path):
            os.unlink(path)


def test_save_and_load_ssh_jump_roundtrip():
    """SSH connection with jump host should survive save/load round-trip."""
    with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
        path = f.name

    try:
        connections = [
            Connection(
                name="jump-test",
                host="10.0.0.50",
                protocol=Protocol.SSH,
                port=22,
                description="Via jump host",
                ssh_config=SSHConfig(
                    username="admin",
                    private_key_path="~/.ssh/id_rsa",
                    jump_host="bastion.example.com",
                    jump_port=2222,
                    jump_username="jumper",
                    jump_password="jumppass",
                    jump_private_key_path="~/.ssh/jump_key",
                ),
            ),
        ]

        save_connections(connections, config_path=path)

        # Verify raw YAML
        with open(path, "r") as f:
            raw = yaml.safe_load(f)
        ssh_data = raw["connections"][0]["ssh"]
        assert ssh_data["jump_host"] == "bastion.example.com"
        assert ssh_data["jump_port"] == 2222
        assert ssh_data["jump_username"] == "jumper"
        assert ssh_data["jump_password"] == "jumppass"
        assert ssh_data["jump_private_key_path"] == "~/.ssh/jump_key"

        # Load back
        loaded_conns, _ = load_connections(path)
        assert len(loaded_conns) == 1
        conn = loaded_conns[0]
        assert conn.name == "jump-test"
        assert conn.ssh_config is not None
        assert conn.ssh_config.jump_host == "bastion.example.com"
        assert conn.ssh_config.jump_port == 2222
        assert conn.ssh_config.jump_username == "jumper"
        assert conn.ssh_config.jump_password == "jumppass"
        assert conn.ssh_config.jump_private_key_path == "~/.ssh/jump_key"
        assert conn.ssh_config.username == "admin"
        assert conn.ssh_config.private_key_path == "~/.ssh/id_rsa"
    finally:
        if os.path.exists(path):
            os.unlink(path)
