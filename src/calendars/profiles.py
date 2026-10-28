"""Per-calendar settings files (``sources/<name>.yaml``).

A profile holds the options that otherwise go on the command line, so a feed
can be refreshed with ``calendar-import --profile <name>``. Command-line flags
always win over profile values.
"""

from __future__ import annotations

from pathlib import Path

import yaml

PROFILE_DIR = Path("sources")
KNOWN_KEYS = {
    "format", "file", "url", "domain", "class_type", "feeds", "semester", "location",
    "published_date", "optional", "school_year", "from_date", "docs_root", "cache_file",
}


def load_profile(name_or_path: str) -> dict:
    path = Path(name_or_path)
    if not path.suffix:
        path = PROFILE_DIR / f"{name_or_path}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Profile not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    unknown = set(data) - KNOWN_KEYS
    if unknown:
        raise ValueError(f"Unknown setting(s) in {path}: {', '.join(sorted(unknown))}")
    if "feeds" in data:
        data["feeds"] = [str(feed) for feed in data["feeds"]]
    for key in ("semester", "class_type", "domain", "location"):
        if key in data:
            data[key] = str(data[key]).lower()
    return data
