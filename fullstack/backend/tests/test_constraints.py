import unittest
from datetime import timedelta

import helpers
from helpers import START, avail
from constraints import ConstraintChecker, DAY_END_HOUR, build_week
from models import StudySession


class ConstraintTests(unittest.TestCase):
    def setUp(self):
        self.checker = ConstraintChecker(avail(4), "anytime", START)
        self.exams = {"AI": START + timedelta(days=2)}  # Wednesday

    def test_week_maps_days_to_real_dates(self):
        week = build_week(START)
        self.assertEqual(week[0][0], "Monday")
        self.assertEqual(week[0][1], START)
        self.assertEqual(week[6], ("Sunday", START + timedelta(days=6)))

    def test_valid_schedule_has_no_violations(self):
        s = [StudySession("AI", "Monday", 9, 1.5), StudySession("AI", "Tuesday", 9, 1.5)]
        self.assertEqual(self.checker.validate_sessions(s, self.exams), [])

    def test_session_after_exam_is_rejected(self):
        v = self.checker.validate_sessions([StudySession("AI", "Thursday", 9, 1)], self.exams)
        self.assertTrue(any("after the exam" in x for x in v))

    def test_session_on_exam_day_is_allowed(self):
        self.assertEqual(self.checker.validate_sessions([StudySession("AI", "Wednesday", 9, 1)], self.exams), [])

    def test_overlap_is_rejected(self):
        s = [StudySession("AI", "Monday", 9, 2), StudySession("AI", "Monday", 10, 1)]
        self.assertTrue(any("overlaps" in x for x in self.checker.validate_sessions(s, self.exams)))

    def test_over_capacity_is_rejected(self):
        s = [StudySession("AI", "Monday", 9, 3), StudySession("AI", "Monday", 12, 2)]  # 5h > 4h
        self.assertTrue(any("exceeds capacity" in x for x in self.checker.validate_sessions(s, self.exams)))

    def test_session_past_end_of_day_is_rejected(self):
        v = self.checker.validate_sessions([StudySession("AI", "Monday", 22, 2)], self.exams)
        self.assertTrue(any("study window" in x for x in v))

    def test_unknown_course_and_bad_duration_are_rejected(self):
        v = self.checker.validate_sessions(
            [StudySession("Nope", "Monday", 9, 1), StudySession("AI", "Monday", 12, 0)], self.exams)
        self.assertTrue(any("unknown course" in x for x in v))
        self.assertTrue(any("non-positive" in x for x in v))

    def test_unknown_day_is_rejected(self):
        v = self.checker.validate_sessions([StudySession("AI", "Funday", 9, 1)], self.exams)
        self.assertTrue(any("unknown day" in x for x in v))

    def test_capacity_is_capped_by_study_window(self):
        evening = ConstraintChecker(avail(14), "evening", START)
        self.assertEqual(evening.day_capacity("Monday"), DAY_END_HOUR - 18)
        self.assertTrue(evening.capacity_warnings())

    def test_allowed_days_stop_at_exam(self):
        self.assertEqual(self.checker.allowed_days(START + timedelta(days=2)), ["Monday", "Tuesday", "Wednesday"])


if __name__ == "__main__":
    unittest.main()
