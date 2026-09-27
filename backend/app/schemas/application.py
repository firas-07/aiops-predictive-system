from typing import Dict, List, Optional, Literal, Any
from pydantic import BaseModel, Field
from datetime import datetime

# Supported Operators
OperatorType = Literal[">=", ">", "<=", "<"]

class MetricThresholdConfig(BaseModel):
    metric: str
    threshold_percentage: float = Field(..., ge=0.0, le=200.0, description="Threshold entered as percentage (0-100+%)")
    operational_limit: float = Field(..., gt=0.0, description="Reference baseline/operational limit in native metric units")
    operator: OperatorType = Field(">=", description="Comparison operator: >=, >, <=, <")
    enabled: bool = Field(True, description="Whether this threshold is actively monitored")
    unit: str = Field("", description="Native metric unit (%, ms, MB/s, req/min, etc.)")

    @property
    def effective_threshold(self) -> float:
        """
        Convert threshold percentage to actual metric-unit threshold:
        effective_threshold = operational_limit * (threshold_percentage / 100.0)
        """
        return round(self.operational_limit * (self.threshold_percentage / 100.0), 4)

class AzureConnectionConfig(BaseModel):
    tenant_id: Optional[str] = Field(None, description="Azure Active Directory Tenant ID")
    client_id: Optional[str] = Field(None, description="Azure Service Principal Client / Application ID")
    client_secret: Optional[str] = Field(None, description="Azure Service Principal Client Secret (Masked in responses)")
    subscription_id: Optional[str] = Field(None, description="Azure Subscription ID")
    resource_group: Optional[str] = Field(None, description="Azure Resource Group")
    resource_name: Optional[str] = Field(None, description="Azure Resource or Application Insights component name")
    telemetry_service: Literal["azure_monitor", "app_insights", "log_analytics"] = Field(
        "azure_monitor",
        description="Target Azure telemetry source"
    )

class ApplicationCreateRequest(BaseModel):
    id: str = Field(..., description="Unique application identifier (e.g. app-001, chatgpt-azure-prod)")
    name: str = Field(..., description="Human-readable application name")
    telemetry_source: Literal["csv", "azure"] = Field("csv", description="Telemetry mode: 'csv' for dev or 'azure' for prod")
    azure_config: Optional[AzureConnectionConfig] = None
    csv_file_path: Optional[str] = Field(None, description="Path to CSV telemetry file (for csv mode)")
    thresholds: Optional[Dict[str, MetricThresholdConfig]] = None

class ApplicationUpdateRequest(BaseModel):
    name: Optional[str] = None
    telemetry_source: Optional[Literal["csv", "azure"]] = None
    azure_config: Optional[AzureConnectionConfig] = None
    csv_file_path: Optional[str] = None
    thresholds: Optional[Dict[str, MetricThresholdConfig]] = None

class ApplicationResponse(BaseModel):
    id: str
    name: str
    telemetry_source: Literal["csv", "azure"]
    azure_config: Optional[Dict[str, Any]] = None  # Client secret is masked!
    csv_file_path: Optional[str] = None
    thresholds: Dict[str, MetricThresholdConfig]
    created_at: str
    updated_at: str
    is_connected: bool = True
    last_telemetry_timestamp: Optional[str] = None

# Forecast point for trajectory
class ForecastTrajectoryPoint(BaseModel):
    minutes_ahead: int
    predicted_timestamp: str
    value: float
    estimated_lower: Optional[float] = None
    estimated_upper: Optional[float] = None

# Metric Prediction in 30-minute real-time flow
class MetricPredictionResult(BaseModel):
    metric: str
    unit: str
    current_value: float
    threshold_percentage: float
    operational_limit: float
    effective_threshold: float
    operator: str
    predicted_value_30m: float
    status: Literal["CURRENT_BREACH", "PREDICTED_BREACH", "NO_BREACH"]
    predicted_crossing_minutes: Optional[int] = None
    predicted_crossing_time: Optional[str] = None
    severity: Literal["NORMAL", "WARNING", "CRITICAL"]
    message: str
    forecast: List[ForecastTrajectoryPoint]

class EarliestBreachInfo(BaseModel):
    metric: str
    predicted_crossing_minutes: int
    predicted_crossing_time: Optional[str] = None
    effective_threshold: float
    current_value: float
    severity: str

class RealtimePredictionRequest(BaseModel):
    horizon_minutes: int = Field(30, ge=5, le=120, description="Prediction horizon in minutes (default 30)")

class RealtimePredictionResponse(BaseModel):
    application: Dict[str, str]
    prediction_time: str
    telemetry_source: str
    horizon_minutes: int
    overall_status: Literal["NORMAL", "WARNING", "AT_RISK", "CRITICAL"]
    status_summary: str
    metrics_breaching_count: int
    earliest_breach: Optional[EarliestBreachInfo] = None
    metrics: List[MetricPredictionResult]
    failure_probability_30m: Optional[float] = None
    failure_risk_level: Optional[str] = None
    model_version: str
