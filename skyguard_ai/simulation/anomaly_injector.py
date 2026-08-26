#!/usr/bin/env python3
"""
SkyGuard AI — Synthetic Anomaly Injector Framework
=================================================
Injects ground-truth labeled synthetic anomalies into VALIDATION and TEST sets ONLY.
Leaves Training datasets 100% clean normal weather observations.
"""

import numpy as np
import pandas as pd

def inject_anomalies(df: pd.DataFrame, anomaly_rate: float = 0.15, seed: int = 42) -> pd.DataFrame:
    """
    Injects synthetic ground-truth labeled anomalies into a clean weather DataFrame.
    Returns DataFrame with extra columns: ['ground_truth_label', 'anomaly_type', 'affected_parameter']
    """
    np.random.seed(seed)
    df = df.copy()

    # Add ground-truth tracking columns
    df["ground_truth_label"] = 0
    df["anomaly_type"] = "nominal"
    df["affected_parameter"] = "none"

    n_samples = len(df)
    n_anomalies = int(n_samples * anomaly_rate)
    if n_anomalies == 0 or n_samples < 20:
        return df

    # Select random indices for anomaly injection (grouped in contiguous blocks for time-series realism)
    block_sizes = [1, 1, 1, 3, 5, 10]
    injected_count = 0
    current_idx = 10

    anomaly_types = [
        "temperature_spike",
        "temperature_drop",
        "pressure_spike",
        "pressure_drop",
        "humidity_spike",
        "frozen_sensor",
        "sensor_drift",
        "gaussian_noise",
        "multivariate_inconsistency"
    ]

    while injected_count < n_anomalies and current_idx < n_samples - 15:
        a_type = np.random.choice(anomaly_types)
        block_len = np.random.choice(block_sizes)

        if a_type == "temperature_spike":
            df.loc[current_idx, "temperature"] += 25.0
            df.loc[current_idx, "ground_truth_label"] = 1
            df.loc[current_idx, "anomaly_type"] = "temperature_spike"
            df.loc[current_idx, "affected_parameter"] = "temperature"
            injected_count += 1
            current_idx += np.random.randint(5, 15)

        elif a_type == "temperature_drop":
            df.loc[current_idx, "temperature"] -= 20.0
            df.loc[current_idx, "ground_truth_label"] = 1
            df.loc[current_idx, "anomaly_type"] = "temperature_drop"
            df.loc[current_idx, "affected_parameter"] = "temperature"
            injected_count += 1
            current_idx += np.random.randint(5, 15)

        elif a_type == "pressure_spike":
            df.loc[current_idx, "pressure"] += 35.0
            df.loc[current_idx, "ground_truth_label"] = 1
            df.loc[current_idx, "anomaly_type"] = "pressure_spike"
            df.loc[current_idx, "affected_parameter"] = "pressure"
            injected_count += 1
            current_idx += np.random.randint(5, 15)

        elif a_type == "pressure_drop":
            df.loc[current_idx, "pressure"] -= 40.0
            df.loc[current_idx, "ground_truth_label"] = 1
            df.loc[current_idx, "anomaly_type"] = "pressure_drop"
            df.loc[current_idx, "affected_parameter"] = "pressure"
            injected_count += 1
            current_idx += np.random.randint(5, 15)

        elif a_type == "humidity_spike":
            df.loc[current_idx, "humidity"] = min(100.0, df.loc[current_idx, "humidity"] + 45.0)
            df.loc[current_idx, "ground_truth_label"] = 1
            df.loc[current_idx, "anomaly_type"] = "humidity_spike"
            df.loc[current_idx, "affected_parameter"] = "humidity"
            injected_count += 1
            current_idx += np.random.randint(5, 15)

        elif a_type == "frozen_sensor":
            freeze_val = df.loc[current_idx, "temperature"]
            end_idx = min(n_samples, current_idx + max(5, block_len))
            for i in range(current_idx, end_idx):
                df.loc[i, "temperature"] = freeze_val
                df.loc[i, "ground_truth_label"] = 1
                df.loc[i, "anomaly_type"] = "frozen_sensor"
                df.loc[i, "affected_parameter"] = "temperature"
                injected_count += 1
            current_idx = end_idx + np.random.randint(5, 15)

        elif a_type == "sensor_drift":
            end_idx = min(n_samples, current_idx + max(5, block_len))
            ramp = 0.5
            for step, i in enumerate(range(current_idx, end_idx)):
                df.loc[i, "temperature"] += (step + 1) * ramp
                df.loc[i, "ground_truth_label"] = 1
                df.loc[i, "anomaly_type"] = "sensor_drift"
                df.loc[i, "affected_parameter"] = "temperature"
                injected_count += 1
            current_idx = end_idx + np.random.randint(5, 15)

        elif a_type == "gaussian_noise":
            noise = np.random.normal(0, 10.0)
            df.loc[current_idx, "temperature"] += noise
            df.loc[current_idx, "ground_truth_label"] = 1
            df.loc[current_idx, "anomaly_type"] = "gaussian_noise"
            df.loc[current_idx, "affected_parameter"] = "temperature"
            injected_count += 1
            current_idx += np.random.randint(5, 15)

        elif a_type == "multivariate_inconsistency":
            # High temperature (48°C) + max relative humidity (98%) -> psychrometric violation
            df.loc[current_idx, "temperature"] = 48.0
            df.loc[current_idx, "humidity"] = 98.0
            df.loc[current_idx, "ground_truth_label"] = 1
            df.loc[current_idx, "anomaly_type"] = "multivariate_inconsistency"
            df.loc[current_idx, "affected_parameter"] = "multivariate"
            injected_count += 1
            current_idx += np.random.randint(5, 15)

        else:
            current_idx += 1

    print(f"[Anomaly Injector] Injected {injected_count} ground-truth anomalies into dataset ({len(df)} total rows).")
    return df
