"""Terminal styling for zr's user-facing output.

Set ``ZORESEARCH_PLAIN=1`` to drop colours and marks.
"""
from __future__ import annotations

import os

PLAIN = bool(os.environ.get("ZORESEARCH_PLAIN"))

ACCENT = "bright_cyan"
HIGHLIGHT = "yellow"
ERROR = "bright_red"
SUCCESS = "bright_green"
DIM = "dim cyan"

OK_MARK = "✓"
OFF_MARK = "·"
WARN_MARK = "!"
BULLET = "•"


def ok(plain: str) -> str:
    return f"ok  {plain}" if PLAIN else f"[{SUCCESS}]{OK_MARK}[/{SUCCESS}] {plain}"


def warn(plain: str) -> str:
    return f"warn  {plain}" if PLAIN else f"[{HIGHLIGHT}]{WARN_MARK}[/{HIGHLIGHT}] {plain}"


def err(plain: str) -> str:
    return f"err  {plain}" if PLAIN else f"[{ERROR}]✕[/{ERROR}] {plain}"


def info(plain: str) -> str:
    return f"info  {plain}" if PLAIN else f"[{DIM}]{OFF_MARK}[/{DIM}] {plain}"


def status_icon(state: str) -> str:
    """Map a doctor status to a coloured mark."""
    if PLAIN:
        return state
    return {
        "ok":      f"[{SUCCESS}]{OK_MARK}[/{SUCCESS}] ok",
        "warn":    f"[{HIGHLIGHT}]{WARN_MARK}[/{HIGHLIGHT}] warn",
        "missing": f"[{ERROR}]✕[/{ERROR}] missing",
        "off":     f"[{ERROR}]✕[/{ERROR}] off",
        "info":    f"[{DIM}]{OFF_MARK}[/{DIM}] info",
    }.get(state, state)


def title(text: str) -> str:
    return text if PLAIN else f"[{ACCENT} bold]{text}[/{ACCENT} bold]"


PHRASES = {
    "doctor_ready":     "All checks passed",
    "doctor_partial":   "Some checks need attention",
    "lib_overview":     "Library overview",
    "import_added":     "Added to Zotero",
    "import_pending":   "Importing…",
    "parse_done":       "Parsed",
    "parse_cached":     "Already parsed, using the cached transcript",
    "related_done":     "Related work",
    "trends_done":      "Topic trends",
    "ws_created":       "Workspace created",
    "ws_seed_added":    "Seed added",
    "ws_related_done":  "Related work collected",
    "notes_appended":   "Note appended",
    "notes_empty":      "No notes yet",
    "section_abstract": "Abstract",
    "section_notes":    "Notes",
}


def say(key: str, *, plain: str | None = None) -> str:
    return PHRASES.get(key, plain or key)
