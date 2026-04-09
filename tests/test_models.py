"""Tests for the data models."""
from datetime import datetime, timedelta

from trelay.models import (
    Connection,
    ConnectionStatus,
    DEFAULT_PORTS,
    Protocol,
    PROTOCOL_COLORS,
    SSHConfig,
    STATUS_COLORS,
)


def test_protocol_values():
    assert Protocol.SSH.value == "ssh"
    assert Protocol.RDP.value == "rdp"
    assert Protocol.VNC.value == "vnc"
    assert Protocol.TELNET.value == "telnet"
    assert Protocol.K8S.value == "k8s"


def test_connection_status_values():
    assert ConnectionStatus.ONLINE.value == "online"
    assert ConnectionStatus.OFFLINE.value == "offline"
    assert ConnectionStatus.ERROR.value == "error"
    assert ConnectionStatus.UNKNOWN.value == "unknown"


def test_default_ports():
    assert DEFAULT_PORTS[Protocol.SSH] == 22
    assert DEFAULT_PORTS[Protocol.RDP] == 3389
    assert DEFAULT_PORTS[Protocol.VNC] == 5900
    assert DEFAULT_PORTS[Protocol.TELNET] == 23
    assert DEFAULT_PORTS[Protocol.K8S] == 0


def test_protocol_colors():
    for proto in Protocol:
        assert proto in PROTOCOL_COLORS


def test_status_colors():
    for status in ConnectionStatus:
        assert status in STATUS_COLORS


def test_connection_defaults():
    conn = Connection(name="test", host="1.2.3.4", protocol=Protocol.SSH, port=22)
    assert conn.description == ""
    assert conn.last_connected is None
    assert conn.status == ConnectionStatus.UNKNOWN
    assert conn.ssh_config is None


def test_connection_get_protocol_config(ssh_connection):
    config = ssh_connection.get_protocol_config()
    assert isinstance(config, SSHConfig)
    assert config.username == "root"


def test_display_last_connected_never():
    conn = Connection(name="t", host="h", protocol=Protocol.SSH, port=22)
    assert conn.display_last_connected() == "Never"


def test_display_last_connected_just_now():
    conn = Connection(
        name="t", host="h", protocol=Protocol.SSH, port=22,
        last_connected=datetime.now(),
    )
    assert conn.display_last_connected() == "Just now"


def test_display_last_connected_minutes():
    conn = Connection(
        name="t", host="h", protocol=Protocol.SSH, port=22,
        last_connected=datetime.now() - timedelta(minutes=5),
    )
    assert "min ago" in conn.display_last_connected()


def test_display_last_connected_hours():
    conn = Connection(
        name="t", host="h", protocol=Protocol.SSH, port=22,
        last_connected=datetime.now() - timedelta(hours=3),
    )
    assert "hr ago" in conn.display_last_connected()


def test_display_last_connected_days():
    conn = Connection(
        name="t", host="h", protocol=Protocol.SSH, port=22,
        last_connected=datetime.now() - timedelta(days=2),
    )
    assert "days ago" in conn.display_last_connected()
