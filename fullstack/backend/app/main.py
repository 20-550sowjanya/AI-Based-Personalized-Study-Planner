"""
main.py
FastAPI backend for the AI Study Planner: a thin, validated REST layer over the
scheduling engine (models, priority, constraints, scheduler, search, explanation).

Run with:  uvicorn main:app --reload --port 8000     (from the backend/app folder)
"""

import os
from datetime import date
from typing import List, Literal, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, field_validator

from data_loader import load_courses
from explanation import explain
from models import Course
import scheduler as greedy_module
import search as search_module

app = FastAPI(title="AI Study Planner API", version="1.1.0")

# Development default allows any origin. For a real deployment set
# STUDY_PLANNER_ORIGINS to a comma-separated list, e.g.
#   STUDY_PLANNER_ORIGINS="https://my-frontend.example.com"
_origins = os.environ.get("STUDY_PLANNER_ORIGINS", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins.split(",")],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------

class CourseIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    difficulty: int = Field(ge=1, le=5)
    exam_date: date                      # ISO "YYYY-MM-DD"; invalid dates -> 422
    required_hours: float = Field(gt=0, le=200)

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Course name cannot be blank.")
        return v


class Availability(BaseModel):
    """Hours available per weekday. Unknown keys (e.g. "Mon") are rejected."""
    model_config = ConfigDict(extra="forbid")

    Monday: float = Field(ge=0, le=24)
    Tuesday: float = Field(ge=0, le=24)
    Wednesday: float = Field(ge=0, le=24)
    Thursday: float = Field(ge=0, le=24)
    Friday: float = Field(ge=0, le=24)
    Saturday: float = Field(ge=0, le=24)
    Sunday: float = Field(ge=0, le=24)


class ScheduleRequest(BaseModel):
    courses: List[CourseIn] = Field(min_length=1, max_length=30)
    availability: Availability
    preferred_time: Literal["anytime", "morning", "afternoon", "evening"] = "anytime"
    algorithm: Literal["greedy", "search"] = "greedy"
    start_date: Optional[date] = None    # first day of the 7-day plan; default today
    iterations: int = Field(default=800, ge=50, le=5000)
    seed: Optional[int] = None

    @field_validator("courses")
    @classmethod
    def names_unique(cls, courses: List[CourseIn]) -> List[CourseIn]:
        seen = set()
        for c in courses:
            key = c.name.lower()
            if key in seen:
                raise ValueError(f"Course names must be unique (duplicate: {c.name!r}).")
            seen.add(key)
        return courses


class CourseOut(BaseModel):
    name: str
    priority: float
    required_hours: float
    scheduled_hours: float
    explanation: str


class SessionOut(BaseModel):
    course: str
    day: str
    date: str
    start_hour: float
    duration: float


class WeekDay(BaseModel):
    day: str
    date: str


class ScheduleResponse(BaseModel):
    algorithm: str
    start_date: str
    coverage_percent: float
    week: List[WeekDay]
    warnings: List[str]
    courses: List[CourseOut]
    sessions: List[SessionOut]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/sample-courses", response_model=List[CourseIn])
def sample_courses():
    """The bundled sample dataset (study_data.csv), so the UI can offer example data."""
    return [
        CourseIn(name=c.name, difficulty=c.difficulty, exam_date=c.exam_date,
                 required_hours=c.required_hours)
        for c in load_courses()
    ]


@app.post("/schedule", response_model=ScheduleResponse)
def generate_schedule(req: ScheduleRequest):
    start = req.start_date or date.today()
    availability = req.availability.model_dump()
    courses = [
        Course(name=c.name, difficulty=c.difficulty, exam_date=c.exam_date,
               required_hours=c.required_hours)
        for c in req.courses
    ]

    if req.algorithm == "greedy":
        result = greedy_module.generate_schedule_api(
            courses, availability, req.preferred_time, start_date=start)
    else:
        result = search_module.generate_schedule_api(
            courses, availability, req.preferred_time,
            iterations=req.iterations, seed=req.seed, start_date=start)

    # Both schedulers set .priority / .scheduled_hours on `courses` as a side effect.
    explanations = {c.name: explain(c, start) for c in courses}

    total_required = sum(c["required_hours"] for c in result["courses"])
    total_scheduled = sum(c["scheduled_hours"] for c in result["courses"])
    coverage = round(100 * total_scheduled / total_required, 1) if total_required else 0.0

    return ScheduleResponse(
        algorithm=req.algorithm,
        start_date=start.isoformat(),
        coverage_percent=coverage,
        week=[WeekDay(**w) for w in result["week"]],
        warnings=result["warnings"],
        courses=[CourseOut(**c, explanation=explanations.get(c["name"], ""))
                 for c in result["courses"]],
        sessions=[SessionOut(**s) for s in result["sessions"]],
    )
