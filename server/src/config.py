from pydantic_settings import BaseSettings
from typing import List
import json


class Settings(BaseSettings):
    # Security
    secret_key: str = "dev-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24 hours

    # Database
    database_url: str = "postgresql+asyncpg://ifcgit:ifcgit@db:5432/ifcgit"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # Storage paths
    data_dir: str = "/data"

    @property
    def repos_dir(self) -> str:
        return f"{self.data_dir}/repos"

    @property
    def cache_dir(self) -> str:
        return f"{self.data_dir}/cache"

    @property
    def working_dir(self) -> str:
        return f"{self.data_dir}/working"

    # Fragment generation
    node_converter_path: str = "/app/convert_ifc.js"
    max_full_fragment_size_mb: int = 500

    # Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_level: str = "info"
    cors_origins: str = '["http://localhost:3000"]'

    @property
    def cors_origins_list(self) -> List[str]:
        return json.loads(self.cors_origins)

    # Nextcloud (optional)
    nextcloud_enabled: bool = False
    nextcloud_url: str = "http://nextcloud:8080"

    # Neo4j (optional)
    neo4j_enabled: bool = False
    neo4j_uri: str = "bolt://neo4j:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "neo4j-ifcgit"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
