"""In-memory storage for Cloud Load Balancing resources, keyed by project."""

from typing import Dict, List, Optional
import itertools
import threading

from .models import HealthCheck, BackendService, Backend, UrlMap, TargetHttpProxy, ForwardingRule

_ip_counter = itertools.count(100)


class LoadBalancerStorage:
    def __init__(self):
        self._lock = threading.Lock()
        self.health_checks: Dict[str, Dict[str, HealthCheck]] = {}
        self.backend_services: Dict[str, Dict[str, BackendService]] = {}
        self.url_maps: Dict[str, Dict[str, UrlMap]] = {}
        self.target_proxies: Dict[str, Dict[str, TargetHttpProxy]] = {}
        self.forwarding_rules: Dict[str, Dict[str, ForwardingRule]] = {}
        self._rr_counters: Dict[str, int] = {}  # backend_service key -> next index

    # Health checks
    def create_health_check(self, project_id: str, name: str, port: int = 80) -> HealthCheck:
        with self._lock:
            bucket = self.health_checks.setdefault(project_id, {})
            if name in bucket:
                raise ValueError(f"HealthCheck '{name}' already exists")
            hc = HealthCheck(project_id=project_id, name=name, port=port)
            bucket[name] = hc
            return hc

    def list_health_checks(self, project_id: str) -> List[HealthCheck]:
        return list(self.health_checks.get(project_id, {}).values())

    def get_health_check(self, project_id: str, name: str) -> Optional[HealthCheck]:
        return self.health_checks.get(project_id, {}).get(name)

    # Backend services
    def create_backend_service(
        self, project_id: str, name: str, protocol: str = "HTTP",
        health_checks: Optional[List[str]] = None,
    ) -> BackendService:
        with self._lock:
            bucket = self.backend_services.setdefault(project_id, {})
            if name in bucket:
                raise ValueError(f"BackendService '{name}' already exists")
            svc = BackendService(project_id=project_id, name=name, protocol=protocol, health_checks=health_checks or [])
            bucket[name] = svc
            return svc

    def get_backend_service(self, project_id: str, name: str) -> Optional[BackendService]:
        return self.backend_services.get(project_id, {}).get(name)

    def list_backend_services(self, project_id: str) -> List[BackendService]:
        return list(self.backend_services.get(project_id, {}).values())

    def add_backend(self, project_id: str, name: str, instance_name: str, zone: str, port: int = 80) -> BackendService:
        svc = self.get_backend_service(project_id, name)
        if not svc:
            raise ValueError(f"BackendService '{name}' not found")
        with self._lock:
            svc.backends.append(Backend(instance_name=instance_name, zone=zone, port=port))
            return svc

    def next_backend(self, project_id: str, name: str) -> Optional[Backend]:
        svc = self.get_backend_service(project_id, name)
        if not svc or not svc.backends:
            return None
        key = f"{project_id}/{name}"
        with self._lock:
            idx = self._rr_counters.get(key, 0)
            backend = svc.backends[idx % len(svc.backends)]
            self._rr_counters[key] = idx + 1
            return backend

    # URL maps
    def create_url_map(self, project_id: str, name: str, default_service: str) -> UrlMap:
        with self._lock:
            bucket = self.url_maps.setdefault(project_id, {})
            if name in bucket:
                raise ValueError(f"UrlMap '{name}' already exists")
            um = UrlMap(project_id=project_id, name=name, default_service=default_service)
            bucket[name] = um
            return um

    def get_url_map(self, project_id: str, name: str) -> Optional[UrlMap]:
        return self.url_maps.get(project_id, {}).get(name)

    def list_url_maps(self, project_id: str) -> List[UrlMap]:
        return list(self.url_maps.get(project_id, {}).values())

    # Target proxies
    def create_target_proxy(self, project_id: str, name: str, url_map: str) -> TargetHttpProxy:
        with self._lock:
            bucket = self.target_proxies.setdefault(project_id, {})
            if name in bucket:
                raise ValueError(f"TargetHttpProxy '{name}' already exists")
            proxy = TargetHttpProxy(project_id=project_id, name=name, url_map=url_map)
            bucket[name] = proxy
            return proxy

    def get_target_proxy(self, project_id: str, name: str) -> Optional[TargetHttpProxy]:
        return self.target_proxies.get(project_id, {}).get(name)

    def list_target_proxies(self, project_id: str) -> List[TargetHttpProxy]:
        return list(self.target_proxies.get(project_id, {}).values())

    # Forwarding rules
    def create_forwarding_rule(
        self, project_id: str, name: str, target: str, port_range: str = "80"
    ) -> ForwardingRule:
        with self._lock:
            bucket = self.forwarding_rules.setdefault(project_id, {})
            if name in bucket:
                raise ValueError(f"ForwardingRule '{name}' already exists")
            ip_address = f"10.200.0.{next(_ip_counter) % 250 + 1}"
            rule = ForwardingRule(project_id=project_id, name=name, target=target, ip_address=ip_address, port_range=port_range)
            bucket[name] = rule
            return rule

    def get_forwarding_rule(self, project_id: str, name: str) -> Optional[ForwardingRule]:
        return self.forwarding_rules.get(project_id, {}).get(name)

    def list_forwarding_rules(self, project_id: str) -> List[ForwardingRule]:
        return list(self.forwarding_rules.get(project_id, {}).values())

    def resolve_backend_service_for_rule(self, project_id: str, rule_name: str) -> Optional[str]:
        rule = self.get_forwarding_rule(project_id, rule_name)
        if not rule:
            return None
        # target -> proxy -> urlMap -> backendService
        proxy_name = rule.target.rsplit("/", 1)[-1]
        proxy = self.get_target_proxy(project_id, proxy_name)
        if not proxy:
            return None
        url_map_name = proxy.url_map.rsplit("/", 1)[-1]
        url_map = self.get_url_map(project_id, url_map_name)
        if not url_map:
            return None
        return url_map.default_service.rsplit("/", 1)[-1]

    def get_stats(self) -> Dict[str, int]:
        return {
            "healthChecks": sum(len(v) for v in self.health_checks.values()),
            "backendServices": sum(len(v) for v in self.backend_services.values()),
            "forwardingRules": sum(len(v) for v in self.forwarding_rules.values()),
        }


storage = LoadBalancerStorage()
