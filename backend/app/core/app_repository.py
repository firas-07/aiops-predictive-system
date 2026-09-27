from typing import Dict, List, Optional, Any
from pathlib import Path
import json
from datetime import datetime
from backend.app.core.logging import logger
from backend.app.core.config import settings
from backend.app.schemas.application import (
    MetricThresholdConfig,
    AzureConnectionConfig,
    ApplicationCreateRequest,
    ApplicationUpdateRequest,
    ApplicationResponse,
)

def get_default_thresholds() -> Dict[str, MetricThresholdConfig]:
    """Default operational limits and percentage thresholds for all 8 metrics."""
    return {
        "cpu_percent": MetricThresholdConfig(
            metric="cpu_percent",
            threshold_percentage=80.0,
            operational_limit=100.0,
            operator=">=",
            unit="%",
            enabled=True,
        ),
        "memory_percent": MetricThresholdConfig(
            metric="memory_percent",
            threshold_percentage=85.0,
            operational_limit=100.0,
            operator=">=",
            unit="%",
            enabled=True,
        ),
        "disk_io_mb_s": MetricThresholdConfig(
            metric="disk_io_mb_s",
            threshold_percentage=80.0,
            operational_limit=80.0,
            operator=">=",
            unit="MB/s",
            enabled=True,
        ),
        "latency_ms": MetricThresholdConfig(
            metric="latency_ms",
            threshold_percentage=80.0,
            operational_limit=500.0,
            operator=">=",
            unit="ms",
            enabled=True,
        ),
        "http_errors": MetricThresholdConfig(
            metric="http_errors",
            threshold_percentage=80.0,
            operational_limit=50.0,
            operator=">=",
            unit="count/min",
            enabled=True,
        ),
        "http_success": MetricThresholdConfig(
            metric="http_success",
            threshold_percentage=30.0,
            operational_limit=3500.0,
            operator="<=",
            unit="req/min",
            enabled=True,
        ),
        "network_mb_s": MetricThresholdConfig(
            metric="network_mb_s",
            threshold_percentage=80.0,
            operational_limit=70.0,
            operator=">=",
            unit="MB/s",
            enabled=True,
        ),
        "request_volume": MetricThresholdConfig(
            metric="request_volume",
            threshold_percentage=90.0,
            operational_limit=4000.0,
            operator=">=",
            unit="req/min",
            enabled=True,
        ),
    }

class ApplicationRepository:
    """
    Manages application definitions, Azure credentials, and threshold configurations.
    Masks secrets when returning data to prevent credential leakage.
    """

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or (settings.base_dir / "data" / "applications.json")
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._apps: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self):
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r") as f:
                    self._apps = json.load(f)
            except Exception as e:
                logger.error(f"Error reading applications storage: {e}")
                self._apps = {}

        # If empty, initialize default application
        if not self._apps:
            default_app_id = "chatgpt-azure-prod"
            default_app = {
                "id": default_app_id,
                "name": "ChatGPT Azure Prod (Default)",
                "telemetry_source": "csv",
                "csv_file_path": str(settings.raw_data_path),
                "azure_config": {
                    "tenant_id": "",
                    "client_id": "",
                    "client_secret": "",
                    "subscription_id": "",
                    "resource_group": "",
                    "resource_name": "chatgpt-prod-insights",
                    "telemetry_service": "azure_monitor",
                },
                "thresholds": {k: v.model_dump() for k, v in get_default_thresholds().items()},
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }
            self._apps[default_app_id] = default_app
            self._save()

    def _save(self):
        try:
            with open(self.storage_path, "w") as f:
                json.dump(self._apps, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving applications: {e}")

    def list_applications(self) -> List[ApplicationResponse]:
        results = []
        for app in self._apps.values():
            results.append(self._to_response(app))
        return results

    def get_application(self, app_id: str) -> Optional[ApplicationResponse]:
        app = self._apps.get(app_id)
        if not app:
            return None
        return self._to_response(app)

    def get_raw_application(self, app_id: str) -> Optional[Dict[str, Any]]:
        """Internal access containing real credentials for Azure provider only."""
        return self._apps.get(app_id)

    def create_application(self, req: ApplicationCreateRequest) -> ApplicationResponse:
        now = datetime.utcnow().isoformat()
        
        # Merge provided thresholds with defaults
        thresholds_dict = {k: v.model_dump() for k, v in get_default_thresholds().items()}
        if req.thresholds:
            for k, v in req.thresholds.items():
                thresholds_dict[k] = v.model_dump()

        azure_cfg = req.azure_config.model_dump() if req.azure_config else {}

        app_data = {
            "id": req.id,
            "name": req.name,
            "telemetry_source": req.telemetry_source,
            "azure_config": azure_cfg,
            "csv_file_path": req.csv_file_path or str(settings.raw_data_path),
            "thresholds": thresholds_dict,
            "created_at": now,
            "updated_at": now,
        }

        self._apps[req.id] = app_data
        self._save()
        logger.info(f"Registered new application: id={req.id}, source={req.telemetry_source}")
        return self._to_response(app_data)

    def update_application(self, app_id: str, req: ApplicationUpdateRequest) -> Optional[ApplicationResponse]:
        app = self._apps.get(app_id)
        if not app:
            return None

        if req.name is not None:
            app["name"] = req.name
        if req.telemetry_source is not None:
            app["telemetry_source"] = req.telemetry_source
        if req.csv_file_path is not None:
            app["csv_file_path"] = req.csv_file_path
        if req.azure_config is not None:
            # Preserve existing secret if not provided in update
            new_az = req.azure_config.model_dump()
            if not new_az.get("client_secret") and app.get("azure_config", {}).get("client_secret"):
                new_az["client_secret"] = app["azure_config"]["client_secret"]
            app["azure_config"] = new_az
        if req.thresholds is not None:
            for k, v in req.thresholds.items():
                app["thresholds"][k] = v.model_dump()

        app["updated_at"] = datetime.utcnow().isoformat()
        self._apps[app_id] = app
        self._save()
        return self._to_response(app)

    def update_thresholds(self, app_id: str, thresholds: Dict[str, MetricThresholdConfig]) -> Optional[Dict[str, MetricThresholdConfig]]:
        app = self._apps.get(app_id)
        if not app:
            return None

        for k, v in thresholds.items():
            app["thresholds"][k] = v.model_dump()

        app["updated_at"] = datetime.utcnow().isoformat()
        self._apps[app_id] = app
        self._save()
        return {k: MetricThresholdConfig(**v) for k, v in app["thresholds"].items()}

    def delete_application(self, app_id: str) -> bool:
        if app_id in self._apps:
            del self._apps[app_id]
            self._save()
            return True
        return False

    def _to_response(self, app: Dict[str, Any]) -> ApplicationResponse:
        """Mask client secrets to prevent credential leakage."""
        az_cfg = app.get("azure_config", {}).copy() if app.get("azure_config") else None
        if az_cfg and az_cfg.get("client_secret"):
            az_cfg["client_secret"] = "••••••••"  # Masked!

        thresholds = {
            k: MetricThresholdConfig(**v) for k, v in app.get("thresholds", {}).items()
        }

        return ApplicationResponse(
            id=app["id"],
            name=app["name"],
            telemetry_source=app.get("telemetry_source", "csv"),
            azure_config=az_cfg,
            csv_file_path=app.get("csv_file_path"),
            thresholds=thresholds,
            created_at=app.get("created_at", ""),
            updated_at=app.get("updated_at", ""),
            is_connected=True,
            last_telemetry_timestamp=None,
        )

app_repo = ApplicationRepository()
