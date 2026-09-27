import os
import sys
import pandas as pd
import numpy as np
import json

def inspect_dataset(csv_path: str):
    print("=" * 60)
    print(f"INSPECTING DATASET: {csv_path}")
    print("=" * 60)
    
    if not os.path.exists(csv_path):
        print(f"Error: File not found: {csv_path}")
        return
        
    df = pd.read_csv(csv_path)
    
    # 1. Row count and columns
    print(f"Row count: {len(df)}")
    print(f"Column count: {len(df.columns)}")
    print(f"Column names: {list(df.columns)}")
    print("\nData Types:")
    print(df.dtypes)
    
    # 2. Timestamp analysis
    print("\n" + "=" * 30 + " TIMESTAMP ANALYSIS " + "=" * 30)
    df['parsed_timestamp'] = pd.to_datetime(df['timestamp'])
    min_ts = df['parsed_timestamp'].min()
    max_ts = df['parsed_timestamp'].max()
    print(f"Min timestamp: {min_ts}")
    print(f"Max timestamp: {max_ts}")
    duration = max_ts - min_ts
    print(f"Total time span: {duration}")
    
    # Sampling frequency and gaps
    df_sorted = df.sort_values('parsed_timestamp')
    diffs = df_sorted['parsed_timestamp'].diff().dropna()
    print(f"Sampling frequency mode: {diffs.mode().iloc[0]}")
    print(f"Interval distribution:\n{diffs.value_counts().head(5)}")
    expected_step = pd.Timedelta(minutes=1)
    gaps = diffs[diffs != expected_step]
    print(f"Total irregular intervals / gaps: {len(gaps)}")
    if len(gaps) > 0:
        print(f"Sample gaps:\n{gaps.head(5)}")
        
    # 3. Duplicates
    dup_ts = df.duplicated(subset=['timestamp']).sum()
    dup_all = df.duplicated().sum()
    print(f"\nDuplicate full rows: {dup_all}")
    print(f"Duplicate timestamps: {dup_ts}")
    
    # 4. Missing values
    print("\n" + "=" * 30 + " MISSING VALUES " + "=" * 30)
    missing = df.isnull().sum()
    print(missing[missing > 0] if missing.sum() > 0 else "No missing values found across all columns.")
    
    # 5. Descriptive statistics (numeric)
    print("\n" + "=" * 30 + " DESCRIPTIVE STATISTICS " + "=" * 30)
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    stats = df[numeric_cols].describe().T[['count', 'mean', 'std', 'min', '25%', '50%', '75%', 'max']]
    print(stats.to_string())
    
    # 6. Status distribution & failure events
    print("\n" + "=" * 30 + " LABELS / STATUS DISTRIBUTION " + "=" * 30)
    if 'app_status' in df.columns:
        print("app_status value counts:")
        print(df['app_status'].value_counts(dropna=False))
        print("app_status percentages:")
        print((df['app_status'].value_counts(normalize=True) * 100).round(2))
        
    if 'failure_event' in df.columns:
        print("\nfailure_event value counts:")
        print(df['failure_event'].value_counts(dropna=False))
        
    if 'app_id' in df.columns:
        print("\nUnique app_ids:", df['app_id'].unique().tolist())
        
    # 7. Correlation matrix (numeric metrics)
    print("\n" + "=" * 30 + " CORRELATIONS (Metric Features) " + "=" * 30)
    metric_cols = [c for c in ['cpu_percent', 'memory_percent', 'disk_io_mb_s', 'latency_ms', 
                               'http_errors', 'http_success', 'network_mb_s', 'request_volume'] if c in df.columns]
    corr = df[metric_cols].corr().round(3)
    print(corr.to_string())
    
    # Export summary json for verification
    summary = {
        "rows": int(len(df)),
        "cols": list(df.columns),
        "min_timestamp": str(min_ts),
        "max_timestamp": str(max_ts),
        "duplicate_timestamps": int(dup_ts),
        "missing_values": {k: int(v) for k, v in missing.items()},
        "app_status_counts": {k: int(v) for k, v in df['app_status'].value_counts().items()} if 'app_status' in df.columns else {},
        "failure_event_counts": {k: int(v) for k, v in df['failure_event'].value_counts().items()} if 'failure_event' in df.columns else {},
        "stats": stats.to_dict(orient='index')
    }
    
    os.makedirs("data/raw", exist_ok=True)
    with open("data/raw/dataset_summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    print("\nDataset summary saved to data/raw/dataset_summary.json")

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "docs/Sample Dataset.csv"
    inspect_dataset(path)
