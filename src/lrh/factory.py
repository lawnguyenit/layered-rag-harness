"""Dựng mô hình đã bọc: Cached(Throttled(Gemini)). Mô hình lạ bị từ chối vì chưa khai báo hạn mức và giá."""
from __future__ import annotations

from lrh.adapters.gemini import GeminiEmbedder, GeminiModel
from lrh.adapters.stub import StubModel
from lrh.cache import CachedModel, ResponseCache
from lrh.config import ConfigError, Settings
from lrh.limits_table import EMBEDDING_LIMITS, MODELS
from lrh.limiter import RateLimiter, SpendGuard, ThrottledModel


def build_generator(model_id: str, settings: Settings, *, use_cache: bool = True):
    if model_id == "stub":
        return StubModel()
    spec = MODELS.get(model_id)
    if spec is None:
        raise ConfigError(f"Mô hình '{model_id}' chưa có trong src/lrh/limits_table.py: khai báo hạn mức và giá trước.")
    if not settings.gemini_api_key:
        raise ConfigError("Thiếu GEMINI_API_KEY trong .env")
    inner = GeminiModel(model_id, api_key=settings.gemini_api_key, thinking_level=spec.thinking_level)
    spend = SpendGuard(settings.spend_cap_usd, {model_id: (spec.price_in_per_m, spec.price_out_per_m)})
    model = ThrottledModel(inner, RateLimiter(spec.limits), spend=spend)
    if use_cache:
        settings.cache_path.parent.mkdir(parents=True, exist_ok=True)
        model = CachedModel(model, ResponseCache(str(settings.cache_path)))
    return model


def build_embedder(settings: Settings) -> GeminiEmbedder:
    if settings.embedding_model_id not in EMBEDDING_LIMITS:
        raise ConfigError(f"Mô hình embedding '{settings.embedding_model_id}' chưa có hạn mức trong limits_table.py")
    if not settings.gemini_api_key:
        raise ConfigError("Thiếu GEMINI_API_KEY trong .env")
    return GeminiEmbedder(settings.embedding_model_id, dim=settings.embedding_dim, api_key=settings.gemini_api_key)
