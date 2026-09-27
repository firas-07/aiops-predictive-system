from typing import List, Dict, Optional
from fastapi import APIRouter, HTTPException, Query
from backend.app.core.logging import logger
from backend.app.core.app_repository import app_repo
from backend.app.data.telemetry_provider import get_telemetry_provider
from backend.app.forecasting.realtime_service import realtime_service
from backend.app.schemas.application import (
    ApplicationCreateRequest,
    ApplicationUpdateRequest,
    ApplicationResponse,
    MetricThresholdConfig,
    RealtimePredictionRequest,
    RealtimePredictionResponse,
)

router = APIRouter(prefix="/applications", tags=["Applications & Real-time Predictions"])

@router.post("", response_model=ApplicationResponse, status_code=201)
def create_application(req: ApplicationCreateRequest):
    """Register a new application with telemetry source (CSV or Azure) and thresholds."""
    if app_repo.get_application(req.id):
        raise HTTPException(status_code=409, detail=f"Application with ID '{req.id}' already exists.")
    try:
        return app_repo.create_application(req)
    except Exception as e:
        logger.error(f"Error creating application: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("", response_model=List[ApplicationResponse])
def list_applications():
    """List all registered applications with masked Azure secrets."""
    return app_repo.list_applications()

@router.get("/{app_id}", response_model=ApplicationResponse)
def get_application(app_id: str):
    """Get single application details."""
    app = app_repo.get_application(app_id)
    if not app:
        raise HTTPException(status_code=404, detail=f"Application '{app_id}' not found.")
    return app

@router.put("/{app_id}", response_model=ApplicationResponse)
def update_application(app_id: str, req: ApplicationUpdateRequest):
    """Update application connection details or thresholds."""
    updated = app_repo.update_application(app_id, req)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Application '{app_id}' not found.")
    return updated

@router.delete("/{app_id}")
def delete_application(app_id: str):
    """Remove application configuration."""
    success = app_repo.delete_application(app_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Application '{app_id}' not found.")
    return {"status": "success", "message": f"Application '{app_id}' deleted."}

@router.get("/{app_id}/telemetry")
def get_application_telemetry(
    app_id: str,
    limit: int = Query(75, ge=10, le=500, description="Telemetry window points (minutes)")
):
    """Fetch recent telemetry observations directly from configured telemetry provider."""
    raw_app = app_repo.get_raw_application(app_id)
    if not raw_app:
        raise HTTPException(status_code=404, detail=f"Application '{app_id}' not found.")
    try:
        provider = get_telemetry_provider(raw_app)
        df = provider.get_recent_window(app_id=app_id, minutes=limit)
        df["timestamp"] = df["timestamp"].astype(str)
        return {
            "app_id": app_id,
            "telemetry_source": raw_app.get("telemetry_source", "csv"),
            "total_points": len(df),
            "points": df.to_dict(orient="records"),
        }
    except Exception as e:
        logger.error(f"Error retrieving telemetry for {app_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{app_id}/telemetry/latest")
def get_latest_telemetry(app_id: str):
    """Get the single latest telemetry observation for the application."""
    raw_app = app_repo.get_raw_application(app_id)
    if not raw_app:
        raise HTTPException(status_code=404, detail=f"Application '{app_id}' not found.")
    try:
        provider = get_telemetry_provider(raw_app)
        latest = provider.get_latest_metrics(app_id=app_id)
        if "timestamp" in latest:
            latest["timestamp"] = str(latest["timestamp"])
        return {
            "app_id": app_id,
            "telemetry_source": raw_app.get("telemetry_source", "csv"),
            "latest_metrics": latest
        }
    except Exception as e:
        logger.error(f"Error retrieving latest telemetry for {app_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{app_id}/thresholds", response_model=Dict[str, MetricThresholdConfig])
def get_thresholds(app_id: str):
    """Get configured percentage thresholds and operational limits for an application."""
    app = app_repo.get_application(app_id)
    if not app:
        raise HTTPException(status_code=404, detail=f"Application '{app_id}' not found.")
    return app.thresholds

@router.put("/{app_id}/thresholds", response_model=Dict[str, MetricThresholdConfig])
@router.post("/{app_id}/thresholds", response_model=Dict[str, MetricThresholdConfig])
def update_thresholds(app_id: str, thresholds: Dict[str, MetricThresholdConfig]):
    """Update percentage thresholds and operational limits."""
    updated = app_repo.update_thresholds(app_id, thresholds)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Application '{app_id}' not found.")
    return updated

@router.post("/{app_id}/predict", response_model=RealtimePredictionResponse)
def predict_realtime_for_application(
    app_id: str,
    req: RealtimePredictionRequest = RealtimePredictionRequest(horizon_minutes=30)
):
    """
    Real-time Production Prediction Endpoint:
    1. Obtains latest telemetry window from configured provider (CSV or Azure)
    2. Runs the 8 LightGBM models for the 30-minute horizon
    3. Normalizes percentage thresholds to effective units
    4. Evaluates threshold crossings, time-to-threshold, and generates alerts
    """
    try:
        response = realtime_service.predict_for_application(
            app_id=app_id,
            horizon_minutes=req.horizon_minutes
        )
        return response
    except ValueError as ve:
        logger.warning(f"Prediction validation issue: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Prediction error on {app_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
