"""
constraints.py
Hard and soft constraints for the study schedule.

The plan covers 7 consecutive calendar days starting at `start_date`, so every
weekday name maps to one real date. That is what makes the exam-deadline
constraint enforceable: a session on a given day is only allowed if that day's
date is on or before the course's exam date.

Hard constraints (a schedule violating any of these is invalid):
  1. every session is on a day inside the plan window
  2. session duration is positive
  3. the course exists
  4. the session is on or before the course's exam date
  5. the session lies inside the daily study window (DAY_START_HOUR..DAY_END_HOUR)
  6. total hours on a day never exceed that day's usable capacity
  7. no two sessions on the same day overlap

Soft constraint: a bonus for sessions that start in the preferred time of day.
"""

from datetime import date, timedelta

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# Studying is only allowed between these clock hours (24h). 23.0 = 11 PM.
DAY_START_HOUR = 6.0
DAY_END_HOUR = 23.0

# Where each day's first session starts for each preference.
PREFERRED_START_HOUR = {
    "morning": 8.0,
    "afternoon": 13.0,
    "evening": 18.0,
    "anytime": 9.0,
}

EPS = 1e-6


def build_week(start_date: date):
    """Return [(weekday_name, date), ...] for 7 consecutive days from start_date."""
    return [
        (DAY_NAMES[(start_date + timedelta(days=i)).weekday()], start_date + timedelta(days=i))
        for i in range(7)
    ]


class ConstraintChecker:
    def __init__(self, availability: dict, preferred_time: str = "anytime", start_date: date = None):
        """
        availability: {"Monday": 3, "Tuesday": 2, ...} hours the student could study that weekday
        preferred_time: "morning" | "afternoon" | "evening" | "anytime"
        start_date: first day of the 7-day plan window (defaults to today)
        """
        self.availability = availability
        self.preferred_time = preferred_time
        self.start_date = start_date or date.today()
        self.week = build_week(self.start_date)
        self.day_date = dict(self.week)
        self.base_start = PREFERRED_START_HOUR.get(preferred_time, PREFERRED_START_HOUR["anytime"])

    # ---- capacity ----------------------------------------------------------

    def day_capacity(self, day: str) -> float:
        """Usable hours on a day: what the student entered, but never more than
        fits between the preferred start time and the end of the study window."""
        window = max(0.0, DAY_END_HOUR - self.base_start)
        return min(float(self.availability.get(day, 0) or 0), window)

    def capacity_warnings(self):
        """Days where the entered availability can't all be used."""
        warnings = []
        for day, _ in self.week:
            entered = float(self.availability.get(day, 0) or 0)
            usable = self.day_capacity(day)
            if entered > usable + EPS:
                warnings.append(
                    f"{day}: {entered:g}h entered, but only {usable:g}h fit between "
                    f"the preferred start time and the end of the study window."
                )
        return warnings

    # ---- individual checks (used by the greedy scheduler while building) -------

    def day_has_room(self, day: str, existing_sessions, extra_hours: float) -> bool:
        used = sum(s.duration for s in existing_sessions if s.day == day)
        return used + extra_hours <= self.day_capacity(day) + EPS

    def no_overlap(self, day: str, start_hour: float, duration: float, existing_sessions) -> bool:
        new_end = start_hour + duration
        for s in existing_sessions:
            if s.day != day:
                continue
            if start_hour < s.start_hour + s.duration - EPS and s.start_hour < new_end - EPS:
                return False
        return True

    def before_exam(self, day: str, exam_date: date) -> bool:
        """True if `day` (a weekday inside the plan window) is on or before the exam."""
        d = self.day_date.get(day)
        return d is not None and d <= exam_date

    def within_study_window(self, start_hour: float, duration: float) -> bool:
        return start_hour >= DAY_START_HOUR - EPS and start_hour + duration <= DAY_END_HOUR + EPS

    def allowed_days(self, exam_date: date):
        """Weekday names in the window that are on or before the exam."""
        return [day for day, d in self.week if d <= exam_date]

    # ---- full validation (single source of truth) --------------------------------

    def validate_sessions(self, sessions, exam_dates: dict):
        """
        Check a complete list of sessions against every hard constraint.
        exam_dates: {course_name: exam_date}
        Returns a list of human-readable violations (empty list = valid).
        """
        violations = []
        by_day = {}

        for s in sessions:
            if s.day not in self.day_date:
                violations.append(f"{s.course_name}: unknown day {s.day!r}")
                continue
            if s.duration <= 0:
                violations.append(f"{s.course_name} on {s.day}: non-positive duration")
            if s.course_name not in exam_dates:
                violations.append(f"unknown course {s.course_name!r}")
                continue
            if not self.before_exam(s.day, exam_dates[s.course_name]):
                violations.append(f"{s.course_name} on {s.day}: session is after the exam date")
            if not self.within_study_window(s.start_hour, s.duration):
                violations.append(f"{s.course_name} on {s.day}: outside the daily study window")
            by_day.setdefault(s.day, []).append(s)

        for day, day_sessions in by_day.items():
            total = sum(s.duration for s in day_sessions)
            if total > self.day_capacity(day) + EPS:
                violations.append(f"{day}: {total:g}h scheduled exceeds capacity {self.day_capacity(day):g}h")
            ordered = sorted(day_sessions, key=lambda s: s.start_hour)
            for a, b in zip(ordered, ordered[1:]):
                if a.start_hour + a.duration > b.start_hour + EPS:
                    violations.append(f"{day}: {a.course_name} overlaps {b.course_name}")

        return violations

    # ---- soft constraint -----------------------------------------------------------

    def preference_bonus(self, start_hour: float) -> float:
        windows = {"morning": (6, 12), "afternoon": (12, 17), "evening": (17, 23)}
        if self.preferred_time not in windows:
            return 0.0
        lo, hi = windows[self.preferred_time]
        return 1.0 if lo <= start_hour < hi else 0.0
