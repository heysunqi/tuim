"""Data models for Trelay."""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

from trelay.i18n import t


class Protocol(str, Enum):
    SSH = "ssh"
    RDP = "rdp"
    VNC = "vnc"
    TELNET = "telnet"
    K8S = "k8s"


class ConnectionStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"
    UNKNOWN = "unknown"


# Protocol-specific default ports
DEFAULT_PORTS = {
    Protocol.SSH: 22,
    Protocol.RDP: 3389,
    Protocol.VNC: 5900,
    Protocol.TELNET: 23,
    Protocol.K8S: 0,
}

# Protocol display colors (for TCSS/Rich markup)
PROTOCOL_COLORS = {
    Protocol.SSH: "#3fb950",
    Protocol.RDP: "#58a6ff",
    Protocol.VNC: "#a371f7",
    Protocol.TELNET: "#d29922",
    Protocol.K8S: "#39c5cf",
}

STATUS_COLORS = {
    ConnectionStatus.ONLINE: "#3fb950",
    ConnectionStatus.OFFLINE: "#6e7681",
    ConnectionStatus.ERROR: "#f85149",
    ConnectionStatus.UNKNOWN: "#6e7681",
}


@dataclass
class SSHConfig:
    username: str = ""
    password: str = ""
    private_key_path: str = ""


@dataclass
class RDPConfig:
    username: str = ""
    password: str = ""
    domain: str = ""


@dataclass
class VNCConfig:
    password: str = ""


@dataclass
class TelnetConfig:
    username: str = ""
    password: str = ""


@dataclass
class K8sConfig:
    kubeconfig: str = ""
    context: str = ""
    namespace: str = "default"
    pod: str = ""
    container: str = ""
    command: str = "/bin/sh"


@dataclass
class Connection:
    name: str
    host: str
    protocol: Protocol
    port: int
    description: str = ""
    last_connected: Optional[datetime] = None
    status: ConnectionStatus = ConnectionStatus.UNKNOWN
    ssh_config: Optional[SSHConfig] = None
    rdp_config: Optional[RDPConfig] = None
    vnc_config: Optional[VNCConfig] = None
    telnet_config: Optional[TelnetConfig] = None
    k8s_config: Optional[K8sConfig] = None

    def get_protocol_config(self):
        """Return the protocol-specific config for this connection."""
        mapping = {
            Protocol.SSH: self.ssh_config,
            Protocol.RDP: self.rdp_config,
            Protocol.VNC: self.vnc_config,
            Protocol.TELNET: self.telnet_config,
            Protocol.K8S: self.k8s_config,
        }
        return mapping.get(self.protocol)

    def _resolve_k8s_server(self):
        """Parse kubeconfig to extract API server host and port for this connection.

        Returns (host, port) strings, or (None, None) on any failure.
        """
        cfg = self.k8s_config
        if cfg is None:
            return None, None
        try:
            import os
            import yaml
            from urllib.parse import urlparse

            kubeconfig_path = cfg.kubeconfig or os.environ.get(
                "KUBECONFIG", os.path.expanduser("~/.kube/config")
            )
            kubeconfig_path = os.path.expanduser(kubeconfig_path)
            with open(kubeconfig_path, "r") as f:
                kc = yaml.safe_load(f)
            if not kc:
                return None, None

            # Determine which context to use
            ctx_name = cfg.context or kc.get("current-context", "")
            # Find the context entry
            cluster_name = None
            for ctx in kc.get("contexts") or []:
                if ctx.get("name") == ctx_name:
                    cluster_name = (ctx.get("context") or {}).get("cluster")
                    break
            if not cluster_name:
                return None, None

            # Find the cluster entry
            for cl in kc.get("clusters") or []:
                if cl.get("name") == cluster_name:
                    server = (cl.get("cluster") or {}).get("server", "")
                    if server:
                        parsed = urlparse(server)
                        host = parsed.hostname or ""
                        port = str(parsed.port) if parsed.port else ""
                        return host, port
            return None, None
        except Exception:
            return None, None

    def display_host(self):
        """Return a display-friendly host string.

        For K8s connections: API server address from kubeconfig; falls back
        to context name, kubeconfig basename, or '(default)'.
        For other protocols: the raw host field.
        """
        if self.protocol == Protocol.K8S and self.k8s_config is not None:
            host, _ = self._resolve_k8s_server()
            if host:
                return host
            cfg = self.k8s_config
            if cfg.context:
                return cfg.context
            if cfg.kubeconfig:
                import os
                return os.path.basename(cfg.kubeconfig)
            return t("k8s_default_context")
        return self.host

    def display_port(self):
        """Return a display-friendly port string.

        For K8s connections: API server port from kubeconfig; falls back
        to default namespace.
        For other protocols: the port number as a string.
        """
        if self.protocol == Protocol.K8S and self.k8s_config is not None:
            _, port = self._resolve_k8s_server()
            if port:
                return port
            return self.k8s_config.namespace or "-"
        return str(self.port)

    def display_last_connected(self):
        """Return a human-readable last connected string."""
        if self.last_connected is None:
            return t("time_never")
        now = datetime.now()
        diff = now - self.last_connected
        seconds = int(diff.total_seconds())
        if seconds < 60:
            return t("time_just_now")
        elif seconds < 3600:
            minutes = seconds // 60
            return t("time_min_ago", n=str(minutes))
        elif seconds < 86400:
            hours = seconds // 3600
            return t("time_hr_ago", n=str(hours))
        else:
            days = seconds // 86400
            if days > 1:
                return t("time_days_ago", n=str(days))
            return t("time_day_ago", n=str(days))
