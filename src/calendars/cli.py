from __future__ import annotations

import argparse
import shutil
import sys
import urllib.request
from datetime import date
from pathlib import Path

from .ics import render_ics
from .models import FeedMetadata
from .parsers import detect_parser, get_parser
from .profiles import load_profile

DEFAULTS = {
    "format": "auto",
    "location": "iasi",
    "docs_root": "docs",
    "cache_file": "data/source-schedule.pdf",
}


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


def _choose(prompt: str, available: list[str]) -> list[str]:
    if not sys.stdin.isatty():
        raise ValueError(f"{prompt}: none selected. Available: {', '.join(available)}.")
    answer = input(f"{prompt} ({', '.join(available)}): ").strip()
    lookup = {value.casefold(): value for value in available}
    selected = [lookup.get(value.strip().casefold(), value.strip()) for value in answer.split(",") if value.strip()]
    invalid = set(selected) - set(available)
    if not selected or invalid:
        raise ValueError(f"Choose one or more of: {', '.join(available)}.")
    return selected


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create selected ICS feeds from schedule PDFs.")
    parser.add_argument("--profile", help="Settings file: a name in sources/ (without .yaml) or a path.")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--file", type=Path, help="Path to a downloaded schedule PDF.")
    source.add_argument("--url", help="Public URL of a schedule PDF to download.")
    parser.add_argument("--format", help="Parser to use: uaic, asc-weekly, or auto (default).")
    parser.add_argument("--domain", type=_slug)
    parser.add_argument("--class-type", type=_slug)
    parser.add_argument("--year", dest="feeds", action="append", help="Study year to import (UAIC); repeat for more.")
    parser.add_argument("--class", dest="feeds", action="append", help="Class to import, e.g. 9B (school timetables).")
    parser.add_argument("--semester", type=_slug, help="1, 2, or full.")
    parser.add_argument("--location", type=_slug)
    parser.add_argument("--published-date", type=date.fromisoformat)
    parser.add_argument("--optional", type=int, action="append", help="Optional group to include; repeat as needed.")
    parser.add_argument("--school-year", type=Path, help="School-year file for weekly timetables.")
    parser.add_argument("--from-date", type=date.fromisoformat, help="First date to generate for weekly timetables (default: publishing date).")
    parser.add_argument("--docs-root", type=Path)
    parser.add_argument("--cache-file", type=Path)
    return parser


def _settings(args: argparse.Namespace) -> dict:
    settings = dict(DEFAULTS)
    if args.profile:
        settings.update(load_profile(args.profile))
    if args.file or args.url:  # a source given on the command line replaces the profile's
        settings.pop("file", None)
        settings.pop("url", None)
    settings.update({key: value for key, value in vars(args).items() if value is not None and key != "profile"})
    for key in ("file", "school_year", "docs_root", "cache_file"):
        if settings.get(key) is not None:
            settings[key] = Path(settings[key])
    return settings


def main(argv: list[str] | None = None) -> int:
    settings = _settings(build_parser().parse_args(argv))
    for key in ("domain", "semester"):
        if not settings.get(key):
            raise SystemExit(f"Missing --{key} (or '{key}' in the profile).")
    if settings.get("file"):
        source_path = settings["file"]
    elif settings.get("url"):
        source_path = _download(settings["url"], settings["cache_file"])
    else:
        raise SystemExit("Give a PDF with --file or --url (or 'url' in the profile).")
    if not source_path.exists():
        raise FileNotFoundError(f"Schedule PDF not found: {source_path}")

    schedule_parser = detect_parser(source_path) if settings["format"] == "auto" else get_parser(settings["format"])
    print(f"Format: {schedule_parser.name}")

    available = schedule_parser.available_feeds(source_path)
    feeds = settings.get("feeds") or _choose(f"Choose {schedule_parser.feed_label}(s)", available)
    lookup = {value.casefold(): value for value in available}
    invalid = [feed for feed in feeds if feed.casefold() not in lookup]
    if invalid:
        raise ValueError(f"PDF has no {schedule_parser.feed_label} {', '.join(invalid)}. Available: {', '.join(available)}")
    feeds = [lookup[feed.casefold()] for feed in feeds]

    result = schedule_parser.parse(source_path, {**settings, "feeds": feeds})
    published = settings.get("published_date") or result.published_date
    if published is None:
        raise SystemExit("Missing --published-date: the PDF does not state when it was published.")

    selected_events = [event for event in result.events if event.feed_key in feeds]
    available_optionals = sorted({event.optional_group for event in selected_events if event.optional_group is not None})
    optionals = settings.get("optional")
    if optionals is None and available_optionals and sys.stdin.isatty():
        answer = input(f"Optional groups available: {', '.join(map(str, available_optionals))}. Include (comma-separated, blank for none): ").strip()
        optionals = [int(value.strip()) for value in answer.split(",") if value.strip()]
    optionals = optionals or []
    selected_events = [
        event for event in selected_events if event.optional_group is None or event.optional_group in optionals
    ]

    for feed in feeds:
        feed_events = [event for event in selected_events if event.feed_key == feed]
        if not feed_events:
            print(f"No events for {schedule_parser.feed_label} {feed}; nothing written.", file=sys.stderr)
            continue
        class_type = settings.get("class_type") or _slug(feed)
        metadata = FeedMetadata(
            settings["domain"], class_type, feed_events[0].year, settings["semester"], settings["location"],
            published, schedule_parser.naming, feed,
        )
        dated_path, current_path = metadata.output_paths(settings["docs_root"])
        dated_path.parent.mkdir(parents=True, exist_ok=True)
        content = render_ics(feed_events, metadata)
        dated_path.write_text(content, encoding="utf-8", newline="")
        current_path.write_text(content, encoding="utf-8", newline="")
        print(f"Wrote {len(feed_events)} events: {dated_path}")
        print(f"Updated stable feed: {current_path}")

    for item in result.reviews:
        print(f"REVIEW [page {item.source_page}]: {item.message}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
