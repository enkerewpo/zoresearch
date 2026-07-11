from zoresearch.import_ import ResolvedTarget, _shallow_to_zotero_item


def test_doi_import_preserves_resolved_title():
    target = ResolvedTarget(
        kind="doi",
        doi="10.1109/LRA.2025.3606350",
        url="https://doi.org/10.1109/LRA.2025.3606350",
    )

    item = _shallow_to_zotero_item(
        {"title": "Resolved DOI Title", "authors": [], "year": 2025},
        target,
    )

    assert item["title"] == "Resolved DOI Title"


def test_missing_doi_title_falls_back_to_untitled():
    target = ResolvedTarget(
        kind="doi",
        doi="10.0000/example",
        url="https://doi.org/10.0000/example",
    )

    item = _shallow_to_zotero_item({}, target)

    assert item["title"] == "Untitled"
