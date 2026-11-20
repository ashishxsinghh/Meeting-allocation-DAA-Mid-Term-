import itertools
import random
import unittest

from roompilot.algorithms import (
    analyze_schedule,
    count_overlapping_pairs,
    greedy_multi_room,
    greedy_single_room,
    peak_overlap,
)
from roompilot.models import prepare_meeting, to_hhmm
from roompilot.storage import default_meetings


def make(start, end, name=None):
    meeting, error = prepare_meeting({"Meeting": name or "m{}-{}".format(start, end), "Start": to_hhmm(start), "End": to_hhmm(end)})
    assert error is None, error
    return meeting


def random_schedule(rng, size):
    meetings = []
    for _ in range(size):
        start = rng.randrange(0, 20 * 60, 15)
        meetings.append(make(start, start + rng.randrange(15, 240, 15)))
    return meetings


def brute_force_max(meetings):
    spans = [(int(m["Start"][:2]) * 60 + int(m["Start"][3:]), int(m["End"][:2]) * 60 + int(m["End"][3:])) for m in meetings]
    for size in range(len(spans), 0, -1):
        for combo in itertools.combinations(spans, size):
            ordered = sorted(combo)
            if all(a[1] <= b[0] for a, b in zip(ordered, ordered[1:])):
                return size
    return 0


class SingleRoomTests(unittest.TestCase):
    def test_sample_schedule(self):
        result = greedy_single_room(default_meetings(), "end")
        names = [m["Meeting"] for m in result["selected"]]
        self.assertEqual(names, ["M2: Morning Standup", "M3: Client Sync", "M5: Design Review", "M6: Sprint Planning", "M8: Security Audit", "M9: Retrospective"])

    def test_earliest_finish_is_optimal(self):
        rng = random.Random(7)
        for _ in range(150):
            meetings = random_schedule(rng, rng.randint(1, 9))
            self.assertEqual(len(greedy_single_room(meetings, "end")["selected"]), brute_force_max(meetings))

    def test_every_strategy_returns_a_conflict_free_set(self):
        rng = random.Random(11)
        for _ in range(100):
            meetings = random_schedule(rng, rng.randint(1, 12))
            for strategy in ("end", "start", "duration"):
                result = greedy_single_room(meetings, strategy)
                chosen = sorted((m["start_min"], m["end_min"]) for m in result["selected"])
                self.assertTrue(all(a[1] <= b[0] for a, b in zip(chosen, chosen[1:])))
                self.assertEqual(len(result["selected"]) + len(result["rejected"]), len(meetings))
                self.assertEqual(len(result["trace"]), len(meetings))

    def test_touching_meetings_do_not_conflict(self):
        result = greedy_single_room([make(540, 600), make(600, 660)], "end")
        self.assertEqual(len(result["selected"]), 2)

    def test_empty_and_unknown_strategy(self):
        self.assertEqual(greedy_single_room([], "end")["selected"], [])
        with self.assertRaises(ValueError):
            greedy_single_room([], "nope")


class MultiRoomTests(unittest.TestCase):
    def test_rooms_equal_peak_overlap_and_no_room_double_booked(self):
        rng = random.Random(3)
        for _ in range(150):
            meetings = random_schedule(rng, rng.randint(0, 14))
            rooms, assignments = greedy_multi_room(meetings)
            self.assertEqual(rooms, peak_overlap(meetings))
            self.assertEqual(len(assignments), len(meetings))
            by_room = {}
            for item in assignments:
                by_room.setdefault(item["Room"], []).append((item["start_min"], item["end_min"]))
            for spans in by_room.values():
                spans.sort()
                self.assertTrue(all(a[1] <= b[0] for a, b in zip(spans, spans[1:])))

    def test_sample_needs_three_rooms(self):
        self.assertEqual(greedy_multi_room(default_meetings())[0], 3)

    def test_overlap_pairs(self):
        self.assertEqual(count_overlapping_pairs([make(540, 600), make(570, 630), make(630, 700)]), 1)


class AnalysisTests(unittest.TestCase):
    def test_empty_schedule(self):
        result = analyze_schedule([])
        self.assertEqual((result["room_count"], result["total_minutes"], result["utilization"]), (0, 0, 0.0))

    def test_sample_numbers(self):
        result = analyze_schedule(default_meetings())
        self.assertEqual(len(result["optimal"]["selected"]), 6)
        self.assertLessEqual(result["utilization"], 100.0)


if __name__ == "__main__":
    unittest.main()
