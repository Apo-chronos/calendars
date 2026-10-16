from __future__ import annotations

import argparse
import shutil
import sys
import urllib.request
from datetime import date
from pathlib import Path

from .ics import render_ics
from .models import FeedMetadata
from .parser import parse_schedule


def _slug(value: str) -> str:
    value = value.strip().lower()
    if not value or any(character not in "abcdefghijklmnopqrstuvwxyz0123456789-" for character in value):
        raise argparse.ArgumentTypeError("Use lowercase letters, numbers, and hyphens only.")
    return value


def _download(url: str, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=30) as response, destination.open("wb") as output:
        shutil.copyfileobj(response, output)
    return destination


def _choose(prompt: str, available: list[int]) -> list[int]:
    answer = input(f"{prompt} ({', '.join(map(str, available))}): ").strip()
    selected = sorted({int(value.strip()) for value in answer.split(",") if value.strip()})
    invalid = set(selected) - set(available)
    if not selected or invalid:
        raise ValueError(f"Choose one or more of: {', '.join(map(str, available))}.")
    return selected


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create selected ICS feeds from UAIC schedule PDFs.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--file", type=Path, help="Path to a downloaded schedule PDF.")
    source.add_argument("--url", help="Public URL of a schedule PDF to download.")
    parser.add_argument("--domain", required=True, type=_slug)
    parser.add_argument("--class-type", required=True, type=_slug)
    parser.add_argument("--year", type=int, action="append", help="Study year to import; repeat for more than one.")
    parser.add_argument("--semester", required=True, type=int, choices=(1, 2))
    parser.add_argument("--location", default="iasi", type=_slug)
    parser.add_argument("--published-date", required=True, type=date.fromisoformat)
    parser.add_argument("--optional", type=int, action="append", help="Optional group to include; repeat as needed.")
    parser.add_argument("--docs-root", type=Path, default=Path("docs"))
    parser.add_argument("--cache-file", type=Path, default=Path("data/source-schedule.pdf"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    source_path = args.file if args.file else _download(args.url, args.cache_file)
    if not source_path.exists():
        raise FileNotFoundError(f"Schedule PDF not found: {source_path}")

    events, reviews = parse_schedule(source_path)
    available_years = sorted({event.year for event in events})
    years = args.year or _choose("Choose study year(s)", available_years)
    invalid_years = set(years) - set(available_years)
    if invalid_years:
        raise ValueError(f"PDF has no events for year(s): {', '.join(map(str, sorted(invalid_years)))}")

    selected_events = [event for event in events if event.year in years]
    available_optionals = sorted({event.optional_group for event in selected_events if event.optional_group is not None})
    optionals = args.optional
    if optionals is None and available_optionals and sys.stdin.isatty():
        answer = input(f"Optional groups available: {', '.join(map(str, available_optionals))}. Include (comma-separated, blank for none): ").strip()
        optionals = [int(value.strip()) for value in answer.split(",") if value.strip()]
    optionals = optionals or []
    selected_events = [
        event for event in selected_events if event.optional_group is None or event.optional_group in optionals
    ]

    for year in years:
        feed_events = [event for event in selected_events if event.year == year]
        metadata = FeedMetadata(args.domain, args.class_type, year, args.semester, args.location, args.published_date)
        dated_path, current_path = metadata.output_paths(args.docs_root)
        dated_path.parent.mkdir(parents=True, exist_ok=True)
        content = render_ics(feed_events, metadata)
        dated_path.write_text(content, encoding="utf-8", newline="")
        current_path.write_text(content, encoding="utf-8", newline="")
        print(f"Wrote {len(feed_events)} events: {dated_path}")
        print(f"Updated stable feed: {current_path}")

    for item in reviews:
        print(f"REVIEW [page {item.source_page}]: {item.message}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

