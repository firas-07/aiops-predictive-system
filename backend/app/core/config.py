import os
from pathlib import Path
from typing import Dict, List, Optional, Any
import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

class ThresholdSetting(BaseModel):
    enabled: bool = True
    operator: str = ">"
    value: float
    unit: str = ""
    critical_threshold: Optional[float] = None

class AppSettings(BaseSettings):
    app_name: str = "AIOPS Predictive System"
    app_version: str = "1.0.0"
    environment: str = "production"
    debug: bool = False
    
    # Paths
    base_dir: Path = Path(__file__).resolve().parent.parent.parent.parent
    config_path: Path = base_dir / "config.yaml"
    raw_data_path: Path = base_dir / "data" / "raw" / "chatgpt_azure_synthetic_telemetry_50000.csv"
    processed_data_path: Path = base_dir / "data" / "processed" / "telemetry_clean.parquet"
    features_data_path: Path = base_dir / "data" / "features" / "features_matrix.parquet"
    models_dir: Path = base_dir / "models"
    
    # Telemetry configuration
    target_metrics: List[str] = [
        "cpu_percent",
        "memory_percent",
        "disk_io_mb_s",
        "latency_ms",
        "http_errors",
        "http_success",
        "network_mb_s",
        "request_volume"
    ]
    label_columns: List[str] = ["app_status", "failure_event"]
    timestamp_column: str = "timestamp"
    expected_interval_minutes: int = 1
    missing_strategy: str = "interpolate"
    outlier_method: str = "iqr"
    
    # Feature engineering
    lags: List[int] = [1, 5, 10, 15, 30, 60]
    rolling_windows: List[int] = [5, 15, 30, 60]
    deltas: List[int] = [1, 5, 15]
    cyclical_time: bool = True
    
    # Forecasting
    default_horizon_minutes: int = 60
    max_horizon_minutes: int = 120
    model_type: str = "recursive"
    train_split: float = 0.70
    val_split: float = 0.15
    test_split: float = 0.15
    random_seed: int = 42
    
    # LightGBM params
    lightgbm_params: Dict[str, Any] = {
        "n_estimators": 150,
        "learning_rate": 0.05,
        "num_leaves": 31,
        "max_depth": -1,
        "min_child_samples": 20,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "random_state": 42,
        "n_jobs": -1
    }
    
    # Thresholds
    thresholds: Dict[str, ThresholdSetting] = {
        "cpu_percent": ThresholdSetting(enabled=True, operator=">", value=90.0, unit="%", critical_threshold=95.0),
        "memory_percent": ThresholdSetting(enabled=True, operator=">", value=85.0, unit="%", critical_threshold=90.0),
        "disk_io_mb_s": ThresholdSetting(enabled=True, operator=">", value=80.0, unit="MB/s", critical_threshold=100.0),
        "latency_ms": ThresholdSetting(enabled=True, operator=">", value=500.0, unit="ms", critical_threshold=800.0),
        "http_errors": ThresholdSetting(enabled=True, operator=">", value=50.0, unit="count/min", critical_threshold=100.0),
        "network_mb_s": ThresholdSetting(enabled=True, operator=">", value=70.0, unit="MB/s", critical_threshold=90.0),
        "request_volume": ThresholdSetting(enabled=True, operator=">", value=4000.0, unit="req/min", critical_threshold=5000.0)
    }
    
    # Risk rules
    critical_minutes: int = 15
    warning_minutes: int = 45

    def load_from_yaml(self):
        if self.config_path.exists():
            with open(self.config_path, "r") as f:
                data = yaml.safe_load(f) or {}
                if "forecasting" in data:
                    self.default_horizon_minutes = data["forecasting"].get("default_horizon_minutes", self.default_horizon_minutes)
                    self.max_horizon_minutes = data["forecasting"].get("max_horizon_minutes", self.max_horizon_minutes)
                    self.train_split = data["forecasting"].get("train_split", self.train_split)
                    self.val_split = data["forecasting"].get("val_split", self.val_split)
                    self.test_split = data["forecasting"].get("test_split", self.test_split)
                    self.random_seed = data["forecasting"].get("random_seed", self.random_seed)
                if "features" in data:
                    self.lags = data["features"].get("lags", self.lags)
                    self.rolling_windows = data["features"].get("rolling_windows", self.rolling_windows)
                    self.deltas = data["features"].get("deltas", self.deltas)
                if "lightgbm_params" in data:
                    self.lightgbm_params.update(data["lightgbm_params"])
                if "risk_rules" in data:
                    self.critical_minutes = data["risk_rules"].get("critical_minutes", self.critical_minutes)
                    self.warning_minutes = data["risk_rules"].get("warning_minutes", self.warning_minutes)
                if "thresholds" in data:
                    for k, v in data["thresholds"].items():
                        self.thresholds[k] = ThresholdSetting(**v)

settings = AppSettings()
try:
    settings.load_from_yaml()
except Exception:
    pass
