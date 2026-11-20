"""Google Calendar tab and .ics download."""

from datetime import date
from typing import Dict, List, Optional

import pandas as pd
import streamlit as st

from .. import google_cal, oauth
from ..formats import build_ics
from ..models import Meeting
from ..ui import stretch

SETUP_HELP = """
**A. Create Google OAuth credentials**
1. Open [Google Cloud Console](https://console.cloud.google.com/) and create a project.
2. Enable the **Google Calendar API**.
3. Configure the OAuth consent screen and add your Google account as a test user.
4. Create an OAuth Client ID of type **Web application**.
5. Add this exact Authorized redirect URI: `http://localhost:8501`

**B. Add credentials to the project**

Create `.streamlit/secrets.toml` beside `app.py` (copy `.streamlit/secrets.toml.example`):

```toml
[google_calendar]
client_id = "YOUR_CLIENT_ID"
client_secret = "YOUR_CLIENT_SECRET"
redirect_uri = "http://localhost:8501"
```

Restart Streamlit afterwards. Never commit `secrets.toml`.
"""


def render(meetings: List[Meeting], schedule_date: date, config: Optional[Dict[str, str]]) -> None:
    st.subheader("Google Calendar connection")
    st.write(
        "Connect your Google account to create calendar events from this schedule. "
        "Attendee emails are optional."
    )

    bundle = oauth.get_service()
    if bundle:
        _render_connected(bundle, meetings, schedule_date)
    else:
        _render_connect(config)

    st.divider()
    st.markdown("**No API credentials? Use calendar import instead.**")
    st.download_button(
        "Download this schedule as an .ics calendar file",
        data=build_ics(meetings, schedule_date),
        file_name="roompilot-{}.ics".format(schedule_date.isoformat()),
        mime="text/calendar",
        disabled=not meetings,
        **stretch(),
    )
    st.caption("The .ics file can be imported into Google Calendar, Apple Calendar or Outlook. It is a one-time import, not a live sync.")


def _render_connect(config: Optional[Dict[str, str]]) -> None:
    if not config:
        st.warning("Google Calendar is not configured yet. Add your OAuth client details to `.streamlit/secrets.toml`, then restart Streamlit.")
    else:
        try:
            st.link_button("Connect Google Calendar", oauth.authorization_url(config), **stretch())
        except ImportError:
            st.error("Google packages are missing. Run: `python3 -m pip install -r requirements.txt`")
        except Exception as exc:
            st.error("Could not start Google sign-in: {}".format(exc))
    with st.expander("Google Calendar setup — one-time configuration"):
        st.markdown(SETUP_HELP)


def _render_connected(bundle, meetings: List[Meeting], schedule_date: date) -> None:
    service, credentials = bundle
    st.success("Connected to Google Calendar · primary calendar")
    if st.button("Disconnect Google account", key="disconnect_google"):
        oauth.disconnect()
        st.rerun()

    if meetings:
        by_id = {m["id"]: m for m in meetings}
        selected_ids = st.multiselect(
            "Choose meetings to sync",
            options=list(by_id),
            default=list(by_id),
            format_func=lambda uid: "{} ({}–{})".format(by_id[uid]["Meeting"], by_id[uid]["Start"], by_id[uid]["End"]),
            key="sync_selection_{}".format(st.session_state.data_version),
        )
        notify = st.checkbox(
            "Email invitations to attendees",
            value=False,
            help="When off, events are created silently even if attendee emails are set.",
        )
        if st.button("⇧ Sync selected meetings to Google Calendar", type="primary", disabled=not selected_ids, **stretch()):
            with st.spinner("Creating calendar events..."):
                created, existing, errors = google_cal.sync_events(
                    service, [by_id[uid] for uid in selected_ids], schedule_date, notify
                )
            st.success("Created {} event(s). {} already existed.".format(created, existing))
            for error in errors:
                st.error(error)

    try:
        events = google_cal.list_day_events(service, schedule_date)
        oauth.save_credentials(credentials)
    except Exception as exc:
        st.warning("Could not load events for this date: {}".format(exc))
        return

    st.markdown("**Events already on your Google Calendar for this date**")
    if not events:
        st.info("No events found on this date.")
        return
    rows = [
        {
            "Event": e.get("summary", "(No title)"),
            "Start": e.get("start", {}).get("dateTime") or e.get("start", {}).get("date", ""),
            "End": e.get("end", {}).get("dateTime") or e.get("end", {}).get("date", ""),
            "Location": e.get("location", ""),
        }
        for e in events
    ]
    st.dataframe(pd.DataFrame(rows), hide_index=True, **stretch())
