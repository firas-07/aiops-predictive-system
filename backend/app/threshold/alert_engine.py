from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from backend.app.schemas.application import (
    MetricPredictionResult,
    ForecastTrajectoryPoint,
    EarliestBreachInfo,
)

class AlertEngine:
    """
    Dedicated Alert & Threshold Evaluation Engine.
    Consumes current metrics, 30-minute forecast trajectories, effective thresholds, and operators.
    Calculates exact predicted time-to-threshold and assigns severity levels:
    - CURRENT_BREACH (time=0, CRITICAL)
    - PREDICTED_BREACH (0-15m -> CRITICAL, 16-30m -> WARNING)
    - NO_BREACH (Normal)
    """

    def __init__(self, critical_lead_minutes: int = 15, warning_lead_minutes: int = 30):
        self.critical_lead_minutes = critical_lead_minutes
        self.warning_lead_minutes = warning_lead_minutes

    @staticmethod
    def _is_breached(value: float, threshold: float, operator: str) -> bool:
        if operator == ">=":
            return value >= threshold
        elif operator == ">":
            return value > threshold
        elif operator == "<=":
            return value <= threshold
        elif operator == "<":
            return value < threshold
        return value >= threshold

    def evaluate_metric(
        self,
        metric: str,
        current_val: float,
        trajectory: List[Dict[str, Any]],
        threshold_percentage: float,
        operational_limit: float,
        effective_threshold: float,
        operator: str,
        unit: str,
    ) -> MetricPredictionResult:
        # Check State 1: CURRENT_BREACH
        is_now_breached = self._is_breached(current_val, effective_threshold, operator)

        forecast_points = [
            ForecastTrajectoryPoint(
                minutes_ahead=pt["step_minutes"],
                predicted_timestamp=pt["predicted_timestamp"],
                value=round(float(pt["predicted_value"]), 2),
                estimated_lower=round(float(pt.get("lower_bound", pt["predicted_value"])), 2),
                estimated_upper=round(float(pt.get("upper_bound", pt["predicted_value"])), 2),
            )
            for pt in trajectory
        ]

        predicted_val_30m = forecast_points[-1].value if forecast_points else current_val

        if is_now_breached:
            crossing_time_str = forecast_points[0].predicted_timestamp if forecast_points else None
            return MetricPredictionResult(
                metric=metric,
                unit=unit,
                current_value=round(current_val, 2),
                threshold_percentage=threshold_percentage,
                operational_limit=operational_limit,
                effective_threshold=effective_threshold,
                operator=operator,
                predicted_value_30m=predicted_val_30m,
                status="CURRENT_BREACH",
                predicted_crossing_minutes=0,
                predicted_crossing_time=crossing_time_str,
                severity="CRITICAL",
                message=f"Current value ({current_val} {unit}) is actively breaching operational threshold ({operator} {effective_threshold} {unit}).",
                forecast=forecast_points,
            )

        # Check State 2: PREDICTED_BREACH along trajectory
        first_crossing_minutes = None
        crossing_time_str = None

        for pt in forecast_points:
            if self._is_breached(pt.value, effective_threshold, operator):
                first_crossing_minutes = pt.minutes_ahead
                crossing_time_str = pt.predicted_timestamp
                break

        if first_crossing_minutes is not None:
            if first_crossing_minutes <= self.critical_lead_minutes:
                severity = "CRITICAL"
                msg = f"Predicted threshold crossing in ~{first_crossing_minutes} min (Imminent / Critical)."
            else:
                severity = "WARNING"
                msg = f"Predicted threshold crossing in ~{first_crossing_minutes} min (Warning)."

            return MetricPredictionResult(
                metric=metric,
                unit=unit,
                current_value=round(current_val, 2),
                threshold_percentage=threshold_percentage,
                operational_limit=operational_limit,
                effective_threshold=effective_threshold,
                operator=operator,
                predicted_value_30m=predicted_val_30m,
                status="PREDICTED_BREACH",
                predicted_crossing_minutes=first_crossing_minutes,
                predicted_crossing_time=crossing_time_str,
                severity=severity,
                message=msg,
                forecast=forecast_points,
            )

        # State 3: NO_BREACH
        return MetricPredictionResult(
            metric=metric,
            unit=unit,
            current_value=round(current_val, 2),
            threshold_percentage=threshold_percentage,
            operational_limit=operational_limit,
            effective_threshold=effective_threshold,
            operator=operator,
            predicted_value_30m=predicted_val_30m,
            status="NO_BREACH",
            predicted_crossing_minutes=None,
            predicted_crossing_time=None,
            severity="NORMAL",
            message=f"Projected to stay within safe operational limits ({operator} {effective_threshold} {unit}) throughout 30m horizon.",
            forecast=forecast_points,
        )

    def evaluate_all(
        self,
        current_metrics: Dict[str, float],
        trajectories: Dict[str, List[Dict[str, Any]]],
        normalized_thresholds: Dict[str, Dict[str, Any]],
    ) -> Tuple[List[MetricPredictionResult], Optional[EarliestBreachInfo], str, str, int]:
        """
        Evaluate all metrics and compute overall system risk state:
        - NORMAL: 0 breaches
        - WARNING: breach projected in 16-30m
        - AT_RISK: breach projected in 0-15m
        - CRITICAL: current breach or multiple critical breaches
        """
        metric_results: List[MetricPredictionResult] = []
        earliest_cand: Optional[EarliestBreachInfo] = None
        earliest_minutes = float("inf")
        breaching_count = 0
        critical_count = 0
        warning_count = 0

        for metric, traj in trajectories.items():
            conf = normalized_thresholds.get(metric)
            if not conf:
                continue

            current_val = float(current_metrics.get(metric, 0.0))
            res = self.evaluate_metric(
                metric=metric,
                current_val=current_val,
                trajectory=traj,
                threshold_percentage=conf["threshold_percentage"],
                operational_limit=conf["operational_limit"],
                effective_threshold=conf["effective_threshold"],
                operator=conf["operator"],
                unit=conf.get("unit", ""),
            )
            metric_results.append(res)

            if res.status in ["CURRENT_BREACH", "PREDICTED_BREACH"]:
                breaching_count += 1
                if res.severity == "CRITICAL":
                    critical_count += 1
                elif res.severity == "WARNING":
                    warning_count += 1

                crossing_min = res.predicted_crossing_minutes or 0
                if crossing_min < earliest_minutes:
                    earliest_minutes = crossing_min
                    earliest_cand = EarliestBreachInfo(
                        metric=metric,
                        predicted_crossing_minutes=crossing_min,
                        predicted_crossing_time=res.predicted_crossing_time,
                        effective_threshold=res.effective_threshold,
                        current_value=res.current_value,
                        severity=res.severity,
                    )

        # Determine overall application status
        if critical_count > 0:
            if any(r.status == "CURRENT_BREACH" for r in metric_results) or critical_count >= 2:
                overall_status = "CRITICAL"
                summary = f"{breaching_count} of {len(metric_results)} metrics exceeding or immediately breaching thresholds."
            else:
                overall_status = "AT_RISK"
                summary = f"{breaching_count} metric(s) projected to breach thresholds within 15 minutes."
        elif warning_count > 0:
            overall_status = "WARNING"
            summary = f"{breaching_count} metric(s) projected to approach thresholds within 16-30 minutes."
        else:
            overall_status = "NORMAL"
            summary = f"All {len(metric_results)} monitored metrics projected within safe thresholds across the horizon."

        return metric_results, earliest_cand, overall_status, summary, breaching_count
