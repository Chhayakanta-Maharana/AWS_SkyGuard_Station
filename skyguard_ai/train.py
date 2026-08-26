#!/usr/bin/env python3
"""
SkyGuard AI — Production Model Training Engine
================================================
Trains Isolation Forest on 100% CLEAN normal weather data (chronological split).
Evaluates decision threshold on synthetic validation data, measures empirical FPR,
and exports model artifacts to models/.
"""

import os
import sys
import json
import joblib
import numpy as np
import pandas as pd
from datetime import datetime, timezone

from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix

script_dir = os.path.dirname(os.path.abspath(__file__))
skyguard_ai_dir = script_dir if os.path.basename(script_dir) == "skyguard_ai" else os.path.dirname(script_dir)
if skyguard_ai_dir not in sys.path:
    sys.path.insert(0, skyguard_ai_dir)

from features.feature_pipeline import transform_dataframe, FEATURE_COLUMNS
from training.dataset_loader import load_aws_dataset, split_chronologically
from simulation.anomaly_injector import inject_anomalies

def train_and_evaluate_model():
    print("=" * 60, flush=True)
    print("SkyGuard AI -- Production Model Training Engine", flush=True)
    print("=" * 60, flush=True)

    project_dir = os.path.dirname(skyguard_ai_dir)
    possible_datasets = [
        os.path.join(project_dir, "radiosonde_profile_10000.txt"),
        os.path.join(project_dir, "aws_sample_input.txt"),
    ]

    dataset_path = None
    for p in possible_datasets:
        if os.path.exists(p):
            dataset_path = p
            break

    if not dataset_path:
        print("Notice: Generating clean synthetic historical dataset for initial training...", flush=True)
        np.random.seed(42)
        n = 3000
        t_base = np.linspace(18, 36, n) + np.sin(np.linspace(0, 20*np.pi, n)) * 4.0
        p_base = np.linspace(1010, 1016, n) + np.cos(np.linspace(0, 10*np.pi, n)) * 2.0
        h_base = np.linspace(50, 85, n) - np.sin(np.linspace(0, 20*np.pi, n)) * 10.0

        raw_df = pd.DataFrame({
            "timestamp": pd.date_range(start="2026-08-01", periods=n, freq="10s").astype(int) // 10**9,
            "temperature": t_base + np.random.normal(0, 0.2, n),
            "pressure": p_base + np.random.normal(0, 0.1, n),
            "humidity": np.clip(h_base + np.random.normal(0, 0.5, n), 0, 100)
        })
    else:
        print(f"Loading historical AWS dataset: {os.path.basename(dataset_path)}", flush=True)
        raw_df = load_aws_dataset(dataset_path)

    print(f"Loaded {len(raw_df)} valid meteorological observations.", flush=True)

    # Chronological Dataset Splitting (70% Train, 15% Val, 15% Test) BEFORE Anomaly Injection
    train_raw, val_raw, test_raw = split_chronologically(raw_df, train_ratio=0.70, val_ratio=0.15, test_ratio=0.15)

    # Anomaly Injection (Inject ONLY into Validation and Test sets; Training stays 100% clean)
    print("\n[Anomaly Injection Layer]", flush=True)
    val_injected = inject_anomalies(val_raw, anomaly_rate=0.15, seed=42)
    test_injected = inject_anomalies(test_raw, anomaly_rate=0.15, seed=100)

    # Feature Engineering via Shared feature_pipeline.py
    print("\n[Feature Engineering Layer]", flush=True)
    X_train_raw = transform_dataframe(train_raw)
    X_val_raw = transform_dataframe(val_injected)
    X_test_raw = transform_dataframe(test_injected)

    y_val = val_injected["ground_truth_label"].values
    y_test = test_injected["ground_truth_label"].values

    # Preprocessing / Scaling
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train_raw)
    X_val_scaled = scaler.transform(X_val_raw)
    X_test_scaled = scaler.transform(X_test_raw)

    # Fit Production Isolation Forest Model on CLEAN Training Data ONLY
    print("\n[Model Fitting Layer]", flush=True)
    model = IsolationForest(
        n_estimators=100,
        contamination=0.01,
        max_samples="auto",
        random_state=42,
        n_jobs=1
    )
    model.fit(X_train_scaled)
    print("[+] Fitted Isolation Forest on 100% clean baseline weather features.", flush=True)

    # Decision Threshold Tuning on Validation Set
    val_scores_raw = model.decision_function(X_val_scaled)
    val_anomaly_scores = -val_scores_raw

    best_thresh = 0.0
    best_f1 = -1.0
    for thresh in np.linspace(np.percentile(val_anomaly_scores, 70), np.percentile(val_anomaly_scores, 99), 50):
        y_pred = (val_anomaly_scores > thresh).astype(int)
        f = f1_score(y_val, y_pred, zero_division=0)
        if f > best_f1:
            best_f1 = f
            best_thresh = thresh

    print(f"[+] Selected Decision Threshold: {best_thresh:.4f} (Validation F1: {best_f1:.4f})", flush=True)

    # Final Evaluation on Test Set
    test_scores_raw = model.decision_function(X_test_scaled)
    test_anomaly_scores = -test_scores_raw
    test_preds = (test_anomaly_scores > best_thresh).astype(int)

    prec = float(precision_score(y_test, test_preds, zero_division=0))
    rec = float(recall_score(y_test, test_preds, zero_division=0))
    f1 = float(f1_score(y_test, test_preds, zero_division=0))

    tn, fp, fn, tp = confusion_matrix(y_test, test_preds).ravel()
    fpr = float(fp / max(1, (fp + tn)))

    print("\n" + "=" * 60, flush=True)
    print("FINAL MODEL EVALUATION METRICS (TEST SET)", flush=True)
    print("=" * 60, flush=True)
    print(f"  Precision:                   {prec * 100:.2f}%", flush=True)
    print(f"  Recall (Detection Rate):    {rec * 100:.2f}%", flush=True)
    print(f"  F1-Score:                   {f1 * 100:.2f}%", flush=True)
    print(f"  Empirically Measured FPR:   {fpr * 100:.2f}%", flush=True)
    print(f"  Confusion Matrix:           TN={tn}, FP={fp}, FN={fn}, TP={tp}", flush=True)
    print("=" * 60, flush=True)

    # Save Artifacts to unified skyguard_ai/models/
    models_dir = os.path.join(skyguard_ai_dir, "models")
    os.makedirs(models_dir, exist_ok=True)

    joblib.dump(model, os.path.join(models_dir, "anomaly_model.pkl"))
    joblib.dump(scaler, os.path.join(models_dir, "scaler.pkl"))

    with open(os.path.join(models_dir, "feature_config.json"), "w") as f:
        json.dump({"features": FEATURE_COLUMNS}, f, indent=2)

    with open(os.path.join(models_dir, "threshold_config.json"), "w") as f:
        json.dump({"decision_threshold": float(best_thresh)}, f, indent=2)

    metadata = {
        "model_type": "IsolationForest",
        "model_version": "v1.0.0",
        "training_timestamp": datetime.now(timezone.utc).isoformat(),
        "train_samples": int(len(train_raw)),
        "validation_samples": int(len(val_raw)),
        "test_samples": int(len(test_raw)),
        "feature_count": len(FEATURE_COLUMNS),
        "features": FEATURE_COLUMNS,
        "metrics": {
            "precision": prec,
            "recall": rec,
            "f1_score": f1,
            "false_positive_rate": fpr,
            "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)}
        },
        "decision_threshold": float(best_thresh)
    }

    with open(os.path.join(models_dir, "model_metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"\n[+] Saved model artifacts to: {models_dir}", flush=True)
    print("  |- anomaly_model.pkl", flush=True)
    print("  |- scaler.pkl", flush=True)
    print("  |- feature_config.json", flush=True)
    print("  |- threshold_config.json", flush=True)
    print("  |- model_metadata.json", flush=True)
    print("\n[+] Model Training & Evaluation Complete.", flush=True)

if __name__ == "__main__":
    train_and_evaluate_model()
