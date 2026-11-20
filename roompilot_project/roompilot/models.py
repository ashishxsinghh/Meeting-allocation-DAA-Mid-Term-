"""Meeting data model: normalization, validation and time helpers."""

from __future__ import annotations

import re
import uuid
from datetime import date, datetime, time
from typing import Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from .config import LOCAL_TZ

Meeting = Dict[str, str]

FIELDS = ("Meeting", "Start", "End", "Location", "Description", "Attendees")
_EMAIL_RE = re.compile(r"^[^@\s,;]+@[^@\s,;]+\.[^@\s,;]+$")


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def _clean(value) -> str:
    if value is None or (isinstance(value, float) and value != value):  # None / NaN
        return ""
    return str(value).strip()


def normalize_meeting(item: Dict) -> Meeting:
    """Return a meeting with an id and every field as a stripped string."""
    meeting = {"id": _clean(item.get("id")) or new_id()}
    for field in FIELDS:
        meeting[field] = _clean(item.get(field))
    return meeting


# ----------------------------------------------------------------------------
# Time helpers
# ----------------------------------------------------------------------------
def to_minutes(value) -> int:
    """Convert 'HH:MM' (24-hour) to minutes after midnight."""
    try:
        parsed = datetime.strptime(_clean(value), "%H:%M")
    except ValueError:
        raise ValueError("Time must use HH:MM 24-hour format, e.g. 09:30.") from None
    return parsed.hour * 60 + parsed.minute


def to_hhmm(minutes: int) -> str:
    return "{:02d}:{:02d}".format(minutes // 60, minutes % 60)


def local_datetime(schedule_date: date, hhmm: str) -> datetime:
    """Timezone-aware datetime for a meeting time on the given date."""
    hour, minute = divmod(to_minutes(hhmm), 60)
    return datetime.combine(schedule_date, time(hour, minute), tzinfo=ZoneInfo(LOCAL_TZ))


# ----------------------------------------------------------------------------
# Email helpers
# ----------------------------------------------------------------------------
def parse_emails(text: str) -> List[str]:
    return [part.strip() for part in re.split(r"[,;]", text or "") if part.strip()]


def is_valid_email(value: str) -> bool:
    return bool(_EMAIL_RE.match(value))


# ----------------------------------------------------------------------------
# Validation
# ----------------------------------------------------------------------------
def prepare_meeting(raw: Dict, validate_emails: bool = True) -> Tuple[Optional[Meeting], Optional[str]]:
    """Normalize and validate a meeting.

    Returns (meeting, None) on success or (None, error_message) on failure.
    Times are rewritten in canonical zero-padded HH:MM form.
    """
    meeting = normalize_meeting(raw)
    if not meeting["Meeting"]:
        return None, "Meeting title is required."
    try:
        start, end = to_minutes(meeting["Start"]), to_minutes(meeting["End"])
    except ValueError as exc:
        return None, str(exc)
    if end <= start:
        return None, "End time must be later than start time (overnight meetings are not supported)."

    emails = parse_emails(meeting["Attendees"])
    invalid = [email for email in emails if not is_valid_email(email)]
    if validate_emails and invalid:
        return None, "Invalid attendee email: {}".format(", ".join(invalid))

    meeting["Start"], meeting["End"] = to_hhmm(start), to_hhmm(end)
    meeting["Attendees"] = ", ".join(emails)
    return meeting, None
