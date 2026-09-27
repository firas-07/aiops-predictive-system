from typing import List
import pandas as pd

def add_lag_features(
    df: pd.DataFrame,
    metrics: List[str],
    lags: List[int] = [1, 5, 10, 15, 30, 60]
) -> pd.DataFrame:
    """
    Generate lag features strictly using historical values at or before time t.
    lag_k for metric M is M(t - k).
    """
    df_out = df.copy()
    for metric in metrics:
        if metric in df.columns:
            for lag in lags:
                col_name = f"{metric}_lag_{lag}"
                df_out[col_name] = df[metric].shift(lag)
    return df_out


def add_delta_features(
    df: pd.DataFrame,
    metrics: List[str],
    deltas: List[int] = [1, 5, 15]
) -> pd.DataFrame:
    """
    Generate change / rate-of-change features:
    delta_k = M(t) - M(t - k)
    """
    df_out = df.copy()
    for metric in metrics:
        if metric in df.columns:
            for delta in deltas:
                col_name = f"{metric}_delta_{delta}"
                df_out[col_name] = df[metric] - df[metric].shift(delta)
    return df_out
