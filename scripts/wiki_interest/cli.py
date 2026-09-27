"""Small JSON-speaking interface for inexpensive tool-using agents."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from .analysis import last_closed_month, shift_month
from .client import Client, ResearchError, canonical_json, write_json
from .report import export
from .research import analyze, collect, create_plan, search

ROOT = Path(__file__).resolve().parents[2]


def read_json(path):
    if path.stat().st_size > 40_000_000:
        raise ResearchError("Input JSON exceeds 40 MB limit")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise ResearchError(f"Invalid JSON: {path}") from exc


def ensure_new_output(path):
    if path.exists() and (not path.is_dir() or any(path.iterdir())):
        raise ResearchError("Output must be an empty or new directory; choose a new run name")


def verify(directory):
    manifest = read_json(directory / "manifest.json")
    expected = {
        "snapshot.json",
        "analysis.json",
        "sources.json",
        "monthly.csv",
        "report.md",
        "chart.png",
        "report.pdf",
    }
    if set(manifest) != expected:
        raise ResearchError("Artifact manifest is incomplete or unexpected")
    for name, expected_hash in manifest.items():
        if hashlib.sha256((directory / name).read_bytes()).hexdigest() != expected_hash:
            raise ResearchError(f"Artifact integrity check failed: {name}")
    actual = analyze(read_json(directory / "snapshot.json"))
    if actual != read_json(directory / "analysis.json"):
        raise ResearchError("Analysis does not match source replay")
    return dict(verified=True, files=len(manifest), snapshot_sha256=actual["snapshot_sha256"])


def parser():
    p = argparse.ArgumentParser(
        description="Wikipedia interest research: search -> plan -> run -> verify"
    )
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--cache", type=Path, default=ROOT / ".cache")
    common.add_argument(
        "--offline",
        action="store_true",
        help="Use verified cache entries, even if old; never network",
    )
    common.add_argument(
        "--refresh", action="store_true", help="Bypass cache and fetch sources again"
    )
    commands = p.add_subparsers(dest="command", required=True)
    s = commands.add_parser(
        "search",
        parents=[common],
        help="Find candidate Wikidata entities; does not silently choose one",
    )
    s.add_argument("--query", required=True)
    s.add_argument("--language", default="en")
    s = commands.add_parser(
        "plan",
        parents=[common],
        help="Resolve one shared topic basket into current canonical articles",
    )
    s.add_argument("--topic", required=True)
    s.add_argument("--qid", action="append", required=True)
    s.add_argument("--languages", nargs="+", required=True)
    window = s.add_mutually_exclusive_group()
    window.add_argument("--start")
    window.add_argument("--months", type=int)
    s.add_argument("--end", default=last_closed_month())
    s.add_argument("--min-views", type=int, default=1000)
    s.add_argument("--growth-threshold", type=float, default=10)
    s.add_argument("--report-language", choices=["en", "uk", "ru"], default="en")
    s.add_argument("--output", required=True, type=Path)
    s = commands.add_parser(
        "run", parents=[common], help="Fetch, analyze and render from a saved plan"
    )
    s.add_argument("--plan", required=True, type=Path)
    s.add_argument("--out", required=True, type=Path)
    s = commands.add_parser("replay", help="Recompute and render from a snapshot; never network")
    s.add_argument("--snapshot", required=True, type=Path)
    s.add_argument("--out", required=True, type=Path)
    s = commands.add_parser(
        "verify", help="Check artifact hashes and recompute metrics from saved API bodies"
    )
    s.add_argument("--directory", required=True, type=Path)
    return p


def execute(args):
    if args.command == "verify":
        return verify(args.directory)
    if args.command == "replay":
        ensure_new_output(args.out)
        snapshot = read_json(args.snapshot)
        result = analyze(snapshot)
        export(result, snapshot, args.out)
        return summary(result, args.out)
    client = Client(args.cache, offline=args.offline, refresh=args.refresh)
    if args.command == "search":
        return dict(
            candidates=search(client, args.query, args.language),
            network_requests=client.requests,
            cache_hits=client.hits,
        )
    if args.command == "plan":
        if args.output.exists():
            raise ResearchError(
                "Plan already exists; choose a new filename to preserve the earlier assumptions"
            )
        count = args.months if args.months is not None else 24
        if not 1 <= count <= 120:
            raise ResearchError("months must be 1-120")
        start = args.start or shift_month(args.end, 1 - count)
        plan = create_plan(
            client,
            args.topic,
            args.qid,
            args.languages,
            start,
            args.end,
            args.min_views,
            args.growth_threshold,
            args.report_language,
        )
        write_json(args.output, plan)
        return dict(
            plan=str(args.output.resolve()),
            start=start,
            end=args.end,
            topics=plan["topics"],
            projects=plan["projects"],
            network_requests=client.requests,
            cache_hits=client.hits,
        )
    ensure_new_output(args.out)
    snapshot = collect(client, read_json(args.plan))
    result = analyze(snapshot)
    export(result, snapshot, args.out)
    return dict(summary(result, args.out), network_requests=client.requests, cache_hits=client.hits)


def summary(result, output):
    return dict(
        output=str(output.resolve()),
        pdf=str((output / "report.pdf").resolve()),
        research_shortlist=result["research_shortlist"],
        results=[dict(language=r["language"], **r["metrics"]) for r in result["rows"]],
    )


def main():
    args = parser().parse_args()
    try:
        print(canonical_json(execute(args)))
    except (ResearchError, OSError, ValueError) as exc:
        print(
            canonical_json(dict(error=str(exc), retryable="retry" in str(exc).lower())),
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
