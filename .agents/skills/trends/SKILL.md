---
name: trends
description: Analyse research trends and gaps for a topic by combining the user's local library with OpenAlex. Use when the user asks "what's hot in X?", "where are the gaps?", or "is this a saturated field?".
---

# trends

Two complementary views:

1. **External view** — `zr trends "<topic>"` runs an OpenAlex search and
   summarises year distribution, top venues, and most-cited works.
2. **Internal view** — `zr lib search "<topic>"` shows what the user already
   owns on the topic.

Compare the two to surface gaps: external papers that aren't in the library,
research-heavy years where the user has no coverage, venues missing entirely.

## When to use

- "What's the activity around \<topic\> in the last 5 years?"
- "Are there obvious sub-areas of \<topic\> I'm not following?"
- "Has anyone published on \<X\> recently? Or is the field cold?"
- "Help me find a research gap" — combine `trends` with `lib search` and
  summarise where external activity is high but library coverage is low.

## Tools

```bash
zr trends "<topic>" --n 100              # OpenAlex pull
zr lib search "<topic>" -n 100           # local coverage
```

## Workflow

1. Run both `zr trends` and `zr lib search` for the same topic.
2. Cross-reference: which top-cited external works are missing? Which venues
   appear externally but never in the library? Which years are well-covered
   externally but absent locally?
3. Produce a short structured report:
   - **Activity over time** — how the topic moves year over year.
   - **Where the work happens** — top venues and groups.
   - **Library coverage** — what fraction of high-impact work the user owns.
   - **Gaps** — concrete missing papers / sub-areas the user could fill in.
4. If gaps are clear and small, suggest 3-5 specific imports via the
   `import` skill.

## Don't

- Don't conflate "high cited_by_count" with "important to the user's research"
  — old foundational papers dominate that metric. Look at recency too.
- Don't assume an empty `lib search` means the user doesn't care; check
  related terms (e.g. "RAG" vs "retrieval-augmented generation") before
  declaring a gap.
