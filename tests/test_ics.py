import re
from datetime import date, time

from calendars.ics import _fold, render_ics
from calendars.models import FeedMetadata, ScheduleEvent


def test_optional_event_is_visibly_and_semantically_marked() -> None:
    event = ScheduleEvent(date(2026, 10, 17), time(16), time(20), "Introducere în muzeologie (optional 1)", "Vasile Cotiugă", "Cabinet Corp H", 2, 1, 1)
    metadata = FeedMetadata("history", "id", 2, 1, "iasi", date(2026, 10, 5))

    output = render_ics([event], metadata)

    assert "SUMMARY:OPTIONAL - Introducere în muzeologie" in output
    assert "CATEGORIES:OPTIONAL" in output
    assert "Optional group: 1" in output


def test_feed_declares_timezone_and_utc_timestamp() -> None:
    metadata = FeedMetadata("history", "id", 2, 1, "iasi", date(2026, 10, 5))
    event = ScheduleEvent(date(2026, 10, 17), time(16), time(20), "Curs", "", "Online", 2)

    output = render_ics([event], metadata)

    assert "BEGIN:VTIMEZONE\r\nTZID:Europe/Bucharest" in output
    assert re.search(r"DTSTAMP:\d{8}T\d{6}Z", output)


def test_lines_are_folded_at_75_octets() -> None:
    folded = _fold("DESCRIPTION:" + "ăîșțâ" * 40)

    assert all(len(line.encode("utf-8")) <= 75 for line in folded.split("\r\n"))
    assert folded.replace("\r\n ", "") == "DESCRIPTION:" + "ăîșțâ" * 40
