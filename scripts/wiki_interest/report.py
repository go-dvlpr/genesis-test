"""Portable one-page PDF, chart and machine-readable evidence exports."""

from __future__ import annotations

import csv
import hashlib
import io
from pathlib import Path
from xml.sax.saxutils import escape

from .client import write_json
from .language import STATUS_KEYS, brief_recommendation, brief_text

STATUS = {
    "consistent_growth": "Consistent growth",
    "consistent_decline": "Consistent decline",
    "mixed_or_flat": "Mixed / flat",
    "sensitive": "Sensitive to a month",
    "low_volume": "Low volume",
    "insufficient_data": "Insufficient data",
}
COLORS = ["#087F8C", "#E16B3B", "#7161B5", "#3575A6", "#8A7227", "#B54572"]


def percent(value):
    return "n/a" if value is None else f"{value:+.1f}%"


def number(value):
    return "n/a" if value is None else f"{value:,.0f}"


def interval(value):
    return "n/a" if value is None else f"{percent(value[0])} to {percent(value[1])}"


def recommendation(result):
    return brief_recommendation(dict(result, report_language="en"))


def chart(result, path):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from .analysis import days

    with plt.rc_context(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.spines.left": False,
            "axes.spines.bottom": False,
            "axes.titleweight": "bold",
        }
    ):
        fig, axes = plt.subplots(1, 2, figsize=(10.8, 3.6), layout="constrained")
        x = list(range(len(result["months"])))
        for i, row in enumerate(result["rows"]):
            daily = [
                v / days(m) if v is not None else float("nan")
                for v, m in zip(row["views"], result["months"], strict=True)
            ]
            shares = [v if v is not None else float("nan") for v in row["share_per_million"]]
            axes[0].plot(x, daily, label=row["language"], color=COLORS[i], linewidth=1.8)
            axes[1].plot(x, shares, label=row["language"], color=COLORS[i], linewidth=1.8)
        titles = brief_text(result)["chart_titles"]
        labels = brief_text(result)["chart_labels"]
        step = max(1, (len(x) - 1 + 3) // 4)
        ticks = sorted(set([*range(0, len(x), step), len(x) - 1]))
        for ax, title, label in zip(axes, titles, labels, strict=True):
            ax.set_title(title, loc="left", pad=16)
            ax.set_ylabel(label)
            ax.set_xticks(ticks, [result["months"][v] for v in ticks], rotation=25, ha="right")
            ax.set_ylim(bottom=0)
            ax.grid(axis="y", color="#E3E9EB", linewidth=0.7)
            ax.legend(frameon=False, ncol=min(3, len(result["rows"])), fontsize=8, loc="best")
        fig.savefig(path, dpi=180, facecolor="white")
        plt.close(fig)


def markdown(result, snapshot):
    plan = snapshot["plan"]
    lines = [
        f"# Wikipedia interest: {result['topic']}",
        "",
        f"Period: {plan['start']} through {plan['end']} (complete UTC months).",
        f"Source retrieval: {snapshot['fetched_at']}. Measurement: user / all-access / monthly.",
        "",
        recommendation(result),
        "",
        "| Language | Recent annual views | Annual change | Traffic-share change | Signal |",
        "|---|---:|---:|---:|---|",
    ]
    for row in result["rows"]:
        m = row["metrics"]
        lines.append(
            f"| {row['language']} | {number(m['recent_views'])} | {percent(m['yoy_pct'])} | {percent(m['share_yoy_pct'])} | {STATUS[m['status']]} |"
        )
    lines += [
        "",
        "Annual changes compare the latest 12 months with the preceding 12 calendar months. Longer histories are plotted, but do not change this comparison window.",
        "",
        f"Screen: both raw and share growth >= {result['criteria']['growth_threshold_pct']:g}%; >=9 positive matched months; each annual window >= {result['criteria']['min_annual_views']} views; direction survives every leave-one-pair-out check.",
        "The shortlist orders qualifying languages by traffic-share growth, then recent views. This is a transparent research heuristic, not an estimate of commercial value.",
        "",
    ]
    for row in result["rows"]:
        m = row["metrics"]
        lines += [
            f"## {row['language']}",
            "",
            f"Observed article-month coverage: {m['coverage']:.1%}.",
            f"Raw growth after excluding each matched month pair: {interval(m['loo_yoy_range'])}.",
            f"Share growth after the same exclusions: {interval(m['loo_share_yoy_range'])}.",
            f"Median matched daily-rate growth: {percent(m['median_daily_yoy_pct'])}.",
        ]
        for warning in m["warnings"]:
            lines.append(f"- {warning}")
        lines += ["", "Articles:"]
        for article in row["articles"]:
            if article["title"]:
                title = article["title"].replace("[", "\\[").replace("]", "\\]")
                lines.append(
                    f"- [{title}]({article['url']}) / [{article['qid']}](https://www.wikidata.org/wiki/{article['qid']}): annual change {percent(article['metrics']['yoy_pct'])}; revision {article['revision_id']} at resolution."
                )
            else:
                lines.append(
                    f"- {article['qid']}: missing sitelink; not substituted with a different topic."
                )
        lines.append("")
    lines += [
        "## Interpretation limits",
        "",
        *[f"- {v}" for v in result["limitations"]],
        "",
        "## Reproducibility",
        "",
        "`snapshot.json` contains the plan and original API response bodies. `sources.json` records exact URLs, retrieval times and content hashes. `monthly.csv` and `analysis.json` expose the calculations. `manifest.json` hashes all delivered report files.",
        "Run `verify --directory <report-dir>` to independently replay the arithmetic and check file integrity. Hashes detect accidental edits, not malicious replacement of both data and hashes.",
        "",
        "[Pageview API](https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/reference/page-views.html) | [Pageview definitions and redirects](https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/concepts/page-views.html)",
        "",
    ]
    return "\n".join(lines)


def pdf(result, snapshot, path, chart_path):
    import matplotlib
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas
    from reportlab.platypus import Paragraph

    font_dir = Path(matplotlib.get_data_path()) / "fonts/ttf"
    for name, filename in [("DejaVu", "DejaVuSans.ttf"), ("DejaVu-Bold", "DejaVuSans-Bold.ttf")]:
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name, str(font_dir / filename)))
    c = canvas.Canvas(str(path), pagesize=(595.28, 841.89), invariant=1)
    c.setTitle(f"Wikipedia interest: {result['topic']}")
    c.setAuthor("Wiki Interest")
    width = 515.28
    language = brief_text(result)
    statuses = dict(zip(STATUS_KEYS, language["statuses"], strict=True))

    def paragraph(text, x, top, size=9, leading=13, color="#233D48", bold=False, max_height=None):
        style = ParagraphStyle(
            "text",
            fontName="DejaVu-Bold" if bold else "DejaVu",
            fontSize=size,
            leading=leading,
            textColor=colors.HexColor(color),
        )
        p = Paragraph(escape(text), style)
        _, height = p.wrap(width if x == 40 else 490, 800)
        if max_height is not None and height > max_height:
            if size <= 7:
                raise ValueError("Text cannot fit the one-page brief")
            return paragraph(text, x, top, size - 0.5, leading - 0.5, color, bold, max_height)
        p.drawOn(c, x, top - height)
        return top - height

    c.setFillColor(colors.HexColor("#F2F7F7"))
    c.rect(0, 700, 595.28, 141.89, fill=1, stroke=0)
    paragraph(language["badge"], 40, 806, 8, 11, "#087F8C", True)
    paragraph(result["topic"], 40, 779, 20, 25, "#183844", True, max_height=55)
    paragraph(
        f"{result['months'][0]} - {result['months'][-1]}  |  {language['period']}  |  user / all-access",
        40,
        714,
        8,
        11,
    )
    paragraph(brief_recommendation(result), 40, 680, 9.5, 14, max_height=60)
    c.drawImage(
        str(chart_path), 34, 434, width=527, height=175.67, preserveAspectRatio=True, mask="auto"
    )
    y = 414
    headings = list(zip([40, 89, 181, 270, 372], language["headings"], strict=True))
    c.setFillColor(colors.HexColor("#087F8C"))
    c.setFont("DejaVu-Bold", 8)
    for x, value in headings:
        c.drawString(x, y, value)
    for row in result["rows"]:
        y -= 23
        m = row["metrics"]
        c.setStrokeColor(colors.HexColor("#E2E9EB"))
        c.line(40, y - 8, 555, y - 8)
        c.setFillColor(colors.HexColor("#233D48"))
        c.setFont("DejaVu", 8.5)
        values = [
            row["language"],
            number(m["recent_views"]),
            percent(m["yoy_pct"]),
            percent(m["share_yoy_pct"]),
            statuses[m["status"]],
        ]
        for (x, _), value in zip(headings, values, strict=True):
            c.drawString(x, y, value)
    y -= 27
    text = language["criteria"].format(
        threshold=f"{result['criteria']['growth_threshold_pct']:g}",
        volume=result["criteria"]["min_annual_views"],
    )
    y = paragraph(text, 40, y, 7.5, 10.5) - 13
    ranges = []
    for row in result["rows"]:
        value = row["metrics"]["loo_yoy_range"]
        bounds = "n/a" if value is None else f"{percent(value[0])} .. {percent(value[1])}"
        ranges.append(f"{row['language']}: {bounds}")
    y = paragraph(language["sensitivity"] + ": " + "; ".join(ranges), 40, y, 7.5, 10.5) - 12
    titles = []
    for row in result["rows"]:
        if len(row["articles"]) == 1:
            a = row["articles"][0]
            label = a["title"] or language["missing"]
            if len(label) > 70:
                label = label[:67] + "..."
            titles.append(f"{row['language']}: {label} ({a['qid']})")
        else:
            titles.append(
                f"{row['language']}: " + language["basket"].format(count=len(row["articles"]))
            )
    if len(result["rows"]) > 3:
        titles = [
            ", ".join(t["qid"] for t in snapshot["plan"]["topics"]),
            language["basket"].format(count=len(snapshot["plan"]["topics"])),
        ]
    y = paragraph(language["scope"] + ": " + "; ".join(titles), 40, y, 7.5, 10.5) - 12
    caveat = language["caveat"]
    y = paragraph(caveat, 40, y, 7.5, 10.5)
    if y < 65:
        raise ValueError("Report content exceeds one-page layout; shorten topic or scope")
    c.setStrokeColor(colors.HexColor("#AABFC4"))
    c.line(40, 57, 555, 57)
    paragraph(
        language["source"].format(date=snapshot["fetched_at"][:10]),
        40,
        46,
        7,
        10,
    )
    c.linkURL(
        "https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/reference/page-views.html",
        (40, 31, 555, 50),
        relative=0,
    )
    c.showPage()
    c.save()


def export(result, snapshot, output):
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "snapshot.json", snapshot)
    write_json(output / "analysis.json", result)
    all_sources = snapshot["plan"].get("resolution_sources", []) + snapshot["sources"]
    write_json(
        output / "sources.json",
        [{k: v for k, v in source.items() if k != "data"} for source in all_sources],
    )
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(
        [
            "language",
            "month",
            "article_views",
            "project_views",
            "article_views_per_million_project_views",
        ]
    )
    for row in result["rows"]:
        writer.writerows(
            zip(
                [row["language"]] * len(result["months"]),
                result["months"],
                row["views"],
                row["project_views"],
                row["share_per_million"],
                strict=True,
            )
        )
    (output / "monthly.csv").write_text(stream.getvalue(), encoding="utf-8")
    (output / "report.md").write_text(markdown(result, snapshot), encoding="utf-8")
    chart(result, output / "chart.png")
    pdf(result, snapshot, output / "report.pdf", output / "chart.png")
    paths = [
        "snapshot.json",
        "analysis.json",
        "sources.json",
        "monthly.csv",
        "report.md",
        "chart.png",
        "report.pdf",
    ]
    write_json(
        output / "manifest.json",
        {name: hashlib.sha256((output / name).read_bytes()).hexdigest() for name in paths},
    )
