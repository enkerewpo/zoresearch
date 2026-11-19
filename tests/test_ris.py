from pathlib import Path

from zoresearch.import_ import parse_ris


def test_parse_ris_maps_fields_and_local_pdf(tmp_path: Path):
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    ris = tmp_path / "x.ris"
    ris.write_text(
        "TY  - MANSCPT\nTI  - A Title\nT2  - AAAI 2027 Conference Submission\nDA  - 2026/07/22\n"
        "AU  - Ren, Hangqi\nAU  - Han, Yulong\nN1  - Under review.\nKW  - under review\n"
        f"L1  - file://{pdf}\nER  - \n"
        "TY  - JOUR\nTI  - B\nT2  - Sci China Inf Sci\nVL  - 69\nDO  - 10.1/x\nPY  - 2026\nER  - \n",
        encoding="utf-8",
    )
    (a, a_pdf), (b, b_pdf) = parse_ris(ris)
    assert a["itemType"] == "manuscript" and a["manuscriptType"] == "AAAI 2027 Conference Submission"
    assert a["date"] == "2026-07-22" and a["extra"] == "Under review."
    assert a["creators"][1] == {"creatorType": "author", "lastName": "Han", "firstName": "Yulong"}
    assert a["tags"] == [{"tag": "under review"}] and a_pdf == pdf
    assert b["itemType"] == "journalArticle" and b["DOI"] == "10.1/x" and b["volume"] == "69" and b_pdf is None
