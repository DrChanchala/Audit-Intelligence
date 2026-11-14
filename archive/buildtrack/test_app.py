import pytest
from fastapi.testclient import TestClient
from app import app
from database import init_db
from seed_data import seed_all_data
from progress_engine import compute_project_metrics, calculate_activity_progress
from ai_agent import ProjectAIAgent

@pytest.fixture(scope="module", autouse=True)
def setup_test_database():
    seed_all_data()

client = TestClient(app)

def test_weighted_progress_calculation():
    acc_pct, rep_pct = calculate_activity_progress(150.0, 115.0, 120.0)
    assert acc_pct == 76.67
    assert rep_pct == 80.0

def test_project_metrics_summary():
    metrics = compute_project_metrics()
    assert "planned_progress" in metrics
    assert "ai_automated_progress" in metrics
    assert "field_observed_progress" in metrics
    assert "pm_approved_progress" in metrics
    assert len(metrics["stages"]) == 10
    tower_ids = [t['tower_id'] for t in metrics["towers"]]
    assert "TOW-A" in tower_ids
    assert "TOW-B" in tower_ids
    total_stage_weight = sum(s["weightage"] for s in metrics["stages"])
    assert abs(total_stage_weight - 100.0) < 0.001

def test_api_dashboard_endpoint():
    response = client.get("/api/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert "metrics" in data
    assert "kpis" in data
    assert "planned_progress" in data["kpis"]
    assert "ai_automated_progress" in data["kpis"]
    assert "pm_approved_progress" in data["kpis"]

def test_mode_a_camera_analysis():
    response = client.get("/api/cameras/CAM-T01-12/analyze")
    assert response.status_code == 200
    data = response.json()
    assert data["source_type"] == "STATIC_CAMERA"
    assert "ai_progress_percent" in data
    assert data["requires_human_intervention"] is False

def test_mode_b_pm_review_workflow():
    # 1. Check pending reviews
    res = client.get("/api/pm/reviews?status=PENDING")
    assert res.status_code == 200
    reviews = res.json()
    assert len(reviews) >= 1
    rev_id = reviews[0]["id"]

    # 2. PM approves review
    appr_res = client.post(f"/api/pm/reviews/{rev_id}/approve", json={
        "reviewer_name": "Er. Robert Vance (PM)",
        "remarks": "Approved with full verification"
    })
    assert appr_res.status_code == 200
    appr_data = appr_res.json()
    assert appr_data["pm_status"] == "APPROVED"

def test_discrepancy_detection():
    res = client.get("/api/discrepancies")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)

def test_excel_export():
    res = client.get("/api/reports/download?report_type=progress")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
