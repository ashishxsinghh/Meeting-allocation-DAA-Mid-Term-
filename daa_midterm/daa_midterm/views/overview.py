"""Overview tab."""

from datetime import date
from typing import Dict, List

import pandas as pd
import streamlit as st

from ..charts import strategy_bar_figure, timeline_figure
from ..config import STRATEGIES
from ..models import Meeting, to_minutes
from ..ui import stretch

PLOT_CONFIG = {"displaylogo": False, "scrollZoom": True}


def render(meetings: List[Meeting], analysis: Dict, schedule_date: date) -> None:
    left, right = st.columns([1.45, 1])

    with left:
        st.subheader("Schedule at a glance")
        if meetings:
            items = [dict(m, Status="Scheduled") for m in analysis["assignments"]]
            fig = timeline_figure(items, schedule_date, "Room", "Room allocation timeline")
            st.plotly_chart(fig, config=PLOT_CONFIG, **stretch())
        else:
            st.info("Add meetings to generate the schedule timeline.")

    with right:
        st.subheader("Greedy strategy benchmark")
        if meetings:
            rows = [
                {"Strategy": label, "Meetings": len(analysis["strategies"][key]["selected"])}
                for label, key in STRATEGIES.items()
            ]
            st.plotly_chart(strategy_bar_figure(rows), config={"displaylogo": False}, **stretch())
            st.caption("Earliest Finish Time is the optimal greedy strategy for single-room activity selection.")
        else:
            st.info("No data to compare yet.")

    st.subheader("Upcoming schedule")
    if meetings:
        rows = [
            {
                "Meeting": m["Meeting"],
                "Time": "{} – {}".format(m["Start"], m["End"]),
                "Location": m["Location"] or "—",
                "Attendees": m["Attendees"] or "—",
            }
            for m in sorted(meetings, key=lambda m: (to_minutes(m["Start"]), to_minutes(m["End"])))
        ]
        st.dataframe(pd.DataFrame(rows), hide_index=True, **stretch())
