"""
models.py
Core data structures shared across the scheduling pipeline.
"""

from dataclasses import dataclass, field
from datetime import date


@dataclass
class Course:
    name: str
    difficulty: int          # 1 (easy) - 5 (hard)
    exam_date: date
    required_hours: float    # total hours the student wants to study this course
    priority: float = 0.0    # filled in by PriorityEngine
    scheduled_hours: float = field(default=0.0)


@dataclass
class StudySession:
    course_name: str
    day: str                 # e.g. "Monday"
    start_hour: float        # 0-24 offset within the day's available block
    duration: float          # hours


@dataclass
class Schedule:
    sessions: list

    def hours_for(self, course_name: str) -> float:
        return sum(s.duration for s in self.sessions if s.course_name == course_name)

    def by_day(self):
        grouped = {}
        for s in self.sessions:
            grouped.setdefault(s.day, []).append(s)
        return grouped
