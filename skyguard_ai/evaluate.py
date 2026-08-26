#!/usr/bin/env python3
"""
SkyGuard AI — Standalone Model Evaluation & Benchmarking Subsystem
==================================================================
Evaluates the trained production Isolation Forest model artifact on held-out test data.
Generates per-anomaly-type metrics, empirical FPR, confusion matrix, and JSON/CSV reports.
"""

import os
import sys
import json
import joblib
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix

script_dir = os.path.dirname(os.path.abspath(__file__))
skyguard_ai_dir = script_dir if os.path.basename(script_dir) == "skyguard_ai" else os.path.dirname(script_dir)
if skyguard_ai_dir not in sys.path:
    sys.path.insert(0, skyguard_ai_dir)

from features.feature_pipeline import transform_dataframe, FEATURE_COLUMNS
from training.dataset_loader import load_aws_dataset, split_chronologically
from simulation.anomaly_injector import inject_anomalies

def evaluate_model():
    print("=" * 60, flush=True)
    print("SkyGuard AI -- Model Evaluation & Metrics Pipeline", flush=True)
    print("=" * 60, flush=True)

    models_dir = os.path.join(skyguard_ai_dir, "models")
    model_path = os.path.join(models_dir, "anomaly_model.pkl")
    scaler_path = os.path.join(models_dir, "scaler.pkl")
    thresh_path = os.path.join(models_dir, "threshold_config.json")

    if not os.path.exists(model_path):
        print("[-] Error: Saved model artifact not found. Please run `python train.py` first.", flush=True)
        sys.exit(1)

    model = joblib.load(model_path)
    scaler = joblib.load(scaler_path)

    with open(thresh_path, "r") as f:
        threshold = json.load(f)["decision_threshold"]

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

    if dataset_path:
        raw_df = load_aws_dataset(dataset_path)
    else:
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

    _, _, test_raw = split_chronologically(raw_df, train_ratio=0.70, val_ratio=0.15, test_ratio=0.15)
    test_injected = inject_anomalies(test_raw, anomaly_rate=0.20, seed=200)

    X_test_feat = transform_dataframe(test_injected)
    X_test_scaled = scaler.transform(X_test_feat)
    y_true = test_injected["ground_truth_label"].values

    raw_scores = model.decision_function(X_test_scaled)
    anomaly_scores = -raw_scores
    y_pred = (anomaly_scores > threshold).astype(int)

    # Per-Anomaly Type Performance Breakdown
    test_injected["pred_label"] = y_pred
    anomaly_types = test_injected["anomaly_type"].unique()

    type_metrics = []
    for a_type in anomaly_types:
        subset = test_injected[test_injected["anomaly_type"] == a_type]
        sub_true = subset["ground_truth_label"].values
        sub_pred = subset["pred_label"].values

        p = precision_score(sub_true, sub_pred, zero_division=0)
        r = recall_score(sub_true, sub_pred, zero_division=0)
        f = f1_score(sub_true, sub_pred, zero_division=0)

        type_metrics.append({
            "anomaly_type": a_type,
            "sample_count": len(subset),
            "precision": float(p),
            "recall": float(r),
            "f1_score": float(f)
        })

    overall_prec = float(precision_score(y_true, y_pred, zero_division=0))
    overall_rec = float(recall_score(y_true, y_pred, zero_division=0))
    overall_f1 = float(f1_score(y_true, y_pred, zero_division=0))

    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
    fpr = float(fp / max(1, (fp + tn)))

    report = {
        "evaluation_timestamp": datetime.now(timezone.utc).isoformat(),
        "total_test_samples": len(test_injected),
        "overall_metrics": {
            "precision": overall_prec,
            "recall": overall_rec,
            "f1_score": overall_f1,
            "false_positive_rate": fpr,
            "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)}
        },
        "per_anomaly_type_breakdown": type_metrics
    }

    report_path = os.path.join(models_dir, "evaluation_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    df_metrics = pd.DataFrame(type_metrics)
    csv_path = os.path.join(models_dir, "evaluation_report.csv")
    df_metrics.to_csv(csv_path, index=False)

    print("\n" + "=" * 60, flush=True)
    print("PER-ANOMALY-TYPE EVALUATION BREAKDOWN", flush=True)
    print("=" * 60, flush=True)
    for m in type_metrics:
        print(f"  {m['anomaly_type']:<28} | Samples: {m['sample_count']:<4} | P: {m['precision']*100:5.1f}% | R: {m['recall']*100:5.1f}% | F1: {m['f1_score']*100:5.1f}%", flush=True)
    print("=" * 60, flush=True)
    print(f"[+] Saved evaluation reports to:\n  |- {report_path}\n  |- {csv_path}", flush=True)

if __name__ == "__main__":
    evaluate_model()
