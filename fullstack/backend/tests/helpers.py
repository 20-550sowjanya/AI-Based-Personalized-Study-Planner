import random
from datetime import date, timedelta

import context  # noqa: F401
from models import Course

# A Monday, so weekday order in tests is easy to reason about.
START = date(2026, 10, 5)
ALL_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def avail(hours=3.0, **overrides):
    a = {d: hours for d in ALL_DAYS}
    a.update(overrides)
    return a


def sample_courses():
    return [
        Course("AI", 5, START + timedelta(days=15), 10),
        Course("Databases", 3, START + timedelta(days=20), 6),
        Course("Algorithms", 4, START + timedelta(days=10), 8),
        Course("Networks", 2, START + timedelta(days=31), 4),
        Course("ML", 5, START + timedelta(days=13), 9),
    ]


def random_courses(rng, n=None):
    """Random course set; some exams fall inside the 7-day plan window."""
    n = n or rng.randint(2, 7)
    return [
        Course(f"Course{i}", rng.randint(1, 5), START + timedelta(days=rng.randint(0, 40)),
               float(rng.randint(2, 14)))
        for i in range(n)
    ]


def random_availability(rng):
    return {d: float(rng.randint(0, 14)) for d in ALL_DAYS}
