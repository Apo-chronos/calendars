from __future__ import annotations

import hashlib
from datetime import datetime
from zoneinfo import ZoneInfo

from .models import FeedMetadata, ScheduleEvent

TIMEZONE = ZoneInfo("Europe/Bucharest")


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _fold(line: str) -> str:
    # RFC 5545 folds at 75 octets. This conservative character version keeps
    # ordinary Romanian schedule data readable in all common calendar clients.
    return "\r\n ".join(line[index : index + 73] for index in range(0, len(line), 73))


def _event_uid(event: ScheduleEvent, metadata: FeedMetadata) -> str:
    basis = "|".join((metadata.domain, metadata.class_type, str(event.year), event.date.isoformat(), event.start.isoformat(), event.subject))
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()[:24] + "@apostolachealin.github.io"


def render_ics(events: list[ScheduleEvent], metadata: FeedMetadata) -> str:
    now = datetime.now(tz=TIMEZONE).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//apostolachealin//UAIC Calendar Importer//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{_escape(metadata.domain.title())} {metadata.class_type.upper()} - Year {metadata.year}",
        "X-WR-TIMEZONE:Europe/Bucharest",
    ]
    for event in events:
        start = datetime.combine(event.date, event.start, tzinfo=TIMEZONE).strftime("%Y%m%dT%H%M%S")
        end = datetime.combine(event.date, event.end, tzinfo=TIMEZONE).strftime("%Y%m%dT%H%M%S")
        summary = event.subject
        description = [f"Instructor: {event.instructor or 'Not provided'}", f"Source page: {event.source_page}"]
        categories: list[str] = []
        if event.optional_group is not None:
            summary = f"OPTIONAL - {summary}"
            categories.append("OPTIONAL")
            description.append(f"Optional group: {event.optional_group}")
        if event.date_has_note:
            description.append("The source schedule marks this date with an asterisk.")
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

