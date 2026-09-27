from typing import List, Dict, Tuple, Optional, Any
from pathlib import Path
import json
import pandas as pd
from backend.app.core.logging import logger
from backend.app.core.config import settings
from backend.app.features.lag_features import add_lag_features, add_delta_features
from backend.app.features.rolling_features import add_rolling_features, add_trend_features
from backend.app.features.time_features import add_time_features

EXCLUDED_LABEL_COLUMNS = ["app_status", "failure_event", "app_id"]

class FeaturePipeline:
    """
    Constructs the end-to-end feature matrix for supervised time-series forecasting.
    Includes:
    - Lag features (t-1, t-5, t-10, t-15, t-30, t-60)
    - Delta / change features (t - (t-k))
    - Rolling window statistics (mean, std, min, max for windows 5, 15, 30, 60)
    - Trend slope
    - Calendar and cyclical time features (hour, day_of_week, sin/cos)
    - Strictly excludes target labels (app_status, failure_event) to eliminate leakage
    """

    def __init__(
        self,
        metrics: Optional[List[str]] = None,
        lags: Optional[List[int]] = None,
        rolling_windows: Optional[List[int]] = None,
        deltas: Optional[List[int]] = None,
    ):
        self.metrics = metrics or settings.target_metrics
        self.lags = lags or settings.lags
        self.rolling_windows = rolling_windows or settings.rolling_windows
        self.deltas = deltas or settings.deltas
        self.feature_columns: List[str] = []

    def fit_transform(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
        logger.info(f"Generating features for {len(df)} telemetry rows")
        df_feat = df.copy()

        # 1. Ensure timestamp ordering
        df_feat["timestamp"] = pd.to_datetime(df_feat["timestamp"], utc=True)
        df_feat = df_feat.sort_values("timestamp").reset_index(drop=True)

        # 2. Add time features
        df_feat = add_time_features(df_feat, timestamp_col="timestamp")

        # 3. Add lag features
        df_feat = add_lag_features(df_feat, metrics=self.metrics, lags=self.lags)

        # 4. Add delta features
        df_feat = add_delta_features(df_feat, metrics=self.metrics, deltas=self.deltas)

        # 5. Add rolling statistics
        df_feat = add_rolling_features(df_feat, metrics=self.metrics, windows=self.rolling_windows)

        # 6. Add short-term trend / slope
        df_feat = add_trend_features(df_feat, metrics=self.metrics, window=15)

        # 7. Identify all feature columns (excluding raw timestamp, app_id, labels, and target columns if used separately)
        non_feature_cols = set(["timestamp", "app_id"] + EXCLUDED_LABEL_COLUMNS)
        
        # All columns created by the pipeline plus the raw metric values at time t
        feature_cols = [
            c for c in df_feat.columns 
            if c not in non_feature_cols and not c.endswith("_is_operational_anomaly")
        ]

        # 8. Drop rows with NaNs resulting from max lag (e.g. initial 60 rows)
        max_lag = max(self.lags + self.rolling_windows)
        logger.info(f"Dropping initial {max_lag} warmup rows with incomplete lag history")
        df_feat_clean = df_feat.iloc[max_lag:].reset_index(drop=True)

        self.feature_columns = feature_cols
        logger.info(f"Generated {len(feature_cols)} features across {len(df_feat_clean)} samples")
        return df_feat_clean, feature_cols

    def transform_single_window(
        self,
        recent_window_df: pd.DataFrame,
        current_metrics: Optional[Dict[str, float]] = None
    ) -> pd.DataFrame:
        """
        Generate feature vector for inference from a recent telemetry window (last 60+ rows).
        Returns a 1-row DataFrame containing all engineered features ready for forecasting.
        """
        df_win = recent_window_df.copy()
        df_win["timestamp"] = pd.to_datetime(df_win["timestamp"], utc=True)
        df_win = df_win.sort_values("timestamp").reset_index(drop=True)

        if current_metrics is not None:
            # If current metrics are provided as an explicit latest point, append or update last row
            last_ts = df_win["timestamp"].iloc[-1] + pd.Timedelta(minutes=1)
            row_data = {"timestamp": last_ts}
            for m in self.metrics:
                row_data[m] = current_metrics.get(m, df_win[m].iloc[-1])
            df_win = pd.concat([df_win, pd.DataFrame([row_data])], ignore_index=True)

        # Add time features
        df_win = add_time_features(df_win, timestamp_col="timestamp")
        # Add lag features
        df_win = add_lag_features(df_win, metrics=self.metrics, lags=self.lags)
        # Add deltas
        df_win = add_delta_features(df_win, metrics=self.metrics, deltas=self.deltas)
        # Add rolling features
        df_win = add_rolling_features(df_win, metrics=self.metrics, windows=self.rolling_windows)
        # Add trend slope
        df_win = add_trend_features(df_win, metrics=self.metrics, window=15)

        # Take only the final row
        latest_row = df_win.iloc[[-1]][self.feature_columns].copy()
        return latest_row

    def save_feature_config(self, save_path: str | Path):
        meta = {
            "feature_columns": self.feature_columns,
            "metrics": self.metrics,
            "lags": self.lags,
            "rolling_windows": self.rolling_windows,
            "deltas": self.deltas
        }
        path = Path(save_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(meta, f, indent=2)

    def load_feature_config(self, load_path: str | Path):
        with open(load_path, "r") as f:
            meta = json.load(f)
        self.feature_columns = meta["feature_columns"]
        self.metrics = meta["metrics"]
        self.lags = meta["lags"]
        self.rolling_windows = meta["rolling_windows"]
        self.deltas = meta["deltas"]
