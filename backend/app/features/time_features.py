import numpy as np
import pandas as pd

def add_time_features(df: pd.DataFrame, timestamp_col: str = "timestamp") -> pd.DataFrame:
    """
    Extract calendar and cyclical time features from datetime series.
    Adds hour, day_of_week, day_of_month, is_weekend, and cyclical sin/cos encodings.
    """
    df_out = df.copy()
    ts = pd.to_datetime(df_out[timestamp_col], utc=True)

    df_out["hour"] = ts.dt.hour
    df_out["day_of_week"] = ts.dt.dayofweek
    df_out["day_of_month"] = ts.dt.day
    df_out["is_weekend"] = ts.dt.dayofweek.isin([5, 6]).astype(int)

    # Cyclical hour encoding (24 hours in a day)
    df_out["sin_hour"] = np.sin(2 * np.pi * df_out["hour"] / 24.0)
    df_out["cos_hour"] = np.cos(2 * np.pi * df_out["hour"] / 24.0)

    # Cyclical day of week encoding (7 days in a week)
    df_out["sin_day_of_week"] = np.sin(2 * np.pi * df_out["day_of_week"] / 7.0)
    df_out["cos_day_of_week"] = np.cos(2 * np.pi * df_out["day_of_week"] / 7.0)

    return df_out
