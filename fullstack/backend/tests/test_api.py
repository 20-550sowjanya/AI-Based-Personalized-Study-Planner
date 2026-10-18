"""API tests. Skipped automatically if FastAPI / httpx aren't installed."""
import unittest

import context  # noqa: F401

try:
    from fastapi.testclient import TestClient
    import main
    HAVE_FASTAPI = True
except Exception:  # ImportError, or httpx missing for TestClient
    HAVE_FASTAPI = False

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def payload(**overrides):
    body = {
        "courses": [{"name": "AI", "difficulty": 5, "exam_date": "2026-10-20", "required_hours": 10}],
        "availability": {d: 3 for d in DAYS},
        "preferred_time": "anytime",
        "algorithm": "greedy",
        "start_date": "2026-10-05",
    }
    body.update(overrides)
    return body


@unittest.skipUnless(HAVE_FASTAPI, "fastapi/httpx not installed")
class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)

    def test_health(self):
        r = self.client.get("/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"status": "ok"})

    def test_sample_courses(self):
        r = self.client.get("/sample-courses")
        self.assertEqual(r.status_code, 200)
        self.assertGreaterEqual(len(r.json()), 1)

    def test_schedule_greedy_and_search(self):
        for algo in ("greedy", "search"):
            r = self.client.post("/schedule", json=payload(algorithm=algo))
            self.assertEqual(r.status_code, 200, r.text)
            body = r.json()
            self.assertEqual(len(body["week"]), 7)
            self.assertTrue(body["sessions"])
            self.assertTrue(all("date" in s for s in body["sessions"]))
            self.assertGreater(body["coverage_percent"], 0)

    def test_no_session_after_exam_through_the_api(self):
        body = payload(courses=[{"name": "Early", "difficulty": 5, "exam_date": "2026-10-06", "required_hours": 12}])
        r = self.client.post("/schedule", json=body).json()
        self.assertTrue(all(s["date"] <= "2026-10-06" for s in r["sessions"]))

    def test_duplicate_course_names_rejected(self):
        c = {"name": "AI", "difficulty": 3, "exam_date": "2026-10-20", "required_hours": 4}
        r = self.client.post("/schedule", json=payload(courses=[c, dict(c, name="ai")]))
        self.assertEqual(r.status_code, 422)

    def test_bad_availability_rejected(self):
        bad_key = payload(availability={"Mon": 3})
        negative = payload(availability={**{d: 3 for d in DAYS}, "Monday": -5})
        too_big = payload(availability={**{d: 3 for d in DAYS}, "Monday": 30})
        for body in (bad_key, negative, too_big):
            self.assertEqual(self.client.post("/schedule", json=body).status_code, 422)

    def test_invalid_input_rejected(self):
        self.assertEqual(self.client.post("/schedule", json=payload(courses=[])).status_code, 422)
        bad_date = [{"name": "X", "difficulty": 3, "exam_date": "2026-13-45", "required_hours": 4}]
        self.assertEqual(self.client.post("/schedule", json=payload(courses=bad_date)).status_code, 422)
        bad_diff = [{"name": "X", "difficulty": 9, "exam_date": "2026-10-20", "required_hours": 4}]
        self.assertEqual(self.client.post("/schedule", json=payload(courses=bad_diff)).status_code, 422)
        self.assertEqual(self.client.post("/schedule", json=payload(algorithm="magic")).status_code, 422)


if __name__ == "__main__":
    unittest.main()
