---
name: workspace
description: Create and maintain a research-question workspace — a per-project directory holding the question, seed papers, discovered related work, and synthesis notes. Use when the user states a research question or starts a new line of inquiry.
---

# workspace

A workspace is one directory under `workspace/<slug>/`:

```
workspace/<slug>/
  question.md      # the user's framing of the problem
  seeds.txt        # one Zotero key, citekey, DOI, or arXiv id per line
  related.md       # OpenAlex-derived related work, deduped vs library
  notes.md         # your accumulated synthesis
```

Workspaces are gitignored. They are the user's personal research scratch.

> **`seeds.txt` is the deep-read list.** Anything in `seeds.txt` is a paper
> the user has decided is worth reading in full — these are the only items
> that should ever be passed to MinerU (`zr ws parse <name>`). Anything in
> `related.md` is a candidate to skim at abstract level only; promoting one
> to a seed requires the user's say-so.

## When to use

- The user states a research question (even vaguely): **start a workspace
  before doing anything else**, write the question into `question.md`, and
  put any cited seed papers into `seeds.txt`.
- The user is iterating on a question over multiple sessions: load the
  existing workspace and append to its `notes.md`.
- The user wants a "literature review" or "state of the art" on something:
  this is a workspace task.

## Tools

```bash
zr ws init "<name>" -q "<the research question>"
zr ws list
zr ws add <name> <key|doi|arxiv-id>
zr ws show <name>
zr ws related <name> --top 60     # rebuild related.md from seeds (no parsing)
zr ws parse <name>                # preview which seeds need MinerU
zr ws parse <name> --yes          # parse the seeds, only the seeds
```

## Workflow

1. **Init**: `zr ws init "<name>" -q "<question>"`. Pick a short slug; the CLI
   slugifies the name for the directory.
2. **Seed**: search the local library (`zr lib search`) for items the user
   already owns on this topic. Add the most relevant ones with `zr ws add`.
   If the user mentions specific papers, add their DOIs or arXiv ids.
3. **Expand**: `zr ws related <name>` runs the citation graph against every
   seed, dedupes, and writes `related.md`. Read it.
4. **Synthesise**: write themes, gaps, and disagreements into `notes.md`.
   Append, don't rewrite — old reasoning is useful in future sessions.
5. **Promote candidates to seeds before parsing.** When the user says "I want
   to actually read \<X\>", `zr ws add <name> <X>` first, then
   `zr ws parse <name>` to confirm only that one is added to the parse queue,
   then `--yes` to run.
6. **Loop**: as the user reacts to the synthesis, add more seeds and re-run
   `ws related`. Track the question's evolution in `question.md` (revise it
   when the framing shifts).

## Don't

- Don't dump the full `related.md` content into the main agent's context.
  Summarise the top groups (most actionable / surprising / well-cited) and
  point the user at the file.
- Don't put research output in `data/` — that directory is a rebuildable
  cache. Anything you want to survive a `rm -rf data/` goes in `workspace/`.
- Don't mix unrelated questions in one workspace. Two questions = two
  workspaces.
