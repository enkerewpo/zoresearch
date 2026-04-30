"""PDF -> Markdown transcript pipeline.

Two engines:

1. ``mineru`` (default) — calls MinerU cloud API (mineru.net). Produces
   structured Markdown that preserves formulas, figures, and tables, plus an
   ``images/`` directory. Best for LLM consumption.
2. ``pymupdf`` — local fallback via ``pymupdf4llm``. Always available, but
   loses figure positioning and table structure.

Outputs are cached under ``data/transcripts/<key>/``. Re-running on an already
parsed item is a no-op unless ``--force`` is passed.
"""
from __future__ import annotations

import io
import json
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path

import httpx

from . import zot
from .config import CONFIG
from .paths import TRANSCRIPTS


@dataclass
class ParseResult:
    item_key: str
    engine: str
    markdown_path: Path
    image_dir: Path | None
    pages: int | None = None


def _out_dir(item_key: str) -> Path:
    d = TRANSCRIPTS / item_key
    d.mkdir(parents=True, exist_ok=True)
    return d


def _already_parsed(item_key: str) -> Path | None:
    md = _out_dir(item_key) / "paper.md"
    return md if md.exists() else None


def parse_item(item_key: str, *, engine: str | None = None, force: bool = False) -> ParseResult:
    item = zot.get_item(item_key)
    if item is None:
        raise ValueError(f"Zotero item not found: {item_key}")
    pdfs = [p for p in zot.attachments(item.key) if p.suffix.lower() == ".pdf"]
    if not pdfs:
        raise FileNotFoundError(
            f"no PDF attachment for {item.key} ({item.short()})"
        )
    pdf_path = pdfs[0]

    if not force and (existing := _already_parsed(item.key)):
        return ParseResult(
            item_key=item.key,
            engine="cache",
            markdown_path=existing,
            image_dir=existing.parent / "images" if (existing.parent / "images").exists() else None,
        )

    chosen = (engine or CONFIG.parse_engine).lower()
    if chosen == "mineru":
        if not CONFIG.mineru.token:
            print("MinerU token missing, falling back to pymupdf")
            chosen = "pymupdf"
    if chosen == "mineru":
        return _parse_mineru(item.key, pdf_path)
    return _parse_pymupdf(item.key, pdf_path)


# --- engines ----------------------------------------------------------------


def _parse_pymupdf(item_key: str, pdf_path: Path) -> ParseResult:
    import pymupdf4llm

    md = pymupdf4llm.to_markdown(str(pdf_path))
    out = _out_dir(item_key)
    md_path = out / "paper.md"
    md_path.write_text(md, encoding="utf-8")
    (out / "meta.json").write_text(
        json.dumps(
            {"engine": "pymupdf4llm", "source_pdf": str(pdf_path), "ts": int(time.time())},
            indent=2,
        ),
        encoding="utf-8",
    )
    return ParseResult(item_key=item_key, engine="pymupdf4llm", markdown_path=md_path, image_dir=None)


def _parse_mineru(item_key: str, pdf_path: Path) -> ParseResult:
    cfg = CONFIG.mineru
    headers = {"Authorization": f"Bearer {cfg.token}"}
    out = _out_dir(item_key)

    file_payload = {
        "enable_formula": cfg.enable_formula,
        "enable_table": cfg.enable_table,
        "language": cfg.language,
        "data_id": item_key,
        "name": pdf_path.name,
    }
    batch_payload = {
        "enable_formula": cfg.enable_formula,
        "enable_table": cfg.enable_table,
        "language": cfg.language,
        "files": [file_payload],
    }

    with httpx.Client(timeout=120) as client:
        r = client.post(
            f"{cfg.endpoint}/file-urls/batch",
            json=batch_payload,
            headers=headers,
        )
        r.raise_for_status()
        body = r.json()
        if body.get("code") not in (0, 200):
            raise RuntimeError(f"MinerU file-urls error: {body}")
        data = body["data"]
        batch_id = data["batch_id"]
        upload_urls = data["file_urls"]
        if not upload_urls:
            raise RuntimeError(f"MinerU returned no upload URL: {body}")
        with pdf_path.open("rb") as fp:
            up = client.put(upload_urls[0], content=fp.read())
            up.raise_for_status()

        result_url = f"{cfg.endpoint}/extract-results/batch/{batch_id}"
        for _ in range(120):  # ~10 min cap
            r = client.get(result_url, headers=headers)
            r.raise_for_status()
            payload = r.json()
            extract_results = (payload.get("data") or {}).get("extract_result") or []
            if extract_results:
                file_result = extract_results[0]
                state = (file_result.get("state") or "").lower()
                if state in ("done", "success", "succeeded"):
                    zip_url = file_result.get("full_zip_url")
                    if not zip_url:
                        raise RuntimeError(f"MinerU done but no zip url: {file_result}")
                    zr = client.get(zip_url)
                    zr.raise_for_status()
                    _extract_mineru_zip(zr.content, out)
                    pages = file_result.get("extract_progress", {}).get("total_pages")
                    (out / "meta.json").write_text(
                        json.dumps(
                            {
                                "engine": "mineru",
                                "source_pdf": str(pdf_path),
                                "batch_id": batch_id,
                                "pages": pages,
                                "ts": int(time.time()),
                            },
                            indent=2,
                        ),
                        encoding="utf-8",
                    )
                    img_dir = out / "images"
                    return ParseResult(
                        item_key=item_key,
                        engine="mineru",
                        markdown_path=out / "paper.md",
                        image_dir=img_dir if img_dir.exists() else None,
                        pages=pages,
                    )
                if state in ("failed", "error"):
                    raise RuntimeError(f"MinerU failed: {file_result}")
            time.sleep(5)
        raise TimeoutError(f"MinerU job {batch_id} did not finish in time")


def _extract_mineru_zip(blob: bytes, out_dir: Path) -> None:
    """Pull the markdown out of a MinerU result zip into ``out_dir``.

    MinerU's bundle usually contains: ``full.md`` (or ``<name>.md``), an
    ``images/`` directory, and a ``content_list.json``. We rename the markdown
    to ``paper.md`` so downstream consumers don't have to guess.
    """
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        zf.extractall(out_dir)
    candidates = (
        list(out_dir.glob("*.md"))
        + list(out_dir.glob("**/full.md"))
        + list(out_dir.glob("**/*.md"))
    )
    chosen: Path | None = None
    for c in candidates:
        if c.name.lower() in ("full.md", "paper.md"):
            chosen = c
            break
    if chosen is None and candidates:
        chosen = max(candidates, key=lambda p: p.stat().st_size)
    if chosen is None:
        raise RuntimeError("MinerU zip contained no markdown")
    target = out_dir / "paper.md"
    if chosen.resolve() != target.resolve():
        target.write_bytes(chosen.read_bytes())
    images_src = next((p for p in out_dir.rglob("images") if p.is_dir()), None)
    if images_src and images_src.resolve() != (out_dir / "images").resolve():
        for img in images_src.iterdir():
            (out_dir / "images").mkdir(exist_ok=True)
            (out_dir / "images" / img.name).write_bytes(img.read_bytes())
