from datetime import date
from pathlib import Path

from calendars.school_year import load_school_year

SCHOOL_YEAR = Path(__file__).parents[1] / "school-years" / "ro-2026-2027.yaml"


def test_teaching_days_skip_weekends_holidays_and_breaks() -> None:
    days = set(load_school_year(SCHOOL_YEAR).teaching_days(grade=9))

    assert date(2026, 9, 7) in days  # first day of school
    assert date(2026, 10, 5) not in days  # Ziua Educației
    assert date(2026, 10, 10) not in days  # Saturday
    assert date(2026, 10, 27) not in days  # autumn break
    assert date(2027, 2, 23) not in days  # February mobile week
    assert date(2027, 6, 18) in days  # last day for grade 9


def test_grade_specific_end_and_start_date() -> None:
    school_year = load_school_year(SCHOOL_YEAR)

    grade_12 = list(school_year.teaching_days(grade=12, start_from=date(2026, 9, 30)))

    assert grade_12[0] == date(2026, 9, 30)
    assert grade_12[-1] == date(2027, 6, 4)
