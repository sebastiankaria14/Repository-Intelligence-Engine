"""
Repository Intelligence Engine — Core Configuration
Centralized settings loaded from environment variables.
"""

from __future__ import annotations

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

    # ── PostgreSQL ──
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "rie"
    postgres_user: str = "rie"
    postgres_password: str = "rie_secret_change_me"
    database_url: str | None = None

    @property
    def effective_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # ── Redis ──
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/1"

    # ── Neo4j ──
    neo4j_host: str = "neo4j"
    neo4j_bolt_port: int = 7687
    neo4j_http_port: int = 7474
    neo4j_user: str = "neo4j"
    neo4j_password: str = "neo4j_secret_change_me"

    @property
    def neo4j_uri(self) -> str:
        return f"bolt://{self.neo4j_host}:{self.neo4j_bolt_port}"

    # ── Qdrant ──
    qdrant_host: str = "qdrant"
    qdrant_port: int = 6333
    qdrant_grpc_port: int = 6334

    # ── Meilisearch ──
    meilisearch_host: str = "meilisearch"
    meilisearch_port: int = 7700
    meilisearch_master_key: str = "rie_meili_master_key"

    @property
    def meilisearch_url(self) -> str:
        return f"http://{self.meilisearch_host}:{self.meilisearch_port}"

    # ── Ollama ──
    ollama_host: str = "ollama"
    ollama_port: int = 11434
    ollama_base_url: str = "http://ollama:11434"

    # ── Backend ──
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    backend_cors_origins: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    clone_base_dir: str = "/app/repos"


settings = Settings()
