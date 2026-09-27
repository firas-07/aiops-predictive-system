from typing import Dict, Tuple, Any
from backend.app.schemas.application import MetricThresholdConfig

# Default operational limit baselines for native metrics if user hasn't specified
DEFAULT_OPERATIONAL_LIMITS = {
    "cpu_percent": 100.0,
    "memory_percent": 100.0,
    "disk_io_mb_s": 80.0,
    "latency_ms": 500.0,
    "http_errors": 50.0,
    "http_success": 3500.0,
    "network_mb_s": 70.0,
    "request_volume": 4000.0,
}

class ThresholdNormalizer:
    """
    Normalizes user-entered percentage thresholds into effective native metric units:
    effective_threshold = operational_limit * (threshold_percentage / 100.0)
    Validates operational limits and boundary conditions.
    """

    @staticmethod
    def normalize(config: MetricThresholdConfig) -> float:
        """Calculate and return effective threshold value in native units."""
        if config.operational_limit <= 0:
            raise ValueError(
                f"Invalid operational limit for metric '{config.metric}': {config.operational_limit}. "
                "Operational limit must be strictly greater than 0."
            )
        if config.threshold_percentage < 0:
            raise ValueError(
                f"Invalid threshold percentage for metric '{config.metric}': {config.threshold_percentage}%. "
                "Threshold percentage must be non-negative."
            )

        effective = config.operational_limit * (config.threshold_percentage / 100.0)
        return round(effective, 4)

    @staticmethod
    def normalize_all(configs: Dict[str, MetricThresholdConfig]) -> Dict[str, Dict[str, Any]]:
        """
        Validate and convert a dictionary of threshold configs into effective evaluation maps.
        Returns:
            {
               metric_name: {
                   "threshold_percentage": 80.0,
                   "operational_limit": 500.0,
                   "effective_threshold": 400.0,
                   "operator": ">=",
                   "unit": "ms",
                   "enabled": True
               }
            }
        """
        resolved = {}
        for metric, conf in configs.items():
            if not conf.enabled:
                continue
            effective_val = ThresholdNormalizer.normalize(conf)
            resolved[metric] = {
                "threshold_percentage": conf.threshold_percentage,
                "operational_limit": conf.operational_limit,
                "effective_threshold": effective_val,
                "operator": conf.operator,
                "unit": conf.unit,
                "enabled": conf.enabled,
            }
        return resolved
