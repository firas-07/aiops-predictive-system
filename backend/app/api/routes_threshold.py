from typing import Dict, Any
from fastapi import APIRouter, HTTPException
from backend.app.core.config import settings, ThresholdSetting
from backend.app.schemas.threshold import ThresholdAnalysisRequest, ThresholdAnalysisResponse, ThresholdPrediction
from backend.app.threshold.threshold_engine import ThresholdEngine
from datetime import datetime

router = APIRouter(prefix="/threshold", tags=["Thresholds"])
threshold_engine = ThresholdEngine()

@router.get("/config")
def get_threshold_config():
    """Retrieve current operational threshold configurations."""
    return {
        "thresholds": {k: v.model_dump() for k, v in settings.thresholds.items()},
        "risk_rules": {
            "critical_minutes": settings.critical_minutes,
            "warning_minutes": settings.warning_minutes
        }
    }

@router.put("/config")
def update_threshold_config(updates: Dict[str, Dict[str, Any]]):
    """Update user-defined threshold limits and operators."""
    try:
        for metric, conf in updates.items():
            if metric in settings.thresholds:
                cur = settings.thresholds[metric]
                settings.thresholds[metric] = ThresholdSetting(
                    enabled=conf.get("enabled", cur.enabled),
                    operator=conf.get("operator", cur.operator),
                    value=float(conf.get("value", cur.value)),
                    unit=conf.get("unit", cur.unit),
                    critical_threshold=conf.get("critical_threshold", cur.critical_threshold)
                )
        return {
            "status": "success",
            "message": "Threshold configuration updated successfully.",
            "thresholds": {k: v.model_dump() for k, v in settings.thresholds.items()}
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to update thresholds: {str(e)}")

@router.post("/analyze", response_model=ThresholdAnalysisResponse)
def analyze_threshold_crossing(req: ThresholdAnalysisRequest):
    """
    Given a set of metric trajectories and current values, compute time-to-threshold
    and risk levels.
    """
    try:
        formatted_trajectories = {}
        for m, vals in req.metric_forecasts.items():
            pts = []
            for step, val in enumerate(vals, start=1):
                pts.append({
                    "step_minutes": step,
                    "predicted_timestamp": f"+{step}m",
                    "predicted_value": float(val)
                })
            formatted_trajectories[m] = pts

        preds, earliest, overall = threshold_engine.evaluate_trajectories(
            metric_forecasts=formatted_trajectories,
            current_metrics=req.current_metrics,
            threshold_configs=req.thresholds
        )

        return ThresholdAnalysisResponse(
            app_id=req.app_id,
            generated_at=datetime.utcnow().isoformat(),
            threshold_predictions=preds,
            earliest_threshold=earliest,
            overall_status=overall
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
