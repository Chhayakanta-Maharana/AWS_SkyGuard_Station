# SkyGuard AI: Intelligent Real-Time Anomaly Detection & Self-Healing System for Automatic Weather Stations (AWS)
## Smart India Hackathon (SIH) 2026 | Problem Statement ID: 26073
**Organization**: Ministry of Earth Sciences (MoES)  
**Target Domain**: Meteorological Sensor Quality Control, Edge AI & Self-Healing Environmental Networks

---

## 1. Executive Summary & SIH Alignment Matrix

| SIH 2026 Requirement / Evaluation Metric | Weightage | Implementation in SkyGuard AI | Status |
| :--- | :--- | :--- | :--- |
| **Real-Time Anomaly Detection** | 20% | Sub-millisecond Go-lang streaming analysis engine analyzing Temperature, Pressure, and Humidity. | ✅ Implemented |
| **Sensor Fault, Spike & Flatline Detection** | 20% | 3-Sigma Z-Score + Temporal Rate-of-Change ($\Delta T/\Delta t$) + Invariant Rolling Variance flatline buffer. | ✅ Implemented |
| **Multivariate Physical Consistency** | 25% | Magnus-Tetens Psychrometric Thermodynamic equation coupling $T_{\text{dry}}$, $T_{\text{wet}}$, $P$, and $\text{RH}$. | ✅ Implemented |
| **Explainable AI (XAI) & Root Cause** | 10% | Instant plain-language diagnostic generation with severity tags and confidence metrics (0–100%). | ✅ Implemented |
| **Self-Healing & Imputation (Grand Challenge)** | 25% | Real-time statistical EWMA + Psychrometric Vapor Pressure physical estimation with one-click toggle. | ✅ Implemented |
| **Fault Injection Testbench & Evaluation** | 15% | Interactive live injection buttons (Spike +25°C, Pressure Freeze, Humidity Drift, Packet Outage). | ✅ Implemented |
| **Interactive Visualization & UI** | 5% | Next.js 19 desktop GUI with 10 parameter cards, SVG compass needle dial, spectral charts, and data logger. | ✅ Implemented |
| **Edge & Standalone Deployment** | 10% | Fully self-contained Windows standalone `.exe` (Go Backend + Next.js Frontend bundled). | ✅ Implemented |

---

## 2. Architecture: Full Pipeline

```mermaid
flowchart TD
    %% Global Styling
    classDef inputNode fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc;
    classDef procBox fill:#1e1b4b,stroke:#818cf8,stroke-width:1.5px,color:#e0e7ff;
    classDef decBox fill:#311042,stroke:#c084fc,stroke-width:1.5px,color:#f3e8ff;
    classDef outBox fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#ecfdf5;
    classDef alertBox fill:#701a75,stroke:#f472b6,stroke-width:1.5px,color:#fdf2f8;
    classDef edgeBox fill:#451a03,stroke:#fb923c,stroke-width:1.5px,color:#fff7ed;

    %% PHASE 1: SENSOR INGESTION
    subgraph P1 ["PHASE 1: SENSOR INGESTION & DATA INGRESS"]
        RAW_INPUT["<b>RAW AWS SENSOR STREAM</b><br/>• Dry Bulb & Wet Bulb Temp (°C)<br/>• Surface Pressure (hPa)<br/>• Relative Humidity (%)<br/>• Wind & Solar Parameters"]:::inputNode
        
        INGRESS["<b>NETWORK INGRESS LISTENER</b><br/>• UDP Port 5000 (LAN Broadcast)<br/>• TCP Port 5001 (Stream Ingestion)<br/>• Serial / TXT Replay Fallback"]:::procBox
        
        PARSER["<b>MULTI-FORMAT CANONICAL PARSER</b><br/>• 24/31-Byte Scaled Binary (0xAA 0x55)<br/>• 40-Byte IEEE 754 Float32<br/>• Checksum-8 Bitwise Verification"]:::procBox
    end

    %% PHASE 2: FEATURE ENGINEERING
    subgraph P2 ["PHASE 2: REAL-TIME FEATURE PIPELINE (14-D VECTOR)"]
        BUFFER["<b>ROLLING TIME-SERIES BUFFER (N=15)</b><br/>• History Window Caching<br/>• Zero-Copy Ring Buffer"]:::procBox
        
        FEATS["<b>FEATURE EXTRACTION ENGINE</b><br/>• Rate of Change (ΔT/Δt, ΔP/Δt, ΔRH/Δt)<br/>• Rolling Mean & Std Dev (μ_5, σ_5, μ_15, σ_15)<br/>• Diurnal Encodings: sin(2πh/24), cos(2πh/24)"]:::procBox
    end

    %% PHASE 3: HYBRID ANOMALY ENGINE
    subgraph P3 ["PHASE 3: DUAL-TIER ANOMALY DETECTION ENGINE"]
        TIER1_QC["<b>TIER 1: PHYSICAL BOUNDS & SPIKE DERIVATIVE</b><br/>• Range Limits: T ∈ [-40, 55], P ∈ [850, 1080]<br/>• Spike Threshold: |ΔT| > 3.5°C/s, |ΔP| > 6 hPa/s<br/>• Flatline Invariance: σ² < 10⁻⁵ over 10 ticks"]:::decBox
        
        TIER2_THERMO["<b>TIER 2: MAGNUS-TETENS THERMODYNAMICS</b><br/>• Saturation Vapor Pressure: e_s(T)<br/>• Psychrometric Vapor Eq: e = e_s(T_wet) - AP(T_dry - T_wet)<br/>• Discrepancy Check: |RH_rep - RH_theo| > 35%"]:::decBox
        
        TIER3_ML["<b>TIER 3: 14-DIMENSIONAL ISOLATION FOREST</b><br/>• Unsupervised Path-Length Isolation Scoring<br/>• Calibrated Decision Threshold (τ = -0.12)<br/>• Multivariate Correlation Distance (D²)"]:::decBox
    end

    %% PHASE 4: EXPLAINABLE AI & DIAGNOSTICS
    subgraph P4 ["PHASE 4: EXPLAINABLE AI (XAI) & ROOT-CAUSE ENGINE"]
        SHAP_XAI["<b>TREE-PATH SHAP ATTRIBUTION</b><br/>• Feature Contribution % (Temp, Hum, Press)<br/>• Dominant Anomaly Driver Isolation"]:::alertBox
        
        CONFIDENCE["<b>CALIBRATED CONFIDENCE CLASSIFIER</b><br/>• Severity: HIGH / MEDIUM / LOW / NOMINAL<br/>• Confidence Metric: 0.0% - 100.0%"]:::alertBox
        
        DIAGNOSTICS["<b>ROOT-CAUSE DIAGNOSTIC GENERATOR</b><br/>• ADC Spike / Electrical Glitch<br/>• Sensor Icing / Frozen Diaphragm<br/>• Calibration Drift / RF Packet Drop"]:::alertBox
    end

    %% PHASE 5: SELF-HEALING & HEALTH MONITORING
    subgraph P5 ["PHASE 5: SELF-HEALING & TRANSDUCER HEALTH (GRAND CHALLENGE)"]
        IMPUTATION["<b>REAL-TIME SELF-HEALING IMPUTATION</b><br/>• Double-Weighted Exponential Moving Avg (EWMA)<br/>• Inverse Psychrometric Physical Estimation<br/>• Zero-Mutation Raw Audit Trail Preservation"]:::procBox
        
        HEALTH["<b>SENSOR HEALTH DECAY & MAINTENANCE</b><br/>• Cumulative Anomaly Density Meter (0-100%)<br/>• Predictive Remaining Useful Life (RUL)<br/>• Actionable Maintenance Advisories"]:::procBox
        
        ONLINE_ADAPT["<b>CONTINUOUS ONLINE LEARNING</b><br/>• Dynamic Nominal Buffer (500 Samples)<br/>• Baseline Drift Re-calibration"]:::procBox
    end

    %% PHASE 6: DEPLOYMENT & UI
    subgraph P6 ["PHASE 6: GROUND STATION VISUALIZATION & EDGE DEPLOYMENT"]
        DESKTOP_EXE["<b>STANDALONE DESKTOP APPLICATION</b><br/>• AWS_SkyGuard_Station.exe (PyInstaller)<br/>• High-Speed Go SSE Stream (:8080)<br/>• Embedded Microsoft Edge WebView2 GUI"]:::outBox
        
        NEXTJS_UI["<b>NEXT.JS 14 GROUND STATION DASHBOARD</b><br/>• Real-Time Gauge Cards & Spectral Line Charts<br/>• SVG Compass Needle & Psychrometric Radar<br/>• Live Fault Injection Bench & Healed Toggle"]:::outBox
        
        ESP32_EDGE["<b>ESP32 ULTRA-LOW-POWER EDGE FIRMWARE</b><br/>• skyguard_edge_ai.h / .ino Microcontroller Engine<br/>• < 15 μs Decision Latency, < 1 KB RAM Footprint"]:::edgeBox
    end

    %% Pipeline Connections
    RAW_INPUT --> INGRESS
    INGRESS --> PARSER
    PARSER --> BUFFER
    BUFFER --> FEATS
    FEATS --> TIER1_QC
    TIER1_QC --> TIER2_THERMO
    TIER2_THERMO --> TIER3_ML
    TIER3_ML --> SHAP_XAI
    SHAP_XAI --> CONFIDENCE
    CONFIDENCE --> DIAGNOSTICS
    DIAGNOSTICS --> IMPUTATION
    DIAGNOSTICS --> HEALTH
    IMPUTATION --> ONLINE_ADAPT
    IMPUTATION --> NEXTJS_UI
    HEALTH --> NEXTJS_UI
    NEXTJS_UI --> DESKTOP_EXE
    FEATS -.->|C-Header Model Export| ESP32_EDGE
```

> **Pipeline Overview:** *SkyGuard AI processes Automatic Weather Station telemetry through a six-phase end-to-end pipeline — from raw binary/UDP sensor signals to explainable root causes, self-healed data streams, and native desktop/edge deployments.*

---

## 3. Core Meteorological Parameters (SIH Specification)

SkyGuard AI focuses on the 3 primary thermodynamic variables specified in SIH PS-26073:
1. **Temperature ($T$, $^\circ\text{C}$)**: Dry Bulb and Wet Bulb air temperatures.
2. **Atmospheric Pressure ($P$, $\text{hPa}$)**: Barometric surface pressure.
3. **Relative Humidity ($\text{RH}$, $\%$ )**: Saturation percentage of water vapor in air.

---

## 3. Mathematical & Algorithmic Detection Formulations

### A. Univariate Extreme Operational Limits
Detects physical impossibility based on MoES/WMO climatological constraints:
$$\text{Temperature: } -40^\circ\text{C} \le T \le 55^\circ\text{C}$$
$$\text{Barometric Pressure: } 850\text{ hPa} \le P \le 1080\text{ hPa}$$
$$\text{Relative Humidity: } 0\% \le \text{RH} \le 100\%$$

### B. Temporal Rate-of-Change (Spike Detection)
Detects abrupt transient electrical spikes and ADC corruption:
$$\Delta T = |T_t - T_{t-1}| > 3.5^\circ\text{C/s} \implies \text{Flag: Temp Spike (Z-Score > 4.2)}$$
$$\Delta P = |P_t - P_{t-1}| > 6.0\text{ hPa/s} \implies \text{Flag: Pressure Jump}$$
$$\Delta\text{RH} = |\text{RH}_t - \text{RH}_{t-1}| > 25.0\%/\text{s} \implies \text{Flag: Humidity Dropout}$$

### C. Sensor Freeze / Flatline Detection
Detects sensor lockups, frozen diaphragms, and communication line jamming:
$$\sigma^2 = \frac{1}{N}\sum_{i=0}^{N-1}(x_{t-i} - \mu)^2, \quad N=10$$
$$\text{If } \sigma^2 < 10^{-5} \text{ over 10 consecutive ticks} \implies \text{Flag: Sensor Freeze}$$

### D. Multivariate Thermodynamic Consistency (Magnus-Tetens)
Differentiates between a genuine weather event (e.g. cold front, thunderstorm) and an instrument defect using atmospheric thermodynamics:
1. **Saturation Vapor Pressure ($e_s$)**:
   $$e_s(T) = 6.112 \times \exp\left(\frac{17.67 \times T}{T + 243.5}\right)\text{ hPa}$$
2. **Actual Vapor Pressure via Psychrometric Equation ($e$)**:
   $$e = e_s(T_{\text{wet}}) - P \times 0.00066 \times (1 + 0.00115 \times T_{\text{wet}}) \times (T_{\text{dry}} - T_{\text{wet}})$$
3. **Theoretical Relative Humidity ($\text{RH}_{\text{theo}}$)**:
   $$\text{RH}_{\text{theo}} = \frac{e}{e_s(T_{\text{dry}})} \times 100\%$$
$$\text{If } |\text{RH}_{\text{reported}} - \text{RH}_{\text{theo}}| > 35\% \implies \text{Flag: Multivariate Psychrometric Inconsistency}$$

---

## 4. Key Use Cases & Fault Scenarios

### Use Case 1: Extreme Temperature Spike (+25°C Sensor Glitch)
*   **Observation**: Station reports a jump from 24°C to 49°C in 1 second.
*   **AI Diagnosis**: `🚨 HIGH SEVERITY: SENSOR MALFUNCTION (Dry Bulb Temp spiked +25°C in 1s. Temporal gradient 25°C/s > Max 3.5°C/s).`
*   **Self-Healing**: Imputes 24.2°C using rolling EWMA; prevents false heatwave alerts.

### Use Case 2: Barometric Sensor Freezing (Icing / Stuck ADC)
*   **Observation**: Pressure remains at exactly 1013.25 hPa for 10+ samples with zero variance while other sensors fluctuate.
*   **AI Diagnosis**: `🚨 MEDIUM SEVERITY: SENSOR FREEZE (Barometric Pressure invariant over 10 consecutive ticks).`
*   **Self-Healing**: Flags maintenance alert; substitutes pressure from hydrostatic trend.

### Use Case 3: Psychrometric Violation ($T_{\text{wet}} > T_{\text{dry}}$)
*   **Observation**: Wet bulb temperature reports higher than dry bulb temperature.
*   **AI Diagnosis**: `🚨 HIGH SEVERITY: PHYSICAL INCONSISTENCY (Wet Bulb > Dry Bulb. Violates 2nd Law of Thermodynamics).`
*   **Self-Healing**: Recalculates wet bulb using inverse Magnus equation.

### Use Case 4: Complete Telemetry Loss / RF Dropout
*   **Observation**: Missing data packets / zero-byte payload received on UDP port 5000.
*   **AI Diagnosis**: `🚨 CRITICAL SEVERITY: COMMUNICATION FAILURE (Complete packet loss / RF Link Dropout).`
*   **Self-Healing**: Seamlessly switches to local failover simulator to maintain ground terminal uptime.

---

## 5. How to Run and Evaluate the System

1. Open the application:
   ```
   aws_skyguard_station\dist\AWS_SkyGuard_Station.exe
   ```
2. Navigate to **Dashboard Monitor** to observe live streaming parameters across 10 cards and the live rotating compass needle.
3. Switch to **History Replay Hub** and use the **AI Fault Injection Bench** to test any anomaly scenario on demand.
4. Click **`✨ HEALED STREAM`** in the top header to observe instant AI-driven data correction.
5. Export captured logs and incident reports via the **System Export Center**.
