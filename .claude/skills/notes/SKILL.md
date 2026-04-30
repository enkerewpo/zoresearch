---
name: notes
description: Append durable per-paper analysis notes that persist across sessions. Use after any meaningful analysis of a paper so the next session can pick up where you left off.
---

# notes

Each Zotero item gets one Markdown file at `data/notes/<key>.md`. The agent
appends a dated section per analysis pass. `zr show <key>` automatically
displays existing notes, so the next session starts with prior context.

This is the **T2 layer** in the layered-reading model: refined findings worth
keeping. The full transcript (T3) lives in `data/transcripts/`; the
conversational reply (T1) ends with the chat.

## When to use

- Right after parsing and analysing a paper: capture the 3-5 things worth
  remembering before the conversation moves on.
- When discovering a connection between papers: note it on **both** items so
  whichever one you load next, the link surfaces.
- When the user disagrees with the paper or flags a methodological flaw:
  capture the user's critique alongside the paper.

## Tools

```bash
zr show <key>                              # always shows existing notes too
zr notes <key>                             # just the notes
zr notes <key> --append "<body>"           # append a new section
zr notes <key> --append "..." --kind methods   # tag the section
```

Section format (auto-applied by `--append`):

```
## YYYY-MM-DD | agent | analysis
- Finding 1
- Finding 2
```

## Workflow

1. Before analysing a paper, run `zr show <key>` to load any existing notes.
   Treat them as prior agent output — they may be biased or stale; verify
   against the transcript when conclusions feel shaky.
2. After analysis, append findings:
   - **Methods** — what the paper actually did, not what the abstract claims.
   - **Headline result** — single sentence.
   - **Limitations** — be honest, don't parrot the paper.
   - **Connections** — other items in the library this relates to (cite keys).
3. Keep entries terse. Bullet points, not paragraphs.

## Don't

- Don't rewrite or delete prior notes — append, even if you think a previous
  entry is wrong. Add a new dated section with the corrected reading.
- Don't put workspace-level synthesis here; that goes in
  `workspace/<project>/notes.md`. Per-paper notes are about one paper.
- Don't dump highlights from `zr annotations` into notes verbatim — those
  are the user's own marks. Notes are *your* derived findings.
