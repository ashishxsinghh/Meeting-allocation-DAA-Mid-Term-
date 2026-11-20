"""DAA algorithms: activity selection, interval partitioning and schedule analysis.

Two meetings overlap only when they share time; a meeting that starts exactly
when another ends does NOT overlap with it.
"""

from __future__ import annotations

import heapq
from typing import Dict, List, Optional, Tuple

from .config import OPTIMAL_STRATEGY, STRATEGIES
from .models import Meeting, to_minutes

SORT_KEYS = {
    "end": lambda m: (m["end_min"], m["start_min"]),
    "start": lambda m: (m["start_min"], m["end_min"]),
    "duration": lambda m: (m["duration"], m["end_min"]),
}


def _with_minutes(meeting: Meeting) -> Dict:
    start, end = to_minutes(meeting["Start"]), to_minutes(meeting["End"])
    return dict(meeting, start_min=start, end_min=end, duration=end - start)


def _overlaps(a: Dict, b: Dict) -> bool:
    return a["start_min"] < b["end_min"] and b["start_min"] < a["end_min"]


def _find_conflict(item: Dict, selected: List[Dict]) -> Optional[Dict]:
    return next((s for s in selected if _overlaps(item, s)), None)


# ----------------------------------------------------------------------------
# Activity selection (one room)
# ----------------------------------------------------------------------------
def greedy_single_room(meetings: List[Meeting], strategy: str = OPTIMAL_STRATEGY) -> Dict:
    """Pick compatible meetings for a single room.

    Earliest Finish Time is provably optimal. The other strategies are
    heuristics kept for comparison.
    """
    if strategy not in SORT_KEYS:
        raise ValueError("Unknown strategy: {!r}".format(strategy))

    ordered = sorted((_with_minutes(m) for m in meetings), key=SORT_KEYS[strategy])
    selected, rejected, evaluated, trace = [], [], [], []
    last_end = -1

    for step, item in enumerate(ordered, start=1):
        if strategy == "duration":
            # Shortest-first is not sorted by time, so check against every accepted meeting.
            conflict = _find_conflict(item, selected)
            accepted = conflict is None
        else:
            # Sorted by time: comparing with the last accepted finish time is enough.
            accepted = item["start_min"] >= last_end
            conflict = None if accepted else _find_conflict(item, selected)

        if accepted:
            selected.append(item)
            last_end = max(last_end, item["end_min"])
            evaluated.append(dict(item, Status="Scheduled"))
            reason = "First meeting selected" if len(selected) == 1 else "No overlap with selected meetings"
        else:
            rejected.append(item)
            evaluated.append(dict(item, Status="Rejected"))
            reason = (
                "Overlaps with {} ({}–{})".format(conflict["Meeting"], conflict["Start"], conflict["End"])
                if conflict
                else "Overlaps with an already scheduled meeting"
            )

        trace.append({
            "Step": step,
            "Meeting": item["Meeting"],
            "Interval": "{} – {}".format(item["Start"], item["End"]),
            "Duration (min)": item["duration"],
            "Decision": "ACCEPTED" if accepted else "REJECTED",
            "Reason": reason,
        })

    return {
        "selected": selected,
        "rejected": rejected,
        "evaluated": evaluated,
        "trace": trace,
        "busy_minutes": sum(m["duration"] for m in selected),
    }


# ----------------------------------------------------------------------------
# Interval partitioning (minimum rooms)
# ----------------------------------------------------------------------------
def greedy_multi_room(meetings: List[Meeting]) -> Tuple[int, List[Dict]]:
    """Assign every meeting to a room using the fewest rooms possible."""
    ordered = sorted((_with_minutes(m) for m in meetings), key=SORT_KEYS["start"])
    free_at: List[Tuple[int, int]] = []  # min-heap of (end time, room number)
    assignments: List[Dict] = []
    room_count = 0

    for item in ordered:
        if free_at and free_at[0][0] <= item["start_min"]:
            _, room = heapq.heappop(free_at)
        else:
            room_count += 1
            room = room_count
        heapq.heappush(free_at, (item["end_min"], room))
        assignments.append(dict(item, Room="Room {}".format(room)))

    return room_count, assignments


# ----------------------------------------------------------------------------
# Schedule statistics
# ----------------------------------------------------------------------------
def peak_overlap(meetings: List[Meeting]) -> int:
    """Maximum number of meetings running at the same moment (sweep line)."""
    events = []
    for m in meetings:
        events.append((to_minutes(m["Start"]), 1))
        events.append((to_minutes(m["End"]), -1))
    events.sort()  # at equal times, -1 (end) sorts before +1 (start)
    current = peak = 0
    for _, delta in events:
        current += delta
        peak = max(peak, current)
    return peak


def count_overlapping_pairs(meetings: List[Meeting]) -> int:
    items = [_with_minutes(m) for m in meetings]
    return sum(1 for i, a in enumerate(items) for b in items[i + 1:] if _overlaps(a, b))


def analyze_schedule(meetings: List[Meeting]) -> Dict:
    """Run every algorithm once and collect the numbers the UI needs."""
    strategies = {key: greedy_single_room(meetings, key) for key in STRATEGIES.values()}
    room_count, assignments = greedy_multi_room(meetings)

    if meetings:
        starts = [to_minutes(m["Start"]) for m in meetings]
        ends = [to_minutes(m["End"]) for m in meetings]
        total_minutes = sum(e - s for s, e in zip(starts, ends))
        day_span = max(ends) - min(starts)
    else:
        total_minutes = day_span = 0

    optimal = strategies[OPTIMAL_STRATEGY]
    return {
        "strategies": strategies,
        "optimal": optimal,
        "room_count": room_count,
        "assignments": assignments,
        "peak_overlap": peak_overlap(meetings),
        "overlap_pairs": count_overlapping_pairs(meetings),
        "total_minutes": total_minutes,
        "utilization": 100.0 * optimal["busy_minutes"] / day_span if day_span else 0.0,
    }
