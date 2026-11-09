"""Hạn mức tầng Free của project chủ repo, từng mô hình. Nguồn chuẩn: Brain/Accounts/Gemini-API.md (vault) và docs/PROVIDERS.md mục 2b.
Số từ ảnh chụp AI Studio ngày 2026-11-08; có thể đổi, Google ghi hạn mức "không được đảm bảo". Cập nhật khi chủ repo báo."""
from __future__ import annotations

from dataclasses import dataclass

from lrh.limiter import Limits

AS_OF = "2026-11-08"


@dataclass(frozen=True)
class ModelSpec:
    limits: Limits
    price_in_per_m: float = 0.0   # tầng Free = 0
    price_out_per_m: float = 0.0
    # Mức suy nghĩ cố định cho đường đo. None = để mặc định của nhà cung cấp (chưa kiểm cho mô hình đó).
    thinking_level: str | None = None


MODELS: dict[str, ModelSpec] = {
    # HIGH: chủ repo chốt 2026-11-09 sau docs/lab/thinking-level.md. Đặt tường minh (bằng mặc định đo được) để
    # nhà cung cấp đổi mặc định cũng không đổi lặng lẽ điều đang đo. Gemma 4 31B chỉ nhận MINIMAL/HIGH.
    "gemma-4-31b-it": ModelSpec(Limits(rpm=30, tpm=16_000, rpd=14_400), thinking_level="HIGH"),
    # 26B: chưa kiểm mức suy nghĩ nào được nhận; giữ HIGH cho cùng điều kiện với 31B, kiểm khi dùng tới
    "gemma-4-26b-a4b-it": ModelSpec(Limits(rpm=30, tpm=16_000, rpd=14_400), thinking_level="HIGH"),
    # ID "gemini-3.8-flash" lấy từ tài liệu, chưa gọi thử
    "gemini-3.8-flash": ModelSpec(Limits(rpm=5, tpm=250_000, rpd=20)),
}
EMBEDDING_LIMITS = {"gemini-embedding-2": Limits(rpm=100, tpm=30_000, rpd=1_000)}
