from datetime import date, time

from calendars.ics import render_ics
from calendars.models import FeedMetadata, ScheduleEvent


def test_optional_event_is_visibly_and_semantically_marked() -> None:
    event = ScheduleEvent(date(2026, 10, 17), time(16), time(20), "Introducere în muzeologie (optional 1)", "Vasile Cotiugă", "Cabinet Corp H", 2, 1, 1)
    metadata = FeedMetadata("history", "id", 2, 1, "iasi", date(2026, 10, 5))

    output = render_ics([event], metadata)

    assert "SUMMARY:OPTIONAL - Introducere în muzeologie" in output
    assert "CATEGORIES:OPTIONAL" in output
    assert "Optional group: 1" in output

