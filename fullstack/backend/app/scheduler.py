"""
scheduler.py
Greedy scheduler: ranks courses by priority and, for each course in turn, places
one study block per day across the 7-day plan window, skipping any day that is
after that course's exam date and any day without room.

Also holds format_result(), the single place that turns a finished schedule
into the dict the API returns (shared with search.py).
"""

from datetime import date

from models import StudySession, Schedule
from priority import PriorityEngine
from constraints import ConstraintChecker, DAY_NAMES, PREFERRED_START_HOUR  # noqa: F401 (re-exported)

BLOCK_SIZE = 1.5  # hours per study block


class GreedyScheduler:
    def __init__(self, availability: dict, preferred_time: str = "anytime", start_date: date = None):
        self.availability = availability
        self.preferred_time = preferred_time
        self.checker = ConstraintChecker(availability, preferred_time, start_date)

    def generate_schedule(self, courses) -> Schedule:
        checker = self.checker
        engine = PriorityEngine(checker.start_date)
        ranked_courses = engine.rank(courses)

        for c in courses:
            c.scheduled_hours = 0.0

        sessions = []
        for course in ranked_courses:
            hours_remaining = course.required_hours
            for day, _day_date in checker.week:
                if hours_remaining <= 1e-9:
                    break
                if not checker.before_exam(day, course.exam_date):
                    continue

                block = min(BLOCK_SIZE, hours_remaining)
                used_today = sum(s.duration for s in sessions if s.day == day)
                start_hour = checker.base_start + used_today

                if (checker.day_has_room(day, sessions, block)
                        and checker.within_study_window(start_hour, block)
                        and checker.no_overlap(day, start_hour, block, sessions)):
                    sessions.append(StudySession(course.name, day, start_hour, block))
                    hours_remaining -= block
                    course.scheduled_hours += block

        return Schedule(sessions)


def format_result(courses, schedule, checker):
    """Build the API/UI result dict from a finished schedule."""
    warnings = list(checker.capacity_warnings())
    for c in courses:
        if c.exam_date < checker.start_date:
            warnings.append(f"{c.name}: exam date {c.exam_date.isoformat()} is before the plan "
                            f"start ({checker.start_date.isoformat()}), so nothing was scheduled for it.")

    return {
        "week": [{"day": d, "date": dt.isoformat()} for d, dt in checker.week],
        "warnings": warnings,
        "courses": [
            {
                "name": c.name,
                "priority": c.priority,
                "required_hours": c.required_hours,
                "scheduled_hours": round(c.scheduled_hours, 2),
            }
            for c in sorted(courses, key=lambda c: c.priority, reverse=True)
        ],
        "sessions": [
            {
                "course": s.course_name,
                "day": s.day,
                "date": checker.day_date[s.day].isoformat(),
                "start_hour": s.start_hour,
                "duration": s.duration,
            }
            for s in schedule.sessions
        ],
    }


def generate_schedule_api(courses, availability, preferred_time="anytime", start_date=None):
    """
    Prototype API entry point.
      courses: list[Course]
      availability: dict[str, float]  e.g. {"Monday": 3, ...}
      preferred_time: "morning" | "afternoon" | "evening" | "anytime"
      start_date: first day of the 7-day plan window (default: today)
    """
    scheduler = GreedyScheduler(availability, preferred_time, start_date)
    schedule = scheduler.generate_schedule(courses)
    return format_result(courses, schedule, scheduler.checker)
