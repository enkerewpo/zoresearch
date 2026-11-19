"""Generate the README banner and badges as SVG.

Text is converted to outlines with IBM Plex Sans, so the images do not depend
on fonts installed where they are viewed, and colours follow the viewer's
light or dark scheme through a CSS media query inside each SVG.

Run before tagging a release; the PyPI badge shows the version in
pyproject.toml.

    python scripts/make_assets.py

Needs fontTools and the IBM Plex Sans OTF files (Regular, Medium, SemiBold).
Set IBM_PLEX_DIR if they are not in ~/Library/Fonts or ~/.local/share/fonts.
Icons are from Simple Icons (CC0).
"""
from __future__ import annotations

import os
import tomllib
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"

ICONS = {
    "pypi": "M23.922 13.58v3.912L20.55 18.72l-.078.055.052.037 3.45-1.256.026-.036v-3.997l-.053-.036-.025.092z M23.621 5.618l-3.04 1.107v3.912l3.339-1.215V5.509zM23.92 13.457V9.544l-3.336 1.215v3.913zM20.47 14.71V10.8L17.17 12v3.913zM17.034 19.996v-3.912l-3.313 1.206v3.912zM17.17 16.057v3.868l3.314-1.206V14.85l-3.314 1.206zm2.093 1.882c-.367.134-.663-.074-.663-.463s.296-.814.663-.947c.365-.133.662.075.662.464s-.297.814-.662.946z M13.225 9.315l.365-.132-3.285-1.197-3.323 1.21.102.037 3.184 1.16zM20.507 10.664V6.751L17.17 7.965v3.913zM17.058 11.918V8.005l-3.302 1.202v3.912zM13.643 9.246l-3.336 1.215v3.913l3.336-1.215zM6.907 13.165l3.322 1.209v-3.913L6.907 9.252z M10.34 7.873l3.281 1.193V5.198l-3.28-1.193zM20.507 2.715L17.19 3.922v3.913l3.317-1.207zM16.95 3.903L13.724 2.73l-3.269 1.19 3.225 1.174zM15.365 4.606l-1.624.592v3.868l3.317-1.207V3.991l-1.693.615zm-.391 2.778c-.367.134-.662-.074-.662-.464s.295-.813.662-.946c.366-.133.663.074.663.464s-.297.813-.663.946z M10.229 18.41v-3.914l-3.322-1.209V17.2zM13.678 17.182v-3.913l-3.371 1.227v3.913z M13.756 17.154l3.3-1.2V12.04l-3.3 1.2zM13.678 21.217l-3.371 1.227v-3.912h-.078v3.912l-3.322-1.209v-3.913l-.053-.058-.025-.06-3.336-1.21v-3.948l.034.013 3.287 1.196.015-.078-3.261-1.187 3.26-1.187v-.109L3.876 9.62l-.307-.112 3.26-1.188v.877l.079-.055V6.769l3.257 1.185.058-.061L7.084 6.75l-.102-.037 3.24-1.179v-.083L6.854 6.677v.018l-.025.018v1.523L3.44 9.47v.02l-.025.017v4.007l-3.39 1.233v.019L0 14.784v3.995l.025.037 3.4 1.237.008-.006.007.01 3.4 1.238.008-.006.006.01 3.4 1.237.014-.009.012.01 3.45-1.256.026-.037-.078-.027zM3.493 9.563l3.257 1.185-3.257 1.187V9.562zM3.4 19.96L.078 18.752v-3.913l2.361.86.96.349v3.913zm.015-3.99L.335 14.85l-.182-.066 3.262-1.187v2.374zm3.399 5.231l-3.321-1.209v-3.912l3.321 1.209v3.912zM23.791 5.434l-3.21-1.17v2.338zM20.387 2.643l-3.24-1.18-3.27 1.19 3.247 1.182z",
    "python": "M11.858 0c-.978.005-1.913.088-2.736.234C6.7.662 6.26 1.558 6.26 3.21v2.182h5.725v.727H4.111c-1.664 0-3.121 1-3.577 2.903-.526 2.181-.549 3.542 0 5.82.407 1.694 1.379 2.902 3.043 2.902h1.969v-2.616c0-1.89 1.635-3.557 3.576-3.557h5.72c1.591 0 2.862-1.31 2.862-2.91v-5.45c0-1.553-1.309-2.718-2.863-2.977A18 18 0 0 0 11.858 0M8.762 1.755c.591 0 1.074.491 1.074 1.095 0 .601-.483 1.087-1.074 1.087A1.08 1.08 0 0 1 7.688 2.85c0-.604.48-1.095 1.074-1.095m9.656 4.364v2.543c0 1.971-1.671 3.63-3.577 3.63H9.122c-1.566 0-2.862 1.34-2.862 2.91v5.452c0 1.551 1.349 2.464 2.862 2.91 1.813.532 3.55.628 5.72 0 1.44-.418 2.862-1.258 2.862-2.91V18.47h-5.719v-.727h8.582c1.664 0 2.284-1.16 2.862-2.903.598-1.793.573-3.518 0-5.819-.41-1.656-1.196-2.903-2.862-2.903zm-3.216 13.807a1.08 1.08 0 0 1 1.074 1.088c0 .604-.48 1.094-1.074 1.094-.592 0-1.075-.49-1.075-1.094 0-.601.483-1.088 1.075-1.088",
    "zotero": "M21.231 2.462 7.18 20.923h14.564V24H2.256v-2.462L16.308 3.076H2.975V0h18.256v2.462z",
}

FONTS: dict[str, TTFont] = {}


def _font_dir() -> Path:
    for d in [os.environ.get("IBM_PLEX_DIR"), Path.home() / "Library/Fonts", Path.home() / ".local/share/fonts"]:
        if d and (Path(d) / "IBMPlexSans-Regular.otf").exists():
            return Path(d)
    raise SystemExit("IBM Plex Sans not found; set IBM_PLEX_DIR")


def font(weight: str) -> TTFont:
    if weight not in FONTS:
        FONTS[weight] = TTFont(_font_dir() / f"IBMPlexSans-{weight}.otf")
    return FONTS[weight]


def text_width(text: str, weight: str, size: float, tracking: float = 0) -> float:
    f = font(weight)
    cmap, hmtx, upm = f.getBestCmap(), f["hmtx"], f["head"].unitsPerEm
    return sum(hmtx[cmap[ord(ch)]][0] for ch in text) * size / upm + tracking * (len(text) - 1)


def text_path(text: str, weight: str, size: float, x: float, baseline: float, tracking: float = 0) -> str:
    """SVG path data for ``text`` whose baseline starts at (x, baseline)."""
    f = font(weight)
    glyphs, cmap, hmtx = f.getGlyphSet(), f.getBestCmap(), f["hmtx"]
    scale = size / f["head"].unitsPerEm
    pen = SVGPathPen(glyphs)
    for ch in text:
        name = cmap[ord(ch)]
        glyphs[name].draw(TransformPen(pen, (scale, 0, 0, -scale, x, baseline)))
        x += hmtx[name][0] * scale + tracking
    return pen.getCommands()


def _eye() -> str:
    """The logo without its square background, coloured by CSS class."""
    svg = (ASSETS / "logo.svg").read_text()
    body = svg[svg.index("<path"):svg.rindex("</svg>")]
    return body.replace('stroke="#76ffe6"', 'class="accent-stroke"').replace('fill="#76ffe6"', 'class="accent"')


def banner() -> str:
    W, H = 1280, 340
    name, tag_a, tag_b, tag_c = "zorsch", "A research copilot for your ", "Zotero", " library, from the terminal or any coding agent"
    name_size, name_track, logo, gap = 112, -3, 132, 30
    row_w = logo + gap + text_width(name, "SemiBold", name_size, name_track)
    x0 = (W - row_w) / 2
    base, tag_size, tag_base = 192, 29, 268
    wa, wb, wc = (text_width(tag_a, "Regular", tag_size), text_width(tag_b, "Medium", tag_size),
                  text_width(tag_c, "Regular", tag_size))
    tx = (W - wa - wb - wc) / 2
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="zorsch: a research copilot for your Zotero library">
<style>
.bg{{fill:#f5f8fb}} .b1{{stop-color:#d8e8f4}} .b2{{stop-color:#d3f1ea}} .dot{{fill:#0a1828;fill-opacity:.07}}
.accent{{fill:#0e9b87}} .accent-stroke{{stroke:#0e9b87}} .title{{fill:#0a1828}} .tag{{fill:#4b5f73}} .glow{{flood-color:#0e9b87;flood-opacity:.18}}
@media (prefers-color-scheme: dark) {{
.bg{{fill:#0a1828}} .b1{{stop-color:#163a55}} .b2{{stop-color:#0f3b3c}} .dot{{fill:#76ffe6;fill-opacity:.10}}
.accent{{fill:#76ffe6}} .accent-stroke{{stroke:#76ffe6}} .title{{fill:#ffffff}} .tag{{fill:#a9bdd1}} .glow{{flood-color:#76ffe6;flood-opacity:.35}}
}}
</style>
<defs>
<clipPath id="r"><rect width="{W}" height="{H}" rx="24"/></clipPath>
<radialGradient id="g1" cx="22%" cy="30%" r="60%"><stop offset="0" class="b1"/><stop offset="1" class="b1" stop-opacity="0"/></radialGradient>
<radialGradient id="g2" cx="85%" cy="95%" r="50%"><stop offset="0" class="b2"/><stop offset="1" class="b2" stop-opacity="0"/></radialGradient>
<pattern id="dots" width="22" height="22" patternUnits="userSpaceOnUse"><circle cx="11" cy="11" r="1.1" class="dot"/></pattern>
<linearGradient id="fade"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".25" stop-color="#fff"/><stop offset=".75" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
<mask id="m"><rect width="{W}" height="{H}" fill="url(#fade)"/></mask>
<filter id="glow" x="-30%" y="-30%" width="160%" height="160%"><feDropShadow dx="0" dy="0" stdDeviation="9" class="glow"/></filter>
</defs>
<g clip-path="url(#r)">
<rect width="{W}" height="{H}" class="bg"/>
<rect width="{W}" height="{H}" fill="url(#g1)"/>
<rect width="{W}" height="{H}" fill="url(#g2)"/>
<rect width="{W}" height="{H}" fill="url(#dots)" mask="url(#m)"/>
<g transform="translate({x0:.1f} {base - 42 - logo / 2:.1f}) scale({logo / 256:.4f})" filter="url(#glow)">{_eye()}</g>
<path class="title" d="{text_path(name, 'SemiBold', name_size, x0 + logo + gap, base, name_track)}"/>
<path class="tag" d="{text_path(tag_a, 'Regular', tag_size, tx, tag_base)}"/>
<path class="accent" d="{text_path(tag_b, 'Medium', tag_size, tx + wa, tag_base)}"/>
<path class="tag" d="{text_path(tag_c, 'Regular', tag_size, tx + wa + wb, tag_base)}"/>
</g>
</svg>
"""


def badge(label: str, value: str, icon: str | None = None, value_class: str = "v") -> str:
    H, size, pad, icon_s, track = 28, 12.5, 10, 14, 0.3
    lead = icon_s + 6 if icon else 0
    lw = pad + lead + text_width(label, "Medium", size, track) + pad
    vw = pad + text_width(value, "SemiBold", size, track) + pad
    base = H / 2 + size * 0.36
    ico = (f'<path class="lt" transform="translate({pad} {(H - icon_s) / 2}) scale({icon_s / 24})" d="{ICONS[icon]}"/>'
           if icon else "")
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {lw + vw:.1f} {H}" width="{lw + vw:.1f}" height="{H}" role="img" aria-label="{label}: {value}">
<style>
.l{{fill:#e7edf2}} .lt{{fill:#0a1828}} .v{{fill:#163a55}} .z{{fill:#cc2936}} .vt{{fill:#ffffff}}
@media (prefers-color-scheme: dark) {{ .l{{fill:#0a1828}} .lt{{fill:#e6edf3}} }}
</style>
<clipPath id="c"><rect width="{lw + vw:.1f}" height="{H}" rx="5"/></clipPath>
<g clip-path="url(#c)"><rect width="{lw:.1f}" height="{H}" class="l"/><rect x="{lw:.1f}" width="{vw:.1f}" height="{H}" class="{value_class}"/></g>
{ico}<path class="lt" d="{text_path(label, 'Medium', size, pad + lead, base, track)}"/>
<path class="vt" d="{text_path(value, 'SemiBold', size, lw + pad, base, track)}"/>
</svg>
"""


def main() -> None:
    meta = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    pythons = [c.rsplit("::", 1)[1].strip() for c in meta.get("classifiers", [])
               if c.startswith("Programming Language :: Python :: 3.")]
    (ASSETS / "badges").mkdir(exist_ok=True)
    (ASSETS / "banner.svg").write_text(banner())
    badges = {
        "pypi": badge("PyPI", meta["version"], "pypi"),
        "python": badge("Python", " | ".join(pythons), "python"),
        "zotero": badge("works with", "Zotero", "zotero", "z"),
        "license": badge("license", meta["license"]),
    }
    for name, svg in badges.items():
        (ASSETS / "badges" / f"{name}.svg").write_text(svg)
    print("wrote assets/banner.svg and assets/badges/{" + ",".join(badges) + "}.svg")


if __name__ == "__main__":
    main()
