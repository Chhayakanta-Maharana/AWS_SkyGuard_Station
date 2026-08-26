#!/usr/bin/env python3
"""
SkyGuard AI — Dataset Loader & Chronological Splitter
===================================================
Loads historical AWS weather datasets (including 10,000-record radiosonde profiles),
cleans records, and performs chronological time-series splitting (70/15/15) BEFORE any anomaly injection.
"""

import os
from io import StringIO
import pandas as pd
import numpy as np

def load_aws_dataset(filepath: str) -> pd.DataFrame:
    """
    Loads raw text/CSV AWS dataset or radiosonde profile, normalizes columns, and validates values.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Dataset file not found: {filepath}")

    if "radiosonde" in filepath.lower() or "profile" in filepath.lower():
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        data_start = 0
        for i, line in enumerate(lines):
            if "Time" in line and "P" in line and "T" in line and "Hu" in line:
                data_start = i
                break
        
        clean_text = "".join(lines[data_start:])
        try:
            df = pd.read_csv(StringIO(clean_text), sep=r"\s+", on_bad_lines="skip", engine="python")
        except Exception:
            df = pd.read_csv(StringIO(clean_text), sep=r"\s+", on_bad_lines="skip")

        if len(df) > 0 and ("[" in str(df.iloc[0, 0]) or "sec" in str(df.iloc[0, 0]).lower()):
            df = df.iloc[1:].reset_index(drop=True)

        rename_map = {}
        for col in df.columns:
            c = col.strip()
            if c == "T":
                rename_map[col] = "temperature"
            elif c == "P":
                rename_map[col] = "pressure"
            elif c == "Hu":
                rename_map[col] = "humidity"
            elif c == "Time":
                rename_map[col] = "timestamp"
        df = df.rename(columns=rename_map)

    else:
        try:
            df = pd.read_csv(filepath, on_bad_lines="skip")
        except Exception:
            df = pd.read_csv(filepath, sep=r"\s+", on_bad_lines="skip", engine="python")

        norm_cols = {}
        for col in df.columns:
            c_clean = col.lower().strip()
            if "dry" in c_clean:
                norm_cols[col] = "temperature"
            elif "wet" in c_clean:
                norm_cols[col] = "wet_bulb_temp"
            elif "press" in c_clean and "imu" not in c_clean:
                norm_cols[col] = "pressure"
            elif "press" in c_clean and "pressure" not in norm_cols.values():
                norm_cols[col] = "pressure"
            elif "hum" in c_clean or "rh" in c_clean or c_clean == "hu":
                norm_cols[col] = "humidity"
            elif "time" in c_clean or "inst" in c_clean or "date" in c_clean:
                norm_cols[col] = "timestamp"
        df = df.rename(columns=norm_cols)

    # Fallback renaming if any core column missing
    for col in df.columns:
        c_clean = col.lower().strip()
        if "temperature" not in df.columns and "t" in c_clean:
            df = df.rename(columns={col: "temperature"})
        elif "pressure" not in df.columns and ("p" in c_clean or "hpa" in c_clean):
            df = df.rename(columns={col: "pressure"})
        elif "humidity" not in df.columns and ("hu" in c_clean or "rh" in c_clean):
            df = df.rename(columns={col: "humidity"})

    # Extract target Series
    selected = {}
    for col_name in ["timestamp", "temperature", "pressure", "humidity"]:
        if col_name in df.columns:
            val = df[col_name]
            if isinstance(val, pd.DataFrame):
                val = val.iloc[:, 0]
            selected[col_name] = pd.to_numeric(val, errors="coerce")

    clean_df = pd.DataFrame(selected)

    # Drop NaNs ONLY from core sensor columns
    sensor_cols = [c for c in ["temperature", "pressure", "humidity"] if c in clean_df.columns]
    clean_df = clean_df.dropna(subset=sensor_cols).reset_index(drop=True)

    # Fill timestamp if missing or NaN
    if "timestamp" not in clean_df.columns or clean_df["timestamp"].isna().any():
        clean_df["timestamp"] = np.arange(1000, 1000 + len(clean_df), dtype=float)

    # Physical bounds filtering
    if "temperature" in clean_df.columns:
        clean_df = clean_df[(clean_df["temperature"] >= -60.0) & (clean_df["temperature"] <= 60.0)]
    if "humidity" in clean_df.columns:
        clean_df = clean_df[(clean_df["humidity"] >= 0.0) & (clean_df["humidity"] <= 100.0)]
    if "pressure" in clean_df.columns:
        clean_df = clean_df[(clean_df["pressure"] >= 5.0) & (clean_df["pressure"] <= 1100.0)]

    return clean_df.reset_index(drop=True)

def split_chronologically(df: pd.DataFrame, train_ratio=0.70, val_ratio=0.15, test_ratio=0.15):
    """
    Splits time-series dataset chronologically into Train, Validation, and Test sets.
    Targeting 70% Train, 15% Validation, 15% Test.
    """
    total = len(df)
    train_end = int(total * train_ratio)
    val_end = train_end + int(total * val_ratio)

    train_df = df.iloc[:train_end].copy().reset_index(drop=True)
    val_df = df.iloc[train_end:val_end].copy().reset_index(drop=True)
    test_df = df.iloc[val_end:].copy().reset_index(drop=True)

    print(f"[Dataset Split] Total: {total} records", flush=True)
    print(f"  |- Train (Clean Normal): {len(train_df)} samples ({train_ratio*100:.0f}%)", flush=True)
    print(f"  |- Validation:           {len(val_df)} samples ({val_ratio*100:.0f}%)", flush=True)
    print(f"  |- Test:                 {len(test_df)} samples ({test_ratio*100:.0f}%)", flush=True)

    return train_df, val_df, test_df
