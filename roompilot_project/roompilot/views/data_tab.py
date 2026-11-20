"""Manage & export tab: edit, delete, import and export meetings."""

from datetime import date
from typing import List

import pandas as pd
import streamlit as st

from ..formats import build_csv, build_ics, parse_meetings_csv
from ..models import FIELDS, Meeting, prepare_meeting
from ..storage import default_meetings
from ..ui import commit_meetings, flash, stretch

REPLACE, APPEND = "Replace existing schedule", "Append to existing schedule"


def render(meetings: List[Meeting], schedule_date: date) -> None:
    st.subheader("Manage meeting data")
    st.caption("Edit the table and save changes. Meeting times use 24-hour HH:MM format.")

    if meetings:
        _render_editor(meetings)
    else:
        st.info("No meeting data to edit. Add a meeting from the sidebar or load the sample schedule.")

    st.divider()
    st.subheader("Import and export")
    import_col, export_col = st.columns(2)
    with import_col:
        _render_import(meetings)
    with export_col:
        _render_export(meetings, schedule_date)


def _render_editor(meetings: List[Meeting]) -> None:
    version = st.session_state.data_version  # new key after each change avoids stale edits
    table = pd.DataFrame([{field: m[field] for field in FIELDS} for m in meetings])
    edited = st.data_editor(
        table,
        hide_index=True,
        num_rows="fixed",
        column_config={
            "Meeting": st.column_config.TextColumn("Meeting", required=True),
            "Start": st.column_config.TextColumn("Start (HH:MM)", required=True),
            "End": st.column_config.TextColumn("End (HH:MM)", required=True),
            "Location": st.column_config.TextColumn("Location"),
            "Description": st.column_config.TextColumn("Description"),
            "Attendees": st.column_config.TextColumn("Attendee emails"),
        },
        key="meeting_editor_{}".format(version),
        **stretch(),
    )

    if st.button("Save table changes", type="primary", key="save_table"):
        updated, errors = [], []
        for position, row in enumerate(edited.fillna("").to_dict("records")):
            meeting, error = prepare_meeting(dict(row, id=meetings[position]["id"]))
            if error:
                errors.append("Row {}: {}".format(position + 1, error))
            else:
                updated.append(meeting)
        if errors:
            for error in errors:
                st.error(error)
        else:
            commit_meetings(updated)
            flash("Meeting data saved.")
            st.rerun()

    delete_ids = st.multiselect(
        "Select meetings to delete",
        options=[m["id"] for m in meetings],
        format_func={m["id"]: "{} ({}–{})".format(m["Meeting"], m["Start"], m["End"]) for m in meetings}.get,
        key="delete_selection_{}".format(version),
    )
    if st.button("Delete selected meetings", disabled=not delete_ids, key="delete_meetings"):
        commit_meetings([m for m in meetings if m["id"] not in delete_ids])
        flash("Deleted {} meeting(s).".format(len(delete_ids)))
        st.rerun()


def _render_import(meetings: List[Meeting]) -> None:
    uploaded = st.file_uploader("Import a meeting CSV", type=["csv"], key="meeting_csv_upload")
    mode = st.radio("Import behaviour", [REPLACE, APPEND], key="csv_import_mode")
    if st.button("Import CSV", disabled=uploaded is None, key="import_csv"):
        parsed, errors = parse_meetings_csv(uploaded.getvalue())
        if parsed:
            commit_meetings(parsed if mode == REPLACE else meetings + parsed)
            flash("Imported {} meeting(s).".format(len(parsed)))
            for error in errors:  # keep skipped-row warnings visible across the rerun
                flash(error, "warning")
            st.rerun()
        for error in errors:
            st.warning(error)
        if not errors:
            st.error("No valid rows were found in the CSV.")
    st.download_button(
        "Download sample CSV template",
        build_csv(default_meetings()),
        "roompilot_sample.csv",
        "text/csv",
        **stretch(),
    )


def _render_export(meetings: List[Meeting], schedule_date: date) -> None:
    st.download_button(
        "Export current schedule as CSV",
        build_csv(meetings),
        "roompilot_schedule.csv",
        "text/csv",
        disabled=not meetings,
        **stretch(),
    )
    st.download_button(
        "Export calendar file (.ics)",
        build_ics(meetings, schedule_date),
        "roompilot_schedule.ics",
        "text/calendar",
        disabled=not meetings,
        **stretch(),
    )
    st.caption("Your schedule lives in `meetings_data.json`. Copy it to move the schedule to another computer.")
