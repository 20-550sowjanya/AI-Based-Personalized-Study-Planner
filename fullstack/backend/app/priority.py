"""
priority.py
Computes a priority score for each course from three weighted attributes:
difficulty, exam urgency (inverse of days remaining), and required study hours.

This is the heuristic used by the greedy scheduler (Milestone 1) and will
also seed the evaluation function for the search-based scheduler (Milestone 2).
"""

from datetime import date

# Weights are tunable; they sum to 1.0 for an interpretable score in [0, 1]-ish range.
W_DIFFICULTY = 0.4
W_URGENCY = 0.4
W_HOURS = 0.2


class PriorityEngine:
    def __init__(self, today: date = None):
        self.today = today or date.today()

    def urgency_score(self, exam_date: date) -> float:
        days_left = (exam_date - self.today).days
        if days_left < 0:
            # Exam already happened: studying for it is pointless, so it is not urgent.
            return 0.0
        # Fewer days left -> higher urgency. Normalize against a 60-day horizon.
        return max(0.0, 1 - (max(days_left, 1) / 60))

    def score(self, course) -> float:
        difficulty_norm = course.difficulty / 5.0
        urgency_norm = self.urgency_score(course.exam_date)
        hours_norm = min(course.required_hours / 15.0, 1.0)

        priority = (
            W_DIFFICULTY * difficulty_norm
            + W_URGENCY * urgency_norm
            + W_HOURS * hours_norm
        )
        course.priority = round(priority, 4)
        return course.priority

    def rank(self, courses):
        for c in courses:
            self.score(c)
        return sorted(courses, key=lambda c: c.priority, reverse=True)
