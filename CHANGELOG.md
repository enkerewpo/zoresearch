# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.1] - 2026-11-19

### Changed

- README: the logo, name, tagline and badges are centred at the top, and the
  install section walks through prerequisites, installing, `zr doctor`, the
  optional MinerU token, where files go, and upgrading.

### Fixed

- The logo on the PyPI project page. The README referred to it by a relative
  path, which PyPI cannot resolve; it now uses the raw GitHub URL.

## [0.2.0] - 2026-11-19

First release on PyPI, published as `zorsch`.

### Added

- `zr import <file.ris>` adds hand-written records, each with the local PDF
  its `L1` field points to. It covers papers with no DOI or arXiv record, such
  as submissions under review.
- `zr import` accepts Journal of Software (JOS) article pages and takes the
  metadata and PDF from the journal site.
- `zr web`: a browser reader for workspaces with KaTeX math, syntax
  highlighting and Zotero citation links, which renders `format: slides`
  documents as 16:9 slide decks; later a workspace switcher, a folder tree and
  embedded viewers.
- `AGENTS.md` and `.agents/skills/`, so coding agents other than Claude Code
  find the instructions and skills. `CLAUDE.md` imports `AGENTS.md` and
  `.claude/skills` links to the shared directory.
- `zr import --collection` files the new item into a named collection.
- `ZORESEARCH_HOME` sets where `data/` and `workspace/` live.
- A `LICENSE` file (MIT, as the metadata already declared) and a GitHub
  Actions workflow that publishes tagged releases through PyPI trusted
  publishing.

### Changed

- The PyPI package is named `zorsch`, because `zoresearch` and `zr` are taken
  there. The command is still `zr` and the Python module is still `zoresearch`.
- Installed from PyPI, `data/` and `workspace/` go to the per-user data
  directory (on macOS `~/Library/Application Support/zorsch`). A source
  checkout keeps them in the repository as before.
- Command help, status messages, the web reader and the docs use plain
  wording.
- The web reader sets body text in Source Serif 4 and CJK text in Noto Sans
  CJK SC.

### Removed

- The cosmetic command aliases `compendium`, `stable`, `sensor`, `memory`,
  `shrine` and `map`; use `lib`, `ws`, `related`, `notes`, `parse` and `web`.
- The startup banner.
- The `zoresearch` console script; the command is `zr`.

### Fixed

- `--collection` no longer reports a collection as missing when it was created
  while Zotero is running. The lookup now reads a copy of the database
  together with its WAL instead of an immutable read that skipped the WAL.
- DOI imports keep the title resolved from OpenAlex instead of falling back to
  "Untitled".
- In `zr web`, a dollar amount followed by a digit no longer opens inline math
  and swallows the text up to the next `$`.
- `zr web` renders KaTeX math correctly and serves pages without caching, so a
  refresh shows the file on disk.

## [0.1.0] - 2026-04-30

### Added

- The `zr` command: `doctor`, `show`, `parse` (MinerU, or `pymupdf4llm` as the
  fallback), `annotations`, `related` and `trends` (OpenAlex), `import` (DOI,
  arXiv id or URL through the Zotero connector), `notes`,
  `lib` (`stats`, `search`, `list`, `collections`) and `ws` (`init`, `list`,
  `add`, `show`, `parse`, `related`).
- Agent skills that compose these commands.

[Unreleased]: https://github.com/enkerewpo/zoresearch/compare/v0.2.1...HEAD
[0.2.1]: https://github.com/enkerewpo/zoresearch/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/enkerewpo/zoresearch/compare/40f298b...v0.2.0
[0.1.0]: https://github.com/enkerewpo/zoresearch/commit/40f298b
