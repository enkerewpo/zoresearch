<p align="center"><img src="assets/logo.svg" width="128" alt="zoresearch logo"/></p>

# zoresearch

> _"It's dangerous to read alone. Take this."_

A small, personal research copilot built on top of a local Zotero library. Think of it as a Sheikah Slate for your reading: the **Compendium** catalogues what you already have, the **Sensor** points at the related work you don't, **Stables** are workspaces around a research question, and **Memories** are the durable notes you accumulate paper by paper.

Zotero stays the source of truth — `zotero.sqlite` is read-only from this tool's perspective, and any new items are pushed in through Zotero's own connector API. Nothing in `~/Zotero/` gets rewritten by hand.

## What it does

When opened with Claude Code (or another agent that reads `.claude/skills/`):

- Browse and search your existing library by topic, author, year, collection.
- Convert any attached PDF into a multimodal Markdown transcript (figures + tables preserved) that an LLM can actually reason over — MinerU as the default engine, `pymupdf4llm` as zero-config fallback.
- Pull a citation graph for a seed paper or a working set, deduplicate it against your library, find the related work you haven't found yet, and import the missing items back into Zotero.
- Identify research trends and gaps for a topic, grounded in your own library plus OpenAlex.
- Persist per-paper notes that survive across sessions.

The `zr` CLI is the load-bearing layer. Skills are thin orchestration on top.

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
zr doctor                    # checks Zotero / BBT / MinerU
zr lib stats                 # library overview
zr lib search "embodied"     # keyword search
zr show <key|citekey>        # metadata + abstract + attachment + memories
zr ws init "<question>"      # open a workspace for a research question
zr ws related <name>         # build related.md from the workspace's seeds
zr ws parse <name> [--yes]   # parse only this workspace's seeds (preview by default)
```

Open the directory with Claude Code and the skills under `.claude/skills/` become available — describe a research question in natural language and the agent drives the CLI.

## Layout

```
zoresearch/
  src/zoresearch/        # python package, CLI lives here
  .claude/skills/        # agent skills (SKILL.md per skill)
  data/                  # local cache (gitignored, rebuildable)
    transcripts/<key>/   # parsed PDFs as markdown + images
    citations/           # OpenAlex response cache
    notes/<key>.md       # per-paper notes the agent appends to
  workspace/             # research projects (gitignored)
    <project>/
      question.md
      seeds.txt
      related.md
      notes.md
```

## Notes

- macOS only tested. Zotero must be installed; running is required for imports.
- MinerU token lives at `~/.zoresearch/config.toml` (mode 600, outside the repo).
- Citation graph uses OpenAlex (no key required).
- Never modifies `~/Zotero/zotero.sqlite`. Imports go through the connector API.
- `ZORESEARCH_PLAIN=1` mutes the Sheikah Slate flavor entirely.

## Aliases

The Zelda flavor is paint on user-facing strings; canonical command names work too.

| Flavor | Canonical |
|--------|-----------|
| `zr compendium ...` | `zr lib ...` |
| `zr stable ...`     | `zr ws ...` |
| `zr sensor <key>`   | `zr related <key>` |
| `zr memory <key>`   | `zr notes <key>` |
| `zr shrine <key>`   | `zr parse <key>` |

## License

MIT.
