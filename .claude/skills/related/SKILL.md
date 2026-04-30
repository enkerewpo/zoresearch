---
name: related
description: Find related work for a paper or set of seed papers via the OpenAlex citation graph. Use when the user asks "what should I read next?", "what cites this?", or "what's the prior work this builds on?".
---

# related

Pulls **backward references** (what the seed cites) and **forward citations**
(what cites the seed) from OpenAlex, then deduplicates against the local
Zotero library so you can immediately see what's missing.

Each result is tagged:
- `[✓]` — already in your Zotero
- `[ ]` — not in your library; candidate for `zr import`
- `back` / `forw` — direction in the citation graph

Ranking is heuristic: missing items first, forward citations before backward,
then by `cited_by_count`.

## When to use

- "What should I read next on \<topic\> based on \<seed\>?" → `zr related <key> --top 50`
- "What's the lineage of this paper?" → `zr related <key>` and read backward refs.
- "What recent work builds on this?" → `zr related <key>` and read forward refs.
- "Build a related-work picture for my project" → use the workspace skill, not
  just `related` — workspaces dedupe across multiple seeds.

## Tools

```bash
zr related <key> --top 50                # print to console
zr related <key> --out workspace/X/related.md
```

Requires the seed item to have a DOI in Zotero. If it doesn't, ask the user
to add one (Zotero's "Add by Identifier" can fill it in) or use the workspace
skill with arXiv id seeds.

## Workflow

1. Confirm the seed has a DOI: `zr show <key>` shows `doi: ...`. If missing,
   stop and tell the user — OpenAlex needs DOI or arXiv id to find a record.
2. Run `zr related <key> --top 80`.
3. Group the results: missing-and-highly-cited (most actionable), missing-and-
   recent (frontier), already-in-library (worth re-reading).
4. Suggest 3-7 concrete next reads with one-line justifications. Don't dump
   the whole list — summarise.
5. If the user wants to fetch missing ones, hand off to the `import` skill.

## Don't

- Don't claim a paper is "the most relevant" without reading at least its
  abstract via OpenAlex's `shallow` projection (already inlined in `--out`).
- Don't run `related` on more than ~5 seeds at a time without a workspace —
  the result set explodes and dedup gets fuzzy.
