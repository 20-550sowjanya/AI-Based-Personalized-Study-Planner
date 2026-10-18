import unittest
from datetime import timedelta

import helpers
from helpers import START
from models import Course
from priority import PriorityEngine


class PriorityTests(unittest.TestCase):
    def setUp(self):
        self.engine = PriorityEngine(START)
        self.exam = START + timedelta(days=20)

    def test_higher_difficulty_gives_higher_priority(self):
        easy, hard = Course("e", 1, self.exam, 6), Course("h", 5, self.exam, 6)
        self.assertGreater(self.engine.score(hard), self.engine.score(easy))

    def test_closer_exam_gives_higher_priority(self):
        near, far = Course("n", 3, START + timedelta(days=3), 6), Course("f", 3, START + timedelta(days=40), 6)
        self.assertGreater(self.engine.score(near), self.engine.score(far))

    def test_more_hours_gives_higher_priority(self):
        small, big = Course("s", 3, self.exam, 2), Course("b", 3, self.exam, 12)
        self.assertGreater(self.engine.score(big), self.engine.score(small))

    def test_passed_exam_is_not_urgent(self):
        self.assertEqual(self.engine.urgency_score(START - timedelta(days=2)), 0.0)

    def test_rank_orders_descending(self):
        ranked = self.engine.rank(helpers.sample_courses())
        priorities = [c.priority for c in ranked]
        self.assertEqual(priorities, sorted(priorities, reverse=True))


if __name__ == "__main__":
    unittest.main()
