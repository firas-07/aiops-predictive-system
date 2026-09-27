from fastapi import APIRouter, HTTPException
from backend.app.models.model_registry import ModelRegistry

router = APIRouter(prefix="/models", tags=["Models"])

@router.get("")
def list_models():
    """List all trained model versions and performance evaluations."""
    registry = ModelRegistry()
    versions = registry.get_all_versions()
    latest = registry.get_latest_version()
    
    return {
        "active_version": latest,
        "total_versions": len(versions),
        "versions": versions
    }
