import pytest
from backend.app.threshold.threshold_engine import ThresholdEngine

def test_threshold_crossed_in_future():
    engine = ThresholdEngine(critical_minutes=15, warning_minutes=45)
    # CPU steadily rises from 70 to 95 at step 25
    trajectory = {
        "cpu_percent": [
            {"step_minutes": i, "predicted_timestamp": f"2026-01-01T00:{i:02d}:00Z", "predicted_value": 70.0 + i}
            for i in range(1, 35)
        ]
    }
    current_metrics = {"cpu_percent": 70.0}
    threshold_configs = {"cpu_percent": {"value": 90.0, "operator": ">", "enabled": True}}

    preds, earliest, overall = engine.evaluate_trajectories(trajectory, current_metrics, threshold_configs)
    
    assert "cpu_percent" in preds
    pred = preds["cpu_percent"]
    # 70 + 20 = 90 at step 20
    assert pred.time_to_threshold_minutes == 20
    assert pred.status == "approaching_threshold"
    assert pred.risk_level == "WARNING"
    assert earliest["minutes_until_threshold"] == 20
    assert overall == "WARNING"

def test_threshold_not_crossed():
    engine = ThresholdEngine()
    trajectory = {
        "cpu_percent": [
            {"step_minutes": i, "predicted_timestamp": f"2026-01-01T00:{i:02d}:00Z", "predicted_value": 50.0}
            for i in range(1, 61)
        ]
    }
    current_metrics = {"cpu_percent": 50.0}
    threshold_configs = {"cpu_percent": {"value": 90.0, "operator": ">", "enabled": True}}

    preds, earliest, overall = engine.evaluate_trajectories(trajectory, current_metrics, threshold_configs)
    pred = preds["cpu_percent"]
    assert pred.time_to_threshold_minutes is None
    assert pred.status == "not_reached_within_horizon"
    assert pred.risk_level == "NORMAL"
    assert earliest is None
    assert overall == "NORMAL"

def test_threshold_crossed_immediately():
    engine = ThresholdEngine()
    trajectory = {
        "cpu_percent": [
            {"step_minutes": i, "predicted_timestamp": f"2026-01-01T00:{i:02d}:00Z", "predicted_value": 92.0}
            for i in range(1, 10)
        ]
    }
    current_metrics = {"cpu_percent": 92.0}
    threshold_configs = {"cpu_percent": {"value": 90.0, "operator": ">", "enabled": True}}

    preds, earliest, overall = engine.evaluate_trajectories(trajectory, current_metrics, threshold_configs)
    pred = preds["cpu_percent"]
    assert pred.time_to_threshold_minutes == 0
    assert pred.status == "currently_exceeded"
    assert pred.risk_level == "CRITICAL"
    assert overall == "CRITICAL"

def test_less_than_threshold():
    engine = ThresholdEngine()
    # Free memory drops below 15%
    trajectory = {
        "free_mem": [
            {"step_minutes": i, "predicted_timestamp": f"2026-01-01T00:{i:02d}:00Z", "predicted_value": 25.0 - i}
            for i in range(1, 20)
        ]
    }
    current_metrics = {"free_mem": 25.0}
    threshold_configs = {"free_mem": {"value": 15.0, "operator": "<", "enabled": True}}

    preds, earliest, overall = engine.evaluate_trajectories(trajectory, current_metrics, threshold_configs)
    pred = preds["free_mem"]
    # 25 - 10 = 15 <= 15 at step 10
    assert pred.time_to_threshold_minutes == 10
    assert pred.risk_level == "CRITICAL"
