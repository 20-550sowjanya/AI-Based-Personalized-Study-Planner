"""
explanation.py
Rule-based, plain-English justification for each course's priority. Every
reason is derived from the course's actual data (difficulty, days until the
exam, required hours), not inferred from the combined priority score.
"""

from datetime import date


def _days_phrase(days_left: int) -> str:
    if days_left == 0:
        return "exam today"
    if days_left == 1:
        return "exam tomorrow"
    return f"exam in {days_left} days"


def explain(course, today: date = None) -> str:
    today = today or date.today()
    days_left = (course.exam_date - today).days

    if days_left < 0:
        return f"{course.name}: the exam date has already passed, so no study time was scheduled."

    reasons = []
    if course.difficulty >= 4:
        reasons.append(f"high difficulty ({course.difficulty}/5)")
    if days_left <= 14:
        reasons.append(_days_phrase(days_left))
    if course.required_hours >= 8:
        reasons.append(f"a large workload ({course.required_hours:g} hours)")

    if not reasons:
        return (f"{course.name} has a lower priority: manageable difficulty, "
                f"{_days_phrase(days_left)}, and a modest workload (score {course.priority}).")

    return f"{course.name} was prioritized for: {', '.join(reasons)} (score {course.priority})."
