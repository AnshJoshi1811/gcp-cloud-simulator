"""In-memory storage + Docker lifecycle for Cloud SQL instances."""

from typing import Dict, List, Optional
import logging
import threading

from .models import SqlInstance, SqlDatabase, SqlUser, SqlInstanceState, ENGINE_CONFIG
from app.core import docker_manager

logger = logging.getLogger(__name__)


class SqlStorage:
    def __init__(self):
        self._lock = threading.Lock()
        self.instances: Dict[str, Dict[str, SqlInstance]] = {}  # project_id -> instance_id -> SqlInstance

    def create_instance(
        self, project_id: str, instance_id: str, region: str,
        database_version: str, tier: str = "db-f1-micro",
        root_password: Optional[str] = None, labels: Optional[Dict[str, str]] = None,
    ) -> SqlInstance:
        with self._lock:
            project_instances = self.instances.setdefault(project_id, {})
            if instance_id in project_instances:
                raise ValueError(f"Instance '{instance_id}' already exists")

            instance = SqlInstance(
                instance_id=instance_id,
                project_id=project_id,
                region=region,
                database_version=database_version,
                tier=tier,
                labels=labels or {},
            )
            if root_password:
                instance.root_password = root_password
            project_instances[instance_id] = instance

        self._provision(instance)
        return instance

    def _provision(self, instance: SqlInstance):
        config = ENGINE_CONFIG[instance.database_version]
        env = {
            config["user_env"]: config["default_user"],
            config["password_env"]: instance.root_password,
            config["db_env"]: "postgres" if "POSTGRES" in instance.database_version else "mysql",
        }
        try:
            result = docker_manager.create_data_service_container(
                name=f"sql-{instance.project_id}-{instance.instance_id}",
                image=config["image"],
                env=env,
                ports={"db": config["port"]},
            )
            instance.container_id = result["container_id"]
            instance.internal_ip = result["internal_ip"]
            instance.host_port = result["host_port"]
            instance.state = SqlInstanceState.RUNNABLE
        except Exception as e:
            logger.error(f"Failed to provision Cloud SQL instance {instance.instance_id}: {e}")
            instance.state = SqlInstanceState.FAILED

    def get_instance(self, project_id: str, instance_id: str) -> Optional[SqlInstance]:
        return self.instances.get(project_id, {}).get(instance_id)

    def list_instances(self, project_id: str) -> List[SqlInstance]:
        return list(self.instances.get(project_id, {}).values())

    def delete_instance(self, project_id: str, instance_id: str) -> bool:
        instance = self.get_instance(project_id, instance_id)
        if not instance:
            return False
        docker_manager.delete_data_service_container(instance.container_id)
        with self._lock:
            instance.state = SqlInstanceState.DELETED
            del self.instances[project_id][instance_id]
        return True

    def stop_instance(self, project_id: str, instance_id: str) -> Optional[SqlInstance]:
        instance = self.get_instance(project_id, instance_id)
        if not instance:
            return None
        docker_manager.stop_data_service_container(instance.container_id)
        instance.state = SqlInstanceState.STOPPED
        return instance

    def start_instance(self, project_id: str, instance_id: str) -> Optional[SqlInstance]:
        instance = self.get_instance(project_id, instance_id)
        if not instance:
            return None
        docker_manager.start_data_service_container(instance.container_id)
        instance.state = SqlInstanceState.RUNNABLE
        return instance

    def create_database(self, project_id: str, instance_id: str, db_name: str) -> SqlDatabase:
        instance = self.get_instance(project_id, instance_id)
        if not instance:
            raise ValueError(f"Instance '{instance_id}' not found")
        with self._lock:
            if db_name in instance.databases:
                raise ValueError(f"Database '{db_name}' already exists")
            db = SqlDatabase(instance_id=instance_id, project_id=project_id, name=db_name)
            instance.databases[db_name] = db
            return db

    def list_databases(self, project_id: str, instance_id: str) -> List[SqlDatabase]:
        instance = self.get_instance(project_id, instance_id)
        if not instance:
            return []
        return list(instance.databases.values())

    def delete_database(self, project_id: str, instance_id: str, db_name: str) -> bool:
        instance = self.get_instance(project_id, instance_id)
        if not instance or db_name not in instance.databases:
            return False
        del instance.databases[db_name]
        return True

    def create_user(self, project_id: str, instance_id: str, user_name: str, password: Optional[str] = None) -> SqlUser:
        instance = self.get_instance(project_id, instance_id)
        if not instance:
            raise ValueError(f"Instance '{instance_id}' not found")
        from .models import generate_password
        with self._lock:
            if user_name in instance.users:
                raise ValueError(f"User '{user_name}' already exists")
            user = SqlUser(
                instance_id=instance_id, project_id=project_id, name=user_name,
                password=password or generate_password(),
            )
            instance.users[user_name] = user
            return user

    def list_users(self, project_id: str, instance_id: str) -> List[SqlUser]:
        instance = self.get_instance(project_id, instance_id)
        if not instance:
            return []
        return list(instance.users.values())

    def get_stats(self) -> Dict[str, int]:
        total = sum(len(i) for i in self.instances.values())
        return {"instances": total}


storage = SqlStorage()
