"""Single-room optimizer tab (activity selection)."""

from datetime import date
from typing import Dict, List

import pandas as pd
import streamlit as st

from ..charts import timeline_figure
from ..config import OPTIMAL_STRATEGY, STRATEGIES
from ..models import Meeting
from ..ui import stretch


def render(meetings: List[Meeting], analysis: Dict, schedule_date: date) -> None:
    st.subheader("Activity Selection · One room, maximum compatible meetings")
    st.markdown("<span class='rp-pill'>Greedy choice: select by finishing time</span>", unsafe_allow_html=True)

    label = st.radio("Strategy to inspect", list(STRATEGIES), horizontal=True, key="single_strategy")
    result = analysis["strategies"][STRATEGIES[label]]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Accepted", len(result["selected"]))
    c2.metric("Rejected", len(result["rejected"]))
    c3.metric("Booked time", "{}h {}m".format(*divmod(result["busy_minutes"], 60)))
    c4.metric("Time complexity", "O(n log n)")

    comparison = [
        {
            "Strategy": name,
            "Meetings selected": len(analysis["strategies"][key]["selected"]),
            "Status": "Optimal" if key == OPTIMAL_STRATEGY else "Heuristic (not guaranteed optimal)",
        }
        for name, key in STRATEGIES.items()
    ]
    st.dataframe(pd.DataFrame(comparison), hide_index=True, **stretch())

    if result["evaluated"]:
        st.plotly_chart(
            timeline_figure(result["evaluated"], schedule_date, "Status", "Greedy decision timeline"),
            config={"displaylogo": False},
            **stretch(),
        )
        st.subheader("Execution trace")
        st.dataframe(pd.DataFrame(result["trace"]), hide_index=True, **stretch())
    else:
        st.info("Add meetings to see the algorithm run.")

    with st.expander("How this algorithm works"):
        st.markdown(
            "1. Sort meeting requests using the selected strategy.\n"
            "2. Examine requests in sorted order.\n"
            "3. Accept a meeting only when it does not overlap an already accepted meeting.\n\n"
            "**Optimal rule:** Earliest Finish Time. Sorting costs O(n log n); the scan costs O(n)."
        )
