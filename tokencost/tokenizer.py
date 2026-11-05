"""Offline, deterministic token-count estimation.

These are *estimates*. tokencost does not bundle a vendor tokenizer, so counts
approximate how byte-pair-encoding tokenizers (GPT, Claude, etc.) tend to split
text. Expect the heuristic to land within roughly +/-20% of a real tokenizer on
ordinary prose and code, with larger error on unusual input (long base64 blobs,
dense punctuation, non-Latin scripts). For billing-grade numbers, run the
provider's own tokenizer; for budgeting and comparison, this is enough.

Two methods are provided:

* ``heuristic`` (default) -- classifies the text into runs of letters, digits,
  whitespace and other characters and sizes each run the way BPE merges tend to.
* ``chars`` -- a flat ``len(text) / divisor`` estimate (divisor defaults to 4),
  the widely cited "~4 characters per token" rule of thumb.

Both are pure functions of the input and contain no randomness.
"""

from __future__ import annotations

import math
import re

METHODS = ("heuristic", "chars")
DEFAULT_METHOD = "heuristic"
DEFAULT_CHARS_PER_TOKEN = 4.0

# One chunk = a maximal run of a single character class.
_CHUNK_RE = re.compile(
    r"[^\W\d_]+"      # letters (unicode-aware word chars minus digits/underscore)
    r"|\d+"           # digit runs
    r"|\s+"           # whitespace runs
    r"|[^\w\s]|_",    # a single punctuation/symbol char, or underscore
    re.UNICODE,
)


def _letters_tokens(length: int) -> int:
    # English averages ~4 characters per token; short common words are 1 token.
    return max(1, round(length / 4))


def _digit_tokens(length: int) -> int:
    # Numbers fragment more than words (often 1-3 digits per token).
    return max(1, math.ceil(length / 3))


def _whitespace_tokens(chunk: str) -> int:
    # Spaces are usually absorbed into the following token by BPE tokenizers;
    # newlines commonly cost a token each.
    return chunk.count("\n")


def estimate_tokens(
    text: str,
    method: str = DEFAULT_METHOD,
    chars_per_token: float = DEFAULT_CHARS_PER_TOKEN,
) -> int:
    """Estimate the number of tokens in ``text``.

    Raises ``ValueError`` for an unknown method or a non-positive divisor.
    """
    if method not in METHODS:
        raise ValueError(f"unknown method: {method!r} (choose from {', '.join(METHODS)})")
    if not text:
        return 0

    if method == "chars":
        if chars_per_token <= 0:
            raise ValueError("chars_per_token must be > 0")
        return max(1, round(len(text) / chars_per_token))

    total = 0
    for chunk in _CHUNK_RE.findall(text):
        first = chunk[0]
        if first.isspace():
            total += _whitespace_tokens(chunk)
        elif first.isdigit():
            total += _digit_tokens(len(chunk))
        elif chunk.isalpha() or (len(chunk) > 1):
            total += _letters_tokens(len(chunk))
        else:
            total += 1  # single punctuation/symbol/underscore
    return max(1, total)
