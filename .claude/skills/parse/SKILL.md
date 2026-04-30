---
name: parse
description: Convert a Zotero PDF attachment into multimodal Markdown (text, figures, tables, formulas) that an LLM can reason over. Use when the user wants to read or analyse a paper's full content.
---

# parse

Default engine is **MinerU** (cloud, SOTA layout / formula / table reconstruction).
The token is in `~/.zoresearch/config.toml`. Fallback is `pymupdf4llm` for when
the network or token is unavailable.

> **Scope rule (load-bearing).** MinerU is the only expensive operation in
> this tool. The library has hundreds of papers; only parse the ones the user
> is actually deep-reading right now — i.e. the active workspace's
> `seeds.txt`. Never auto-parse from `related.md`. Never parse "everything on
> topic X". When in doubt, ask first.

Output goes to `data/transcripts/<key>/`:

```
data/transcripts/<key>/
  paper.md      # the markdown
  images/       # extracted figures (MinerU only)
  meta.json     # engine, source pdf, timing
```

Already-parsed items are returned from cache instantly. Pass `--force` to
re-run.

## When to use

- "Read this paper" / "what does \<key\> argue?" → parse, then read `paper.md`.
- "Compare the methods in A and B" → parse both, then read both transcripts.
- "Pull the equations / tables out of this paper" → MinerU is the right choice
  (do not fall back to pymupdf for equations).

## Tools

```bash
zr parse <key>                    # MinerU by default, ~1-3 min for a normal paper
zr parse <key> -e pymupdf         # local fallback, instant, no figures
zr parse <key> --force            # ignore cache, re-parse
zr ws parse <name>                # preview which seeds in a workspace need parsing
zr ws parse <name> --yes          # actually run, only on workspace seeds
```

## Workflow

1. **First: is this paper in the active workspace's `seeds.txt`?** If yes,
   parse. If no, ask the user whether to add it as a seed first — parsing
   without seeding is a smell.
2. Run `zr parse <key>`. If the user's question only needs metadata or
   abstract, use `zr show` instead — don't burn a parse call.
2. After parse, read the relevant section of `data/transcripts/<key>/paper.md`
   with grep / Read first; only load the whole file when the paper is short
   or the question really requires it.
3. Figures live in `data/transcripts/<key>/images/` and are referenced from
   the markdown by relative path. You can read figures as images when the
   question asks about a chart or diagram.
4. After meaningful analysis, write your conclusions back via `zr notes <key> --append "..."` so future sessions don't redo the work.

## Don't

- Don't re-parse cached transcripts unless `--force` is justified (e.g. the
  user says "the parse looked broken").
- Don't paste the full transcript into the main agent context. Summarise or
  delegate to a subagent.
- **Never parse from `related.md` automatically.** Related work is for
  skimming at the abstract level. The seeds.txt is the deep-read list.
- Don't loop `zr parse` over more than a couple of items in one go. Use
  `zr ws parse <name> --yes` so the user sees the batch before it runs.
