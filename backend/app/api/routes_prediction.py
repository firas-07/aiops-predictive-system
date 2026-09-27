from fastapi import APIRouter, HTTPException
from backend.app.core.logging import logger
from backend.app.schemas.prediction import PredictRequest, PredictResponse
from backend.app.forecasting.forecast_service import ForecastService

router = APIRouter(tags=["Prediction"])
forecast_service = ForecastService()

@router.post("/predict", response_model=PredictResponse)
def predict_metrics_and_thresholds(req: PredictRequest):
    """
    Generate multi-step future metric forecasts, predict time-to-threshold crossings,
    and compute second-stage degradation/failure probability.
    """
    try:
        response = forecast_service.predict(req)
        return response
    except ValueError as ve:
        logger.warning(f"Prediction validation error: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Unexpected prediction failure: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")
