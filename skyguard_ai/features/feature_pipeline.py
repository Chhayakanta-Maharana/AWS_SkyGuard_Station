#!/usr/bin/env python3
"""
SkyGuard AI — Unified Shared Feature Engineering Pipeline
=========================================================
Single Source of Truth for Feature Generation across:
  - Training (train.py)
  - Evaluation (evaluate.py)
  - Live Real-Time Inference (inference_service.py)

Ensures 100% feature consistency and column order matching.
"""

import math
import numpy as np
import pandas as pd

FEATURE_COLUMNS = [
    "temperature",
    "pressure",
    "humidity",
    "temp_delta",
    "pressure_delta",
    "humidity_delta",
    "temp_rolling_mean_5",
    "temp_rolling_std_5",
    "pressure_rolling_mean_5",
    "humidity_rolling_mean_5",
    "dew_point",
    "dew_point_spread",
    "hour_sin",
    "hour_cos"
]

def calculate_dew_point(temp_c: float, humidity_pct: float) -> float:
    """Psychrometric dew point calculation (°C)."""
    # Simple Magnus-Tetens approximation
    a = 17.27
    b = 237.7
    humidity_pct = max(0.1, min(100.0, humidity_pct))
    alpha = ((a * temp_c) / (b + temp_c)) + math.log(humidity_pct / 100.0)
    return (b * alpha) / (a - alpha)

def transform_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Transforms a DataFrame containing ['temperature', 'pressure', 'humidity']
    and optional ['timestamp'] into the complete engineered feature matrix.
    """
    df = df.copy()

    # Column name normalization
    rename_map = {}
    for col in df.columns:
        c_lower = col.lower().strip()
        if "dry" in c_lower or "temp" in c_lower:
            rename_map[col] = "temperature"
        elif "press" in c_lower:
            rename_map[col] = "pressure"
        elif "hum" in c_lower or "rh" in c_lower:
            rename_map[col] = "humidity"
        elif "time" in c_lower or "date" in c_lower:
            rename_map[col] = "timestamp"
    df = df.rename(columns=rename_map)

    # Ensure required base columns exist
    for col in ["temperature", "pressure", "humidity"]:
        if col not in df.columns:
            raise ValueError(f"Missing required base column: {col}")

    # Convert to numeric
    df["temperature"] = pd.to_numeric(df["temperature"], errors="coerce")
    df["pressure"] = pd.to_numeric(df["pressure"], errors="coerce")
    df["humidity"] = pd.to_numeric(df["humidity"], errors="coerce")

    # Forward fill / backward fill NaNs for feature generation
    df = df.bfill().ffill().fillna(0.0)

    # 1. Temporal Deltas
    df["temp_delta"] = df["temperature"].diff().fillna(0.0)
    df["pressure_delta"] = df["pressure"].diff().fillna(0.0)
    df["humidity_delta"] = df["humidity"].diff().fillna(0.0)

    # 2. Rolling Statistics (Window size = 5)
    df["temp_rolling_mean_5"] = df["temperature"].rolling(window=5, min_periods=1).mean()
    df["temp_rolling_std_5"] = df["temperature"].rolling(window=5, min_periods=1).std().fillna(0.0)
    df["pressure_rolling_mean_5"] = df["pressure"].rolling(window=5, min_periods=1).mean()
    df["humidity_rolling_mean_5"] = df["humidity"].rolling(window=5, min_periods=1).mean()

    # 3. Psychrometric Features
    df["dew_point"] = df.apply(lambda row: calculate_dew_point(row["temperature"], row["humidity"]), axis=1)
    df["dew_point_spread"] = df["temperature"] - df["dew_point"]

    # 4. Cyclic Time Features
    if "timestamp" in df.columns:
        try:
            timestamps = pd.to_datetime(df["timestamp"], unit="s", errors="coerce")
            if timestamps.isna().all():
                timestamps = pd.to_datetime(df["timestamp"], errors="coerce")
            hours = timestamps.dt.hour.fillna(12)
        except Exception:
            hours = pd.Series([12] * len(df))
    else:
        hours = pd.Series([12] * len(df))

    df["hour_sin"] = np.sin(2 * np.pi * hours / 24.0)
    df["hour_cos"] = np.cos(2 * np.pi * hours / 24.0)

    return df[FEATURE_COLUMNS]

class RollingFeatureBuffer:
    """
    Stateful rolling window buffer for Real-Time Single Packet Inference.
    Maintains historical memory of incoming live datagrams to generate rolling features.
    """
    def __init__(self, capacity: int = 15):
        self.capacity = capacity
        self.history = []

    def push_and_transform(self, temp: float, pressure: float, humidity: float, timestamp: float = None) -> np.ndarray:
        record = {
            "temperature": float(temp),
            "pressure": float(pressure),
            "humidity": float(humidity),
            "timestamp": timestamp if timestamp is not None else 0.0
        }
        self.history.append(record)
        if len(self.history) > self.capacity:
            self.history.pop(0)

        df_hist = pd.DataFrame(self.history)
        df_feat = transform_dataframe(df_hist)
        # Return the latest feature vector as a 2D numpy array [1, num_features]
        return df_feat.iloc[-1:].values
