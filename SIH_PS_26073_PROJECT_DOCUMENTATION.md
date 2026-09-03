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
    %% Styling matching the reference image layout
    classDef redBox fill:#ffffff,stroke:#e11d48,stroke-width:2px,color:#0f172a,font-weight:bold,rx:5px,ry:5px;
    classDef blueBox fill:#ffffff,stroke:#0284c7,stroke-width:2px,color:#0f172a,font-weight:bold,rx:5px,ry:5px;
    classDef subBox fill:#f8fafc,stroke:#64748b,stroke-width:1.5px,color:#334155,rx:5px,ry:5px;
    classDef diamondBox fill:#ffffff,stroke:#10b981,stroke-width:2px,color:#0f172a,font-weight:bold;
    classDef circleBox fill:#f0fdf4,stroke:#10b981,stroke-width:1.5px,color:#0f172a,shape:circle;
    classDef centerText fill:none,stroke:none,color:#0f172a,font-style:italic,font-size:14px;

    %% Left Spine
    INP["AWS SENSOR INPUT"]:::redBox
    ING["DATA INGESTION"]:::blueBox
    FEAT["FEATURE PIPELINE"]:::redBox
    VEC{"14-D Feature<br/>Vector"}:::diamondBox
    ENG["HYBRID ANOMALY<br/>ENGINE"]:::blueBox

    %% Left Branches
    ING_1["Binary/CSV Parser"]:::subBox
    ING_2["Checksum Validation"]:::subBox
    ING_3["Descaling Output"]:::subBox
    ING_4["Canonical Struct"]:::subBox

    FEAT_1["Rolling Buffer"]:::subBox
    FEAT_2["Rate of Change (ΔT)"]:::subBox
    FEAT_3["Cyclic Encodings"]:::subBox

    ENG_1["Physical Bounds QC"]:::subBox
    ENG_2["Magnus-Tetens Thermo"]:::subBox
    ENG_3["Isolation Forest ML"]:::subBox

    %% Right Spine
    XAI["EXPLAINABLE AI<br/>(XAI)"]:::redBox
    HEAL["SELF-HEALING<br/>ENGINE"]:::redBox
    DASH["NEXT.JS<br/>DASHBOARD"]:::blueBox

    %% Right Branches
    XAI_1["SHAP Attribution"]:::subBox
    XAI_2["Feature Contributions"]:::subBox
    XAI_3["Confidence Classifier"]:::subBox
    XAI_4["Diagnostic Text"]:::subBox

    HEAL_1["Sensor Health Decay"]:::subBox
    HEAL_2["EWMA Imputation"]:::subBox
    HEAL_3["Inverse Psychrometric"]:::subBox
    HEAL_4["Online Learning"]:::subBox

    C1(("Live<br/>Gauges")):::circleBox
    C2(("Fault<br/>Bench")):::circleBox
    C3(("Healed<br/>Stream")):::circleBox

    %% Center text node
    CENTER["SkyGuard AI processes AWS telemetry<br/>through a six-phase end-to-end pipeline —<br/>from raw sensor signals to<br/>interactive self-healing dashboard."]:::centerText

    %% Wiring Left Side
    INP --> ING
    ING --> ING_1
    ING_1 --> ING_2
    ING_2 --> ING_3
    ING_3 --> ING_4
    
    ING --> FEAT
    FEAT --> FEAT_1
    FEAT_1 --> FEAT_2
    FEAT_2 --> FEAT_3
    
    FEAT --> VEC
    VEC --> ENG
    ENG --> ENG_1
    ENG_1 --> ENG_2
    ENG_2 --> ENG_3

    %% Wiring Right Side
    XAI --> XAI_1
    XAI_1 --> XAI_2
    XAI_2 --> XAI_3
    XAI_3 --> XAI_4

    XAI --> HEAL
    HEAL --> HEAL_1
    HEAL_1 --> HEAL_2
    HEAL_2 --> HEAL_3
    HEAL_3 --> HEAL_4

    HEAL --> DASH
    DASH --> C1
    DASH --> C2
    DASH --> C3

    %% Cross connection (Matches the long swooping arrow in the image)
    ENG_3 ---->|Real-time Scoring Transfer| XAI
    
    %% Invisible links to align the center text visually between the two flows
    FEAT_3 ~~~ CENTER
    CENTER ~~~ XAI_1
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
