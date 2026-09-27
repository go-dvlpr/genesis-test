# Methodology and decision rules

## What is measured

The measurement is monthly `all-access / user` pageviews for explicitly selected,
current canonical article titles. Wikimedia's `user` classification excludes
recognized automated traffic, but is not a guarantee of human identity. Pageviews
are neither unique readers nor willingness to pay.

Entity discovery uses Wikidata labels and descriptions. The agent selects the
meaning; code resolves sitelinks and verifies namespace, absence of a disambiguation
marker and matching Wikidata ID. Each plan records page IDs, current revision IDs,
exact titles and API response bodies. These identify the resolution state; they do
not prove that article content is equivalent across languages.

The same QID set is required in every language. Missing sitelinks produce an
incomplete basket, not an automatic substitute or a smaller comparison basket.
For broad topics, select multiple justified concepts rather than assuming the
umbrella article represents every subtopic. Inspect per-article growth in the full
report. Opposite article directions downgrade an otherwise growing basket.

Current-title pageviews do not join historical title changes or all redirect
variants. This is a systematic measurement limitation. Do not silently add redirect
views: title histories and redirect accounting need dedicated validation. Unexpected
discontinuities require a page-history investigation before business interpretation.

## Time and missingness

Only complete UTC calendar months from July 2015 are accepted. The default is the
last 24 closed months. On September 22, 2026 that is September 2024-August 2026.
The latest closed month can still have publication delays or upstream revisions;
empty/missing months remain `null`, and raw snapshots preserve observed responses.

The main statistic always compares the most recent 12 months with the preceding 12.
Both windows have the same calendar-month composition, reducing seasonal mismatch.
This does not estimate or remove seasonality, establish a causal trend or forecast.
With fewer than 24 months, show the chart and report insufficient annual evidence.
For longer histories, the chart includes all requested months while the annual
comparison uses the last 24. Coverage describes the whole plotted interval.

An explicit observed zero stays zero. Missing API records and HTTP 404 remain
unknown. No interpolation, zero-filling or drop-missing growth calculation occurs.
An incomplete month in the final 24 prevents the annual comparison. Zero annual
baseline makes percentage growth undefined. Missing project totals prevent a
normalized recommendation even when raw article counts exist.

## Formulas

Let A be baseline annual article views, B recent annual article views,
P baseline annual project views, and Q recent annual project views.

- Raw annual growth: `100 * (B / A - 1)`, defined only when A > 0.
- Recent share: `1,000,000 * B / Q` (views per million project views).
- Share growth: `100 * ((B / Q) / (A / P) - 1)`.
- Chart daily attention: monthly article views / calendar days in that month.
- Chart share: monthly article views / monthly project views * 1,000,000.
- Matched daily-rate growth: compare each recent calendar month with the same
  month a year earlier after dividing both by their month lengths (leap years matter).
- Pair-exclusion sensitivity: omit January in both windows, recompute raw and
  share growth; repeat for all 12 calendar-month pairs. Report min/max.

Annual share is the ratio of annual sums, **not** the average of monthly shares.
A basket sums pageviews, not readers; the same person may visit multiple articles.
Per-article results are retained. Project totals provide a contextual denominator,
not a population adjustment or an addressable market estimate.

## Reliability is descriptive

No p-values or confidence intervals are produced. Correlated, observational traffic
and uncertain title coverage do not justify an automatic confidence claim. The
pair-exclusion range is a robustness diagnostic, not a sampling interval.

Default screening rules are explicit product-research heuristics, adjustable before
ranking. They are not empirically calibrated success predictors:

1. Complete final 24 article and project months are required.
2. Each annual window must contain at least 1,000 selected-article views.
3. If excluding any matched month pair changes raw **or** share growth direction,
   classify as `sensitive`. Undefined exclusions also fail robustness.
4. `consistent_growth`: raw and share annual growth >=10%, at least 9 of 12 matched
   daily-rate comparisons positive, and all exclusions preserve directions.
5. `consistent_decline`: both growth rates <=-10%, all 12 daily comparisons defined,
   at most 3 positive comparisons, and all exclusions preserve directions.
6. Remaining complete, sufficient-volume results are `mixed_or_flat`.

`low_volume` takes precedence over sensitivity; warnings still retain both issues.
A month contributing >25% of recent annual traffic gets a concentration warning.
That alone does not distinguish recurring seasonality from an isolated event.

Only consistently growing languages enter the research shortlist. Sort by share
growth, then recent absolute views, then language code for stable ties. Keep raw
volume alongside normalized growth: neither metric alone determines commercial
priority. If user criteria differ, change the exposed thresholds or explain why the
requested criterion is outside the tool; never relabel the default screen as theirs.

## Primary sources

- [Wikimedia pageview API](https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/reference/page-views.html)
- [Pageviews, redirects and automated traffic](https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/concepts/page-views.html)
- [Wikibase API and sitelinks](https://www.mediawiki.org/wiki/Wikibase/API)
- [Agent Skills specification](https://agentskills.io/specification)

Exact data URLs and retrieval timestamps are generated for every report. Text here
is original methodology, not copied documentation. Retrieved statistical facts are
attributed to Wikimedia; retain the report's source records when sharing it.
