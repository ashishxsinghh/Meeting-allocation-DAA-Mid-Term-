"""Google Calendar OAuth and API helpers.

Google libraries are imported lazily so the rest of the app works without them.
This module does not depend on Streamlit.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import date, datetime, time, timedelta
from typing import Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from .config import GOOGLE_SCOPES, LOCAL_TZ
from .models import Meeting, is_valid_email, local_datetime, parse_emails

# Google may return extra previously granted scopes; don't treat that as an error.
os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")


# ----------------------------------------------------------------------------
# OAuth
# ----------------------------------------------------------------------------
def _build_flow(config: Dict[str, str], state: Optional[str] = None, code_verifier: Optional[str] = None):
    from google_auth_oauthlib.flow import Flow

    client_config = {
        "web": {
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [config["redirect_uri"]],
        }
    }
    extra = {"code_verifier": code_verifier, "autogenerate_code_verifier": False} if code_verifier else {}
    flow = Flow.from_client_config(client_config, scopes=GOOGLE_SCOPES, state=state, **extra)
    flow.redirect_uri = config["redirect_uri"]
    return flow


def create_authorization(config: Dict[str, str]) -> Tuple[str, str, Optional[str]]:
    """Return (authorization_url, state, pkce_code_verifier)."""
    flow = _build_flow(config)
    url, state = flow.authorization_url(access_type="offline", prompt="consent")
    return url, state, getattr(flow, "code_verifier", None)


def exchange_code(config: Dict[str, str], code: str, state: str, code_verifier: Optional[str]) -> str:
    """Exchange an authorization code for credentials. Returns credentials as JSON."""
    flow = _build_flow(config, state=state, code_verifier=code_verifier)
    flow.fetch_token(code=code)
    return flow.credentials.to_json()


# ----------------------------------------------------------------------------
# Service
# ----------------------------------------------------------------------------
def build_service(token_json: str):
    """Return (calendar service, credentials) from stored credentials JSON."""
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    credentials = Credentials.from_authorized_user_info(json.loads(token_json), GOOGLE_SCOPES)
    service = build("calendar", "v3", credentials=credentials, cache_discovery=False)
    return service, credentials


# ----------------------------------------------------------------------------
# Events
# ----------------------------------------------------------------------------
def event_payload(item: Meeting, schedule_date: date) -> Dict:
    """Google event body. The id is deterministic so re-syncing never duplicates."""
    event_id = hashlib.sha256("{}|{}".format(item["id"], schedule_date.isoformat()).encode("utf-8")).hexdigest()[:32]
    body = {
        "id": event_id,
        "summary": item["Meeting"],
        "description": item.get("Description", ""),
        "location": item.get("Location", ""),
        "start": {"dateTime": local_datetime(schedule_date, item["Start"]).isoformat(), "timeZone": LOCAL_TZ},
        "end": {"dateTime": local_datetime(schedule_date, item["End"]).isoformat(), "timeZone": LOCAL_TZ},
    }
    emails = [email for email in parse_emails(item.get("Attendees", "")) if is_valid_email(email)]
    if emails:
        body["attendees"] = [{"email": email} for email in emails]
    return body


def sync_events(service, meetings: List[Meeting], schedule_date: date, notify_attendees: bool = False) -> Tuple[int, int, List[str]]:
    """Insert meetings into the primary calendar. Returns (created, already_existing, errors)."""
    from googleapiclient.errors import HttpError

    created, existing, errors = 0, 0, []
    for item in meetings:
        try:
            service.events().insert(
                calendarId="primary",
                body=event_payload(item, schedule_date),
                sendUpdates="all" if notify_attendees else "none",
            ).execute()
            created += 1
        except HttpError as exc:
            if getattr(exc.resp, "status", None) == 409:
                existing += 1
            else:
                errors.append("{}: {}".format(item["Meeting"], exc))
        except Exception as exc:  # network or auth problems should not stop the whole batch
            errors.append("{}: {}".format(item["Meeting"], exc))
    return created, existing, errors


def list_day_events(service, schedule_date: date) -> List[Dict]:
    start = datetime.combine(schedule_date, time.min, tzinfo=ZoneInfo(LOCAL_TZ))
    result = service.events().list(
        calendarId="primary",
        timeMin=start.isoformat(),
        timeMax=(start + timedelta(days=1)).isoformat(),
        singleEvents=True,
        orderBy="startTime",
        maxResults=100,
    ).execute()
    return result.get("items", [])
