"""
search.py
Search-based scheduler: starts from the greedy schedule and runs randomized
local search (hill-climbing) to find a higher-scoring schedule.

Moves tried each iteration:
  1. "move_day"  - relocate a session to another day in the plan window
  2. "swap_days" - swap the days of two sessions
  3. "add_block" - give an under-covered course a small block in a day's
                   leftover capacity (the main source of gains over greedy)

Every candidate is rebuilt into back-to-back start times and then checked with
ConstraintChecker.validate_sessions() -- the same function the tests use -- so
a candidate that breaks ANY hard constraint (exam deadline, daily capacity,
study window, overlap, ...) is rejected. The search can therefore only return
a schedule that is valid and at least as good as the greedy baseline.

Honest note on where the gain comes from: greedy places fixed 1.5h blocks and
wastes any smaller leftover time on a day; search recovers it with 0.5h blocks
and by moving sessions. It is a simple local search, not a global optimizer.
"""

import random
from datetime import date

from models import Course, StudySession, Schedule
from priority import PriorityEngine
from constraints import ConstraintChecker
from scheduler import GreedyScheduler, format_result

ADD_BLOCK_SIZE = 0.5  # finer grain than greedy's 1.5h, used to fill leftover gaps


class SearchScheduler:
    def __init__(self, availability: dict, preferred_time: str = "anytime",
                 iterations: int = 800, seed: int = None, start_date: date = None):
        self.availability = availability
        self.preferred_time = preferred_time
        self.checker = ConstraintChecker(availability, preferred_time, start_date)
        self.iterations = iterations
        self.rng = random.Random(seed)
        self.exam_dates = {}

    # ---- helpers -----------------------------------------------------------------

    def _hours_by_course(self, sessions):
        totals = {}
        for s in sessions:
            totals[s.course_name] = totals.get(s.course_name, 0.0) + s.duration
        return totals

    def _rebuild_start_hours(self, sessions):
        """Stack each day's sessions back-to-back from the preferred start hour."""
        by_day = {}
        for s in sessions:
            by_day.setdefault(s.day, []).append(s)
        rebuilt = []
        for day, day_sessions in by_day.items():
            cursor = self.checker.base_start
            for s in day_sessions:
                rebuilt.append(StudySession(s.course_name, day, cursor, s.duration))
                cursor += s.duration
        return rebuilt

    def _is_valid(self, sessions):
        return not self.checker.validate_sessions(sessions, self.exam_dates)

    def _score(self, sessions, courses_by_name):
        """Maximize priority-weighted scheduled hours plus a small preference bonus."""
        score = 0.0
        for s in sessions:
            course = courses_by_name[s.course_name]
            score += s.duration * (1 + course.priority)
            score += self.checker.preference_bonus(s.start_hour) * 0.25
        return score

    # ---- main search -------------------------------------------------------------------

    def generate_schedule(self, courses) -> Schedule:
        names = [c.name for c in courses]
        if len(names) != len(set(names)):
            raise ValueError("Course names must be unique.")

        engine = PriorityEngine(self.checker.start_date)
        engine.rank(courses)
        courses_by_name = {c.name: c for c in courses}
        self.exam_dates = {c.name: c.exam_date for c in courses}

        # Greedy baseline on copies (so `courses` isn't double-counted); always valid.
        baseline_courses = [
            Course(c.name, c.difficulty, c.exam_date, c.required_hours, c.priority, 0.0)
            for c in courses
        ]
        baseline = GreedyScheduler(self.availability, self.preferred_time,
                                   self.checker.start_date).generate_schedule(baseline_courses)

        best = [StudySession(s.course_name, s.day, s.start_hour, s.duration) for s in baseline.sessions]
        best_score = self._score(best, courses_by_name)
        days = [d for d, _ in self.checker.week]

        for _ in range(self.iterations):
            candidate = [StudySession(s.course_name, s.day, s.start_hour, s.duration) for s in best]
            move = self.rng.choice(["move_day", "swap_days", "add_block"])

            if move == "move_day" and candidate:
                idx = self.rng.randrange(len(candidate))
                s = candidate[idx]
                candidate[idx] = StudySession(s.course_name, self.rng.choice(days), s.start_hour, s.duration)

            elif move == "swap_days" and len(candidate) >= 2:
                i, j = self.rng.sample(range(len(candidate)), 2)
                day_i, day_j = candidate[i].day, candidate[j].day
                candidate[i] = StudySession(candidate[i].course_name, day_j, candidate[i].start_hour, candidate[i].duration)
                candidate[j] = StudySession(candidate[j].course_name, day_i, candidate[j].start_hour, candidate[j].duration)

            elif move == "add_block":
                scheduled = self._hours_by_course(candidate)
                under_covered = [c for c in courses if c.required_hours - scheduled.get(c.name, 0.0) > 1e-6]
                if not under_covered:
                    continue
                course = self.rng.choice(under_covered)
                options = self.checker.allowed_days(course.exam_date)  # only days on/before the exam
                if not options:
                    continue
                day = self.rng.choice(options)
                day_used = sum(s.duration for s in candidate if s.day == day)
                leftover = self.checker.day_capacity(day) - day_used
                remaining_needed = course.required_hours - scheduled.get(course.name, 0.0)
                block = min(ADD_BLOCK_SIZE, leftover, remaining_needed)
                if block <= 1e-6:
                    continue
                candidate.append(StudySession(course.name, day, 0.0, block))  # start fixed by rebuild
            else:
                continue

            candidate = self._rebuild_start_hours(candidate)
            if not self._is_valid(candidate):
                continue

            candidate_score = self._score(candidate, courses_by_name)
            if candidate_score >= best_score:
                best = candidate
                best_score = candidate_score

        totals = self._hours_by_course(best)
        for c in courses:
            c.scheduled_hours = totals.get(c.name, 0.0)

        return Schedule(best)


def generate_schedule_api(courses, availability, preferred_time="anytime",
                          iterations=800, seed=None, start_date=None):
    """Same output shape as scheduler.generate_schedule_api."""
    scheduler = SearchScheduler(availability, preferred_time, iterations=iterations,
                                seed=seed, start_date=start_date)
    schedule = scheduler.generate_schedule(courses)
    return format_result(courses, schedule, scheduler.checker)
