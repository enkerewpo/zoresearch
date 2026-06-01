"""``zr`` CLI entrypoint."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from . import import_, lore, notes as notes_mod, openalex, parse as parse_mod, related as related_mod, workspace as ws, zot
from .config import CONFIG, USER_CONFIG
from .paths import DATA, NOTES, REPO, TRANSCRIPTS, WORKSPACE, ZOTERO_DB, ensure_dirs

app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help="zoresearch — Sheikah Slate for your Zotero library.",
)
lib_app = typer.Typer(no_args_is_help=True, help="Hyrule Compendium — browse and search the library.")
ws_app = typer.Typer(no_args_is_help=True, help="Stables — research-question workspaces.")
app.add_typer(lib_app, name="lib")
app.add_typer(ws_app, name="ws")
app.add_typer(lib_app, name="compendium", help="(alias of lib) Hyrule Compendium — browse the library.")
app.add_typer(ws_app, name="stable", help="(alias of ws) Stables — research-question workspaces.")

console = Console()


# ---------- top-level commands ----------------------------------------------


@app.command()
def doctor():
    """Run environment checks: Zotero, BBT, MinerU, deps."""
    ensure_dirs()
    if (b := lore.banner()):
        console.print(f"[cyan]{b}[/cyan]")
    rows: list[tuple[str, str, str]] = []
    rows.append(("repo root", "info", str(REPO)))
    rows.append(("Zotero db", "ok" if ZOTERO_DB.exists() else "missing", str(ZOTERO_DB)))
    if ZOTERO_DB.exists():
        st = zot.stats()
        rows.append(("library size", "info", f"{sum(st['by_type'].values())} papers, {st['pdf_attachments']} PDFs"))
    rows.append(("Zotero running", "ok" if zot.zotero_running() else "off", "needed for import"))
    try:
        zot.bbt_rpc("user.groups")
        rows.append(("Better BibTeX", "ok", "JSON-RPC reachable"))
    except Exception as e:  # noqa: BLE001
        rows.append(("Better BibTeX", "warn", f"{e}"))
    rows.append(
        (
            "MinerU token",
            "ok" if CONFIG.mineru.token else "missing",
            f"config at {USER_CONFIG}",
        )
    )
    try:
        import pymupdf4llm  # noqa: F401
        rows.append(("pymupdf4llm", "ok", ""))
    except Exception as e:  # noqa: BLE001
        rows.append(("pymupdf4llm", "warn", str(e)))

    table = Table(
        title=f"[{lore.SHEIKAH_CYAN} bold]Sheikah Slate diagnostics[/{lore.SHEIKAH_CYAN} bold]",
        border_style=lore.ANCIENT_DIM,
        title_style=lore.SHEIKAH_CYAN,
    )
    table.add_column("rune", style=lore.SHEIKAH_CYAN)
    table.add_column("status")
    table.add_column("detail", style="dim")
    statuses = [s for _, s, _ in rows]
    for k, s, d in rows:
        table.add_row(k, lore.status_icon(s), d)
    console.print(table)
    all_ok = all(s in ("ok", "info") for s in statuses)
    console.print(
        f"[{lore.KOROK_GREEN if all_ok else lore.TRIFORCE_GOLD}]"
        f"{lore.HEX_ON if all_ok else lore.TRIANGLE} "
        f"{lore.say('doctor_ready' if all_ok else 'doctor_partial')}"
        f"[/{lore.KOROK_GREEN if all_ok else lore.TRIFORCE_GOLD}]"
    )


@app.command()
def show(key_or_citekey: str = typer.Argument(..., help="Zotero item key or BBT citekey")):
    """Show metadata, abstract, attachment paths, and existing notes."""
    item = zot.get_item(key_or_citekey)
    if item is None:
        console.print(lore.err(f"not found: {key_or_citekey}"))
        raise typer.Exit(1)
    cyan = lore.SHEIKAH_CYAN
    dim = lore.ANCIENT_DIM
    console.print(f"[{cyan} bold]{lore.EYE} {item.title}[/{cyan} bold]")
    console.print(f"  [{dim}]type     [/{dim}] {item.item_type}")
    console.print(f"  [{dim}]authors  [/{dim}] {', '.join(item.creators) or '—'}")
    console.print(f"  [{dim}]year     [/{dim}] {item.year or '—'}")
    console.print(f"  [{dim}]venue    [/{dim}] {item.publication or '—'}")
    console.print(f"  [{dim}]doi      [/{dim}] {item.doi or '—'}")
    console.print(f"  [{dim}]key      [/{dim}] [{cyan}]{item.key}[/{cyan}]")
    if item.citekey:
        console.print(f"  [{dim}]citekey  [/{dim}] {item.citekey}")
    if item.tags:
        console.print(f"  [{dim}]glyphs   [/{dim}] {', '.join(item.tags)}")
    if item.collections:
        console.print(f"  [{dim}]filed in [/{dim}] {', '.join(item.collections)}")
    pdfs = zot.attachments(item.key)
    if pdfs:
        console.print(f"  [{dim}]tome     [/{dim}]")
        for p in pdfs:
            console.print(f"    {p}")
    transcript = TRANSCRIPTS / item.key / "paper.md"
    if transcript.exists():
        console.print(f"  [{dim}]transcript[/{dim}] [{lore.KOROK_GREEN}]{lore.HEX_ON}[/{lore.KOROK_GREEN}] {transcript}")
    if item.abstract:
        console.print(f"\n[{cyan} bold]{lore.TEAR} {lore.say('section_abstract')}[/{cyan} bold]")
        console.print(item.abstract)
    n = notes_mod.read(item.key)
    if n:
        console.print(f"\n[{cyan} bold]{lore.EYE} {lore.say('section_notes')}[/{cyan} bold]")
        console.print(n)


@app.command()
def parse(
    key: str = typer.Argument(..., help="Zotero item key or citekey"),
    engine: str = typer.Option(None, "--engine", "-e", help="mineru | pymupdf"),
    force: bool = typer.Option(False, "--force", "-f"),
):
    """Run the PDF -> Markdown pipeline for an item."""
    ensure_dirs()
    res = parse_mod.parse_item(key, engine=engine, force=force)
    phrase = "parse_cached" if res.engine == "cache" else "parse_done"
    console.print(lore.ok(f"{lore.say(phrase)}  engine={res.engine}  out={res.markdown_path}"))


@app.command()
def annotations(key: str):
    """Show user highlights and notes attached to a paper's PDF."""
    rows = zot.annotations(key)
    if not rows:
        console.print("(no annotations)")
        return
    for a in rows:
        marker = {"highlight": "▌", "note": "✎", "underline": "_"}.get(a["type"], "•")
        page = f"p.{a['page']}" if a["page"] else ""
        console.print(f"[dim]{page:<6}[/dim] {marker} {a['text']}")
        if a["comment"]:
            console.print(f"        [yellow]→ {a['comment']}[/yellow]")


@app.command(name="import")
def import_cmd(
    value: str = typer.Argument(..., help="DOI, arXiv id, or URL"),
    collection: str = typer.Option(None, "--collection", "-c", help="Zotero collection name to file the item under"),
):
    """Fetch metadata + PDF and add to Zotero (optionally into a collection)."""
    console.print(lore.say("import_pending"))
    res = import_.import_one(value, collection=collection)
    if res.error and not res.item_saved:
        console.print(lore.err(res.error))
        raise typer.Exit(1)
    bits = []
    if res.item_saved: bits.append("metadata ✓")
    if res.pdf_attached: bits.append("PDF ✓")
    elif res.target.kind == "arxiv": bits.append("PDF ✗")
    else: bits.append("PDF (none — likely paywall)")
    console.print(lore.ok(f"{lore.say('import_added')}  {res.target.url}  [{', '.join(bits)}]"))
    if res.error and res.item_saved:
        console.print(lore.warn(res.error))
    if res.metadata.get("title"):
        console.print(f"  [{lore.ANCIENT_DIM}]title:[/{lore.ANCIENT_DIM}] {res.metadata['title']}")


@app.command()
def related(
    key: str,
    out: Path = typer.Option(None, "--out", "-o", help="Write Markdown ranking to this file"),
    top: int = typer.Option(50, "--top", "-n"),
):
    """Pull OpenAlex backward refs + forward citations for an item, ranked."""
    ensure_dirs()
    works = related_mod.rank(related_mod.for_item(key))[:top]
    if out:
        with out.open("w", encoding="utf-8") as f:
            f.write(f"# Related work for {key}\n\n")
            for w in works:
                f.write(f"- {w.line()}\n")
                if w.doi:
                    f.write(f"    doi: {w.doi}\n")
                if w.abstract:
                    f.write(f"    {w.abstract[:300]}\n")
        console.print(lore.ok(f"{lore.say('related_done')} — {len(works)} signals → {out}"))
        return
    console.print(f"[dim]{lore.say('related_done')} — {len(works)} signals[/dim]")
    for w in works:
        console.print(w.line())


@app.command()
def trends(
    topic: str = typer.Argument(..., help="Free-text topic / question"),
    n: int = typer.Option(50, "--n"),
):
    """Quick OpenAlex pull for a topic — venues, years, top-cited."""
    works = openalex.search(topic, per_page=min(n, 50), max_pages=max(1, n // 50))
    if not works:
        console.print("(no hits)")
        return
    by_year: dict[int, int] = {}
    venues: dict[str, int] = {}
    for w in works:
        s = openalex.shallow(w)
        if s.get("year"):
            by_year[s["year"]] = by_year.get(s["year"], 0) + 1
        if s.get("venue"):
            venues[s["venue"]] = venues.get(s["venue"], 0) + 1
    console.print(f"[bold]{lore.say('trends_done')}:[/bold] {topic}  (n={len(works)})\n")
    console.print("[bold]Years[/bold]")
    for y in sorted(by_year):
        console.print(f"  {y}: {'█' * by_year[y]} {by_year[y]}")
    console.print("\n[bold]Top venues[/bold]")
    for v, c in sorted(venues.items(), key=lambda x: -x[1])[:8]:
        console.print(f"  {c:>3}  {v}")
    console.print("\n[bold]Top-cited[/bold]")
    top_cited = sorted(works, key=lambda w: -(w.get("cited_by_count") or 0))[:10]
    for w in top_cited:
        s = openalex.shallow(w)
        a = s["authors"][0].split()[-1] if s["authors"] else "Anon"
        console.print(f"  [{s['cited_by_count']:>5}cit] {a} {s['year']} — {s['title'][:90]}")


@app.command()
def notes(
    key: str,
    append: str = typer.Option("", "--append", "-a"),
    source: str = typer.Option("agent", "--source"),
    kind: str = typer.Option("analysis", "--kind"),
):
    """Read or append per-paper notes."""
    if append:
        p = notes_mod.append(key, append, source=source, kind=kind)
        console.print(lore.ok(f"{lore.say('notes_appended')} → {p}"))
        return
    body = notes_mod.read(key)
    if not body:
        console.print(lore.say("notes_empty"))
        return
    console.print(body)


# ---------- lib ---------------------------------------------------------------


@lib_app.command("stats")
def lib_stats():
    """Counts by type, attachment / annotation totals, collections."""
    s = zot.stats()
    table = Table(
        title=f"[{lore.SHEIKAH_CYAN} bold]{lore.EYE}  {lore.say('lib_overview')}[/{lore.SHEIKAH_CYAN} bold]",
        border_style=lore.ANCIENT_DIM,
    )
    table.add_column("entry", style=lore.SHEIKAH_CYAN)
    table.add_column("count", justify="right", style=lore.TRIFORCE_GOLD)
    for t, n in s["by_type"].items():
        table.add_row(t, str(n))
    table.add_row("pdf tomes", str(s["pdf_attachments"]))
    table.add_row("annotations", str(s["annotations"]))
    table.add_row("collections", str(s["collections"]))
    console.print(table)


@lib_app.command("search")
def lib_search(
    query: str,
    limit: int = typer.Option(25, "--limit", "-n"),
):
    """Substring search over title / abstract / tags."""
    items = zot.search(query, limit=limit)
    if not items:
        console.print("(no matches)")
        return
    for item in items:
        console.print(f"[cyan]{item.key}[/cyan]  {item.short()}")


@lib_app.command("list")
def lib_list(
    collection: str = typer.Option(None, "--collection", "-c"),
    type_: str = typer.Option(None, "--type", "-t"),
    limit: int = typer.Option(50, "--limit", "-n"),
):
    """List items, optionally filtered by collection or item type."""
    types = (type_,) if type_ else zot.PAPER_TYPES
    for item in zot.iter_items(types=types, collection=collection, limit=limit):
        console.print(f"[cyan]{item.key}[/cyan]  {item.short()}")


@lib_app.command("collections")
def lib_collections():
    """List collections and their item counts."""
    for name, n in zot.collections():
        console.print(f"  {n:>4}  {name}")


# ---------- workspace --------------------------------------------------------


@ws_app.command("init")
def ws_init(name: str, question: str = typer.Option("", "--question", "-q")):
    """Set up a new stable (workspace) for a research question."""
    p = ws.init(name, question=question)
    console.print(lore.ok(f"{lore.say('ws_created')} → {p}"))


@ws_app.command("list")
def ws_list():
    for n in ws.list_workspaces():
        console.print(f"  {n}")


@ws_app.command("add")
def ws_add(name: str, seed: str):
    """Plant a Korok seed (Zotero key / citekey / DOI / arXiv id) in the stable."""
    p = ws.add_seed(name, seed)
    console.print(lore.ok(f"{lore.say('ws_seed_added')} → {p}"))


@ws_app.command("show")
def ws_show(name: str):
    w = ws.load(name)
    console.print(f"[bold]{w.name}[/bold]  ({w.path})\n")
    console.print(w.question)
    console.print("\n[bold]Seeds[/bold]")
    for s in w.seeds:
        console.print(f"  {s}")


@ws_app.command("parse")
def ws_parse(
    name: str,
    engine: str = typer.Option(None, "--engine", "-e", help="mineru | pymupdf"),
    yes: bool = typer.Option(False, "--yes", "-y", help="actually run; without this, only previews"),
    force: bool = typer.Option(False, "--force", "-f"),
):
    """Parse the seed papers of a workspace — and only those.

    By default this previews what would be parsed and exits. Pass ``--yes`` to
    actually run. We never parse the full ``related.md`` — the workspace's
    seeds.txt is the deliberate "papers I want to deep-read" list; everything
    else stays at metadata + abstract.
    """
    w = ws.load(name)
    todo: list[str] = []
    for seed in w.seeds:
        item = zot.get_item(seed)
        if item is None:
            console.print(lore.warn(f"skip {seed}: not in Zotero"))
            continue
        transcript = TRANSCRIPTS / item.key / "paper.md"
        if transcript.exists() and not force:
            continue
        if not [p for p in zot.attachments(item.key) if p.suffix.lower() == ".pdf"]:
            console.print(lore.warn(f"skip {item.key}: no PDF attachment"))
            continue
        todo.append(item.key)
    if not todo:
        console.print(lore.ok("nothing to parse — every seed already has a transcript"))
        return
    chosen = (engine or CONFIG.parse_engine).lower()
    console.print(
        f"[{lore.SHEIKAH_CYAN}]would clear {len(todo)} shrine(s) "
        f"with engine={chosen}:[/{lore.SHEIKAH_CYAN}]"
    )
    for key in todo:
        item = zot.get_item(key)
        console.print(f"  [{lore.TRIFORCE_GOLD}]{lore.TRIANGLE}[/{lore.TRIFORCE_GOLD}] {key}  {item.short() if item else ''}")
    if not yes:
        console.print(lore.info("preview only — pass --yes to run"))
        return
    for key in todo:
        try:
            res = parse_mod.parse_item(key, engine=engine, force=force)
            console.print(lore.ok(f"{lore.say('parse_done')}  {key}  ({res.engine})"))
        except Exception as e:  # noqa: BLE001
            console.print(lore.err(f"{key}: {e}"))


@ws_app.command("related")
def ws_related(name: str, top: int = typer.Option(40, "--top", "-n")):
    """Build / refresh ``related.md`` for a workspace from its seeds."""
    w = ws.load(name)
    all_works: list[related_mod.RelatedWork] = []
    for seed in w.seeds:
        try:
            all_works.extend(related_mod.for_item(seed))
        except ValueError as e:
            console.print(f"[yellow]skip[/yellow] {seed}: {e}")
    seen: set[str] = set()
    deduped: list[related_mod.RelatedWork] = []
    for r in all_works:
        ident = r.doi.lower() or r.title.lower()
        if ident in seen:
            continue
        seen.add(ident)
        deduped.append(r)
    deduped = related_mod.rank(deduped)[:top]
    out = w.path / "related.md"
    with out.open("w", encoding="utf-8") as f:
        f.write(f"# Related work — {w.name}\n\n")
        f.write(f"_n={len(deduped)} from {len(w.seeds)} seeds_\n\n")
        for r in deduped:
            f.write(f"- {r.line()}\n")
            if r.doi:
                f.write(f"    doi: {r.doi}\n")
            if r.abstract:
                f.write(f"    {r.abstract[:280]}\n")
    console.print(lore.ok(f"{lore.say('ws_related_done')} — {len(deduped)} signals → {out}"))


# ---------- Zelda-flavored aliases ------------------------------------------
# These delegate to the canonical commands so help text stays single-source.


@app.command("sensor", help="(alias of related) Shrine Sensor — find related work via citation graph.")
def sensor(
    key: str,
    out: Path = typer.Option(None, "--out", "-o"),
    top: int = typer.Option(50, "--top", "-n"),
):
    related(key, out=out, top=top)


@app.command("memory", help="(alias of notes) Recovered Memory — read or append per-paper notes.")
def memory(
    key: str,
    append: str = typer.Option("", "--append", "-a"),
    source: str = typer.Option("agent", "--source"),
    kind: str = typer.Option("analysis", "--kind"),
):
    notes(key, append=append, source=source, kind=kind)


@app.command("shrine", help="(alias of parse) Clear the shrine — convert a paper's PDF to multimodal Markdown.")
def shrine(
    key: str,
    engine: str = typer.Option(None, "--engine", "-e"),
    force: bool = typer.Option(False, "--force", "-f"),
):
    parse(key, engine=engine, force=force)


@app.command()
def web(
    port: int = typer.Option(8765, "--port", "-p", help="port to bind"),
    host: str = typer.Option("127.0.0.1", "--host", help="host to bind"),
    no_open: bool = typer.Option(False, "--no-open", help="do not auto-open browser"),
):
    """Map mode — open workspaces in a browser with KaTeX + Zotero citation links."""
    try:
        from . import web as web_mod
    except ImportError as e:
        console.print(f"[red]web reader needs extra deps:[/red] {e}")
        console.print("install with: [cyan]pip install starlette uvicorn markdown-it-py mdit-py-plugins[/cyan]")
        raise typer.Exit(1)
    if (b := lore.banner()):
        console.print(f"[cyan]{b}[/cyan]")
    console.print(f"[green]Sheikah Slate online[/green] → http://{host}:{port}/")
    if not no_open:
        console.print("opening browser…")
    web_mod.serve(host=host, port=port, open_browser=not no_open)


@app.command("map", help="(alias of web) Sheikah Slate map mode — workspace reader.")
def map_cmd(
    port: int = typer.Option(8765, "--port", "-p"),
    host: str = typer.Option("127.0.0.1", "--host"),
    no_open: bool = typer.Option(False, "--no-open"),
):
    web(port=port, host=host, no_open=no_open)


if __name__ == "__main__":
    app()
