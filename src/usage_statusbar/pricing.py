"""模型計價表（每 100 萬 tokens 的美金價格）。

這些數字用於「估算」用量成本，並非帳單真實金額。
官方計價可能調整，必要時請更新此表。
"""

from __future__ import annotations

# (input_per_mtok, output_per_mtok)
# 比對方式：用 model 字串做「前綴 / 子字串」比對，越靠前越優先。
_PRICES: list[tuple[str, float, float]] = [
    ("claude-fable", 10.0, 50.0),
    ("claude-mythos", 10.0, 50.0),
    ("claude-opus-4-8", 5.0, 25.0),
    ("claude-opus-4-7", 5.0, 25.0),
    ("claude-opus-4-6", 5.0, 25.0),
    ("claude-opus-4-5", 5.0, 25.0),
    ("claude-opus-4-1", 15.0, 75.0),
    ("claude-opus-4", 15.0, 75.0),
    ("claude-opus", 15.0, 75.0),
    ("claude-sonnet-4-6", 3.0, 15.0),
    ("claude-sonnet-4-5", 3.0, 15.0),
    ("claude-sonnet-4", 3.0, 15.0),
    ("claude-sonnet", 3.0, 15.0),
    ("claude-haiku-4-5", 1.0, 5.0),
    ("claude-haiku-3-5", 0.8, 4.0),
    ("claude-haiku", 0.25, 1.25),
]

# 快取定價倍率（相對 input 價格）
_CACHE_WRITE_MULT = 1.25
_CACHE_READ_MULT = 0.10

_DEFAULT = (5.0, 25.0)  # 未知模型先當 opus 級估算


def _rates(model: str | None) -> tuple[float, float]:
    if not model:
        return _DEFAULT
    m = model.lower()
    for key, inp, out in _PRICES:
        if key in m:
            return inp, out
    return _DEFAULT


def estimate_cost(model: str | None, usage: dict) -> float:
    """依單筆 usage 估算美金成本。"""
    inp_rate, out_rate = _rates(model)
    input_tokens = usage.get("input_tokens", 0) or 0
    output_tokens = usage.get("output_tokens", 0) or 0
    cache_write = usage.get("cache_creation_input_tokens", 0) or 0
    cache_read = usage.get("cache_read_input_tokens", 0) or 0

    cost = (
        input_tokens * inp_rate
        + output_tokens * out_rate
        + cache_write * inp_rate * _CACHE_WRITE_MULT
        + cache_read * inp_rate * _CACHE_READ_MULT
    ) / 1_000_000
    return cost
