# UAIC calendar importer

This command-line tool converts a UAIC schedule PDF into a selective iCalendar
feed. It is designed for schedules that list several study years in one PDF.

It never imports every listed event by default: choose the year of study and,
where relevant, which optional groups to include. Entries without a date and
time are reported for review and are not added to the calendar.

## Install

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

## Generate a feed

Use a local file:

```powershell
calendar-import --file C:\Downloads\orar.pdf --domain history --class-type id --semester 1 --location iasi --published-date 2026-10-05
```

Or fetch the current PDF directly:

```powershell
calendar-import --url "https://history.uaic.ro/path/to/orar.pdf" --domain history --class-type id --semester 1 --location iasi --published-date 2026-10-05
```

If `--year` is omitted, the program lists detected years and asks which to
import. It then asks which optional groups to include. The corresponding
non-interactive form is:

```powershell
calendar-import --file C:\Downloads\orar.pdf --domain history --class-type id --year 2 --semester 1 --location iasi --published-date 2026-10-05 --optional 1
```

The command writes both a dated snapshot and a stable subscription alias:

```text
docs/history-id/history-calendar-2-1-iasi-2026-10-05.ics
docs/history-id/history-calendar-2-1-iasi-current.ics
```

Subscribe Outlook to the `-current.ics` URL after GitHub Pages is enabled.
The dated file is retained as a historical record.

## Optional classes

Optional subjects are visibly labelled `OPTIONAL -` in event titles, carry the
standard ICS `CATEGORIES:OPTIONAL` field, and retain their group number in the
description. This makes them distinguishable even in calendar apps that ignore
ICS categories.

## Notes

- The PDF is not copied into `docs/` or the public feed.
- Dates marked with an asterisk are imported but noted in the event description.
- Rows marked `Programare ulterioară` have no usable date/time and are listed in
  the review report instead of being guessed.

