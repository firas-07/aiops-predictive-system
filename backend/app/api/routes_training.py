import asyncio
from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter, HTTPException, BackgroundTasks
from backend.app.core.logging import logger
from backend.app.core.config import settings
from backend.app.models.model_registry import ModelRegistry
from backend.app.schemas.training import TrainRequest, TrainResponse, MetricEvaluation
from scripts.train_pipeline import run_training_pipeline

router = APIRouter(prefix="/training", tags=["Training"])

# Global training execution state tracker
training_state = {
    "is_training": False,
    "last_run": None,
    "last_status": "idle",
    "progress_message": "Ready to train",
    "last_result": None
}

executor = ThreadPoolExecutor(max_workers=1)

def _run_train_worker(raw_path: str, fast_mode: bool):
    global training_state
    try:
        training_state["is_training"] = True
        training_state["progress_message"] = "Training in progress..."
        training_state["last_status"] = "running"

        evals, failure_eval = run_training_pipeline(
            raw_csv_path=raw_path,
            version="1.0.0",
            fast_mode=fast_mode
        )

        training_state["is_training"] = False
        training_state["last_status"] = "completed"
        training_state["progress_message"] = "Training finished successfully."
        training_state["last_result"] = {
            "evaluations": evals,
            "failure_eval": failure_eval
        }
    except Exception as e:
        logger.error(f"Background training failed: {e}")
        training_state["is_training"] = False
        training_state["last_status"] = "failed"
        training_state["progress_message"] = f"Training failed: {str(e)}"

@router.post("/train", response_model=TrainResponse)
def trigger_training(req: TrainRequest, background_tasks: BackgroundTasks):
    """Trigger training pipeline synchronously or asynchronously."""
    global training_state
    if training_state["is_training"]:
        raise HTTPException(status_code=409, detail="A training job is already in progress.")

    raw_path = req.data_path or str(settings.raw_data_path)

    # For fast turnaround in UI or test, run in executor
    try:
        evals, failure_eval = run_training_pipeline(
            raw_csv_path=raw_path,
            version="1.0.0",
            fast_mode=req.fast_mode
        )
        registry = ModelRegistry()
        meta = registry.get_all_versions().get("1.0.0", {})

        return TrainResponse(
            status="completed",
            message="Training pipeline finished successfully.",
            model_version="1.0.0",
            trained_at=meta.get("trained_at", ""),
            training_rows=meta.get("training_rows", 0),
            validation_rows=meta.get("validation_rows", 0),
            test_rows=meta.get("test_rows", 0),
            target_metrics=list(evals.keys()),
            evaluations={k: MetricEvaluation(**v) for k, v in evals.items()},
            failure_model_evaluation=failure_eval
        )
    except Exception as e:
        logger.error(f"Training failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
def get_training_status():
    """Check current background training progress and status."""
    return training_state
