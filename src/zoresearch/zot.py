"""Read-only adapter for the local Zotero library + a thin import client.

We never write to ``zotero.sqlite``. Reads use SQLite in immutable mode so we
won't fight Zotero's own writes. New items go through Zotero's connector API
(the same endpoint browser extensions hit) and Better BibTeX for citekey
resolution; both require Zotero to be running.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Iterator

import httpx

from .paths import ZOTERO_DB, ZOTERO_LOCAL_API, ZOTERO_STORAGE


PAPER_TYPES = (
    "journalArticle",
    "conferencePaper",
    "preprint",
    "thesis",
    "report",
    "book",
    "bookSection",
    "manuscript",
)


@dataclass
class Item:
    key: str
    item_type: str
    title: str
    creators: list[str] = field(default_factory=list)
    year: int | None = None
    abstract: str = ""
    doi: str = ""
    url: str = ""
    publication: str = ""
    tags: list[str] = field(default_factory=list)
    collections: list[str] = field(default_factory=list)
    citekey: str = ""
    date_added: str = ""

    def short(self) -> str:
        a = self.creators[0].split()[-1] if self.creators else "Anon"
        y = self.year or "n.d."
        return f"{a} {y} — {self.title[:80]}"


def _connect() -> sqlite3.Connection:
    if not ZOTERO_DB.exists():
        raise FileNotFoundError(
            f"Zotero database not found at {ZOTERO_DB}. "
            f"Set ZORESEARCH_ZOTERO_DIR if your data dir is elsewhere."
        )
    uri = f"file:{ZOTERO_DB}?mode=ro&immutable=1"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


_FIELD_QUERY = """
SELECT f.fieldName, idv.value
FROM itemData id
JOIN fieldsCombined f ON f.fieldID = id.fieldID
JOIN itemDataValues idv ON idv.valueID = id.valueID
WHERE id.itemID = ?
"""

_CREATOR_QUERY = """
SELECT c.firstName, c.lastName, ct.creatorType
FROM itemCreators ic
JOIN creators c ON c.creatorID = ic.creatorID
JOIN creatorTypes ct ON ct.creatorTypeID = ic.creatorTypeID
WHERE ic.itemID = ?
ORDER BY ic.orderIndex
"""

_TAG_QUERY = """
SELECT t.name
FROM itemTags it JOIN tags t ON t.tagID = it.tagID
WHERE it.itemID = ?
"""

_COLLECTION_QUERY = """
SELECT col.collectionName
FROM collectionItems ci JOIN collections col ON col.collectionID = ci.collectionID
WHERE ci.itemID = ?
"""

_CITEKEY_QUERY = """
SELECT itemKey, citationKey FROM betterbibtex.citationkey
"""


def _attach_bbt(conn: sqlite3.Connection) -> bool:
    bbt = ZOTERO_DB.parent / "better-bibtex" / "better-bibtex-search.sqlite"
    if not bbt.exists():
        return False
    try:
        conn.execute(f"ATTACH DATABASE 'file:{bbt}?mode=ro&immutable=1' AS bbt")
        return True
    except sqlite3.Error:
        return False


def _citekey_map() -> dict[str, str]:
    """itemKey -> citekey, via Better BibTeX. Empty if BBT not available."""
    bbt_db = ZOTERO_DB.parent / "better-bibtex.sqlite"
    if not bbt_db.exists():
        return {}
    try:
        conn = sqlite3.connect(f"file:{bbt_db}?mode=ro&immutable=1", uri=True)
        rows = conn.execute(
            "SELECT itemKey, citationKey FROM citationkey"
        ).fetchall()
        return {k: v for k, v in rows if k and v}
    except sqlite3.Error:
        return {}


def _row_to_item(conn: sqlite3.Connection, row: sqlite3.Row, citekeys: dict[str, str]) -> Item:
    item_id = row["itemID"]
    fields = {f["fieldName"]: f["value"] for f in conn.execute(_FIELD_QUERY, (item_id,))}
    creators = [
        " ".join(filter(None, [c["firstName"], c["lastName"]]))
        for c in conn.execute(_CREATOR_QUERY, (item_id,))
        if c["creatorType"] in ("author", "contributor", "editor", "inventor")
    ]
    tags = [r["name"] for r in conn.execute(_TAG_QUERY, (item_id,))]
    cols = [r["collectionName"] for r in conn.execute(_COLLECTION_QUERY, (item_id,))]
    year = None
    raw_date = fields.get("date", "")
    for token in raw_date.replace("/", "-").split("-"):
        if token.isdigit() and len(token) == 4:
            year = int(token)
            break
    publication = (
        fields.get("publicationTitle")
        or fields.get("proceedingsTitle")
        or fields.get("bookTitle")
        or fields.get("repository")
        or ""
    )
    return Item(
        key=row["key"],
        item_type=row["typeName"],
        title=fields.get("title", "").strip(),
        creators=creators,
        year=year,
        abstract=fields.get("abstractNote", "").strip(),
        doi=fields.get("DOI", "").strip(),
        url=fields.get("url", "").strip(),
        publication=publication.strip(),
        tags=tags,
        collections=cols,
        citekey=citekeys.get(row["key"], ""),
        date_added=row["dateAdded"],
    )


def iter_items(
    *,
    types: Iterable[str] = PAPER_TYPES,
    collection: str | None = None,
    limit: int | None = None,
) -> Iterator[Item]:
    conn = _connect()
    citekeys = _citekey_map()
    type_placeholders = ",".join("?" * len(tuple(types)))
    base = f"""
        SELECT items.itemID, items.key, items.dateAdded, it.typeName
        FROM items
        JOIN itemTypes it ON it.itemTypeID = items.itemTypeID
        WHERE items.itemID NOT IN (SELECT itemID FROM deletedItems)
          AND it.typeName IN ({type_placeholders})
    """
    params: list = list(types)
    if collection:
        base += """
          AND items.itemID IN (
            SELECT ci.itemID FROM collectionItems ci
            JOIN collections c ON c.collectionID = ci.collectionID
            WHERE c.collectionName = ?
          )
        """
        params.append(collection)
    base += " ORDER BY items.dateAdded DESC"
    if limit:
        base += f" LIMIT {int(limit)}"
    for row in conn.execute(base, params):
        yield _row_to_item(conn, row, citekeys)


def get_item(key_or_citekey: str) -> Item | None:
    conn = _connect()
    citekeys = _citekey_map()
    inverse = {v: k for k, v in citekeys.items()}
    item_key = inverse.get(key_or_citekey, key_or_citekey)
    row = conn.execute(
        """
        SELECT items.itemID, items.key, items.dateAdded, it.typeName
        FROM items
        JOIN itemTypes it ON it.itemTypeID = items.itemTypeID
        WHERE items.key = ?
          AND items.itemID NOT IN (SELECT itemID FROM deletedItems)
        """,
        (item_key,),
    ).fetchone()
    if not row:
        return None
    return _row_to_item(conn, row, citekeys)


def search(query: str, *, limit: int = 50) -> list[Item]:
    """Naive case-insensitive substring search across title/abstract/tags."""
    q = f"%{query.lower()}%"
    conn = _connect()
    citekeys = _citekey_map()
    rows = conn.execute(
        f"""
        SELECT DISTINCT items.itemID, items.key, items.dateAdded, it.typeName
        FROM items
        JOIN itemTypes it ON it.itemTypeID = items.itemTypeID
        LEFT JOIN itemData idTitle ON idTitle.itemID = items.itemID AND idTitle.fieldID = (
            SELECT fieldID FROM fieldsCombined WHERE fieldName='title')
        LEFT JOIN itemDataValues vTitle ON vTitle.valueID = idTitle.valueID
        LEFT JOIN itemData idAbs ON idAbs.itemID = items.itemID AND idAbs.fieldID = (
            SELECT fieldID FROM fieldsCombined WHERE fieldName='abstractNote')
        LEFT JOIN itemDataValues vAbs ON vAbs.valueID = idAbs.valueID
        LEFT JOIN itemTags itg ON itg.itemID = items.itemID
        LEFT JOIN tags ON tags.tagID = itg.tagID
        WHERE items.itemID NOT IN (SELECT itemID FROM deletedItems)
          AND it.typeName IN ({','.join('?' * len(PAPER_TYPES))})
          AND (LOWER(vTitle.value) LIKE ?
               OR LOWER(vAbs.value) LIKE ?
               OR LOWER(tags.name) LIKE ?)
        ORDER BY items.dateAdded DESC
        LIMIT ?
        """,
        (*PAPER_TYPES, q, q, q, limit),
    ).fetchall()
    return [_row_to_item(conn, r, citekeys) for r in rows]


def attachments(item_key: str) -> list[Path]:
    """Return existing local PDF/EPUB attachment paths for an item."""
    conn = _connect()
    rows = conn.execute(
        """
        SELECT child.key, ia.path, ia.contentType
        FROM items child
        JOIN itemAttachments ia ON ia.itemID = child.itemID
        JOIN items parent ON parent.itemID = ia.parentItemID
        WHERE parent.key = ?
          AND child.itemID NOT IN (SELECT itemID FROM deletedItems)
        """,
        (item_key,),
    ).fetchall()
    paths: list[Path] = []
    for r in rows:
        path_field = r["path"] or ""
        if path_field.startswith("storage:"):
            fname = path_field[len("storage:") :]
            p = ZOTERO_STORAGE / r["key"] / fname
            if p.exists():
                paths.append(p)
        elif path_field:
            p = Path(path_field)
            if p.exists():
                paths.append(p)
    return paths


def annotations(item_key: str) -> list[dict]:
    """Return user-made annotations on an item's PDF attachments.

    Each entry: {type, text, comment, page, color, sortIndex}.
    """
    conn = _connect()
    rows = conn.execute(
        """
        SELECT ann.type, ann.text, ann.comment, ann.pageLabel, ann.color, ann.sortIndex
        FROM itemAnnotations ann
        JOIN items annItem ON annItem.itemID = ann.itemID
        JOIN items parent ON parent.itemID = (
            SELECT parentItemID FROM itemAttachments WHERE itemID = ann.parentItemID
        )
        WHERE parent.key = ?
          AND annItem.itemID NOT IN (SELECT itemID FROM deletedItems)
        ORDER BY ann.sortIndex
        """,
        (item_key,),
    ).fetchall()
    return [
        {
            "type": r["type"],
            "text": (r["text"] or "").strip(),
            "comment": (r["comment"] or "").strip(),
            "page": r["pageLabel"] or "",
            "color": r["color"] or "",
            "sortIndex": r["sortIndex"] or "",
        }
        for r in rows
    ]


def collections() -> list[tuple[str, int]]:
    conn = _connect()
    rows = conn.execute(
        """
        SELECT c.collectionName, COUNT(ci.itemID) AS n
        FROM collections c
        LEFT JOIN collectionItems ci ON ci.collectionID = c.collectionID
        WHERE c.collectionID NOT IN (SELECT collectionID FROM deletedCollections)
        GROUP BY c.collectionID
        ORDER BY c.collectionName
        """
    ).fetchall()
    return [(r["collectionName"], r["n"]) for r in rows]


def stats() -> dict:
    conn = _connect()
    by_type = dict(
        conn.execute(
            f"""
            SELECT it.typeName, COUNT(*) AS n
            FROM items
            JOIN itemTypes it ON it.itemTypeID = items.itemTypeID
            WHERE items.itemID NOT IN (SELECT itemID FROM deletedItems)
              AND it.typeName IN ({','.join('?' * len(PAPER_TYPES))})
            GROUP BY it.typeName
            ORDER BY n DESC
            """,
            PAPER_TYPES,
        ).fetchall()
    )
    n_attachments = conn.execute(
        """
        SELECT COUNT(*) FROM itemAttachments ia
        JOIN items i ON i.itemID = ia.itemID
        WHERE ia.contentType = 'application/pdf'
          AND i.itemID NOT IN (SELECT itemID FROM deletedItems)
        """
    ).fetchone()[0]
    n_annotations = conn.execute(
        "SELECT COUNT(*) FROM itemAnnotations"
    ).fetchone()[0]
    n_collections = conn.execute(
        """
        SELECT COUNT(*) FROM collections
        WHERE collectionID NOT IN (SELECT collectionID FROM deletedCollections)
        """
    ).fetchone()[0]
    return {
        "by_type": by_type,
        "pdf_attachments": n_attachments,
        "annotations": n_annotations,
        "collections": n_collections,
    }


# ----- write path: connector + BBT JSON-RPC ---------------------------------


def zotero_running() -> bool:
    try:
        with httpx.Client(timeout=2) as c:
            r = c.get(f"{ZOTERO_LOCAL_API}/connector/ping")
            return r.status_code in (200, 404)  # 404 if endpoint name shifts
    except httpx.HTTPError:
        return False


def bbt_rpc(method: str, params: list | None = None) -> object:
    payload = {"jsonrpc": "2.0", "method": method, "params": params or [], "id": 1}
    with httpx.Client(timeout=10) as c:
        r = c.post(
            f"{ZOTERO_LOCAL_API}/better-bibtex/json-rpc",
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        r.raise_for_status()
        data = r.json()
        if "error" in data:
            raise RuntimeError(f"BBT RPC error: {data['error']}")
        return data.get("result")


def connector_save(items: list[dict], session_id: str = "zoresearch") -> dict:
    """Submit Zotero-translator-shaped items via the connector endpoint.

    The connector accepts the same payload Zotero browser extensions send.
    Items are added to the user's library; the response includes the new keys.
    """
    payload = {"sessionID": session_id, "items": items, "uri": "", "cookie": ""}
    with httpx.Client(timeout=60) as c:
        r = c.post(
            f"{ZOTERO_LOCAL_API}/connector/saveItems",
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        r.raise_for_status()
        try:
            return r.json()
        except json.JSONDecodeError:
            return {"raw": r.text}


def connector_translate(url: str, session_id: str = "zoresearch") -> dict:
    """Ask Zotero to translate a URL (DOI page, arXiv abs, journal page) and save.

    This is the most reliable way to add a paper: Zotero's translators handle
    metadata + PDF attachment in one shot, exactly like clicking the browser
    button.
    """
    with httpx.Client(timeout=60) as c:
        r = c.post(
            f"{ZOTERO_LOCAL_API}/connector/savePage",
            json={"sessionID": session_id, "uri": url},
            headers={"Content-Type": "application/json"},
        )
        r.raise_for_status()
        try:
            return r.json()
        except json.JSONDecodeError:
            return {"raw": r.text}
