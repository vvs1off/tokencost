"""Assemble token counts into a cost report and render it."""

from __future__ import annotations

from dataclasses import dataclass, field

from . import __version__
from .pricing import ModelPrice


@dataclass
class FileCount:
    path: str
    tokens: int


@dataclass
class Report:
    method: str
    currency: str
    per_tokens: int
    input_tokens: int
    output_tokens: int
    prices: list[ModelPrice]
    files: list[FileCount] = field(default_factory=list)

    @property
    def file_count(self) -> int:
        return len(self.files)

    @property
    def prices_verified(self) -> bool:
        return all(p.verified for p in self.prices) if self.prices else False

    def to_dict(self) -> dict:
        models = []
        for p in self.prices:
            input_cost = self.input_tokens * p.input_per_m / p.per_tokens
            output_cost = self.output_tokens * p.output_per_m / p.per_tokens
            models.append(
                {
                    "model": p.name,
                    "input_cost": round(input_cost, 8),
                    "output_cost": round(output_cost, 8),
                    "total_cost": round(input_cost + output_cost, 8),
                    "verified": p.verified,
                }
            )
        out = {
            "tokencost_version": __version__,
            "method": self.method,
            "currency": self.currency,
            "per_tokens": self.per_tokens,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "file_count": self.file_count,
            "prices_verified": self.prices_verified,
            "models": models,
        }
        if self.files:
            out["files"] = [{"path": f.path, "tokens": f.tokens} for f in self.files]
        return out


def _fmt_money(value: float) -> str:
    return f"{value:.6f}"


def render_text(report: Report, *, by_file: bool = False) -> str:
    lines: list[str] = []
    d = report.to_dict()

    if report.file_count:
        header = f"tokencost — {report.file_count} file(s)"
    else:
        header = "tokencost"
    lines.append(header)
    lines.append(f"method: {report.method}   currency: {report.currency}")
    lines.append(f"input tokens:  {report.input_tokens:,}")
    lines.append(f"output tokens: {report.output_tokens:,}")
    lines.append("")

    if by_file and report.files:
        width = max((len(f.path) for f in report.files), default=4)
        lines.append(f"{'FILE'.ljust(width)}  TOKENS")
        for f in sorted(report.files, key=lambda x: (-x.tokens, x.path)):
            lines.append(f"{f.path.ljust(width)}  {f.tokens:>8,}")
        lines.append("")

    if report.prices:
        name_w = max(max(len(p.name) for p in report.prices), len("MODEL"))
        lines.append(
            f"{'MODEL'.ljust(name_w)}  {'INPUT':>12}  {'OUTPUT':>12}  {'TOTAL':>12}"
        )
        for m in d["models"]:
            lines.append(
                f"{m['model'].ljust(name_w)}  "
                f"{_fmt_money(m['input_cost']):>12}  "
                f"{_fmt_money(m['output_cost']):>12}  "
                f"{_fmt_money(m['total_cost']):>12}"
            )
        lines.append("")

    if not report.prices_verified:
        lines.append(
            "note: prices are UNVERIFIED placeholders — override with --pricing "
            "and verify against the provider."
        )
    lines.append(
        "note: token counts are heuristic estimates, not an exact tokenizer."
    )
    return "\n".join(lines)
