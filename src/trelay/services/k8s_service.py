"""Kubernetes resource query service using kubectl."""
import asyncio
import json
import logging
import os
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

RESOURCE_ALIASES = {
    # Existing
    "po": "pods", "pod": "pods", "pods": "pods",
    "svc": "services", "service": "services", "services": "services",
    "deploy": "deployments", "deployment": "deployments", "deployments": "deployments",
    "ds": "daemonsets", "daemonset": "daemonsets", "daemonsets": "daemonsets",
    "sts": "statefulsets", "statefulset": "statefulsets", "statefulsets": "statefulsets",
    "ns": "namespaces", "namespace": "namespaces", "namespaces": "namespaces",
    # New - Workloads
    "job": "jobs", "jobs": "jobs",
    "cj": "cronjobs", "cronjob": "cronjobs", "cronjobs": "cronjobs",
    "rs": "replicasets", "replicaset": "replicasets", "replicasets": "replicasets",
    # New - Service Discovery
    "ing": "ingresses", "ingress": "ingresses", "ingresses": "ingresses",
    "ep": "endpoints", "endpoint": "endpoints", "endpoints": "endpoints",
    "netpol": "networkpolicies", "networkpolicy": "networkpolicies", "networkpolicies": "networkpolicies",
    # New - Storage Config
    "cm": "configmaps", "configmap": "configmaps", "configmaps": "configmaps",
    "secret": "secrets", "secrets": "secrets",
    "pv": "persistentvolumes", "persistentvolume": "persistentvolumes", "persistentvolumes": "persistentvolumes",
    "pvc": "persistentvolumeclaims", "persistentvolumeclaim": "persistentvolumeclaims", "persistentvolumeclaims": "persistentvolumeclaims",
    "sc": "storageclasses", "storageclass": "storageclasses", "storageclasses": "storageclasses",
    # New - Cluster Management
    "node": "nodes", "nodes": "nodes",
    "ev": "events", "event": "events", "events": "events",
    "rq": "resourcequotas", "resourcequota": "resourcequotas", "resourcequotas": "resourcequotas",
    "hpa": "horizontalpodautoscalers", "horizontalpodautoscaler": "horizontalpodautoscalers", "horizontalpodautoscalers": "horizontalpodautoscalers",
    "limitrange": "limitranges", "limitranges": "limitranges",
    "pdb": "poddisruptionbudgets", "poddisruptionbudget": "poddisruptionbudgets", "poddisruptionbudgets": "poddisruptionbudgets",
}

# Column definitions per resource type
RESOURCE_COLUMNS = {
    # Existing
    "pods": ["NAME", "READY", "STATUS", "RESTARTS", "AGE", "IP", "NODE"],
    "services": ["NAME", "TYPE", "CLUSTER-IP", "PORTS", "AGE"],
    "deployments": ["NAME", "READY", "UP-TO-DATE", "AVAILABLE", "AGE"],
    "daemonsets": ["NAME", "DESIRED", "CURRENT", "READY", "UP-TO-DATE", "AGE"],
    "statefulsets": ["NAME", "READY", "AGE"],
    "namespaces": ["NAME", "STATUS", "AGE"],
    # New - Workloads
    "jobs": ["NAME", "COMPLETIONS", "DURATION", "AGE"],
    "cronjobs": ["NAME", "SCHEDULE", "SUSPEND", "ACTIVE", "LASTSCHEDULE", "AGE"],
    "replicasets": ["NAME", "DESIRED", "CURRENT", "READY", "AGE"],
    # New - Service Discovery
    "ingresses": ["NAME", "CLASS", "HOSTS", "ADDRESS", "PORTS", "AGE"],
    "endpoints": ["NAME", "ENDPOINTS", "AGE"],
    "networkpolicies": ["NAME", "POD-SELECTOR", "AGE"],
    # New - Storage Config
    "configmaps": ["NAME", "DATA", "AGE"],
    "secrets": ["NAME", "TYPE", "DATA", "AGE"],
    "persistentvolumes": ["NAME", "CAPACITY", "ACCESSMODES", "RECLAIMPOLICY", "STATUS", "CLAIM", "AGE"],
    "persistentvolumeclaims": ["NAME", "STATUS", "VOLUME", "CAPACITY", "ACCESSMODES", "AGE"],
    "storageclasses": ["NAME", "PROVISIONER", "RECLAIMPOLICY", "VOLUMEBINDINGMODE", "AGE"],
    # New - Cluster Management
    "nodes": ["NAME", "STATUS", "ROLES", "AGE", "VERSION", "INTERNAL-IP", "EXTERNAL-IP", "OS-IMAGE", "KERNEL-VERSION", "CONTAINER-RUNTIME"],
    "events": ["LASTSEEN", "TYPE", "REASON", "OBJECT", "MESSAGE"],
    "resourcequotas": ["NAME", "AGE", "REQUEST", "LIMIT"],
    "horizontalpodautoscalers": ["NAME", "REFERENCE", "TARGETS", "MINPODS", "MAXPODS", "REPLICAS", "AGE"],
    "limitranges": ["NAME", "AGE"],
    "poddisruptionbudgets": ["NAME", "MINAVAILABLE", "ALLOWEDDISRUPTIONS", "AGE"],
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


def _calc_job_duration(start_time, end_time=None):
    # type: (str, str) -> str
    """Calculate job duration from start and end time."""
    from datetime import datetime, timezone

    try:
        if start_time:
            start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            end = datetime.now(timezone.utc)
            if end_time:
                end = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
            diff = end - start
            total_seconds = int(diff.total_seconds())
            if total_seconds < 60:
                return "{}s".format(total_seconds)
            elif total_seconds < 3600:
                return "{}m".format(total_seconds // 60)
            else:
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                return "{}h{}m".format(hours, minutes)
        return "?"
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


def _parse_daemonset(item):
    # type: (dict) -> List[str]
    metadata = item.get("metadata", {})
    status = item.get("status", {})
    return [
        metadata.get("name", ""),
        str(status.get("desiredNumberScheduled", 0)),
        str(status.get("currentNumberScheduled", 0)),
        str(status.get("numberReady", 0)),
        str(status.get("updatedNumberScheduled", 0)),
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


def _parse_job(item):
    # type: (dict) -> List[str]
    metadata = item.get("metadata", {})
    status = item.get("status", {})
    spec = item.get("spec", {})
    succeeded = status.get("succeeded", 0) or 0
    parallelism = spec.get("parallelism", 1) or 1
    completions = spec.get("completions", 1) or 1
    completion_str = f"{succeeded}/{completions}"
    duration_str = _calc_job_duration(status.get("startTime"), status.get("completionTime"))
    return [
        metadata.get("name", ""),
        completion_str,
        duration_str,
        _calc_age(metadata.get("creationTimestamp", "")),
    ]


def _parse_cronjob(item):
    # type: (dict) -> List[str]
    metadata = item.get("metadata", {})
    spec = item.get("spec", {})
    status = item.get("status", {})
    suspend = spec.get("suspend", False)
    active = len(status.get("active", []))
    last_schedule = status.get("lastScheduleTime", "<none>")
    last_age = _calc_age(last_schedule) if last_schedule != "<none>" else "<none>"
    return [
        metadata.get("name", ""),
        spec.get("schedule", ""),
        "True" if suspend else "False",
        str(active),
        last_age,
        _calc_age(metadata.get("creationTimestamp", "")),
    ]


def _parse_replicaset(item):
    # type: (dict) -> List[str]
    metadata = item.get("metadata", {})
    spec = item.get("spec", {})
    status = item.get("status", {})
    desired = spec.get("replicas", 0) or 0
    current = status.get("replicas", 0) or 0
    ready = status.get("readyReplicas", 0) or 0
    return [
        metadata.get("name", ""),
        str(desired),
        str(current),
        str(ready),
        _calc_age(metadata.get("creationTimestamp", "")),
    ]


def _parse_ingress(item):
    # type: (dict) -> List[str]
    metadata = item.get("metadata", {})
    spec = item.get("spec", {})
    status = item.get("status", {})

    # Class
    ingress_class = spec.get("ingressClassName", "")

    # Hosts
    hosts = []
    for rule in spec.get("rules", []):
        host = rule.get("host", "")
        if host:
            hosts.append(host)
    hosts_str = ", ".join(hosts) if hosts else "*"

    # Address
    load_balancer = status.get("loadBalancer", {})
    ingress_list = load_balancer.get("ingress", [])
    addresses = []
    for ing in ingress_list:
        if ing.get("ip"):
            addresses.append(ing["ip"])
        elif ing.get("hostname"):
            addresses.append(ing["hostname"])
    address_str = ", ".join(addresses) if addresses else ""

    # Ports
    ports = set()
    for tls in spec.get("tls", []):
        ports.add("443")
    for rule in spec.get("rules", []):
        for http in rule.get("http", {}).get("paths", []):
            port = http.get("backend", {}).get("service", {}).get("port", {}).get("number")
            if port:
                ports.add(str(port))
    ports_str = ", ".join(sorted(ports)) if ports else ""

    return [
        metadata.get("name", ""),
        ingress_class,
        hosts_str,
        address_str,
        ports_str,
        _calc_age(metadata.get("creationTimestamp", "")),
    ]


def _parse_endpoint(item):
    # type: (dict) -> List[str]
    metadata = item.get("metadata", {})
    subsets = item.get("subsets", [])
    endpoint_count = 0
    for subset in subsets:
        addresses = subset.get("addresses", [])
        not_ready = subset.get("notReadyAddresses", [])
        endpoint_count += len(addresses) + len(not_ready)
    return [
        metadata.get("name", ""),
        str(endpoint_count) if endpoint_count > 0 else "<none>",
        _calc_age(metadata.get("creationTimestamp", "")),
    ]


def _parse_networkpolicy(item):
    # type: (dict) -> List[str]
    metadata = item.get("metadata", {})
    spec = item.get("spec", {})
    pod_selector = spec.get("podSelector", {})
    selector_str = ",".join(f"{k}={v}" for k, v in pod_selector.get("matchLabels", {}).items())
    return [
        metadata.get("name", ""),
        selector_str if selector_str else "<none>",
        _calc_age(metadata.get("creationTimestamp", "")),
    ]


def _parse_configmap(item):
    # type: (dict) -> List[str]
    metadata = item.get("metadata", {})
    data = item.get("data", {}) or {}
    binary_data = item.get("binaryData", {}) or {}
    data_count = len(data) + len(binary_data)
    return [
        metadata.get("name", ""),
        str(data_count),
        _calc_age(metadata.get("creationTimestamp", "")),
    ]


def _parse_secret(item):
    # type: (dict) -> List[str]
    metadata = item.get("metadata", {})
    spec = item.get("type", "Opaque")
    data = item.get("data", {}) or {}
    data_count = len(data)
    return [
        metadata.get("name", ""),
        spec,
        str(data_count),
        _calc_age(metadata.get("creationTimestamp", "")),
    ]


def _parse_persistentvolume(item):
    # type: (dict) -> List[str]
    metadata = item.get("metadata", {})
    spec = item.get("spec", {})
    status = item.get("status", {})
    capacity = spec.get("capacity", {}) or {}
    access_modes = spec.get("accessModes", [])
    reclaim_policy = spec.get("persistentVolumeReclaimPolicy", "")
    phase = status.get("phase", "")
    claim_ref = spec.get("claimRef", {}) or {}
    claim_str = claim_ref.get("name", "") if claim_ref else ""
    return [
        metadata.get("name", ""),
        capacity.get("storage", ""),
        ",".join(access_modes) if access_modes else "",
        reclaim_policy,
        phase,
        claim_str,
        _calc_age(metadata.get("creationTimestamp", "")),
    ]


def _parse_persistentvolumeclaim(item):
    # type: (dict) -> List[str]
    metadata = item.get("metadata", {})
    spec = item.get("spec", {})
    status = item.get("status", {})
    volume_name = spec.get("volumeName", "")
    capacity = status.get("capacity", {}) or {}
    access_modes = spec.get("accessModes", [])
    phase = status.get("phase", "")
    return [
        metadata.get("name", ""),
        phase,
        volume_name if volume_name else "<none>",
        capacity.get("storage", ""),
        ",".join(access_modes) if access_modes else "",
        _calc_age(metadata.get("creationTimestamp", "")),
    ]


def _parse_storageclass(item):
    # type: (dict) -> List[str]
    metadata = item.get("metadata", {})
    annotations = metadata.get("annotations", {}) or {}
    provisioner = item.get("provisioner", "")
    reclaim_policy = item.get("reclaimPolicy", "")
    volume_binding = annotations.get("storageclass.kubernetes.io/is-default-class", "")
    binding_mode = item.get("volumeBindingMode", "")
    return [
        metadata.get("name", ""),
        provisioner,
        reclaim_policy,
        binding_mode,
        _calc_age(metadata.get("creationTimestamp", "")),
    ]


def _parse_node(item):
    # type: (dict) -> List[str]
    metadata = item.get("metadata", {})
    status = item.get("status", {})
    conditions = status.get("conditions", []) or []
    # Find Ready condition
    ready_status = "Unknown"
    for cond in conditions:
        if cond.get("type") == "Ready":
            ready_status = cond.get("status", "")
            break
    # Extract roles from labels
    labels = metadata.get("labels", {}) or {}
    roles = []
    if labels.get("node-role.kubernetes.io/master") or labels.get("node-role.kubernetes.io/control-plane"):
        roles.append("master")
    if labels.get("node-role.kubernetes.io/worker"):
        roles.append("worker")
    role_str = ",".join(roles) if roles else "<none>"
    # Version and node info
    node_info = status.get("nodeInfo", {}) or {}
    version = node_info.get("kubeletVersion", "")
    # Extract IP addresses
    addresses = status.get("addresses", []) or []
    internal_ip = ""
    external_ip = ""
    for addr in addresses:
        addr_type = addr.get("type", "")
        if addr_type == "InternalIP":
            internal_ip = addr.get("address", "")
        elif addr_type == "ExternalIP":
            external_ip = addr.get("address", "")
    # Additional node info fields
    os_image = node_info.get("osImage", "")
    kernel_version = node_info.get("kernelVersion", "")
    container_runtime = node_info.get("containerRuntimeVersion", "")
    return [
        metadata.get("name", ""),
        ready_status,
        role_str,
        _calc_age(metadata.get("creationTimestamp", "")),
        version,
        internal_ip or "<none>",
        external_ip or "<none>",
        os_image,
        kernel_version,
        container_runtime,
    ]


def _parse_event(item):
    # type: (dict) -> List[str]
    metadata = item.get("metadata", {})
    event_time = metadata.get("eventTime", "") or item.get("lastTimestamp", "")
    if event_time:
        try:
            from datetime import datetime, timezone
            created = datetime.fromisoformat(event_time.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            diff = now - created
            total_seconds = int(diff.total_seconds())
            if total_seconds < 60:
                last_seen = "{}s".format(total_seconds)
            elif total_seconds < 3600:
                last_seen = "{}m".format(total_seconds // 60)
            elif total_seconds < 86400:
                last_seen = "{}h".format(total_seconds // 3600)
            else:
                last_seen = "{}d".format(total_seconds // 86400)
        except Exception:
            last_seen = "?"
    else:
        last_seen = "?"
    event_type = item.get("type", "")
    reason = item.get("reason", "")
    involved = item.get("involvedObject", {}) or {}
    object_str = involved.get("kind", "") + "/" + involved.get("name", "") if involved else ""
    message = item.get("message", "")
    return [
        last_seen,
        event_type,
        reason,
        object_str,
        message,
    ]


def _parse_resourcequota(item):
    # type: (dict) -> List[str]
    metadata = item.get("metadata", {})
    spec = item.get("spec", {}) or {}
    hard = spec.get("hard", {}) or {}
    request_str = ",".join(f"{k}={v}" for k, v in sorted(hard.items())[:2])
    limit_str = ",".join(f"{k}={v}" for k, v in sorted(hard.items())[2:4])
    return [
        metadata.get("name", ""),
        _calc_age(metadata.get("creationTimestamp", "")),
        request_str if request_str else "<none>",
        limit_str if limit_str else "<none>",
    ]


def _parse_horizontalpodautoscaler(item):
    # type: (dict) -> List[str]
    metadata = item.get("metadata", {})
    spec = item.get("spec", {})
    status = item.get("status", {}) or {}
    scale_target_ref = spec.get("scaleTargetRef", {}) or {}
    reference = scale_target_ref.get("kind", "") + "/" + scale_target_ref.get("name", "")
    # Targets
    min_pods = spec.get("minReplicas", 0)
    max_pods = spec.get("maxReplicas", 0)
    replicas = status.get("currentReplicas", 0)
    target_str = "<unknown>"
    current_metrics = status.get("currentMetrics", []) or []
    if current_metrics:
        metric = current_metrics[0]
        if "resource" in metric:
            target = metric.get("resource", {}).get("current", {}) or {}
            usage = target.get("averageUtilization")
            if usage is not None:
                target_str = "{}%".format(usage)
    return [
        metadata.get("name", ""),
        reference,
        target_str,
        str(min_pods),
        str(max_pods),
        str(replicas),
        _calc_age(metadata.get("creationTimestamp", "")),
    ]


def _parse_limitrange(item):
    # type: (dict) -> List[str]
    metadata = item.get("metadata", {})
    return [
        metadata.get("name", ""),
        _calc_age(metadata.get("creationTimestamp", "")),
    ]


def _parse_poddisruptionbudget(item):
    # type: (dict) -> List[str]
    metadata = item.get("metadata", {})
    spec = item.get("spec", {})
    status = item.get("status", {}) or {}
    min_available = spec.get("minAvailable") or spec.get("maxUnavailable") or "N/A"
    if isinstance(min_available, dict):
        min_available = str(min_available)
    allowed_disruptions = status.get("disruptionsAllowed", 0) or 0
    return [
        metadata.get("name", ""),
        str(min_available),
        str(allowed_disruptions),
        _calc_age(metadata.get("creationTimestamp", "")),
    ]


_PARSERS = {
    # Existing
    "pods": _parse_pod,
    "services": _parse_service,
    "deployments": _parse_deployment,
    "daemonsets": _parse_daemonset,
    "statefulsets": _parse_statefulset,
    "namespaces": _parse_namespace,
    # New - Workloads
    "jobs": _parse_job,
    "cronjobs": _parse_cronjob,
    "replicasets": _parse_replicaset,
    # New - Service Discovery
    "ingresses": _parse_ingress,
    "endpoints": _parse_endpoint,
    "networkpolicies": _parse_networkpolicy,
    # New - Storage Config
    "configmaps": _parse_configmap,
    "secrets": _parse_secret,
    "persistentvolumes": _parse_persistentvolume,
    "persistentvolumeclaims": _parse_persistentvolumeclaim,
    "storageclasses": _parse_storageclass,
    # New - Cluster Management
    "nodes": _parse_node,
    "events": _parse_event,
    "resourcequotas": _parse_resourcequota,
    "horizontalpodautoscalers": _parse_horizontalpodautoscaler,
    "limitranges": _parse_limitrange,
    "poddisruptionbudgets": _parse_poddisruptionbudget,
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
