<p align="center"><img src="assets/logo.svg" width="128" alt="zoresearch logo"/></p>

# zoresearch

> _"It's dangerous to read alone. Take this."_

A small, personal research copilot built on top of a local Zotero library. Think of it as a Sheikah Slate for your reading: the **Compendium** catalogues what you already have, the **Sensor** points at the related work you don't, **Stables** are workspaces around a research question, and **Memories** are the durable notes you accumulate paper by paper.

Zotero stays the source of truth — `zotero.sqlite` is read-only from this tool's perspective, and any new items are pushed in through Zotero's own connector API. Nothing in `~/Zotero/` gets rewritten by hand.

## What it does

The `zr` CLI is the load-bearing layer; the skills under `.claude/skills/` are thin orchestration on top, so the same workflows run by hand or driven by an agent (Claude Code).

- **Browse & search** your existing library by topic, author, year, or collection.
- **Parse PDFs** into multimodal Markdown transcripts (figures + tables preserved) that an LLM can actually reason over — MinerU as the default engine, `pymupdf4llm` as the zero-config fallback.
- **Find related work** via a citation graph (OpenAlex) for a seed paper or a whole workspace, deduplicated against your library, and **import** the missing items back into Zotero.
- **Analyse trends & gaps** for a topic, grounded in your own library plus OpenAlex.
- **Keep per-paper notes** (Memories) that survive across sessions.
- **Read in the browser** — `zr web` serves your workspaces as a clean reader with KaTeX math, syntax highlighting, and clickable citation links, and renders any `format: slides` document as a self-contained 16:9 slide deck (print-to-PDF ready).

## Install

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e .                 # core CLI
pip install -e ".[web]"          # + browser reader / slides  (zr web)
pip install -e ".[mineru]"       # + MinerU PDF engine        (zr parse)
pip install -e ".[embed]"        # + local embeddings         (optional)
```

Requires Python 3.10+ and a local Zotero install. Zotero must be **running** for imports (they go through the connector API). The [Better BibTeX](https://retorque.re/zotero-better-bibtex/) plugin is recommended for stable citekeys.

## Quick start

```bash
zr doctor                    # check Zotero / BBT / MinerU wiring
zr lib stats                 # Hyrule Compendium overview
zr lib search "embodied"     # keyword search across title/abstract/tags
zr show <key|citekey>        # metadata + abstract + attachment + memories

zr ws init paper -q "How do VLAs handle mid-execution task switching?"
zr ws add paper 2506.03574   # plant a seed (Zotero key / DOI / arXiv id / url)
zr ws related paper          # rebuild related.md from all seeds
zr ws parse paper --yes      # parse ONLY this workspace's seeds (preview without --yes)

zr web                       # read everything in the browser at 127.0.0.1:8765
```

Open the directory with Claude Code and the skills become available — describe a research question in natural language and the agent drives the CLI for you.

## Command reference

| Command | Purpose |
|---|---|
| `zr doctor` | Sheikah Slate diagnostics (Zotero DB, BBT, MinerU token) |
| `zr lib stats` | library overview |
| `zr lib search <q> [--type ...]` | keyword search across title / abstract / tags |
| `zr lib list --collection <name>` | items in a collection |
| `zr lib collections` | list collections |
| `zr show <key\|citekey>` | metadata + abstract + attachment + memories |
| `zr parse <key> [--engine mineru\|pymupdf]` | PDF → `data/transcripts/<key>/paper.md` |
| `zr annotations <key>` | your highlights & notes from the PDF |
| `zr related <key>` | backward refs + forward citations, deduped vs library |
| `zr trends "<topic>"` | OpenAlex pull (years, venues, top-cited) |
| `zr import <doi\|arxiv\|url>` | +1 to the Compendium via the Zotero connector |
| `zr notes <key> [--append "..."]` | recovered Memory — durable per-paper notes |
| `zr ws init <name> [-q "..."]` | establish a Stable for a question |
| `zr ws add <name> <seed>` | plant a Korok seed (Zotero key / DOI / arXiv / url) |
| `zr ws list` / `zr ws show <name>` | list / inspect workspaces |
| `zr ws related <name> [-n N]` | rebuild `related.md` from all seeds |
| `zr ws parse <name> [--yes]` | parse only this workspace's seeds (preview by default) |
| `zr web [--port P] [--host H] [--no-open]` | browser reader + slide decks |

Zelda-flavoured aliases are cosmetic and behave identically: `zr compendium` = `lib`, `zr stable` = `ws`, `zr sensor` = `related`, `zr memory` = `notes`, `zr shrine` = `parse`, `zr map` = `web`. Set `ZORESEARCH_PLAIN=1` to mute the flavour entirely.

## Reading in the browser

```bash
zr web              # serves http://127.0.0.1:8765
```

The reader renders every Markdown file under `workspace/` with KaTeX math, highlighted code, and citation links that resolve back to Zotero / arXiv. A document whose front-matter sets `format: slides` is rendered as a presentation instead:

```markdown
---
format: slides
title: My talk
---
# Title slide

---
## A content slide
- bullets, math $E=mc^2$, images, `<video>` all work

left column
:::
right column
```

- `---` on its own line separates slides; `:::` splits a slide into columns.
- Decks are letterboxed to a fixed **16:9** stage, so they look identical on any screen.
- `F` toggles fullscreen, `← / →` / `Space` navigate, `⌘P` prints the deck straight to a 1280×720 PDF.
- A theme toggle (light / dark) sits in the corner and is remembered across reloads.

## Layout

```
zoresearch/
  src/zoresearch/        # python package — the CLI and web reader live here
  .claude/skills/        # agent skills (one SKILL.md per skill)
  data/                  # local cache (gitignored, rebuildable)
    transcripts/<key>/   # parsed PDFs as markdown + extracted images
    citations/           # OpenAlex response cache
    notes/<key>.md       # per-paper Memories the agent appends to
  workspace/             # research projects (gitignored)
    <project>/
      question.md        # your framing of the question
      seeds.txt          # Zotero keys / DOIs / arXiv ids to start from
      related.md         # discovered work
      notes.md           # synthesis
```

See [DEVELOPMENT.md](DEVELOPMENT.md) for the module map, data flow, and how to add a command or a skill.

## Notes

- Developed and tested on macOS.
- The MinerU token lives at `~/.zoresearch/config.toml` (mode `600`, outside the repo).
- The citation graph uses OpenAlex — no API key required.
- This tool **never** writes to `~/Zotero/zotero.sqlite`; imports go through the connector API, which is why Zotero has to be running.
- `data/` and `workspace/` are rebuildable / personal and are gitignored.

## License

MIT.
