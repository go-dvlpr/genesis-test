import copy

import pytest
from conftest import reseal
from wiki_interest.client import ResearchError
from wiki_interest.research import analyze, create_plan, search, series_url, validate_plan


def test_snapshot_recomputes_from_original_items(synthetic_snapshot):
    result = analyze(synthetic_snapshot)
    assert result["research_shortlist"] == ["uk"]
    assert result["rows"][0]["metrics"]["recent_views"] == 1440


def test_tampered_snapshot_is_rejected(synthetic_snapshot):
    synthetic_snapshot["sources"][0]["data"]["items"][0]["views"] += 1
    with pytest.raises(ResearchError, match="integrity"):
        analyze(synthetic_snapshot)


def test_duplicate_months_rejected(synthetic_snapshot):
    items = synthetic_snapshot["sources"][0]["data"]["items"]
    items.append(copy.deepcopy(items[0]))
    reseal(synthetic_snapshot)
    with pytest.raises(ResearchError, match="duplicate"):
        analyze(synthetic_snapshot)


def test_wrong_measurement_dimensions_rejected(synthetic_snapshot):
    synthetic_snapshot["sources"][0]["data"]["items"][0]["agent"] = "all-agents"
    reseal(synthetic_snapshot)
    with pytest.raises(ResearchError, match="dimensions"):
        analyze(synthetic_snapshot)


def test_404_is_missing_not_zero(synthetic_snapshot):
    source = synthetic_snapshot["sources"][-1]
    source["data"] = {"items": []}
    source["status"] = 404
    reseal(synthetic_snapshot)
    r = analyze(synthetic_snapshot)
    assert r["rows"][0]["views"][-1] is None
    assert r["research_shortlist"] == []


def test_missing_sitelink_keeps_language_but_excludes_basket(synthetic_snapshot):
    synthetic_snapshot["plan"]["projects"][0]["pages"][0]["title"] = None
    reseal(synthetic_snapshot)
    r = analyze(synthetic_snapshot)
    assert r["rows"][0]["metrics"]["status"] == "insufficient_data"
    assert r["research_shortlist"] == []


def test_threshold_is_a_real_input(synthetic_snapshot):
    synthetic_snapshot["plan"]["criteria"]["growth_threshold_pct"] = 30
    reseal(synthetic_snapshot)
    assert analyze(synthetic_snapshot)["research_shortlist"] == []


def test_title_is_encoded_as_single_path_segment():
    url = series_url("en", "Foo/Bar & C?", "2024-01", "2024-02")
    assert "Foo%2FBar_%26_C%3F" in url
    assert url.endswith("2024010100/2024022900")


def test_duplicate_qids_fail(synthetic_snapshot):
    plan = synthetic_snapshot["plan"]
    plan["topics"] *= 2
    with pytest.raises(ResearchError, match="duplicate"):
        validate_plan(plan)


class FakeResolution:
    sources = {}

    def __init__(self, disambiguation=False, wrong_id=False, absent=False):
        self.disambiguation = disambiguation
        self.wrong_id = wrong_id
        self.absent = absent

    def api(self, wiki_language=None, **params):
        if params["action"] == "wbsearchentities":
            assert wiki_language is None
            assert params["language"] == "uk"
            return {"search": [{"id": "Q333", "label": "Астрономія"}]}
        if params["action"] == "wbgetentities":
            return {
                "entities": {
                    "Q333": {
                        "sitelinks": {} if self.absent else {"ukwiki": {"title": "Астрономія"}}
                    }
                }
            }
        props = {"wikibase_item": "Q5" if self.wrong_id else "Q333"}
        if self.disambiguation:
            props["disambiguation"] = ""
        return {
            "query": {
                "pages": [
                    {
                        "ns": 0,
                        "title": "Астрономія",
                        "pageid": 827,
                        "lastrevid": 1,
                        "pageprops": props,
                    }
                ]
            }
        }


def test_search_language_is_api_parameter_not_wikipedia_host():
    assert search(FakeResolution(), "Астрономія", "uk")[0]["qid"] == "Q333"


@pytest.mark.parametrize("kwargs", [{"disambiguation": True}, {"wrong_id": True}])
def test_resolution_rejects_wrong_entity(kwargs):
    with pytest.raises(ResearchError):
        create_plan(FakeResolution(**kwargs), "Astronomy", ["Q333"], ["uk"], "2024-09", "2026-08")


def test_absent_language_does_not_substitute_topic():
    p = create_plan(
        FakeResolution(absent=True), "Astronomy", ["Q333"], ["uk"], "2024-09", "2026-08"
    )
    assert p["projects"][0]["pages"][0]["title"] is None


def test_basket_growth_does_not_hide_opposite_article_trends(synthetic_snapshot):
    snapshot = synthetic_snapshot
    plan = snapshot["plan"]
    second = dict(plan["projects"][0]["pages"][0], qid="Q5", title="Second topic")
    plan["topics"].append(dict(qid="Q5", label="Second", description="synthetic fixture"))
    plan["projects"][0]["pages"].append(second)
    extra = []
    for source in snapshot["sources"]:
        if "/per-article/" not in source["url"]:
            continue
        other = copy.deepcopy(source)
        other["url"] = source["url"].replace(
            "%D0%90%D1%81%D1%82%D1%80%D0%BE%D0%BD%D0%BE%D0%BC%D1%96%D1%8F", "Second_topic"
        )
        for item in source["data"]["items"]:
            item["views"] = 300 if item["timestamp"] >= "2025090100" else 100
        for item in other["data"]["items"]:
            item["article"] = "Second_topic"
            item["views"] = 80 if item["timestamp"] >= "2025090100" else 100
        extra.append(other)
    snapshot["sources"].extend(extra)
    reseal(snapshot)
    result = analyze(snapshot)
    metrics = result["rows"][0]["metrics"]
    assert metrics["yoy_pct"] == 90
    assert metrics["status"] == "mixed_or_flat"
    assert result["research_shortlist"] == []
