"""Đọc cấu hình từ .env ở gốc repo và biến môi trường. Khóa API không bao giờ được in (repr bị ẩn)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str = field(default="", repr=False)
    model_id: str = "gemma-4-31b-it"
    fallback_model_id: str = "gemma-4-26b-a4b-it"
    reference_model_id: str = "gemini-3.8-flash"
    embedding_model_id: str = "gemini-embedding-2"
    embedding_dim: int = 768
    spend_cap_usd: float = 0.0
    cache_path: Path = REPO_ROOT / "data" / "private" / "cache.sqlite"


def load_settings(env_file: Optional[Path] = None) -> Settings:
    load_dotenv(env_file or (REPO_ROOT / ".env"), override=False)
    g = os.environ.get
    d = Settings()
    return Settings(
        gemini_api_key=g("GEMINI_API_KEY", ""),
        model_id=g("MODEL_ID") or d.model_id,
        fallback_model_id=g("FALLBACK_MODEL_ID") or d.fallback_model_id,
        reference_model_id=g("REFERENCE_MODEL_ID") or d.reference_model_id,
        embedding_model_id=g("EMBEDDING_MODEL_ID") or d.embedding_model_id,
        embedding_dim=int(g("EMBEDDING_DIM") or d.embedding_dim),
        spend_cap_usd=float(g("SPEND_CAP_USD") or d.spend_cap_usd),
        cache_path=d.cache_path,
    )
