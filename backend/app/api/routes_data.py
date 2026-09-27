from typing import Optional
from pathlib import Path
import shutil
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
import pandas as pd
from backend.app.core.logging import logger
from backend.app.core.config import settings
from backend.app.data.loader import DataLoader
from backend.app.data.validator import DataValidator
from backend.app.data.analysis import TimeSeriesAnalyzer

router = APIRouter(prefix="/data", tags=["Data"])

@router.post("/upload")
async def upload_telemetry_csv(file: UploadFile = File(...)):
    """Upload new telemetry CSV and validate schema."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted.")

    temp_path = settings.raw_data_path.parent / f"uploaded_{file.filename}"
    temp_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Validate dataset
        df, val_res = DataLoader.load_from_csv(temp_path)
        
        # Replace default raw data path
        shutil.copyfile(temp_path, settings.raw_data_path)

        return {
            "status": "success",
            "message": f"Dataset {file.filename} uploaded and validated successfully.",
            "validation_report": val_res.quality_report
        }
    except Exception as e:
        logger.error(f"Error handling upload: {e}")
        if temp_path.exists():
            temp_path.unlink()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/summary")
def get_data_summary():
    """Return descriptive stats, correlation matrix, missing values, and ACF."""
    try:
        if settings.processed_data_path.exists():
            df = DataLoader.load_from_parquet(settings.processed_data_path)
        elif settings.raw_data_path.exists():
            df = pd.read_csv(settings.raw_data_path)
        else:
            raise HTTPException(status_code=404, detail="Dataset not found. Please upload or place dataset.")

        analyzer = TimeSeriesAnalyzer()
        summary = analyzer.compute_summary(df)
        return summary
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error computing data summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics")
def get_recent_metrics(
    limit: int = Query(500, ge=10, le=5000),
    app_id: Optional[str] = "chatgpt-azure-prod"
):
    """Return recent historical telemetry points for dashboard charting."""
    try:
        if settings.processed_data_path.exists():
            df = DataLoader.load_from_parquet(settings.processed_data_path)
        elif settings.raw_data_path.exists():
            df = pd.read_csv(settings.raw_data_path)
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        else:
            raise HTTPException(status_code=404, detail="Dataset not found.")

        if app_id and "app_id" in df.columns:
            df = df[df["app_id"] == app_id]

        recent_df = df.tail(limit).copy()
        recent_df["timestamp"] = recent_df["timestamp"].astype(str)
        
        cols = ["timestamp"] + [c for c in settings.target_metrics if c in recent_df.columns]
        if "app_status" in recent_df.columns:
            cols.append("app_status")
        if "failure_event" in recent_df.columns:
            cols.append("failure_event")

        return {
            "total_points": len(recent_df),
            "points": recent_df[cols].to_dict(orient="records")
        }
    except Exception as e:
        logger.error(f"Error fetching metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))
