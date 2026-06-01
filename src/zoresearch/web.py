"""Web reader for workspace markdown.

Light Starlette app that renders `.md` files in any workspace with:
- GFM-flavored Markdown (markdown-it-py)
- KaTeX math (client-side, CDN)
- Auto-linking of inline citations like ``[AMS, 2025, 2508.10259]`` ->
  ``zotero://`` if the arXiv ID is found in the local Zotero library,
  else ``https://arxiv.org/abs/...``
- Pygments code highlighting
- Sidebar: workspace tree

Launched via ``zr web`` — Sheikah Slate map mode for the Stable.
"""
from __future__ import annotations

import html
import re
from functools import lru_cache
from pathlib import Path
from typing import Iterable

from . import zot, workspace
from .paths import WORKSPACE


# --- citation matching ---------------------------------------------------
# Forms we tolerate:
#   [AMS, 2025, 2508.10259]
#   [LeRobot, ICLR 2026, 2602.22818]
#   [Pezzato et al., T-RO 2022, 2011.09756]
#   [Colledanchise, Almeida, Ögren, ICRA 2019, 1611.00230]
# The "name" can contain spaces, commas, dots, hyphens, Unicode letters.
# What's load-bearing is the trailing ``, NNNN.NNNNN(vN)?]`` arXiv id.
CITE_RE = re.compile(
    r"\[([^\[\]]{1,160}?),\s*(\d{4}\.\d{4,6})(v\d+)?\]"
)


@lru_cache(maxsize=1)
def _arxiv_index() -> dict[str, dict]:
    """Build arxiv-id -> {key, citekey, title, ...} from local Zotero.

    Cheap on first call (~800 items), cached forever (process lifetime).
    arXiv IDs are scraped from item URL ('arxiv.org/abs/X.X') and extras.
    """
    idx: dict[str, dict] = {}
    arxiv_url = re.compile(r"arxiv\.org/(?:abs|pdf|html)/(\d{4}\.\d{4,6})")
    arxiv_id = re.compile(r"\barXiv[:\s]*(\d{4}\.\d{4,6})", re.IGNORECASE)
    for item in zot.iter_items():
        hits: set[str] = set()
        for blob in (item.url, item.abstract, item.publication):
            if not blob:
                continue
            for m in arxiv_url.finditer(blob):
                hits.add(m.group(1))
            for m in arxiv_id.finditer(blob):
                hits.add(m.group(1))
        for h in hits:
            idx[h] = {
                "key": item.key,
                "citekey": item.citekey or "",
                "title": item.title,
                "creators": item.creators,
                "year": item.year,
                "publication": item.publication,
            }
    return idx


def _reset_arxiv_index() -> None:
    _arxiv_index.cache_clear()


def _cite_link(match: re.Match) -> str:
    label = match.group(0)
    label_safe = html.escape(label)
    arxiv = match.group(2)
    idx = _arxiv_index()
    entry = idx.get(arxiv)
    if entry:
        href = f"zotero://select/library/items/{entry['key']}"
        title_bits = [entry["title"]]
        if entry["creators"]:
            title_bits.append("; ".join(entry["creators"][:3]))
        if entry["year"]:
            title_bits.append(str(entry["year"]))
        title = " · ".join(t for t in title_bits if t)
        return (
            f'<a class="cite hit" href="{href}" title="{html.escape(title)}"'
            f' data-arxiv="{arxiv}">{label_safe}</a>'
        )
    href = f"https://arxiv.org/abs/{arxiv}"
    return (
        f'<a class="cite miss" href="{href}" target="_blank" rel="noopener"'
        f' title="not in Zotero — open arXiv" data-arxiv="{arxiv}">{label_safe}</a>'
    )


# --- markdown rendering --------------------------------------------------

def _make_md():
    from markdown_it import MarkdownIt
    md = (
        MarkdownIt("commonmark", {"html": True, "linkify": True, "typographer": True})
        .enable("table")
        .enable("strikethrough")
    )
    try:
        from mdit_py_plugins.tasklists import tasklists_plugin
        md.use(tasklists_plugin)
    except ImportError:
        pass
    try:
        from mdit_py_plugins.footnote import footnote_plugin
        md.use(footnote_plugin)
    except ImportError:
        pass
    return md


_MD = None
def render_md(text: str) -> str:
    global _MD
    if _MD is None:
        _MD = _make_md()
    html_body = _MD.render(text)
    # Link inline citations AFTER HTML render so we operate on tag-aware text.
    # Skip inside <code> / <pre> / <a> by splitting on those blocks.
    html_body = _link_citations_outside_code(html_body)
    html_body = _replace_emoji(html_body)
    return html_body


_CODE_BLOCK_RE = re.compile(r"(<pre[\s\S]*?</pre>|<code[\s\S]*?</code>|<a [\s\S]*?</a>)")


def _link_citations_outside_code(html_body: str) -> str:
    parts = _CODE_BLOCK_RE.split(html_body)
    out = []
    for i, p in enumerate(parts):
        if i % 2 == 1:
            out.append(p)
        else:
            out.append(CITE_RE.sub(_cite_link, p))
    return "".join(out)


# --- emoji → typographic symbol substitution -----------------------------
# Replace high-frequency emoji (which render as garish color glyphs via
# system fonts) with monochrome Unicode symbols styled by .sym CSS classes.
# Order matters: longer / variation-selector sequences first.
EMOJI_SUBS: list[tuple[str, str]] = [
    ("✅", '<span class="sym ok">✓</span>'),
    ("❌", '<span class="sym no">✗</span>'),
    ("⚠️", '<span class="sym warn">!</span>'),
    ("⚠", '<span class="sym warn">!</span>'),
    ("⏳", '<span class="sym pending">○</span>'),
    ("⭐", '<span class="sym star">★</span>'),
    ("🌟", '<span class="sym star">★</span>'),
    ("🎯", '<span class="sym target">◎</span>'),
    ("🚀", "→"),
    ("🎉", ""),
    ("📜", ""),
    ("📁", ""),
    ("📄", ""),
    ("📊", ""),
    ("📌", ""),
    ("🔥", '<span class="sym warn">!</span>'),
    ("💡", '<span class="sym star">★</span>'),
    ("🔧", ""),
    ("⚡️", '<span class="sym warn">!</span>'),
    ("⚡", '<span class="sym warn">!</span>'),
    ("❓", "?"),
    ("❗", "!"),
    ("ℹ️", '<span class="sym pending">i</span>'),
    ("✔️", '<span class="sym ok">✓</span>'),
    ("✔", '<span class="sym ok">✓</span>'),
    ("✖️", '<span class="sym no">✗</span>'),
    ("✖", '<span class="sym no">✗</span>'),
    ("🟢", '<span class="sym ok">●</span>'),
    ("🔴", '<span class="sym no">●</span>'),
    ("🟡", '<span class="sym warn">●</span>'),
    ("🟠", '<span class="sym warn">●</span>'),
    ("🔵", '<span class="sym pending">●</span>'),
]


def _replace_emoji(html_body: str) -> str:
    """Run after markdown render. Skips inside <code>/<pre>/<a>."""
    parts = _CODE_BLOCK_RE.split(html_body)
    out = []
    for i, p in enumerate(parts):
        if i % 2 == 1:
            out.append(p)
            continue
        for src, dst in EMOJI_SUBS:
            if src in p:
                p = p.replace(src, dst)
        out.append(p)
    return "".join(out)


# --- heading anchors + TOC -----------------------------------------------

_SLUG_NON_WORD = re.compile(r"[^\w一-鿿㐀-䶿一-鿿\-]+")
_HEADING_RE = re.compile(r"<h([2-4])>([\s\S]*?)</h\1>")


def _slugify(text: str) -> str:
    # Strip HTML tags inside heading
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"&[a-z]+;", "", text)
    text = text.strip().lower()
    text = _SLUG_NON_WORD.sub("-", text)
    return text.strip("-") or "section"


def inject_anchors_and_toc(html_body: str) -> tuple[str, str]:
    """Add id="..." to h2-h4, append clickable anchor; build TOC HTML."""
    toc_items: list[tuple[int, str, str]] = []  # (level, slug, label_text)
    seen: dict[str, int] = {}

    def repl(m: re.Match) -> str:
        level = int(m.group(1))
        inner = m.group(2)
        label = re.sub(r"<[^>]+>", "", inner).strip()
        if not label:
            return m.group(0)
        slug = _slugify(label)
        if slug in seen:
            seen[slug] += 1
            slug = f"{slug}-{seen[slug]}"
        else:
            seen[slug] = 1
        toc_items.append((level, slug, label))
        return f'<h{level} id="{slug}">{inner}<a class="anchor" href="#{slug}" aria-hidden="true">¶</a></h{level}>'

    html_with = _HEADING_RE.sub(repl, html_body)

    if not toc_items:
        return html_with, ""
    # Build TOC HTML
    lis = []
    for level, slug, label in toc_items:
        cls = {2: "h2", 3: "h3", 4: "h4"}[level]
        lis.append(f'<li class="{cls}"><a href="#{slug}">{html.escape(label)}</a></li>')
    toc_html = (
        '<nav class="toc"><div class="toctitle">On this page</div>'
        f'<ul>{"".join(lis)}</ul></nav>'
    )
    return html_with, toc_html


# --- frontmatter + slides ------------------------------------------------

_FM_RE = re.compile(r"\A---[ \t]*\n(.*?)\n---[ \t]*\n", re.DOTALL)
_SLIDE_SPLIT_RE = re.compile(r"\n-{3,}[ \t]*\n")


def split_frontmatter(text: str) -> tuple[dict, str]:
    """Pull a leading ``---\\n...\\n---`` block. Returns (meta, body).

    Only fires when the file *starts* with ``---`` so ordinary docs (and their
    inline ``---`` rules) are untouched. Parsing is a deliberately tiny
    ``key: value`` reader — no YAML dependency; values are scalar strings.
    """
    m = _FM_RE.match(text)
    if not m:
        return {}, text
    meta: dict[str, str] = {}
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        k, _, v = line.partition(":")
        meta[k.strip().lower()] = v.strip().strip("'\"")
    return meta, text[m.end():]


def is_slides(meta: dict) -> bool:
    """True when frontmatter asks for slide rendering.

    Accepts ``format: slides|deck|presentation|pdf`` or ``slides: true``.
    ``pdf`` is allowed because the slide view *is* the print-to-PDF source.
    """
    fmt = (meta.get("format") or meta.get("type") or meta.get("mode") or "").lower()
    if fmt in ("slides", "slide", "deck", "presentation", "pdf"):
        return True
    return meta.get("slides", "").lower() in ("true", "1", "yes", "on")


# --- page chrome ---------------------------------------------------------

_PAGE_CSS = r"""
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,500;8..60,600;8..60,700&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;600;700&display=swap');

/* Latin Modern Sans (real LM Sans webfont, sugina-dev) via jsDelivr —
   verified HTTP 200 + permissive CORS. CJK glyphs fall through to
   PingFang SC / Noto Sans SC (these faces cover Latin only).
   NB: clean lining digits come from body `lnum` below, not from the
   font swap — LM Sans' oldstyle figures (the old `onum`) were the
   "weird digits". */
@font-face{font-family:"Latin Modern Sans";font-style:normal;font-weight:400;font-display:swap;
  src:url("https://cdn.jsdelivr.net/gh/sugina-dev/latin-modern-web@1.0.1/font/lmsans-regular-webfont.woff") format("woff")}
@font-face{font-family:"Latin Modern Sans";font-style:normal;font-weight:700;font-display:swap;
  src:url("https://cdn.jsdelivr.net/gh/sugina-dev/latin-modern-web@1.0.1/font/lmsans-bold-webfont.woff") format("woff")}
@font-face{font-family:"Latin Modern Sans";font-style:italic;font-weight:400;font-display:swap;
  src:url("https://cdn.jsdelivr.net/gh/sugina-dev/latin-modern-web@1.0.1/font/lmsans-oblique-webfont.woff") format("woff")}
@font-face{font-family:"Latin Modern Sans";font-style:italic;font-weight:700;font-display:swap;
  src:url("https://cdn.jsdelivr.net/gh/sugina-dev/latin-modern-web@1.0.1/font/lmsans-boldoblique-webfont.woff") format("woff")}

:root{
  /* 西文 Latin Modern Sans + CJK 黑体:Latin 字符落 Latin Modern Sans(系统已装
     的 lmsans otf),CJK 字符 fall through 到 PingFang SC / Noto Sans SC。
     西文 TeX 学术感 + 中文清爽。 */
  --serif:"Latin Modern Sans","Source Serif 4","Iowan Old Style",Charter,
          "PingFang SC","Noto Sans SC","Hiragino Sans GB","Microsoft YaHei",
          "WenQuanYi Micro Hei",sans-serif;
  --sans:"Inter",system-ui,-apple-system,BlinkMacSystemFont,
         "PingFang SC","Noto Sans SC","Hiragino Sans GB","Microsoft YaHei",
         sans-serif;
  --mono:"SF Mono",ui-monospace,SFMono-Regular,Menlo,"JetBrains Mono",Consolas,monospace;

  --fg:#2c2c2c;--fg-mute:#666;--fg-faint:#999;
  --bg:#fbfaf7;--card:#fff;
  --border:#e6e2da;--border-soft:#efece5;
  --accent:#b34226;--accent-soft:rgba(179,66,38,.07);
  --hit:#2c6e3a;--hit-soft:rgba(44,110,58,.08);--hit-border:rgba(44,110,58,.22);
  --miss:#a4453c;--miss-soft:rgba(164,69,60,.06);--miss-border:rgba(164,69,60,.2);
  --code-bg:#f5f2eb;--row-stripe:rgba(0,0,0,.018);
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme]){
    --fg:#d8d3c8;--fg-mute:#9b9286;--fg-faint:#6a6358;
    --bg:#1c1a17;--card:#25221d;
    --border:#3a3528;--border-soft:#2c2823;
    --accent:#e2876b;--accent-soft:rgba(226,135,107,.12);
    --hit:#80bd8b;--hit-soft:rgba(128,189,139,.1);--hit-border:rgba(128,189,139,.25);
    --miss:#d97c72;--miss-soft:rgba(217,124,114,.1);--miss-border:rgba(217,124,114,.25);
    --code-bg:#201d18;--row-stripe:rgba(255,255,255,.02);
  }
}
:root[data-theme="dark"]{
    --fg:#d8d3c8;--fg-mute:#9b9286;--fg-faint:#6a6358;
    --bg:#1c1a17;--card:#25221d;
    --border:#3a3528;--border-soft:#2c2823;
    --accent:#e2876b;--accent-soft:rgba(226,135,107,.12);
    --hit:#80bd8b;--hit-soft:rgba(128,189,139,.1);--hit-border:rgba(128,189,139,.25);
    --miss:#d97c72;--miss-soft:rgba(217,124,114,.1);--miss-border:rgba(217,124,114,.25);
    --code-bg:#201d18;--row-stripe:rgba(255,255,255,.02);
}
.theme-btn{position:fixed;bottom:16px;right:16px;z-index:50;width:34px;height:34px;
  border:1px solid var(--border-soft);border-radius:8px;background:var(--card);
  color:var(--fg-mute);font-size:16px;line-height:1;cursor:pointer;opacity:.7;
  box-shadow:0 1px 4px rgba(0,0,0,.08);transition:opacity .15s,color .15s}
.theme-btn:hover{opacity:1;color:var(--accent)}

*{box-sizing:border-box}
html,body{margin:0;padding:0;background:var(--bg);color:var(--fg);
  font-family:var(--serif);font-size:17px;line-height:1.75;
  text-rendering:optimizeLegibility;-webkit-font-smoothing:antialiased;
  font-feature-settings:"kern","liga","lnum";font-variant-numeric:lining-nums;
  font-variant-emoji:text}

/* Monochrome typographic symbols replacing high-frequency emoji.
   Each .sym.* gets a color that fits the warm-paper palette. */
.sym{font-family:var(--serif);font-style:normal;font-weight:600;
  display:inline-block;padding:0 1px;font-feature-settings:normal;
  line-height:1}
.sym.ok{color:var(--hit)}
.sym.no{color:var(--miss)}
.sym.warn{color:#b88200}
.sym.pending{color:var(--fg-faint);font-weight:500}
.sym.star{color:#b88200}
.sym.target{color:var(--accent)}
@media (prefers-color-scheme:dark){
  .sym.warn,.sym.star{color:#e0b15a}
}

.wrap{display:grid;grid-template-columns:260px minmax(0,1fr) 220px;min-height:100vh}

/* --- left sidebar --- */
nav.side{position:sticky;top:0;height:100vh;overflow-y:auto;
  padding:24px 16px 28px 22px;border-right:1px solid var(--border-soft);
  background:var(--card);font-family:var(--sans);font-size:13.5px;line-height:1.5}
nav.side .brand{display:block;font-family:var(--serif);font-size:19px;font-weight:600;
  margin:0 0 22px;color:var(--fg);letter-spacing:-.015em;
  font-style:italic;border:0;text-decoration:none}
nav.side .brand:hover{color:var(--accent)}
nav.side .ws{font-weight:600;text-transform:uppercase;font-size:11px;
  letter-spacing:.08em;color:var(--fg-faint);margin:18px 0 6px}
nav.side ul{list-style:none;padding:0;margin:0 0 10px}
nav.side ul.tree{margin:0 0 12px}
nav.side ul.tree ul.tree{padding-left:13px;border-left:1px dashed var(--border-soft);margin:1px 0 1px 6px}
nav.side li{margin:1px 0}
nav.side a{display:block;color:var(--fg-mute);text-decoration:none;
  padding:3px 8px 3px 22px;border-radius:4px;border:0;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
  font-size:13px}
nav.side a:hover{background:var(--border-soft);color:var(--fg)}
nav.side a.active{background:var(--accent-soft);color:var(--accent);font-weight:500}
/* tree: folders */
nav.side details{margin:0}
nav.side summary{cursor:pointer;list-style:none;
  padding:3px 8px 3px 4px;border-radius:4px;
  font-weight:500;font-size:13px;color:var(--fg-mute);
  display:flex;align-items:center;gap:2px}
nav.side summary::-webkit-details-marker{display:none}
nav.side summary::before{content:"▸";display:inline-block;width:12px;
  transition:transform .12s ease;color:var(--fg-faint);font-size:10px}
nav.side details[open]>summary::before{transform:rotate(90deg)}
nav.side summary:hover{background:var(--border-soft);color:var(--fg)}
nav.side li.dir{margin:1px 0}

/* --- main column --- */
main{padding:48px 64px 80px;max-width:1024px;width:100%;margin:0 auto;font-family:var(--serif)}
main>h1:first-child{margin-top:0}
h1,h2,h3,h4,h5,h6{font-family:var(--sans);font-weight:600;line-height:1.3;color:var(--fg);
  scroll-margin-top:24px}
h1{font-size:1.85em;margin:1.4em 0 .6em;letter-spacing:-.02em}
h2{font-size:1.4em;margin:2em 0 .5em;padding-bottom:.15em;border-bottom:1px solid var(--border-soft);letter-spacing:-.01em}
h3{font-size:1.16em;margin:1.6em 0 .35em}
h4{font-size:.95em;margin:1.3em 0 .3em;color:var(--fg-mute);text-transform:uppercase;letter-spacing:.04em}

p,ul,ol{margin:.8em 0}
p{hanging-punctuation:first last}

a{color:var(--accent);text-decoration:none;border-bottom:1px solid var(--accent-soft)}
a:hover{border-bottom-color:var(--accent)}

blockquote{margin:1.3em 0;padding:.7em 1.1em;background:var(--card);
  border-left:3px solid var(--accent);border-radius:0 4px 4px 0;color:var(--fg-mute)}
blockquote>:first-child{margin-top:0}
blockquote>:last-child{margin-bottom:0}

code{font-family:var(--mono);font-size:.78em;background:var(--code-bg);
  padding:1px 6px;border-radius:3px;border:1px solid var(--border-soft);
  font-feature-settings:"calt" 0,"liga" 0}
pre{background:var(--code-bg);border:1px solid var(--border-soft);border-radius:6px;
  padding:14px 16px;overflow-x:auto;font-size:.78em;line-height:1.55;margin:1.2em 0;
  font-family:var(--mono);font-feature-settings:"calt" 0,"liga" 0}
pre code{background:none;border:0;padding:0;font-size:1em;font-family:inherit}
/* highlight.js — match warm palette: terracotta accents, muted greys, no garish blues */
.hljs{background:transparent !important;color:var(--fg);padding:0 !important}
.hljs-keyword,.hljs-built_in,.hljs-meta{color:#9d3a1f;font-weight:500}
.hljs-string,.hljs-attr,.hljs-template-tag,.hljs-template-variable{color:#735d2a}
.hljs-number,.hljs-literal,.hljs-symbol{color:#4a6f3a}
.hljs-comment,.hljs-quote{color:var(--fg-faint);font-style:italic}
.hljs-title,.hljs-section,.hljs-name,.hljs-selector-tag,.hljs-selector-class{color:#5c3d8a;font-weight:500}
.hljs-tag,.hljs-attribute{color:#7a4925}
.hljs-variable,.hljs-params{color:var(--fg)}
.hljs-deletion{background:rgba(179,66,38,.08)}
.hljs-addition{background:rgba(74,111,58,.08)}
@media (prefers-color-scheme:dark){
  .hljs-keyword,.hljs-built_in,.hljs-meta{color:#e2876b}
  .hljs-string,.hljs-attr,.hljs-template-tag,.hljs-template-variable{color:#c9b06d}
  .hljs-number,.hljs-literal,.hljs-symbol{color:#8fb676}
  .hljs-title,.hljs-section,.hljs-name,.hljs-selector-tag,.hljs-selector-class{color:#b89bd9}
  .hljs-tag,.hljs-attribute{color:#d18a5e}
}

/* Images — fit within prose column, never overflow */
img{max-width:100%;height:auto;display:block;margin:1.5em auto;border-radius:4px;
  border:1px solid var(--border-soft)}
figure{margin:1.5em 0}
figure img{margin:0 auto .4em}
figcaption{font-size:.88em;color:var(--fg-mute);text-align:center;font-family:var(--sans)}

/* Tables — break out beyond prose width, more breathable */
table{width:100%;border-collapse:collapse;margin:1.4em 0;
  font-family:var(--sans);font-size:.91em;line-height:1.55}
th,td{text-align:left;padding:8px 14px;border-bottom:1px solid var(--border-soft);vertical-align:top}
th{font-weight:600;border-bottom:2px solid var(--border);background:var(--card);color:var(--fg)}
tr:nth-child(2n) td{background:var(--row-stripe)}

hr{border:0;border-top:1px solid var(--border-soft);margin:2.4em 0}

/* Citations */
a.cite{font-family:var(--mono);font-size:.78em;font-weight:500;
  text-decoration:none;padding:1px 5px;border-radius:3px;
  border:1px solid transparent;border-bottom:none;white-space:nowrap;
  vertical-align:baseline}
a.cite.hit{color:var(--hit);background:var(--hit-soft);border-color:var(--hit-border)}
a.cite.miss{color:var(--miss);background:var(--miss-soft);border-color:var(--miss-border)}
a.cite:hover{filter:brightness(1.06)}

/* --- right TOC --- */
nav.toc{position:sticky;top:0;height:100vh;overflow-y:auto;
  padding:60px 22px 28px 12px;font-family:var(--sans);font-size:12.5px;
  border-left:1px solid var(--border-soft)}
nav.toc .toctitle{font-size:10.5px;text-transform:uppercase;letter-spacing:.1em;
  color:var(--fg-faint);margin:0 0 10px;font-weight:600}
nav.toc ul{list-style:none;padding:0;margin:0}
nav.toc a{display:block;padding:3px 0;color:var(--fg-mute);
  text-decoration:none;border:0;line-height:1.45}
nav.toc a:hover{color:var(--accent)}
nav.toc li.h3{margin-left:14px;font-size:12px}
nav.toc li.h4{margin-left:28px;font-size:11.5px;color:var(--fg-faint)}

/* Meta strip / breadcrumb above content */
.meta{font-family:var(--sans);color:var(--fg-faint);font-size:12.5px;
  margin:0 0 36px;display:flex;gap:8px;align-items:baseline;flex-wrap:wrap;
  border-bottom:1px solid var(--border-soft);padding-bottom:12px}
.meta a,.meta .crumb{color:var(--fg-mute);border:0;text-decoration:none}
.meta a:hover,.meta .crumb:hover{color:var(--accent)}
.meta .sep{color:var(--fg-faint);font-family:var(--serif);font-size:14px;
  line-height:1;padding:0 2px}

.empty{color:var(--fg-mute);padding:40px 0;font-style:italic}

/* KaTeX overrides */
.katex-display{margin:1.3em 0;overflow-x:auto;overflow-y:hidden;padding:2px 0}
.katex{font-size:1.02em}

/* Heading anchors */
.anchor{visibility:hidden;opacity:0;margin-left:.4em;
  font-weight:400;color:var(--fg-faint);font-size:.8em;border:0}
h1:hover .anchor,h2:hover .anchor,h3:hover .anchor,h4:hover .anchor{visibility:visible;opacity:1}
.anchor:hover{color:var(--accent)}

/* Responsive */
@media (max-width:1280px){
  .wrap{grid-template-columns:240px minmax(0,1fr)}
  nav.toc{display:none}
  main{padding:40px 56px 80px}
}
@media (max-width:760px){
  .wrap{grid-template-columns:1fr}
  nav.side{position:relative;height:auto;max-height:240px;border-right:0;border-bottom:1px solid var(--border-soft)}
  main{padding:24px 20px 40px;font-size:16px}
  h1{font-size:1.6em}
}
"""

_KATEX_HEAD = (
    '<link rel="stylesheet" '
    'href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css">'
    '<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>'
    '<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js" '
    'onload="renderMathInElement(document.body,{'
    'delimiters:['
    '{left:\'$$\',right:\'$$\',display:true},'
    '{left:\'$\',right:\'$\',display:false},'
    '{left:\'\\\\(\',right:\'\\\\)\',display:false},'
    '{left:\'\\\\[\',right:\'\\\\]\',display:true}'
    '],throwOnError:false})"></script>'
)

# highlight.js — only the languages we actually use. We override theme colors
# in our CSS (see .hljs-* rules) so we don't load any hljs theme stylesheet.
_HLJS_HEAD = (
    '<script src="https://cdn.jsdelivr.net/npm/@highlightjs/cdn-assets@11.9.0/highlight.min.js"></script>'
    '<script src="https://cdn.jsdelivr.net/npm/@highlightjs/cdn-assets@11.9.0/languages/python.min.js"></script>'
    '<script src="https://cdn.jsdelivr.net/npm/@highlightjs/cdn-assets@11.9.0/languages/bash.min.js"></script>'
    '<script src="https://cdn.jsdelivr.net/npm/@highlightjs/cdn-assets@11.9.0/languages/json.min.js"></script>'
    '<script src="https://cdn.jsdelivr.net/npm/@highlightjs/cdn-assets@11.9.0/languages/yaml.min.js"></script>'
    '<script src="https://cdn.jsdelivr.net/npm/@highlightjs/cdn-assets@11.9.0/languages/markdown.min.js"></script>'
    '<script>document.addEventListener("DOMContentLoaded",function(){'
    'document.querySelectorAll("pre code").forEach(function(b){hljs.highlightElement(b);});});</script>'
)


def _build_ws_tree(ws_path, allowed_exts=(".md",), skip_hidden=True):
    """Walk ws_path; return nested dict {name: <dict or None>}.  None = leaf file."""
    root = {}
    for p in sorted(ws_path.rglob("*")):
        if skip_hidden and any(part.startswith(".") for part in p.relative_to(ws_path).parts):
            continue
        if p.is_file() and p.suffix.lower() not in allowed_exts:
            continue
        if p.is_dir():
            continue
        rel = p.relative_to(ws_path)
        node = root
        parts = list(rel.parts)
        for i, part in enumerate(parts):
            if i == len(parts) - 1:
                node[part] = None
            else:
                child = node.get(part)
                if child is None or not isinstance(child, dict):
                    node[part] = {}
                node = node[part]
    return root


def _render_ws_tree(node, ws_name: str, active_path: str, current_rel: str = "") -> list[str]:
    """Render nested dict as <ul class='tree'>. Auto-opens ancestors of active_path."""
    out = ['<ul class="tree">']
    # folders first (dict values), then files
    items = sorted(node.items(), key=lambda kv: (kv[1] is None, kv[0].lower()))
    for name, child in items:
        new_rel = f"{current_rel}/{name}" if current_rel else name
        if child is None:  # leaf
            url = f"/w/{ws_name}/{new_rel}"
            cls = "active" if new_rel == active_path else ""
            label = name[:-3] if name.endswith(".md") else name
            out.append(f'<li><a class="{cls}" href="{url}">{html.escape(label)}</a></li>')
        else:  # folder
            is_open = active_path == new_rel or active_path.startswith(new_rel + "/")
            open_attr = " open" if is_open else ""
            out.append(f'<li class="dir"><details{open_attr}><summary>{html.escape(name)}</summary>')
            out.extend(_render_ws_tree(child, ws_name, active_path, new_rel))
            out.append('</details></li>')
    out.append('</ul>')
    return out


def _sidebar(active_ws: str = "", active_path: str = "") -> str:
    parts = ['<nav class="side">', '<a class="brand" href="/" style="text-decoration:none">zoresearch</a>']
    workspaces = workspace.list_workspaces()
    if not workspaces:
        parts.append('<div class="empty">No workspaces yet. Use <code>zr ws init &lt;name&gt;</code>.</div>')
    for ws in workspaces:
        ws_path = WORKSPACE / ws
        is_active = (ws == active_ws)
        ws_label_class = "ws active" if is_active else "ws"
        parts.append(f'<div class="{ws_label_class}"><a href="/w/{ws}/" style="color:inherit;text-decoration:none">{html.escape(ws)}</a></div>')
        tree = _build_ws_tree(ws_path, allowed_exts=(".md", ".pdf"))
        if tree:
            parts.extend(_render_ws_tree(tree, ws, active_path if is_active else ""))
    parts.append("</nav>")
    return "".join(parts)


_THEME_HEAD = (
    "<script>(function(){try{var t=localStorage.getItem('zr-theme');"
    "if(t==='dark'||t==='light')document.documentElement.dataset.theme=t;}catch(e){}})();"
    "function zrToggleTheme(){var d=document.documentElement,c=d.dataset.theme;"
    "if(!c)c=matchMedia('(prefers-color-scheme:dark)').matches?'dark':'light';"
    "var n=c==='dark'?'light':'dark';d.dataset.theme=n;"
    "try{localStorage.setItem('zr-theme',n);}catch(e){}}</script>"
)


def _page(title: str, body: str, sidebar_html: str, toc_html: str = "") -> str:
    return (
        "<!doctype html><html lang=\"zh-CN\"><head>"
        f"<meta charset=\"utf-8\"><title>{html.escape(title)} — zoresearch</title>"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        f"<style>{_PAGE_CSS}</style>"
        f"{_KATEX_HEAD}"
        f"{_HLJS_HEAD}"
        f"{_THEME_HEAD}"
        "</head><body>"
        "<button class=\"theme-btn\" onclick=\"zrToggleTheme()\" title=\"切换主题\" aria-label=\"theme\">◐</button>"
        f"<div class=\"wrap\">{sidebar_html}<main>{body}</main>{toc_html}</div>"
        "</body></html>"
    )


# --- slides view ---------------------------------------------------------

_SLIDES_CSS = r"""
html{background:#000}
body{overflow:hidden;background:#000}
.deck{position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);
  width:min(100vw,calc(100vh*16/9));height:min(100vh,calc(100vw*9/16));
  background:var(--bg);overflow:hidden}
.slide{position:absolute;inset:0;container-type:size;display:flex;flex-direction:column;
  align-items:stretch;justify-content:flex-start;gap:.06em;
  padding:7cqh 7cqw 6cqh;overflow:hidden;text-align:left;
  opacity:0;pointer-events:none;transition:opacity .18s ease;
  font-size:clamp(25px,3.7cqh,44px);line-height:1.5}
.slide.active{opacity:1;pointer-events:auto}
.slide>*{margin:0;max-width:100%}
.slide>:first-child{margin-top:0}.slide>:last-child{margin-bottom:0}
.slide h1{font-size:2.0em;margin:.05em 0 .4em;letter-spacing:-.02em;line-height:1.15;
  border:0;padding:0;font-family:var(--sans)}
.slide h2{font-size:1.5em;border:0;padding:0;margin:.05em 0 .45em;line-height:1.2;font-family:var(--sans)}
.slide h3{font-size:1.12em;margin:.3em 0 .2em;color:var(--fg-mute);font-family:var(--sans)}
.slide p{margin:.34em 0}
.slide ul,.slide ol{margin:.34em 0;padding-left:1.25em}
.slide li{margin:.32em 0}
/* nested (sub)list items render a touch smaller; ol numbers scale with the li */
.slide li li{font-size:.9em}
/* title pinned at top, remaining body vertically centered in the leftover space */
.slide>.slide-head{flex:0 0 auto}
.slide>.slide-body{flex:1 1 auto;min-height:0;display:flex;flex-direction:column;
  justify-content:center;overflow:hidden}
.slide>.slide-body>*{margin:.34em 0;max-width:100%}
.slide>.slide-body>:first-child{margin-top:0}.slide>.slide-body>:last-child{margin-bottom:0}
.slide blockquote{margin:.45em 0;font-size:.92em}
/* only media is centered; text stays left */
.slide img{display:block;max-height:50cqh;max-width:100%;width:auto;margin:.4em auto}
.slide figure{margin:.3em auto;text-align:center}.slide figure img{max-height:46cqh;margin:.2em auto}
.slide figcaption{font-size:.6em;text-align:center}
.slide video{display:block;max-height:48cqh;max-width:100%;width:auto;margin:.3em auto}
.slide table{font-size:.74em;margin:.45em auto;width:auto;max-width:100%}
.slide pre{font-size:.56em;margin:.4em 0;max-width:100%;overflow:auto}
.slide .katex{font-size:1.02em}.slide .katex-display{margin:.4em 0}
/* two-column slides: author separates columns with a line of  :::
   a leading heading stays full-width on top; columns fill the rest */
.slide .cols-row{display:flex;flex-direction:row;align-items:center;justify-content:center;
  gap:4.5cqw;width:100%;flex:1 1 auto;min-height:0;margin-top:.25em}
.slide .col{flex:1 1 0;min-width:0;display:flex;flex-direction:column;justify-content:center}
.slide .col>*{margin:.32em 0;max-width:100%}.slide .col>:first-child{margin-top:0}.slide .col>:last-child{margin-bottom:0}
.slide .col img,.slide .col figure img,.slide .col video{max-height:72cqh;margin:.2em auto}
/* cover / title slides (any slide led by an h1): centered both ways, bigger */
.slide.cover{align-items:center;justify-content:center;text-align:center}
.slide.cover h1{font-size:2.7em;line-height:1.12;margin:.1em 0 .25em}
.slide.cover h3{font-size:1.3em;font-weight:400;color:var(--fg-mute);margin:.1em 0 .5em;font-family:var(--sans)}
.slide.cover p{color:var(--fg-mute);font-size:.95em;margin:.2em 0}
.deck-bar{position:absolute;left:0;bottom:0;height:3px;width:0;background:var(--accent);
  transition:width .2s ease;z-index:10}
.deck-num{position:absolute;right:18px;bottom:13px;font-family:var(--sans);
  font-size:13px;color:var(--fg-faint);z-index:10;font-variant-numeric:lining-nums}
.deck-hint{position:absolute;left:18px;bottom:13px;font-family:var(--sans);
  font-size:11.5px;color:var(--fg-faint);opacity:.6;z-index:10}
.deck-nav{position:absolute;top:0;bottom:0;width:14%;z-index:9;cursor:pointer;
  border:0;background:transparent;padding:0;outline:none}
.deck-nav.prev{left:0;cursor:w-resize}.deck-nav.next{right:0;cursor:e-resize}
.deck-exit{position:absolute;top:11px;left:14px;z-index:11;width:30px;height:30px;
  border:0;border-radius:6px;background:transparent;color:var(--fg-faint);
  font-size:17px;line-height:1;cursor:pointer;opacity:.4;transition:opacity .15s,color .15s}
.deck-exit:hover{opacity:1;color:var(--accent)}
.deck-theme{position:absolute;top:11px;left:50px;z-index:11;width:30px;height:30px;
  border:0;border-radius:6px;background:transparent;color:var(--fg-faint);
  font-size:15px;line-height:1;cursor:pointer;opacity:.4;transition:opacity .15s,color .15s}
.deck-theme:hover{opacity:1;color:var(--accent)}
.deck-logo{position:absolute;top:22px;right:30px;height:10vh;max-height:88px;width:auto;
  z-index:10;opacity:.95;pointer-events:none;user-select:none;
  border:0;border-radius:0;margin:0;background:none;box-shadow:none}
@media print{
  @page{size:1280px 720px;margin:0}
  html,body{overflow:visible;background:#fff}
  .deck{position:static;width:auto;height:auto;transform:none;background:transparent;overflow:visible}
  .slide{position:relative;inset:auto;opacity:1 !important;pointer-events:auto;
    height:720px;width:1280px;page-break-after:always;break-after:page}
  .deck-bar,.deck-num,.deck-hint,.deck-nav,.deck-exit,.deck-theme{display:none}
  .deck-logo{position:absolute;top:18px;right:24px;opacity:1}
}
"""

_SLIDES_JS = r"""
(function(){
  var S=[].slice.call(document.querySelectorAll('.slide')),n=S.length,i=0;
  function show(k){
    i=Math.max(0,Math.min(n-1,k));
    for(var j=0;j<n;j++)S[j].classList.toggle('active',j===i);
    var num=document.querySelector('.deck-num');if(num)num.textContent=(i+1)+' / '+n;
    var bar=document.querySelector('.deck-bar');if(bar)bar.style.width=((i+1)/n*100)+'%';
    try{history.replaceState(null,'','#s'+(i+1));}catch(e){}
  }
  function next(){show(i+1);}function prev(){show(i-1);}
  function exitDeck(){
    if(document.fullscreenElement){document.exitFullscreen();return;}
    var p=location.pathname.replace(/[^\/]*$/,'');location.assign(p||'/');
  }
  document.addEventListener('keydown',function(e){
    if(e.key==='ArrowRight'||e.key==='ArrowDown'||e.key==='PageDown'||e.key===' '){e.preventDefault();next();}
    else if(e.key==='ArrowLeft'||e.key==='ArrowUp'||e.key==='PageUp'){e.preventDefault();prev();}
    else if(e.key==='Home'){e.preventDefault();show(0);}
    else if(e.key==='End'){e.preventDefault();show(n-1);}
    else if(e.key==='f'||e.key==='F'){if(!document.fullscreenElement){document.documentElement.requestFullscreen();}else{document.exitFullscreen();}}
    else if(e.key==='Escape'){e.preventDefault();exitDeck();}
  });
  var pv=document.querySelector('.deck-nav.prev'),nx=document.querySelector('.deck-nav.next');
  if(pv)pv.addEventListener('click',prev);if(nx)nx.addEventListener('click',next);
  var ex=document.querySelector('.deck-exit');if(ex)ex.addEventListener('click',function(e){e.stopPropagation();exitDeck();});
  var m=(location.hash.match(/^#s(\d+)/));show(m?parseInt(m[1],10)-1:0);
})();
"""


def _slides_page(title: str, deck_html: str, logo_src: str = "") -> str:
    logo = f'<img class="deck-logo" src="{html.escape(logo_src)}" alt="">' if logo_src else ""
    return (
        "<!doctype html><html lang=\"zh-CN\"><head>"
        f"<meta charset=\"utf-8\"><title>{html.escape(title)} — slides</title>"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        f"<style>{_PAGE_CSS}{_SLIDES_CSS}</style>{_KATEX_HEAD}{_HLJS_HEAD}{_THEME_HEAD}"
        "</head><body>"
        f"<div class=\"deck\">{deck_html}"
        f"{logo}"
        "<button class=\"deck-nav prev\" aria-label=\"previous slide\"></button>"
        "<button class=\"deck-nav next\" aria-label=\"next slide\"></button>"
        "<button class=\"deck-exit\" title=\"退出（Esc）\" aria-label=\"exit\">✕</button>"
        "<button class=\"deck-theme\" onclick=\"zrToggleTheme()\" title=\"切换主题\" aria-label=\"theme\">◐</button>"
        "<div class=\"deck-bar\"></div><div class=\"deck-num\"></div>"
        "<div class=\"deck-hint\">← → / Space 翻页 · F 全屏 · Esc 退出 · ⌘P 导出 PDF</div>"
        "</div>"
        f"<script>{_SLIDES_JS}</script>"
        "</body></html>"
    )


_COL_SPLIT_RE = re.compile(r"\n:{3,}[ \t]*\n")


def _logo_src(meta: dict, md_dir) -> str:
    """Resolve a slide logo to an inlinable ``src``.

    Order: frontmatter ``logo:`` (a URL, or a local path — absolute, ``~``, or
    relative to the deck), else a local default at
    ``~/.config/zoresearch/logo.{png,svg,jpg,jpeg,webp}``. Local files are
    embedded as data URIs so the image never has to live in the repo.
    """
    import base64
    import mimetypes
    val = (meta.get("logo") or "").strip()
    if val.startswith(("http://", "https://", "data:")):
        return val
    if val:
        p = Path(val).expanduser()
        candidates = [p if p.is_absolute() else Path(md_dir) / p]
    else:
        cfg = Path.home() / ".config" / "zoresearch"
        candidates = [cfg / f"logo.{ext}" for ext in ("png", "svg", "jpg", "jpeg", "webp")]
    for p in candidates:
        try:
            data = p.expanduser().resolve().read_bytes()
        except OSError:
            continue
        mime = mimetypes.guess_type(str(p))[0] or "image/png"
        return f"data:{mime};base64," + base64.b64encode(data).decode("ascii")
    return ""


def render_slides(meta: dict, body_md: str, fallback_title: str, logo_src: str = "") -> str:
    """Split body on ``---`` into slides; within a slide, ``:::`` splits columns.

    Each slide / column goes through the normal markdown pipeline, so figures,
    tables, math and code work everywhere. A ``:::`` line lets the author put
    text on the left and a figure on the right (a flex row) to avoid overflow.
    """
    chunks = [c.strip() for c in _SLIDE_SPLIT_RE.split(body_md) if c.strip()]
    if not chunks:
        chunks = [body_md.strip() or "*(empty deck)*"]
    sections = []
    for c in chunks:
        if _COL_SPLIT_RE.search(c):
            header_html, rest = "", c
            mh = re.match(r"(#{1,6}[ \t][^\n]*)\n+", c)   # leading heading -> full width
            if mh:
                header_html = render_md(mh.group(1))
                rest = c[mh.end():]
            cols = [col.strip() for col in _COL_SPLIT_RE.split(rest) if col.strip()]
            if len(cols) >= 2:
                body = "".join(f'<div class="col">{render_md(col)}</div>' for col in cols)
                sections.append(f'<section class="slide colslide">{header_html}'
                                f'<div class="cols-row">{body}</div></section>')
                continue
        sec = render_md(c)
        if "<h1" in sec:                       # cover/title slide: centered both ways
            sections.append(f'<section class="slide cover">{sec}</section>')
            continue
        # normal slide: leading heading pinned at top, the rest vertically centered
        mh = re.match(r"(#{1,6}[ \t][^\n]*)\n+", c)
        if mh:
            head = render_md(mh.group(1)); body = render_md(c[mh.end():])
            sections.append(f'<section class="slide"><div class="slide-head">{head}</div>'
                            f'<div class="slide-body">{body}</div></section>')
        else:
            sections.append(f'<section class="slide"><div class="slide-body">{sec}</div></section>')
    return _slides_page(meta.get("title") or fallback_title, "".join(sections), logo_src)


# --- routes --------------------------------------------------------------

def _route_index(request):
    from starlette.responses import HTMLResponse
    body = ["<h1>zoresearch — workspace reader</h1>",
            "<p class=\"meta\">Pick a Stable from the sidebar, or start with one of these:</p>"]
    workspaces = workspace.list_workspaces()
    if not workspaces:
        body.append('<p class="empty">No workspaces yet.</p>')
    else:
        body.append("<ul>")
        for ws in workspaces:
            body.append(f'<li><a href="/w/{ws}/">{html.escape(ws)}</a></li>')
        body.append("</ul>")
    body.append(f'<p class="meta">Citation index: {len(_arxiv_index())} arXiv IDs mapped from Zotero.</p>')
    return HTMLResponse(_page("home", "".join(body), _sidebar()))


def _route_workspace(request):
    from starlette.responses import HTMLResponse, RedirectResponse
    name = request.path_params["ws"]
    ws_path = WORKSPACE / name
    if not ws_path.is_dir():
        return HTMLResponse(_page("not found", f"<h1>workspace not found: {html.escape(name)}</h1>", _sidebar()), status_code=404)
    # If there's a research-proposal-draft.md, jump straight to it.
    for prefer in ("research-proposal-draft.md", "question.md", "notes.md"):
        if (ws_path / prefer).exists():
            return RedirectResponse(f"/w/{name}/{prefer}", status_code=302)
    # Otherwise show file list
    md_files = sorted(ws_path.rglob("*.md"))
    items = [f'<li><a href="/w/{name}/{p.relative_to(ws_path).as_posix()}">{html.escape(p.relative_to(ws_path).as_posix())}</a></li>' for p in md_files]
    body = f"<h1>{html.escape(name)}</h1><ul>{''.join(items)}</ul>"
    return HTMLResponse(_page(name, body, _sidebar(active_ws=name)))


def _route_file(request):
    from starlette.responses import HTMLResponse
    name = request.path_params["ws"]
    rel = request.path_params["path"]
    ws_path = WORKSPACE / name
    f = ws_path / rel
    try:
        f = f.resolve()
        ws_path = ws_path.resolve()
        f.relative_to(ws_path)
    except (ValueError, FileNotFoundError):
        return HTMLResponse(_page("403", "<h1>forbidden</h1>", _sidebar()), status_code=403)
    if not f.is_file():
        return HTMLResponse(_page("404", f"<h1>not found: {html.escape(rel)}</h1>", _sidebar(active_ws=name)), status_code=404)
    if f.suffix.lower() != ".md":
        from starlette.responses import FileResponse
        return FileResponse(f)
    text = f.read_text(encoding="utf-8")
    meta, body_md = split_frontmatter(text)
    if is_slides(meta):
        return HTMLResponse(render_slides(meta, body_md, f.stem, _logo_src(meta, f.parent)))
    body_html = render_md(body_md)
    body_with_anchors, toc_html = inject_anchors_and_toc(body_html)
    title = f.stem
    meta = (
        f'<div class="meta">'
        f'<a href="/w/{name}/" class="crumb">{html.escape(name)}</a>'
        f'<span class="sep">›</span>'
        f'<span>{html.escape(rel)}</span>'
        f'</div>'
    )
    body = meta + body_with_anchors
    return HTMLResponse(_page(title, body, _sidebar(active_ws=name, active_path=rel), toc_html))


def _route_cite(request):
    from starlette.responses import JSONResponse
    arxiv = request.path_params["arxiv"]
    entry = _arxiv_index().get(arxiv)
    if not entry:
        return JSONResponse({"found": False, "arxiv": arxiv}, status_code=404)
    return JSONResponse({"found": True, "arxiv": arxiv, **entry})


def build_app():
    from starlette.applications import Starlette
    from starlette.routing import Route
    return Starlette(
        debug=False,
        routes=[
            Route("/", _route_index),
            Route("/w/{ws}/", _route_workspace),
            Route("/w/{ws}/{path:path}", _route_file),
            Route("/api/cite/{arxiv}", _route_cite),
        ],
    )


def serve(host: str = "127.0.0.1", port: int = 8765, open_browser: bool = True) -> None:
    import uvicorn
    if open_browser:
        import threading, webbrowser, time
        def _open():
            time.sleep(0.5)
            webbrowser.open(f"http://{host}:{port}/")
        threading.Thread(target=_open, daemon=True).start()
    uvicorn.run(build_app(), host=host, port=port, log_level="warning")
