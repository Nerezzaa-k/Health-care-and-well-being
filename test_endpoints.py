"""
Nirantar Phase 6 API Integration Test
Tests all endpoints against a live local server instance.
"""
import urllib.request
import urllib.parse
import json
import time
import subprocess
import sys

BASE_URL = "http://127.0.0.1:8000"

def get(path):
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))

def post(path, data):
    url = f"{BASE_URL}{path}"
    payload = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST", headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))

def test_api():
    print("Testing Nirantar Phase 6 Endpoints...")

    # 1. GET /api/clock
    s, data = get("/api/clock")
    assert s == 200 and "current_date" in data
    print("✓ GET /api/clock:", data["current_date"])

    # 2. GET /api/scorecard
    s, data = get("/api/scorecard")
    assert s == 200
    assert "active_patients" in data
    assert "patients_at_risk" in data
    assert "completion_rate" in data
    assert "median_days_to_resolve" in data
    assert "open_and_escalated_cases" in data
    assert "cases_past_due" in data
    assert "cases_per_worker" in data
    assert "coordinator_hours_saved" in data
    print("✓ GET /api/scorecard: completion_rate =", data["completion_rate_percent"], "%, median_days =", data["median_days_to_resolve"])

    # 3. GET /api/medicine-availability
    s, data = get("/api/medicine-availability")
    assert s == 200
    assert "facilities" in data
    assert "critical_refill_alerts" in data
    print("✓ GET /api/medicine-availability:", len(data["facilities"]), "facilities,", len(data["critical_refill_alerts"]), "critical alerts")

    # 4. GET /api/gaps
    s, data = get("/api/gaps")
    assert s == 200
    assert "villages" in data
    top_vil = data["villages"][0]
    assert "gap_score" in top_vil
    assert "factors" in top_vil
    print("✓ GET /api/gaps: top gap village =", top_vil["village_name"], "score =", top_vil["gap_score"])

    # 5. POST /api/cases
    s, data = post("/api/cases", {
        "patient_id": "P-001",
        "owner_id": "W-101",
        "due_date": "2026-10-25",
        "reason": "feels_fine",
        "action": "counselling",
        "notes": "Testing case assignment"
    })
    assert s == 201
    new_case_id = data["case_id"]
    print("✓ POST /api/cases: created", new_case_id)

    # 6. POST /api/cases/{id}/status
    s, data = post(f"/api/cases/{new_case_id}/status", {
        "status": "resolved"
    })
    assert s == 200
    print(f"✓ POST /api/cases/{new_case_id}/status: updated to resolved")

    # 7. POST /api/escalation/run
    s, data = post("/api/escalation/run", {})
    assert s == 200
    assert "escalated_count" in data
    print("✓ POST /api/escalation/run:", data["escalated_count"], "escalated")

    # 8. POST /api/clock (advance day)
    s, data = post("/api/clock", {"action": "advance_day", "days": 1})
    assert s == 200
    print("✓ POST /api/clock:", data["previous_date"], "->", data["current_date"])

    print("\nALL HTTP ENDPOINT INTEGRATION TESTS PASSED!\n")

if __name__ == "__main__":
    test_api()
