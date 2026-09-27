import pytest
from starlette.testclient import TestClient
from backend.app.main import app
from backend.app.schemas.application import MetricThresholdConfig
from backend.app.threshold.normalizer import ThresholdNormalizer
from backend.app.threshold.alert_engine import AlertEngine
from backend.app.data.telemetry_provider import CsvTelemetryProvider, AzureTelemetryProvider
from backend.app.core.config import settings

client = TestClient(app)

# ----------------- 1. Threshold Normalization Tests -----------------
def test_threshold_percentage_to_effective_conversion():
    # Percentage metric: CPU 80% with operational limit 100% -> 80.0%
    cpu_conf = MetricThresholdConfig(
        metric="cpu_percent",
        threshold_percentage=80.0,
        operational_limit=100.0,
        operator=">=",
        unit="%"
    )
    assert ThresholdNormalizer.normalize(cpu_conf) == 80.0
    assert cpu_conf.effective_threshold == 80.0

    # Non-percentage metric: Latency 80% with operational limit 500 ms -> 400.0 ms
    lat_conf = MetricThresholdConfig(
        metric="latency_ms",
        threshold_percentage=80.0,
        operational_limit=500.0,
        operator=">=",
        unit="ms"
    )
    assert ThresholdNormalizer.normalize(lat_conf) == 400.0
    assert lat_conf.effective_threshold == 400.0

    # Non-percentage metric: HTTP Success 30% with operational limit 3500 req/min -> 1050.0 req/min
    succ_conf = MetricThresholdConfig(
        metric="http_success",
        threshold_percentage=30.0,
        operational_limit=3500.0,
        operator="<=",
        unit="req/min"
    )
    assert ThresholdNormalizer.normalize(succ_conf) == 1050.0

def test_invalid_operational_limit_rejected():
    with pytest.raises(ValueError, match="greater than 0"):
        MetricThresholdConfig(
            metric="latency_ms",
            threshold_percentage=80.0,
            operational_limit=0.0,
            operator=">="
        )

# ----------------- 2. Alert Engine & Threshold Evaluation Tests -----------------
def test_alert_engine_current_breach():
    engine = AlertEngine()
    trajectory = [{"step_minutes": i, "predicted_timestamp": f"2026-01-01T00:{i:02d}:00Z", "predicted_value": 85.0} for i in range(1, 31)]
    
    # Current value = 85.0 >= effective threshold 80.0
    res = engine.evaluate_metric(
        metric="cpu_percent",
        current_val=85.0,
        trajectory=trajectory,
        threshold_percentage=80.0,
        operational_limit=100.0,
        effective_threshold=80.0,
        operator=">=",
        unit="%"
    )
    assert res.status == "CURRENT_BREACH"
    assert res.predicted_crossing_minutes == 0
    assert res.severity == "CRITICAL"

def test_alert_engine_predicted_breach_and_earliest_selector():
    engine = AlertEngine(critical_lead_minutes=15, warning_lead_minutes=30)
    
    # CPU: starts at 70%, rises to 82% at step 20
    cpu_traj = [{"step_minutes": i, "predicted_timestamp": f"2026-01-01T00:{i:02d}:00Z", "predicted_value": 70.0 + (i * 0.6)} for i in range(1, 31)]
    # Latency: starts at 300ms, crosses 400ms at step 10
    lat_traj = [{"step_minutes": i, "predicted_timestamp": f"2026-01-01T00:{i:02d}:00Z", "predicted_value": 300.0 + (i * 12.0)} for i in range(1, 31)]

    trajectories = {"cpu_percent": cpu_traj, "latency_ms": lat_traj}
    current_metrics = {"cpu_percent": 70.0, "latency_ms": 300.0}
    normalized_thresholds = {
        "cpu_percent": {"threshold_percentage": 80.0, "operational_limit": 100.0, "effective_threshold": 80.0, "operator": ">=", "unit": "%"},
        "latency_ms": {"threshold_percentage": 80.0, "operational_limit": 500.0, "effective_threshold": 400.0, "operator": ">=", "unit": "ms"},
    }

    metric_results, earliest, overall, summary, count = engine.evaluate_all(current_metrics, trajectories, normalized_thresholds)
    
    assert count == 2
    assert earliest is not None
    # Latency breaches earlier (step ~9-10) than CPU (step ~17-20)
    assert earliest.metric == "latency_ms"
    assert earliest.predicted_crossing_minutes <= 15
    assert earliest.severity == "CRITICAL"
    assert overall in ["CRITICAL", "AT_RISK"]

def test_alert_engine_less_than_operator():
    engine = AlertEngine()
    # HTTP Success drops below threshold 1050 at step 5
    succ_traj = [{"step_minutes": i, "predicted_timestamp": f"2026-01-01T00:{i:02d}:00Z", "predicted_value": 1200.0 - (i * 40.0)} for i in range(1, 31)]
    
    res = engine.evaluate_metric(
        metric="http_success",
        current_val=1200.0,
        trajectory=succ_traj,
        threshold_percentage=30.0,
        operational_limit=3500.0,
        effective_threshold=1050.0,
        operator="<=",
        unit="req/min"
    )
    assert res.status == "PREDICTED_BREACH"
    # 1200 - (4 * 40) = 1040 <= 1050 at step 4
    assert res.predicted_crossing_minutes == 4
    assert res.severity == "CRITICAL"

# ----------------- 3. Telemetry Provider Tests -----------------
def test_csv_provider_loads_and_windows():
    provider = CsvTelemetryProvider(settings.raw_data_path)
    window = provider.get_recent_window(app_id="chatgpt-azure-prod", minutes=75)
    assert len(window) == 75
    assert "cpu_percent" in window.columns
    assert "latency_ms" in window.columns

def test_azure_provider_stream_and_normalization():
    az_provider = AzureTelemetryProvider(azure_config={
        "tenant_id": "test-tenant",
        "client_id": "test-client",
        "client_secret": "test-secret",
        "resource_name": "azure-prod-web"
    })
    window = az_provider.get_recent_window(app_id="azure-prod-app", minutes=65)
    assert len(window) == 65
    for col in ["cpu_percent", "memory_percent", "disk_io_mb_s", "latency_ms", "http_errors", "http_success", "network_mb_s", "request_volume"]:
        assert col in window.columns
        assert (window[col] >= 0).all()

# ----------------- 4. Security & API Workflow Tests -----------------
def test_azure_secrets_never_exposed_in_api():
    payload = {
        "id": "secure-azure-app",
        "name": "Secure Production App",
        "telemetry_source": "azure",
        "azure_config": {
            "tenant_id": "tenant-12345",
            "client_id": "client-67890",
            "client_secret": "SuperSecretPassword123!",
            "subscription_id": "sub-111",
            "resource_group": "rg-prod",
            "resource_name": "aiops-prod-insights",
            "telemetry_service": "azure_monitor"
        }
    }
    # Clean up if already exists from prior test runs
    client.delete("/api/applications/secure-azure-app")

    # Create application
    create_resp = client.post("/api/applications", json=payload)
    assert create_resp.status_code == 201
    data = create_resp.json()
    assert data["azure_config"]["client_secret"] == "••••••••"
    assert "SuperSecretPassword123!" not in str(data)

    # Get application
    get_resp = client.get("/api/applications/secure-azure-app")
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert get_data["azure_config"]["client_secret"] == "••••••••"
    assert "SuperSecretPassword123!" not in str(get_data)

    # List applications
    list_resp = client.get("/api/applications")
    assert list_resp.status_code == 200
    assert "SuperSecretPassword123!" not in list_resp.text

def test_realtime_prediction_endpoint():
    # Call real-time prediction for default app with Sample Dataset
    pred_resp = client.post("/api/applications/chatgpt-azure-prod/predict", json={"horizon_minutes": 30})
    assert pred_resp.status_code == 200
    res = pred_resp.json()
    
    assert res["application"]["id"] == "chatgpt-azure-prod"
    assert res["horizon_minutes"] == 30
    assert res["overall_status"] in ["NORMAL", "WARNING", "AT_RISK", "CRITICAL"]
    assert len(res["metrics"]) == 8

    # Verify every metric has 30 forecast points
    for m in res["metrics"]:
        assert len(m["forecast"]) == 30
        assert m["status"] in ["CURRENT_BREACH", "PREDICTED_BREACH", "NO_BREACH"]
        assert m["severity"] in ["NORMAL", "WARNING", "CRITICAL"]
        assert m["effective_threshold"] > 0
