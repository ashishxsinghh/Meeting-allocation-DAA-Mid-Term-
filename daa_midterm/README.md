# DAA Midterm — Smart Meeting Scheduler

A Streamlit project for Design & Analysis of Algorithms (DAA) that schedules meetings with greedy algorithms.

## Features

- **Activity Selection** — picks the maximum number of non-overlapping meetings for one room (Earliest Finish Time is provably optimal).
- **Interval Partitioning** — assigns every meeting to the minimum number of rooms using a min-heap.
- **Strategy comparison** — Earliest Finish Time vs Earliest Start Time vs Shortest Duration First, with a step-by-step execution trace.
- **Interactive timelines** (Plotly), meeting add / edit / delete, local JSON persistence.
- **CSV import / export** and **.ics calendar export** (no account needed).
- **Google Calendar sync** (optional OAuth) — creates events in your primary calendar; invitations are only emailed if you tick the checkbox.

## Project structure

```
app.py                  Entry point (layout and tab wiring only)
daa_midterm/
  config.py             Constants and sample data
  models.py             Meeting validation and time helpers
  algorithms.py         Greedy algorithms and schedule statistics
  formats.py            CSV and .ics import/export
  storage.py            Local JSON persistence
  google_cal.py         Google Calendar API (no Streamlit code)
  oauth.py              Streamlit glue for Google sign-in
  charts.py, styles.py, ui.py
  views/                One file per tab
tests/                  Unit tests (algorithms, validation, CSV/ICS, storage)
.streamlit/             Theme config and secrets.toml.example
```

## Run it

Requires Python 3.9+.

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
python3 -m pip install -r requirements.txt
python3 -m streamlit run app.py
```

Then open <http://localhost:8501>.

## Run the tests

```bash
python3 -m unittest discover -s tests -t .
```

The tests compare the greedy algorithms against brute-force search on random schedules.

## Google Calendar

Follow [GOOGLE_CALENDAR_SETUP.md](GOOGLE_CALENDAR_SETUP.md). The `.ics` export works without any setup.

## Data and secrets

- Meetings are saved to `meetings_data.json` beside `app.py` (override with the `DAA_MIDTERM_DATA_FILE` environment variable).
- Google credentials go in `.streamlit/secrets.toml` (copy `secrets.toml.example`). Both files are git-ignored — never commit them.
- Times are 24-hour `HH:MM` in the `Asia/Kolkata` time zone; change `LOCAL_TZ` in `daa_midterm/config.py` to use another.
- Meetings cannot cross midnight.
