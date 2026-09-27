import pytest
from wiki_interest.analysis import (
    days,
    last_closed_month,
    months_between,
    paired_summary,
    shift_month,
)
from wiki_interest.client import ResearchError

MONTHS = months_between("2024-09", "2026-08")


def assess(views, totals=None, **kwargs):
    return paired_summary(MONTHS, views, totals or [1_000_000] * 24, **kwargs)


def test_real_growth_and_known_range():
    m = assess([100] * 12 + [120] * 12)
    assert m["yoy_pct"] == pytest.approx(20)
    assert m["share_yoy_pct"] == pytest.approx(20)
    assert m["recent_views"] == 1440
    assert m["recent_share_per_million"] == 120
    assert m["loo_yoy_range"] == pytest.approx([20, 20])
    assert m["status"] == "consistent_growth"


def test_exact_threshold_passes_without_floating_point_artifact():
    assert assess([100] * 12 + [120] * 12, threshold=20)["status"] == "consistent_growth"


def test_overall_wikipedia_growth_is_not_topic_share_growth():
    m = assess([100] * 12 + [200] * 12, [1_000_000] * 12 + [2_000_000] * 12)
    assert m["yoy_pct"] == 100
    assert m["share_yoy_pct"] == 0
    assert m["status"] == "mixed_or_flat"


def test_share_growth_does_not_hide_raw_decline():
    m = assess([200] * 12 + [100] * 12, [4_000_000] * 12 + [1_000_000] * 12)
    assert m["yoy_pct"] == -50
    assert m["share_yoy_pct"] == 100
    assert m["status"] == "mixed_or_flat"


def test_one_spike_does_not_pass_growth_screen():
    m = assess([100] * 12 + [100] * 11 + [2500])
    assert m["yoy_pct"] == 200
    assert m["loo_yoy_range"][0] == 0
    assert m["status"] == "sensitive"
    assert len(m["warnings"]) >= 2


def test_missing_is_not_zero():
    m = assess([100] * 23 + [None])
    assert m["status"] == "insufficient_data"
    assert m["yoy_pct"] is None
    assert m["coverage"] == 23 / 24


def test_zero_baseline_is_not_infinite_growth():
    m = assess([0] * 12 + [1000] * 12)
    assert m["yoy_pct"] is None
    assert m["status"] == "insufficient_data"


def test_zero_recent_is_observed_decline_and_warned():
    m = assess([1000] * 12 + [0] * 12)
    assert m["yoy_pct"] == -100
    assert m["recent_views"] == 0
    assert m["status"] == "low_volume"


def test_low_volume_prevents_strong_recommendation():
    assert assess([1] * 12 + [10] * 12)["status"] == "low_volume"


def test_missing_project_total_blocks_normalized_recommendation():
    m = assess([100] * 12 + [120] * 12, [1_000_000] * 23 + [None])
    assert m["yoy_pct"] == pytest.approx(20)
    assert m["share_yoy_pct"] is None
    assert m["status"] == "insufficient_data"


def test_short_series_has_no_annual_conclusion():
    m = paired_summary(MONTHS[:12], [1000] * 12, [1_000_000] * 12)
    assert m["yoy_pct"] is None


def test_equal_daily_rates_account_for_leap_year():
    months = months_between("2023-03", "2025-02")
    views = [days(m) * 100 for m in months]
    m = paired_summary(months, views, [1_000_000] * 24)
    assert m["median_daily_yoy_pct"] == 0
    assert m["paired_positive_months"] == 0


def test_share_uses_ratio_of_sums_not_mean_of_monthly_ratios():
    totals = [1000] * 24
    totals[-1] = 13000
    m = assess([100] * 24, totals)
    assert m["share_yoy_pct"] == -50
    assert m["recent_share_per_million"] == 50000


def test_latest_24_months_drive_metric_for_longer_chart():
    months = months_between("2023-09", "2026-08")
    m = paired_summary(months, [9000] * 12 + [100] * 12 + [120] * 12, [1_000_000] * 36)
    assert m["yoy_pct"] == pytest.approx(20)


@pytest.mark.parametrize(
    "start,end",
    [("2015-06", "2015-07"), ("2026-08", "2026-07"), ("2024-13", "2026-08"), ("2024-9", "2026-08")],
)
def test_bad_windows_fail(start, end):
    with pytest.raises(ResearchError):
        months_between(start, end)


def test_current_month_is_not_a_complete_period():
    with pytest.raises(ResearchError):
        months_between("2026-01", shift_month(last_closed_month(), 1))
