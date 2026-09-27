# Iterative development after the baseline

## First: improve measurement validity

Collect failures from real questions: ambiguous concepts, different article scope,
missing translations, renamed pages, noisy series. Add each as a bounded fixture
and behavioral evaluation before changing instructions. Establish a small human-
reviewed set of topic-to-article mappings. Evaluate mapping correctness separately
from numeric correctness and report quality.

Add title-history reconstruction next: resolve historical moves, test redirect
accounting against Wikimedia definitions, join non-overlapping title intervals and
report coverage. Avoid simply summing every redirect. Keep current-title analysis as
an explicitly labeled baseline and compare both results.

## Then: richer research, without false precision

Add per-topic comparisons and reviewed semantic baskets. Investigate article quality,
external news shocks and changes in search visibility. Add daily drill-down only
for flagged months to keep cost bounded. For longer series, assess seasonality and
change points with held-out periods; only introduce uncertainty intervals with a
defensible dependence-aware model and clearly stated assumptions.

Use external demand signals (search intent, interviews, conversions) to validate
whether the screening rules predict anything useful. Do not train a “market score”
on pageviews alone. Geography would require a separate privacy-respecting dataset;
language editions cannot provide a country-level customer estimate.

## Scale after measuring the bottleneck

Record request counts, cache hit rate, bytes, runtime, model tokens and task success.
For tens of projects and hundreds of topics, persist normalized monthly facts in
SQLite/DuckDB, maintain source snapshot IDs, add bounded concurrency, resumable jobs
and per-host rate control. Switch to bulk sources only when measured API workload
warrants their operational cost. Retain immutable input snapshots and deterministic
calculation versions through migrations.

## Keep inexpensive-agent usability measurable

Maintain a scenario set covering ambiguous topics, missing languages, a growth case,
a decline case, a spike-driven reversal and a user changing the period or criteria.
Run complete tool workflows on a small model; retain tool traces and score entity
selection, numerical fidelity, use of caveats, valid files, and unnecessary calls.
Use a separate reviewer for qualitative judgments; automatically verify all numeric
and artifact invariants. Re-run only the affected scenarios after a small patch,
and the full set before a release. Never equate unit tests with an agent evaluation.

Improve compact errors and tool outputs before adding a larger model or longer
instructions. Add a structured tool wrapper only if shell invocation is a measured
source of errors; the current CLI and short entrypoint are intentionally sufficient.
