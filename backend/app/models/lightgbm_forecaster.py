from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import lightgbm as lgb
from backend.app.core.logging import logger
from backend.app.core.config import settings
from backend.app.models.baseline import NaiveBaselineForecaster
from backend.app.models.evaluation import ModelEvaluator

class MetricForecaster:
    """
    Forecasting model for a single metric using LightGBM Regressor.
    Supports chronological validation, residual error estimation for confidence bounds,
    and comparison against the naive baseline forecaster.
    """

    def __init__(
        self,
        metric: str,
        params: Optional[Dict[str, Any]] = None,
        model_version: str = "1.0.0"
    ):
        self.metric = metric
        self.model_version = model_version
        self.params = params or settings.lightgbm_params
        self.model: Optional[lgb.LGBMRegressor] = None
        self.baseline = NaiveBaselineForecaster(metric=metric)
        self.feature_names: List[str] = []
        self.residual_std: float = 0.0
        self.evaluation_summary: Dict[str, Any] = {}

    def fit(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: Optional[pd.DataFrame] = None,
        y_val: Optional[pd.Series] = None
    ) -> Dict[str, Any]:
        logger.info(f"Training LightGBM forecaster for metric: {self.metric} on {len(X_train)} samples")
        self.feature_names = list(X_train.columns)

        # Baseline evaluation on validation set
        latest_val = X_val[self.metric] if (X_val is not None and self.metric in X_val.columns) else None
        baseline_mae, baseline_rmse = 0.0, 0.0
        if latest_val is not None and y_val is not None:
            baseline_preds = latest_val.to_numpy()
            base_res = ModelEvaluator.calculate_regression_metrics(y_val.to_numpy(), baseline_preds)
            baseline_mae, baseline_rmse = base_res["mae"], base_res["rmse"]

        # Configure LightGBM Regressor
        clean_params = {k: v for k, v in self.params.items() if k not in ["random_seed"]}
        clean_params["random_state"] = settings.random_seed
        clean_params["verbosity"] = -1
        
        self.model = lgb.LGBMRegressor(**clean_params)

        if X_val is not None and y_val is not None:
            self.model.fit(
                X_train,
                y_train,
                eval_set=[(X_val, y_val)],
                callbacks=[lgb.early_stopping(stopping_rounds=15, verbose=False)]
            )
            val_preds = self.model.predict(X_val)
            lgb_res = ModelEvaluator.calculate_regression_metrics(y_val.to_numpy(), val_preds)
            
            # Compute empirical residual standard deviation for confidence intervals
            residuals = y_val.to_numpy() - val_preds
            self.residual_std = float(np.std(residuals))
        else:
            self.model.fit(X_train, y_train)
            lgb_res = {"mae": 0.0, "rmse": 0.0, "mape": None}
            self.residual_std = 1.0

        improvement = 0.0
        if baseline_mae > 0:
            improvement = round(((baseline_mae - lgb_res["mae"]) / baseline_mae) * 100.0, 2)

        self.evaluation_summary = {
            "metric": self.metric,
            "baseline_mae": baseline_mae,
            "baseline_rmse": baseline_rmse,
            "lightgbm_mae": lgb_res["mae"],
            "lightgbm_rmse": lgb_res["rmse"],
            "lightgbm_mape": lgb_res["mape"],
            "improvement_vs_baseline_pct": improvement,
            "residual_std": round(self.residual_std, 4)
        }

        logger.info(
            f"Metric {self.metric} trained: LGB MAE={lgb_res['mae']} vs Baseline MAE={baseline_mae} "
            f"(Improvement: {improvement}%)"
        )
        return self.evaluation_summary

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if self.model is None:
            raise ValueError(f"Model for {self.metric} is not trained.")
        X_in = X[self.feature_names]
        preds = self.model.predict(X_in)
        # Apply physical lower bound constraint
        preds = np.clip(preds, a_min=0.0, a_max=100.0 if "percent" in self.metric else None)
        return preds

    def save(self, filepath: str | Path):
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        bundle = {
            "metric": self.metric,
            "model_version": self.model_version,
            "params": self.params,
            "feature_names": self.feature_names,
            "model": self.model,
            "residual_std": self.residual_std,
            "evaluation_summary": self.evaluation_summary
        }
        joblib.dump(bundle, path)
        logger.info(f"Saved {self.metric} forecaster bundle to {path}")

    @classmethod
    def load(cls, filepath: str | Path) -> "MetricForecaster":
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Model file not found: {path}")
        bundle = joblib.load(path)
        forecaster = cls(
            metric=bundle["metric"],
            params=bundle["params"],
            model_version=bundle.get("model_version", "1.0.0")
        )
        forecaster.model = bundle["model"]
        forecaster.feature_names = bundle["feature_names"]
        forecaster.residual_std = bundle.get("residual_std", 1.0)
        forecaster.evaluation_summary = bundle.get("evaluation_summary", {})
        return forecaster
