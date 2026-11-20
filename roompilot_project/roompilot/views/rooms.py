"""Room allocation tab (interval partitioning)."""

from datetime import date
from typing import Dict, List

import pandas as pd
import streamlit as st

from ..charts import timeline_figure
from ..models import Meeting
from ..ui import stretch


def render(meetings: List[Meeting], analysis: Dict, schedule_date: date) -> None:
    assignments = analysis["assignments"]

    st.subheader("Interval Partitioning · Allocate every meeting")
    st.markdown("<span class='rp-pill'>Greedy choice: reuse the room that becomes free earliest</span>", unsafe_allow_html=True)

    a, b, c, d = st.columns(4)
    a.metric("Minimum rooms required", analysis["room_count"])
    b.metric("Peak simultaneous meetings", analysis["peak_overlap"], help="Lower bound on rooms; the greedy result matches it.")
    c.metric("Meetings assigned", len(assignments))
    d.metric("Time complexity", "O(n log n)")

    if assignments:
        st.plotly_chart(
            timeline_figure(assignments, schedule_date, "Room", "All meetings assigned to rooms"),
            config={"displaylogo": False, "scrollZoom": True},
            **stretch(),
        )
        table = pd.DataFrame([
            {"Room": x["Room"], "Meeting": x["Meeting"], "Start": x["Start"], "End": x["End"], "Location": x["Location"]}
            for x in assignments
        ])
        st.dataframe(table, hide_index=True, **stretch())
    else:
        st.info("Add meetings to see room assignments.")

    with st.expander("Why the min-heap gives the minimum room count"):
        st.markdown(
            "Meetings are sorted by start time. A min-heap stores the next free time for each room. "
            "When the earliest room is free before the next meeting starts, it is reused; otherwise a new room is opened. "
            "The maximum number of simultaneous meetings is a lower bound on the rooms needed, "
            "and this greedy algorithm achieves that bound."
        )
