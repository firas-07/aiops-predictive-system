from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import acf
from backend.app.core.logging import logger
from backend.app.core.config import settings

class TimeSeriesAnalyzer:
    """
    Computes time-series statistical properties:
    - Descriptive statistics & quantiles
    - Cross-metric correlation matrix
    - Autocorrelation function (ACF) across lags
    - Rolling metrics (trend, rolling mean, rolling std)
    - Anomaly period summaries
    """

    def __init__(self, target_metrics: Optional[List[str]] = None):
        self.target_metrics = target_metrics or settings.target_metrics

    def compute_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        logger.info(f"Computing time-series analysis summary for {len(df)} rows")
        
        # 1. Descriptive stats
        numeric_cols = [c for c in self.target_metrics if c in df.columns]
        desc_df = df[numeric_cols].describe(percentiles=[0.05, 0.25, 0.5, 0.75, 0.95, 0.99]).T
        stats_dict = {}
        for col, row in desc_df.iterrows():
            stats_dict[col] = {
                "count": int(row["count"]),
                "mean": round(float(row["mean"]), 2),
                "std": round(float(row["std"]), 2),
                "min": round(float(row["min"]), 2),
                "p5": round(float(row["5%"]), 2),
                "p25": round(float(row["25%"]), 2),
                "median": round(float(row["50%"]), 2),
                "p75": round(float(row["75%"]), 2),
                "p95": round(float(row["95%"]), 2),
                "p99": round(float(row["99%"]), 2),
                "max": round(float(row["max"]), 2),
            }

        # 2. Correlation matrix
        corr_matrix = df[numeric_cols].corr().round(3).to_dict()

        # 3. Autocorrelation (lags 1, 5, 10, 15, 30, 60)
        acf_dict = {}
        for col in numeric_cols:
            series = df[col].dropna()
            if len(series) > 60:
                acf_vals = acf(series, nlags=60, fft=True)
                acf_dict[col] = {
                    "lag_1": round(float(acf_vals[1]), 3),
                    "lag_5": round(float(acf_vals[5]), 3),
                    "lag_15": round(float(acf_vals[15]), 3),
                    "lag_30": round(float(acf_vals[30]), 3),
                    "lag_60": round(float(acf_vals[60]), 3),
                }

        # 4. Status counts
        status_counts = {}
        if "app_status" in df.columns:
            status_counts = {k: int(v) for k, v in df["app_status"].value_counts().items()}

        failure_counts = {}
        if "failure_event" in df.columns:
            failure_counts = {str(k): int(v) for k, v in df["failure_event"].value_counts().items()}

        # 5. Downsampled preview for frontend visualization (e.g. 1000 points over the dataset)
        sample_step = max(1, len(df) // 1000)
        sampled_df = df.iloc[::sample_step][["timestamp"] + numeric_cols]
        sampled_df["timestamp"] = sampled_df["timestamp"].astype(str)
        time_series_preview = sampled_df.to_dict(orient="records")

        return {
            "total_records": len(df),
            "metrics": numeric_cols,
            "statistics": stats_dict,
            "correlations": corr_matrix,
            "autocorrelations": acf_dict,
            "app_status_counts": status_counts,
            "failure_event_counts": failure_counts,
            "time_series_preview": time_series_preview,
            "start_time": str(df["timestamp"].min()),
            "end_time": str(df["timestamp"].max())
        }
