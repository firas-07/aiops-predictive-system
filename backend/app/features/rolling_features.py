from typing import List
import numpy as np
import pandas as pd

def add_rolling_features(
    df: pd.DataFrame,
    metrics: List[str],
    windows: List[int] = [5, 15, 30, 60]
) -> pd.DataFrame:
    """
    Generate rolling statistics strictly backwards-looking:
    rolling_mean_w, rolling_std_w
    """
    df_out = df.copy()
    for metric in metrics:
        if metric in df.columns:
            for w in windows:
                # Rolling mean (shift(0) is current t and past t-1..t-w+1)
                df_out[f"{metric}_rolling_mean_{w}"] = (
                    df[metric].rolling(window=w, min_periods=max(2, w // 2)).mean()
                )
                # Rolling standard deviation
                df_out[f"{metric}_rolling_std_{w}"] = (
                    df[metric].rolling(window=w, min_periods=max(2, w // 2)).std().fillna(0.0)
                )
                # Rolling min and max
                df_out[f"{metric}_rolling_min_{w}"] = (
                    df[metric].rolling(window=w, min_periods=max(2, w // 2)).min()
                )
                df_out[f"{metric}_rolling_max_{w}"] = (
                    df[metric].rolling(window=w, min_periods=max(2, w // 2)).max()
                )
    return df_out


def add_trend_features(
    df: pd.DataFrame,
    metrics: List[str],
    window: int = 15
) -> pd.DataFrame:
    """
    Calculate short-term linear trend / slope over a rolling window.
    Slope = (mean(t..t-w/2) - mean(t-w/2..t-w)) / (w / 2)
    This provides directional momentum without future data.
    """
    df_out = df.copy()
    half_w = max(2, window // 2)
    for metric in metrics:
        if metric in df.columns:
            recent_mean = df[metric].rolling(window=half_w, min_periods=2).mean()
            past_mean = df[metric].shift(half_w).rolling(window=half_w, min_periods=2).mean()
            df_out[f"{metric}_slope_{window}"] = (recent_mean - past_mean) / half_w
    return df_out
