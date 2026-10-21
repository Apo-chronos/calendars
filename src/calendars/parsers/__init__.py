"""PDF schedule parsers.

Every parser exposes the same small interface (see ``base.ScheduleParser``).
To support a new kind of PDF, add a module here and register it in PARSERS.
"""

from __future__ import annotations

from pathlib import Path

import pdfplumber

from .asc_weekly import AscWeeklyParser
from .base import ScheduleParser
from .uaic_dated import UaicDatedParser

PARSERS: dict[str, ScheduleParser] = {
    parser.name: parser for parser in (UaicDatedParser(), AscWeeklyParser())
}


def get_parser(name: str) -> ScheduleParser:
    try:
        return PARSERS[name]
    except KeyError:
        raise ValueError(f"Unknown format '{name}'. Available: {', '.join(PARSERS)}") from None


def detect_parser(pdf_path: Path) -> ScheduleParser:
    with pdfplumber.open(pdf_path) as pdf:
        first_page_text = (pdf.pages[0].extract_text() or "") if pdf.pages else ""
    for parser in PARSERS.values():
        if parser.detect(first_page_text):
            return parser
    raise ValueError("Could not recognise this PDF layout. Pass --format explicitly.")
