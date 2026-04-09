"""Kubernetes resource query service using kubectl."""
import asyncio
import json
import logging
import os
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

RESOURCE_ALIASES = {
    "po": "pods",
    "pod": "pods",
    "pods": "pods",
    "svc": "services",
    "service": "services",
    "services": "services",
    "deploy": "deployments",
    "deployment": "deployments",
    "deployments": "deployments",
    "sts": "statefulsets",
    "statefulset": "statefulsets",
    "statefulsets": "statefulsets",
    "ns": "namespaces",
    "namespace": "namespaces",
    "namespaces": "namespaces",
}

# Column definitions per resource type
RESOURCE_COLUMNS = {
    "pods": ["NAME", "READY", "STATUS", "RESTARTS", "AGE", "IP", "NODE"],
    "services": ["NAME", "TYPE", "CLUSTER-IP", "PORTS", "AGE"],
    "deployments": ["NAME", "READY", "UP-TO-DATE", "AVAILABLE", "AGE"],
    "statefulsets": ["NAME", "READY", "AGE"],
    "namespaces": ["NAME", "STATUS", "AGE"],
}


def _calc_age(creation_timestamp):
    # type: (str) -> str
    """Calculate a human-readable age from a creation timestamp."""
    from datetime import datetime, timezone

    try:
        created = datetime.fromisoformat(creation_timestamp.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        diff = now - created
        total_seconds = int(diff.total_seconds())
        if total_seconds < 60:
            return "{}s".format(total_seconds)
        elif total_seconds < 3600:
            return "{}m".format(total_seconds // 60)
        elif total_seconds < 86400:
            return "{}h".format(total_seconds // 3600)
        else:
            return "{}d".format(total_seconds // 86400)
    except Exception:
        return "?"


def _calc_restarts(container_statuses):
    # type: (list) -> str
    """Sum restart counts from container statuses."""
    if not container_statuses:
        return "0"
    total = sum(cs.get("restartCount", 0) for cs in container_statuses)
    return str(total)


def _calc_ready_pods(container_statuses):
    # type: (list) -> str
    """Calculate ready/total from container statuses."""
    if not container_statuses:
        return "0/0"
    ready = sum(1 for cs in container_statuses if cs.get("ready", False))
    total = len(container_statuses)
    return "{}/{}".format(ready, total)


def _calc_ready_deploy(status):
    # type: (dict) -> str
    """Calculate ready replicas for deployments."""
    ready = status.get("readyReplicas", 0)
    replicas = status.get("replicas", 0)
    return "{}/{}".format(ready, replicas)


def _calc_ready_sts(status):
    # type: (dict) -> str
    """Calculate ready replicas for statefulsets."""
    ready = status.get("readyReplicas", 0)
    replicas = status.get("replicas", 0)
    return "{}/{}".format(ready, replicas)


def _extract_ports(spec):
    # type: (dict) -> str
    """Extract ports from service spec."""
    ports = spec.get("ports", [])
    parts = []
    for p in ports:
        port_str = str(p.get("port", ""))
        node_port = p.get("nodePort")
        protocol = p.get("protocol", "TCP")
        if node_port:
            parts.append("{}:{}/{}".format(port_str, node_port, protocol))
        else:
            parts.append("{}/{}".format(port_str, protocol))
    return ",".join(parts) if parts else "<none>"


def _parse_pod(item):
    # type: (dict) -> List[str]
    metadata = item.get("metadata", {})
    status = item.get("status", {})
    spec = item.get("spec", {})
    container_statuses = status.get("containerStatuses", [])
    return [
        metadata.get("name", ""),
        _calc_ready_pods(container_statuses),
        status.get("phase", "Unknown"),
        _calc_restarts(container_statuses),
        _calc_age(metadata.get("creationTimestamp", "")),
        status.get("podIP", "<none>"),
        spec.get("nodeName", "<none>"),
    ]


def _parse_service(item):
    # type: (dict) -> List[str]
    metadata = item.get("metadata", {})
    spec = item.get("spec", {})
    return [
        metadata.get("name", ""),
        spec.get("type", ""),
        spec.get("clusterIP", "<none>"),
        _extract_ports(spec),
        _calc_age(metadata.get("creationTimestamp", "")),
    ]


def _parse_deployment(item):
    # type: (dict) -> List[str]
    metadata = item.get("metadata", {})
    status = item.get("status", {})
    return [
        metadata.get("name", ""),
        _calc_ready_deploy(status),
        str(status.get("updatedReplicas", 0)),
        str(status.get("availableReplicas", 0)),
        _calc_age(metadata.get("creationTimestamp", "")),
    ]


def _parse_statefulset(item):
    # type: (dict) -> List[str]
    metadata = item.get("metadata", {})
    status = item.get("status", {})
    return [
        metadata.get("name", ""),
        _calc_ready_sts(status),
        _calc_age(metadata.get("creationTimestamp", "")),
    ]


def _parse_namespace(item):
    # type: (dict) -> List[str]
    metadata = item.get("metadata", {})
    status = item.get("status", {})
    return [
        metadata.get("name", ""),
        status.get("phase", ""),
        _calc_age(metadata.get("creationTimestamp", "")),
    ]


_PARSERS = {
    "pods": _parse_pod,
    "services": _parse_service,
    "deployments": _parse_deployment,
    "statefulsets": _parse_statefulset,
    "namespaces": _parse_namespace,
}


class K8sService:
    """Async service for querying Kubernetes resources via kubectl."""

    def __init__(self, kubeconfig="", context="", namespace="default"):
        # type: (str, str, str) -> None
        self.kubeconfig = kubeconfig
        self.context = context
        self.namespace = namespace

    def _base_args(self):
        # type: () -> List[str]
        args = ["kubectl"]
        if self.kubeconfig:
            args.extend(["--kubeconfig", os.path.expanduser(self.kubeconfig)])
        if self.context:
            args.extend(["--context", self.context])
        return args

    async def get_resources(self, resource_type):
        # type: (str) -> Tuple[List[str], List[List[str]]]
        """Fetch resources and return (headers, rows)."""
        canonical = RESOURCE_ALIASES.get(resource_type, resource_type)
        headers = RESOURCE_COLUMNS.get(canonical, ["NAME"])
        parser = _PARSERS.get(canonical)

        cmd = self._base_args()
        cmd.extend(["get", canonical])
        if canonical != "namespaces":
            cmd.extend(["-n", self.namespace])
        cmd.extend(["-o", "json"])

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=15.0)

            if proc.returncode != 0:
                err = stderr.decode("utf-8", errors="replace").strip()
                logger.error("kubectl failed: %s", err)
                return headers, []

            data = json.loads(stdout.decode("utf-8", errors="replace"))
            items = data.get("items", [])

            rows = []
            for item in items:
                if parser:
                    rows.append(parser(item))
                else:
                    name = item.get("metadata", {}).get("name", "")
                    rows.append([name])
            return headers, rows

        except asyncio.TimeoutError:
            logger.error("kubectl timed out")
            return headers, []
        except Exception as exc:
            logger.error("kubectl error: %s", exc)
            return headers, []

    async def get_namespaces(self):
        # type: () -> List[str]
        """Return a list of namespace names."""
        _, rows = await self.get_resources("namespaces")
        return [row[0] for row in rows if row]
