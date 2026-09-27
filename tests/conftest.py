from __future__ import annotations

import copy

import pytest
from wiki_interest.analysis import months_between
from wiki_interest.client import digest
from wiki_interest.research import series_url, year_ranges


@pytest.fixture
def synthetic_snapshot():
    """Synthetic traffic with exactly +20% views and +20% share; never a live example."""
    months = months_between("2024-09", "2026-08")
    plan = dict(
        schema_version=1,
        topic="Synthetic astronomy fixture",
        start=months[0],
        end=months[-1],
        topics=[dict(qid="Q333", label="astronomy", description="test fixture")],
        projects=[
            dict(
                language="uk",
                pages=[
                    dict(
                        qid="Q333",
                        title="Астрономія",
                        pageid=827,
                        revision_id=1,
                        url="https://uk.wikipedia.org/wiki/Астрономія",
                        requested_title="Астрономія",
                    )
                ],
            )
        ],
        agent="user",
        access="all-access",
        granularity="monthly",
        criteria=dict(min_annual_views=1000, growth_threshold_pct=10),
        resolution_sources=[],
    )
    sources = []
    for title in (None, "Астрономія"):
        for start, end in year_ranges(months[0], months[-1], "2026-08"):
            items = []
            for month in months_between(start, end):
                views = 1_000_000 if title is None else 120 if month >= "2025-09" else 100
                item = dict(
                    project="uk.wikipedia",
                    agent="user",
                    access="all-access",
                    granularity="monthly",
                    timestamp=month.replace("-", "") + "0100",
                    views=views,
                )
                if title is not None:
                    item["article"] = title
                items.append(item)
            data = dict(items=items)
            sources.append(
                dict(
                    url=series_url("uk", title, start, end),
                    fetched_at="2026-09-22T12:00:00+00:00",
                    data=data,
                    sha256=digest(data),
                    status=200,
                )
            )
    snapshot = dict(
        schema_version=1,
        plan=plan,
        sources=sources,
        as_of="2026-08",
        fetched_at="2026-09-22T12:00:00+00:00",
    )
    snapshot["sha256"] = digest(snapshot)
    return copy.deepcopy(snapshot)


def reseal(snapshot):
    for source in snapshot["sources"]:
        source["sha256"] = digest(source["data"])
    snapshot["sha256"] = digest({k: v for k, v in snapshot.items() if k != "sha256"})
