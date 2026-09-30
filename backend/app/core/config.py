"""
Repository Intelligence Engine — Core Configuration
Centralized settings loaded from environment variables.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings populated from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──
    app_name: str = "Repository Intelligence Engine"
    debug: bool = False
    testing: bool = False
    secret_key: str = "rie_secret_key_change_me"
    api_key: str = "rie_dev_api_key"

    # ── Local Storage & Persistence ──
    storage_dir: str = str(Path.home() / ".rie")
    database_url: str | None = None

    @property
    def effective_storage_path(self) -> Path:
        p = Path(self.storage_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def effective_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        db_path = self.effective_storage_path / "rie.db"
        # Standard forward-slash path format for SQLite URL
        normalized_path = db_path.as_posix()
        return f"sqlite+aiosqlite:///{normalized_path}"

    # ── Legacy External Services (Optional / Fallbacks) ──
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "rie"
    postgres_user: str = "rie"
    postgres_password: str = "rie_secret_change_me"

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    neo4j_host: str = "localhost"
    neo4j_bolt_port: int = 7687
    neo4j_http_port: int = 7474
    neo4j_user: str = "neo4j"
    neo4j_password: str = "neo4j_secret_change_me"

    @property
    def neo4j_uri(self) -> str:
        return f"bolt://{self.neo4j_host}:{self.neo4j_bolt_port}"

    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_grpc_port: int = 6334

    meilisearch_host: str = "localhost"
    meilisearch_port: int = 7700
    meilisearch_master_key: str = "rie_meili_master_key"

    @property
    def meilisearch_url(self) -> str:
        return f"http://{self.meilisearch_host}:{self.meilisearch_port}"

    ollama_host: str = "localhost"
    ollama_port: int = 11434
    ollama_base_url: str = "http://localhost:11434"

    # ── Backend ──
    backend_host: str = "127.0.0.1"
    backend_port: int = 8000
    backend_cors_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]
    clone_base_dir: str = str(Path.home() / ".rie" / "repos")

    @property
    def effective_clone_dir(self) -> Path:
        if self.clone_base_dir and self.clone_base_dir != "/app/repos":
            p = Path(self.clone_base_dir)
        else:
            p = self.effective_storage_path / "repos"
        p.mkdir(parents=True, exist_ok=True)
        return p


settings = Settings()
