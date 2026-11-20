import csv
import heapq
import io
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Optimal Meeting Room Allocation", layout="wide")


# --- Time Conversion Helpers ---
def to_minutes(hhmm: str) -> int:
    parts = hhmm.strip().split(":")
    if len(parts) < 2:
        raise ValueError(f"Invalid time '{hhmm}'. Expected HH:MM.")
    h, m = int(parts[0]), int(parts[1])
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise ValueError(f"Time '{hhmm}' out of 24-hour range.")
    return h * 60 + m


def to_hhmm(mins: int) -> str:
    return f"{mins // 60:02d}:{mins % 60:02d}"


# --- Default Dataset (Preserved Sample Data) ---
DEFAULT_MEETINGS = [
    {"Meeting": "M1: All-Day Workshop", "Start": "08:45", "End": "16:00"},
    {"Meeting": "M2: Morning Standup", "Start": "09:00", "End": "10:00"},
    {"Meeting": "M3: Client Sync", "Start": "10:00", "End": "11:30"},
    {"Meeting": "M4: Quick Check-in", "Start": "11:15", "End": "11:45"},
    {"Meeting": "M5: Design Review", "Start": "11:30", "End": "13:00"},
    {"Meeting": "M6: Sprint Planning", "Start": "13:00", "End": "14:30"},
    {"Meeting": "M7: Lunch Overlap", "Start": "12:45", "End": "13:15"},
    {"Meeting": "M8: Security Audit", "Start": "14:30", "End": "16:00"},
    {"Meeting": "M9: Retrospective", "Start": "16:00", "End": "17:00"},
]

STRATEGY_OPTIONS = {
    "Earliest Finish Time (Optimal)": "end",
    "Earliest Start Time": "start",
    "Shortest Duration First": "duration",
}


# --- CSV Parser Using csv.DictReader ---
def parse_meetings_csv(file_bytes: bytes) -> tuple[list[dict], list[str]]:
    """
    Reads CSV bytes with csv.DictReader and formats rows into:
    [{"Meeting": str, "Start": "HH:MM", "End": "HH:MM"}, ...]
    """
    text = file_bytes.decode("utf-8-sig")
    stream = io.StringIO(text)
    reader = csv.DictReader(stream)

    if not reader.fieldnames:
        return [], ["The uploaded CSV file is empty."]

    # Case-insensitive header lookup (supports Meeting/Title, Start, End)
    header_map = {h.strip().lower(): h for h in reader.fieldnames if h}
    meeting_col = header_map.get("meeting") or header_map.get("title")
    start_col = header_map.get("start") or header_map.get("start time")
    end_col = header_map.get("end") or header_map.get("end time")

    if not (meeting_col and start_col and end_col):
        return [], [
            "Missing required CSV headers. Include columns: Meeting, Start, End"
        ]

    parsed_meetings = []
    errors = []

    for row_num, row in enumerate(reader, start=2):
        # Skip completely blank lines
        if not any(val and val.strip() for val in row.values()):
            continue

        title = (row.get(meeting_col) or "").strip()
        raw_start = (row.get(start_col) or "").strip()
        raw_end = (row.get(end_col) or "").strip()

        if not title:
            errors.append(f"Row {row_num}: Missing meeting title.")
            continue

        try:
            s_min = to_minutes(raw_start)
            e_min = to_minutes(raw_end)
            if e_min <= s_min:
                errors.append(
                    f"Row {row_num} ({title}): End time ({raw_end}) must be after Start time ({raw_start})."
                )
                continue

            parsed_meetings.append({
                "Meeting": title,
                "Start": to_hhmm(s_min),
                "End": to_hhmm(e_min),
            })
        except ValueError as exc:
            errors.append(f"Row {row_num} ({title}): {exc}")

    return parsed_meetings, errors


def build_sample_csv() -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["Meeting", "Start", "End"])
    writer.writeheader()
    writer.writerows(DEFAULT_MEETINGS)
    return output.getvalue()


# --- DAA Core Algorithm 1: Greedy Activity Selection (Single Room) ---
def greedy_single_room(meetings: list[dict], sort_key: str = "end"):
    """
    Optimal Greedy Choice: sort_key='end' -> O(n log n) time, O(n) space.
    Other keys ('start', 'duration') demonstrate suboptimal counterexamples.
    """
    enriched = []
    for m in meetings:
        s, e = to_minutes(m["Start"]), to_minutes(m["End"])
        enriched.append({**m, "start_min": s, "end_min": e, "duration": e - s})

    if sort_key == "end":
        sorted_meetings = sorted(enriched, key=lambda x: (x["end_min"], x["start_min"]))
    elif sort_key == "start":
        sorted_meetings = sorted(enriched, key=lambda x: (x["start_min"], x["end_min"]))
    else:  # shortest duration
        sorted_meetings = sorted(enriched, key=lambda x: (x["duration"], x["end_min"]))

    selected, rejected, evaluated, trace = [], [], [], []
    last_end = -1

    for step, m in enumerate(sorted_meetings, start=1):
        if sort_key == "duration":
            # Non-chronological order: must check overlap against ALL selected meetings
            conflict_with = next(
                (
                    s
                    for s in selected
                    if m["start_min"] < s["end_min"] and m["end_min"] > s["start_min"]
                ),
                None,
            )
            if conflict_with is None:
                selected.append(m)
                evaluated.append({**m, "Status": "Scheduled"})
                reason = (
                    "First meeting selected"
                    if len(selected) == 1
                    else "No overlap with any scheduled meeting"
                )
                trace.append({
                    "Step": step,
                    "Meeting": m["Meeting"],
                    "Interval": f"{m['Start']} - {m['End']}",
                    "Duration (min)": m["duration"],
                    "Decision": "ACCEPTED",
                    "Reason": reason,
                })
            else:
                rejected.append(m)
                evaluated.append({**m, "Status": "Rejected"})
                trace.append({
                    "Step": step,
                    "Meeting": m["Meeting"],
                    "Interval": f"{m['Start']} - {m['End']}",
                    "Duration (min)": m["duration"],
                    "Decision": "REJECTED",
                    "Reason": (
                        f"Overlaps with {conflict_with['Meeting']} "
                        f"({conflict_with['Start']} - {conflict_with['End']})"
                    ),
                })
        else:
            # Chronological strategies ('end' and 'start'): check against last_end
            if m["start_min"] >= last_end:
                selected.append(m)
                evaluated.append({**m, "Status": "Scheduled"})
                reason = (
                    "First meeting in sorted order"
                    if last_end == -1
                    else f"Start ({m['Start']}) >= Last End ({to_hhmm(last_end)})"
                )
                last_end = m["end_min"]
                trace.append({
                    "Step": step,
                    "Meeting": m["Meeting"],
                    "Interval": f"{m['Start']} - {m['End']}",
                    "Duration (min)": m["duration"],
                    "Decision": "ACCEPTED",
                    "Reason": reason,
                })
            else:
                rejected.append(m)
                evaluated.append({**m, "Status": "Rejected"})
                trace.append({
                    "Step": step,
                    "Meeting": m["Meeting"],
                    "Interval": f"{m['Start']} - {m['End']}",
                    "Duration (min)": m["duration"],
                    "Decision": "REJECTED",
                    "Reason": f"Conflict: Start ({m['Start']}) < Last End ({to_hhmm(last_end)})",
                })

    return {
        "selected": selected,
        "rejected": rejected,
        "evaluated": evaluated,
        "trace": trace,
    }


# --- DAA Core Algorithm 2: Greedy Interval Partitioning (Min Rooms) ---
def greedy_multi_room(meetings: list[dict]):
    """
    Assigns all meetings to minimum rooms using a Min-Heap.
    Time Complexity: O(n log n) | Space Complexity: O(n)
    """
    enriched = sorted(
        [
            {**m, "start_min": to_minutes(m["Start"]), "end_min": to_minutes(m["End"])}
            for m in meetings
        ],
        key=lambda x: (x["start_min"], x["end_min"]),
    )

    min_heap = []
    room_assignments = []
    room_count = 0

    for m in enriched:
        if min_heap and min_heap[0][0] <= m["start_min"]:
            _, room_id = heapq.heappop(min_heap)
        else:
            room_count += 1
            room_id = room_count

        heapq.heappush(min_heap, (m["end_min"], room_id))
        room_assignments.append({**m, "Room": f"Room {room_id}"})

    return room_count, room_assignments


# --- Visual Timeline Renderer (Pure HTML/CSS) ---
def render_timeline(items: list[dict], status_field: str):
    min_t = min(x["start_min"] for x in items)
    max_t = max(x["end_min"] for x in items)
    span = max(max_t - min_t, 1)

    parts = [
        '<div style="border:1px solid #ddd; border-radius:8px; padding:14px; background:#fafafa;">'
    ]
    for idx, item in enumerate(items, start=1):
        left_pct = ((item["start_min"] - min_t) / span) * 100
        width_pct = max(((item["end_min"] - item["start_min"]) / span) * 100, 1.5)
        is_accepted = item[status_field] == "Scheduled"
        bar_color = "#2e7d32" if is_accepted else "#c62828"
        opacity = "1.0" if is_accepted else "0.55"

        parts.append(
            f'<div style="margin-bottom:10px;">'
            f'<div style="font-size:13px; font-weight:600; margin-bottom:3px; color:#222;">'
            f'Step {idx}: {item["Meeting"]} <span style="font-weight:400; color:#555;">({item["Start"]} – {item["End"]})</span>'
            f'</div>'
            f'<div style="width:100%; background:#e0e0e0; height:18px; border-radius:4px; position:relative;">'
            f'<div style="position:absolute; left:{left_pct:.2f}%; width:{width_pct:.2f}%; height:18px; background:{bar_color}; opacity:{opacity}; border-radius:4px;"></div>'
            f'</div>'
            f'</div>'
        )

    parts.append(
        f'<div style="display:flex; justify-content:space-between; font-size:12px; color:#666; margin-top:6px;">'
        f'<span>{to_hhmm(min_t)}</span><span>{to_hhmm((min_t + max_t)//2)}</span><span>{to_hhmm(max_t)}</span>'
        f'</div></div>'
    )
    st.markdown("".join(parts), unsafe_allow_html=True)


# --- Streamlit UI ---
st.title("Optimal Meeting Room Allocation System")
st.caption("DAA Project #27")

if "meetings" not in st.session_state:
    st.session_state.meetings = DEFAULT_MEETINGS.copy()

# Sidebar: Manage Meetings & Import Meeting Schedule (CSV)
with st.sidebar:
    st.header("Schedule Controls")
    side_tab1, side_tab2 = st.tabs(["Manage Meetings", "Import Meeting Schedule"])

    with side_tab1:
        with st.form("add_meeting_form", clear_on_submit=True):
            name = st.text_input("Meeting Title", placeholder="e.g., M10: Tech Sync")
            col1, col2 = st.columns(2)
            start_time = col1.time_input("Start", value=pd.to_datetime("10:30").time())
            end_time = col2.time_input("End", value=pd.to_datetime("11:30").time())
            submitted = st.form_submit_button("Add Meeting", width='stretch')

            if submitted:
                if not name.strip():
                    st.error("Enter a meeting title.")
                elif end_time <= start_time:
                    st.error("End time must be after start time.")
                else:
                    st.session_state.meetings.append({
                        "Meeting": name.strip(),
                        "Start": start_time.strftime("%H:%M"),
                        "End": end_time.strftime("%H:%M"),
                    })
                    st.success(f"Added '{name.strip()}'")

    with side_tab2:
        st.caption("Upload a CSV with headers: `Meeting`, `Start`, `End` (24-hour `HH:MM`).")
        uploaded_csv = st.file_uploader(
            "Choose CSV File", type=["csv"], label_visibility="collapsed"
        )
        import_mode = st.radio(
            "Import Mode",
            options=["Replace current schedule", "Append to current schedule"],
            index=0,
        )

        if st.button("Import CSV Schedule", width='stretch', disabled=uploaded_csv is None):
            parsed, errors = parse_meetings_csv(uploaded_csv.getvalue())
            for err in errors:
                st.warning(err)
            if parsed:
                if import_mode == "Replace current schedule":
                    st.session_state.meetings = parsed
                else:
                    st.session_state.meetings.extend(parsed)
                st.success(f"Imported {len(parsed)} meeting(s) via csv.DictReader.")
                st.rerun()
            elif not errors:
                st.error("No valid meeting rows found in the CSV.")

        st.download_button(
            label="Download Sample CSV",
            data=build_sample_csv(),
            file_name="sample_meeting_schedule.csv",
            mime="text/csv",
            width='stretch',
        )

    st.divider()
    c1, c2 = st.columns(2)
    if c1.button("Load Sample", width='stretch'):
        st.session_state.meetings = DEFAULT_MEETINGS.copy()
        st.rerun()
    if c2.button("Clear All", width='stretch'):
        st.session_state.meetings = []
        st.rerun()

if not st.session_state.meetings:
    st.info("No meetings scheduled. Add meetings, import a CSV, or click **Load Sample** in the sidebar.")
    st.stop()

with st.expander("View / Inspect Raw Meeting Requests", expanded=False):
    st.dataframe(pd.DataFrame(st.session_state.meetings), width='stretch', hide_index=True)

tab1, tab2 = st.tabs([
    "1. Single Room Optimization (Activity Selection)",
    "2. Multi-Room Allocation (Min Rooms Needed)",
])

# --- TAB 1: Single Room ---
with tab1:
    selected_label = st.radio(
        "Select Greedy Strategy to Inspect:",
        options=list(STRATEGY_OPTIONS.keys()),
        horizontal=True,
    )
    active_key = STRATEGY_OPTIONS[selected_label]

    results = {
        key: greedy_single_room(st.session_state.meetings, sort_key=key)
        for key in STRATEGY_OPTIONS.values()
    }
    active_res = results[active_key]
    selected = active_res["selected"]
    rejected = active_res["rejected"]
    evaluated = active_res["evaluated"]
    trace = active_res["trace"]

    st.subheader("All Strategies Comparison")
    comp_df = pd.DataFrame([
        {
            "Active": "Viewing" if active_key == "end" else "",
            "Greedy Strategy": "Earliest Finish Time (Optimal)",
            "Meetings Scheduled": len(results["end"]["selected"]),
            "Optimality": "Guaranteed Optimal",
        },
        {
            "Active": "Viewing" if active_key == "start" else "",
            "Greedy Strategy": "Earliest Start Time",
            "Meetings Scheduled": len(results["start"]["selected"]),
            "Optimality": "Suboptimal (Fails on long early meetings)",
        },
        {
            "Active": "Viewing" if active_key == "duration" else "",
            "Greedy Strategy": "Shortest Duration First",
            "Meetings Scheduled": len(results["duration"]["selected"]),
            "Optimality": "Suboptimal (Fails when short meeting bridges two longer ones)",
        },
    ])
    st.table(comp_df)

    total_busy = sum(m["duration"] for m in selected)
    day_start = min(to_minutes(m["Start"]) for m in st.session_state.meetings)
    day_end = max(to_minutes(m["End"]) for m in st.session_state.meetings)
    utilization = (total_busy / max(day_end - day_start, 1)) * 100

    opt_count = len(results["end"]["selected"])
    diff = len(selected) - opt_count

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Requests", len(st.session_state.meetings))
    m2.metric(
        "Meetings Scheduled",
        len(selected),
        delta=None if active_key == "end" else f"{diff} vs Optimal",
    )
    m3.metric("Conflicts Rejected", len(rejected))
    m4.metric("Room Utilization", f"{utilization:.1f}%")

    st.subheader(f"Schedule Timeline — {selected_label}")
    st.caption("Green = Scheduled | Red = Rejected Conflict (Displayed in the strategy's step-by-step evaluation order)")
    render_timeline(evaluated, "Status")

    st.subheader(f"Step-by-Step Algorithm Execution Trace — {selected_label}")
    st.dataframe(pd.DataFrame(trace), width='stretch', hide_index=True)

# --- TAB 2: Multi-Room ---
with tab2:
    min_rooms, assignments = greedy_multi_room(st.session_state.meetings)
    st.metric("Minimum Rooms Required for Zero Conflicts", min_rooms)

    assign_df = pd.DataFrame(assignments)[["Room", "Meeting", "Start", "End"]].sort_values(
        by=["Room", "Start"]
    )
    st.dataframe(assign_df, width='stretch', hide_index=True)