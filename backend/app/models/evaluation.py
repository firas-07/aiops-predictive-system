from typing import Dict, List, Optional, Tuple, Any
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error

class ModelEvaluator:
    """
    Computes standard regression metrics (MAE, RMSE, MAPE)
    and operational threshold-specific time-series metrics:
    - Threshold crossing detection accuracy
    - Mean absolute time-to-threshold error (minutes)
    - False early warning rate
    - Missed threshold rate
    """

    @staticmethod
    def calculate_regression_metrics(
        y_true: np.ndarray,
        y_pred: np.ndarray
    ) -> Dict[str, float]:
        y_true = np.asarray(y_true, dtype=float)
        y_pred = np.asarray(y_pred, dtype=float)

        mae = float(mean_absolute_error(y_true, y_pred))
        rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))

        # Robust MAPE (avoid division by near-zero)
        non_zero_mask = np.abs(y_true) > 1e-3
        if np.sum(non_zero_mask) > 0:
            mape = float(np.mean(np.abs((y_true[non_zero_mask] - y_pred[non_zero_mask]) / y_true[non_zero_mask])) * 100.0)
            mape = round(min(mape, 1000.0), 2)
        else:
            mape = None

        return {
            "mae": round(mae, 4),
            "rmse": round(rmse, 4),
            "mape": mape
        }

    @staticmethod
    def calculate_threshold_operational_metrics(
        actual_trajectories: List[np.ndarray],
        predicted_trajectories: List[np.ndarray],
        threshold: float,
        operator: str = ">"
    ) -> Dict[str, Any]:
        """
        Evaluate threshold-crossing predictions:
        Did the actual trajectory cross the threshold?
        Did the predicted trajectory cross the threshold?
        What was the difference in crossing time?
        """
        tp = 0  # Both crossed
        fp = 0  # Predicted crossed, actual did not (False Early Warning)
        fn = 0  # Actual crossed, predicted did not (Missed Warning)
        tn = 0  # Neither crossed

        time_errors = []

        for actual, pred in zip(actual_trajectories, predicted_trajectories):
            actual_crossing = None
            pred_crossing = None

            for t, val in enumerate(actual):
                if (operator == ">" and val > threshold) or (operator == "<" and val < threshold):
                    actual_crossing = t + 1
                    break

            for t, val in enumerate(pred):
                if (operator == ">" and val > threshold) or (operator == "<" and val < threshold):
                    pred_crossing = t + 1
                    break

            if actual_crossing is not None and pred_crossing is not None:
                tp += 1
                time_errors.append(abs(actual_crossing - pred_crossing))
            elif actual_crossing is None and pred_crossing is not None:
                fp += 1
            elif actual_crossing is not None and pred_crossing is None:
                fn += 1
            else:
                tn += 1

        total = max(1, tp + fp + fn + tn)
        accuracy = round((tp + tn) / total, 4)
        false_early_warning_rate = round(fp / max(1, fp + tn), 4)
        missed_threshold_rate = round(fn / max(1, fn + tp), 4)
        mean_time_error = round(float(np.mean(time_errors)), 2) if time_errors else None

        return {
            "threshold": threshold,
            "operator": operator,
            "accuracy": accuracy,
            "mean_time_to_threshold_error_min": mean_time_error,
            "false_early_warning_rate": false_early_warning_rate,
            "missed_threshold_rate": missed_threshold_rate,
            "eval_cases_analyzed": len(actual_trajectories)
        }
