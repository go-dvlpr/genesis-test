"""Deterministic descriptive analysis, with explicit missingness and no causal claims."""

from __future__ import annotations

import calendar
import re
import statistics
from datetime import UTC, date, datetime

from .client import ResearchError


def month_date(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}", value):
        raise ResearchError("Month must be YYYY-MM")
    try:
        return date.fromisoformat(value + "-01")
    except ValueError as exc:
        raise ResearchError(f"Invalid month: {value}") from exc


def shift_month(value, offset):
    d = month_date(value)
    number = d.year * 12 + d.month - 1 + offset
    return f"{number // 12:04d}-{number % 12 + 1:02d}"


def last_closed_month():
    return shift_month(datetime.now(UTC).strftime("%Y-%m"), -1)


def months_between(start, end):
    a, b = month_date(start), month_date(end)
    count = (b.year - a.year) * 12 + b.month - a.month + 1
    if not 1 <= count <= 120 or start < "2015-07" or end > last_closed_month():
        raise ResearchError(
            "Use 1-120 complete months, from 2015-07 through the last closed UTC month"
        )
    return [shift_month(start, i) for i in range(count)]


def days(month):
    d = month_date(month)
    return calendar.monthrange(d.year, d.month)[1]


def growth(before, after):
    # Stabilize threshold comparisons and zero direction against floating-point noise.
    return round(100 * (after - before) / before, 10) if before > 0 else None


def direction(value):
    if value is None:
        return None
    return 1 if value > 0 else -1 if value < 0 else 0


def paired_summary(months, views, totals, min_views=1000, threshold=10.0):
    """Compare the latest 12 calendar months with their exact year-earlier counterparts."""
    result = {
        "status": "insufficient_data",
        "coverage": sum(v is not None for v in views) / len(months),
        "warnings": [],
        "yoy_pct": None,
        "share_yoy_pct": None,
        "baseline_views": None,
        "recent_views": None,
        "recent_share_per_million": None,
        "paired_positive_months": None,
        "loo_yoy_range": None,
        "loo_share_yoy_range": None,
        "median_daily_yoy_pct": None,
        "recent_peak_month_fraction": None,
    }
    if len(months) < 24:
        result["warnings"].append("Fewer than 24 months: two complete annual windows are required.")
        return result
    before, after = views[-24:-12], views[-12:]
    old_totals, new_totals = totals[-24:-12], totals[-12:]
    if any(v is None for v in before + after):
        result["warnings"].append(
            "Missing article months; missing observations are never treated as zero."
        )
        return result
    baseline, recent = sum(before), sum(after)
    result.update(baseline_views=baseline, recent_views=recent, yoy_pct=growth(baseline, recent))
    if baseline == 0:
        result["warnings"].append("Zero baseline: percentage growth is undefined.")
        return result
    if recent == 0:
        result["warnings"].append(
            "Recent annual views are zero; verify title and measurement changes."
        )
    if any(v is None or v <= 0 for v in old_totals + new_totals):
        result["warnings"].append(
            "Project traffic is missing or zero; normalized comparison is unavailable."
        )
        return result
    old_share = baseline / sum(old_totals)
    new_share = recent / sum(new_totals)
    result["share_yoy_pct"] = growth(old_share, new_share)
    result["recent_share_per_million"] = new_share * 1_000_000
    paired = [
        growth(a / days(m1), b / days(m2))
        for a, b, m1, m2 in zip(before, after, months[-24:-12], months[-12:], strict=True)
    ]
    valid_pairs = [v for v in paired if v is not None]
    result["paired_positive_months"] = sum(v > 0 for v in valid_pairs)
    result["paired_defined_months"] = len(valid_pairs)
    result["median_daily_yoy_pct"] = statistics.median(valid_pairs) if valid_pairs else None
    raw_loo, share_loo = [], []
    for i in range(12):
        old, new = baseline - before[i], recent - after[i]
        if old > 0:
            raw_loo.append(growth(old, new))
            share_loo.append(
                growth(
                    old / (sum(old_totals) - old_totals[i]), new / (sum(new_totals) - new_totals[i])
                )
            )
    if raw_loo:
        result["loo_yoy_range"] = [min(raw_loo), max(raw_loo)]
        result["loo_share_yoy_range"] = [min(share_loo), max(share_loo)]
    result["recent_peak_month_fraction"] = max(after) / recent if recent else None
    fragile = (
        len(raw_loo) < 12
        or any(direction(v) != direction(result["yoy_pct"]) for v in raw_loo)
        or any(direction(v) != direction(result["share_yoy_pct"]) for v in share_loo)
    )
    if fragile:
        result["warnings"].append(
            "Growth direction changes when one matched month pair is removed."
        )
    if result["recent_peak_month_fraction"] and result["recent_peak_month_fraction"] > 0.25:
        result["warnings"].append(
            "One month contributes over 25% of recent annual views; inspect seasonality or a spike."
        )
    if min(baseline, recent) < min_views:
        result["status"] = "low_volume"
        result["warnings"].append(
            f"Annual volume below the explicit {min_views}-view screening threshold."
        )
    elif fragile:
        result["status"] = "sensitive"
    elif (
        result["yoy_pct"] >= threshold
        and result["share_yoy_pct"] >= threshold
        and result["paired_positive_months"] >= 9
    ):
        result["status"] = "consistent_growth"
    elif (
        result["yoy_pct"] <= -threshold
        and result["share_yoy_pct"] <= -threshold
        and len(valid_pairs) == 12
        and result["paired_positive_months"] <= 3
    ):
        result["status"] = "consistent_decline"
    else:
        result["status"] = "mixed_or_flat"
    return result
