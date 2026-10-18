import random
import unittest
from datetime import timedelta

import helpers
from helpers import START, avail
from constraints import ConstraintChecker
from models import Course, StudySession
import scheduler
import search


def to_sessions(result):
    return [StudySession(s["course"], s["day"], s["start_hour"], s["duration"]) for s in result["sessions"]]


def coverage(result):
    req = sum(c["required_hours"] for c in result["courses"])
    return sum(c["scheduled_hours"] for c in result["courses"]) / req


class SearchTests(unittest.TestCase):
    def test_search_never_violates_any_hard_constraint(self):
        rng = random.Random(11)
        for i in range(60):
            courses = helpers.random_courses(rng)
            a = helpers.random_availability(rng)
            pref = rng.choice(["anytime", "morning", "afternoon", "evening"])
            r = search.generate_schedule_api(courses, a, pref, iterations=200, seed=i, start_date=START)
            checker = ConstraintChecker(a, pref, START)
            exams = {c.name: c.exam_date for c in courses}
            self.assertEqual(checker.validate_sessions(to_sessions(r), exams), [])

    def test_search_never_schedules_after_exam(self):
        courses = [Course("Early", 5, START + timedelta(days=1), 12),
                   Course("Late", 3, START + timedelta(days=30), 12)]
        for seed in range(10):
            r = search.generate_schedule_api(courses, avail(6), "anytime", iterations=400, seed=seed, start_date=START)
            early_days = {s["day"] for s in r["sessions"] if s["course"] == "Early"}
            self.assertTrue(early_days <= {"Monday", "Tuesday"})

    def test_search_coverage_never_below_greedy(self):
        rng = random.Random(3)
        for i in range(40):
            courses = helpers.random_courses(rng)
            a = helpers.random_availability(rng)
            g = scheduler.generate_schedule_api(
                [Course(c.name, c.difficulty, c.exam_date, c.required_hours) for c in courses], a, "anytime", START)
            s = search.generate_schedule_api(courses, a, "anytime", iterations=300, seed=i, start_date=START)
            self.assertGreaterEqual(coverage(s) + 1e-9, coverage(g))

    def test_search_improves_on_greedy_for_sample_data(self):
        g = scheduler.generate_schedule_api(helpers.sample_courses(), avail(3), "evening", START)
        s = search.generate_schedule_api(helpers.sample_courses(), avail(3), "evening",
                                         iterations=1500, seed=42, start_date=START)
        self.assertGreater(coverage(s), coverage(g))

    def test_same_seed_gives_same_result(self):
        a = search.generate_schedule_api(helpers.sample_courses(), avail(3), "anytime", iterations=300, seed=5, start_date=START)
        b = search.generate_schedule_api(helpers.sample_courses(), avail(3), "anytime", iterations=300, seed=5, start_date=START)
        self.assertEqual(a["sessions"], b["sessions"])

    def test_duplicate_course_names_are_rejected(self):
        dup = [Course("AI", 5, START + timedelta(days=9), 5), Course("AI", 2, START + timedelta(days=12), 3)]
        with self.assertRaises(ValueError):
            search.generate_schedule_api(dup, avail(3), "anytime", start_date=START)


if __name__ == "__main__":
    unittest.main()
