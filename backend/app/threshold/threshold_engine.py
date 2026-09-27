from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from backend.app.core.logging import logger
from backend.app.core.config import settings
from backend.app.schemas.threshold import ThresholdPrediction

class ThresholdEngine:
    """
    Evaluates forecast metric trajectories against operational thresholds.
    Determines:
    - First predicted crossing timestamp & minutes
    - Risk classification (NORMAL, WARNING, CRITICAL)
    - Earliest predicted threshold across all active metrics
    """

    def __init__(
        self,
        critical_minutes: Optional[int] = None,
        warning_minutes: Optional[int] = None
    ):
        self.critical_minutes = critical_minutes or settings.critical_minutes
        self.warning_minutes = warning_minutes or settings.warning_minutes

    def evaluate_trajectories(
        self,
        metric_forecasts: Dict[str, List[Dict[str, Any]]],
        current_metrics: Dict[str, float],
        threshold_configs: Optional[Dict[str, Any]] = None
    ) -> Tuple[Dict[str, ThresholdPrediction], Optional[Dict[str, Any]], str]:
        """
        Calculates time-to-threshold for all configured metrics.
        Returns:
            - Dict of ThresholdPrediction per metric
            - Earliest predicted threshold dict (or None)
            - Overall system status ("NORMAL", "WARNING", "CRITICAL")
        """
        predictions: Dict[str, ThresholdPrediction] = {}
        earliest_candidate: Optional[Dict[str, Any]] = None
        earliest_minutes = float("inf")
        system_status = "NORMAL"

        active_thresholds = threshold_configs or {}

        for metric, trajectory in metric_forecasts.items():
            current_val = float(current_metrics.get(metric, 0.0))
            
            # Find threshold value and operator
            if metric in active_thresholds:
                t_conf = active_thresholds[metric]
                if isinstance(t_conf, dict):
                    threshold_val = float(t_conf.get("value", 90.0))
                    operator = t_conf.get("operator", ">")
                    enabled = t_conf.get("enabled", True)
                else:
                    threshold_val = float(t_conf)
                    operator = ">"
                    enabled = True
            elif metric in settings.thresholds:
                def_thresh = settings.thresholds[metric]
                threshold_val = float(def_thresh.value)
                operator = def_thresh.operator
                enabled = def_thresh.enabled
            else:
                continue

            if not enabled:
                continue

            # Check if already currently breached at t=0
            is_currently_breached = (
                (operator in [">", ">="] and current_val >= threshold_val) or
                (operator in ["<", "<="] and current_val <= threshold_val)
            )

            crossing_time_str = None
            minutes_until = None
            status_text = "not_reached_within_horizon"
            risk_level = "NORMAL"
            message = f"Metric projected to remain within operational limit ({operator} {threshold_val})."

            if is_currently_breached:
                minutes_until = 0
                crossing_time_str = trajectory[0]["predicted_timestamp"] if trajectory else None
                status_text = "currently_exceeded"
                risk_level = "CRITICAL"
                message = f"Metric is CURRENTLY exceeding threshold ({current_val} vs {threshold_val}). Immediate attention recommended."
            else:
                # Search forward along trajectory for the first crossing point
                for point in trajectory:
                    pred_val = point["predicted_value"]
                    crossed = (
                        (operator in [">", ">="] and pred_val >= threshold_val) or
                        (operator in ["<", "<="] and pred_val <= threshold_val)
                    )
                    if crossed:
                        minutes_until = point["step_minutes"]
                        crossing_time_str = point["predicted_timestamp"]
                        
                        if minutes_until <= self.critical_minutes:
                            status_text = "imminent_breach"
                            risk_level = "CRITICAL"
                            message = f"Threshold predicted to be reached within {minutes_until} minutes! (Critical)"
                        elif minutes_until <= self.warning_minutes:
                            status_text = "approaching_threshold"
                            risk_level = "WARNING"
                            message = f"Threshold predicted to be reached in {minutes_until} minutes (Warning)."
                        else:
                            status_text = "approaching_threshold_late"
                            risk_level = "NORMAL"
                            message = f"Threshold predicted in {minutes_until} minutes (Later horizon)."
                        break

            # Update overall system status
            if risk_level == "CRITICAL":
                system_status = "CRITICAL"
            elif risk_level == "WARNING" and system_status != "CRITICAL":
                system_status = "WARNING"

            # Check for earliest predicted threshold
            if minutes_until is not None and minutes_until < earliest_minutes:
                earliest_minutes = minutes_until
                earliest_candidate = {
                    "metric": metric,
                    "minutes_until_threshold": minutes_until,
                    "predicted_time": crossing_time_str,
                    "threshold": threshold_val,
                    "current_value": current_val,
                    "risk_level": risk_level
                }

            predictions[metric] = ThresholdPrediction(
                metric=metric,
                current_value=current_val,
                threshold_value=threshold_val,
                operator=operator,
                time_to_threshold_minutes=minutes_until,
                predicted_crossing_time=crossing_time_str,
                status=status_text,
                risk_level=risk_level,
                message=message
            )

        return predictions, earliest_candidate, system_status
