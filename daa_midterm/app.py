"""DAA Midterm: smart meeting scheduler. Run with: streamlit run app.py"""

import streamlit as st

# Must be the first Streamlit call.
st.set_page_config(
    page_title="DAA Midterm | Smart Meeting Scheduler",
    page_icon="🗓️",
    layout="wide",
    initial_sidebar_state="expanded",
)

from daa_midterm import oauth  # noqa: E402
from daa_midterm.algorithms import analyze_schedule  # noqa: E402
from daa_midterm.config import DATA_FILE, LOCAL_TZ  # noqa: E402
from daa_midterm.styles import inject_styles  # noqa: E402
from daa_midterm.ui import init_state, show_flash  # noqa: E402
from daa_midterm.views import calendar_tab, data_tab, overview, rooms, single_room, sidebar  # noqa: E402


def main() -> None:
    inject_styles()
    init_state()

    google_config = oauth.get_config()
    oauth.handle_callback(google_config)

    sidebar.render()

    meetings = st.session_state.meetings
    schedule_date = st.session_state.schedule_date
    analysis = analyze_schedule(meetings)

    st.markdown(
        """
        <div class="rp-hero">
          <div class="rp-eyebrow">DAA project · Greedy optimization workspace</div>
          <h1>DAA Midterm</h1>
          <p>Plan meetings, resolve conflicts, allocate rooms, and sync your schedule to Google Calendar.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    show_flash()

    hours, minutes = divmod(analysis["total_minutes"], 60)
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Meeting requests", len(meetings))
    k2.metric("Optimal single-room", len(analysis["optimal"]["selected"]))
    k3.metric("Minimum rooms", analysis["room_count"])
    k4.metric("Overlapping pairs", analysis["overlap_pairs"])
    k5.metric("Requested meeting time", "{}h {}m".format(hours, minutes))
    st.caption(
        "Schedule date: {} · Time zone: {} · {}".format(
            schedule_date.strftime("%A, %d %B %Y"),
            LOCAL_TZ,
            "Saved locally" if DATA_FILE.exists() else "Not saved yet",
        )
    )
    if not meetings:
        st.info("Your schedule is empty. Add a meeting from the sidebar or load the sample schedule.")

    tab_overview, tab_single, tab_rooms, tab_calendar, tab_data = st.tabs([
        "✦ Overview",
        "① Single-room optimizer",
        "② Room allocation",
        "▣ Google Calendar",
        "⚙ Manage & export",
    ])
    with tab_overview:
        overview.render(meetings, analysis, schedule_date)
    with tab_single:
        single_room.render(meetings, analysis, schedule_date)
    with tab_rooms:
        rooms.render(meetings, analysis, schedule_date)
    with tab_calendar:
        calendar_tab.render(meetings, schedule_date, google_config)
    with tab_data:
        data_tab.render(meetings, schedule_date)

    st.markdown(
        "<div class='rp-footer'>DAA Midterm · Greedy Activity Selection + "
        "Greedy Interval Partitioning · Built with Streamlit and Python</div>",
        unsafe_allow_html=True,
    )


main()
