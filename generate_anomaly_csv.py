import csv
import math
import random
from datetime import datetime, timedelta, timezone

def generate_1000_samples_with_anomalies(output_path="aws_telemetry_1000_samples.csv"):
    start_time = datetime(2026, 9, 24, 6, 0, 0, tzinfo=timezone.utc)
    rows = []

    # Nominal base diurnal curve parameters
    base_temp = 28.5
    base_pressure = 1013.2
    base_humidity = 66.0

    for i in range(1000):
        t_now = start_time + timedelta(seconds=i * 2)
        ts_str = t_now.strftime("%Y-%m-%d %H:%M:%S UTC")
        st_id = "AWS-01"

        # Smooth diurnal variation
        diurnal_t = math.sin((i / 1000.0) * math.pi) * 3.5
        diurnal_h = -math.sin((i / 1000.0) * math.pi) * 8.0
        diurnal_p = math.cos((i / 1000.0) * math.pi * 2) * 1.5

        noise_t = (random.random() - 0.5) * 0.4
        noise_h = (random.random() - 0.5) * 0.8
        noise_p = (random.random() - 0.5) * 0.3

        temp_dry = round(base_temp + diurnal_t + noise_t, 2)
        temp_wet = round(temp_dry - 4.5 + (random.random() - 0.5) * 0.3, 2)
        humidity = round(base_humidity + diurnal_h + noise_h, 2)
        pressure_hpa = round(base_pressure + diurnal_p + noise_p, 2)
        pressure_imu = round(pressure_hpa * 100.0 + random.uniform(-1.0, 1.0), 1)

        # ─── INJECTED ANOMALY WINDOWS ───
        
        # 1. Samples 61-90 (30 samples): Temperature Positive Spike & Out-of-Bounds (+27°C)
        if 60 <= i <= 90:
            temp_dry = round(56.5 + (i % 3) * 0.8, 2)  # Exceeds 55°C limit -> flags Out of Bounds & Spike
            temp_wet = 24.2  # Severe psychrometric disparity
            
        # 2. Samples 181-220 (40 samples): Barometric Transducer Frozen Lockup
        elif 180 <= i <= 220:
            pressure_hpa = 1013.25  # Exactly zero variance across 40 frames -> flags Freeze Lockup
            pressure_imu = 101325.0
            
        # 3. Samples 321-360 (40 samples): Capacitive Humidity Sudden Collapse (-45%)
        elif 320 <= i <= 360:
            humidity = round(12.4 + (random.random() - 0.5) * 0.5, 2)  # Extreme drop from ~65% to ~12%
            
        # 4. Samples 481-515 (35 samples): Hard Negative Bounds Transducer Fault (-48°C)
        elif 480 <= i <= 515:
            temp_dry = round(-48.5 + (i % 2) * 0.5, 2)  # Below -40°C limit -> flags Hard Negative Out of Bounds
            temp_wet = -50.0
            
        # 5. Samples 631-670 (40 samples): Barometric Pressure Transient Spike / Drop (910 hPa)
        elif 630 <= i <= 670:
            pressure_hpa = round(910.5 + (random.random() - 0.5) * 0.4, 2)  # Extreme low pressure glitch
            pressure_imu = round(pressure_hpa * 100.0, 1)
            
        # 6. Samples 781-830 (50 samples): Compound Multivariate Cascade Fault
        elif 780 <= i <= 830:
            temp_dry = 54.2
            humidity = 98.6
            pressure_hpa = 925.4
            pressure_imu = 92540.0
            
        # 7. Samples 921-960 (40 samples): High-Frequency Jitter / Transducer Flutter
        elif 920 <= i <= 960:
            if i % 2 == 0:
                temp_dry = 48.6  # Flutter spike
            else:
                temp_dry = 27.2  # Normal floor

        rows.append([
            ts_str,
            st_id,
            f"{temp_dry:.2f}",
            f"{temp_wet:.2f}",
            f"{humidity:.2f}",
            f"{pressure_imu:.1f}",
            f"{pressure_hpa:.2f}"
        ])

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Timestamp",
            "Station ID",
            "Dry Bulb Temp",
            "Wet Bulb Temp",
            "Relative Humidity",
            "Pressure(IMU)",
            "Pressure (hPa)"
        ])
        writer.writerows(rows)

    print(f"Generated {len(rows)} samples with 7 distinct anomaly episodes at {output_path}")

if __name__ == "__main__":
    generate_1000_samples_with_anomalies("aws_telemetry_1000_samples.csv")
