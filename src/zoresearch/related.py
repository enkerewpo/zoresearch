"""Related-work discovery: backward refs + forward citations + library dedupe."""
from __future__ import annotations

from dataclasses import dataclass

from . import openalex, zot


@dataclass
class RelatedWork:
    title: str
    authors: list[str]
    year: int | None
    doi: str
    venue: str
    cited_by_count: int
    direction: str  # "backward" | "forward" | "neighbor"
    in_library: bool
    library_key: str = ""
    abstract: str = ""

    def line(self) -> str:
        flag = "✓" if self.in_library else " "
        a = self.authors[0].split()[-1] if self.authors else "Anon"
        y = self.year or "n.d."
        cit = f"[{self.cited_by_count}cit]"
        return f"[{flag}] {self.direction[:3]} {cit:<8} {a} {y} — {self.title[:90]}"


def _library_doi_index() -> dict[str, str]:
    """DOI (lowercased) -> Zotero item key, for items already in the library."""
    out: dict[str, str] = {}
    for item in zot.iter_items():
        if item.doi:
            out[item.doi.lower()] = item.key
    return out


def _project(work: dict, direction: str, lib_index: dict[str, str]) -> RelatedWork:
    s = openalex.shallow(work)
    doi = s.get("doi") or ""
    in_lib = doi.lower() in lib_index if doi else False
    return RelatedWork(
        title=s.get("title", ""),
        authors=s.get("authors", []),
        year=s.get("year"),
        doi=doi,
        venue=s.get("venue", ""),
        cited_by_count=s.get("cited_by_count", 0),
        direction=direction,
        in_library=in_lib,
        library_key=lib_index.get(doi.lower(), "") if doi else "",
        abstract=s.get("abstract", ""),
    )


def for_item(item_key: str, *, max_forward: int = 80) -> list[RelatedWork]:
    item = zot.get_item(item_key)
    if item is None:
        raise ValueError(f"item not found: {item_key}")
    if not item.doi:
        raise ValueError(
            f"item {item.key} has no DOI; OpenAlex lookup needs DOI or arXiv id"
        )
    work = openalex.by_doi(item.doi)
    if not work:
        raise ValueError(f"OpenAlex has no record for DOI {item.doi}")
    lib_index = _library_doi_index()
    out: list[RelatedWork] = []
    for ref in openalex.references(work):
        out.append(_project(ref, "backward", lib_index))
    for cit in openalex.cited_by(work)[:max_forward]:
        out.append(_project(cit, "forward", lib_index))
    return out


def rank(works: list[RelatedWork]) -> list[RelatedWork]:
    """Cheap heuristic ranking: forward citations beat backward, then citation count."""
    return sorted(
        works,
        key=lambda w: (
            0 if w.in_library else 1,
            0 if w.direction == "forward" else 1,
            -(w.cited_by_count or 0),
        ),
    )
