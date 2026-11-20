"""Central configuration and sample data."""

import os
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = Path(os.environ.get("DAA_MIDTERM_DATA_FILE", APP_DIR / "meetings_data.json"))

LOCAL_TZ = "Asia/Kolkata"

GOOGLE_SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
DEFAULT_REDIRECT_URI = "http://localhost:8501"
OAUTH_PENDING_TTL_SECONDS = 600
OAUTH_PENDING_MAX = 50

# Strategy label -> internal key
STRATEGIES = {
    "Earliest Finish Time": "end",
    "Earliest Start Time": "start",
    "Shortest Duration First": "duration",
}
OPTIMAL_STRATEGY = "end"

MAX_CSV_BYTES = 1_000_000

_SAMPLE = [
    ("M1: All-Day Workshop", "08:45", "16:00", "Conference Room A", "Full-day workshop"),
    ("M2: Morning Standup", "09:00", "10:00", "Huddle Room 1", "Daily team standup"),
    ("M3: Client Sync", "10:00", "11:30", "Online", "Client project update"),
    ("M4: Quick Check-in", "11:15", "11:45", "Huddle Room 2", "Quick status check"),
    ("M5: Design Review", "11:30", "13:00", "Design Studio", "Review design proposals"),
    ("M6: Sprint Planning", "13:00", "14:30", "Conference Room B", "Plan the next sprint"),
    ("M7: Lunch Overlap", "12:45", "13:15", "Cafeteria", "Sample overlapping request"),
    ("M8: Security Audit", "14:30", "16:00", "Secure Lab", "Security review"),
    ("M9: Retrospective", "16:00", "17:00", "Conference Room A", "Sprint retrospective"),
]

DEFAULT_MEETINGS = [
    {
        "id": "sample-{}".format(i),
        "Meeting": title,
        "Start": start,
        "End": end,
        "Location": location,
        "Description": description,
        "Attendees": "",
    }
    for i, (title, start, end, location, description) in enumerate(_SAMPLE, start=1)
]
