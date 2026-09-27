import pytest
import numpy as np
import pandas as pd
from backend.app.features.feature_pipeline import FeaturePipeline
from backend.app.features.lag_features import add_lag_features, add_delta_features
from backend.app.features.rolling_features import add_rolling_features

def test_feature_pipeline_no_data_leakage():
    """
    CRITICAL DATA LEAKAGE TEST:
    Generate feature matrix on dataset A.
    Then modify future rows (t > T) in dataset B.
    Ensure features at time T are IDENTICAL in both datasets!
    """
    np.random.seed(42)
    n_rows = 150
    timestamps = pd.date_range("2026-01-01 00:00:00", periods=n_rows, freq="1min", tz="UTC")
    
    # Dataset A
    data_a = {
        "timestamp": timestamps,
        "cpu_percent": np.random.uniform(30, 60, size=n_rows),
        "memory_percent": np.random.uniform(40, 70, size=n_rows),
        "disk_io_mb_s": np.random.uniform(10, 50, size=n_rows),
        "latency_ms": np.random.uniform(100, 300, size=n_rows),
        "http_errors": np.random.poisson(3, size=n_rows),
        "http_success": np.random.uniform(1000, 2000, size=n_rows),
        "network_mb_s": np.random.uniform(10, 40, size=n_rows),
        "request_volume": np.random.uniform(1000, 2000, size=n_rows),
    }
    df_a = pd.DataFrame(data_a)

    # Dataset B is identical up to row 100, but future rows (101..150) are drastically mutated (e.g. 10x spike)
    df_b = df_a.copy(deep=True)
    split_index = 100
    df_b.loc[split_index + 1:, "cpu_percent"] = 99.9
    df_b.loc[split_index + 1:, "latency_ms"] = 9999.0
    df_b.loc[split_index + 1:, "http_errors"] = 500

    # Run feature pipeline on both datasets
    pipeline = FeaturePipeline()
    feat_a, cols_a = pipeline.fit_transform(df_a)
    feat_b, cols_b = pipeline.fit_transform(df_b)

    # Compare features at split_index - 60 (offset due to warmup drop)
    offset_index = split_index - 60
    row_a = feat_a.iloc[offset_index][cols_a]
    row_b = feat_b.iloc[offset_index][cols_b]

    # Every single engineered feature at time t must be exactly identical
    pd.testing.assert_series_equal(row_a, row_b, check_exact=True)
    print("Data leakage test passed: Features at time t are completely unaffected by future data.")

def test_labels_excluded_from_features():
    """Verify app_status and failure_event are never included as features."""
    n_rows = 100
    timestamps = pd.date_range("2026-01-01 00:00:00", periods=n_rows, freq="1min", tz="UTC")
    df = pd.DataFrame({
        "timestamp": timestamps,
        "app_status": ["healthy"] * n_rows,
        "failure_event": [0] * n_rows,
        "cpu_percent": [50.0] * n_rows,
        "memory_percent": [50.0] * n_rows,
        "disk_io_mb_s": [30.0] * n_rows,
        "latency_ms": [100.0] * n_rows,
        "http_errors": [0] * n_rows,
        "http_success": [1000] * n_rows,
        "network_mb_s": [10.0] * n_rows,
        "request_volume": [1000] * n_rows,
    })
    pipeline = FeaturePipeline()
    feat_df, cols = pipeline.fit_transform(df)

    assert "app_status" not in cols
    assert "failure_event" not in cols
    assert not any("app_status" in c for c in cols)
    assert not any("failure_event" in c for c in cols)
