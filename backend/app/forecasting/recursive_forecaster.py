from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from backend.app.core.logging import logger
from backend.app.models.lightgbm_forecaster import MetricForecaster
from backend.app.features.feature_pipeline import FeaturePipeline

class RecursiveForecaster:
    """
    Executes multi-step recursive forecasting across all target metrics.
    Maintains a rolling operational buffer, iteratively predicting step t+1,
    updating lag and rolling states, and projecting up to H minutes.
    """

    def __init__(
        self,
        forecasters: Dict[str, MetricForecaster],
        feature_pipeline: FeaturePipeline
    ):
        self.forecasters = forecasters
        self.feature_pipeline = feature_pipeline

    def forecast_trajectory(
        self,
        history_df: pd.DataFrame,
        horizon_minutes: int = 60,
        start_timestamp: Optional[datetime] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Produce minute-by-minute forecasts for 1..horizon_minutes.
        Returns:
            {
               metric_name: [
                   {
                      "step_minutes": 1,
                      "predicted_timestamp": "...",
                      "predicted_value": 72.5,
                      "lower_bound": 68.1,
                      "upper_bound": 76.9
                   }, ...
               ]
            }
        """
        metrics = list(self.forecasters.keys())
        buffer_df = history_df.copy()
        buffer_df["timestamp"] = pd.to_datetime(buffer_df["timestamp"], utc=True)
        buffer_df = buffer_df.sort_values("timestamp").reset_index(drop=True)

        if start_timestamp is None:
            curr_ts = buffer_df["timestamp"].iloc[-1]
        else:
            curr_ts = pd.to_datetime(start_timestamp, utc=True)

        forecasts: Dict[str, List[Dict[str, Any]]] = {m: [] for m in metrics}

        logger.info(f"Generating recursive forecast for horizon={horizon_minutes}m across {len(metrics)} metrics")

        for step in range(1, horizon_minutes + 1):
            next_ts = curr_ts + timedelta(minutes=step)

            # Generate single feature row from current buffer state
            feat_row = self.feature_pipeline.transform_single_window(
                recent_window_df=buffer_df.tail(75)
            )

            predicted_values = {}
            for metric, forecaster in self.forecasters.items():
                pred_val = float(forecaster.predict(feat_row)[0])
                
                # Dynamic confidence interval based on empirical validation residuals
                # Error scales with square root of time step diffusion
                uncertainty_factor = np.sqrt(step / 10.0) if step > 1 else 1.0
                margin = 1.96 * forecaster.residual_std * uncertainty_factor
                
                lower = max(0.0, pred_val - margin)
                upper = pred_val + margin
                if "percent" in metric:
                    lower = min(100.0, max(0.0, lower))
                    upper = min(100.0, max(0.0, upper))

                predicted_values[metric] = pred_val

                forecasts[metric].append({
                    "step_minutes": step,
                    "predicted_timestamp": next_ts.isoformat(),
                    "predicted_value": round(pred_val, 2),
                    "lower_bound": round(lower, 2),
                    "upper_bound": round(upper, 2)
                })

            # Append new predicted row to rolling buffer for the next step's recursive computation
            new_buffer_row = {"timestamp": next_ts}
            for m in metrics:
                new_buffer_row[m] = predicted_values[m]
            
            # Fill other required non-metric columns if needed
            buffer_df = pd.concat([buffer_df, pd.DataFrame([new_buffer_row])], ignore_index=True)

        return forecasts
