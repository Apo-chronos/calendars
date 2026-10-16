from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time
from pathlib import Path


@dataclass(frozen=True)
class ScheduleEvent:
    date: date
    start: time
    end: time
    subject: str
    instructor: str
    location: str
    year: int
    optional_group: int | None = None
    source_page: int = 0
    date_has_note: bool = False


@dataclass(frozen=True)
class ReviewItem:
    message: str
    source_page: int


@dataclass(frozen=True)
class FeedMetadata:
    domain: str
    class_type: str
    year: int
    semester: int
    location: str
    published_date: date

    @property
    def directory_name(self) -> str:
        return f"{self.domain}-{self.class_type}"

    @property
    def dated_filename(self) -> str:
        return (
            f"{self.domain}-calendar-{self.year}-{self.semester}-"
            f"{self.location}-{self.published_date.isoformat()}.ics"
        )

    @property
    def current_filename(self) -> str:
        return (
            f"{self.domain}-calendar-{self.year}-{self.semester}-"
            f"{self.location}-current.ics"
        )

    def output_paths(self, docs_root: Path) -> tuple[Path, Path]:
        feed_dir = docs_root / self.directory_name
        return feed_dir / self.dated_filename, feed_dir / self.current_filename

