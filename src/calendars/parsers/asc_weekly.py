"""Weekly school timetables exported from aSc Timetables (one class per page).

Each page is a grid: days (Lu, Ma, Mi, Jo, Vi) down the side, numbered periods
with their times across the top. A lesson cell holds three text sizes: the room
in small print at the top, the subject in large print, and the teacher below
it. A cell may be split vertically when two groups (e.g. French / German) have
lessons at the same time; both halves are kept as overlapping events.

The weekly grid is turned into dated events using a school-year file
(teaching modules and holidays, see ``school-years/``).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path

import pdfplumber

from ..models import SCHOOL_NAMING, ParseResult, ReviewItem, ScheduleEvent
from ..school_year import load_school_year

DAYS = {"lu": 0, "ma": 1, "mi": 2, "jo": 3, "vi": 4, "sâ": 5, "sa": 5}
TIME_RE = re.compile(r"(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})")
GENERATED_RE = re.compile(r"Orar generat:\s*(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})")
CLASS_RE = re.compile(r"^(\d{1,2})\s*([A-Za-z]*)$")
SPLIT_RATIO = 0.75  # a cell shorter than this share of its day row is a split cell


@dataclass(frozen=True)
class WeeklySlot:
    weekday: int
    start: time
    end: time
    subject: str
    teacher: str
    room: str
    split: bool
    page: int


@dataclass(frozen=True)
class ClassPage:
    name: str  # e.g. "9B"
    header: str  # school name and address line
    slots: tuple[WeeklySlot, ...]
    page: int


def _centre(box: tuple[float, float, float, float]) -> tuple[float, float]:
    return (box[0] + box[2]) / 2, (box[1] + box[3]) / 2


def _inside(word: dict, box: tuple[float, float, float, float]) -> bool:
    x = (word["x0"] + word["x1"]) / 2
    y = (word["top"] + word["bottom"]) / 2
    return box[0] <= x <= box[2] and box[1] <= y <= box[3]


def _join(words: list[dict]) -> str:
    """Join words in reading order, grouping words of similar height into lines."""
    lines: list[list[dict]] = []
    for word in sorted(words, key=lambda item: item["top"]):
        if lines and abs(word["top"] - lines[-1][0]["top"]) < 3:
            lines[-1].append(word)
        else:
            lines.append([word])
    text = " ".join(" ".join(item["text"] for item in sorted(line, key=lambda item: item["x0"])) for line in lines)
    return re.sub(r"\s+", " ", text).strip()


def tidy_subject(subject: str) -> str:
    """'LIMBA ȘI LITERATURA ROMÂNĂ' -> 'Limba și literatura română'; keep short acronyms like 'TIC'."""
    if subject.isupper() and (" " in subject or len(subject) > 4):
        return subject.capitalize()
    return subject


def classify_cell(words: list[dict]) -> tuple[str, str, str]:
    """Split a lesson cell's words into (subject, teacher, room) by font size and position."""
    if not words:
        return "", "", ""
    largest = max(word["size"] for word in words)
    subject_words = [word for word in words if word["size"] >= largest - 0.5]
    others = [word for word in words if word["size"] < largest - 0.5]
    subject_top = min(word["top"] for word in subject_words)
    room = [word for word in others if word["bottom"] <= subject_top + 1]
    teacher = [word for word in others if word not in room]
    return tidy_subject(_join(subject_words)), _join(teacher), _join(room)


def _read_page(page: pdfplumber.page.Page, page_number: int) -> tuple[ClassPage | None, list[ReviewItem]]:
    reviews: list[ReviewItem] = []
    text_lines = [line.strip() for line in (page.extract_text() or "").splitlines() if line.strip()]
    if not text_lines:
        return None, reviews
    tables = page.find_tables()
    if not tables:
        reviews.append(ReviewItem("No timetable grid found on this page.", page_number))
        return None, reviews
    table = max(tables, key=lambda item: (item.bbox[2] - item.bbox[0]) * (item.bbox[3] - item.bbox[1]))
    left, top = table.bbox[0], table.bbox[1]
    words = page.extract_words(extra_attrs=["size"])

    # Header row: one cell per period, holding "N." and "HH:MM - HH:MM".
    periods: list[tuple[float, float, time, time]] = []
    # First column: one cell per day, holding the day label.
    days: list[tuple[float, float, int]] = []
    lessons = []
    for cell in table.cells:
        cell_words = [word for word in words if _inside(word, cell)]
        if abs(cell[1] - top) < 2:
            match = TIME_RE.search(_join(cell_words))
            if match:
                periods.append((cell[0], cell[2], *(datetime.strptime(value, "%H:%M").time() for value in match.groups())))
        elif abs(cell[0] - left) < 2:
            label = _join(cell_words).casefold()[:2]
            if label in DAYS:
                days.append((cell[1], cell[3], DAYS[label]))
        else:
            lessons.append((cell, cell_words))

    if not periods or not days:
        reviews.append(ReviewItem("Could not identify the period times or day rows.", page_number))
        return None, reviews

    slots: list[WeeklySlot] = []
    for cell, cell_words in lessons:
        subject, teacher, room = classify_cell(cell_words)
        if not subject:
            continue
        x, y = _centre(cell)
        day = next(((day_top, day_bottom, weekday) for day_top, day_bottom, weekday in days if day_top <= y <= day_bottom), None)
        covered = sorted((start, end) for x0, x1, start, end in periods if cell[0] - 1 <= (x0 + x1) / 2 <= cell[2] + 1)
        if day is None or not covered:
            reviews.append(ReviewItem(f"Could not place the cell '{subject}' in the grid.", page_number))
            continue
        day_top, day_bottom, weekday = day
        split = (cell[3] - cell[1]) < SPLIT_RATIO * (day_bottom - day_top)
        # A cell spanning several columns is a double lesson.
        slots.append(WeeklySlot(weekday, covered[0][0], covered[-1][1], subject, teacher, room, split, page_number))

    slots.sort(key=lambda slot: (slot.weekday, slot.start, slot.subject))
    header = next((line for line in text_lines[1:3] if "," in line), "")
    header = re.sub(r"\s+Diriginte(le)?:.*$", "", header).strip()
    return ClassPage(text_lines[0], header, tuple(slots), page_number), reviews


def read_timetable(pdf_path: Path) -> tuple[list[ClassPage], list[ReviewItem], date | None]:
    pages: list[ClassPage] = []
    reviews: list[ReviewItem] = []
    generated: date | None = None
    with pdfplumber.open(pdf_path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            class_page, page_reviews = _read_page(page, page_number)
            reviews.extend(page_reviews)
            if class_page:
                pages.append(class_page)
            match = GENERATED_RE.search(page.extract_text() or "")
            if match and generated is None:
                day, month, year = map(int, match.groups())
                generated = date(year, month, day)
    return pages, reviews, generated


def _grade(class_name: str) -> int:
    match = CLASS_RE.match(class_name.strip())
    if not match:
        raise ValueError(f"Cannot read the grade from class name '{class_name}'.")
    return int(match.group(1))


def expand(class_page: ClassPage, school_year_path: Path, start_from: date | None) -> list[ScheduleEvent]:
    """Repeat the weekly slots on every teaching day of the school year."""
    school_year = load_school_year(school_year_path)
    grade = _grade(class_page.name)
    by_weekday: dict[int, list[WeeklySlot]] = {}
    for slot in class_page.slots:
        by_weekday.setdefault(slot.weekday, []).append(slot)

    events: list[ScheduleEvent] = []
    for day in school_year.teaching_days(grade, start_from):
        for slot in by_weekday.get(day.weekday(), []):
            notes: list[str] = []
            categories: tuple[str, ...] = ()
            if slot.split:
                parallel = [
                    other.subject
                    for other in by_weekday[slot.weekday]
                    if other is not slot and other.split and other.start < slot.end and slot.start < other.end
                ]
                notes.append(f"Split slot: runs in parallel with {', '.join(parallel) or 'another group'}.")
                categories = ("SPLIT",)
            location = ", ".join(part for part in (slot.room, class_page.header) if part)
            events.append(
                ScheduleEvent(
                    date=day,
                    start=slot.start,
                    end=slot.end,
                    subject=slot.subject,
                    instructor=slot.teacher,
                    location=location,
                    year=grade,
                    source_page=slot.page,
                    feed=class_page.name,
                    notes=tuple(notes),
                    categories=categories,
                )
            )
    return events


class AscWeeklyParser:
    name = "asc-weekly"
    feed_label = "class"
    naming = SCHOOL_NAMING

    def detect(self, first_page_text: str) -> bool:
        return "aSc Timetables" in first_page_text or bool(GENERATED_RE.search(first_page_text))

    def available_feeds(self, pdf_path: Path) -> list[str]:
        pages, _, _ = read_timetable(pdf_path)
        return [page.name for page in pages]

    def parse(self, pdf_path: Path, options: dict) -> ParseResult:
        school_year = options.get("school_year")
        if not school_year:
            raise ValueError("Weekly timetables need a school-year file (--school-year or 'school_year' in the profile).")
        pages, reviews, generated = read_timetable(pdf_path)
        wanted = {feed.casefold() for feed in options.get("feeds") or []}
        start_from = options.get("from_date") or options.get("published_date") or generated
        events: list[ScheduleEvent] = []
        for class_page in pages:
            if wanted and class_page.name.casefold() not in wanted:
                continue
            events.extend(expand(class_page, Path(school_year), start_from))
        events.sort(key=lambda event: (event.feed, event.date, event.start, event.subject))
        return ParseResult(events, reviews, generated)
