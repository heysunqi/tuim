"""Tests for the data models."""
from datetime import datetime, timedelta

from tuim.models import (
    Connection,
    ConnectionStatus,
    DEFAULT_PORTS,
    K8sConfig,
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


def test_kubectl_auth_args_token_mode():
    """Token mode should produce --server, --token, and optionally --insecure-skip-tls-verify."""
    cfg = K8sConfig(token="my-token", insecure_skip_tls_verify=True)
    args = cfg.kubectl_auth_args(host="10.0.0.1", port=6443)
    assert "--server" in args
    assert "https://10.0.0.1:6443" in args
    assert "--token" in args
    assert "my-token" in args
    assert "--insecure-skip-tls-verify" in args


def test_kubectl_auth_args_token_no_skip_tls():
    """Token mode without skip-TLS should not include --insecure-skip-tls-verify."""
    cfg = K8sConfig(token="my-token", insecure_skip_tls_verify=False)
    args = cfg.kubectl_auth_args(host="10.0.0.1", port=6443)
    assert "--insecure-skip-tls-verify" not in args
    assert "--token" in args


def test_kubectl_auth_args_kubeconfig_mode():
    """Kubeconfig mode should produce --kubeconfig and --context."""
    cfg = K8sConfig(kubeconfig="/home/user/.kube/config", context="my-ctx")
    args = cfg.kubectl_auth_args()
    assert "--kubeconfig" in args
    assert "--context" in args
    assert "my-ctx" in args
    # Should NOT have token args
    assert "--token" not in args
    assert "--server" not in args


def test_kubectl_auth_args_empty():
    """Empty config should produce no arguments."""
    cfg = K8sConfig()
    args = cfg.kubectl_auth_args()
    assert args == []


def test_kubectl_auth_args_token_no_port():
    """Token mode without port should produce server URL without port."""
    cfg = K8sConfig(token="tok")
    args = cfg.kubectl_auth_args(host="api.example.com", port=0)
    assert "https://api.example.com" in args
    # Ensure no port in the URL
    for arg in args:
        if arg.startswith("https://"):
            assert arg == "https://api.example.com"
