<p align="center"><img src="assets/logo.svg" width="128" alt="zoresearch logo"/></p>

# zoresearch

A small research copilot built on top of a local Zotero library. It browses what you already have, finds the related work you don't, keeps workspaces around a research question, and keeps durable per-paper notes.

Zotero stays the source of truth — `zotero.sqlite` is read-only from this tool's perspective, and any new items are pushed in through Zotero's own connector API. Nothing in `~/Zotero/` gets rewritten by hand.

## What it does

The `zr` CLI is the load-bearing layer; the skills under `.agents/skills/` are thin orchestration on top, so the same workflows run by hand or driven by any coding agent (Codex, Claude Code, and others that read `AGENTS.md` and `SKILL.md`).

- **Browse & search** your existing library by topic, author, year, or collection.
- **Parse PDFs** into multimodal Markdown transcripts (figures + tables preserved) that an LLM can actually reason over — MinerU as the default engine, `pymupdf4llm` as the zero-config fallback.
- **Find related work** via a citation graph (OpenAlex) for a seed paper or a whole workspace, deduplicated against your library, and **import** the missing items back into Zotero.
- **Analyse trends & gaps** for a topic, grounded in your own library plus OpenAlex.
- **Keep per-paper notes** that survive across sessions.
- **Read in the browser** — `zr web` serves your workspaces as a clean reader with KaTeX math, syntax highlighting, and clickable citation links, and renders any `format: slides` document as a self-contained 16:9 slide deck (print-to-PDF ready).

## Install

```bash
pip install zorsch               # core CLI, installs the `zr` command
pip install "zorsch[web]"        # + browser reader / slides  (zr web)
pip install "zorsch[mineru]"     # + MinerU PDF engine        (zr parse)
pip install "zorsch[embed]"      # + local embeddings         (optional)
```

Installed this way, `data/` and `workspace/` live in the per-user data directory (on macOS `~/Library/Application Support/zorsch`). Set `ZORESEARCH_HOME` to put them elsewhere. From a source checkout, `pip install -e .` keeps them inside the repository.

Requires Python 3.10+ and a local Zotero install. Zotero must be **running** for imports (they go through the connector API). The [Better BibTeX](https://retorque.re/zotero-better-bibtex/) plugin is recommended for stable citekeys.

## Quick start

```bash
zr doctor                    # check Zotero / BBT / MinerU wiring
zr lib stats                 # library overview
zr lib search "embodied"     # keyword search across title/abstract/tags
zr show <key|citekey>        # metadata + abstract + attachment + notes

zr ws init paper -q "How do VLAs handle mid-execution task switching?"
zr ws add paper 2506.03574   # plant a seed (Zotero key / DOI / arXiv id / url)
zr ws related paper          # rebuild related.md from all seeds
zr ws parse paper --yes      # parse ONLY this workspace's seeds (preview without --yes)

zr web                       # read everything in the browser at 127.0.0.1:8765
```

Open the directory with a coding agent: it reads `AGENTS.md` and the skills under `.agents/skills/`. Describe a research question in natural language and the agent drives the CLI for you. Claude Code finds the same skills through the `.claude/skills` link.

## Command reference

| Command | Purpose |
|---|---|
| `zr doctor` | environment checks (Zotero DB, BBT, MinerU token) |
| `zr lib stats` | library overview |
| `zr lib search <q> [--type ...]` | keyword search across title / abstract / tags |
| `zr lib list --collection <name>` | items in a collection |
| `zr lib collections` | list collections |
| `zr show <key\|citekey>` | metadata + abstract + attachment + notes |
| `zr parse <key> [--engine mineru\|pymupdf]` | PDF → `data/transcripts/<key>/paper.md` |
| `zr annotations <key>` | your highlights & notes from the PDF |
| `zr related <key>` | backward refs + forward citations, deduped vs library |
| `zr trends "<topic>"` | OpenAlex pull (years, venues, top-cited) |
| `zr import <doi\|arxiv\|url\|file.ris>` | add to Zotero via the connector; a `.ris` file adds hand-written records with their local PDFs (`L1`) |
| `zr notes <key> [--append "..."]` | durable per-paper notes |
| `zr ws init <name> [-q "..."]` | create a workspace for a question |
| `zr ws add <name> <seed>` | add a seed paper (Zotero key / DOI / arXiv / url) |
| `zr ws list` / `zr ws show <name>` | list / inspect workspaces |
| `zr ws related <name> [-n N]` | rebuild `related.md` from all seeds |
| `zr ws parse <name> [--yes]` | parse only this workspace's seeds (preview by default) |
| `zr web [--port P] [--host H] [--no-open]` | browser reader + slide decks |

Set `ZORESEARCH_PLAIN=1` for output without colours.

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
  .agents/skills/        # agent skills (one SKILL.md per skill); .claude/skills links here
  data/                  # local cache (gitignored, rebuildable)
    transcripts/<key>/   # parsed PDFs as markdown + extracted images
    citations/           # OpenAlex response cache
    notes/<key>.md       # per-paper notes the agent appends to
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
