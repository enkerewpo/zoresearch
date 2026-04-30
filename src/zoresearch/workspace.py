"""Workspaces — one directory per research question.

A workspace owns the user's framing of a problem plus the set of seed papers
and the agent's accumulated synthesis. Workspaces live under
``workspace/<slug>/`` and are gitignored by default — they are personal
research scratch.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .paths import WORKSPACE


def _slugify(name: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "-", name).strip("-").lower()
    return s or "workspace"


def root(name: str) -> Path:
    return WORKSPACE / _slugify(name)


def init(name: str, question: str = "") -> Path:
    d = root(name)
    if d.exists():
        return d
    d.mkdir(parents=True, exist_ok=True)
    (d / "question.md").write_text(
        f"# {name}\n\n{question or '(write the research question here)'}\n",
        encoding="utf-8",
    )
    (d / "seeds.txt").write_text(
        "# one Zotero key, citekey, DOI, or arXiv id per line\n",
        encoding="utf-8",
    )
    (d / "related.md").write_text(
        f"# Related work — {name}\n\n_(populated by `zr ws related {name}`)_\n",
        encoding="utf-8",
    )
    (d / "notes.md").write_text(
        f"# Notes — {name}\n\n", encoding="utf-8"
    )
    return d


def add_seed(name: str, seed: str) -> Path:
    d = root(name)
    if not d.exists():
        raise FileNotFoundError(f"workspace not found: {name} (try `zr ws init`)")
    seeds = d / "seeds.txt"
    existing = seeds.read_text() if seeds.exists() else ""
    if seed.strip() in existing.splitlines():
        return seeds
    with seeds.open("a", encoding="utf-8") as f:
        f.write(seed.strip() + "\n")
    return seeds


def list_workspaces() -> list[str]:
    if not WORKSPACE.exists():
        return []
    return sorted(p.name for p in WORKSPACE.iterdir() if p.is_dir())


@dataclass
class Workspace:
    name: str
    path: Path

    @property
    def question(self) -> str:
        p = self.path / "question.md"
        return p.read_text() if p.exists() else ""

    @property
    def seeds(self) -> list[str]:
        p = self.path / "seeds.txt"
        if not p.exists():
            return []
        return [
            line.strip()
            for line in p.read_text().splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]


def load(name: str) -> Workspace:
    d = root(name)
    if not d.exists():
        raise FileNotFoundError(f"workspace not found: {name}")
    return Workspace(name=d.name, path=d)
