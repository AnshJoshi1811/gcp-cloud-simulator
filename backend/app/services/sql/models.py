"""Cloud SQL data models: instances, databases, users."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any
import secrets
import string


class DatabaseVersion:
    POSTGRES_15 = "POSTGRES_15"
    MYSQL_8_0 = "MYSQL_8_0"


class SqlInstanceState:
    PENDING_CREATE = "PENDING_CREATE"
    RUNNABLE = "RUNNABLE"
    STOPPED = "STOPPED"
    FAILED = "FAILED"
    DELETED = "DELETED"


# Maps a GCP database_version to the Docker image + port + default admin
# credentials used to actually run it locally.
ENGINE_CONFIG = {
    DatabaseVersion.POSTGRES_15: {
        "image": "postgres:15-alpine",
        "port": 5432,
        "user_env": "POSTGRES_USER",
        "password_env": "POSTGRES_PASSWORD",
        "db_env": "POSTGRES_DB",
        "default_user": "postgres",
    },
    DatabaseVersion.MYSQL_8_0: {
        "image": "mysql:8.0",
        "port": 3306,
        "user_env": "MYSQL_USER",
        "password_env": "MYSQL_ROOT_PASSWORD",
        "db_env": "MYSQL_DATABASE",
        "default_user": "root",
    },
}


def generate_password(length: int = 20) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


@dataclass
class SqlDatabase:
    instance_id: str
    project_id: str
    name: str
    charset: str = "utf8"
    create_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "project": self.project_id,
            "instance": self.instance_id,
            "charset": self.charset,
            "kind": "sql#database",
        }


@dataclass
class SqlUser:
    instance_id: str
    project_id: str
    name: str
    password: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "project": self.project_id,
            "instance": self.instance_id,
            "kind": "sql#user",
        }


@dataclass
class SqlInstance:
    instance_id: str
    project_id: str
    region: str
    database_version: str = DatabaseVersion.POSTGRES_15
    tier: str = "db-f1-micro"
    root_password: str = field(default_factory=generate_password)
    state: str = SqlInstanceState.PENDING_CREATE
    create_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    container_id: Optional[str] = None
    internal_ip: Optional[str] = None
    host_port: Optional[int] = None
    databases: Dict[str, SqlDatabase] = field(default_factory=dict)
    users: Dict[str, SqlUser] = field(default_factory=dict)
    labels: Dict[str, str] = field(default_factory=dict)

    @property
    def self_link(self) -> str:
        return f"projects/{self.project_id}/instances/{self.instance_id}"

    def to_dict(self) -> Dict[str, Any]:
        config = ENGINE_CONFIG[self.database_version]
        return {
            "kind": "sql#instance",
            "name": self.instance_id,
            "project": self.project_id,
            "region": self.region,
            "databaseVersion": self.database_version,
            "settings": {
                "tier": self.tier,
            },
            "state": self.state,
            "createTime": self.create_time.isoformat() + "Z",
            "connectionName": f"{self.project_id}:{self.region}:{self.instance_id}",
            "ipAddresses": (
                [{"type": "PRIMARY", "ipAddress": self.internal_ip}] if self.internal_ip else []
            ),
            "hostPort": self.host_port,
            "enginePort": config["port"],
            "selfLink": self.self_link,
            "labels": self.labels,
        }
