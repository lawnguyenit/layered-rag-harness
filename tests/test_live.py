"""Gọi API thật. Mặc định bỏ qua. Chạy: LRH_LIVE=1 uv run pytest -m live -s  (cần GEMINI_API_KEY trong .env). Mỗi lần tốn vài lượt free."""
import os

import pytest

from lrh.config import load_settings
from lrh.contracts import GenerateRequest, Message
from lrh.factory import build_embedder, build_generator

S = load_settings()
pytestmark = [pytest.mark.live, pytest.mark.skipif(not (os.environ.get("LRH_LIVE") == "1" and S.gemini_api_key), reason="cần LRH_LIVE=1 và GEMINI_API_KEY")]


def test_live_generate():
    m = build_generator(S.model_id, S, use_cache=False)
    out = m.generate(GenerateRequest(messages=[Message(role="user", content="Trả lời đúng một từ: xin chào bằng tiếng Anh?")], max_output_tokens=256))
    print(out.model_dump())
    assert out.text.strip() and out.usage.prompt_tokens > 0


def test_live_embed_two_texts_two_vectors():
    e = build_embedder(S)
    out = e.embed(["gói ăn 2 người", "chính sách hoàn tiền"], titles=["a", "b"])
    assert len(out.vectors) == 2 and out.dim == S.embedding_dim
