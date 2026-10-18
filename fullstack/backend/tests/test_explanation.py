import unittest
from datetime import timedelta

from helpers import START
from explanation import explain
from models import Course


class ExplanationTests(unittest.TestCase):
    def test_mentions_exam_only_when_it_is_actually_near(self):
        far = Course("Far", 5, START + timedelta(days=45), 6)
        far.priority = 0.7  # high priority purely from difficulty
        text = explain(far, START)
        self.assertIn("high difficulty", text)
        self.assertNotIn("exam in", text)

    def test_reports_real_days_until_exam(self):
        near = Course("Near", 2, START + timedelta(days=6), 3)
        near.priority = 0.5
        self.assertIn("exam in 6 days", explain(near, START))

    def test_passed_exam_is_explained(self):
        done = Course("Done", 3, START - timedelta(days=1), 3)
        done.priority = 0.1
        self.assertIn("already passed", explain(done, START))


if __name__ == "__main__":
    unittest.main()
