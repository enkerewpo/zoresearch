"""Tiny OpenAlex client for citation graph + topic exploration.

OpenAlex is free and unauthenticated, but they ask for an email in the
``mailto`` query param to get into the polite pool with higher rate limits.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Iterator

import httpx

from .paths import CITATIONS

API = "https://api.openalex.org"
MAILTO = "zoresearch@local"  # cosmetic; OpenAlex just wants a contact


def _client() -> httpx.Client:
    return httpx.Client(
        timeout=30,
        headers={"User-Agent": f"zoresearch ({MAILTO})"},
        params={"mailto": MAILTO},
    )


def _cache_path(slug: str) -> Path:
    safe = slug.replace("/", "_").replace(":", "_")
    return CITATIONS / f"{safe}.json"


def _cached(slug: str, fetcher) -> dict:
    p = _cache_path(slug)
    if p.exists():
        try:
            return json.loads(p.read_text())
        except json.JSONDecodeError:
            pass
    data = fetcher()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2))
    return data


def by_doi(doi: str) -> dict | None:
    if not doi:
        return None
    doi_clean = doi.lower().lstrip()
    if doi_clean.startswith("https://doi.org/"):
        doi_clean = doi_clean[len("https://doi.org/") :]
    slug = f"doi/{doi_clean}"

    def fetch() -> dict:
        with _client() as c:
            r = c.get(f"{API}/works/doi:{doi_clean}")
            if r.status_code == 404:
                return {}
            r.raise_for_status()
            return r.json()

    data = _cached(slug, fetch)
    return data or None


def by_id(openalex_id: str) -> dict | None:
    short = openalex_id.split("/")[-1]
    slug = f"id/{short}"

    def fetch() -> dict:
        with _client() as c:
            r = c.get(f"{API}/works/{short}")
            if r.status_code in (404, 410):
                return {}
            r.raise_for_status()
            return r.json()

    data = _cached(slug, fetch)
    return data or None


def references(work: dict) -> list[dict]:
    """Hydrate referenced_works ids -> shallow work dicts. Dead ids are skipped."""
    out: list[dict] = []
    for ref_id in work.get("referenced_works") or []:
        try:
            w = by_id(ref_id)
        except httpx.HTTPError:
            continue
        if w:
            out.append(w)
    return out


def cited_by(work: dict, *, per_page: int = 50, max_pages: int = 4) -> list[dict]:
    """Forward citations: works that cite ``work``."""
    target = work.get("id")
    if not target:
        return []
    short = target.split("/")[-1]
    slug = f"cited_by/{short}_p{max_pages}_n{per_page}"

    def fetch() -> dict:
        results: list[dict] = []
        cursor = "*"
        with _client() as c:
            for _ in range(max_pages):
                r = c.get(
                    f"{API}/works",
                    params={
                        "filter": f"cites:{short}",
                        "per-page": per_page,
                        "cursor": cursor,
                    },
                )
                r.raise_for_status()
                page = r.json()
                results.extend(page.get("results") or [])
                cursor = ((page.get("meta") or {}).get("next_cursor")) or None
                if not cursor:
                    break
                time.sleep(0.2)
        return {"results": results}

    return _cached(slug, fetch).get("results", [])


def search(query: str, *, per_page: int = 25, max_pages: int = 2, filter_: str | None = None) -> list[dict]:
    slug = f"search/{query[:80]}_p{max_pages}_n{per_page}_{filter_ or ''}"

    def fetch() -> dict:
        results: list[dict] = []
        cursor = "*"
        with _client() as c:
            for _ in range(max_pages):
                params = {
                    "search": query,
                    "per-page": per_page,
                    "cursor": cursor,
                }
                if filter_:
                    params["filter"] = filter_
                r = c.get(f"{API}/works", params=params)
                r.raise_for_status()
                page = r.json()
                results.extend(page.get("results") or [])
                cursor = ((page.get("meta") or {}).get("next_cursor")) or None
                if not cursor:
                    break
                time.sleep(0.2)
        return {"results": results}

    return _cached(slug, fetch).get("results", [])


def shallow(work: dict) -> dict:
    """Project an OpenAlex work to a compact, agent-friendly view."""
    if not work:
        return {}
    authors = []
    for au in (work.get("authorships") or [])[:8]:
        a = au.get("author") or {}
        if a.get("display_name"):
            authors.append(a["display_name"])
    primary = (work.get("primary_location") or {}).get("source") or {}
    return {
        "id": work.get("id"),
        "doi": (work.get("doi") or "").replace("https://doi.org/", ""),
        "title": work.get("title") or "",
        "year": work.get("publication_year"),
        "venue": primary.get("display_name") or "",
        "authors": authors,
        "cited_by_count": work.get("cited_by_count") or 0,
        "abstract": _abstract_from_inverted(work.get("abstract_inverted_index")),
        "concepts": [c.get("display_name") for c in (work.get("concepts") or [])[:5] if c.get("display_name")],
    }


def _abstract_from_inverted(idx: dict | None) -> str:
    if not idx:
        return ""
    positions: list[tuple[int, str]] = []
    for word, pos_list in idx.items():
        for p in pos_list:
            positions.append((p, word))
    positions.sort()
    return " ".join(w for _, w in positions)


def iter_search(query: str, *, per_page: int = 50) -> Iterator[dict]:
    cursor = "*"
    with _client() as c:
        while cursor:
            r = c.get(
                f"{API}/works",
                params={"search": query, "per-page": per_page, "cursor": cursor},
            )
            r.raise_for_status()
            page = r.json()
            for w in page.get("results") or []:
                yield w
            cursor = ((page.get("meta") or {}).get("next_cursor"))
            time.sleep(0.2)
