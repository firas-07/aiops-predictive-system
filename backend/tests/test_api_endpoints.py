import pytest
from starlette.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert data["models_ready"] is True

def test_get_models():
    response = client.get("/api/v1/models")
    assert response.status_code == 200
    data = response.json()
    assert data["active_version"] is not None
    assert "1.0.0" in data["versions"]

def test_get_threshold_config():
    response = client.get("/api/v1/threshold/config")
    assert response.status_code == 200
    data = response.json()
    assert "thresholds" in data
    assert "cpu_percent" in data["thresholds"]

def test_predict_endpoint_success():
    payload = {
        "app_id": "chatgpt-azure-prod",
        "latest_metrics": {
            "cpu_percent": 75.0,
            "memory_percent": 70.0,
            "disk_io_mb_s": 45.0,
            "latency_ms": 300.0,
            "http_errors": 12.0,
            "http_success": 2400.0,
            "network_mb_s": 35.0,
            "request_volume": 2500.0
        },
        "thresholds": {
            "cpu_percent": 88.0,
            "memory_percent": 85.0
        },
        "forecast_horizon_minutes": 30
    }
    response = client.post("/api/v1/predict", json=payload)
    assert response.status_code == 200
    res = response.json()
    assert res["app_id"] == "chatgpt-azure-prod"
    assert res["forecast_horizon_minutes"] == 30
    assert "cpu_percent" in res["metric_forecasts"]
    assert len(res["metric_forecasts"]["cpu_percent"]) == 30
    assert "threshold_predictions" in res
    assert "overall_system_status" in res
