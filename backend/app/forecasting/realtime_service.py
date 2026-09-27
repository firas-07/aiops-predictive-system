from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import pandas as pd
from backend.app.core.logging import logger
from backend.app.core.config import settings
from backend.app.core.app_repository import app_repo
from backend.app.data.telemetry_provider import get_telemetry_provider
from backend.app.threshold.normalizer import ThresholdNormalizer
from backend.app.threshold.alert_engine import AlertEngine
from backend.app.models.model_registry import ModelRegistry
from backend.app.forecasting.recursive_forecaster import RecursiveForecaster
from backend.app.schemas.application import (
    RealtimePredictionRequest,
    RealtimePredictionResponse,
    MetricPredictionResult,
    EarliestBreachInfo,
)

class RealtimePredictionService:
    """
    Real-time AIOps Prediction Service:
    - Obtains latest telemetry automatically from the configured provider (CSV or Azure)
    - Normalizes user percentage thresholds into effective metric limits
    - Runs the 8 LightGBM forecasters to generate 30-minute trajectories
    - Evaluates threshold crossings, time-to-threshold, and alert severities
    - Computes overall application risk without conflating threshold breach with system crash
    """

    def __init__(self):
        self.registry = ModelRegistry()
        self.alert_engine = AlertEngine()

    def predict_for_application(
        self,
        app_id: str,
        horizon_minutes: int = 30
    ) -> RealtimePredictionResponse:
        logger.info(f"Executing real-time prediction for app_id={app_id}, horizon={horizon_minutes}m")

        # 1. Fetch Application Configuration
        app_data = app_repo.get_raw_application(app_id)
        if not app_data:
            raise ValueError(f"Application with ID '{app_id}' not found.")

        # 2. Get Telemetry Provider (CsvTelemetryProvider or AzureTelemetryProvider)
        provider = get_telemetry_provider(app_data)

        # 3. Retrieve Latest Telemetry Window (75 min history needed for lags up to 60m + warmup)
        history_df = provider.get_recent_window(app_id=app_id, minutes=75)
        if history_df.empty or len(history_df) < 60:
            raise ValueError(
                f"Insufficient historical telemetry available for app '{app_id}' "
                f"({len(history_df)} rows found, minimum 60 required for feature generation)."
            )

        # 4. Extract Current Metrics from latest observation
        history_df["timestamp"] = pd.to_datetime(history_df["timestamp"], utc=True)
        history_df = history_df.sort_values("timestamp").reset_index(drop=True)
        latest_row = history_df.iloc[-1]
        
        current_metrics = {}
        for m in settings.target_metrics:
            if m in latest_row:
                current_metrics[m] = float(latest_row[m])
            else:
                current_metrics[m] = 0.0

        current_timestamp = pd.to_datetime(latest_row["timestamp"], utc=True)

        # 5. Load Trained Forecasting Models
        try:
            forecasters, failure_model, feature_pipeline, meta = self.registry.load_model_suite()
        except FileNotFoundError as e:
            raise ValueError("Model suite not trained. Please train models before requesting predictions.") from e

        # 6. Normalize User Threshold Percentages
        app_thresholds = app_repo.get_application(app_id).thresholds
        normalized_thresholds = ThresholdNormalizer.normalize_all(app_thresholds)

        # 7. Generate 30-Minute Trajectory Projection
        recursive_forecaster = RecursiveForecaster(
            forecasters=forecasters,
            feature_pipeline=feature_pipeline
        )
        trajectories = recursive_forecaster.forecast_trajectory(
            history_df=history_df,
            horizon_minutes=horizon_minutes,
            start_timestamp=current_timestamp
        )

        # 8. Evaluate Thresholds & Alerts
        metric_results, earliest_breach, overall_status, summary, breach_count = self.alert_engine.evaluate_all(
            current_metrics=current_metrics,
            trajectories=trajectories,
            normalized_thresholds=normalized_thresholds
        )

        # 9. Second-Stage Failure / Degradation Probability
        failure_prob = None
        failure_risk = None
        if failure_model is not None:
            try:
                feat_row = feature_pipeline.transform_single_window(recent_window_df=history_df.tail(75))
                failure_prob = round(failure_model.predict_probability(feat_row), 4)
                if failure_prob >= 0.5:
                    failure_risk = "HIGH_FAILURE_RISK"
                elif failure_prob >= 0.2:
                    failure_risk = "MODERATE_FAILURE_RISK"
                else:
                    failure_risk = "LOW_FAILURE_RISK"
            except Exception as e:
                logger.warning(f"Could not compute second-stage failure probability: {e}")

        # Update last telemetry timestamp in repo metadata
        app_data["last_telemetry_timestamp"] = current_timestamp.isoformat()

        response = RealtimePredictionResponse(
            application={
                "id": app_id,
                "name": app_data.get("name", app_id)
            },
            prediction_time=datetime.now(timezone.utc).isoformat(),
            telemetry_source=app_data.get("telemetry_source", "csv"),
            horizon_minutes=horizon_minutes,
            overall_status=overall_status,
            status_summary=summary,
            metrics_breaching_count=breach_count,
            earliest_breach=earliest_breach,
            metrics=metric_results,
            failure_probability_30m=failure_prob,
            failure_risk_level=failure_risk,
            model_version=meta.get("model_version", "1.0.0"),
        )
        return response

realtime_service = RealtimePredictionService()
