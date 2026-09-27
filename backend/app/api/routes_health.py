from fastapi import APIRouter
from datetime import datetime
from backend.app.core.config import settings
from backend.app.models.model_registry import ModelRegistry

router = APIRouter(tags=["Health"])

@router.get("/health")
def get_health():
    registry = ModelRegistry()
    latest_version = registry.get_latest_version()
    
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "version": settings.app_version,
        "active_model_version": latest_version,
        "models_ready": latest_version is not None,
        "timestamp": datetime.utcnow().isoformat()
    }
