---
name: library
description: Browse and search the user's local Zotero library. Use when the user asks what they have, wants to find a paper they remember, or needs an overview of a collection.
---

# library

The local Zotero library has ~800 papers and ~1100 PDF attachments. Whole-library
scans are cheap; do them.

## When to use

- "What do I have on \<topic\>?" → `zr lib search "<topic>"`
- "Show me what's in my <X> collection" → `zr lib list --collection X`
- "How many papers do I have on Y?" → `zr lib search "Y" -n 100 | wc -l`
- "Open this paper" / "tell me about this one" → `zr show <key>`

## Tools

```bash
zr doctor                          # sanity check before anything else
zr lib stats                       # by-type counts, attachment / annotation totals
zr lib collections                 # workspace-style organisation in Zotero
zr lib list --collection "<name>"  # items in a collection
zr lib list --type journalArticle  # filter by type
zr lib search "<query>"            # substring search (title/abstract/tags)
zr show <key|citekey>              # one item: metadata, abstract, attachment, notes
zr annotations <key>               # user highlights from the PDF
```

## Workflow

1. Always start with `zr doctor` if you haven't this session — it confirms
   Zotero is reachable and shows library size.
2. For a topic question, run `zr lib search` first. If the user's framing is
   broad, run two or three queries with different keywords and merge results
   in your head.
3. When showing a single paper, `zr show <key>` already prints metadata,
   abstract, attachment paths, and any existing notes — no need to read those
   files separately.
4. Always cite items by their key (e.g. `ABCD1234`) so the user can copy/paste
   it into other commands.

## Don't

- Don't read `~/Zotero/zotero.sqlite` or files under `~/Zotero/storage/`
  directly. Always go through `zr`.
- Don't dump more than ~30 items into the main agent context — if a search
  returns a long list, summarise themes and cite the top few keys.
