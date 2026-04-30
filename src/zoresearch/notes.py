"""Per-paper persistent notes (T2 layer).

Each Zotero item gets its own file under ``data/notes/<key>.md``. The agent
appends one timestamped section per analysis pass; sections accumulate.
Reading an item should always show existing notes so prior work isn't redone.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from .paths import NOTES


def path_for(item_key: str) -> Path:
    return NOTES / f"{item_key}.md"


def read(item_key: str) -> str:
    p = path_for(item_key)
    return p.read_text() if p.exists() else ""


def append(item_key: str, body: str, *, source: str = "agent", kind: str = "analysis") -> Path:
    p = path_for(item_key)
    p.parent.mkdir(parents=True, exist_ok=True)
    header = f"\n## {date.today().isoformat()} | {source} | {kind}\n\n"
    with p.open("a", encoding="utf-8") as f:
        if not p.exists() or p.stat().st_size == 0:
            f.write(f"# Notes — {item_key}\n")
        f.write(header)
        f.write(body.rstrip() + "\n")
    return p
