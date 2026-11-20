"""CSV import/export and iCalendar (.ics) export."""

from __future__ import annotations

import csv
import io
from datetime import date, datetime, timezone
from typing import List, Tuple

from .config import MAX_CSV_BYTES
from .models import FIELDS, Meeting, local_datetime, prepare_meeting

_HEADER_ALIASES = {
    "Meeting": ("meeting", "title"),
    "Start": ("start", "start time"),
    "End": ("end", "end time"),
    "Location": ("location",),
    "Description": ("description",),
    "Attendees": ("attendees",),
}
_REQUIRED = ("Meeting", "Start", "End")


# ----------------------------------------------------------------------------
# CSV
# ----------------------------------------------------------------------------
def parse_meetings_csv(file_bytes: bytes) -> Tuple[List[Meeting], List[str]]:
    """Parse an uploaded CSV. Returns (valid meetings, error messages)."""
    if len(file_bytes) > MAX_CSV_BYTES:
        return [], ["The CSV is larger than {} KB.".format(MAX_CSV_BYTES // 1000)]
    try:
        text = file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        return [], ["Could not read the CSV as UTF-8. Save it as UTF-8 and retry."]

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return [], ["The uploaded CSV is empty."]

    headers = {h.strip().lower(): h for h in reader.fieldnames if h}
    columns = {
        field: next((headers[a] for a in aliases if a in headers), None)
        for field, aliases in _HEADER_ALIASES.items()
    }
    if not all(columns[field] for field in _REQUIRED):
        return [], ["Required headers: Meeting, Start, End. Optional: Location, Description, Attendees."]

    meetings, errors = [], []
    for row_number, row in enumerate(reader, start=2):
        if not any((value or "").strip() for value in row.values() if isinstance(value, str)):
            continue
        raw = {field: row.get(col) if col else "" for field, col in columns.items()}
        meeting, error = prepare_meeting(raw)
        if error:
            errors.append("Row {}: {}".format(row_number, error))
        else:
            meetings.append(meeting)
    return meetings, errors


def build_csv(meetings: List[Meeting]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(FIELDS), extrasaction="ignore")
    writer.writeheader()
    writer.writerows(meetings)
    return output.getvalue()


# ----------------------------------------------------------------------------
# iCalendar
# ----------------------------------------------------------------------------
def _ics_escape(value: str) -> str:
    return (
        str(value or "")
        .replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
        .replace("\r", "\\n")
    )


def _ics_fold(line: str) -> str:
    """Fold a content line to at most 75 octets, as required by RFC 5545."""
    if len(line.encode("utf-8")) <= 75:
        return line
    parts, current, size = [], "", 0
    for char in line:
        width = len(char.encode("utf-8"))
        limit = 75 if not parts else 74  # continuation lines start with a space
        if size + width > limit:
            parts.append(current)
            current, size = char, width
        else:
            current += char
            size += width
    parts.append(current)
    return "\r\n ".join(parts)


def _ics_utc(schedule_date: date, hhmm: str) -> str:
    return local_datetime(schedule_date, hhmm).astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def build_ics(meetings: List[Meeting], schedule_date: date) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//DAA Midterm//Meeting Scheduler//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]
    for item in meetings:
        lines += [
            "BEGIN:VEVENT",
            "UID:{}-{}@daa_midterm.local".format(item["id"], schedule_date.isoformat()),
            "DTSTAMP:" + stamp,
            "DTSTART:" + _ics_utc(schedule_date, item["Start"]),
            "DTEND:" + _ics_utc(schedule_date, item["End"]),
            "SUMMARY:" + _ics_escape(item["Meeting"]),
            "LOCATION:" + _ics_escape(item.get("Location", "")),
            "DESCRIPTION:" + _ics_escape(item.get("Description", "")),
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "\r\n".join(_ics_fold(line) for line in lines) + "\r\n"
