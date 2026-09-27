from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

class MetricEvaluation(BaseModel):
    metric: str
    baseline_mae: float
    baseline_rmse: float
    lightgbm_mae: float
    lightgbm_rmse: float
    lightgbm_mape: Optional[float] = None
    improvement_vs_baseline_pct: float
    threshold_crossing_accuracy: Optional[float] = None
    mean_time_to_threshold_error_min: Optional[float] = None
    false_early_warning_rate: Optional[float] = None
    missed_threshold_rate: Optional[float] = None

class TrainRequest(BaseModel):
    data_path: Optional[str] = None
    forecast_horizon_minutes: int = 60
    retrain_models: bool = True
    train_failure_model: bool = True
    fast_mode: bool = False  # If true, train on representative subset for rapid iteration

class TrainResponse(BaseModel):
    status: str
    message: str
    model_version: str
    trained_at: str
    training_rows: int
    validation_rows: int
    test_rows: int
    target_metrics: List[str]
    evaluations: Dict[str, MetricEvaluation]
    failure_model_evaluation: Optional[Dict[str, Any]] = None
