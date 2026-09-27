from typing import Dict, List, Tuple, Any
from datetime import datetime
import pandas as pd
import numpy as np
from backend.app.core.logging import logger

REQUIRED_TELEMETRY_COLUMNS = [
    "timestamp",
    "cpu_percent",
    "memory_percent",
    "disk_io_mb_s",
    "latency_ms",
    "http_errors",
    "http_success",
    "network_mb_s",
    "request_volume"
]

NUMERIC_COLUMNS = [
    "cpu_percent",
    "memory_percent",
    "disk_io_mb_s",
    "latency_ms",
    "http_errors",
    "http_success",
    "network_mb_s",
    "request_volume"
]

class DataValidationResult:
    def __init__(self):
        self.is_valid: bool = True
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.quality_report: Dict[str, Any] = {}

    def add_error(self, message: str):
        self.is_valid = False
        self.errors.append(message)
        logger.error(f"DataValidationError: {message}")

    def add_warning(self, message: str):
        self.warnings.append(message)
        logger.warning(f"DataValidationWarning: {message}")


class DataValidator:
    """
    Validates telemetry datasets:
    - Checks required columns
    - Parses timestamps to UTC
    - Detects duplicates & missing intervals
    - Validates numeric boundaries and types
    - Generates comprehensive data quality report
    """

    @classmethod
    def validate_schema(cls, df: pd.DataFrame) -> Tuple[bool, List[str]]:
        missing_cols = [c for c in REQUIRED_TELEMETRY_COLUMNS if c not in df.columns]
        if missing_cols:
            return False, [f"Missing required column(s): {', '.join(missing_cols)}"]
        return True, []

    @classmethod
    def validate_dataset(
        cls,
        df: pd.DataFrame,
        expected_interval_minutes: int = 1
    ) -> DataValidationResult:
        result = DataValidationResult()
        
        # 1. Check required columns
        valid_schema, schema_errors = cls.validate_schema(df)
        if not valid_schema:
            for err in schema_errors:
                result.add_error(err)
            return result

        # 2. Check row count
        row_count = len(df)
        if row_count < 60:
            result.add_error(f"Dataset too small ({row_count} rows). Minimum 60 rows required for time-series analysis.")
            return result

        # 3. Parse timestamp
        try:
            ts_series = pd.to_datetime(df["timestamp"], utc=True)
        except Exception as e:
            result.add_error(f"Failed to parse 'timestamp' column into datetime: {str(e)}")
            return result

        # 4. Check for duplicates
        dup_timestamps = int(ts_series.duplicated().sum())
        full_row_duplicates = int(df.duplicated().sum())
        if dup_timestamps > 0:
            result.add_warning(f"Found {dup_timestamps} duplicate timestamps. Will be deduplicated during preprocessing.")

        # 5. Check time ordering and sampling frequency
        sorted_ts = ts_series.sort_values().reset_index(drop=True)
        min_ts = sorted_ts.min()
        max_ts = sorted_ts.max()
        time_diffs = sorted_ts.diff().dropna()
        
        expected_delta = pd.Timedelta(minutes=expected_interval_minutes)
        irregular_gaps = int((time_diffs != expected_delta).sum())
        if irregular_gaps > 0:
            result.add_warning(
                f"Found {irregular_gaps} irregular time intervals (expected {expected_interval_minutes}m intervals). "
                f"Sampling will be normalized in preprocessing."
            )

        # 6. Check numeric columns
        column_quality = {}
        for col in NUMERIC_COLUMNS:
            series = pd.to_numeric(df[col], errors="coerce")
            nan_count = int(series.isna().sum())
            inf_count = int(np.isinf(series.dropna()).sum())
            
            if nan_count > 0:
                result.add_warning(f"Column '{col}' has {nan_count} missing/invalid numeric values.")
            if inf_count > 0:
                result.add_error(f"Column '{col}' contains {inf_count} infinite values.")

            col_stats = {
                "missing_count": nan_count,
                "missing_pct": round(float(nan_count / row_count * 100), 2),
                "min": float(series.min()) if not series.dropna().empty else None,
                "max": float(series.max()) if not series.dropna().empty else None,
                "mean": round(float(series.mean()), 3) if not series.dropna().empty else None,
                "std": round(float(series.std()), 3) if not series.dropna().empty else None,
            }
            column_quality[col] = col_stats

        # 7. Check percentage bounds for CPU and Memory
        if "cpu_percent" in df.columns:
            cpu_num = pd.to_numeric(df["cpu_percent"], errors="coerce")
            if (cpu_num < 0).any() or (cpu_num > 100).any():
                result.add_warning("cpu_percent values found outside expected [0, 100] range.")

        if "memory_percent" in df.columns:
            mem_num = pd.to_numeric(df["memory_percent"], errors="coerce")
            if (mem_num < 0).any() or (mem_num > 100).any():
                result.add_warning("memory_percent values found outside expected [0, 100] range.")

        # Build Quality Report
        result.quality_report = {
            "total_rows": row_count,
            "columns": list(df.columns),
            "min_timestamp": min_ts.isoformat(),
            "max_timestamp": max_ts.isoformat(),
            "time_span_hours": round((max_ts - min_ts).total_seconds() / 3600, 2),
            "duplicate_timestamps": dup_timestamps,
            "full_row_duplicates": full_row_duplicates,
            "irregular_gaps": irregular_gaps,
            "column_metrics": column_quality,
            "validation_timestamp": datetime.utcnow().isoformat(),
            "is_valid": result.is_valid,
            "warnings_count": len(result.warnings),
            "errors_count": len(result.errors)
        }

        logger.info(f"Data validation complete: is_valid={result.is_valid}, errors={len(result.errors)}, warnings={len(result.warnings)}")
        return result
