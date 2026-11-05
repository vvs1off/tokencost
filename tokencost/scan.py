"""Filesystem scanning: single files, stdin, or a whole repository tree.

Repo mode walks a directory, optionally honouring ``.gitignore`` files and
include/exclude globs, and skips files that look binary. The ``.gitignore``
support covers the common cases -- comments, blank lines, ``!`` negation,
anchored (`/`-prefixed) patterns, directory-only (`/`-suffixed) patterns and
``*``/``?``/``**`` globs -- but is a pragmatic subset, not a bit-for-bit
reimplementation of git. The ``.git`` directory is always skipped.
"""

from __future__ import annotations

import fnmatch
import os
import re
from dataclasses import dataclass
from pathlib import Path

_BINARY_SNIFF_BYTES = 8192


@dataclass(frozen=True)
class ScannedFile:
    path: str          # repo-relative, posix separators
    text: str


@dataclass(frozen=True)
class _Rule:
    base: str          # dir (repo-relative, posix) the pattern is scoped to
    regex: re.Pattern
    dir_only: bool
    negate: bool


def _translate(pattern: str) -> str:
    """Translate a gitignore glob body into a regex matching one path."""
    out = []
    i, n = 0, len(pattern)
    while i < n:
        c = pattern[i]
        if c == "*":
            if i + 1 < n and pattern[i + 1] == "*":
                out.append(".*")
                i += 2
                if i < n and pattern[i] == "/":
                    i += 1
                continue
            out.append("[^/]*")
        elif c == "?":
            out.append("[^/]")
        else:
            out.append(re.escape(c))
        i += 1
    return "".join(out)


def _compile_rules(base: str, lines: list[str]) -> list[_Rule]:
    rules: list[_Rule] = []
    for raw in lines:
        line = raw.rstrip("\n").rstrip("\r")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        line = line.rstrip()
        negate = line.startswith("!")
        if negate:
            line = line[1:]
        dir_only = line.endswith("/")
        if dir_only:
            line = line[:-1]
        anchored = line.startswith("/") or ("/" in line)
        if line.startswith("/"):
            line = line[1:]
        body = _translate(line)
        if anchored:
            regex = re.compile("^" + body + r"(/.*)?$")
        else:
            regex = re.compile(r"(^|.*/)" + body + r"(/.*)?$")
        rules.append(_Rule(base=base, regex=regex, dir_only=dir_only, negate=negate))
    return rules


def _is_ignored(rel_path: str, is_dir: bool, rules: list[_Rule]) -> bool:
    ignored = False
    for rule in rules:
        if rule.dir_only and not is_dir:
            continue
        if rule.base:
            prefix = rule.base + "/"
            if not rel_path.startswith(prefix):
                continue
            sub = rel_path[len(prefix):]
        else:
            sub = rel_path
        if rule.regex.match(sub):
            ignored = not rule.negate
    return ignored


def _read_gitignore(path: Path) -> list[str]:
    try:
        return path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []


def _decode_or_none(data: bytes) -> str | None:
    if b"\x00" in data[:_BINARY_SNIFF_BYTES]:
        return None
    return data.decode("utf-8", errors="replace")


def read_file_text(path: str | os.PathLike) -> str:
    """Read a file as text, decoding UTF-8 and replacing invalid bytes."""
    data = Path(path).read_bytes()
    return data.decode("utf-8", errors="replace")


def _matches_globs(rel_path: str, include: list[str], exclude: list[str]) -> bool:
    if include and not any(fnmatch.fnmatch(rel_path, g) for g in include):
        return False
    if any(fnmatch.fnmatch(rel_path, g) for g in exclude):
        return False
    return True


def scan_tree(
    root: str | os.PathLike,
    *,
    use_gitignore: bool = True,
    include: list[str] | None = None,
    exclude: list[str] | None = None,
) -> list[ScannedFile]:
    """Walk ``root`` and return text files, honouring gitignore and globs."""
    root_path = Path(root)
    include = include or []
    exclude = exclude or []
    rules: list[_Rule] = []
    results: list[ScannedFile] = []

    for dirpath, dirnames, filenames in os.walk(root_path):
        rel_dir = os.path.relpath(dirpath, root_path)
        rel_dir = "" if rel_dir == "." else rel_dir.replace(os.sep, "/")

        if use_gitignore:
            gi = Path(dirpath) / ".gitignore"
            if gi.is_file():
                rules.extend(_compile_rules(rel_dir, _read_gitignore(gi)))

        kept_dirs = []
        for d in sorted(dirnames):
            if d == ".git":
                continue
            rel = f"{rel_dir}/{d}" if rel_dir else d
            if use_gitignore and _is_ignored(rel, True, rules):
                continue
            kept_dirs.append(d)
        dirnames[:] = kept_dirs

        for f in sorted(filenames):
            rel = f"{rel_dir}/{f}" if rel_dir else f
            if use_gitignore and _is_ignored(rel, False, rules):
                continue
            if not _matches_globs(rel, include, exclude):
                continue
            try:
                data = (Path(dirpath) / f).read_bytes()
            except OSError:
                continue
            text = _decode_or_none(data)
            if text is None:
                continue
            results.append(ScannedFile(path=rel, text=text))

    results.sort(key=lambda s: s.path)
    return results
