from datetime import date
from pathlib import Path

from calendars.models import SCHOOL_NAMING, FeedMetadata


def test_feed_naming_matches_the_agreed_convention() -> None:
    metadata = FeedMetadata("history", "id", 2, 1, "iasi", date(2026, 10, 5))

    dated, current = metadata.output_paths(Path("docs"))

    assert dated == Path("docs/history-id/history-calendar-2-1-iasi-2026-10-05.ics")
    assert current == Path("docs/history-id/history-calendar-2-1-iasi-current.ics")


def test_school_feed_naming() -> None:
    metadata = FeedMetadata("liceul-varlaam", "9b", 9, "full", "iasi", date(2026, 9, 30), SCHOOL_NAMING, "9B")

    dated, current = metadata.output_paths(Path("docs"))

    assert dated == Path("docs/liceul-varlaam/liceul-varlaam-9b-calendar-full-iasi-2026-09-30.ics")
    assert current == Path("docs/liceul-varlaam/liceul-varlaam-9b-calendar-full-iasi-current.ics")
    assert metadata.calendar_name == "Liceul Varlaam 9B"
