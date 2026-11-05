"""Price tables and cost computation.

IMPORTANT: the shipped prices are ILLUSTRATIVE PLACEHOLDERS, not quoted rates.
Provider pricing changes often and varies by region, tier and context length.
Always override the table with current numbers from the provider before trusting
a cost. The value of this tool is the mechanism (count -> cost), not the shipped
figures. Every default entry carries ``"verified": false``.

Prices are expressed in USD per 1,000,000 tokens, split into input (prompt) and
output (completion) rates. Override by passing ``--pricing FILE`` or setting
``TOKENCOST_PRICING`` to a JSON file shaped like:

    {
      "currency": "USD",
      "per_tokens": 1000000,
      "models": {
        "my-model": {"input": 3.0, "output": 15.0}
      }
    }

A user file is merged over the defaults: listed models are replaced or added,
unlisted defaults are kept.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

PRICING_ENV_VAR = "TOKENCOST_PRICING"

# Placeholder rates (USD per 1,000,000 tokens). VERIFY against the provider.
# These are deliberately round and are not quoted current prices.
DEFAULT_PRICING: dict = {
    "currency": "USD",
    "per_tokens": 1_000_000,
    "_meta": {
        "verified": False,
        "note": "Illustrative placeholder prices. Override before trusting costs.",
    },
    "models": {
        "small":  {"input": 0.50,  "output": 1.50,  "verified": False},
        "medium": {"input": 3.00,  "output": 15.00, "verified": False},
        "large":  {"input": 15.00, "output": 75.00, "verified": False},
    },
}


class PricingError(Exception):
    """Raised when a pricing table or model lookup is invalid."""


@dataclass(frozen=True)
class ModelPrice:
    name: str
    input_per_m: float
    output_per_m: float
    currency: str
    per_tokens: int
    verified: bool

    def cost(self, input_tokens: int, output_tokens: int) -> float:
        rate = (
            input_tokens * self.input_per_m + output_tokens * self.output_per_m
        )
        return rate / self.per_tokens


def _validate_rate(model: str, field: str, value) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise PricingError(f"model {model!r}: {field} must be a number")
    if value < 0:
        raise PricingError(f"model {model!r}: {field} must be >= 0")
    return float(value)


def load_pricing(path: str | os.PathLike | None = None) -> dict:
    """Return a pricing table, merging an optional user file over the defaults.

    ``path`` takes precedence over the ``TOKENCOST_PRICING`` environment variable.
    """
    source = path or os.environ.get(PRICING_ENV_VAR)
    table = {
        "currency": DEFAULT_PRICING["currency"],
        "per_tokens": DEFAULT_PRICING["per_tokens"],
        "models": dict(DEFAULT_PRICING["models"]),
    }
    if not source:
        return table

    p = Path(source)
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise PricingError(f"pricing file not found: {p}")
    except json.JSONDecodeError as exc:
        raise PricingError(f"pricing file is not valid JSON ({p}): {exc}")
    if not isinstance(raw, dict):
        raise PricingError(f"pricing file must be a JSON object: {p}")

    if "currency" in raw:
        table["currency"] = str(raw["currency"])
    if "per_tokens" in raw:
        per = raw["per_tokens"]
        if not isinstance(per, int) or isinstance(per, bool) or per <= 0:
            raise PricingError("per_tokens must be a positive integer")
        table["per_tokens"] = per

    models = raw.get("models", {})
    if not isinstance(models, dict):
        raise PricingError("'models' must be a JSON object")
    for name, spec in models.items():
        if not isinstance(spec, dict):
            raise PricingError(f"model {name!r} must be a JSON object")
        if "input" not in spec or "output" not in spec:
            raise PricingError(f"model {name!r} needs 'input' and 'output'")
        entry = {
            "input": _validate_rate(name, "input", spec["input"]),
            "output": _validate_rate(name, "output", spec["output"]),
            "verified": bool(spec.get("verified", True)),
        }
        table["models"][name] = entry
    return table


def available_models(table: dict) -> list[str]:
    return sorted(table["models"])


def resolve_model(table: dict, name: str) -> ModelPrice:
    models = table["models"]
    if name not in models:
        raise PricingError(
            f"unknown model {name!r}; available: {', '.join(available_models(table))}"
        )
    spec = models[name]
    return ModelPrice(
        name=name,
        input_per_m=float(spec["input"]),
        output_per_m=float(spec["output"]),
        currency=table["currency"],
        per_tokens=int(table["per_tokens"]),
        verified=bool(spec.get("verified", False)),
    )
