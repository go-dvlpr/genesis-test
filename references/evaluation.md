# Evaluation record

Executed on 2026-09-22, on macOS with CPython 3.12.4 and dependencies from `uv.lock`.
This records observed results; it is not a claim of universal correctness or a
statistical benchmark of model reliability.

## Independent inexpensive-model workflow

An independent agent was explicitly configured as **gpt-5.6-luna**, medium reasoning,
with no parent conversation or expected numerical answers. This is the host's
inexpensive tool-using model, used as the assignment's permitted alternative to
Haiku. It read the standalone skill and used terminal tools; the data pipeline itself
never called an LLM. No Anthropic or OpenRouter API run is claimed.

The agent received a realistic Ukrainian request: assess whether interest in astronomy
is growing in Ukrainian Wikipedia over the last two complete years and create a PDF.
It then received a follow-up adding Polish Wikipedia and changing the growth threshold
to 20%, with other assumptions unchanged.

Observed behavior:

- Selected Q333 using a Wikidata search, then resolved `Астрономія` and `Astronomia`.
- Created plans, fetched data, generated reports and ran `verify` successfully.
- Identified declining attention rather than inventing a positive recommendation.
- Distinguished article attention from demand, languages from countries, and
  descriptive robustness from statistical confidence.
- Preserved the earlier report when changing assumptions.
- On the localized retest follow-up, planning used 3 cache hits and 0 requests;
  analysis used 12 cache hits and 0 requests.
- Both localized PDFs contained one page and Ukrainian text verified by pypdf.

Raw command outputs, exit statuses, empty stderr captures, the evaluator's account,
and its unchanged localized report artifacts are in
[`evaluations/small-model/`](../evaluations/small-model/).
Absolute local paths in text logs were normalized to `$SKILL_ROOT`, `$EVAL_ROOT`
and `$PYTHON` for portability; numbers and exit statuses were not changed. Source
snapshots and report artifacts were preserved unchanged.

The initial evaluation found English-only PDF labels. That led to explicit
`--report-language en|uk|ru` support and a successful second execution of both tasks.
The technical Markdown appendix remains English, as documented. The initial
evaluator also tried an unavailable `/usr/bin/pdfinfo`; pypdf and the bundled Poppler
renderer subsequently provided structural and visual checks.

After the retest, the final presentation wording was tightened: missing Wikidata
links are no longer described as proof of absent articles, and no shortlist is
described as no *confirmed* growth signal. The main `examples/` were replayed from
the same snapshots with that wording. The evaluator's original outputs remain in
`evaluations/` so that the observation record is not rewritten.

Limits: two related user tasks, repeated after a localization fix, are a bounded
forward test. They do not establish a task-success rate across domains. Model token
usage and monetary cost were not available from the subagent interface and are not
reported. No claims are made about Haiku or a free OpenRouter model's behavior.

## Automated verification

`uv run --locked pytest -q`: **53 tests passed**.
`ruff check` and `ruff format --check`: passed.
The skill-creator frontmatter validator: passed. Its older allowed-field list did
not accept the specification's optional `compatibility` field; runtime requirements
were moved to the Markdown body so the skill passes both formats.

Coverage includes known growth, exact-threshold rounding, a single spike, raw/share
disagreement, zero baselines, observed zeros, missing article/project months, leap
years, ratio-of-sums normalization, short/long windows, missing sitelinks, entity
mismatch, disambiguation, multi-article composition, corrupted snapshots, wrong API
dimensions, duplicate months, URL encoding, offline cache use, retries and rate
limits, restricted source hosts, tampered artifacts, Unicode PDF text and maximum
six-language one-page layout. Synthetic data are clearly confined to tests.

The end-to-end test blocks HTTP during snapshot replay, creates all report artifacts,
recomputes metrics, checks integrity, and inspects the PDF. Known-answer arithmetic
tests are independent of the operational `verify` command's replay mechanism.

## Live Wikimedia examples

All final examples use September 2024-August 2026, `user / all-access / monthly`.
Annual change compares September 2025-August 2026 with the previous 12 months.

| Topic / language | Baseline | Recent | Raw growth | Share growth | Interpretation |
|---|---:|---:|---:|---:|---|
| Astronomy / uk | 16,614 | 6,708 | -59.6% | -46.4% | Consistent decline |
| Astronomy / pl, 20% threshold | 20,477 | 17,175 | -16.1% | -8.0% | Mixed / flat under this screen |
| Intermittent fasting / cs | 4,741 | 2,198 | -53.6% | -47.0% | Consistent decline |
| Intermittent fasting / pl | n/a | n/a | n/a | n/a | No Q1666254 sitelink; no verified comparison |
| English learning proxy / de | 1,292 | 871 | -32.6% | -27.2% | Low volume |
| English learning proxy / es | 2,915 | 1,389 | -52.3% | -39.8% | Consistent decline |
| English learning proxy / fi | 222 | 171 | -23.0% | -19.0% | Low volume |

The English example selects Q130192, “English as a second or foreign language”,
rather than silently treating the general English-language article as learning
intent. German, Spanish and Finnish are illustrative choices with available
sitelinks, not recommended markets. None of these particular examples supports a
growth-based launch recommendation; that is a valid finding.

One live English-proxy request encountered a long Wikimedia Retry-After. The tool
stopped with a retryable error, retained successful cache entries and resumed later;
the completed run reused 10 entries and fetched the remaining 8. No missing data
were replaced with synthetic values or zeros to complete the example.

Exact response bodies, source URLs, timestamps and hashes accompany each example.
Final package checks also verify replay from a newly installed environment, numeric
agreement with an independent Decimal calculation and one-page PDF rendering.

## How AI output was checked

AI was used to design the workflow, write code and documentation, and run the
independent agent scenario. Generated formulas were checked with hand-computable
fixtures, including counterexamples where a naive recommendation would be wrong.
Operational behavior was exercised against real APIs and controlled failures.
Reports were checked numerically, structurally and visually. The small-model test
exposed an actual usability defect and was repeated after the fix. Source evidence
is preserved so a reviewer can inspect the result without trusting either model.
