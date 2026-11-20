import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from roompilot.formats import _ics_fold, build_csv, build_ics, parse_meetings_csv
from roompilot.google_cal import event_payload
from roompilot.models import prepare_meeting, to_minutes
from roompilot.storage import default_meetings, load_meetings, save_meetings


class ModelTests(unittest.TestCase):
    def test_time_parsing(self):
        self.assertEqual(to_minutes("9:05"), 545)
        self.assertEqual(to_minutes("23:59"), 1439)
        for bad in ("24:00", "9", "09:30:15", "abc", "", None):
            with self.assertRaises(ValueError):
                to_minutes(bad)

    def test_prepare_meeting(self):
        meeting, error = prepare_meeting({"Meeting": " Sync ", "Start": "9:00", "End": "10:00", "Attendees": "a@x.com; b@y.org"})
        self.assertIsNone(error)
        self.assertEqual((meeting["Meeting"], meeting["Start"], meeting["Attendees"]), ("Sync", "09:00", "a@x.com, b@y.org"))

    def test_prepare_meeting_rejects_bad_input(self):
        base = {"Meeting": "A", "Start": "09:00", "End": "10:00"}
        for override in ({"Meeting": " "}, {"End": "09:00"}, {"Start": "x"}, {"Attendees": "not-an-email"}):
            self.assertIsNotNone(prepare_meeting(dict(base, **override))[1], override)

    def test_nan_cells_become_empty(self):
        meeting, error = prepare_meeting({"Meeting": "A", "Start": "09:00", "End": "10:00", "Location": float("nan")})
        self.assertIsNone(error)
        self.assertEqual(meeting["Location"], "")


class CsvTests(unittest.TestCase):
    def test_round_trip(self):
        original = default_meetings()
        parsed, errors = parse_meetings_csv(build_csv(original).encode("utf-8"))
        self.assertEqual(errors, [])
        strip = lambda items: [{k: v for k, v in m.items() if k != "id"} for m in items]
        self.assertEqual(strip(parsed), strip(original))

    def test_bad_rows_are_reported_and_good_rows_kept(self):
        text = "Title,Start Time,End Time\nGood,09:00,10:00\nBad,10:00,09:00\n,,\nWorse,xx,11:00\n"
        parsed, errors = parse_meetings_csv(text.encode("utf-8-sig"))
        self.assertEqual([m["Meeting"] for m in parsed], ["Good"])
        self.assertEqual(len(errors), 2)
        self.assertTrue(errors[0].startswith("Row 3"))

    def test_missing_headers_and_bad_encoding(self):
        self.assertTrue(parse_meetings_csv(b"a,b\n1,2\n")[1])
        self.assertTrue(parse_meetings_csv(b"\xff\xfe\x00")[1])
        self.assertTrue(parse_meetings_csv(b"")[1])


class IcsTests(unittest.TestCase):
    def test_ics_structure_and_escaping(self):
        meeting, _ = prepare_meeting({"Meeting": "A, B; C", "Start": "09:00", "End": "10:00", "Description": "line1\nline2"})
        text = build_ics([meeting], date(2026, 1, 5))
        self.assertIn("SUMMARY:A\\, B\\; C", text)
        self.assertIn("DESCRIPTION:line1\\nline2", text)
        self.assertIn("DTSTART:20260105T033000Z", text)  # 09:00 IST == 03:30 UTC
        self.assertTrue(text.endswith("END:VCALENDAR\r\n"))

    def test_long_lines_are_folded_within_75_octets(self):
        folded = _ics_fold("DESCRIPTION:" + "é" * 120)
        for line in folded.split("\r\n"):
            self.assertLessEqual(len(line.encode("utf-8")), 75)
        self.assertEqual(folded.replace("\r\n ", ""), "DESCRIPTION:" + "é" * 120)


class StorageTests(unittest.TestCase):
    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "m.json"
            self.assertIsNone(save_meetings(default_meetings(), path))
            self.assertEqual(len(load_meetings(path)), 9)
            self.assertFalse(path.with_name("m.json.tmp").exists())

    def test_corrupt_and_invalid_data(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "m.json"
            path.write_text("{not json", encoding="utf-8")
            self.assertEqual(len(load_meetings(path)), 9)  # falls back to samples
            path.write_text(json.dumps([{"Meeting": "ok", "Start": "09:00", "End": "10:00"}, {"Meeting": "bad", "Start": "99:00", "End": "10:00"}, 5]), encoding="utf-8")
            self.assertEqual([m["Meeting"] for m in load_meetings(path)], ["ok"])
            path.write_text("[]", encoding="utf-8")
            self.assertEqual(load_meetings(path), [])


class GooglePayloadTests(unittest.TestCase):
    def test_payload_is_deterministic_and_valid(self):
        meeting, _ = prepare_meeting({"Meeting": "A", "Start": "09:00", "End": "10:00", "Attendees": "a@x.com"})
        first, second = event_payload(meeting, date(2026, 1, 5)), event_payload(meeting, date(2026, 1, 5))
        self.assertEqual(first, second)
        self.assertRegex(first["id"], r"^[0-9a-f]{32}$")
        self.assertEqual(first["start"]["dateTime"], "2026-01-05T09:00:00+05:30")
        self.assertEqual(first["attendees"], [{"email": "a@x.com"}])
        self.assertNotEqual(first["id"], event_payload(meeting, date(2026, 1, 6))["id"])


if __name__ == "__main__":
    unittest.main()
