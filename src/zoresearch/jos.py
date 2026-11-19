"""Journal of Software (软件学报, jos.org.cn) as an import source.

OpenAlex has no records for the journal's current DOIs (10.13328/j.cnki.jos.NNNNNN),
so metadata is read from the article page's citation meta tags and the PDF from
its citation_pdf_url. The article id is the last digits of the DOI.
"""
from __future__ import annotations

import re
from html import unescape

import httpx

_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"
_META = re.compile(r'<meta name="([^"]+)"(?: xml:lang="([a-z]+)")? content="([^"]*)"')
DOI_PREFIX = "10.13328/j.cnki.jos."


def article_id(value: str) -> str | None:
    """JOS article id from a DOI or an article URL, else None."""
    m = re.search(r"10\.13328/j\.cnki\.jos\.0*(\d+)", value) or re.search(r"jos\.org\.cn/+jos/article/(?:abstract|html|pdf)/(\d+)", value)
    return m.group(1) if m else None


def fetch(aid: str) -> tuple[dict, bytes | None]:
    """(shallow metadata as import_.py expects, PDF bytes or None) for one article."""
    with httpx.Client(timeout=60, headers={"User-Agent": _UA}, follow_redirects=True, trust_env=False) as c:
        page = c.get(f"https://www.jos.org.cn/jos/article/abstract/{aid}").text
        meta: dict[tuple[str, str | None], str] = {}
        for name, lang, content in _META.findall(page):
            meta[(name, lang or None)] = unescape(content)
        cn = lambda k: meta.get((k, "cn")) or meta.get((k, None)) or ""
        abstract = re.search(r'id="CnAbstractValue">(.*?)</p>', page, re.S)
        shallow = {
            "title": cn("citation_title"),
            "authors": [a.strip() for a in re.split(r"[，,]", cn("citation_authors")) if a.strip()],
            "year": (cn("citation_date") or "")[:4],
            "date": cn("citation_date"),
            "doi": cn("citation_doi") or DOI_PREFIX + aid.zfill(6),
            "venue": cn("citation_journal_title") or "软件学报",
            "volume": cn("citation_volume"),
            "issue": cn("citation_issue"),
            "pages": "-".join(p for p in (cn("citation_firstpage"), cn("citation_lastpage")) if p),
            "abstract": unescape(re.sub(r"<[^>]+>", "", abstract.group(1))).strip() if abstract else cn("description"),
            "keywords": [k for k in cn("DC.Keywords").split("|") if k],
            "url": f"https://www.jos.org.cn/jos/article/abstract/{aid}",
        }
        pdf = None
        if pdf_url := cn("citation_pdf_url"):
            r = c.get(pdf_url.replace("//jos/", "/jos/"))
            if r.status_code == 200 and r.content[:4] == b"%PDF":
                pdf = r.content
    return shallow, pdf
