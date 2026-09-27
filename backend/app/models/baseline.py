from typing import Dict, List, Optional
import numpy as np
import pandas as pd

class NaiveBaselineForecaster:
    """
    Naive persistence baseline forecaster:
    Predicts that future metric value at t + h equals the latest observed value at time t.
    y_hat(t + h) = y(t)
    """

    def __init__(self, metric: str):
        self.metric = metric
        self.is_fitted = True

    def fit(self, X: pd.DataFrame, y: pd.Series):
        # Persistence model needs no parameter optimization
        self.is_fitted = True
        return self

    def predict_horizon(self, latest_value: float, horizon_minutes: int) -> np.ndarray:
        return np.full(shape=(horizon_minutes,), fill_value=latest_value, dtype=float)

    def predict_direct(self, latest_series: pd.Series, horizon_minutes: int = 1) -> np.ndarray:
        return latest_series.to_numpy(dtype=float)
