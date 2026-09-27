from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from backend.app.schemas.threshold import ThresholdPrediction

class LatestMetrics(BaseModel):
    cpu_percent: float = Field(..., description="CPU utilization in % (0-100)")
    memory_percent: float = Field(..., description="Memory utilization in % (0-100)")
    disk_io_mb_s: float = Field(..., description="Disk I/O rate in MB/s")
    latency_ms: float = Field(..., description="Average request latency in ms")
    http_errors: float = Field(..., description="HTTP 5xx/4xx error count in the last minute")
    http_success: float = Field(..., description="HTTP 2xx success count in the last minute")
    network_mb_s: float = Field(..., description="Network throughput in MB/s")
    request_volume: float = Field(..., description="Total incoming requests count in the last minute")

class PredictRequest(BaseModel):
    app_id: str = "chatgpt-azure-prod"
    latest_metrics: Optional[LatestMetrics] = None
    # User can supply historical window (list of dicts) if available, or backend can pull from recent telemetry
    historical_window: Optional[List[Dict[str, Any]]] = None
    # User-configured threshold overrides: {"cpu_percent": 90.0, "latency_ms": 500.0, ...}
    thresholds: Optional[Dict[str, float]] = None
    forecast_horizon_minutes: int = Field(60, ge=1, le=120)
    current_timestamp: Optional[str] = None

class MetricTrajectoryPoint(BaseModel):
    step_minutes: int
    predicted_timestamp: str
    predicted_value: float
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None

class EarliestThreshold(BaseModel):
    metric: str
    minutes_until_threshold: int
    predicted_time: str
    threshold: float
    current_value: float
    risk_level: str

class PredictResponse(BaseModel):
    app_id: str
    generated_at: str
    forecast_horizon_minutes: int
    current_metrics: Dict[str, float]
    metric_forecasts: Dict[str, List[MetricTrajectoryPoint]]
    threshold_predictions: Dict[str, ThresholdPrediction]
    earliest_threshold: Optional[EarliestThreshold] = None
    failure_probability: Optional[float] = None
    failure_risk_level: Optional[str] = None
    overall_system_status: str  # NORMAL, WARNING, CRITICAL
