"""Config loader. Reads ~/.zoresearch/config.toml + a few env vars.

The user-scoped config lives **outside** the repo so secrets cannot leak through
git. Order of precedence:

    env > ~/.zoresearch/config.toml > built-in defaults
"""
from __future__ import annotations

import os
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

USER_CONFIG = Path.home() / ".zoresearch" / "config.toml"


def _load_user_config() -> dict[str, Any]:
    if not USER_CONFIG.exists():
        return {}
    with USER_CONFIG.open("rb") as f:
        return tomllib.load(f)


@dataclass
class MinerUConfig:
    token: str = ""
    endpoint: str = "https://mineru.net/api/v4"
    enable_formula: bool = True
    enable_table: bool = True
    language: str = "auto"


@dataclass
class Config:
    mineru: MinerUConfig = field(default_factory=MinerUConfig)
    default_engine: str = "mineru"

    @property
    def parse_engine(self) -> str:
        return os.environ.get("ZORESEARCH_ENGINE", self.default_engine)


def load() -> Config:
    raw = _load_user_config()
    m = raw.get("mineru", {})
    p = raw.get("parse", {})
    cfg = Config(
        mineru=MinerUConfig(
            token=os.environ.get("MINERU_TOKEN") or m.get("token", ""),
            endpoint=m.get("endpoint", "https://mineru.net/api/v4"),
            enable_formula=p.get("enable_formula", True),
            enable_table=p.get("enable_table", True),
            language=p.get("language", "auto"),
        ),
        default_engine=m.get("default_engine", "mineru"),
    )
    return cfg


CONFIG: Config = load()


def warn_no_token() -> None:
    if not CONFIG.mineru.token:
        print(
            "warning: no MinerU token configured. "
            f"Set MINERU_TOKEN in env or write [mineru].token to {USER_CONFIG}",
            file=sys.stderr,
        )
