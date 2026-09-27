from typing import Optional, Literal
from pydantic import BaseModel, Field

class ThresholdItem(BaseModel):
    enabled: bool = True
    operator: Literal[">", "<", ">=", "<="] = ">"
    value: float
    unit: Optional[str] = ""
    critical_threshold: Optional[float] = None

class ThresholdPrediction(BaseModel):
    metric: str
    current_value: float
    threshold_value: float
    operator: str
    time_to_threshold_minutes: Optional[int] = None
    predicted_crossing_time: Optional[str] = None
    status: str  # NORMAL, WARNING, CRITICAL, not_reached_within_horizon
    risk_level: str  # NORMAL, WARNING, CRITICAL
    message: str

class ThresholdAnalysisRequest(BaseModel):
    app_id: str = "chatgpt-azure-prod"
    forecast_horizon_minutes: int = 60
    metric_forecasts: dict[str, list[float]]
    current_metrics: dict[str, float]
    thresholds: Optional[dict[str, float]] = None
    start_timestamp: Optional[str] = None

class ThresholdAnalysisResponse(BaseModel):
    app_id: str
    generated_at: str
    threshold_predictions: dict[str, ThresholdPrediction]
    earliest_threshold: Optional[dict] = None
    overall_status: str
