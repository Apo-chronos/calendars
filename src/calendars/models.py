from __future__ import annotations

from dataclasses import dataclass, field
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
    # Which feed the event belongs to: the study year for UAIC PDFs ("2"),
    # the class name for school timetables ("9B"). Defaults to the year.
    feed: str = ""
    notes: tuple[str, ...] = ()
    categories: tuple[str, ...] = ()

    @property
    def feed_key(self) -> str:
        return self.feed or str(self.year)


@dataclass(frozen=True)
class ReviewItem:
    message: str
    source_page: int


@dataclass(frozen=True)
class ParseResult:
    events: list[ScheduleEvent]
    reviews: list[ReviewItem] = field(default_factory=list)
    # Values read from the PDF itself, e.g. the date the timetable was generated.
    published_date: date | None = None


@dataclass(frozen=True)
class Naming:
    """File-name templates. Placeholders: domain, class_type, year, semester,
    location, stamp (the publishing date, or "current"), feed."""

    directory: str
    filename: str
    calendar_name: str


# The original convention, used for UAIC faculty schedules.
UAIC_NAMING = Naming(
    directory="{domain}-{class_type}",
    filename="{domain}-calendar-{year}-{semester}-{location}-{stamp}.ics",
    calendar_name="{domain_title} {class_type_upper} - Year {year}",
)

# School timetables: one folder per school, one feed per class.
SCHOOL_NAMING = Naming(
    directory="{domain}",
    filename="{domain}-{class_type}-calendar-{semester}-{location}-{stamp}.ics",
    calendar_name="{domain_title} {class_type_upper}",
)


@dataclass(frozen=True)
class FeedMetadata:
    domain: str
    class_type: str
    year: int
    semester: int | str
    location: str
    published_date: date
    naming: Naming = UAIC_NAMING
    feed: str = ""

    def _values(self, stamp: str) -> dict[str, str]:
        return {
            "domain": self.domain,
            "class_type": self.class_type,
            "year": str(self.year),
            "semester": str(self.semester),
            "location": self.location,
            "stamp": stamp,
            "feed": self.feed,
            "domain_title": self.domain.replace("-", " ").title(),
            "class_type_upper": self.class_type.upper(),
        }

    @property
    def directory_name(self) -> str:
        return self.naming.directory.format(**self._values(""))

    @property
    def dated_filename(self) -> str:
        return self.naming.filename.format(**self._values(self.published_date.isoformat()))

    @property
    def current_filename(self) -> str:
        return self.naming.filename.format(**self._values("current"))

    @property
    def calendar_name(self) -> str:
        return self.naming.calendar_name.format(**self._values(""))

    def output_paths(self, docs_root: Path) -> tuple[Path, Path]:
        feed_dir = docs_root / self.directory_name
        return feed_dir / self.dated_filename, feed_dir / self.current_filename
