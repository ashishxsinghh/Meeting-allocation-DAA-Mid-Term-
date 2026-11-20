"""Local JSON persistence."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List, Optional

from .config import DATA_FILE, DEFAULT_MEETINGS
from .models import Meeting, prepare_meeting


def default_meetings() -> List[Meeting]:
    return [prepare_meeting(item)[0] for item in DEFAULT_MEETINGS]


def load_meetings(path: Path = DATA_FILE) -> List[Meeting]:
    """Load saved meetings, skipping invalid entries.

    Falls back to the sample schedule when the file is missing or unreadable.
    """
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default_meetings()
    if not isinstance(data, list):
        return default_meetings()

    meetings = []
    for raw in data:
        if isinstance(raw, dict):
            meeting, error = prepare_meeting(raw, validate_emails=False)
            if not error:
                meetings.append(meeting)
    return meetings


def save_meetings(meetings: List[Meeting], path: Path = DATA_FILE) -> Optional[str]:
    """Write meetings atomically. Returns an error message, or None on success."""
    path = Path(path)
    temp_path = path.with_name(path.name + ".tmp")
    try:
        temp_path.write_text(json.dumps(meetings, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temp_path, path)
        return None
    except OSError as exc:
        return str(exc)
