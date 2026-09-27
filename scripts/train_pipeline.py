import sys
import os
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np

# Ensure backend package is in python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.core.logging import logger
from backend.app.core.config import settings
from backend.app.data.loader import DataLoader
from backend.app.data.preprocessing import TelemetryPreprocessor
from backend.app.features.feature_pipeline import FeaturePipeline
from backend.app.models.lightgbm_forecaster import MetricForecaster
from backend.app.models.failure_model import ApplicationFailureClassifier
from backend.app.models.evaluation import ModelEvaluator
from backend.app.models.model_registry import ModelRegistry

def run_training_pipeline(
    raw_csv_path: str = "data/raw/chatgpt_azure_synthetic_telemetry_50000.csv",
    version: str = "1.0.0",
    fast_mode: bool = False
):
    start_time = datetime.utcnow()
    logger.info("=" * 60)
    logger.info(f"STARTING AIOPS TRAINING PIPELINE (Version {version})")
    logger.info("=" * 60)

    # 1. Ingestion & Validation
    df_raw, val_result = DataLoader.load_from_csv(raw_csv_path)
    logger.info(f"Raw data loaded: {len(df_raw)} rows. Validation is_valid={val_result.is_valid}")

    # 2. Preprocessing
    preprocessor = TelemetryPreprocessor()
    df_clean, prep_summary = preprocessor.fit_transform(df_raw)
    
    # Save clean processed parquet
    DataLoader.save_to_parquet(df_clean, settings.processed_data_path)

    # Fast mode for quick testing/benchmarking if needed (use 20,000 rows)
    if fast_mode:
        logger.info("Fast mode enabled: using recent 20,000 rows for rapid training")
        df_clean = df_clean.tail(20000).reset_index(drop=True)

    # 3. Feature Engineering
    pipeline = FeaturePipeline()
    df_features, feature_cols = pipeline.fit_transform(df_clean)
    
    # Save features parquet
    DataLoader.save_to_parquet(df_features, settings.features_data_path)

    # 4. Chronological Train / Val / Test Split
    total_samples = len(df_features)
    train_end = int(total_samples * settings.train_split)
    val_end = int(total_samples * (settings.train_split + settings.val_split))

    logger.info(f"Dataset split chronologically: Train=[0:{train_end}], Val=[{train_end}:{val_end}], Test=[{val_end}:{total_samples}]")

    train_df = df_features.iloc[:train_end]
    val_df = df_features.iloc[train_end:val_end]
    test_df = df_features.iloc[val_end:]

    X_train = train_df[feature_cols]
    X_val = val_df[feature_cols]
    X_test = test_df[feature_cols]

    forecasters = {}
    evaluations = {}

    # 5. Train LightGBM Forecaster for each target metric (1-step model for recursive forecasting)
    for metric in settings.target_metrics:
        logger.info(f"--- Training Forecaster for: {metric} ---")
        
        # Target is metric at t+1
        y_train = train_df[metric].shift(-1).iloc[:-1]
        X_train_m = X_train.iloc[:-1]

        y_val = val_df[metric].shift(-1).iloc[:-1]
        X_val_m = X_val.iloc[:-1]

        y_test = test_df[metric].shift(-1).iloc[:-1]
        X_test_m = X_test.iloc[:-1]

        forecaster = MetricForecaster(metric=metric, model_version=version)
        forecaster.fit(
            X_train=X_train_m,
            y_train=y_train,
            X_val=X_val_m,
            y_val=y_val
        )

        # Evaluate on held-out test set
        test_preds = forecaster.predict(X_test_m)
        baseline_test_preds = X_test_m[metric].to_numpy()

        lgb_test_metrics = ModelEvaluator.calculate_regression_metrics(y_test.to_numpy(), test_preds)
        base_test_metrics = ModelEvaluator.calculate_regression_metrics(y_test.to_numpy(), baseline_test_preds)

        improvement = 0.0
        if base_test_metrics["mae"] > 0:
            improvement = round(((base_test_metrics["mae"] - lgb_test_metrics["mae"]) / base_test_metrics["mae"]) * 100.0, 2)

        # Operational threshold evaluation on test set
        thresh_val = settings.thresholds[metric].value if metric in settings.thresholds else 90.0
        thresh_op = settings.thresholds[metric].operator if metric in settings.thresholds else ">"
        
        # Test operational metric over chunks
        op_metrics = ModelEvaluator.calculate_threshold_operational_metrics(
            actual_trajectories=[y_test.to_numpy()[i:i+30] for i in range(0, min(1000, len(y_test)-30), 30)],
            predicted_trajectories=[test_preds[i:i+30] for i in range(0, min(1000, len(test_preds)-30), 30)],
            threshold=thresh_val,
            operator=thresh_op
        )

        forecasters[metric] = forecaster
        evaluations[metric] = {
            "metric": metric,
            "baseline_mae": base_test_metrics["mae"],
            "baseline_rmse": base_test_metrics["rmse"],
            "lightgbm_mae": lgb_test_metrics["mae"],
            "lightgbm_rmse": lgb_test_metrics["rmse"],
            "lightgbm_mape": lgb_test_metrics["mape"],
            "improvement_vs_baseline_pct": improvement,
            "threshold_crossing_accuracy": op_metrics["accuracy"],
            "mean_time_to_threshold_error_min": op_metrics["mean_time_to_threshold_error_min"],
            "false_early_warning_rate": op_metrics["false_early_warning_rate"],
            "missed_threshold_rate": op_metrics["missed_threshold_rate"]
        }

    # 6. Train Second-Stage Failure Classifier
    logger.info("--- Training Second-Stage Application Failure Classifier ---")
    failure_classifier = ApplicationFailureClassifier(horizon_minutes=30, model_version=version)
    
    if "failure_event" in df_clean.columns:
        # Prepare targets
        y_fail_all = failure_classifier.prepare_target(df_features)
        y_fail_train = y_fail_all.iloc[:train_end]
        y_fail_val = y_fail_all.iloc[train_end:val_end]
        y_fail_test = y_fail_all.iloc[val_end:]

        failure_eval = failure_classifier.fit(
            X_train=X_train,
            y_train=y_fail_train,
            X_val=X_val,
            y_val=y_fail_val
        )
    else:
        failure_classifier = None
        failure_eval = None

    # 7. Save Model Suite to Registry
    registry = ModelRegistry()
    registry.save_model_suite(
        version=version,
        forecasters=forecasters,
        failure_model=failure_classifier,
        feature_pipeline=pipeline,
        training_rows=len(train_df),
        val_rows=len(val_df),
        test_rows=len(test_df),
        evaluations=evaluations
    )

    elapsed = (datetime.utcnow() - start_time).total_seconds()
    logger.info(f"AIOps Training Pipeline completed in {elapsed:.1f}s.")
    return evaluations, failure_eval

if __name__ == "__main__":
    raw_path = sys.argv[1] if len(sys.argv) > 1 else "data/raw/chatgpt_azure_synthetic_telemetry_50000.csv"
    run_training_pipeline(raw_csv_path=raw_path, version="1.0.0", fast_mode=False)
