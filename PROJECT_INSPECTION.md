# AWS SkyGuard Station — Complete Project Inspection Report (SIH PS-26073)

## 1. Existing Architecture & Overview

The target application **`AWS_SkyGuard_Station`** is a hybrid desktop application designed for real-time monitoring and anomaly detection of Automatic Weather Station (AWS) sensors.

```text
[AWS Sensor Hardware / Simulator]
              │
              │ (UDP Port 5000 / TCP Port 5001 - Binary 0xAA55, CSV, or JSON)
              ▼
[aws-telemetry-backend.exe (Go Server)]
              │
              ├─► Ingestion & Parsing (parser.go)
              ├─► Physics-Based Anomaly Detection (detector.go)
              └─► Serves Web UI & Stream API (http://127.0.0.1:8080)
              │
              ▼
[PyWebView Window (desktop/app.py)] ◄──► [Next.js React Dashboard (frontend/out)]
```

---

## 2. Component Inspection

| Component | Source File / Location | Technology | Role & Functionality |
| :--- | :--- | :--- | :--- |
| **Desktop Wrapper** | [desktop/app.py](file:///c:/Users/chhay/OneDrive/Documents/DRDO%20Project/aws_skyguard_station/desktop/app.py) | Python + PyWebView2 | Launches `aws-telemetry-backend.exe`, checks WebView2 runtime, embeds Next.js static frontend output. |
| **Ingestion Backend** | [backend/main.go](file:///c:/Users/chhay/OneDrive/Documents/DRDO%20Project/aws_skyguard_station/backend/main.go) | Go (Golang) | High-concurrency network listener (UDP :5000 / TCP :5001), serves SSE stream `/api/stream`, `/api/stats`, `/api/inject`. |
| **Frame Parser** | [backend/parser.go](file:///c:/Users/chhay/OneDrive/Documents/DRDO%20Project/aws_skyguard_station/backend/parser.go) | Go | Auto-detects 24-byte scaled binary, 40-byte IEEE 754 float32, ASCII Hex, CSV, and JSON datagrams. |
| **Anomaly Engine** | [backend/detector.go](file:///c:/Users/chhay/OneDrive/Documents/DRDO%20Project/aws_skyguard_station/backend/detector.go) | Go | Executes rule-based checks: physical bounds, spike derivatives, ring-buffer freeze variance, Magnus-Tetens psychrometrics, mock Z-score distance. |
| **Frontend UI** | [frontend/src/app/page.js](file:///c:/Users/chhay/OneDrive/Documents/DRDO%20Project/aws_skyguard_station/frontend/src/app/page.js) | Next.js 14 + React + Lucide | Real-time monitoring dashboard, gauge rendering, anomaly alert timeline, SHAP attribution graphs, fault injector. |
| **Python GUI (Alt)** | [aws_skyguard_main.py](file:///c:/Users/chhay/OneDrive/Documents/DRDO%20Project/aws_skyguard_station/aws_skyguard_main.py) | Python + Tkinter + Matplotlib | Native Tkinter GUI alternative for station config, live plotting, and direct serial/UDP monitoring. |
| **Edge AI Module** | [esp32_edge/skyguard_edge_ai.h](file:///c:/Users/chhay/OneDrive/Documents/DRDO%20Project/aws_skyguard_station/esp32_edge/skyguard_edge_ai.h) | C / C++ | Embedded header for ESP32 microcontroller edge screening. |
| **Build Executable** | [AWS_SkyGuard_Station.spec](file:///c:/Users/chhay/OneDrive/Documents/DRDO%20Project/aws_skyguard_station/AWS_SkyGuard_Station.spec) / [build_skyguard_native.py](file:///c:/Users/chhay/OneDrive/Documents/DRDO%20Project/aws_skyguard_station/build_skyguard_native.py) | PyInstaller | Packages `desktop/app.py`, `aws-telemetry-backend.exe`, and `frontend/out` into standalone `AWS_SkyGuard_Station.exe`. |

---

## 3. Communication Protocols, Ports & Ingestion Formats

- **Network Ingestion Protocols**:
  - **UDP**: Port **`5000`** (Default live LAN listener).
  - **TCP**: Port **`5001`** (Fallback TCP stream listener).
  - **HTTP Server**: Port **`8080`** (Serves REST API and Server-Sent Events SSE at `http://127.0.0.1:8080/api/stream`).
- **Core Meteorological Fields**:
  1. `DryBulbTemp` ($^\circ\text{C}$) — Temperature
  2. `PressureHpa` ($\text{hPa}$) — Atmospheric Pressure
  3. `RelHumidity` ($\%$) — Relative Humidity
- **Binary Frame Layout (24-byte, Sync `0xAA 0x55`)**:
  - `[0:2]`: Sync Header (`0xAA 0x55`)
  - `[2:6]`: `Time_Inst` (`uint32`)
  - `[6:8]`: `Direction` (`uint16`)
  - `[8:10]`: `Speed` (`uint16`, scale 0.1)
  - `[10:12]`: `Dry Bulb Temp` (`int16`, signed, scale 0.1)
  - `[12:14]`: `Wet Bulb Temp` (`int16`, signed, scale 0.1)
  - `[14:16]`: `Rel. Humidity` (`uint16`, scale 0.1)
  - `[16:18]`: `Solar Radiation` (`uint16`, scale 1.0)
  - `[18:20]`: `Rainfall` (`uint16`, scale 0.1)
  - `[20:24]`: `Pressure` (`uint32`, scale 0.01)

---

## 4. Current Rule-Based Anomaly Logic vs. Missing SIH Requirements

### Existing Logic (`detector.go`)
- **Hard Limit Check**: If $T < -40^\circ\text{C}$ or $T > 55^\circ\text{C}$, $\text{RH} \notin [0, 100]$, $P \notin [900, 1080]$.
- **Spike Derivative**: If $|\Delta T| / \Delta t > 5^\circ\text{C/s}$, $|\Delta \text{RH}| / \Delta t > 15\%/\text{s}$, $|\Delta P| / \Delta t > 10\text{ hPa/s}$.
- **Frozen Sensor**: If variance across 10 samples equals 0.
- **Psychrometric Equilibrium**: Uses Magnus-Tetens formula to compute theoretical saturation vapor pressure.
- **Mock Z-Score**: Computes Euclidean distance $d^2 = Z_T^2 + Z_H^2 + Z_P^2$.

### Identified Limitations & Gaps (SIH PS-26073)
1. **No Trained ML Model**: Uses hardcoded heuristic limits instead of a trained model fitted on historical AWS observations.
2. **No Offline Model Pipeline**: Lacks reproducible dataset loading, feature engineering, model training (`train.py`), model validation (`evaluate.py`), and model artifact persistence (`models/anomaly_model.pkl`).
3. **Hardcoded SHAP & LIME Strings**: SHAP attributions and LIME formulas are hardcoded template strings rather than derived from tree decision paths.
4. **No Calibrated Probabilistic Confidence**: Confidence scores are assigned static values (e.g., `95.0`, `99.0`).
5. **No Edge Model Quantization**: C-header `skyguard_edge_ai.h` lacks decision tree thresholds generated from the trained ML model.

---

## 5. Integration Roadmap & Strategy

### What Will Be Retained
- Existing standalone PyInstaller build workflow (`AWS_SkyGuard_Station.exe`).
- Existing PyWebView wrapper (`desktop/app.py`).
- Existing Go backend network ingestion (`UDP :5000` / `TCP :5001`) and REST/SSE endpoints (`:8080`).
- Existing Next.js frontend UI components (`frontend/src/app/page.js`).

### What Will Be Added / Replaced
- **[NEW] `aws_skyguard_station/skyguard_ai/` Subsystem**:
  - `data/`: Dataset loaders for `aws_weather_parameters.txt`, `aws_sample_input.txt`, `radiosonde_profile_10000.txt`.
  - `simulation/anomaly_injector.py`: Ground-truth labeled synthetic anomaly generator (Spike, Drop, Freeze, Drift, Noise, Missing, Multivariate).
  - `training/feature_engineering.py`: Time-series rolling features, rate of change, psychrometric spread, and temporal deltas.
  - `train.py` & `evaluate.py`: Chronological dataset splitting (70/15/15), Isolation Forest training, model evaluation (Precision, Recall, F1, FPR per anomaly type), and artifact saving (`anomaly_model.pkl`, `scaler.pkl`, `metadata.json`).
  - `inference/inference_service.py`: Real-time FastAPI / ONNX inference server running on `http://127.0.0.1:5050` returning genuine ML scores & tree-path SHAP feature attributions.
  - `edge/model_converter.py`: Exports trained tree thresholds into `esp32_edge/skyguard_edge_model.h`.
- **[MODIFY] `backend/detector.go` & `aws_skyguard_main.py`**:
  - Replaces hardcoded logic with real HTTP/ONNX queries to the ML inference service.
  - Computes non-fake transducer sensor health decay percentages and maintenance alerts.
- **[NEW] Project Documentation**:
  - `PROJECT_INSPECTION.md`
  - `FEATURE_DOCUMENTATION.md`
  - `SIH_REQUIREMENT_MAPPING.md`
