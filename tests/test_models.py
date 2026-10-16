from datetime import date
from pathlib import Path

from calendars.models import FeedMetadata


def test_feed_naming_matches_the_agreed_convention() -> None:
    metadata = FeedMetadata("history", "id", 2, 1, "iasi", date(2026, 10, 5))

    dated, current = metadata.output_paths(Path("docs"))

    assert dated == Path("docs/history-id/history-calendar-2-1-iasi-2026-10-05.ics")
    assert current == Path("docs/history-id/history-calendar-2-1-iasi-current.ics")

