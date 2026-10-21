from datetime import date, time
from pathlib import Path

import pytest

from calendars.parsers import detect_parser
from calendars.parsers.asc_weekly import AscWeeklyParser, classify_cell, read_timetable, tidy_subject

ROOT = Path(__file__).parents[1]
SAMPLE = ROOT / "data" / "orar clase.pdf"  # not committed (*.pdf is ignored)


def _word(text: str, size: float, top: float, x0: float = 0) -> dict:
    return {"text": text, "size": size, "top": top, "bottom": top + size, "x0": x0, "x1": x0 + 10}


def test_cell_text_is_split_into_subject_teacher_and_room() -> None:
    words = [
        _word("Sala", 6.9, 120, 0), _word("Albastră", 6.9, 120, 20),
        _word("LIMBA", 12.1, 140, 0), _word("ȘI", 12.1, 140, 40),
        _word("LITERATURA", 12.1, 154, 0), _word("ROMÂNĂ", 12.1, 168, 0),
        _word("Alina", 8.7, 195, 0), _word("Andrei", 8.7, 195, 30),
    ]

    assert classify_cell(words) == ("Limba și literatura română", "Alina Andrei", "Sala Albastră")


def test_short_acronyms_keep_their_case() -> None:
    assert tidy_subject("TIC") == "TIC"
    assert tidy_subject("EDUCAȚIE FIZICĂ") == "Educație fizică"


@pytest.mark.skipif(not SAMPLE.exists(), reason="sample school PDF not present in data/")
def test_9b_page_from_sample_pdf() -> None:
    assert detect_parser(SAMPLE).name == "asc-weekly"
    pages, reviews, generated = read_timetable(SAMPLE)
    assert generated == date(2026, 9, 30) and not reviews
    page = next(page for page in pages if page.name == "9B")
    wednesday_5 = [slot for slot in page.slots if slot.weekday == 2 and slot.start == time(12, 40)]
    assert {slot.subject for slot in wednesday_5} == {"Limba franceză", "Limba germană"}
    assert all(slot.split for slot in wednesday_5)

    result = AscWeeklyParser().parse(SAMPLE, {"feeds": ["9b"], "school_year": ROOT / "school-years" / "ro-2026-2027.yaml"})
    assert {event.feed for event in result.events} == {"9B"}
    assert result.events[0].date == date(2026, 9, 30)
