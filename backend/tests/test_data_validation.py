import pytest
import pandas as pd
from backend.app.data.validator import DataValidator

def test_validator_detects_missing_columns():
    bad_df = pd.DataFrame({
        "timestamp": ["2026-01-01 00:00:00+00:00"],
        "cpu_percent": [50.0]
    })
    is_valid, errors = DataValidator.validate_schema(bad_df)
    assert not is_valid
    assert len(errors) > 0
    assert "Missing required column(s)" in errors[0]

def test_validator_accepts_valid_schema():
    timestamps = pd.date_range("2026-01-01 00:00:00", periods=65, freq="1min", tz="UTC").strftime("%Y-%m-%d %H:%M:%S%z").tolist()
    valid_data = {
        "timestamp": timestamps,
        "cpu_percent": [45.0] * 65,
        "memory_percent": [55.0] * 65,
        "disk_io_mb_s": [30.0] * 65,
        "latency_ms": [150.0] * 65,
        "http_errors": [2] * 65,
        "http_success": [2000] * 65,
        "network_mb_s": [20.0] * 65,
        "request_volume": [2002] * 65,
    }
    df = pd.DataFrame(valid_data)
    result = DataValidator.validate_dataset(df)
    assert result.is_valid
    assert len(result.errors) == 0
    assert result.quality_report["total_rows"] == 65
