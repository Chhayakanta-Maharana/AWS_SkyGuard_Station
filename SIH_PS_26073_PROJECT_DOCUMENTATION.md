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
    classDef mainBox fill:#ffffff,stroke:#e11d48,stroke-width:2px,color:#0f172a,font-weight:bold,rx:5px,ry:5px;
    classDef blueBox fill:#ffffff,stroke:#0284c7,stroke-width:2px,color:#0f172a,font-weight:bold,rx:5px,ry:5px;
    classDef subBox fill:#f8fafc,stroke:#64748b,stroke-width:1.5px,color:#334155,rx:5px,ry:5px;
    classDef diamondBox fill:#ffffff,stroke:#10b981,stroke-width:2px,color:#0f172a,font-weight:bold;
    classDef circleBox fill:#f0fdf4,stroke:#10b981,stroke-width:1.5px,color:#0f172a,shape:circle;

    %% 1. THE TOP CURVE (Left to Right)
    subgraph TopCurve [ ]
        direction LR
        INP["AWS SENSOR INPUT<br/>UDP 5000 / TCP 5001"]:::mainBox
        ING["DATA INGESTION"]:::blueBox
        FEAT["FEATURE PIPELINE"]:::mainBox
        INP --> ING --> FEAT
    end

    %% 2. THE RIGHT DROP (Top Right going Down)
    subgraph RightDrop [ ]
        direction TD
        VEC{"14-D Feature<br/>Vector"}:::diamondBox
        ENG["HYBRID ANOMALY<br/>ENGINE"]:::blueBox
        VEC --> ENG
    end
    FEAT --> VEC

    %% 3. THE STEM (Middle going Down)
    subgraph Stem [ ]
        direction TD
        XAI["EXPLAINABLE AI<br/>(XAI)"]:::mainBox
        HEAL["SELF-HEALING<br/>ENGINE"]:::mainBox
        DASH["NEXT.JS<br/>DASHBOARD<br/>SSE Stream (:8080)"]:::blueBox
        XAI --> HEAL --> DASH
    end
    ENG ----->|Real-time Scoring Transfer| XAI

    %% --- FORCE THE QUESTION MARK (?) LAYOUT ---
    %% Push XAI exactly under ING (center)
    ING ~~~ XAI
    %% Push the left side away to curve it
    INP ~~~ INV_SPACE[ ] ~~~ XAI
    
    %% --- SUB-BRANCHES (Kept exactly as they were without adding new things) ---
    ING --> ING1["<b>Packet Decoder</b><br/>0xAA 0x55 Binary Decode"]:::subBox
    ING1 --> ING2["<b>Checksum Validation</b><br/>Checksum-8 Verification"]:::subBox
    ING2 --> ING3["<b>Descaling Output</b><br/>IEEE 754 Float32"]:::subBox
    ING3 --> ING4["<b>Canonical Struct</b><br/>JSON Serialization"]:::subBox

    FEAT --> FEAT1["<b>Rolling Buffer</b><br/>μ = Σ x_i / N"]:::subBox
    FEAT1 --> FEAT2["<b>Rate of Change</b><br/>Δx / Δt Gradients"]:::subBox
    FEAT2 --> FEAT3["<b>Cyclic Encodings</b><br/>sin(2πh/24)"]:::subBox

    ENG --> ENG1["<b>Physical Bounds QC</b><br/>T ∈ [-40, 55], σ² < 10⁻⁵"]:::subBox
    ENG1 --> ENG2["<b>Magnus-Tetens Thermo</b><br/>e_s(T) = 6.112*exp(...)<br/>e = e_s - AP(ΔT)"]:::subBox
    ENG2 --> ENG3["<b>Isolation Forest ML</b><br/>S(x,n) = 2^(-E(h(x))/c(n))"]:::subBox

    XAI --> XAI1["<b>SHAP Attribution</b><br/>Feature % Contribution"]:::subBox
    XAI1 --> XAI2["<b>Severity Classifier</b><br/>LOW / MED / HIGH"]:::subBox
    XAI2 --> XAI3["<b>Confidence Metric</b><br/>0.0% - 100.0%"]:::subBox
    XAI3 --> XAI4["<b>Root-Cause Generator</b><br/>Text Diagnostics"]:::subBox

    HEAL --> HEAL1["<b>Health Decay Meter</b><br/>Cumulative Density"]:::subBox
    HEAL1 --> HEAL2["<b>EWMA Imputation</b><br/>x_t = α·y_t + (1-α)·x_{t-1}"]:::subBox
    HEAL2 --> HEAL3["<b>Inverse Psychrometric</b><br/>Physical Estimation"]:::subBox
    HEAL3 --> HEAL4["<b>Online Learning</b><br/>Update Baseline (N=500)<br/>Recalibrate τ"]:::subBox

    DASH --> C1(("Live<br/>Gauges")):::circleBox
    DASH --> C2(("Fault<br/>Bench")):::circleBox
    DASH --> C3(("Healed<br/>Stream")):::circleBox

    %% Styling to hide construction boxes
    style TopCurve fill:none,stroke:none
    style RightDrop fill:none,stroke:none
    style Stem fill:none,stroke:none
    style INV_SPACE fill:none,stroke:none,color:none
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
