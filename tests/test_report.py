import json

import pytest
from conftest import reseal
from pypdf import PdfReader
from wiki_interest.cli import ensure_new_output, verify
from wiki_interest.client import ResearchError
from wiki_interest.report import export
from wiki_interest.research import analyze


def test_end_to_end_artifacts_and_independent_replay(tmp_path, synthetic_snapshot, monkeypatch):
    monkeypatch.setattr(
        "urllib.request.OpenerDirector.open",
        lambda *a, **kw: pytest.fail("Replay must not use HTTP"),
    )
    result = analyze(synthetic_snapshot)
    export(result, synthetic_snapshot, tmp_path)
    assert verify(tmp_path)["verified"] is True
    pdf = PdfReader(tmp_path / "report.pdf")
    assert len(pdf.pages) == 1
    text = pdf.pages[0].extract_text()
    assert "Астрономія" in text
    assert "+20.0%" in text
    assert "not customers" in text
    analysis = json.loads((tmp_path / "analysis.json").read_text())
    assert analysis == result
    assert len((tmp_path / "monthly.csv").read_text().splitlines()) == 25


def test_existing_evidence_cannot_be_overwritten(tmp_path):
    (tmp_path / "snapshot.json").write_text("prior evidence")
    with pytest.raises(ResearchError, match="empty or new"):
        ensure_new_output(tmp_path)


def test_report_tampering_detected(tmp_path, synthetic_snapshot):
    export(analyze(synthetic_snapshot), synthetic_snapshot, tmp_path)
    (tmp_path / "report.md").write_text("False claim")
    with pytest.raises(ResearchError, match="report.md"):
        verify(tmp_path)


def test_markup_in_topic_is_text_not_pdf_markup(tmp_path, synthetic_snapshot):
    synthetic_snapshot["plan"]["topic"] = "Astronomy <script> & space"
    reseal(synthetic_snapshot)
    export(analyze(synthetic_snapshot), synthetic_snapshot, tmp_path)
    assert "<script> & space" in PdfReader(tmp_path / "report.pdf").pages[0].extract_text()


@pytest.mark.parametrize(
    "language,expected", [("uk", "ДОСЛІДНИЦЬКИЙ ЗВІТ"), ("ru", "ИССЛЕДОВАТЕЛЬСКИЙ ОТЧЁТ")]
)
def test_localized_brief(tmp_path, synthetic_snapshot, language, expected):
    synthetic_snapshot["plan"]["report_language"] = language
    reseal(synthetic_snapshot)
    export(analyze(synthetic_snapshot), synthetic_snapshot, tmp_path)
    pdf = PdfReader(tmp_path / "report.pdf")
    assert len(pdf.pages) == 1
    assert expected in pdf.pages[0].extract_text()


def test_six_language_brief_fits_one_page(tmp_path, synthetic_snapshot):
    import copy

    synthetic_snapshot["plan"]["report_language"] = "uk"
    reseal(synthetic_snapshot)
    result = analyze(synthetic_snapshot)
    original = result["rows"][0]
    result["rows"] = []
    for language in ["uk", "pl", "cs", "de", "es", "fi"]:
        row = copy.deepcopy(original)
        row["language"] = language
        result["rows"].append(row)
    export(result, synthetic_snapshot, tmp_path)
    pdf = PdfReader(tmp_path / "report.pdf")
    assert len(pdf.pages) == 1
    assert "Точні джерела" in pdf.pages[0].extract_text()
