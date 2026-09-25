"""
humana/app/core/config.py
Centralised settings loaded from .env / environment variables.
"""
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Server ────────────────────────────────────
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    secret_key: str = "change-me-in-production"
    allowed_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
        "http://127.0.0.1:5500",   # VS Code Live Server
        "*",                        # open for dev; tighten in prod
    ]

    # ── Database ──────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///./humana.db"

    # ── LLM ───────────────────────────────────────
    llm_provider: str = "openai"          # openai | anthropic
    llm_model: str = "gpt-4o"
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    # ── Embeddings ────────────────────────────────
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_provider: str = "local"     # local | openai

    # ── Vector store ──────────────────────────────
    chroma_path: str = "./chroma_data"
    chroma_host: str = ""

    # ── ElevenLabs ────────────────────────────────
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = "21m00Tcm4TlvDq8ikWAM"

    # ── Redis ─────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── RAG tuning ────────────────────────────────
    chunk_size: int = 512
    chunk_overlap: int = 64
    top_k_retrieval: int = 5
    similarity_threshold: float = 0.35

    @property
    def is_dev(self) -> bool:
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()
