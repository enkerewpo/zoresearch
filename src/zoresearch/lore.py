"""Cosmetic Zelda flavor — Sheikah Slate vibes for the CLI.

Visual language is borrowed from Breath of the Wild:

* **Sheikah cyan** (bright_cyan) — active runes, the slate's display glow
* **Triforce gold** (yellow) — the user, success, the journey
* **Malice red** (bright_red) — corruption / errors / blocked paths
* **Korok green** (bright_green) — quiet success / discoveries
* **Royal blue** (blue) — info, ambient detail

Iconography:

* ``◈`` — filled hexagon, an *activated* shrine pedestal (success)
* ``◇`` — empty hexagon, a *dormant* state (info / pending)
* ``▲`` — Triforce triangle (warning / direction)
* ``▽`` — inverted triangle, the Sheikah eye's teardrop (info)
* ``◉`` — the Sheikah eye iris itself (the slate's gaze)

Strictly user-facing strings. Set ``ZORESEARCH_PLAIN=1`` to mute everything.
"""
from __future__ import annotations

import os

PLAIN = bool(os.environ.get("ZORESEARCH_PLAIN"))


# --- palette (Rich style names) ----------------------------------------------

SHEIKAH_CYAN = "bright_cyan"
TRIFORCE_GOLD = "yellow"
MALICE_RED = "bright_red"
KOROK_GREEN = "bright_green"
ROYAL_BLUE = "blue"
ANCIENT_DIM = "dim cyan"


# --- glyphs ------------------------------------------------------------------

EYE = "◉"
TEAR = "▽"
HEX_ON = "◈"
HEX_OFF = "◇"
TRIANGLE = "▲"


# --- banner ------------------------------------------------------------------

BANNER = r"""
                       [yellow]▲[/yellow]
                      [yellow]▲ ▲[/yellow]                 [bright_cyan]◉[/bright_cyan]
                     [yellow]▲▲▲▲▲[/yellow]                [bright_cyan]▽[/bright_cyan]
       [dim cyan]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/dim cyan]
       [bright_cyan bold]Z O R E S E A R C H[/bright_cyan bold]   ·   [bright_cyan]Sheikah Slate v0.1.0[/bright_cyan]
       [dim cyan]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/dim cyan]
       [italic dim]"It's dangerous to read alone. Take this."[/italic dim]
"""


def banner() -> str:
    return "" if PLAIN else BANNER


# --- helpers ----------------------------------------------------------------


def ok(plain: str) -> str:
    """Sheikah-style success line. ``◈`` is an activated shrine pedestal."""
    if PLAIN:
        return f"ok  {plain}"
    return f"[{KOROK_GREEN}]{HEX_ON}[/{KOROK_GREEN}] {plain}"


def warn(plain: str) -> str:
    if PLAIN:
        return f"warn  {plain}"
    return f"[{TRIFORCE_GOLD}]{TRIANGLE}[/{TRIFORCE_GOLD}] {plain}"


def err(plain: str) -> str:
    if PLAIN:
        return f"err  {plain}"
    return f"[{MALICE_RED}]✕[/{MALICE_RED}] {plain}"


def info(plain: str) -> str:
    if PLAIN:
        return f"info  {plain}"
    return f"[{ANCIENT_DIM}]{TEAR}[/{ANCIENT_DIM}] {plain}"


def status_icon(state: str) -> str:
    """Map doctor-style status to a Sheikah glyph + colour."""
    if PLAIN:
        return state
    return {
        "ok":      f"[{KOROK_GREEN}]{HEX_ON}[/{KOROK_GREEN}] ok",
        "warn":    f"[{TRIFORCE_GOLD}]{TRIANGLE}[/{TRIFORCE_GOLD}] warn",
        "missing": f"[{MALICE_RED}]✕[/{MALICE_RED}] missing",
        "off":     f"[{MALICE_RED}]✕[/{MALICE_RED}] off",
        "info":    f"[{ANCIENT_DIM}]{HEX_OFF}[/{ANCIENT_DIM}] info",
    }.get(state, state)


def title(text: str) -> str:
    if PLAIN:
        return text
    return f"[{SHEIKAH_CYAN} bold]{text}[/{SHEIKAH_CYAN} bold]"


# Translation table for command success messages. Source of truth for tone.
PHRASES = {
    "doctor_ready":     "Sheikah Slate online — all runes responding",
    "doctor_partial":   "Sheikah Slate online — some runes need attention",
    "lib_overview":     "Hyrule Compendium",
    "import_added":     "+1 to the Compendium",
    "import_pending":   "Sheikah Sensor reaching out…",
    "parse_done":       "Shrine cleared — full text recovered",
    "parse_cached":     "Shrine already cleared — using stored memory",
    "related_done":     "Shrine Sensor pulse",
    "trends_done":      "Surveying the Wilds",
    "ws_created":       "Stable established",
    "ws_seed_added":    "Korok seed planted",
    "ws_related_done":  "Sensor pulse complete",
    "notes_appended":   "Memory recovered",
    "notes_empty":      "No memories here yet — the path is fresh",
    "section_metadata": "Tablet entry",
    "section_abstract": "Abstract",
    "section_notes":    "Recovered Memories",
    "section_pdf":      "Tome attached",
    "section_transcript": "Transcript ready",
    "section_collection": "Filed under",
    "section_tags":     "Glyphs",
    "section_authors":  "Hands that wrote it",
}


def say(key: str, *, plain: str | None = None) -> str:
    if PLAIN and plain is not None:
        return plain
    return PHRASES.get(key, plain or key)
