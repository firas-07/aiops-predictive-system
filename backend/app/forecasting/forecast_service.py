from typing import Dict, List, Optional, Any
from datetime import datetime
import pandas as pd
from backend.app.core.logging import logger
from backend.app.core.config import settings
from backend.app.models.model_registry import ModelRegistry
from backend.app.data.telemetry_provider import CsvTelemetryProvider
from backend.app.forecasting.recursive_forecaster import RecursiveForecaster
from backend.app.threshold.threshold_engine import ThresholdEngine
from backend.app.schemas.prediction import PredictRequest, PredictResponse, EarliestThreshold, MetricTrajectoryPoint
from backend.app.schemas.threshold import ThresholdPrediction

class ForecastService:
    """
    Central orchestration service for generating predictions, threshold alerts,
    and failure risk scores.
    """

    def __init__(
        self,
        registry: Optional[ModelRegistry] = None,
        telemetry_provider: Optional[CsvTelemetryProvider] = None
    ):
        self.registry = registry or ModelRegistry()
        self.telemetry_provider = telemetry_provider or CsvTelemetryProvider(settings.raw_data_path)
        self.threshold_engine = ThresholdEngine()

    def predict(self, request: PredictRequest) -> PredictResponse:
        logger.info(f"Processing prediction request for app_id={request.app_id}, horizon={request.forecast_horizon_minutes}m")

        # 1. Load active models from registry
        try:
            forecasters, failure_model, feature_pipeline, meta = self.registry.load_model_suite()
        except FileNotFoundError as e:
            logger.error(f"Prediction requested but models not ready: {str(e)}")
            raise ValueError("Model not trained. Please train the model before requesting predictions.") from e

        # 2. Assemble historical telemetry context (last 75 minutes required for full lag/rolling calculation)
        if request.historical_window and len(request.historical_window) >= 60:
            history_df = pd.DataFrame(request.historical_window)
            history_df["timestamp"] = pd.to_datetime(history_df["timestamp"], utc=True)
        else:
            # Fetch recent window from telemetry provider
            history_df = self.telemetry_provider.get_recent_window(app_id=request.app_id, minutes=75)
            if history_df.empty or len(history_df) < 60:
                raise ValueError("Insufficient historical telemetry available for accurate feature computation (min 60 rows needed).")

        # 3. Incorporate user-provided latest_metrics if specified
        current_metrics_dict: Dict[str, float] = {}
        if request.latest_metrics:
            metrics_dict = request.latest_metrics.model_dump()
            current_metrics_dict = metrics_dict
            # Append as latest timestamp
            last_ts = pd.to_datetime(history_df["timestamp"].iloc[-1], utc=True) + pd.Timedelta(minutes=1)
            row_dict = {"timestamp": last_ts, "app_id": request.app_id}
            row_dict.update(metrics_dict)
            history_df = pd.concat([history_df, pd.DataFrame([row_dict])], ignore_index=True)
        else:
            # Extract from latest historical row
            last_row = history_df.iloc[-1]
            for m in settings.target_metrics:
                if m in last_row:
                    current_metrics_dict[m] = float(last_row[m])

        start_ts = pd.to_datetime(history_df["timestamp"].iloc[-1], utc=True)

        # 4. Execute recursive multi-step forecasting
        recursive_forecaster = RecursiveForecaster(
            forecasters=forecasters,
            feature_pipeline=feature_pipeline
        )
        trajectories = recursive_forecaster.forecast_trajectory(
            history_df=history_df,
            horizon_minutes=request.forecast_horizon_minutes,
            start_timestamp=start_ts
        )

        # 5. Evaluate threshold crossings
        threshold_preds, earliest_cand, overall_status = self.threshold_engine.evaluate_trajectories(
            metric_forecasts=trajectories,
            current_metrics=current_metrics_dict,
            threshold_configs=request.thresholds
        )

        # 6. Evaluate Application Failure Probability if failure model is active
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
                logger.warning(f"Could not compute failure probability: {e}")

        # 7. Convert trajectories to schema format
        metric_forecasts_response = {}
        for m, pts in trajectories.items():
            metric_forecasts_response[m] = [MetricTrajectoryPoint(**p) for p in pts]

        earliest_obj = EarliestThreshold(**earliest_cand) if earliest_cand else None

        response = PredictResponse(
            app_id=request.app_id,
            generated_at=datetime.utcnow().isoformat(),
            forecast_horizon_minutes=request.forecast_horizon_minutes,
            current_metrics=current_metrics_dict,
            metric_forecasts=metric_forecasts_response,
            threshold_predictions=threshold_preds,
            earliest_threshold=earliest_obj,
            failure_probability=failure_prob,
            failure_risk_level=failure_risk,
            overall_system_status=overall_status
        )
        return response
