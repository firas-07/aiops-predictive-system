from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import json
from datetime import datetime
from backend.app.core.logging import logger
from backend.app.core.config import settings
from backend.app.models.lightgbm_forecaster import MetricForecaster
from backend.app.models.failure_model import ApplicationFailureClassifier
from backend.app.features.feature_pipeline import FeaturePipeline

class ModelRegistry:
    """
    Manages persistence, metadata tracking, and retrieval of trained forecasters
    and failure models.
    """

    def __init__(self, models_dir: Optional[str | Path] = None):
        self.models_dir = Path(models_dir or settings.models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.models_dir / "registry_metadata.json"

    def save_model_suite(
        self,
        version: str,
        forecasters: Dict[str, MetricForecaster],
        failure_model: Optional[ApplicationFailureClassifier],
        feature_pipeline: FeaturePipeline,
        training_rows: int,
        val_rows: int,
        test_rows: int,
        evaluations: Dict[str, Any]
    ):
        version_dir = self.models_dir / version
        version_dir.mkdir(parents=True, exist_ok=True)

        # 1. Save each metric forecaster
        for metric, forecaster in forecasters.items():
            model_path = version_dir / f"forecaster_{metric}.joblib"
            forecaster.save(model_path)

        # 2. Save failure model if provided
        if failure_model is not None:
            failure_model_path = version_dir / "failure_classifier.joblib"
            failure_model.save(failure_model_path)

        # 3. Save feature pipeline configuration
        feat_config_path = version_dir / "feature_pipeline_config.json"
        feature_pipeline.save_feature_config(feat_config_path)

        # 4. Save version metadata
        meta = {
            "model_version": version,
            "trained_at": datetime.utcnow().isoformat(),
            "training_rows": training_rows,
            "validation_rows": val_rows,
            "test_rows": test_rows,
            "metrics": list(forecasters.keys()),
            "has_failure_model": failure_model is not None,
            "evaluations": evaluations,
            "is_active": True
        }

        with open(version_dir / "metadata.json", "w") as f:
            json.dump(meta, f, indent=2)

        # Update registry manifest
        self._update_manifest(version, meta)
        logger.info(f"Model suite version {version} saved and registered successfully.")

    def _update_manifest(self, version: str, meta: Dict[str, Any]):
        manifest = self.get_all_versions()
        manifest[version] = meta
        with open(self.metadata_file, "w") as f:
            json.dump(manifest, f, indent=2)

    def get_all_versions(self) -> Dict[str, Any]:
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, "r") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def get_latest_version(self) -> Optional[str]:
        versions = self.get_all_versions()
        if not versions:
            # Check subdirectories
            subdirs = [d.name for d in self.models_dir.iterdir() if d.is_dir() and (d / "metadata.json").exists()]
            return sorted(subdirs)[-1] if subdirs else None
        return sorted(versions.keys())[-1]

    def load_model_suite(
        self,
        version: Optional[str] = None
    ) -> Tuple[Dict[str, MetricForecaster], Optional[ApplicationFailureClassifier], FeaturePipeline, Dict[str, Any]]:
        ver = version or self.get_latest_version()
        if not ver:
            raise FileNotFoundError("No trained models found in registry. Please train models first.")

        version_dir = self.models_dir / ver
        if not version_dir.exists():
            raise FileNotFoundError(f"Model version {ver} not found at {version_dir}")

        # Load metadata
        with open(version_dir / "metadata.json", "r") as f:
            meta = json.load(f)

        # Load feature pipeline
        pipeline = FeaturePipeline()
        pipeline.load_feature_config(version_dir / "feature_pipeline_config.json")

        # Load forecasters
        forecasters: Dict[str, MetricForecaster] = {}
        for metric in meta["metrics"]:
            m_path = version_dir / f"forecaster_{metric}.joblib"
            forecasters[metric] = MetricForecaster.load(m_path)

        # Load failure model
        failure_model = None
        f_path = version_dir / "failure_classifier.joblib"
        if f_path.exists():
            failure_model = ApplicationFailureClassifier.load(f_path)

        logger.info(f"Successfully loaded model suite version {ver}")
        return forecasters, failure_model, pipeline, meta
