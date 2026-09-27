from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import pandas as pd
from backend.app.core.logging import logger
from backend.app.core.config import settings
from backend.app.data.validator import DataValidator, DataValidationResult

class DataLoader:
    """
    DataLoader handles loading telemetry files from disk or upload streams,
    running validation, and ensuring standard column types.
    """

    @classmethod
    def load_from_csv(
        cls,
        file_path: str | Path,
        expected_interval_minutes: int = 1
    ) -> Tuple[pd.DataFrame, DataValidationResult]:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Telemetry file not found: {path}")

        logger.info(f"Loading telemetry dataset from: {path}")
        df = pd.read_csv(path)

        # Run validation
        validation_result = DataValidator.validate_dataset(
            df=df,
            expected_interval_minutes=expected_interval_minutes
        )

        if not validation_result.is_valid:
            error_msg = "; ".join(validation_result.errors)
            raise ValueError(f"Telemetry validation failed: {error_msg}")

        return df, validation_result

    @classmethod
    def save_to_parquet(cls, df: pd.DataFrame, target_path: str | Path) -> Path:
        target = Path(target_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Saving dataframe ({len(df)} rows) to parquet at: {target}")
        df.to_parquet(target, engine="pyarrow", index=False)
        return target

    @classmethod
    def load_from_parquet(cls, file_path: str | Path) -> pd.DataFrame:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Parquet file not found: {path}")
        return pd.read_parquet(path, engine="pyarrow")
