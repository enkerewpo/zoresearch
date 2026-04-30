"""Importing new papers into Zotero through the local connector API.

We do not write to ``zotero.sqlite`` directly. We:

1. Resolve the input (DOI / arXiv id / URL) into a URL Zotero's translators can
   parse.
2. POST to ``http://127.0.0.1:23119/connector/savePage`` (the same endpoint
   the browser button uses).
3. Zotero handles metadata extraction + PDF download + storage placement.

Zotero must be running for any of this to work.
"""
from __future__ import annotations

import re
from typing import Literal

from . import zot

Source = Literal["doi", "arxiv", "url", "unknown"]


_DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$", re.IGNORECASE)
_ARXIV_RE = re.compile(r"^(arxiv:)?(\d{4}\.\d{4,5})(v\d+)?$", re.IGNORECASE)
_ARXIV_OLD_RE = re.compile(r"^(arxiv:)?([a-z\-]+/\d{7})(v\d+)?$", re.IGNORECASE)


def classify(value: str) -> Source:
    v = value.strip()
    if _DOI_RE.match(v) or v.lower().startswith("doi:") or "doi.org/" in v:
        return "doi"
    if _ARXIV_RE.match(v) or _ARXIV_OLD_RE.match(v) or "arxiv.org/" in v:
        return "arxiv"
    if v.startswith("http://") or v.startswith("https://"):
        return "url"
    return "unknown"


def to_url(value: str) -> str:
    v = value.strip()
    kind = classify(v)
    if kind == "doi":
        doi = v
        if doi.lower().startswith("doi:"):
            doi = doi[4:]
        if "doi.org" not in doi:
            doi = f"https://doi.org/{doi}"
        return doi
    if kind == "arxiv":
        m = _ARXIV_RE.match(v) or _ARXIV_OLD_RE.match(v)
        if "arxiv.org" in v:
            return v
        if m:
            return f"https://arxiv.org/abs/{m.group(2)}"
        return v
    if kind == "url":
        return v
    raise ValueError(f"cannot classify input: {value!r}")


def import_one(value: str) -> dict:
    if not zot.zotero_running():
        raise RuntimeError(
            "Zotero is not reachable on 127.0.0.1:23119. "
            "Open Zotero and try again — the connector endpoint needs the app running."
        )
    url = to_url(value)
    return zot.connector_translate(url)
