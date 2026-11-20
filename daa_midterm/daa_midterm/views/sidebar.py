"""Sidebar: schedule date, quick-add form and workspace actions."""

from datetime import time, timedelta

import streamlit as st

from ..config import DATA_FILE
from ..models import prepare_meeting
from ..storage import default_meetings
from ..ui import commit_meetings, flash, stretch


def render() -> None:
    with st.sidebar:
        st.markdown("## 🗓️ DAA Midterm")
        st.caption("Smart scheduling workspace")
        st.divider()

        st.markdown("**Schedule date**")
        st.date_input("Choose meeting date", key="schedule_date", label_visibility="collapsed")

        st.markdown("**Quick add meeting**")
        # The key changes after every save, which gives a fresh empty form.
        with st.form("quick_add_{}".format(st.session_state.data_version)):
            title = st.text_input("Meeting name", placeholder="e.g. Product review")
            start_col, end_col = st.columns(2)
            start = start_col.time_input("Start", value=time(10, 30), step=timedelta(minutes=15))
            end = end_col.time_input("End", value=time(11, 30), step=timedelta(minutes=15))
            location = st.text_input("Location", placeholder="Room / online")
            attendees = st.text_input("Attendee emails", placeholder="alex@example.com, sam@example.com")
            description = st.text_area("Description", height=70, placeholder="Agenda or notes")
            submitted = st.form_submit_button("＋ Add to schedule", **stretch())

        if submitted:
            meeting, error = prepare_meeting({
                "Meeting": title,
                "Start": start.strftime("%H:%M"),
                "End": end.strftime("%H:%M"),
                "Location": location,
                "Attendees": attendees,
                "Description": description,
            })
            if error:
                st.error(error)
            else:
                commit_meetings(st.session_state.meetings + [meeting])
                flash("Meeting added.")
                st.rerun()

        st.divider()
        st.markdown("**Workspace actions**")
        if st.button("↻ Load sample schedule", key="load_sample", **stretch()):
            commit_meetings(default_meetings())
            flash("Sample schedule loaded.")
            st.rerun()
        if st.button("Clear schedule", key="clear_schedule", **stretch()):
            commit_meetings([])
            flash("Schedule cleared.", "info")
            st.rerun()
        st.caption("Changes are saved to `{}`.".format(DATA_FILE.name))
