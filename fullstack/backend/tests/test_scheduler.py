import random
import unittest
from datetime import timedelta

import helpers
from helpers import START, avail
from constraints import ConstraintChecker, DAY_END_HOUR
from models import Course, StudySession
import scheduler


def to_sessions(result):
    return [StudySession(s["course"], s["day"], s["start_hour"], s["duration"]) for s in result["sessions"]]


class GreedyTests(unittest.TestCase):
    def test_never_schedules_after_exam(self):
        courses = [Course("Early", 5, START + timedelta(days=1), 12)]  # exam Tuesday
        r = scheduler.generate_schedule_api(courses, avail(4), "anytime", START)
        self.assertTrue(r["sessions"])
        self.assertTrue(all(s["day"] in ("Monday", "Tuesday") for s in r["sessions"]))

    def test_sessions_carry_real_dates(self):
        r = scheduler.generate_schedule_api(helpers.sample_courses(), avail(3), "anytime", START)
        self.assertEqual(r["week"][0], {"day": "Monday", "date": START.isoformat()})
        self.assertTrue(all("date" in s for s in r["sessions"]))

    def test_never_runs_past_end_of_study_window(self):
        courses = [Course(f"C{i}", 3, START + timedelta(days=40), 12) for i in range(5)]
        r = scheduler.generate_schedule_api(courses, avail(14), "evening", START)
        self.assertLessEqual(max(s["start_hour"] + s["duration"] for s in r["sessions"]), DAY_END_HOUR)
        self.assertTrue(r["warnings"])  # tells the user availability was capped

    def test_exam_before_plan_start_gets_nothing_and_a_warning(self):
        courses = [Course("Done", 5, START - timedelta(days=3), 6)]
        r = scheduler.generate_schedule_api(courses, avail(4), "anytime", START)
        self.assertEqual(r["sessions"], [])
        self.assertTrue(any("before the plan start" in w for w in r["warnings"]))

    def test_random_inputs_always_produce_valid_schedules(self):
        rng = random.Random(7)
        for _ in range(200):
            courses = helpers.random_courses(rng)
            a = helpers.random_availability(rng)
            pref = rng.choice(["anytime", "morning", "afternoon", "evening"])
            r = scheduler.generate_schedule_api(courses, a, pref, START)
            checker = ConstraintChecker(a, pref, START)
            exams = {c.name: c.exam_date for c in courses}
            self.assertEqual(checker.validate_sessions(to_sessions(r), exams), [])

    def test_never_exceeds_required_hours(self):
        r = scheduler.generate_schedule_api(helpers.sample_courses(), avail(14), "anytime", START)
        for c in r["courses"]:
            self.assertLessEqual(c["scheduled_hours"], c["required_hours"] + 1e-9)


if __name__ == "__main__":
    unittest.main()
