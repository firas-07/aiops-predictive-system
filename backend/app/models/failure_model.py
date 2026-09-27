from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.metrics import roc_auc_score, precision_score, recall_score, f1_score
from backend.app.core.logging import logger
from backend.app.core.config import settings

class ApplicationFailureClassifier:
    """
    Second-Stage ML Model:
    Predicts the probability of application degradation or failure within the upcoming horizon (e.g., 30-60 min).
    Trained strictly on engineered features available at time t to predict whether failure_event=1 occurs in [t+1, t+H].
    """

    def __init__(
        self,
        horizon_minutes: int = 30,
        model_version: str = "1.0.0"
    ):
        self.horizon_minutes = horizon_minutes
        self.model_version = model_version
        self.model: Optional[lgb.LGBMClassifier] = None
        self.feature_names: List[str] = []
        self.evaluation_summary: Dict[str, Any] = {}

    def prepare_target(self, df: pd.DataFrame) -> pd.Series:
        """
        Target: Is there ANY failure_event (1) in the upcoming horizon_minutes?
        y(t) = 1 if max(failure_event(t+1..t+H)) == 1 else 0
        """
        future_window = (
            df["failure_event"]
            .iloc[::-1]
            .rolling(window=self.horizon_minutes, min_periods=1)
            .max()
            .iloc[::-1]
            .shift(-1)
            .fillna(0)
            .astype(int)
        )
        return future_window

    def fit(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: Optional[pd.DataFrame] = None,
        y_val: Optional[pd.Series] = None
    ) -> Dict[str, Any]:
        logger.info(f"Training Application Failure Classifier on {len(X_train)} samples")
        self.feature_names = list(X_train.columns)

        scale_pos_weight = (len(y_train) - y_train.sum()) / max(1, y_train.sum())

        self.model = lgb.LGBMClassifier(
            n_estimators=120,
            learning_rate=0.05,
            num_leaves=31,
            scale_pos_weight=scale_pos_weight,
            random_state=settings.random_seed,
            verbosity=-1
        )

        if X_val is not None and y_val is not None:
            self.model.fit(
                X_train,
                y_train,
                eval_set=[(X_val, y_val)],
                callbacks=[lgb.early_stopping(stopping_rounds=15, verbose=False)]
            )
            val_probs = self.model.predict_proba(X_val)[:, 1]
            val_preds = (val_probs >= 0.5).astype(int)

            auc = float(roc_auc_score(y_val, val_probs)) if len(np.unique(y_val)) > 1 else 0.5
            precision = float(precision_score(y_val, val_preds, zero_division=0))
            recall = float(recall_score(y_val, val_preds, zero_division=0))
            f1 = float(f1_score(y_val, val_preds, zero_division=0))
        else:
            self.model.fit(X_train, y_train)
            auc, precision, recall, f1 = 0.5, 0.0, 0.0, 0.0

        self.evaluation_summary = {
            "horizon_minutes": self.horizon_minutes,
            "roc_auc": round(auc, 4),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
            "model_version": self.model_version
        }

        logger.info(f"Failure model trained: ROC-AUC={auc:.4f}, Precision={precision:.4f}, Recall={recall:.4f}")
        return self.evaluation_summary

    def predict_probability(self, X: pd.DataFrame) -> float:
        if self.model is None:
            raise ValueError("Failure classifier model is not trained.")
        X_in = X[self.feature_names]
        probs = self.model.predict_proba(X_in)
        return float(probs[-1, 1])

    def save(self, filepath: str | Path):
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        bundle = {
            "model_version": self.model_version,
            "horizon_minutes": self.horizon_minutes,
            "feature_names": self.feature_names,
            "model": self.model,
            "evaluation_summary": self.evaluation_summary
        }
        joblib.dump(bundle, path)
        logger.info(f"Saved failure classifier bundle to {path}")

    @classmethod
    def load(cls, filepath: str | Path) -> "ApplicationFailureClassifier":
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Failure model file not found: {path}")
        bundle = joblib.load(path)
        classifier = cls(
            horizon_minutes=bundle.get("horizon_minutes", 30),
            model_version=bundle.get("model_version", "1.0.0")
        )
        classifier.model = bundle["model"]
        classifier.feature_names = bundle["feature_names"]
        classifier.evaluation_summary = bundle.get("evaluation_summary", {})
        return classifier
