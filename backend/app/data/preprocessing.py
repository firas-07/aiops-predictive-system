from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd
from backend.app.core.logging import logger
from backend.app.core.config import settings

class TelemetryPreprocessor:
    """
    Robust preprocessing pipeline for telemetry data:
    1. Parse UTC timestamp and chronological sorting
    2. Duplicate timestamp handling (average duplicates, log count)
    3. Regularize sampling interval (default 1 min)
    4. Missing timestamp / interval imputation (configurable: interpolate, forward_fill, drop)
    5. Missing metric imputation
    6. Outlier detection (IQR / rolling z-score) distinguishing quality bugs from operational spikes
    """

    def __init__(
        self,
        target_metrics: Optional[List[str]] = None,
        expected_interval_minutes: int = 1,
        missing_strategy: str = "interpolate",
        outlier_method: str = "iqr",
        outlier_zscore_threshold: float = 4.0,
        iqr_multiplier: float = 3.0
    ):
        self.target_metrics = target_metrics or settings.target_metrics
        self.expected_interval_minutes = expected_interval_minutes
        self.missing_strategy = missing_strategy
        self.outlier_method = outlier_method
        self.outlier_zscore_threshold = outlier_zscore_threshold
        self.iqr_multiplier = iqr_multiplier
        self.preprocessing_summary: Dict[str, Any] = {}

    def fit_transform(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        logger.info(f"Starting telemetry preprocessing on {len(df)} rows")
        df_clean = df.copy()

        # 1. Parse timestamps and sort
        df_clean["timestamp"] = pd.to_datetime(df_clean["timestamp"], utc=True)
        df_clean = df_clean.sort_values("timestamp").reset_index(drop=True)

        initial_rows = len(df_clean)

        # 2. Handle duplicate timestamps
        dup_count = int(df_clean.duplicated(subset=["timestamp"]).sum())
        if dup_count > 0:
            logger.warning(f"Handling {dup_count} duplicate timestamps by grouping and taking mean for numeric values")
            # Group by timestamp (and app_id if present)
            group_cols = ["timestamp"]
            if "app_id" in df_clean.columns:
                group_cols.append("app_id")
            
            # Numeric aggregation
            numeric_cols = [c for c in self.target_metrics if c in df_clean.columns]
            other_cols = [c for c in df_clean.columns if c not in group_cols and c not in numeric_cols]
            
            agg_dict = {col: "mean" for col in numeric_cols}
            for col in other_cols:
                agg_dict[col] = "last"  # e.g., app_status, failure_event
                
            df_clean = df_clean.groupby(group_cols, as_index=False).agg(agg_dict)
            df_clean = df_clean.sort_values("timestamp").reset_index(drop=True)

        # 3. Detect and fix data-quality bounds (impossible sensor values)
        clipped_quality_errors = 0
        if "cpu_percent" in df_clean.columns:
            invalid_cpu = (df_clean["cpu_percent"] < 0) | (df_clean["cpu_percent"] > 100)
            clipped_quality_errors += int(invalid_cpu.sum())
            df_clean["cpu_percent"] = df_clean["cpu_percent"].clip(0.0, 100.0)

        if "memory_percent" in df_clean.columns:
            invalid_mem = (df_clean["memory_percent"] < 0) | (df_clean["memory_percent"] > 100)
            clipped_quality_errors += int(invalid_mem.sum())
            df_clean["memory_percent"] = df_clean["memory_percent"].clip(0.0, 100.0)

        for col in ["latency_ms", "disk_io_mb_s", "network_mb_s", "request_volume", "http_errors", "http_success"]:
            if col in df_clean.columns:
                invalid_neg = df_clean[col] < 0
                clipped_quality_errors += int(invalid_neg.sum())
                df_clean[col] = df_clean[col].clip(lower=0.0)

        # 4. Regularize time grid / Missing intervals
        df_clean.set_index("timestamp", inplace=True)
        freq_str = f"{self.expected_interval_minutes}min"
        
        # Resample to ensure exact 1-minute steps
        full_time_index = pd.date_range(
            start=df_clean.index.min(),
            end=df_clean.index.max(),
            freq=freq_str,
            tz=df_clean.index.tz
        )
        missing_interval_count = len(full_time_index) - len(df_clean)
        
        if missing_interval_count > 0:
            logger.info(f"Reindexing time series: {missing_interval_count} missing 1-minute intervals detected")
            df_clean = df_clean.reindex(full_time_index)
            df_clean.index.name = "timestamp"

            # Fill categorical / identifiers
            if "app_id" in df_clean.columns:
                df_clean["app_id"] = df_clean["app_id"].ffill().bfill()
            if "app_status" in df_clean.columns:
                df_clean["app_status"] = df_clean["app_status"].ffill().bfill()
            if "failure_event" in df_clean.columns:
                df_clean["failure_event"] = df_clean["failure_event"].fillna(0).astype(int)

            # Impute numeric metrics according to strategy
            numeric_cols = [c for c in self.target_metrics if c in df_clean.columns]
            if self.missing_strategy == "interpolate":
                df_clean[numeric_cols] = df_clean[numeric_cols].interpolate(method="time").ffill().bfill()
            elif self.missing_strategy == "forward_fill":
                df_clean[numeric_cols] = df_clean[numeric_cols].ffill().bfill()
            elif self.missing_strategy == "drop":
                df_clean = df_clean.dropna(subset=numeric_cols)
            else:
                df_clean[numeric_cols] = df_clean[numeric_cols].interpolate(method="time").ffill().bfill()

        # 5. Outlier Detection: Distinguish operational anomalies from sensor corruption
        # We flag operational spikes without deleting them so model learns real stress behavior
        anomaly_flags: Dict[str, int] = {}
        for col in self.target_metrics:
            if col in df_clean.columns:
                series = df_clean[col]
                if self.outlier_method == "iqr":
                    q25 = series.quantile(0.25)
                    q75 = series.quantile(0.75)
                    iqr = q75 - q25
                    lower_bound = q25 - (self.iqr_multiplier * iqr)
                    upper_bound = q75 + (self.iqr_multiplier * iqr)
                    is_anomaly = (series < lower_bound) | (series > upper_bound)
                else:  # rolling z-score
                    rolling_mean = series.rolling(window=30, min_periods=5).mean()
                    rolling_std = series.rolling(window=30, min_periods=5).std().replace(0, 1e-6)
                    z_scores = ((series - rolling_mean) / rolling_std).abs()
                    is_anomaly = z_scores > self.outlier_zscore_threshold

                anomaly_flags[col] = int(is_anomaly.sum())
                # Add operational anomaly flag column for exploration
                df_clean[f"{col}_is_operational_anomaly"] = is_anomaly.astype(int)

        # Reset index to make timestamp a regular column again
        df_clean.reset_index(inplace=True)

        self.preprocessing_summary = {
            "initial_rows": initial_rows,
            "final_rows": len(df_clean),
            "duplicate_timestamps_resolved": dup_count,
            "missing_intervals_imputed": missing_interval_count,
            "imputation_strategy": self.missing_strategy,
            "clipped_quality_errors": clipped_quality_errors,
            "operational_anomalies_flagged": anomaly_flags,
            "start_timestamp": df_clean["timestamp"].min().isoformat(),
            "end_timestamp": df_clean["timestamp"].max().isoformat()
        }

        logger.info(f"Preprocessing completed. Final rows: {len(df_clean)}. Summary: {self.preprocessing_summary}")
        return df_clean, self.preprocessing_summary
