# Schedule PDF to calendar importer

This command-line tool converts class-schedule PDFs into selective iCalendar
feeds. It currently understands two layouts:

| Format       | Source                                         | Feeds per PDF        |
|--------------|------------------------------------------------|----------------------|
| `uaic`       | UAIC faculty schedules (dated sessions)        | one per study year   |
| `asc-weekly` | School timetables exported from aSc Timetables | one per class (page) |

The format is detected automatically; use `--format` to force one.

It never imports every listed event by default: choose the study year or
class and, where relevant, which optional groups to include. Entries without a
date and time are reported for review and are not added to the calendar.

## Install

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

## Profiles (recommended)

Each feed has a settings file in `sources/`. Refresh a feed with:

```powershell
calendar-import --profile history-id-2 --published-date 2026-10-05
calendar-import --profile liceul-varlaam-9b --file "C:\Downloads\orar clase.pdf"
```

Any command-line option overrides the profile. Profile keys use the option
names with underscores: `format`, `file`, `url`, `domain`, `class_type`,
`feeds`, `semester`, `location`, `published_date`, `optional`, `school_year`,
`from_date`, `docs_root`, `cache_file`.

## Command-line use

UAIC schedule (fetch the current PDF directly):

```powershell
calendar-import --url "https://history.uaic.ro/path/to/orar.pdf" --domain history --class-type id --year 2 --semester 1 --location iasi --published-date 2026-10-05 --optional 1
```

School timetable:

```powershell
calendar-import --file "orar clase.pdf" --domain liceul-varlaam --class 9B --semester full --school-year school-years/ro-2026-2027.yaml
```

If `--year` / `--class` is omitted, the program lists what the PDF contains and
asks. The command writes both a dated snapshot and a stable subscription alias:

```text
docs/history-id/history-calendar-2-1-iasi-2026-10-05.ics
docs/history-id/history-calendar-2-1-iasi-current.ics
docs/liceul-varlaam/liceul-varlaam-9b-calendar-full-iasi-2026-09-30.ics
docs/liceul-varlaam/liceul-varlaam-9b-calendar-full-iasi-current.ics
```

Subscribe Outlook to the `-current.ics` URL after GitHub Pages is enabled.
The dated file is retained as a historical record.

## School timetables

- The class is found by its page title (`9B`), not by page number.
- The publishing date is read from "Orar generat: …" on the PDF; events start
  on that date (override with `--from-date`).
- The weekly grid is repeated on every teaching day listed in the school-year
  file (`school-years/ro-2026-2027.yaml`): modules, holidays, and grades that
  finish early. Update the February break there once the county announces it.
- Split cells (e.g. French / German in the same period) become two overlapping
  events tagged `CATEGORIES:SPLIT`, each noting the parallel lesson.
- `--class-type` defaults to the class name in lowercase (`9b`).

## Optional classes (UAIC)

Optional subjects are visibly labelled `OPTIONAL -` in event titles, carry the
standard ICS `CATEGORIES:OPTIONAL` field, and retain their group number in the
description. This makes them distinguishable even in calendar apps that ignore
ICS categories.

## Adding a new PDF layout

1. Add a module in `src/calendars/parsers/` implementing the interface in
   `parsers/base.py` (`detect`, `available_feeds`, `parse`, plus a default
   `naming`).
2. Register it in `PARSERS` in `parsers/__init__.py`.
3. Add a profile in `sources/` and a test in `tests/`.

## Notes

- The PDF is not copied into `docs/` or the public feed (`*.pdf` is ignored).
  Tests that need a sample PDF look for it in `data/` and are skipped otherwise.
- Dates marked with an asterisk are imported but noted in the event description.
- Rows marked `Programare ulterioară` have no usable date/time and are listed in
  the review report instead of being guessed.
