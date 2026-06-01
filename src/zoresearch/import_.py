"""Importing new papers into Zotero through the local connector API.

We do not write to ``zotero.sqlite`` directly. Flow per item:

1. Resolve input (DOI / arXiv id / URL) to a normalised arXiv id or DOI.
2. Pull metadata from OpenAlex (free, no key required).
3. Download the PDF locally — straight from arXiv when possible.
4. POST to ``/connector/saveItems`` (creates the parent item) immediately
   followed by ``/connector/saveAttachment`` (uploads the PDF) **in the same
   ``httpx.Client`` connection** — Zotero pairs the attachment to the
   most-recently-saved item in that session. Sleeps between the two calls
   cause SESSION_NOT_FOUND.

Optional ``collection`` argument places the new item into a Zotero
collection (e.g. a "Metronome" research workspace).

Zotero must be running for any of this to work.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import httpx

from . import openalex, zot

ZOTERO_API = "http://127.0.0.1:23119"
Source = Literal["doi", "arxiv", "url", "unknown"]


_DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$", re.IGNORECASE)
_ARXIV_RE = re.compile(r"^(arxiv:)?(\d{4}\.\d{4,5})(v\d+)?$", re.IGNORECASE)
_ARXIV_OLD_RE = re.compile(r"^(arxiv:)?([a-z\-]+/\d{7})(v\d+)?$", re.IGNORECASE)
_ARXIV_URL_RE = re.compile(r"arxiv\.org/(?:abs|pdf)/([\d\.]+|[a-z\-]+/\d+)", re.IGNORECASE)


@dataclass
class ResolvedTarget:
    kind: Source
    arxiv_id: str = ""        # if arxiv: e.g. "2410.24164"
    doi: str = ""             # if doi: e.g. "10.48550/arxiv.2410.24164"
    url: str = ""             # canonical URL


@dataclass
class ImportResult:
    target: ResolvedTarget
    item_saved: bool = False
    pdf_attached: bool = False
    item_key: str = ""        # not always recoverable
    error: str = ""
    metadata: dict = field(default_factory=dict)


def classify(value: str) -> Source:
    v = value.strip()
    if "arxiv.org/" in v:
        return "arxiv"
    if _DOI_RE.match(v) or v.lower().startswith("doi:") or "doi.org/" in v:
        return "doi"
    if _ARXIV_RE.match(v) or _ARXIV_OLD_RE.match(v):
        return "arxiv"
    if v.startswith("http://") or v.startswith("https://"):
        return "url"
    return "unknown"


def resolve(value: str) -> ResolvedTarget:
    v = value.strip()
    kind = classify(v)
    if kind == "arxiv":
        m = _ARXIV_URL_RE.search(v) or _ARXIV_RE.match(v) or _ARXIV_OLD_RE.match(v)
        aid = m.group(1) if m and "arxiv.org" in v else (m.group(2) if m else "")
        if not aid:
            raise ValueError(f"could not extract arXiv id from {value!r}")
        return ResolvedTarget(
            kind="arxiv", arxiv_id=aid,
            doi=f"10.48550/arxiv.{aid}",
            url=f"https://arxiv.org/abs/{aid}",
        )
    if kind == "doi":
        doi = v
        if doi.lower().startswith("doi:"):
            doi = doi[4:]
        if "doi.org/" in doi:
            doi = doi.split("doi.org/", 1)[1]
        return ResolvedTarget(kind="doi", doi=doi, url=f"https://doi.org/{doi}")
    if kind == "url":
        return ResolvedTarget(kind="url", url=v)
    raise ValueError(f"cannot classify input: {value!r}")


def _shallow_to_zotero_item(s: dict, target: ResolvedTarget) -> dict:
    creators = []
    for name in (s.get("authors") or []):
        if " " in name:
            parts = name.split(" ")
            creators.append({"creatorType": "author", "firstName": " ".join(parts[:-1]), "lastName": parts[-1]})
        else:
            creators.append({"creatorType": "author", "name": name})
    item = {
        "title": s.get("title", "") or f"arXiv:{target.arxiv_id}" if target.arxiv_id else "Untitled",
        "creators": creators,
        "date": str(s.get("year", "")),
        "DOI": target.doi or s.get("doi", ""),
        "url": target.url,
        "abstractNote": (s.get("abstract") or "")[:4000],
    }
    if target.kind == "arxiv":
        item.update({
            "itemType": "preprint",
            "repository": "arXiv",
            "archiveID": f"arXiv:{target.arxiv_id}",
        })
    else:
        item["itemType"] = "journalArticle"
        if s.get("venue"):
            item["publicationTitle"] = s["venue"]
    return item


def _resolve_collection_key(name: str | None) -> str | None:
    """Look up a collection's Zotero key by display name. Read-only sqlite +
    local API are both options; we use the local API since it's already used
    elsewhere and gives us versions for free."""
    if not name:
        return None
    try:
        with httpx.Client(timeout=10) as c:
            r = c.get(f"{ZOTERO_API}/api/users/0/collections", params={"limit": 200})
            r.raise_for_status()
            for col in r.json():
                if col["data"]["name"].lower() == name.lower():
                    return col["key"]
    except httpx.HTTPError:
        return None
    return None


def _resolve_collection_id(name: str | None) -> int | None:
    """Look up a collection's numeric collectionID by display name.

    Zotero's connector /updateSession parses target as <type><id> where id is
    an integer (e.g. ``C80``). The 8-char key (``B3HULW8N``) is not accepted —
    we need the numeric collectionID from the local sqlite.
    """
    if not name:
        return None
    try:
        import sqlite3
        from .paths import ZOTERO_DB
        conn = sqlite3.connect(f"file:{ZOTERO_DB}?mode=ro&immutable=1", uri=True)
        row = conn.execute(
            "SELECT collectionID FROM collections "
            "WHERE LOWER(collectionName)=LOWER(?) "
            "AND collectionID NOT IN (SELECT collectionID FROM deletedCollections)",
            (name,),
        ).fetchone()
        return row[0] if row else None
    except Exception:
        return None


def _download_arxiv_pdf(arxiv_id: str, dest: Path) -> Path:
    """Download the PDF straight from arXiv. Idempotent."""
    if dest.exists() and dest.stat().st_size > 50_000:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    url = f"https://arxiv.org/pdf/{arxiv_id}"
    with httpx.Client(timeout=60, follow_redirects=True,
                      headers={"User-Agent": "Mozilla/5.0 zoresearch"}) as c:
        r = c.get(url)
        r.raise_for_status()
    dest.write_bytes(r.content)
    return dest


def import_one(value: str, *, collection: str | None = None,
               pdf_dir: Path | None = None) -> ImportResult:
    """Resolve, fetch metadata, download PDF (if available), push to Zotero."""
    if not zot.zotero_running():
        raise RuntimeError(
            "Zotero is not reachable on 127.0.0.1:23119. "
            "Open Zotero and try again — the connector endpoint needs the app running."
        )
    target = resolve(value)
    coll_id = _resolve_collection_id(collection) if collection else None
    if collection and coll_id is None:
        return ImportResult(target=target, error=f"collection {collection!r} not found in Zotero")

    # 1) metadata
    if target.kind == "arxiv":
        work = openalex.by_doi(target.doi)
    elif target.kind == "doi":
        work = openalex.by_doi(target.doi)
    else:
        work = None
    shallow = openalex.shallow(work) if work else {}
    item = _shallow_to_zotero_item(shallow, target)
    item.setdefault("tags", []).append({"tag": "zr-imported"})

    # 2) PDF (arXiv only — DOIs are usually paywalled)
    pdf_bytes: bytes | None = None
    if target.kind == "arxiv":
        pdf_dir = pdf_dir or Path("data/imports")
        pdf_path = _download_arxiv_pdf(target.arxiv_id, pdf_dir / f"{target.arxiv_id}.pdf")
        pdf_bytes = pdf_path.read_bytes()

    # 3) push to Zotero — saveItems + saveAttachment in one connection, no sleep
    sess = f"zr-import-{int(time.time() * 1000)}"
    # NOTE: Zotero's /connector/saveItems endpoint ignores any `collections`
    # field in the payload — it always files to the active UI target. To file
    # into a named collection we follow up with /connector/updateSession,
    # which is the same endpoint the browser extension's "Save to" dropdown
    # hits after the connector save completes. Target syntax: L<libraryID>/C<collKey>;
    # for the personal library that's L1/C<key>.
    payload = {"sessionID": sess, "uri": target.url, "items": [item]}
    with httpx.Client(timeout=120) as c:
        r1 = c.post(f"{ZOTERO_API}/connector/saveItems", json=payload)
        if r1.status_code not in (200, 201):
            return ImportResult(target=target, error=f"saveItems {r1.status_code}: {r1.text[:120]}", metadata=item)
        result = ImportResult(target=target, item_saved=True, metadata=item)
        if pdf_bytes:
            metadata_hdr = {
                "sessionID": sess, "id": f"a-{target.arxiv_id or 'doi'}",
                "url": f"https://arxiv.org/pdf/{target.arxiv_id}" if target.arxiv_id else target.url,
                "title": "arXiv Fulltext PDF" if target.kind == "arxiv" else "Fulltext PDF",
                "mimeType": "application/pdf",
            }
            r2 = c.post(
                f"{ZOTERO_API}/connector/saveAttachment",
                headers={"X-Metadata": json.dumps(metadata_hdr), "Content-Type": "application/pdf"},
                content=pdf_bytes,
            )
            if r2.status_code in (200, 201):
                result.pdf_attached = True
            else:
                result.error = f"saveAttachment {r2.status_code}: {r2.text[:120]}"
        # 4) file into collection via updateSession (same connector session
        # the browser extension uses for its "Save to" dropdown). The target
        # parser at server_connector.js parses `<type><parseInt(rest)>`, so
        # we must send a bare ``C<collectionID>`` (numeric), NOT the 8-char
        # collectionKey nor an ``L<lib>/C<id>`` form (the slash gets eaten).
        if coll_id is not None:
            try:
                r3 = c.post(
                    f"{ZOTERO_API}/connector/updateSession",
                    json={"sessionID": sess, "target": f"C{coll_id}"},
                )
                if r3.status_code not in (200, 201):
                    result.error = (result.error or "") + f" updateSession {r3.status_code}: {r3.text[:80]}"
            except httpx.HTTPError as e:
                result.error = (result.error or "") + f" updateSession error: {e}"
        return result


# Back-compat shim — the CLI used to call this.
def to_url(value: str) -> str:
    return resolve(value).url
