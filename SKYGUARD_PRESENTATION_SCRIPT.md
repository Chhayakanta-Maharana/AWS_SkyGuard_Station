# SkyGuard AI: Complete Live Demonstration & Presentation Script

**Project Title:** SkyGuard AI — Intelligent Real-Time Anomaly Detection, Spatial Consensus & Self-Healing Telemetry System for Automatic Weather Stations (AWS)  
**Target Jury:** DRDO / SIH Evaluation Committee  
**Demo Architecture:** Direct LAN Cable Ingestion (System A: ESP32 / `lan_data_sender` $\rightarrow$ System B: SkyGuard Base Ground Station)

---

## 🎬 Section 1: Opening Hook & Problem Statement (0:00 – 1:30)

> **Spoken Script (Start with confidence):**  
> *"Good morning, respected judges and panel members. Today, across India and strategic defense installations, over **900+ Automatic Weather Stations (AWS)** operate autonomously in remote, harsh environments—from high-altitude Himalayan sectors to coastal artillery proving grounds like Balasore Range.*
>
> *These stations monitor mission-critical parameters: **Temperature, Barometric Pressure, and Relative Humidity**. However, in real-world deployments, these sensors frequently suffer from **transducer malfunctions, thermal drift, sensor lockups/freezes, communication noise, and calibration degradation**.*
>
> *Traditional meteorological systems rely merely on static threshold limits (e.g., checking if temperature is between -40°C and +55°C). But static rules **completely fail** to detect complex hidden anomalies—such as a sensor freezing at a constant value, rapid rate-of-change micro-spikes, or multivariate sensor drift. When unverified erroneous data enters Numerical Weather Prediction (NWP) models or ballistic fire-control systems, the consequences can be catastrophic.*
>
> *To solve this national-scale challenge, we present **SkyGuard AI** — a production-grade, edge-deployable telemetry intelligence platform that provides **sub-millisecond anomaly detection, Game-Theoretic Explainable AI (SHAP & LIME), real-time self-healing imputation, and geospatial multi-station consensus**."*

---

## 🔌 Section 2: Hardware & Live Direct LAN Transmission Setup (1:30 – 3:00)

> **Action:** Point towards **System A** (Transmitter Laptop) and show the physical **Ethernet LAN Cable** connecting directly to **System B** (Dashboard Station).

```
┌─────────────────────────────────────────────────────────┐          ┌─────────────────────────────────────────────────────────┐
│              SYSTEM A (WEATHER NODE SENDER)             │          │             SYSTEM B (SKYGUARD BASE STATION)            │
│  • ESP32 Hardware Simulator / lan_data_sender.exe       │  Direct  │  • High-Speed Go Telemetry Engine (Port 5000 / 8080)    │
│  • Real Transducer Bit-Packing (AWS-32B Binary Frame)   ├─────────►│  • Sub-millisecond Isolation Forest & Spatial AI       │
│  • Live Anomaly Injection Matrix (Spike, Drift, Freeze) │ LAN Cable│  • Next.js Tactical Telemetry Ground Console            │
└─────────────────────────────────────────────────────────┘          └─────────────────────────────────────────────────────────┘
```

> **Spoken Script:**  
> *"To demonstrate true military and field readiness, we are not using mock web intervals. We have set up a **Direct Hardware-in-the-Loop LAN transmission** between two dedicated machines:*
>
> 1. ***System A (Remote Weather Node / Proving Ground):*** *Simulating an autonomous remote AWS mast. It uses our **`lan_data_sender.exe`** (and companion ESP32 firmware) to pack 32-byte binary telemetry frames adhering to standard WMO/IMD data loggers and broadcast them over raw UDP/TCP sockets.*
> 2. ***System B (SkyGuard Ground Station):*** *Receives the binary packets on port `5000`, parses and validates CRC checksums in $<0.2\text{ ms}$, executes the AI diagnostic pipeline, and streams real-time updates to our command console.*
>
> *Let me demonstrate injecting live anomalies directly from System A, and observe how System B responds in real-time."*

---

## 🖥️ Section 3: Page-by-Page Console Breakdown & Live Demo

---

### 📍 PAGE 1: Live Real-Time Telemetry & Core AI Diagnostic Console
> **Action:** Click on **Sidebar Tab 1: Live Telemetry**. Show live streaming parameters updating at 1 Hz over LAN.

#### Key Components to Point Out on Screen:

1. **Live Transducer Parameter Cards:**
   * **Dry-Bulb Temperature ($T$ in °C)**, **Barometric Pressure ($P$ in hPa)**, **Relative Humidity ($\text{RH}$ in %)**, Wet-Bulb Temp, Wind Speed, and Solar Radiation.
   * Highlight that data is ingesting live with exact timestamps and decoded binary precision.

2. **2-Tier Hybrid AI Anomaly Engine:**
   * **Tier-1 Embedded Go Engine ($<1\text{ ms}$ latency):** Hard physical boundaries, temporal rate-of-change derivatives ($\Delta T/\Delta t$), and 10-point rolling window freeze checks.
   * **Tier-2 Deep Machine Learning (Isolation Forest):** 14 rolling time-series features analyzing multi-parameter correlations (e.g. Clausius-Clapeyron dew-point physical consistency).

3. **Explainable AI (XAI) — Tree SHAP Attribution Bar Chart:**
   * *What to explain to Judges:* *"Black-box AI is unacceptable in defense operations. When an anomaly is detected, our **Tree SHAP engine** computes game-theoretic Shapley values, showing the exact percentage contribution of each feature (e.g., Temperature Delta: 84%, Humidity: 10%, Pressure: 6%). The operator instantly knows why the AI flagged it."*

4. **Explainable AI (XAI) — LIME & Natural Language Root-Cause Diagnostic:**
   * Converts complex mathematical anomalies into plain, actionable human diagnostics:  
     *e.g., "SUDDEN TEMPERATURE SPIKE: Rate of change (+6.8°C/sec) exceeds physical convective limits."*

5. **Self-Healing AI (Real-Time Temporal Imputation):**
   * Corrupted or anomalous readings are never deleted or left blank. Our **Exponential Moving Decaying Imputer** calculates the true physical reconstruction in real-time, allowing downstream forecasting models to continue running without interruption.

6. **Predictive Maintenance & Transducer Health Score (0–100%):**
   * Tracks degradation risk and sensor wear. Point out the **Sensor Health Scorecard** ($T: 98.5\%$, $P: 99.1\%$, $\text{RH}: 97.4\%$) and actionable maintenance advice (e.g., *"Transducers nominal. Scheduled maintenance valid for 180 days"*).

---

### 🌐 PAGE 2: Multi-AWS Cloud Spatial Consensus & Mesoscale Hub
> **Action:** Click on **Sidebar Tab 2: Spatial Grid / Consensus**.

#### Addressing the 900+ Station Scalability:
> **Spoken Script:**  
> *"A critical question in national networks is: **How do we compare and validate data when there are 900+ AWS stations across India?** Comparing all 900 stations simultaneously is meteorologically meaningless because weather in Kashmir has zero correlation with weather in Kerala.*
>
> *Under **WMO (World Meteorological Organization) Mesoscale Standards**, spatial correlation is physically valid within a **30 to 50 km radius**.*
>
> *Our backend implements the **Geodesic Haversine Distance Algorithm**:*
>
> $$d = 2R \cdot \arcsin\left(\sqrt{\sin^2\left(\frac{\Delta\text{Lat}}{2}\right) + \cos(\text{Lat}_0)\cos(\text{Lat}_i)\sin^2\left(\frac{\Delta\text{Lon}}{2}\right)}\right)$$
>
> *The system queries NeonDB cloud, calculates physical distances from Target Base Station `AWS-01`, and **automatically selects the Top 4 Optimal Nearest Neighbor Stations** within the 13–27 km correlation cluster (`AWS-07` @ 13.0 km, `AWS-10` @ 13.8 km, `AWS-09` @ 18.7 km, `AWS-02` @ 26.6 km).*
>
> *If `AWS-01` suddenly jumps to 55°C while all 4 neighboring stations report 31°C, the system calculates a **Spatial Deviation ($\Delta = +24.0^\circ\text{C}$)** and immediately flags a **Spatial Outlier Fault**, auto-imputing it with the regional neighbor consensus value."*

---

### 📡 PAGE 3: Network Link Matrix & Dynamic Decoders
> **Action:** Click on **Sidebar Tab 3: Link Config / Ingest**.

* Show live UDP socket bound to `0.0.0.0:5000`.
* Show total received packet and byte counters increasing in real-time.
* Explain multi-protocol support: **UDP Broadcast (LAN)**, **TCP Streaming Client**, **Serial COM Port (RS-485 / RS-232)**, and **Multi-Framing Decoders** (AWS-32B Binary, CSV, JSON).

---

### 📋 PAGE 4: Incident Alarm Log & Telemetry Recorder
> **Action:** Click on **Sidebar Tab 4: Alert Logs**.

* Show the timestamped audit log of every detected anomaly.
* Point out the comparison columns: **Original Corrupted Value vs. AI Imputed Self-Healed Value**.
* Explain that DRDO quality control officers can export this log for forensic post-mission analysis.

---

### 🗄️ PAGE 5: Cloud Persistence & NeonDB PostgreSQL Sync
> **Action:** Click on **Sidebar Tab 5: Database / Cloud Sync**.

* **Zero Data Loss Edge Cache:** Explain that all packets are stored locally in SQLite when in offline field conditions.
* **1-Click Cloud Sync:** Automatically pushes synchronized records to **NeonDB Serverless PostgreSQL** once network connectivity is restored.

---

## ⚡ Section 4: Live Anomaly Injection Demo (The "Wow" Factor) (3:00 – 4:00)

> **Live Action Walkthrough:**
> 1. Go to **System A (`lan_data_sender`)**: Click **"Inject Temperature Spike (+15°C)"**.
> 2. Look at **System B (Dashboard)**:
>    * Immediate **RED Alert Banner** pops up in $<50\text{ ms}$.
>    * SHAP bar chart highlights **Temperature: 88% Contribution**.
>    * LIME diagnostic displays root-cause explanation.
>    * Imputed value replaces 46°C with 31.2°C.
> 3. Go to **System A**: Click **"Inject Sensor Freeze (Stuck Value)"**.
>    * Dashboard detects constant zero-variance after 10 samples and flags **Sensor Lockup Fault**.
> 4. Go to **System A**: Click **"Clear / Normal Telemetry"**.
>    * System returns to **Green NOMINAL State** instantly.

---

## 🏆 Section 5: Conclusion & DRDO / SIH Impact (4:00 – 5:00)

> **Spoken Script (Closing Pitch):**  
> *"In summary, SkyGuard AI delivers a complete, production-ready defense solution:
>
> 1. **Ultra-Low Latency:** $<1\text{ ms}$ processing via compiled Go runtime.
> 2. **Explainable & Trustworthy:** Tree SHAP attributions eliminate black-box risks.
> 3. **Autonomous Self-Healing:** Seamless imputation keeps weather forecasting and defense operations alive.
> 4. **Scalable to 900+ Stations:** Automated Haversine Mesoscale Consensus.
> 5. **Direct Hardware Compatibility:** Seamless integration with existing IMD and DRDO AWS data loggers via Direct LAN or RS-485.
>
> *Thank you. We are now open for questions."*
