from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from .models import FeedMetadata, ScheduleEvent

TIMEZONE = ZoneInfo("Europe/Bucharest")

# Calendar clients (Outlook in particular) expect a VTIMEZONE block for every
# TZID used. Romania follows the EU rules: last Sunday of March and October.
VTIMEZONE = [
    "BEGIN:VTIMEZONE",
    "TZID:Europe/Bucharest",
    "BEGIN:DAYLIGHT",
    "TZOFFSETFROM:+0200",
    "TZOFFSETTO:+0300",
    "TZNAME:EEST",
    "DTSTART:19700329T030000",
    "RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU",
    "END:DAYLIGHT",
    "BEGIN:STANDARD",
    "TZOFFSETFROM:+0300",
    "TZOFFSETTO:+0200",
    "TZNAME:EET",
    "DTSTART:19701025T040000",
    "RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU",
    "END:STANDARD",
    "END:VTIMEZONE",
]


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _fold(line: str, limit: int = 75) -> str:
    """Fold at 75 octets (RFC 5545 3.1) without splitting a UTF-8 character."""
    parts: list[str] = []
    current, size = "", 0
    for character in line:
        width = len(character.encode("utf-8"))
        # Continuation lines start with a space, which counts toward the limit.
        if size + width > limit:
            parts.append(current)
            current, size = character, 1 + width
        else:
            current += character
            size += width
    parts.append(current)
    return "\r\n ".join(parts)


def _event_uid(event: ScheduleEvent, metadata: FeedMetadata) -> str:
    basis = "|".join((metadata.domain, metadata.class_type, str(event.year), event.date.isoformat(), event.start.isoformat(), event.subject))
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()[:24] + "@apo-chronos.github.io"


def render_ics(events: list[ScheduleEvent], metadata: FeedMetadata) -> str:
    now = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//apo-chronos//UAIC Calendar Importer//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{_escape(metadata.calendar_name)}",
        "X-WR-TIMEZONE:Europe/Bucharest",
        *VTIMEZONE,
    ]
    for event in events:
        start = datetime.combine(event.date, event.start, tzinfo=TIMEZONE).strftime("%Y%m%dT%H%M%S")
        end = datetime.combine(event.date, event.end, tzinfo=TIMEZONE).strftime("%Y%m%dT%H%M%S")
        summary = event.subject
        description = [f"Instructor: {event.instructor or 'Not provided'}", f"Source page: {event.source_page}"]
        categories: list[str] = list(event.categories)
        if event.optional_group is not None:
            summary = f"OPTIONAL - {summary}"
            categories.append("OPTIONAL")
            description.append(f"Optional group: {event.optional_group}")
        if event.date_has_note:
            description.append("The source schedule marks this date with an asterisk.")
        description.extend(event.notes)
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{_event_uid(event, metadata)}",
                f"DTSTAMP:{now}",
                f"DTSTART;TZID=Europe/Bucharest:{start}",
                f"DTEND;TZID=Europe/Bucharest:{end}",
                f"SUMMARY:{_escape(summary)}",
                f"LOCATION:{_escape(event.location)}",
                f"DESCRIPTION:{_escape(chr(10).join(description))}",
                *( [f"CATEGORIES:{','.join(categories)}"] if categories else [] ),
                "END:VEVENT",
            ]
        )
    lines.append("END:VCALENDAR")
    return "\r\n".join(_fold(line) for line in lines) + "\r\n"
