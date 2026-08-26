# AWS SkyGuard Station - System Reference Manual

This manual documents the design, data schemas, mathematical models, and deployment setups for the **AWS SkyGuard Station** application.

---

## 1. Data Schema & Frame Layout

The Go backend contains a binary parser that decodes raw packet streams received over the network on **UDP Port 5000** (transmitted by the `DRDO_Launcher.py` or LAN telemetry sender).

### Raw Binary Layout (31 Bytes)
*   **Sync Header** (2 bytes): `0xAA 0x55` (identifies active AWS packet)
*   **Time_Inst** (4 bytes): `uint32` Unix timestamp
*   **Direction** (2 bytes): `uint16` Wind direction bearing (0–359°)
*   **Speed** (2 bytes): `uint16` Wind speed (scale 0.1, in m/s)
*   **Dry Bulb Temp** (2 bytes): `int16` Temperature (scale 0.1, in °C)
*   **Wet Bulb Temp** (2 bytes): `int16` Wet Bulb Temperature (scale 0.1, in °C)
*   **Rel. Humidity** (2 bytes): `uint16` Relative Humidity (scale 0.1, in %)
*   **Solar Radiation** (2 bytes): `uint16` Solar intensity (scale 1.0, in W/m²)
*   **Rainfall** (2 bytes): `uint16` Accumulated precipitation (scale 0.1, in mm)
*   **Pressure (hPa)** (4 bytes): `uint32` Atmospheric pressure (scale 0.01, in hPa)
*   **Checksum8** (1 byte): Sum of all preceding 30 bytes modulo 256.

---

## 2. Statistical Anomaly & Explainable AI (XAI) Models

Every telemetry packet goes through concurrent evaluation:
1.  **Univariate Check**: Detects hard range boundaries (e.g. temperatures $>55^\circ\text{C}$ or relative humidity $<0\%$).
2.  **Rate-of-Change Checks (Spikes)**: Computes temporal gradients ($\Delta x / \Delta t$). If dry bulb temperature jumps by $>5^\circ\text{C}$ in a single second, it triggers a Spike warning.
3.  **Zero-Variance Validation (Freezes)**: Monitors a rolling buffer of 10 observations. If values are frozen (variance is 0), it triggers a sensor freeze alert.
4.  **Multivariate Correlation Inconsistency**:
    Standardizes the joint vector:
    $$D^2 = z_T^2 + z_H^2 + z_P^2$$
    If $D^2 > 9.0$ (exceeding 3 standard deviations in joint space), a joint meteorological anomaly is reported.
5.  **Explainable AI (XAI)**:
    Highlights the primary anomaly driver:
    $$\text{Driver} = \arg\max |z_i|$$
    And generates clean explanations describing the exact thermodynamic/meteorological rule violation.
6.  **Self-Healing Imputation**:
    Replaces anomalous values on-the-fly using a double weighted moving average of clean historical records:
    $$x_{\text{imputed}} = \frac{\sum i \cdot x_{\text{clean}, i}}{\sum i}$$

---

## 3. How to Run the Application

### A. Run Go Backend
1.  Navigate to `aws_skyguard_station/backend/`
2.  Run:
    ```bash
    go run main.go
    ```
3.  The backend starts:
    *   **UDP Listener**: Binds to `0.0.0.0:5000` to receive network frames.
    *   **SSE & Control Server**: Binds to `http://localhost:8080` for the Next.js frontend.
    *   **Simulation Fallback**: If no packets arrive on port 5000 within 3 seconds, it automatically starts playing back `aws_sample_input.txt` so the dashboard remains active.

### B. Run Next.js Frontend
1.  Navigate to `aws_skyguard_station/frontend/`
2.  Run:
    ```bash
    npm run dev
    ```
3.  Access the dashboard on `http://localhost:3000`.
