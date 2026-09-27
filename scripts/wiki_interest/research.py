"""Topic resolution, reproducible snapshots and analysis orchestration."""

from __future__ import annotations

import re
from urllib.parse import quote

from .analysis import days, last_closed_month, months_between, paired_summary
from .client import ResearchError, digest, utc_now

LANGUAGE = re.compile(r"[a-z][a-z0-9-]{0,24}")
QID = re.compile(r"Q[1-9][0-9]{0,12}")


def validate_languages(languages):
    if not 1 <= len(languages) <= 6 or len(set(languages)) != len(languages):
        raise ResearchError("Choose 1-6 distinct Wikipedia language codes")
    if any(not LANGUAGE.fullmatch(v) for v in languages):
        raise ResearchError("Invalid Wikipedia language code")


def search(client, query, language="en"):
    validate_languages([language])
    if not query.strip() or len(query) > 200:
        raise ResearchError("Search query must contain 1-200 characters")
    data = client.api(action="wbsearchentities", search=query, language=language, limit=6)
    return [
        {"qid": v["id"], "label": v.get("label"), "description": v.get("description", "")}
        for v in data.get("search", [])
    ]


def create_plan(
    client, topic, qids, languages, start, end, min_views=1000, threshold=10, report_language="en"
):
    validate_languages(languages)
    if (
        not 1 <= len(qids) <= 8
        or len(set(qids)) != len(qids)
        or any(not QID.fullmatch(q) for q in qids)
    ):
        raise ResearchError("Choose 1-8 distinct Wikidata Q identifiers")
    months_between(start, end)
    if not 0 <= min_views <= 1_000_000_000 or not 0 < threshold <= 1000:
        raise ResearchError("min-views must be 0..1000000000 and growth-threshold must be >0..1000")
    if not topic.strip() or len(topic) > 160:
        raise ResearchError("Topic must contain 1-160 characters")
    data = client.api(
        action="wbgetentities",
        ids="|".join(qids),
        props="labels|descriptions|sitelinks",
        languages="en",
    )
    entities = data.get("entities", {})
    topics = []
    projects = []
    for qid in qids:
        entity = entities.get(qid, {})
        if "missing" in entity or not entity:
            raise ResearchError(f"Wikidata item not found: {qid}")
        topics.append(
            dict(
                qid=qid,
                label=entity.get("labels", {}).get("en", {}).get("value", qid),
                description=entity.get("descriptions", {}).get("en", {}).get("value", ""),
            )
        )
    for language in languages:
        pages = []
        for qid in qids:
            sitelink = entities[qid].get("sitelinks", {}).get(language.replace("-", "_") + "wiki")
            if not sitelink:
                pages.append(
                    dict(qid=qid, title=None, reason="No Wikidata sitelink in this language")
                )
                continue
            candidate = sitelink["title"]
            response = client.api(
                language,
                action="query",
                titles=candidate,
                redirects=1,
                prop="pageprops|info",
                ppprop="disambiguation|wikibase_item",
            )
            found = response.get("query", {}).get("pages", [])
            if len(found) != 1 or "missing" in found[0]:
                raise ResearchError(f"Article resolution failed: {language}/{qid}")
            page = found[0]
            props = page.get("pageprops", {})
            if page.get("ns") != 0 or "disambiguation" in props:
                raise ResearchError(
                    f"Choose a specific article, not a disambiguation or non-article page: {candidate}"
                )
            if props.get("wikibase_item") != qid:
                raise ResearchError(
                    f"Wikidata identity mismatch: {language}/{candidate}; resolve the intended item again"
                )
            pages.append(
                dict(
                    qid=qid,
                    title=page["title"],
                    pageid=page["pageid"],
                    revision_id=page.get("lastrevid"),
                    url=f"https://{language}.wikipedia.org/wiki/{quote(page['title'].replace(' ', '_'), safe='')}",
                    requested_title=candidate,
                )
            )
        present_titles = [p["title"] for p in pages if p["title"]]
        if len(present_titles) != len(set(present_titles)):
            raise ResearchError(
                f"Duplicate resolved articles in {language}; revise the topic basket"
            )
        projects.append(dict(language=language, pages=pages))
    plan = dict(
        schema_version=1,
        topic=topic,
        report_language=report_language,
        topics=topics,
        projects=projects,
        start=start,
        end=end,
        access="all-access",
        agent="user",
        granularity="monthly",
        created_at=utc_now(),
        criteria=dict(min_annual_views=min_views, growth_threshold_pct=threshold),
        resolution_sources=list(client.sources.values()),
    )
    validate_plan(plan)
    return plan


def validate_plan(plan):
    try:
        if plan["schema_version"] != 1:
            raise ResearchError("Unsupported plan schema")
        months_between(plan["start"], plan["end"])
        validate_languages([p["language"] for p in plan["projects"]])
        if (
            plan["agent"] != "user"
            or plan["access"] != "all-access"
            or plan["granularity"] != "monthly"
        ):
            raise ResearchError("This methodology requires user/all-access/monthly data")
        qids = [t["qid"] for t in plan["topics"]]
        if (
            not 1 <= len(qids) <= 8
            or len(set(qids)) != len(qids)
            or any(not QID.fullmatch(q) for q in qids)
        ):
            raise ResearchError("Invalid or duplicate topic identifiers")
        for project in plan["projects"]:
            if [p["qid"] for p in project["pages"]] != qids:
                raise ResearchError(
                    "Each project must explicitly include every topic, including missing articles"
                )
            titles = []
            for page in project["pages"]:
                title = page["title"]
                if title is not None:
                    if (
                        not isinstance(title, str)
                        or not title.strip()
                        or len(title) > 512
                        or any(ord(c) < 32 for c in title)
                    ):
                        raise ResearchError("Invalid article title")
                    titles.append(title)
            if len(set(titles)) != len(titles):
                raise ResearchError("Duplicate articles would double-count views")
        criteria = plan["criteria"]
        if plan.get("report_language", "en") not in ("en", "uk", "ru"):
            raise ResearchError("Report language must be en, uk or ru")
        if (
            not 0 <= criteria["min_annual_views"] <= 1_000_000_000
            or not 0 < criteria["growth_threshold_pct"] <= 1000
        ):
            raise ResearchError("Invalid screening criteria")
        if not isinstance(plan["topic"], str) or not 1 <= len(plan["topic"]) <= 160:
            raise ResearchError("Invalid topic label")
    except (KeyError, TypeError, AttributeError) as exc:
        raise ResearchError("Invalid plan structure; generate it with the plan command") from exc


def year_ranges(start, end, as_of):
    """Stable year-sized cache keys also serve narrower related requests."""
    for year in range(int(start[:4]), int(end[:4]) + 1):
        yield max(f"{year}-01", "2015-07"), min(f"{year}-12", as_of)


def series_url(language, title, start, end):
    begin = start.replace("-", "") + "0100"
    finish = end.replace("-", "") + f"{days(end):02d}00"
    base = "https://wikimedia.org/api/rest_v1/metrics/pageviews"
    if title is None:
        return f"{base}/aggregate/{language}.wikipedia/all-access/user/monthly/{begin}/{finish}"
    encoded = quote(title.replace(" ", "_"), safe="")
    return f"{base}/per-article/{language}.wikipedia/all-access/user/{encoded}/monthly/{begin}/{finish}"


def collect(client, plan):
    validate_plan(plan)
    as_of = last_closed_month()
    for project in plan["projects"]:
        titles = [p["title"] for p in project["pages"] if p["title"] is not None]
        for title in [None, *titles]:
            for start, end in year_ranges(plan["start"], plan["end"], as_of):
                client.get(series_url(project["language"], title, start, end), allow_not_found=True)
    snapshot = dict(
        schema_version=1,
        created_at=utc_now(),
        fetched_at=max(source["fetched_at"] for source in client.sources.values()),
        as_of=as_of,
        plan=plan,
        sources=list(client.sources.values()),
    )
    snapshot["sha256"] = digest(snapshot)
    return snapshot


def unpack_series(sources, language, title, months, as_of):
    observed = {}
    for start, end in year_ranges(months[0], months[-1], as_of):
        url = series_url(language, title, start, end)
        if url not in sources:
            raise ResearchError(f"Snapshot is missing a source: {url}")
        source = sources[url]
        data = source["data"]
        if not isinstance(data.get("items"), list):
            raise ResearchError("Unexpected pageview response: items must be a list")
        for item in data["items"]:
            stamp = item.get("timestamp", "")
            if not re.fullmatch(r"\d{6}0100", stamp):
                raise ResearchError("Unexpected monthly timestamp")
            month = stamp[:4] + "-" + stamp[4:6]
            if month < start or month > end or month in observed:
                raise ResearchError("Source contains duplicate or out-of-range months")
            if (
                item.get("project") != f"{language}.wikipedia"
                or item.get("agent") != "user"
                or item.get("access") != "all-access"
                or item.get("granularity") != "monthly"
            ):
                raise ResearchError("Source dimensions do not match the requested measurement")
            if title is not None and item.get("article", "").replace("_", " ") != title.replace(
                "_", " "
            ):
                raise ResearchError("Source article does not match the resolved title")
            value = item.get("views")
            if type(value) is not int or value < 0:
                raise ResearchError("Pageviews must be non-negative integers")
            observed[month] = value
    return [observed.get(m) for m in months]


def analyze(snapshot):
    if not isinstance(snapshot, dict) or not all(
        k in snapshot for k in ("plan", "sources", "as_of", "fetched_at", "sha256")
    ):
        raise ResearchError("Invalid snapshot structure")
    check = {k: v for k, v in snapshot.items() if k != "sha256"}
    if snapshot.get("sha256") != digest(check):
        raise ResearchError("Snapshot integrity check failed")
    if snapshot.get("schema_version") != 1:
        raise ResearchError("Unsupported snapshot schema")
    plan = snapshot["plan"]
    validate_plan(plan)
    sources = {}
    for source in snapshot["sources"]:
        if digest(source["data"]) != source["sha256"]:
            raise ResearchError("Source integrity check failed")
        if source["url"] in sources:
            raise ResearchError("Duplicate source URLs in snapshot")
        sources[source["url"]] = source
    months = months_between(plan["start"], plan["end"])
    rows = []
    for project in plan["projects"]:
        language = project["language"]
        totals = unpack_series(sources, language, None, months, snapshot["as_of"])
        articles = []
        for page in project["pages"]:
            views = (
                unpack_series(sources, language, page["title"], months, snapshot["as_of"])
                if page["title"]
                else [None] * len(months)
            )
            article = dict(page, views=views)
            article["metrics"] = paired_summary(
                months,
                views,
                totals,
                plan["criteria"]["min_annual_views"],
                plan["criteria"]["growth_threshold_pct"],
            )
            articles.append(article)
        views = [
            sum(values) if all(v is not None for v in values) else None
            for values in zip(*(a["views"] for a in articles), strict=True)
        ]
        if any(
            v is not None and t is not None and v > t for v, t in zip(views, totals, strict=True)
        ):
            raise ResearchError("Article basket exceeds project total; inspect source consistency")
        metrics = paired_summary(
            months,
            views,
            totals,
            plan["criteria"]["min_annual_views"],
            plan["criteria"]["growth_threshold_pct"],
        )
        if any(a["title"] is None for a in articles):
            metrics["warnings"].append(
                "Topic basket is incomplete in this language; excluded from prioritization."
            )
        if len(articles) > 1:
            article_growth = [a["metrics"]["yoy_pct"] for a in articles]
            if any(v is not None and v < 0 for v in article_growth) and any(
                v is not None and v > 0 for v in article_growth
            ):
                metrics["warnings"].append(
                    "Individual articles move in opposite directions; basket totals hide differences."
                )
                if metrics["status"] == "consistent_growth":
                    metrics["status"] = "mixed_or_flat"
        shares = [
            v / t * 1_000_000 if v is not None and t is not None and t > 0 else None
            for v, t in zip(views, totals, strict=True)
        ]
        rows.append(
            dict(
                language=language,
                views=views,
                project_views=totals,
                share_per_million=shares,
                articles=articles,
                metrics=metrics,
            )
        )
    candidates = [r for r in rows if r["metrics"]["status"] == "consistent_growth"]
    candidates.sort(
        key=lambda r: (-r["metrics"]["share_yoy_pct"], -r["metrics"]["recent_views"], r["language"])
    )
    return dict(
        schema_version=1,
        topic=plan["topic"],
        report_language=plan.get("report_language", "en"),
        months=months,
        criteria=plan["criteria"],
        rows=rows,
        research_shortlist=[r["language"] for r in candidates],
        snapshot_sha256=snapshot["sha256"],
        limitations=[
            "Pageviews measure article attention, not unique people, learning intent or willingness to pay.",
            "Wikipedia languages are not countries or addressable markets.",
            "Wikidata aligns entities, not article depth, scope, quality or search visibility.",
            "Only current canonical titles are measured; redirects and historical title moves are not reconstructed.",
            "The user category filters recognized automation; it does not guarantee human-only traffic.",
            "Sensitivity ranges are descriptive, not confidence intervals, causal evidence or forecasts.",
            "A topic basket sums pageviews, not distinct readers; related articles may share readers.",
        ],
    )
