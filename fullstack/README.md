# AI Study Planner — Full-Stack Version

A FastAPI backend wrapping a constraint-based scheduling engine (greedy and
search-based schedulers) plus a plain HTML/CSS/JS dashboard frontend.

```
fullstack/
  backend/
    requirements.txt
    app/
      main.py          FastAPI app: validated REST endpoints
      models.py        Course / StudySession / Schedule data classes
      priority.py      priority score (difficulty, exam urgency, workload)
      constraints.py   hard + soft constraints, validate_sessions()
      scheduler.py     greedy scheduler + result formatting
      search.py        hill-climbing local search starting from greedy
      explanation.py   plain-English reasons per course
      evaluate.py      greedy-vs-search comparison over many random scenarios
      data_loader.py, study_data.csv
    tests/             unittest suite (no extra packages needed)
  frontend/
    index.html         the dashboard (no build step)
    config.js          set API_BASE here if the backend isn't on 127.0.0.1:8000
```

Data flow: `models -> priority -> constraints -> scheduler -> search -> FastAPI -> HTML/JS`.

## How scheduling works

A plan covers **7 consecutive calendar days starting at the "Plan starts on" date**
(default: today). Each weekday maps to one real date, which is what lets the
scheduler enforce exam deadlines.

Hard constraints (checked by `ConstraintChecker.validate_sessions`, used by the
tests and by every search move):

1. sessions fall on a day inside the plan window
2. durations are positive and the course exists
3. **no session is scheduled after the course's exam date** (the exam day itself is allowed)
4. sessions stay inside the daily study window, **6 AM – 11 PM**
5. a day's total never exceeds its usable capacity
6. sessions on the same day never overlap

Capacity: the hours you enter per weekday, capped by the time left between the
preferred start time (morning 8, afternoon 1 PM, evening 6 PM, anytime 9) and
11 PM. If your entry can't all be used (e.g. 14h with an evening preference) the
UI shows a warning instead of silently scheduling past midnight.

Soft constraint: a small bonus for sessions that start in the preferred time of day.

Courses whose exam is before the plan start get no sessions and a warning.
Course names must be unique (case-insensitive).

**Greedy**: ranks courses by priority; for each course places up to one 1.5h
block per allowed day.
**Search**: starts from the greedy schedule and tries moving sessions, swapping
days, and adding 0.5h blocks into leftover capacity, keeping a change only if it
scores higher and passes full validation. Most of its gain over greedy comes from
recovering leftover time that greedy's fixed 1.5h blocks waste; it is a simple
local search, not a global optimizer.

## Run the backend

```
cd backend
python -m venv venv
venv\Scripts\activate          (Windows)   |   source venv/bin/activate  (Mac/Linux)
pip install -r requirements.txt
cd app
uvicorn main:app --reload --port 8000
```

Check http://127.0.0.1:8000/health, and see the interactive API docs at /docs.

## Open the frontend

Double-click `frontend/index.html`. Use **Load example data**, then **Generate
study plan** or **Compare both algorithms**. If the backend is elsewhere, edit
`frontend/config.js`.

Note: the bundled example exam dates are in Oct–Nov 2026. After they pass, the
app will (correctly) warn that those exams are before the plan start; edit the
dates or `backend/app/study_data.csv`.

## Tests

```
cd backend
python -m unittest discover -s tests -v
```

Covers priority, constraints, both schedulers (including randomized scenarios
that validate every produced schedule), explanations, and the API. API tests
need `fastapi` and `httpx` (`pip install httpx`) and are skipped automatically
if those aren't installed.

## Evaluation

```
cd backend/app
python evaluate.py 200 800      # scenarios, search iterations
```

Compares greedy and search over randomly generated scenarios and reports mean
coverage, how often search wins/ties/loses, hard-constraint violations,
preference match, and run time.

## API

`GET /health` · `GET /sample-courses` · `POST /schedule`

```json
{
  "courses": [{"name": "CSCE 5210 - AI", "difficulty": 5, "exam_date": "2026-10-20", "required_hours": 10}],
  "availability": {"Monday": 3, "Tuesday": 2, "Wednesday": 3, "Thursday": 2, "Friday": 2, "Saturday": 4, "Sunday": 4},
  "preferred_time": "evening",
  "algorithm": "search",
  "start_date": "2026-10-07",
  "iterations": 800,
  "seed": null
}
```

Invalid input (unknown/negative availability, duplicate course names, bad dates,
difficulty outside 1–5, ...) returns HTTP 422 with a message. The response has
`coverage_percent`, `week` (the 7 dates), `warnings`, ranked `courses` (with
explanations), and `sessions` (each with its date).

CORS: open (`*`) for local development. For deployment set
`STUDY_PLANNER_ORIGINS="https://your-frontend.example.com"` before starting uvicorn.
