# AWS SkyGuard Station

AWS SkyGuard Station is an automated weather station telemetry and AI-driven monitoring system designed for real-time sensor analysis, anomaly detection, and ground station visualization.

## 🚀 Repository Overview

This standalone repository contains the full source code, machine learning models, embedded ESP32 edge components, backend service, frontend dashboard, and pre-built Windows standalone executable for **AWS SkyGuard Station**.

```
AWS_SkyGuard_Station_GitHub/
├── dist/
│   ├── AWS_SkyGuard_Station.exe  # Standalone PyInstaller Executable
│   ├── database/                  # SQLite telemetry storage
│   └── logs/                      # Application runtime logs
├── desktop/                       # Python Desktop GUI & Main Runner
├── backend/                       # Go Telemetry Backend Engine
├── frontend/                      # Next.js Web Dashboard
├── skyguard_ai/                   # ML Training, Feature Engineering & Anomaly Detection
├── models/                        # Pre-trained ML Models (.pkl, .json)
├── esp32_edge/                    # Firmware for ESP32 Sensor Edge Node
├── AWS_SkyGuard_Station.spec      # PyInstaller Packaging Specification
└── README.md                      # Project Documentation
```

## ⚡ Quick Start (Running the Standalone Executable)

1. Navigate to `dist/` directory.
2. Launch `AWS_SkyGuard_Station.exe`.
3. The application will start the embedded backend telemetry server and open the SkyGuard GUI station interface automatically.

## 🛠️ Building from Source

### Prerequisites
- Python 3.10+
- Go 1.20+
- Node.js 18+ (for frontend dashboard rebuilds)

### PyInstaller Build Command
To rebuild `AWS_SkyGuard_Station.exe`:
```bash
python build_skyguard_native.py
```
Or run PyInstaller directly with the spec file:
```bash
pyinstaller AWS_SkyGuard_Station.spec --clean
```

## 📝 GitHub Setup Instructions

To push this standalone directory to your new GitHub repository:

```bash
cd "AWS_SkyGuard_Station_GitHub"
git init
git add .
git commit -m "Initial commit: AWS SkyGuard Station full source and standalone build"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/AWS_SkyGuard_Station.git
git push -u origin main
```
