from fastapi.testclient import TestClient

from app.main import app


def test_health_honestly_reports_no_dataset() -> None:
    response = TestClient(app).get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["database_status"] == "ok"
    assert response.json()["active_dataset_status"] == "ACTIVE"
