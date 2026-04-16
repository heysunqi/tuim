"""YAML configuration loader/saver for Tuim."""
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import yaml

from tuim.models import (
    Connection,
    ConnectionStatus,
    K8sConfig,
    Protocol,
    RDPConfig,
    SSHConfig,
    TelnetConfig,
    VNCConfig,
)

DEFAULT_CONFIG_DIR = os.path.join(str(Path.home()), ".config", "tuim")
DEFAULT_CONFIG_PATH = os.path.join(DEFAULT_CONFIG_DIR, "connections.yaml")

DEFAULT_SETTINGS = {
    "health_check_interval": 30,
}


def get_config_path(custom_path=None):
    # type: (Optional[str]) -> str
    """Return the config file path."""
    if custom_path:
        return custom_path
    return DEFAULT_CONFIG_PATH


def ensure_config_dir(config_path=None):
    # type: (Optional[str]) -> None
    """Ensure the config directory exists."""
    path = get_config_path(config_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)


def _parse_connection(data):
    # type: (dict) -> Connection
    """Parse a connection dict from YAML into a Connection object."""
    protocol = Protocol(data.get("protocol", "ssh"))

    last_connected = data.get("last_connected")
    if isinstance(last_connected, str) and last_connected:
        try:
            last_connected = datetime.fromisoformat(last_connected)
        except (ValueError, TypeError):
            last_connected = None
    elif isinstance(last_connected, datetime):
        pass
    else:
        last_connected = None

    ssh_config = None
    rdp_config = None
    vnc_config = None
    telnet_config = None
    k8s_config = None

    if protocol == Protocol.SSH and "ssh" in data:
        s = data["ssh"]
        ssh_config = SSHConfig(
            username=s.get("username", ""),
            password=s.get("password", ""),
            private_key_path=s.get("private_key_path", ""),
            jump_host=s.get("jump_host", ""),
            jump_port=s.get("jump_port", 22),
            jump_username=s.get("jump_username", ""),
            jump_password=s.get("jump_password", ""),
            jump_private_key_path=s.get("jump_private_key_path", ""),
        )

    if protocol == Protocol.RDP and "rdp" in data:
        r = data["rdp"]
        rdp_config = RDPConfig(
            username=r.get("username", ""),
            password=r.get("password", ""),
            domain=r.get("domain", ""),
        )

    if protocol == Protocol.VNC and "vnc" in data:
        v = data["vnc"]
        vnc_config = VNCConfig(password=v.get("password", ""))

    if protocol == Protocol.TELNET and "telnet" in data:
        t = data["telnet"]
        telnet_config = TelnetConfig(
            username=t.get("username", ""),
            password=t.get("password", ""),
        )

    if protocol == Protocol.K8S and "k8s" in data:
        k = data["k8s"]
        k8s_config = K8sConfig(
            kubeconfig=k.get("kubeconfig", ""),
            context=k.get("context", ""),
            namespace=k.get("namespace", "default"),
            pod=k.get("pod", ""),
            container=k.get("container", ""),
            command=k.get("command", "/bin/sh"),
            token=k.get("token", ""),
            insecure_skip_tls_verify=bool(k.get("insecure_skip_tls_verify", False)),
        )

    return Connection(
        name=data.get("name", ""),
        host=data.get("host", ""),
        protocol=protocol,
        port=data.get("port", 0),
        description=data.get("description", ""),
        last_connected=last_connected,
        status=ConnectionStatus(data.get("status", "unknown")),
        ssh_config=ssh_config,
        rdp_config=rdp_config,
        vnc_config=vnc_config,
        telnet_config=telnet_config,
        k8s_config=k8s_config,
    )


def _serialize_connection(conn):
    # type: (Connection) -> dict
    """Serialize a Connection to a YAML-compatible dict."""
    data = {
        "name": conn.name,
        "host": conn.host,
        "protocol": conn.protocol.value,
        "port": conn.port,
        "description": conn.description,
    }

    if conn.last_connected:
        data["last_connected"] = conn.last_connected.isoformat()

    if conn.ssh_config:
        cfg = {}
        if conn.ssh_config.username:
            cfg["username"] = conn.ssh_config.username
        if conn.ssh_config.password:
            cfg["password"] = conn.ssh_config.password
        if conn.ssh_config.private_key_path:
            cfg["private_key_path"] = conn.ssh_config.private_key_path
        if conn.ssh_config.jump_host:
            cfg["jump_host"] = conn.ssh_config.jump_host
        if conn.ssh_config.jump_port and conn.ssh_config.jump_port != 22:
            cfg["jump_port"] = conn.ssh_config.jump_port
        if conn.ssh_config.jump_username:
            cfg["jump_username"] = conn.ssh_config.jump_username
        if conn.ssh_config.jump_password:
            cfg["jump_password"] = conn.ssh_config.jump_password
        if conn.ssh_config.jump_private_key_path:
            cfg["jump_private_key_path"] = conn.ssh_config.jump_private_key_path
        if cfg:
            data["ssh"] = cfg

    if conn.rdp_config:
        cfg = {}
        if conn.rdp_config.username:
            cfg["username"] = conn.rdp_config.username
        if conn.rdp_config.password:
            cfg["password"] = conn.rdp_config.password
        if conn.rdp_config.domain:
            cfg["domain"] = conn.rdp_config.domain
        if cfg:
            data["rdp"] = cfg

    if conn.vnc_config:
        cfg = {}
        if conn.vnc_config.password:
            cfg["password"] = conn.vnc_config.password
        if cfg:
            data["vnc"] = cfg

    if conn.telnet_config:
        cfg = {}
        if conn.telnet_config.username:
            cfg["username"] = conn.telnet_config.username
        if conn.telnet_config.password:
            cfg["password"] = conn.telnet_config.password
        if cfg:
            data["telnet"] = cfg

    if conn.k8s_config:
        cfg = {}
        if conn.k8s_config.kubeconfig:
            cfg["kubeconfig"] = conn.k8s_config.kubeconfig
        if conn.k8s_config.context:
            cfg["context"] = conn.k8s_config.context
        if conn.k8s_config.namespace:
            cfg["namespace"] = conn.k8s_config.namespace
        if conn.k8s_config.pod:
            cfg["pod"] = conn.k8s_config.pod
        if conn.k8s_config.container:
            cfg["container"] = conn.k8s_config.container
        if conn.k8s_config.command:
            cfg["command"] = conn.k8s_config.command
        if conn.k8s_config.token:
            cfg["token"] = conn.k8s_config.token
        if conn.k8s_config.insecure_skip_tls_verify:
            cfg["insecure_skip_tls_verify"] = True
        if cfg:
            data["k8s"] = cfg

    return data


def load_connections(config_path=None):
    # type: (Optional[str]) -> tuple
    """Load connections from YAML config file. Returns (connections, settings)."""
    path = get_config_path(config_path)

    if not os.path.exists(path):
        return [], DEFAULT_SETTINGS.copy()

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data:
        return [], DEFAULT_SETTINGS.copy()

    settings = data.get("settings", DEFAULT_SETTINGS.copy())
    raw_connections = data.get("connections", [])
    connections = [_parse_connection(c) for c in raw_connections]

    return connections, settings


def save_connections(connections, settings=None, config_path=None):
    # type: (List[Connection], Optional[dict], Optional[str]) -> None
    """Save connections to YAML config file."""
    path = get_config_path(config_path)
    ensure_config_dir(config_path)

    if settings is None:
        settings = DEFAULT_SETTINGS.copy()

    data = {
        "version": 1,
        "settings": settings,
        "connections": [_serialize_connection(c) for c in connections],
    }

    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
