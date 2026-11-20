"""Shared Streamlit helpers: session state, flash messages and width compatibility."""

from __future__ import annotations

from datetime import date
from typing import Dict, List

import streamlit as st

from .models import Meeting
from .storage import load_meetings, save_meetings


def _streamlit_version() -> tuple:
    parts = []
    for piece in st.__version__.split(".")[:2]:
        digits = "".join(ch for ch in piece if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


_USE_NEW_WIDTH_API = _streamlit_version() >= (1, 50)


def stretch() -> Dict:
    """Full-width keyword for buttons, tables and charts across Streamlit versions."""
    return {"width": "stretch"} if _USE_NEW_WIDTH_API else {"use_container_width": True}


# ----------------------------------------------------------------------------
# Session state
# ----------------------------------------------------------------------------
def init_state() -> None:
    if "meetings" not in st.session_state:
        st.session_state.meetings = load_meetings()
    st.session_state.setdefault("schedule_date", date.today())
    st.session_state.setdefault("data_version", 0)  # bumps on every change; resets stale widgets


def commit_meetings(meetings: List[Meeting]) -> None:
    """Replace the schedule, persist it, and reset widgets bound to the old data."""
    st.session_state.meetings = list(meetings)
    st.session_state.data_version += 1
    error = save_meetings(st.session_state.meetings)
    if error:
        flash("Changes are active for this session but could not be saved to disk: {}".format(error), "warning")


# ----------------------------------------------------------------------------
# Flash messages (survive st.rerun)
# ----------------------------------------------------------------------------
def flash(message: str, level: str = "success") -> None:
    st.session_state.setdefault("_flash", []).append((level, message))


def show_flash() -> None:
    for level, message in st.session_state.pop("_flash", []):
        getattr(st, level)(message)
