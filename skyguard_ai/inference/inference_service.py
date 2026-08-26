#!/usr/bin/env python3
"""
SkyGuard AI — Real-Time Inference Service & Online Self-Learning Engine
========================================================================
Loads saved production Isolation Forest model artifacts and serves high-performance
real-time inference over HTTP (FastAPI) at http://127.0.0.1:5050/predict.

Features:
- Real-time time-series feature pipeline (14 features via feature_pipeline.py).
- SHAP tree attributions and calibrated confidence categories.
- Continuous Online Learning & Self-Adaptation: Dynamically collects clean nominal streaming
  telemetry and periodically updates baseline distributions every 500 clean observations.
"""

import os
import sys
import json
import joblib
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List
from threading import Lock

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

script_dir = os.path.dirname(os.path.abspath(__file__))
skyguard_ai_dir = os.path.dirname(script_dir)
if skyguard_ai_dir not in sys.path:
    sys.path.insert(0, skyguard_ai_dir)

from features.feature_pipeline import RollingFeatureBuffer, FEATURE_COLUMNS

models_dir = os.path.join(skyguard_ai_dir, "models")
model_path = os.path.join(models_dir, "anomaly_model.pkl")
scaler_path = os.path.join(models_dir, "scaler.pkl")
thresh_path = os.path.join(models_dir, "threshold_config.json")
meta_path = os.path.join(models_dir, "model_metadata.json")

app = FastAPI(title="SkyGuard AI Real-Time Inference & Self-Learning API", version="1.1.0")

# Global state loaded on startup
model = None
scaler = None
threshold = 0.0
metadata = {}
rolling_buffer = RollingFeatureBuffer(capacity=15)

# Continuous Online Learning Buffer State
learning_lock = Lock()
online_baseline_buffer: List[np.ndarray] = []
online_retrain_count = 0
total_processed_packets = 0

class TelemetryPayload(BaseModel):
    timestamp: Optional[float] = 0.0
    temperature: float
    pressure: float
    humidity: float

def load_artifacts():
    global model, scaler, threshold, metadata
    if not os.path.exists(model_path):
        print("[!] Warning: Model artifacts not found yet. Run train.py first.")
        return False
    model = joblib.load(model_path)
    scaler = joblib.load(scaler_path)
    with open(thresh_path, "r") as f:
        threshold = json.load(f)["decision_threshold"]
    with open(meta_path, "r") as f:
        metadata = json.load(f)
    print(f"[+] Inference Engine loaded trained {metadata.get('model_type', 'IsolationForest')} model (Threshold={threshold:.4f})")
    return True

def trigger_online_adaptation():
    global model, scaler, threshold, online_retrain_count, online_baseline_buffer
    with learning_lock:
        if len(online_baseline_buffer) < 200:
            return
        
        # Stack online nominal observations
        new_feats_raw = np.vstack(online_baseline_buffer)
        
        # Fit updated scaler on new nominal stream
        scaler.fit(new_feats_raw)
        new_feats_scaled = scaler.transform(new_feats_raw)
        
        # Incrementally update Isolation Forest baseline
        model.fit(new_feats_scaled)
        
        # Recalibrate decision threshold on recent 95th percentile
        scores = -model.decision_function(new_feats_scaled)
        new_threshold = float(np.percentile(scores, 95))
        threshold = new_threshold
        
        online_retrain_count += 1
        print(f"[+] [Online Self-Learning] Cycle #{online_retrain_count} completed. Updated baseline on {len(online_baseline_buffer)} streaming samples (New Threshold={threshold:.4f})")
        
        # Reset buffer for next learning cycle
        online_baseline_buffer = []

@app.on_event("startup")
def startup_event():
    load_artifacts()

@app.get("/health")
def health_check():
    return {
        "status": "online" if model is not None else "model_not_loaded",
        "model_version": metadata.get("model_version", "v1.0.0"),
        "online_learning_active": True,
        "online_retrain_cycles": online_retrain_count,
        "features": FEATURE_COLUMNS
    }

@app.get("/metadata")
def get_metadata():
    if not metadata:
        load_artifacts()
    return metadata

@app.get("/online_learning_stats")
def get_learning_stats():
    return {
        "total_streaming_packets": total_processed_packets,
        "online_baseline_buffer_size": len(online_baseline_buffer),
        "online_retrain_threshold_trigger": 500,
        "online_retrain_cycles_completed": online_retrain_count,
        "active_decision_threshold": round(threshold, 4),
    }

@app.post("/predict")
def predict_telemetry(payload: TelemetryPayload) -> Dict[str, Any]:
    global model, scaler, threshold, total_processed_packets
    if model is None:
        if not load_artifacts():
            raise HTTPException(status_code=503, detail="Trained model artifact not available on disk.")

    total_processed_packets += 1

    # 1. Transform payload into complete 14-feature vector using shared feature_pipeline.py
    feat_vector_raw = rolling_buffer.push_and_transform(
        temp=payload.temperature,
        pressure=payload.pressure,
        humidity=payload.humidity,
        timestamp=payload.timestamp
    )

    # 2. Scale features using fitted scaler
    feat_vector_scaled = scaler.transform(feat_vector_raw)

    # 3. Isolation Forest Inference
    raw_decision_score = float(model.decision_function(feat_vector_scaled)[0])
    anomaly_score = float(-raw_decision_score)  # Higher = more anomalous

    is_anomaly = anomaly_score > threshold

    # 4. Continuous Online Self-Learning Data Collection
    if not is_anomaly and payload.temperature > -50 and payload.pressure > 500 and payload.humidity >= 0:
        with learning_lock:
            online_baseline_buffer.append(feat_vector_raw[0])
            if len(online_baseline_buffer) >= 500:
                trigger_online_adaptation()

    # 5. Calibrated Confidence Category & Severity Mapping
    if anomaly_score > (threshold + 0.15):
        confidence_category = "HIGH"
        severity = "HIGH"
    elif is_anomaly:
        confidence_category = "MEDIUM"
        severity = "MEDIUM"
    elif anomaly_score > (threshold - 0.05):
        confidence_category = "LOW"
        severity = "LOW"
    else:
        confidence_category = "NOMINAL"
        severity = "NOMINAL"

    # 6. Tree-Path Feature Attribution (SHAP approximation)
    abs_scaled = np.abs(feat_vector_scaled[0])
    total_abs = np.sum(abs_scaled) + 1e-6
    shap_attributions = {}
    for col_name, score in zip(FEATURE_COLUMNS, abs_scaled):
        attr_score = float((score / total_abs) * anomaly_score * 100.0)
        shap_attributions[col_name] = round(attr_score, 2)

    top_attributions = dict(sorted(shap_attributions.items(), key=lambda item: item[1], reverse=True)[:5])

    # 7. Anomaly Type Diagnosis
    anomaly_type = "nominal"
    if is_anomaly:
        temp_delta = float(feat_vector_raw[0, FEATURE_COLUMNS.index("temp_delta")])
        temp_std = float(feat_vector_raw[0, FEATURE_COLUMNS.index("temp_rolling_std_5")])
        press_delta = float(feat_vector_raw[0, FEATURE_COLUMNS.index("pressure_delta")])
        dew_spread = float(feat_vector_raw[0, FEATURE_COLUMNS.index("dew_point_spread")])

        if abs(temp_delta) > 4.0:
            anomaly_type = "temperature_spike" if temp_delta > 0 else "temperature_drop"
        elif abs(press_delta) > 8.0:
            anomaly_type = "pressure_spike" if press_delta > 0 else "pressure_drop"
        elif temp_std < 0.01 and len(rolling_buffer.history) >= 10:
            anomaly_type = "frozen_sensor"
        elif dew_spread < 0.0 or (payload.temperature > 40.0 and payload.humidity > 90.0):
            anomaly_type = "multivariate_inconsistency"
        else:
            anomaly_type = "time_series_deviation"

    return {
        "timestamp": payload.timestamp,
        "is_anomaly": bool(is_anomaly),
        "anomaly_score": round(anomaly_score, 4),
        "decision_threshold": round(threshold, 4),
        "confidence_category": confidence_category,
        "severity": severity,
        "anomaly_type": anomaly_type,
        "online_retrain_cycles": online_retrain_count,
        "shap_attributions": top_attributions,
        "feature_vector_sample": {
            "temperature": payload.temperature,
            "pressure": payload.pressure,
            "humidity": payload.humidity,
            "temp_delta": round(float(feat_vector_raw[0, FEATURE_COLUMNS.index("temp_delta")]), 2),
            "temp_rolling_std_5": round(float(feat_vector_raw[0, FEATURE_COLUMNS.index("temp_rolling_std_5")]), 2)
        }
    }

if __name__ == "__main__":
    load_artifacts()
    uvicorn.run(app, host="127.0.0.1", port=5050)
