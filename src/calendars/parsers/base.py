from __future__ import annotations

from pathlib import Path
from typing import Protocol

from ..models import Naming, ParseResult


class ScheduleParser(Protocol):
    name: str  # value used with --format and in profiles
    feed_label: str  # what one feed is, for prompts: "study year", "class"
    naming: Naming  # default output naming for this kind of schedule

    def detect(self, first_page_text: str) -> bool:
        """Return True if this parser recognises the PDF layout."""

    def available_feeds(self, pdf_path: Path) -> list[str]:
        """List the feeds the PDF contains (study years, class names, ...)."""

    def parse(self, pdf_path: Path, options: dict) -> ParseResult:
        """Return dated events. ``options`` holds profile/CLI settings such as
        the selected feeds or the school-year file."""
