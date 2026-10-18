"""
data_loader.py
Loads course data from a CSV file into Course objects.
"""

import csv
import os
from datetime import datetime
from models import Course

# Folder this file lives in — used so the CSV is found no matter which
# directory the app is launched from.
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def load_courses(csv_path: str = "study_data.csv"):
    if not os.path.isabs(csv_path):
        csv_path = os.path.join(_BASE_DIR, csv_path)
    courses = []
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            courses.append(
                Course(
                    name=row["course_name"],
                    difficulty=int(row["difficulty"]),
                    exam_date=datetime.strptime(row["exam_date"], "%Y-%m-%d").date(),
                    required_hours=float(row["required_hours"]),
                )
            )
    return courses
