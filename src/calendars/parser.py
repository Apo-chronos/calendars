from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import pdfplumber

from .models import ReviewItem, ScheduleEvent

DATE_RE = re.compile(r"^\d{2}\.\d{2}\.\d{4}\*?$")
TIME_RE = re.compile(r"(\d{2}:\d{2})\s*-\s*(\d{2}:\d{2})")
YEAR_RE = re.compile(r"\bAnul\s+(I|II|III|IV|V|VI)\b", re.IGNORECASE)
OPTIONAL_RE = re.compile(r"\(\s*optional\s*(\d+)?\s*\)", re.IGNORECASE)
ROMAN_YEARS = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6}

def _normalise(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("‐", "-").replace("–", "-")).strip()


def _line_text(words: list[dict]) -> list[tuple[float, str]]:
    lines: dict[int, list[dict]] = defaultdict(list)
    for word in words:
        lines[round(word["top"] / 3)].append(word)
    return [
        (min(item["top"] for item in line), " ".join(item["text"] for item in sorted(line, key=lambda item: item["x0"])))
        for line in lines.values()
    ]


def _headings(words: list[dict]) -> list[tuple[float, int]]:
    found: list[tuple[float, int]] = []
    for top, line in _line_text(words):
        match = YEAR_RE.search(line)
        if match:
            found.append((top, ROMAN_YEARS[match.group(1).upper()]))
    return sorted(found)


def _column_for(x0: float, column_breaks: tuple[float, ...]) -> int:
    for index, boundary in enumerate(column_breaks):
        if x0 < boundary:
            return index
    return len(column_breaks)


def _table_breaks(table: object) -> tuple[float, ...]:
    """Find the four interior vertical borders of a five-column timetable."""
    counts: dict[float, int] = defaultdict(int)
    for cell in table.cells:
        counts[cell[0]] += 1
        counts[cell[2]] += 1
    threshold = max(2, len(table.rows) // 2)
    candidates = sorted(value for value, count in counts.items() if count >= threshold)
    clusters: list[list[float]] = []
    for value in candidates:
        if not clusters or value - clusters[-1][-1] > 10:
            clusters.append([value])
        else:
            clusters[-1].append(value)
    borders = [min(cluster) for cluster in clusters]
    if len(borders) != 6:
        raise ValueError("Expected a five-column timetable table.")
    return tuple(borders[1:-1])


def _event_from_region(
    words: list[dict], *, date_text: str, column_breaks: tuple[float, ...], year: int, page_number: int, has_star: bool
) -> ScheduleEvent | None:
    fields: dict[int, list[dict]] = defaultdict(list)
    for word in words:
        fields[_column_for(word["x0"], column_breaks)].append(word)
    values = {
        column: _normalise(" ".join(word["text"] for word in sorted(items, key=lambda item: (item["top"], item["x0"]))))
        for column, items in fields.items()
    }
    time_match = TIME_RE.search(values.get(1, ""))
    if not time_match:
        return None

    subject = values.get(2, "")
    if subject.startswith("Disciplina "):
        subject = subject.removeprefix("Disciplina ")
    instructor = values.get(3, "").removeprefix("Cadru didactic ")
    location = values.get(4, "").removeprefix("Locație ")
    optional_match = OPTIONAL_RE.search(subject)
    optional_group = int(optional_match.group(1)) if optional_match and optional_match.group(1) else (1 if optional_match else None)
    return ScheduleEvent(
        date=datetime.strptime(date_text, "%d.%m.%Y").date(),
        start=datetime.strptime(time_match.group(1), "%H:%M").time(),
        end=datetime.strptime(time_match.group(2), "%H:%M").time(),
        subject=subject,
        instructor=instructor,
        location=location,
        year=year,
        optional_group=optional_group,
        source_page=page_number,
        date_has_note=has_star,
    )


def parse_schedule(pdf_path: Path) -> tuple[list[ScheduleEvent], list[ReviewItem]]:
    """Extract dated rows from the UAIC-style timetable PDF.

    Events are assembled by physical table row, not PDF text order. This keeps
    wrapped Romanian course names and instructor names in their correct fields.
    """
    events: list[ScheduleEvent] = []
    reviews: list[ReviewItem] = []
    current_year: int | None = None

    with pdfplumber.open(pdf_path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            words = page.extract_words(use_text_flow=False, keep_blank_chars=False)
            headings = _headings(words)
            for table in page.find_tables():
                left, top, right, bottom = table.bbox
                if right - left < 250:  # Ignore one-cell artifacts from merged cells.
                    continue
                try:
                    column_breaks = _table_breaks(table)
                except ValueError:
                    reviews.append(ReviewItem("Could not identify the five timetable columns.", page_number))
                    continue
                table_words = [word for word in words if left <= word["x0"] <= right and top <= word["top"] <= bottom]
                dates = sorted(
                    [word for word in table_words if DATE_RE.match(word["text"])],
                    key=lambda word: word["top"],
                )
                if not dates:
                    continue
                for heading_top, heading_year in headings:
                    if heading_top < top:
                        current_year = heading_year
                if current_year is None:
                    reviews.append(ReviewItem("Could not determine the study year for a table.", page_number))
                    continue

                for index, date_word in enumerate(dates):
                    # Date cells are vertically centred, while a course title
                    # can start above or below that word. The midpoint between
                    # neighboring date cells is a more reliable row boundary
                    # than PDF text order for wrapped table cells.
                    previous_top = dates[index - 1]["top"] if index else top
                    following_top = dates[index + 1]["top"] if index + 1 < len(dates) else bottom
                    row_start = (previous_top + date_word["top"]) / 2 if index else top
                    row_end = (date_word["top"] + following_top) / 2 if index + 1 < len(dates) else bottom + 1
                    later_before_row = [
                        word["top"]
                        for word in table_words
                        if word["text"].casefold() == "programare" and previous_top < word["top"] < date_word["top"]
                    ]
                    if later_before_row:
                        row_start = max(row_start, date_word["top"] - 10)
                    region = [word for word in table_words if row_start <= word["top"] < row_end]
                    later_rows = [word["top"] for word in region if word["text"].casefold() == "programare"]
                    if later_rows:
                        # A row labelled "Programare ulterioară" has no date or
                        # time. Do not accidentally append it to the preceding
                        # class when the PDF omits a visual gap between rows.
                        region = [word for word in region if word["top"] < min(later_rows)]
                    event = _event_from_region(
                        region,
                        date_text=date_word["text"].rstrip("*"),
                        column_breaks=column_breaks,
                        year=current_year,
                        page_number=page_number,
                        has_star=date_word["text"].endswith("*"),
                    )
                    if event:
                        events.append(event)
                    else:
                        reviews.append(ReviewItem(f"Could not read the row dated {date_word['text']}.", page_number))

            page_text = page.extract_text() or ""
            if "Programare" in page_text and "ulterioară" in page_text:
                reviews.append(ReviewItem("One or more rows are scheduled later and were not imported.", page_number))

    events.sort(key=lambda event: (event.year, event.date, event.start, event.subject))
    return events, reviews

