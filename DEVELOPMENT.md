# Developing zoresearch

This is the map of how the package is wired and where to add things. For the
user-facing tour see [README.md](README.md).

## Mental model

Three storage tiers, and only `zr` knows how to talk to them:

| Tier | What lives there | Mutability |
|---|---|---|
| `~/Zotero/` | items, PDFs, metadata, `zotero.sqlite` | **read-only** from this tool; new items added via the connector API |
| `data/` | parsed transcripts, OpenAlex responses, per-paper notes | rebuildable cache — safe to delete |
| `workspace/<project>/` | one directory per research question | the durable research output |

Rule of thumb: never reach into `data/` or the Zotero sqlite directly from a
skill — go through the CLI. Extend the CLI first, then let skills use it.

## Module map

`src/zoresearch/`

| Module | Responsibility |
|---|---|
| `cli.py` | the [Typer](https://typer.tiangolo.com/) app — every `zr` subcommand, plus the cosmetic aliases. Thin: parses args, calls a module, renders with `rich`. |
| `zot.py` | **read-only** access to `zotero.sqlite` (items, collections, tags, attachments) and Better BibTeX citekey resolution. The only reader of the Zotero DB. |
| `import_.py` | adds items to Zotero through the local **connector API** (the path browser extensions use). Requires Zotero to be running. |
| `parse.py` | PDF → multimodal Markdown. MinerU (`mineru`) by default, `pymupdf4llm` fallback. Output lands in `data/transcripts/<key>/`. |
| `openalex.py` | OpenAlex client — backward refs, forward citations, trends. Responses cached under `data/citations/`. |
| `related.py` | composes `openalex` + `zot` to produce related work deduped against the library. |
| `workspace.py` | create / list / inspect `workspace/<project>/` (`question.md`, `seeds.txt`, `related.md`, `notes.md`). |
| `notes.py` | append-only per-paper Memories at `data/notes/<key>.md`. |
| `web.py` | the browser reader and slide renderer (see below). Optional deps (`[web]`). |
| `config.py` | loads `~/.zoresearch/config.toml` (MinerU token, etc.), mode `600`, outside the repo. |
| `paths.py` | resolves the Zotero dir, `data/`, and `workspace/`. Single source of truth for locations. |
| `lore.py` | the Sheikah Slate flavour — banners and strings, muted by `ZORESEARCH_PLAIN=1`. |

## Data flow

```
zr lib/show/search   →  zot.py        →  read zotero.sqlite (RO)
zr parse <key>       →  parse.py      →  data/transcripts/<key>/paper.md
zr related <key>     →  related.py    →  openalex.py (→ data/citations/)  +  zot dedup
zr import <id>       →  import_.py    →  Zotero connector API  →  ~/Zotero/
zr notes <key>       →  notes.py      →  data/notes/<key>.md
zr ws *              →  workspace.py  →  workspace/<project>/*
zr web               →  web.py        →  serves workspace/ in a browser
```

## Adding a CLI command

Commands are plain Typer functions in `cli.py`. Keep them thin — argument
parsing and `rich` rendering only; put real logic in a module.

```python
@app.command()
def summary(key: str, sentences: int = typer.Option(3, "--n")):
    """One-line help shows up in `zr --help`."""
    item = zot.get(key)            # logic lives in a module
    console.print(render(item))    # rich when interactive, plain when piped
```

- Group related commands under a sub-app (`lib_app`, `ws_app`) with
  `app.add_typer(...)`.
- Add a cosmetic alias the same way the existing ones do
  (`zr sensor`, `zr shrine`, …) if it earns a Zelda name.
- Don't add a feature that isn't reachable from `zr --help`.

## The web reader (`web.py`)

A single-file [Starlette](https://www.starlette.io/) app served by `uvicorn`.

- **Routes**: `/` (index), `/w/{ws}/` (a workspace), `/w/{ws}/{path}` (a file),
  `/api/cite/{arxiv}` (citation metadata lookup).
- **Rendering**: `markdown-it-py` + plugins → HTML, with KaTeX for math and
  highlight.js for code. CSS lives in the `_PAGE_CSS` / `_SLIDES_CSS` string
  constants; light/dark themes are CSS custom properties on `:root`, overridable
  via a `data-theme` attribute persisted in `localStorage`.
- **Slides**: a document whose front-matter has `format: slides` (or
  `slides|deck|presentation|pdf`) is rendered as a deck. `---` on its own line
  splits slides; `:::` splits a slide into columns. The deck is a fixed **16:9**
  stage centred in a letterboxed viewport, so `cqh`/`cqw` container units scale
  the content to the stage rather than the screen. `@media print` lays each
  slide out as a 1280×720 page for `⌘P` → PDF.

The server has no hot-reload: editing `web.py` (which holds the CSS/JS as Python
strings) needs a restart; editing a `workspace/` Markdown file only needs a
browser refresh.

## Skills

`.claude/skills/<name>/SKILL.md` are short workflows that compose `zr` commands
(see `library`, `parse`, `related`, `trends`, `import`, `workspace`, `notes`).
They contain no logic of their own — when a capability is missing, add it to the
CLI first and have the skill call it. The load-bearing cost rule (MinerU parsing
is workspace-scoped and quota-bound) is enforced in the skills, not the CLI.

## Conventions

- Python 3.10+, source under `src/zoresearch/`.
- Comments only when the *why* is non-obvious.
- Output via `rich` when interactive, plain text when piped.
- Editable install for development: `pip install -e ".[web,mineru]"`.
