"""Independent Decimal check of example annual metrics, without importing analysis code.

Run from the skill directory: uv run --locked python evaluations/check_examples.py
"""

import json
from decimal import Decimal
from pathlib import Path

from pypdf import PdfReader


def check(root):
    checked = []
    for directory in sorted((root / "examples").iterdir()):
        snapshot = json.loads((directory / "snapshot.json").read_text())
        result = json.loads((directory / "analysis.json").read_text())
        final_months = result["months"][-24:]
        for row in result["rows"]:
            language = row["language"]
            article_values = {}
            project_values = {}
            for source in snapshot["sources"]:
                for item in source["data"]["items"]:
                    if item["project"] != f"{language}.wikipedia":
                        continue
                    timestamp = item["timestamp"]
                    month = timestamp[:4] + "-" + timestamp[4:6]
                    if month not in final_months:
                        continue
                    if "/aggregate/" in source["url"]:
                        project_values[month] = Decimal(item["views"])
                    else:
                        key = (month, item["article"])
                        assert key not in article_values, "Duplicate monthly raw observation"
                        article_values[key] = Decimal(item["views"])
            article_count = len(row["articles"])
            if len(article_values) != 24 * article_count:
                assert row["metrics"]["status"] == "insufficient_data"
                checked.append({"example": directory.name, "language": language, "missing": True})
                continue
            before = sum(v for (m, _), v in article_values.items() if m in final_months[:12])
            after = sum(v for (m, _), v in article_values.items() if m in final_months[12:])
            project_before = sum(project_values[m] for m in final_months[:12])
            project_after = sum(project_values[m] for m in final_months[12:])
            raw = (after / before - 1) * 100
            share = ((after / project_after) / (before / project_before) - 1) * 100
            metrics = row["metrics"]
            assert int(before) == metrics["baseline_views"]
            assert int(after) == metrics["recent_views"]
            assert abs(raw - Decimal(str(metrics["yoy_pct"]))) < Decimal("0.00000001")
            assert abs(share - Decimal(str(metrics["share_yoy_pct"]))) < Decimal("0.00000001")
            checked.append(
                {
                    "example": directory.name,
                    "language": language,
                    "baseline": int(before),
                    "recent": int(after),
                    "verified": True,
                }
            )
        pdf = PdfReader(directory / "report.pdf")
        assert len(pdf.pages) == 1
        assert "ДОСЛІДНИЦЬКИЙ ЗВІТ" in pdf.pages[0].extract_text()
    return {"independent_decimal_checks": checked, "all_pdfs_one_page": True}


if __name__ == "__main__":
    print(json.dumps(check(Path(__file__).resolve().parents[1]), indent=2, ensure_ascii=False))
