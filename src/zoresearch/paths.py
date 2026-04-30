"""Filesystem layout. Single source of truth for where things live."""
from __future__ import annotations

import os
from pathlib import Path


def _detect_zotero_data_dir() -> Path:
    env = os.environ.get("ZORESEARCH_ZOTERO_DIR")
    if env:
        return Path(env).expanduser()
    home = Path.home()
    candidates = [
        home / "Zotero",
        home / "Library" / "Application Support" / "Zotero",
    ]
    for c in candidates:
        if (c / "zotero.sqlite").exists():
            return c
    return home / "Zotero"


def repo_root() -> Path:
    here = Path(__file__).resolve()
    for p in [here.parent, *here.parents]:
        if (p / "pyproject.toml").exists() and (p / "src" / "zoresearch").exists():
            return p
    return here.parents[2]


ZOTERO_DIR: Path = _detect_zotero_data_dir()
ZOTERO_DB: Path = ZOTERO_DIR / "zotero.sqlite"
ZOTERO_STORAGE: Path = ZOTERO_DIR / "storage"

REPO: Path = repo_root()
DATA: Path = REPO / "data"
TRANSCRIPTS: Path = DATA / "transcripts"
CITATIONS: Path = DATA / "citations"
NOTES: Path = DATA / "notes"
WORKSPACE: Path = REPO / "workspace"

ZOTERO_LOCAL_API: str = "http://127.0.0.1:23119"


def ensure_dirs() -> None:
    for p in (DATA, TRANSCRIPTS, CITATIONS, NOTES, WORKSPACE):
        p.mkdir(parents=True, exist_ok=True)
