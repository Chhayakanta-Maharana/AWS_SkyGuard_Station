# AWS SkyGuard Station - System Reference Manual & Use Cases

This manual documents the network communication protocols, core meteorological data schemas, mathematical anomaly models, and practical operational use cases for the **AWS SkyGuard Station** application.

---

## 1. Network Ingestion & Meteorological Data Schema

The Go ingestion backend contains a high-throughput, multi-protocol deserializer supporting **both UDP (Port 5000)** and **TCP (Port 5001)** socket streams (as well as direct serial/file playback) with zero heap allocation per packet.

### 🎯 Core Problem Statement Meteorological Parameters
In strict compliance with **SIH PS-26073 / DRDO Guidelines**, SkyGuard AI performs real-time quality control, multivariate physics verification, and anomaly detection focused on the 3 primary atmospheric parameters:

| Parameter | Unit | Symbol | Physical Range | Validation & QC Checks |
| :--- | :---: | :---: | :---: | :--- |
| **Temperature** | $^\circ\text{C}$ | $T$ | $-40.0^\circ\text{C} \text{ to } +55.0^\circ\text{C}$ | Temporal gradient $|\Delta T/\Delta t| \le 3.5^\circ\text{C/s}$, rolling variance $\sigma^2 > 0$ |
| **Atmospheric Pressure** | $\text{hPa}$ | $P$ | $850.0\text{ hPa to } 1080.0\text{ hPa}$ | Barometric step $|\Delta P/\Delta t| \le 6.0\text{ hPa/s}$, hydrostatic sanity |
| **Relative Humidity** | $\%$ | $\text{RH}$ | $0.0\% \text{ to } 100.0\%$ | Psychrometric saturation limit, step $|\Delta\text{RH}/\Delta t| \le 25\%/\text{s}$ |

---

### 📡 Network Protocol & Frame Ingestion Formats

The backend auto-detects and processes multiple industrial telemetry formats over **UDP (Port 5000)** and **TCP (Port 5001)**:

#### Standard Scaled Binary Layout (`0xAA55` Sync Header)
* **Sync Header** (2 bytes): `0xAA 0x55` (identifies active AWS packet frame)
* **Timestamp (`Time_Inst`)** (4 bytes): `uint32` Unix epoch timestamp
* **Temperature (`Dry Bulb Temp`)** (2 bytes): `int16` scaled by $\times 0.1$ ($^\circ\text{C}$)
* **Relative Humidity (`Rel. Humidity`)** (2 bytes): `uint16` scaled by $\times 0.1$ ($\%$)
* **Pressure (`Pressure_hPa`)** (4 bytes): `uint32` scaled by $\times 0.01$ ($\text{hPa}$)
* **Checksum8** (1 byte): Sum of preceding bytes modulo 256 for bit-corruption verification.

*(Auxiliary meteorological channels such as Wind Speed, Wind Direction, Wet Bulb, and Solar Radiation are also parsed when present).*

---

## 2. Statistical Anomaly, Physical QC & Explainable AI (XAI) Models

Every telemetry packet received over UDP or TCP undergoes simultaneous multi-tier evaluation:

1. **Univariate Hard-Limit Boundary Check**:
   Detects out-of-bounds sensor values based on WMO climatological limits (e.g., $T \notin [-40^\circ\text{C}, 55^\circ\text{C}]$ or $\text{RH} \notin [0\%, 100\%]$).

2. **Rate-of-Change Gradient Checks (Spikes / Drops)**:
   Computes temporal derivatives:
   $$\text{Gradient} = \frac{|\Delta x|}{\Delta t}$$
   If temperature rises by $>3.5^\circ\text{C}$ in a single second, a `TEMPERATURE_SPIKE` alert is triggered.

3. **Zero-Variance Lockup Validation (Frozen Sensor)**:
   Monitors a rolling ring buffer of 10 consecutive observations. If variance $\sigma^2 = 0$, a `SENSOR_FREEZE` alert is triggered.

4. **Multivariate Thermodynamic Consistency (Magnus-Tetens Equation)**:
   Validates moisture-thermal physical equilibrium:
   $$E_s(T) = 6.112 \cdot \exp\left( \frac{17.67 \cdot T}{T + 243.5} \right)$$
   $$E = \frac{\text{RH}}{100.0} \cdot E_s(T)$$
   $$T_d = \frac{243.5 \cdot \ln(E / 6.112)}{17.67 - \ln(E / 6.112)}$$
   If reported temperature falls below the theoretical dew point ($T < T_d$), a **Thermodynamic Inconsistency** alert is flagged.

5. **Joint Multivariate Standardized Distance ($D^2$)**:
   Standardizes the joint vector across all three parameters:
   $$D^2 = z_T^2 + z_P^2 + z_{\text{RH}}^2$$
   If $D^2 > 9.0$ ($>3\sigma$ in joint parameter space), a multivariate anomaly is reported.

6. **Explainable AI (XAI) Root-Cause Attribution**:
   Identifies the primary contributing sensor channel:
   $$\text{Primary Driver} = \arg\max |z_i|$$
   Generates transparent numeric SHAP feature weights and plain-English diagnostic explanations.

7. **Self-Healing Linear Weighted Imputation (LWMA)**:
   Substitutes anomalous values in real time using a Linear Weighted Moving Average across the last $N=10$ verified clean samples:
   $$\hat{x}_t = \frac{\sum_{i=1}^{N} i \cdot x_{\text{clean}, i}}{\sum_{i=1}^{N} i}$$
   This quadratic linear weighting gives the highest confidence to the most recent clean baseline while preventing error propagation.

---

## 3. Operational Use Cases & Fault Scenarios

### 🔬 Use Case 1: Extreme Temperature Spike (+25°C Sensor Glitch)
* **Observation**: Station suddenly reports a temperature jump from $24.0^\circ\text{C}$ to $49.0^\circ\text{C}$ within 1 second while Pressure ($1012\text{ hPa}$) and Humidity ($65\%$) remain stable.
* **AI Diagnosis**: `🚨 CRITICAL: SENSOR_TRANSIENT_SPIKE` (Temporal gradient $25^\circ\text{C/s} \gg 3.5^\circ\text{C/s}$ limit).
* **Self-Healing Action**: Imputes $\hat{T} = 24.2^\circ\text{C}$ using clean historical LWMA; prevents false heatwave warnings in forecasting systems.

---

### 🔬 Use Case 2: Barometric Sensor Freezing (ADC Lockup / Stuck Diaphragm)
* **Observation**: Atmospheric pressure stays pegged at exactly $1013.25\text{ hPa}$ for 15 consecutive samples with $\sigma^2 = 0.0$, while Temperature and Humidity fluctuate naturally.
* **AI Diagnosis**: `⚠️ WARNING: SENSOR_FREEZE` (Pressure transducer variance below $10^{-5}$ threshold).
* **Self-Healing Action**: Generates maintenance alert work-order and substitutes hydrostatic estimated pressure.

---

### 🔬 Use Case 3: Psychrometric Violation ($T_{\text{dry}} < T_d$ or RH > 100%)
* **Observation**: Reported $T = 18.0^\circ\text{C}$ with Reported $\text{RH} = 99\%$ and $T_{\text{wet}} = 22.0^\circ\text{C}$.
* **AI Diagnosis**: `🚨 CRITICAL: PSYCHROMETRIC_INCONSISTENCY` (Wet bulb exceeds dry bulb; violates 2nd Law of Thermodynamics).
* **Self-Healing Action**: Reconstructs physical equilibrium value via inverse Magnus-Tetens equation.

---

### 🔬 Use Case 4: Gradual Calibration Drift (+0.2°C/hour)
* **Observation**: Slow sensor degradation creating a persistent positive temperature bias over several hours without breaching hard climatological bounds.
* **AI Diagnosis**: `⚠️ WARNING: SENSOR_DRIFT` (Detected by unsupervised Isolation Forest anomaly scoring).
* **Self-Healing Action**: Triggers transducer health decay meter ($<70\%$) and schedules field recalibration.

---

### 🔬 Use Case 5: Genuine Severe Weather (Thunderstorm Pressure Drop vs Sensor Error)
* **Observation**: Rapid pressure drop of $-4\text{ hPa}$ accompanied by a simultaneous $+35\%$ spike in relative humidity and a $-6^\circ\text{C}$ temperature drop.
* **AI Diagnosis**: `✅ NOMINAL (Severe Weather Signature)`: Cross-channel correlation confirms genuine convective gust-front rather than instrument malfunction.
* **Self-Healing Action**: No artificial imputation applied; raw meteorological extreme is preserved for NWP models.

---

### 🔬 Use Case 6: Telemetry Bit Corruption & Communication Dropout
* **Observation**: Malformed byte stream or Checksum-8 mismatch received over UDP/TCP link.
* **AI Diagnosis**: `⚠️ WARNING: COMMUNICATION_CORRUPTION` (Frame length or CRC validation failure).
* **Self-Healing Action**: Drops corrupted frame; sustains downstream stream continuity via LWMA buffer.

---

## 4. How to Run & Verify the Application

### A. Run Go Telemetry Backend (UDP :5000 / TCP :5001 / SSE :8080)
1. Open a terminal in `backend/`:
2. Run:
   ```bash
   go run .
   ```
   *(Note: Always use `go run .` with the dot so all package files `main.go`, `detector.go`, `db.go`, `parser.go`, `simulator.go` compile together. You can also double-click `aws-telemetry-backend.exe`).*
3. The backend initializes:
   - **UDP Ingestion Listener**: Binds to `0.0.0.0:5000`
   - **TCP Stream Listener**: Binds to `0.0.0.0:5001`
   - **SSE Stream & REST API**: Serves on `http://127.0.0.1:8080/api/stream`

---

### B. Run Next.js Reactive Web Dashboard
1. Open a terminal in `frontend/`:
2. Run:
   ```bash
   npm run dev
   ```
3. Open **`http://localhost:3000`** in your browser to view real-time telemetry, radial dials, radar charts, and interactive fault injector.

---

### C. Run Standalone Desktop Executable
Double-click **`dist/AWS_SkyGuard_Station.exe`** for instant zero-config desktop ground station deployment.
