"""In-memory storage for API Gateway APIs, configs, and gateways."""

from typing import Dict, List, Optional
import threading

from .models import ApiConfig, Gateway, Route


class ApiGatewayStorage:
    def __init__(self):
        self._lock = threading.Lock()
        self.configs: Dict[str, Dict[str, ApiConfig]] = {}  # project_id -> config_id -> ApiConfig
        self.gateways: Dict[str, Dict[str, Gateway]] = {}  # project_id -> gateway_id -> Gateway

    def create_config(self, project_id: str, api_id: str, config_id: str, routes: List[Route]) -> ApiConfig:
        with self._lock:
            bucket = self.configs.setdefault(project_id, {})
            if config_id in bucket:
                raise ValueError(f"ApiConfig '{config_id}' already exists")
            config = ApiConfig(project_id=project_id, api_id=api_id, config_id=config_id, routes=routes)
            bucket[config_id] = config
            return config

    def get_config(self, project_id: str, config_id: str) -> Optional[ApiConfig]:
        return self.configs.get(project_id, {}).get(config_id)

    def list_configs(self, project_id: str) -> List[ApiConfig]:
        return list(self.configs.get(project_id, {}).values())

    def create_gateway(self, project_id: str, location: str, gateway_id: str, config_id: str) -> Gateway:
        if not self.get_config(project_id, config_id):
            raise ValueError(f"ApiConfig '{config_id}' not found")
        with self._lock:
            bucket = self.gateways.setdefault(project_id, {})
            if gateway_id in bucket:
                raise ValueError(f"Gateway '{gateway_id}' already exists")
            gw = Gateway(project_id=project_id, location=location, gateway_id=gateway_id, api_config=config_id)
            bucket[gateway_id] = gw
            return gw

    def get_gateway(self, project_id: str, gateway_id: str) -> Optional[Gateway]:
        return self.gateways.get(project_id, {}).get(gateway_id)

    def list_gateways(self, project_id: str) -> List[Gateway]:
        return list(self.gateways.get(project_id, {}).values())

    def delete_gateway(self, project_id: str, gateway_id: str) -> bool:
        with self._lock:
            if gateway_id in self.gateways.get(project_id, {}):
                del self.gateways[project_id][gateway_id]
                return True
            return False

    def find_route(self, project_id: str, gateway_id: str, path: str, method: str):
        gw = self.get_gateway(project_id, gateway_id)
        if not gw:
            return None, None
        config = self.get_config(project_id, gw.api_config)
        if not config:
            return None, None
        for route in config.routes:
            if route.matches(path, method):
                return gw, route
        return gw, None

    def get_stats(self) -> Dict[str, int]:
        return {
            "configs": sum(len(c) for c in self.configs.values()),
            "gateways": sum(len(g) for g in self.gateways.values()),
        }


storage = ApiGatewayStorage()
