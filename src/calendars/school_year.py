"""School-year structure (teaching modules, holidays) loaded from YAML."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import yaml


@dataclass(frozen=True)
class SchoolYear:
    name: str
    modules: tuple[tuple[date, date], ...]
    holidays: dict[date, str]
    grade_end_dates: dict[int, date]

    def teaching_days(self, grade: int | None = None, start_from: date | None = None) -> Iterator[date]:
        """Yield Monday-Friday dates inside a module that are not holidays."""
        last_day = self.grade_end_dates.get(grade) if grade is not None else None
        for module_start, module_end in self.modules:
            day = max(module_start, start_from) if start_from else module_start
            end = min(module_end, last_day) if last_day else module_end
            while day <= end:
                if day.weekday() < 5 and day not in self.holidays:
                    yield day
                day += timedelta(days=1)


def load_school_year(path: Path) -> SchoolYear:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return SchoolYear(
        name=data["name"],
        modules=tuple((item["start"], item["end"]) for item in data["modules"]),
        holidays={item["date"]: item.get("name", "") for item in data.get("holidays", [])},
        grade_end_dates={int(grade): end for grade, end in (data.get("grade_end_dates") or {}).items()},
    )
