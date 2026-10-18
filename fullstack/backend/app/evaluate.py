"""
evaluate.py
Compares the greedy and search schedulers over many randomly generated
scenarios (not one hand-picked dataset), and checks every produced schedule
against all hard constraints.

Run from backend/app:   python evaluate.py [num_scenarios] [search_iterations]

Metrics per scenario: study-hour coverage, hard-constraint violations,
preference satisfaction (share of sessions starting in the preferred window),
and run time. The summary reports means and how often search beats / ties /
loses to greedy.
"""

import random
import sys
import time
from datetime import date, timedelta
from statistics import mean

from constraints import ConstraintChecker, DAY_NAMES
from models import Course, StudySession
import scheduler
import search

START = date(2026, 10, 5)  # a Monday
PREFS = ["anytime", "morning", "afternoon", "evening"]


def make_scenario(rng):
    n = rng.randint(3, 7)
    courses = [
        Course(f"Course{i}", rng.randint(1, 5), START + timedelta(days=rng.randint(2, 40)),
               float(rng.randint(3, 14)))
        for i in range(n)
    ]
    availability = {d: float(rng.randint(1, 6)) for d in DAY_NAMES}
    return courses, availability, rng.choice(PREFS)


def clone(courses):
    return [Course(c.name, c.difficulty, c.exam_date, c.required_hours) for c in courses]


def coverage(result):
    req = sum(c["required_hours"] for c in result["courses"])
    return 100 * sum(c["scheduled_hours"] for c in result["courses"]) / req


def preference_rate(result, checker):
    sessions = result["sessions"]
    if not sessions or checker.preferred_time == "anytime":
        return None
    return sum(checker.preference_bonus(s["start_hour"]) for s in sessions) / len(sessions)


def violations(result, courses, checker):
    sessions = [StudySession(s["course"], s["day"], s["start_hour"], s["duration"]) for s in result["sessions"]]
    return len(checker.validate_sessions(sessions, {c.name: c.exam_date for c in courses}))


def main(num_scenarios=200, iterations=800):
    rng = random.Random(2026)
    rows = []
    for i in range(num_scenarios):
        courses, availability, pref = make_scenario(rng)
        checker = ConstraintChecker(availability, pref, START)

        t0 = time.perf_counter()
        g = scheduler.generate_schedule_api(clone(courses), availability, pref, START)
        t_g = time.perf_counter() - t0

        t0 = time.perf_counter()
        s = search.generate_schedule_api(clone(courses), availability, pref,
                                         iterations=iterations, seed=i, start_date=START)
        t_s = time.perf_counter() - t0

        rows.append({
            "g_cov": coverage(g), "s_cov": coverage(s),
            "g_viol": violations(g, courses, checker), "s_viol": violations(s, courses, checker),
            "g_pref": preference_rate(g, checker), "s_pref": preference_rate(s, checker),
            "g_ms": t_g * 1000, "s_ms": t_s * 1000,
        })

    better = sum(r["s_cov"] > r["g_cov"] + 1e-9 for r in rows)
    worse = sum(r["s_cov"] < r["g_cov"] - 1e-9 for r in rows)
    ties = len(rows) - better - worse
    gains = [r["s_cov"] - r["g_cov"] for r in rows]
    g_pref = [r["g_pref"] for r in rows if r["g_pref"] is not None]
    s_pref = [r["s_pref"] for r in rows if r["s_pref"] is not None]

    print(f"Scenarios: {num_scenarios}   search iterations: {iterations}")
    print(f"Mean coverage      greedy {mean(r['g_cov'] for r in rows):5.1f}%   search {mean(r['s_cov'] for r in rows):5.1f}%")
    print(f"Mean gain          {mean(gains):+.1f} pts   (max {max(gains):+.1f}, min {min(gains):+.1f})")
    print(f"Search vs greedy   better {better}   tied {ties}   worse {worse}")
    print(f"Hard violations    greedy {sum(r['g_viol'] for r in rows)}   search {sum(r['s_viol'] for r in rows)}")
    if g_pref:
        print(f"Preference match   greedy {100*mean(g_pref):4.1f}%   search {100*mean(s_pref):4.1f}%   (scenarios with a preference)")
    print(f"Mean run time      greedy {mean(r['g_ms'] for r in rows):6.2f} ms   search {mean(r['s_ms'] for r in rows):6.1f} ms")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    it = int(sys.argv[2]) if len(sys.argv) > 2 else 800
    main(n, it)
