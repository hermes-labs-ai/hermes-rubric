"""Explicit in-memory and path input loading with coverage facts."""

from __future__ import annotations

import glob
from dataclasses import dataclass
from pathlib import Path

from .evidence import DEFAULT_TARGET_WINDOW_BYTES, _utf8_prefix, _warn_truncation
from .models import CoverageReport

ELIGIBLE_SUFFIXES = {".md", ".py", ".txt", ".json", ".yaml", ".toml", ".rst"}
MAX_DIRECTORY_SOURCES = 50
MAX_CONTEXT_SOURCES = 5


@dataclass(frozen=True)
class LoadedInput:
    content: str
    display_name: str
    total_bytes: int | None
    total_sources: int | None
    considered_sources: int | None
    loader_limitations: tuple[str, ...] = ()
    directory: bool = False

    def coverage(self, window_bytes: int) -> CoverageReport:
        if isinstance(window_bytes, bool) or not isinstance(window_bytes, int) or window_bytes < 1:
            raise ValueError("target_window_bytes must be a positive integer")

        represented_bytes = len(self.content.encode("utf-8"))
        limitations = list(self.loader_limitations)
        global_truncation = represented_bytes > window_bytes
        if global_truncation:
            limitations.append(
                f"Evidence inspected only the first {window_bytes} UTF-8 bytes of "
                f"the loaded target representation ({represented_bytes} bytes)."
            )

        complete = not limitations and not global_truncation
        if (self.directory and not complete) or self.total_bytes is None:
            visible_bytes = None
        elif self.directory:
            visible_bytes = self.total_bytes
        else:
            visible_text, _ = _utf8_prefix(self.content, window_bytes)
            visible_bytes = len(visible_text.encode("utf-8"))

        return CoverageReport(
            status="complete" if complete else "partial",
            strategy="utf8-prefix",
            visible_bytes=visible_bytes,
            total_bytes=self.total_bytes,
            considered_sources=self.considered_sources,
            total_sources=self.total_sources,
            limitations=tuple(limitations),
        )


def load_text(text: str, *, name: str = "<memory>") -> LoadedInput:
    """Load literal text. Strings are never guessed to be filesystem paths."""
    if not isinstance(text, str):
        raise TypeError("in-memory input must be a string")
    if not isinstance(name, str) or not name:
        raise ValueError("logical source name must be a non-empty string")
    return LoadedInput(
        content=text,
        display_name=name,
        total_bytes=len(text.encode("utf-8")),
        total_sources=1,
        considered_sources=1,
    )


def load_target_path(
    target_path: str | Path,
    *,
    window_bytes: int = DEFAULT_TARGET_WINDOW_BYTES,
) -> LoadedInput:
    """Load a target file or directory while retaining exclusion facts."""
    _validate_window(window_bytes, "target_window_bytes")
    path = Path(target_path).expanduser()
    if path.is_file():
        content = path.read_text(errors="replace")
        content_bytes = len(content.encode("utf-8"))
        if content_bytes > window_bytes:
            _warn_truncation(str(path), content_bytes, window_bytes)
        return LoadedInput(
            content=content,
            display_name=str(path),
            total_bytes=content_bytes,
            total_sources=1,
            considered_sources=1,
        )
    if not path.is_dir():
        raise FileNotFoundError(f"Target not found: {target_path}")

    eligible = [
        item
        for item in sorted(path.rglob("*"))
        if item.is_file() and item.suffix in ELIGIBLE_SUFFIXES
    ]
    considered = eligible[:MAX_DIRECTORY_SOURCES]
    parts: list[str] = []
    limitations: list[str] = []
    total_bytes = 0
    total_known = True
    per_file_truncated = 0
    readable_considered = 0

    for item in eligible:
        try:
            total_bytes += item.stat().st_size
        except OSError:
            total_known = False

    for item in considered:
        try:
            raw = item.read_text(errors="replace")
        except OSError:
            limitations.append(f"Could not read eligible source {item.relative_to(path)}.")
            continue
        visible, truncated = _utf8_prefix(raw, window_bytes)
        if truncated:
            per_file_truncated += 1
            _warn_truncation(str(item), len(raw.encode("utf-8")), window_bytes)
        parts.append(f"=== {item.relative_to(path)} ===\n{visible}")
        readable_considered += 1

    if len(eligible) > MAX_DIRECTORY_SOURCES:
        limitations.append(
            f"Only the first {MAX_DIRECTORY_SOURCES} of {len(eligible)} eligible "
            "directory sources were loaded."
        )
    if per_file_truncated:
        limitations.append(
            f"{per_file_truncated} loaded source(s) exceeded the per-file "
            f"{window_bytes}-byte prefix limit."
        )

    return LoadedInput(
        content="\n\n".join(parts),
        display_name=str(path),
        total_bytes=total_bytes if total_known else None,
        total_sources=len(eligible),
        considered_sources=readable_considered,
        loader_limitations=tuple(limitations),
        directory=True,
    )


def load_context_path(
    context_path: str | Path,
    *,
    window_bytes: int = DEFAULT_TARGET_WINDOW_BYTES,
) -> LoadedInput:
    """Load one context file or an explicit glob, preserving legacy budgets."""
    _validate_window(window_bytes, "context_window_bytes")
    raw_path = str(context_path)
    path = Path(raw_path).expanduser()
    if path.is_file():
        raw = path.read_text(errors="replace")
        visible, truncated = _utf8_prefix(raw, window_bytes)
        if truncated:
            _warn_truncation(str(path), len(raw.encode("utf-8")), window_bytes)
        limitations = (
            (f"Context was limited to its first {window_bytes} UTF-8 bytes.",)
            if truncated
            else ()
        )
        return LoadedInput(
            content=visible,
            display_name=str(path),
            total_bytes=len(raw.encode("utf-8")),
            total_sources=1,
            considered_sources=1,
            loader_limitations=limitations,
        )

    matches = [Path(item) for item in sorted(glob.glob(str(path))) if Path(item).is_file()]
    if not matches:
        return LoadedInput(
            content=f"[context path not found: {context_path}]",
            display_name=raw_path,
            total_bytes=None,
            total_sources=0,
            considered_sources=0,
            loader_limitations=("The context path or glob matched no readable file.",),
        )

    per_file = max(1, window_bytes // 2)
    parts: list[str] = []
    limitations: list[str] = []
    for item in matches[:MAX_CONTEXT_SOURCES]:
        try:
            raw = item.read_text(errors="replace")
        except OSError:
            continue
        visible, truncated = _utf8_prefix(raw, per_file)
        parts.append(visible)
        if truncated:
            _warn_truncation(str(item), len(raw.encode("utf-8")), per_file)
            limitations.append(
                f"Context source {item} was limited to its first {per_file} UTF-8 bytes."
            )
    if len(matches) > MAX_CONTEXT_SOURCES:
        limitations.append(
            f"Only the first {MAX_CONTEXT_SOURCES} of {len(matches)} context matches were loaded."
        )
    return LoadedInput(
        content="\n\n---\n\n".join(parts),
        display_name=raw_path,
        total_bytes=None,
        total_sources=len(matches),
        considered_sources=len(parts),
        loader_limitations=tuple(limitations),
    )


def _validate_window(value: int, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer")
