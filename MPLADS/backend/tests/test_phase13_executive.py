"""Executive endpoints aggregate persisted evidence and retain server-side scope."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
ADMIN = {"X-MPLADS-Role": "PLATFORM_ADMINISTRATOR"}


def test_executive_summary_and_attention_use_live_counts_and_precedence():
    assert client.get("/api/v1/executive/summary").status_code == 401
    summary = client.get("/api/v1/executive/summary", headers=ADMIN)
    assert summary.status_code == 200
    data = summary.json()
    attention = client.get("/api/v1/executive/attention", headers=ADMIN)
    assert attention.status_code == 200
    item = attention.json()
    open_cases = sum(data["review_backlog"].get(status, 0) for status in ("OPEN", "ASSIGNED", "UNDER_REVIEW", "REOPENED"))
    expected = open_cases + data["review_backlog"].get("FOLLOW_UP_REQUIRED", 0) + data["active_escalations"] + data["high_priority_alerts"] + data["high_priority_risk_works"]
    assert item["signal_count"] == expected
    expected_level = "HIGH" if expected >= 10 or data["active_escalations"] >= 2 or (open_cases >= 5 and data["high_priority_alerts"] >= 5) else "MODERATE" if 3 <= expected <= 9 or data["active_escalations"] == 1 or open_cases >= 2 else "LOWER"
    assert item["level"] == expected_level
    assert item["provenance"]["dataset_version"] == data["provenance"]["dataset_version"]


def test_executive_scope_geography_comparison_trends_and_priority_queue_are_database_backed():
    national = client.get("/api/v1/executive/summary", headers=ADMIN).json()
    state = client.get("/api/v1/executive/summary", headers={"X-MPLADS-Role": "STATE_NODAL_AUTHORITY", "X-MPLADS-State-Scope": "Not an authorized state"})
    assert state.status_code == 200 and state.json()["total_monitored_works"] == 0
    geography = client.get("/api/v1/executive/geography", headers=ADMIN)
    comparison = client.get("/api/v1/executive/comparison", headers=ADMIN)
    trends = client.get("/api/v1/executive/trends", headers=ADMIN)
    drilldown = client.get("/api/v1/executive/drilldown", headers=ADMIN)
    assert geography.status_code == comparison.status_code == trends.status_code == drilldown.status_code == 200
    assert sum(row["monitored_works"] for row in comparison.json()["rows"]) == national["total_monitored_works"]
    assert all("high_priority_risk_rate" in row for row in geography.json()["rows"])
    assert isinstance(trends.json()["available"], bool)
    queue = drilldown.json()["priority_queue"]
    assert len(queue) <= 25 and all("reason" in row and "alert_id" in row for row in queue)
