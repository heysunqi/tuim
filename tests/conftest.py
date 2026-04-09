"""Shared test fixtures for Trelay."""
import pytest

from trelay.models import (
    Connection,
    ConnectionStatus,
    K8sConfig,
    Protocol,
    RDPConfig,
    SSHConfig,
    TelnetConfig,
    VNCConfig,
)


@pytest.fixture
def ssh_connection():
    return Connection(
        name="test-ssh",
        host="192.168.1.100",
        protocol=Protocol.SSH,
        port=22,
        description="Test SSH Server",
        ssh_config=SSHConfig(username="root", private_key_path="~/.ssh/id_rsa"),
    )


@pytest.fixture
def rdp_connection():
    return Connection(
        name="test-rdp",
        host="192.168.1.200",
        protocol=Protocol.RDP,
        port=3389,
        description="Test RDP Desktop",
        rdp_config=RDPConfig(username="admin", domain="CORP"),
    )


@pytest.fixture
def vnc_connection():
    return Connection(
        name="test-vnc",
        host="192.168.1.150",
        protocol=Protocol.VNC,
        port=5900,
        description="Test VNC Workstation",
        vnc_config=VNCConfig(password="secret"),
    )


@pytest.fixture
def telnet_connection():
    return Connection(
        name="test-telnet",
        host="192.168.0.1",
        protocol=Protocol.TELNET,
        port=23,
        description="Test Telnet Router",
        telnet_config=TelnetConfig(username="admin"),
    )


@pytest.fixture
def k8s_connection():
    return Connection(
        name="test-k8s",
        host="",
        protocol=Protocol.K8S,
        port=0,
        description="Test K8s Pod",
        k8s_config=K8sConfig(
            context="test-cluster",
            namespace="default",
            pod="app-pod-123",
            command="/bin/sh",
        ),
    )


@pytest.fixture
def sample_connections(ssh_connection, rdp_connection, vnc_connection, telnet_connection, k8s_connection):
    return [ssh_connection, rdp_connection, vnc_connection, telnet_connection, k8s_connection]
