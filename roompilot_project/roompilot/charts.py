"""Plotly figures."""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime
from typing import Dict, List, Optional

import pandas as pd
import plotly.express as px

from .models import local_datetime

_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(15,23,42,.35)",
    font=dict(color="#dce6fa"),
)


def _lane_labels(items: List[Dict]) -> List[str]:
    """Meeting names, numbered when duplicated so each gets its own timeline lane."""
    totals = Counter(item["Meeting"] for item in items)
    seen: Counter = Counter()
    labels = []
    for item in items:
        name = item["Meeting"]
        seen[name] += 1
        labels.append(name if totals[name] == 1 else "{} ({})".format(name, seen[name]))
    return labels


def _wall_clock(schedule_date: date, hhmm: str) -> datetime:
    return local_datetime(schedule_date, hhmm).replace(tzinfo=None)


def timeline_figure(items: List[Dict], schedule_date: date, color_field: str, title: str) -> Optional[object]:
    if not items:
        return None
    labels = _lane_labels(items)
    df = pd.DataFrame([
        dict(
            item,
            Lane=label,
            StartAt=_wall_clock(schedule_date, item["Start"]),
            EndAt=_wall_clock(schedule_date, item["End"]),
        )
        for item, label in zip(items, labels)
    ])
    fig = px.timeline(
        df,
        x_start="StartAt",
        x_end="EndAt",
        y="Lane",
        color=color_field,
        hover_name="Meeting",
        hover_data={"Start": True, "End": True, "Location": True, "Lane": False, "StartAt": False, "EndAt": False},
        title=title,
        color_discrete_map={"Scheduled": "#35c58a", "Rejected": "#f16d7a"},
    )
    fig.update_yaxes(autorange="reversed", title=None)
    fig.update_xaxes(tickformat="%H:%M", title="Local time")
    fig.update_layout(
        **_LAYOUT,
        height=max(300, 58 * len(items) + 100),
        margin=dict(l=10, r=20, t=55, b=20),
        legend_title_text="",
        title_font_size=17,
    )
    return fig


def strategy_bar_figure(rows: List[Dict]):
    fig = px.bar(
        pd.DataFrame(rows),
        x="Strategy",
        y="Meetings",
        text="Meetings",
        color="Strategy",
        title="Accepted meetings by strategy",
    )
    fig.update_layout(**_LAYOUT, showlegend=False, margin=dict(l=5, r=5, t=50, b=5), height=330)
    return fig
