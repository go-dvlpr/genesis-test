# Operation and reproducibility

## Installation

Install Python 3.11+ and [uv](https://docs.astral.sh/uv/getting-started/installation/).
From the skill directory, run `uv sync --locked`. All direct and transitive Python
dependencies are pinned by `uv.lock`. No compiled executables or local virtual
environments are included. Fonts come from the pinned Matplotlib distribution;
Cyrillic and common European Latin scripts are supported. `--report-language en|uk|ru`
sets PDF and chart labels; original article titles are preserved. The detailed
Markdown appendix and JSON keys stay English. CJK/complex-script font coverage is not
guaranteed; inspect those reports or add a reviewed font package before delivery.

Run `uv run --locked pytest` and `uv run --locked ruff check .` for verification.
The data commands need no LLM API token. An agent host still needs its own model access.
For long-running deployments, set `WIKI_INTEREST_USER_AGENT` to an informative user
agent with your maintained contact URL/email. Do not put credentials in it.

## Files

- `plan.json`: explicit assumptions, topic entities, resolved articles, date window,
  screening criteria, source response bodies for resolution.
- `snapshot.json`: plan plus original analytics response bodies, source timestamps,
  and a SHA-256 digest of canonical JSON. This is portable offline evidence.
- `analysis.json`: deterministic metrics, raw series, per-article series, limitations,
  shortlist and reference to the snapshot hash.
- `monthly.csv`: summed article views, project views and normalized monthly share;
  empty numeric fields mean missing, never zero.
- `report.md`: complete explanation, scope, individual articles and warnings.
- `report.pdf`: one-page brief with two plots, comparison table, criteria and caveats.
- `chart.png`: reusable plot with daily attention and normalized monthly share.
- `sources.json`: exact API URLs, retrieval dates, response status and content hashes.
- `manifest.json`: content hashes of the seven report files.

`verify` checks every artifact hash and recomputes analysis from the original API
bodies; it does not merely compare precomputed totals. Hashes are integrity checks,
not signatures or independent certification of Wikimedia data. `replay` performs
the same arithmetic and renders without HTTP access. Hashes of binary plots/PDFs
can vary across runtime/platform versions, so arithmetic equality is the portable
reproducibility guarantee. The submitted lock and runtime are recorded in evaluation.

## Cache and updates

Default cache: `.cache/` inside this directory; override with `--cache PATH` on
`search`, `plan` and `run`. Entries are keyed by full URL and contain the response,
retrieval time, status and content hash. Writes use atomic replace. Default freshness
is 24 hours, including 404s; `--refresh` bypasses cache, `--offline` accepts older
verified entries. The two flags are mutually exclusive.

Analytics requests use stable calendar-year chunks, cropped to the requested window
after fetching. This lets related narrower queries reuse historical data. The current
year ends at the last closed month, so its cache key changes as the calendar advances.
Snapshots preserve their original chunk boundaries. A stale cache may preserve an
upstream defect; compare an explicit refreshed run when freshness matters.

An interrupted run may leave an incomplete output directory. Keep it for diagnosis
or remove it deliberately, then choose a fresh output path. Success requires a
manifest and a passing `verify`. Existing nonempty outputs and plans are not replaced.

## Bounds and failures

Interactive runs support at most 6 languages, 8 topic entities and 120 months.
Requests are sequential, at least 150 ms apart, with a 25-second timeout, up to 4
attempts for temporary HTTP/network failures, exponential backoff and Retry-After
handling. A requested delay above 30 seconds stops with a retry-later message.
Responses are bounded to 8 MB; JSON input files to 40 MB. No response text is executed.
Only HTTPS Wikimedia/Wikidata/Wikipedia hosts are fetched, including redirects.
No credentials or arbitrary URLs are accepted by the research API.

Bad input, missing offline cache, identity mismatch and invalid API dimensions fail
explicitly. HTTP 404 analytics data become missing observations. Other permanent
HTTP errors fail the run. Retried API failures never become invented zero traffic.
Missing sitelinks are carried into the report instead of aborting the other languages.

The intended use is a trusted local agent creating local artifacts. The CLI is not
an internet-facing service, has no arbitrary shell-evaluation endpoint, and does not
perform external writes. Keep model-generated shell execution under the host's
ordinary permission boundary; the skill does not grant additional permissions.
