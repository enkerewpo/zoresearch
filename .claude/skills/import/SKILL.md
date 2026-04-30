---
name: import
description: Add a paper to the user's Zotero library through the local connector API. Use when the user wants to fetch a specific DOI, arXiv id, or paper URL.
---

# import

Imports go through Zotero's own connector endpoint — the same one browser
extensions use. Zotero must be running. We do **not** modify
`zotero.sqlite` directly.

## When to use

- "Get this paper" with a DOI / arXiv id / URL → `zr import <value>`
- "Pull these missing related papers" → call `zr import` once per item the
  user confirms.
- "Add a bunch of arXiv preprints" → loop, but **always confirm with the user
  before importing more than 3 items at a time** — these become real Zotero
  entries.

## Tools

```bash
zr import 10.1145/3503222.3507724
zr import 2401.12345
zr import https://arxiv.org/abs/2401.12345
zr import https://dl.acm.org/doi/10.1145/...
```

Behind the scenes:

- DOI → `https://doi.org/<doi>` → Zotero's translator handles the publisher
  page, including PDF download where the user has access.
- arXiv id → `https://arxiv.org/abs/<id>` → arXiv translator, PDF included.
- Other URLs → translator dispatch via Zotero's local connector.

## Workflow

1. **Always confirm** with the user before calling import. The connector
   creates a real Zotero entry; you cannot silently undo it via this tool.
2. Run `zr import <value>`. The CLI prints Zotero's response.
3. Wait ~5 seconds, then verify with `zr lib search "<title-fragment>"` so
   you can return the new Zotero key to the user.
4. If the user wants to read the paper next, hand off to the `parse` skill
   using the new key.

## Failure modes

- "Zotero not running" → tell the user to open Zotero, then retry.
- Translator returns no items → the URL is something Zotero doesn't recognise.
  Try the DOI or arXiv id directly instead of a publisher landing page.
- PDF not attached → the publisher requires a campus / paywall login. Tell
  the user; offer to look for a preprint via `zr trends` or arXiv search.

## Don't

- Don't import in a loop without explicit consent for the batch.
- Don't try to "fix" Zotero items by writing to its sqlite. If metadata is
  wrong, ask the user to fix it inside Zotero.
