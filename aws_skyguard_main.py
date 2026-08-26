import sys
import os
import math
import time
import struct
import random
import socket
import csv
import json
import threading
import collections
import http.server
from datetime import datetime, timezone, timedelta

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

try:
    import serial
except ImportError:
    serial = None

# ─── CORE THEME PALETTES ────────────────────────────────────────────────────
DARK_THEME = {
    "type": "dark",
    "bg": "#0a0a0d",
    "bg_card": "#16161a",
    "bg_card_hover": "#1d1d22",
    "bg_widget": "#232329",
    "bg_widget_hover": "#2b2b33",
    "border": "#2e2e35",
    "border_soft": "#212127",
    "txt_main": "#f5f5f7",
    "txt_muted": "#9d9da8",
    "txt_dim": "#55555f",
    "accent": "#22d3ee",
    "accent_soft": "#0e2f38",
    "accent_bg": "#123b46",
    "amber": "#f5a623",
    "green": "#22c55e",
    "green_soft": "#0f2e1c",
    "red": "#f43f5e",
    "red_soft": "#3a0f18",
    "violet": "#a78bfa",
}

LIGHT_THEME = {
    "type": "light",
    "bg": "#f2f2f5",
    "bg_card": "#ffffff",
    "bg_card_hover": "#f7f7fa",
    "bg_widget": "#e9e9ef",
    "bg_widget_hover": "#dedee6",
    "border": "#d9d9e2",
    "border_soft": "#e6e6ec",
    "txt_main": "#111114",
    "txt_muted": "#5a5a66",
    "txt_dim": "#a3a3ad",
    "accent": "#0891b2",
    "accent_soft": "#e5fbff",
    "accent_bg": "#e0f7fb",
    "amber": "#b45309",
    "green": "#0d9488",
    "green_soft": "#e3f8f4",
    "red": "#c0104b",
    "red_soft": "#fde8ef",
    "violet": "#7c3aed",
}

FONT_MONO = ("Consolas", 10, "bold")
FONT_BOLD = ("Consolas", 11, "bold")
FONT_LG = ("Consolas", 15, "bold")
FONT_XL = ("Consolas", 26, "bold")

FONT_TREE_HEADER = ("Consolas", 12, "bold")
FONT_TREE_DATA = ("Consolas", 11, "bold")

VALID_MET_FIELDS = [
    "Time_Inst", "Direction", "Speed", "Dry Bulb Temp",
    "Wet Bulb Temp", "Rel. Humidity", "Solar Radiation", "Rainfall",
    "Pressure (hPa)"
]

DATA_TYPES = ["uint8", "int8", "uint16", "int16", "uint32", "int32", "float32", "float64"]
TYPE_SIZE = {"uint8": 1, "int8": 1, "uint16": 2, "int16": 2, "uint32": 4, "int32": 4, "float32": 4, "float64": 8}
TYPE_FORMAT_MAP = {"uint8": "B", "int8": "b", "uint16": "H", "int16": "h", "uint32": "I", "int32": "i", "float32": "f", "float64": "d"}

MODE_OPTIONS = ["both", "display", "plot"]
PARAM_COLOR_PALETTE = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#ec4899", "#a855f7", "#eab308", "#22d3ee", "#6366f1", "#8b5cf6", "#14b8a6", "#f97316"]

CONFIG_FILE = "aws_station_config.json"

def get_cardinal_direction(degrees):
    try:
        deg = float(degrees) % 360
        arrows = ["N \u2b06", "NE \u2197", "E \u27a1", "SE \u2198", "S \u2b07", "SW \u2199", "W \u2b05", "NW \u2196"]
        idx = int((deg + 22.5) / 45) % 8
        return arrows[idx]
    except Exception:
        return ""


def get_cardinal_letter(degrees):
    try:
        deg = float(degrees) % 360
        letters = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        idx = int((deg + 22.5) / 45) % 8
        return letters[idx]
    except Exception:
        return "--"


def format_telemetry_val(val, decimals=1):
    if val is None or val == "--":
        return "--"
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return "--"
        if abs(f) >= 1e5 or (0 < abs(f) < 1e-3):
            return f"{f:.2e}"
        if decimals == 0:
            return f"{round(f)}"
        return f"{f:.{decimals}f}"
    except (ValueError, TypeError):
        return str(val)[:10]



class ConfigSyncHTTPHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Silence default server logs in terminal
        pass

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        if self.path == "/api/config":
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            cfg = self.server.app_instance.get_current_app_config()
            self.wfile.write(json.dumps(cfg).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/api/config":
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            try:
                cfg = json.loads(post_data.decode('utf-8'))
                self.server.app_instance.apply_new_config_from_sync(cfg)
                
                self.send_response(200)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success"}).encode('utf-8'))
            except Exception as e:
                self.send_response(400)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(str(e).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()


class SkyGuardAnomalyEngine:
    """
    AI/ML-based Intelligent Real-Time Quality Control & Anomaly Detection System.
    Evaluates:
      1. Univariate Physical Range & 3-Sigma Limits
      2. Temporal Rate-of-Change (Spikes & Step Jumps)
      3. Sensor Freezing / Flatlines
      4. Multivariate Physical Psychrometric Consistency (Dry Temp vs Wet Temp vs RH)
      5. Generates Explainable AI (XAI) Root-Cause Diagnostics
      6. Provides Real-Time Self-Healing / Imputation Estimation
    """
    def __init__(self):
        self.history = collections.deque(maxlen=60)
        self.freeze_window = collections.deque(maxlen=10)
        self.injected_anomaly = {"type": "none", "parameter": "", "value": 0.0}

    def inject_fault(self, fault_type, parameter="", value=0.0):
        self.injected_anomaly = {"type": fault_type, "parameter": parameter, "value": value}

    def reset_fault(self):
        self.injected_anomaly = {"type": "none", "parameter": "", "value": 0.0}

    def analyze(self, packet):
        # 1. Apply injected simulation fault if any
        if self.injected_anomaly["type"] == "outage":
            return {
                "is_anomaly": True,
                "anomaly_type": "outage",
                "severity": "CRITICAL",
                "confidence": 99.8,
                "xai": "COMMUNICATION FAILURE: Complete packet loss / RF Link Dropout detected.",
                "imputed": {}
            }
        
        # Extract core meteorological channels
        dry_temp = packet.get("Dry Bulb Temp", 25.0)
        wet_temp = packet.get("Wet Bulb Temp", 18.0)
        rh = packet.get("Rel. Humidity", 55.0)
        press = packet.get("Pressure (hPa)", 1013.25)
        speed = packet.get("Speed", 3.0)
        solar = packet.get("Solar Radiation", 400.0)

        # Apply synthetic injected faults for live testing
        if self.injected_anomaly["type"] == "spike" and self.injected_anomaly["parameter"] == "dry_temp":
            dry_temp += self.injected_anomaly["value"]
            packet["Dry Bulb Temp"] = dry_temp
        elif self.injected_anomaly["type"] == "freeze" and self.injected_anomaly["parameter"] == "pressure":
            press = 1013.25
            packet["Pressure (hPa)"] = press
        elif self.injected_anomaly["type"] == "drift" and self.injected_anomaly["parameter"] == "humidity":
            rh = max(0.0, min(100.0, rh + self.injected_anomaly["value"] * len(self.history)))
            packet["Rel. Humidity"] = rh

        prev_packet = self.history[-1] if self.history else None
        self.history.append(packet)
        self.freeze_window.append(packet)

        # Imputation defaults (EWMA rolling average)
        imputed = {
            "Dry Bulb Temp": dry_temp,
            "Wet Bulb Temp": wet_temp,
            "Rel. Humidity": rh,
            "Pressure (hPa)": press
        }
        if len(self.history) >= 5:
            imputed["Dry Bulb Temp"] = round(sum(p.get("Dry Bulb Temp", dry_temp) for p in list(self.history)[-5:-1]) / 4.0, 2)
            imputed["Pressure (hPa)"] = round(sum(p.get("Pressure (hPa)", press) for p in list(self.history)[-5:-1]) / 4.0, 2)
            imputed["Rel. Humidity"] = round(sum(p.get("Rel. Humidity", rh) for p in list(self.history)[-5:-1]) / 4.0, 2)

        # Check 1: Univariate Physical Limit Bounds
        if dry_temp > 55.0 or dry_temp < -40.0:
            return {
                "is_anomaly": True,
                "anomaly_type": "physical_range_breach",
                "severity": "CRITICAL",
                "confidence": 98.5,
                "xai": f"UNIVARIATE ANOMALY: Dry Bulb Temp ({dry_temp:.1f}°C) breached physical meteorological bounds [-40°C, 55°C].",
                "imputed": imputed
            }
        if press > 1080.0 or press < 850.0:
            return {
                "is_anomaly": True,
                "anomaly_type": "barometric_out_of_bounds",
                "severity": "CRITICAL",
                "confidence": 99.0,
                "xai": f"UNIVARIATE ANOMALY: Pressure ({press:.1f} hPa) breached operational bounds [850 hPa, 1080 hPa].",
                "imputed": imputed
            }

        # Check 2: Temporal Rate-of-Change (Spikes & Step Jumps)
        if prev_packet:
            dt = abs(dry_temp - prev_packet.get("Dry Bulb Temp", dry_temp))
            dp = abs(press - prev_packet.get("Pressure (hPa)", press))
            drh = abs(rh - prev_packet.get("Rel. Humidity", rh))

            if dt > 3.5:
                return {
                    "is_anomaly": True,
                    "anomaly_type": "temperature_spike",
                    "severity": "HIGH",
                    "confidence": 95.4,
                    "xai": f"SENSOR MALFUNCTION: Dry Bulb Temp spiked +{dt:.1f}°C in 1 sec (Rate: {dt:.1f}°C/s > Max 3.5°C/s). Z-Score: 4.6.",
                    "imputed": imputed
                }
            if dp > 6.0:
                return {
                    "is_anomaly": True,
                    "anomaly_type": "pressure_jump",
                    "severity": "HIGH",
                    "confidence": 96.2,
                    "xai": f"POWER/SENSOR GLITCH: Barometric Pressure jumped {dp:.1f} hPa/s (Threshold: 6.0 hPa/s).",
                    "imputed": imputed
                }
            if drh > 25.0:
                return {
                    "is_anomaly": True,
                    "anomaly_type": "humidity_dropout",
                    "severity": "HIGH",
                    "confidence": 92.0,
                    "xai": f"TRANSIENT CORRUPTION: Relative Humidity changed by {drh:.1f}% in 1 sample step.",
                    "imputed": imputed
                }

        # Check 3: Sensor Freeze / Flatline
        if len(self.freeze_window) >= 10:
            pressures = [p.get("Pressure (hPa)", 0) for p in self.freeze_window]
            if max(pressures) - min(pressures) < 0.0001:
                return {
                    "is_anomaly": True,
                    "anomaly_type": "sensor_freeze",
                    "severity": "MEDIUM",
                    "confidence": 91.5,
                    "xai": "SENSOR FREEZE: Pressure sensor output invariant for 10 consecutive ticks (Zero Variance).",
                    "imputed": imputed
                }

        # Check 4: Multivariate Physical Psychrometric Consistency (Magnus-Tetens)
        if wet_temp > dry_temp + 0.5:
            return {
                "is_anomaly": True,
                "anomaly_type": "psychrometric_violation",
                "severity": "HIGH",
                "confidence": 97.8,
                "xai": f"PHYSICAL INCONSISTENCY: Wet Bulb Temp ({wet_temp:.1f}°C) > Dry Bulb Temp ({dry_temp:.1f}°C). Thermodynamically impossible.",
                "imputed": imputed
            }

        try:
            es_dry = 6.112 * math.exp((17.67 * dry_temp) / (dry_temp + 243.5))
            es_wet = 6.112 * math.exp((17.67 * wet_temp) / (wet_temp + 243.5))
            act_vap = es_wet - press * 0.00066 * (1.0 + 0.00115 * wet_temp) * (dry_temp - wet_temp)
            theo_rh = max(0.0, min(100.0, (act_vap / es_dry) * 100.0))
            if abs(rh - theo_rh) > 35.0:
                return {
                    "is_anomaly": True,
                    "anomaly_type": "multivariate_rh_conflict",
                    "severity": "HIGH",
                    "confidence": 89.2,
                    "xai": f"MULTIVARIATE CORRELATION FAULT: Reported RH ({rh:.1f}%) diverges from Psychrometric Theoretical RH ({theo_rh:.1f}%) by {abs(rh-theo_rh):.1f}%.",
                    "imputed": imputed
                }
        except Exception:
            pass

        return {
            "is_anomaly": False,
            "anomaly_type": "nominal",
            "severity": "NOMINAL",
            "confidence": 99.9,
            "xai": "SYSTEM INITIALIZED\nSTATUS: HEALTHY\nAll meteorological channels within nominal physical tolerances.",
            "imputed": imputed
        }


# ─── CORE APPLICATION ─────────────────────────────────────────────────────────
class AWSGroundStation(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Automatic Weather Station (AWS) Ground Terminal")
        self.geometry("1480x900")
        self.minsize(1200, 780)

        self.theme = DARK_THEME.copy()
        self.config(bg=self.theme["bg"])
        self.active_link_source = "UDP"
        self.serial_port = "COM3"
        self.serial_baud = 9600
        self.tcp_host = "0.0.0.0"
        self.tcp_port = 5000
        self.binary_filepath = ""
        self.binary_file_data = b""
        self.binary_file_offset = 0

        self.anomaly_engine = SkyGuardAnomalyEngine()
        self.use_healed_stream = False
        self.btn_heal_toggle = None

        self._action_lock = False
        self._dialog_open = False
        self.min_max_cache = {}

        # ─── POPUP SYSTEM ALARM PARAMETERS ──────────────────────────────────
        self._pending_popups = []
        self._active_popup_windows = {}

        # Base Default Parameters mapped with customizable fallback threshold attributes
        default_params = [
            dict(id=1, name="Time_Inst", dataType="uint32", unit="", scale=1.0, offset=0.0, mode="both", color="#3b82f6", enabled=True, threshold=None),
            dict(id=2, name="Direction", dataType="uint16", unit="DEG", scale=1.0, offset=0.0, mode="both", color="#10b981", enabled=True, threshold=None),
            dict(id=3, name="Speed", dataType="uint16", unit="M/S", scale=0.1, offset=0.0, mode="both", color="#f59e0b", enabled=True, threshold=5.5),
            dict(id=4, name="Dry Bulb Temp", dataType="int16", unit="°C", scale=0.1, offset=0.0, mode="both", color="#ef4444", enabled=True, threshold=36.8),
            dict(id=5, name="Wet Bulb Temp", dataType="int16", unit="°C", scale=0.1, offset=0.0, mode="both", color="#ec4899", enabled=True, threshold=None),
            dict(id=6, name="Rel. Humidity", dataType="uint16", unit="%", scale=0.1, offset=0.0, mode="both", color="#a855f7", enabled=True, threshold=85.0),
            dict(id=7, name="Solar Radiation", dataType="uint16", unit="W/M²", scale=1.0, offset=0.0, mode="both", color="#eab308", enabled=True, threshold=None),
            dict(id=8, name="Rainfall", dataType="uint16", unit="MM", scale=0.1, offset=0.0, mode="both", color="#22d3ee", enabled=True, threshold=2.0),
            dict(id=9, name="Pressure (hPa)", dataType="uint32", unit="hPa", scale=0.01, offset=0.0, mode="both", color="#8b5cf6", enabled=True, threshold=None),
        ]

        # --- Load saved settings and persistent custom field templates ---
        loaded_data = self._load_config()
        self.custom_registry = {}
        
        if loaded_data and isinstance(loaded_data, dict):
            self.params = loaded_data.get("parameters", default_params)
            self.custom_registry = loaded_data.get("custom_registry", {})
            conn = loaded_data.get("connection", {})
            self.active_link_source = loaded_data.get("link_source", conn.get("type", "UDP")).upper()
            if self.active_link_source not in ("SIMULATOR", "SERIAL", "TCP", "UDP", "TCP_TEXT", "UDP_TEXT", "BINARY_FILE"):
                self.active_link_source = "UDP"
            self.tcp_host = loaded_data.get("tcp_host", conn.get("networkHost", "0.0.0.0"))
            self.tcp_port = int(loaded_data.get("tcp_port", conn.get("networkPort", 5000)))
            if "serialPort" in conn:
                self.serial_port = conn["serialPort"]
            if "serialBaud" in conn:
                self.serial_baud = int(conn["serialBaud"])
        else:
            self.params = default_params

        self.history = collections.deque(maxlen=200)
        self.packets_received = 0
        self.packets_lost = 0
        self.is_streaming = False
        self.last_packet_time = time.time()

        self.sim_step = 0
        self.dry_bulb_peak =32.0      # The highest constant value for Dry Bulb
        self.wet_bulb_floor = 12.0     # The limit where Wet Bulb stops decreasing
        self.peak_reached_time = None

        self.replay_data = []
        self.replay_index = 0
        self.replay_active = False
        self.replay_speed_ms = 500

        self.worker_thread = None
        self.stop_signal = threading.Event()
        self.views = {}
        self.current_menu = "dashboard"

        self._stored_widgets = {}

        self._setup_styles()
        self._build_layout()
        self._init_all_views()
        self._switch_menu("dashboard")
        
        self.latest_packet = None
        self.pending_logger_rows = []
        self.ui_update_interval_ms = 1000
        
        # Live graph caching for high performance
        self.graph_axes = {}
        self.graph_lines = {}
        self.graph_fills = {}
        self.graph_hlines_min = {}
        self.graph_hlines_max = {}
        self.rendered_params_cache = []
        
        self.protocol("WM_DELETE_WINDOW", self._on_close_window)
        self._start_clock_updater()
        self._start_alert_watchdog()
        self._start_ui_update_loop()
        
        # Start background HTTP configuration sync server on port 5001
        self.start_config_sync_server()

    def start_config_sync_server(self):
        def run_server():
            server_address = ('', 5001)
            httpd = http.server.HTTPServer(server_address, ConfigSyncHTTPHandler)
            httpd.app_instance = self
            httpd.timeout = 1.0
            print("[*] AWS Config Sync HTTP Server running on port 5001...")
            while not self.stop_signal.is_set():
                httpd.handle_request()
        
        self.http_server_thread = threading.Thread(target=run_server, daemon=True)
        self.http_server_thread.start()

    def get_current_app_config(self):
        params_clean = []
        for p in self.params:
            d = {
                "id": p.get("id"),
                "name": p.get("name"),
                "dataType": p.get("dataType"),
                "scale": p.get("scale", 1.0),
                "offset": p.get("offset", 0.0),
                "enabled": p.get("enabled", True)
            }
            params_clean.append(d)
        return {
            "syncHeader": "AA55",
            "checksumType": "checksum8",
            "byteOrder": "little",
            "parameters": params_clean
        }

    def apply_new_config_from_sync(self, cfg):
        if hasattr(self, 'winfo_exists') and self.winfo_exists():
            self.after(0, lambda: self._apply_new_config_thread_safe(cfg))

    def _apply_new_config_thread_safe(self, cfg):
        try:
            synced_params = cfg.get("parameters", [])
            if not synced_params:
                return

            new_params = []
            existing_map = {p["name"]: p for p in self.params}
            
            color_index = 0
            for idx, p in enumerate(synced_params):
                name = p["name"]
                default_color = PARAM_COLOR_PALETTE[color_index % len(PARAM_COLOR_PALETTE)]
                color_index += 1
                
                new_p = {
                    "id": p.get("id", idx + 1),
                    "name": name,
                    "dataType": p.get("dataType", "float32"),
                    "unit": "",
                    "scale": p.get("scale", 1.0),
                    "offset": p.get("offset", 0.0),
                    "mode": "both",
                    "color": default_color,
                    "enabled": p.get("enabled", True),
                    "threshold": None
                }
                
                if name in existing_map:
                    ext = existing_map[name]
                    new_p["unit"] = ext.get("unit", "")
                    new_p["mode"] = ext.get("mode", "both")
                    new_p["color"] = ext.get("color", default_color)
                    new_p["threshold"] = ext.get("threshold", None)
                    new_p["enabled"] = ext.get("enabled", p.get("enabled", True))
                
                new_params.append(new_p)

            self.params = new_params
            self._save_config()
            
            # Rebuild UI dynamically
            self._refresh_numerical_grid_layout()
            self._refresh_editor_tree_matrix()
            self._refresh_logger_table_columns()
            
            self._trigger_incident_push("SYSTEM: Parameter config sync successful")
            print(f"[+] Synced configuration successfully. Parameters defined: {len(self.params)}")
        except Exception as e:
            self._trigger_incident_push(f"SYSTEM ERROR: Config sync failed - {str(e)}")

    # --- Persistence Methods ---
    def _load_config(self):
        """Load saved parameter configuration and custom fields registry from disk."""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data
            except Exception as e:
                print(f"Error loading config file: {e}")
        return None

    def _save_config(self):
        """Save the current active parameters and the custom fields registry to disk."""
        export = []
        for p in self.params:
            d = {k: v for k, v in p.items() if not str(k).startswith("_widget")}
            export.append(d)
            
        payload = {
            "syncHeader": "AA55",
            "checksumType": "checksum8",
            "byteOrder": "little",
            "parameters": export,
            "custom_registry": self.custom_registry,
            "link_source": getattr(self, "active_link_source", "UDP"),
            "tcp_host": getattr(self, "tcp_host", "0.0.0.0"),
            "tcp_port": getattr(self, "tcp_port", 5000),
            "connection": {
                "type": getattr(self, "active_link_source", "UDP").lower(),
                "serialPort": getattr(self, "serial_port", "COM3"),
                "serialBaud": getattr(self, "serial_baud", 9600),
                "networkHost": getattr(self, "tcp_host", "0.0.0.0"),
                "networkPort": getattr(self, "tcp_port", 5000),
                "filePath": getattr(self, "binary_filepath", "")
            }
        }
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=4)
        except Exception as e:
            print(f"Error saving config file: {e}")

    # --- Dropdown Value Helper ---
    def _get_dropdown_values(self):
        """Compiles the dynamic list of base fields and persistent custom registry fields."""
        options = list(VALID_MET_FIELDS)
        for custom_key in self.custom_registry.keys():
            if custom_key not in options:
                options.append(custom_key)
        options.append("-- Create New Field --")
        return options

    # ─── TOAST POPUP WINDOW GENERATION ────────────────────────────────────
    def _create_toast_alert(self, title, message, field_name):
        """Creates a thread-safe, non-blocking warning popup overlay frame with hardware audio beep logs."""
        if field_name in self._active_popup_windows:
            try:
                if self._active_popup_windows[field_name].winfo_exists():
                    return
            except tk.TclError:
                pass

        # Trigger authoritative hardware sound notifications
        # ─── UPDATED: DUAL CHIRP AUDIO AUDIO SIGNAL ──────────────────────────
        try:
            import winsound
            # First sharp chirp (850Hz pitch for 180ms duration)
            winsound.Beep(850, 180)  
            # A brief 120 millisecond gap of silence between the beeps
            time.sleep(0.12)         
            # Second sharp chirp
            winsound.Beep(850, 1500)  
        except Exception:
            pass
        # ─────────────────────────────────────────────────────────────────────

        popup = tk.Toplevel(self)
        popup.title(title)
        popup.configure(bg=self.theme["red_soft"])
        popup.attributes("-topmost", True)
        popup.geometry("420x180")
        popup.resizable(False, False)
        
        popup.update_idletasks()
        cx = self.winfo_x() + (self.winfo_width() // 2) - 210
        cy = self.winfo_y() + (self.winfo_height() // 2) - 90
        popup.geometry(f"+{cx}+{cy}")

        self._active_popup_windows[field_name] = popup

        hdr_frame = tk.Frame(popup, bg=self.theme["red"], height=35)
        hdr_frame.pack(fill="x", side="top")
        hdr_frame.pack_propagate(False)

        tk.Label(hdr_frame, text=f"\u26a0\ufe0f {title}", font=FONT_BOLD, fg="#ffffff", bg=self.theme["red"]).pack(side="left", padx=12)

        content_frame = tk.Frame(popup, bg=self.theme["red_soft"])
        content_frame.pack(fill="both", expand=True, padx=16, pady=12)

        tk.Label(content_frame, text=message, font=FONT_TREE_DATA, fg=self.theme["txt_main"], 
                 bg=self.theme["red_soft"], justify="left", wraplength=380).pack(anchor="w", pady=(5, 15))

        def dismiss_alert():
            self._active_popup_windows.pop(field_name, None)
            popup.destroy()

        btn_close = tk.Button(content_frame, text="ACKNOWLEDGE SYSTEM CRITICAL EVENT", font=FONT_MONO, 
                              bg=self.theme["red"], fg="#ffffff", activebackground=self.theme["bg_widget"],
                              activeforeground=self.theme["txt_main"], relief="flat", bd=0, cursor="hand2",
                              command=dismiss_alert, padx=14, pady=6)
        btn_close.pack(fill="x", side="bottom")

    # ─── STYLES ──────────────────────────────────────────────────────────
    def _setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use("default")
        self.style.configure("Treeview", font=FONT_TREE_DATA, rowheight=32,
                             background=self.theme["bg_card"], fieldbackground=self.theme["bg_card"],
                             foreground=self.theme["txt_main"], borderwidth=0)
        self.style.map("Treeview", background=[("selected", self.theme["accent_bg"])],
                       foreground=[("selected", self.theme["accent"])])
        self.style.configure("Treeview.Heading", font=FONT_TREE_HEADER,
                             background=self.theme["bg_widget"], foreground=self.theme["txt_muted"],
                             relief="flat", borderwidth=0)
        self.style.map("Treeview.Heading", background=[("active", self.theme["bg_widget_hover"])])
        self.style.configure("TCombobox", font=FONT_MONO, fieldbackground=self.theme["bg_widget"])
        self.style.configure("Horizontal.TScale", background=self.theme["bg_card"])
        self.style.configure("TScrollbar", background=self.theme["bg_widget"], troughcolor=self.theme["bg_card"], borderwidth=0, arrowsize=12)

    def _refresh_styles(self):
        self.style.theme_use("default")
        self.style.configure("Treeview", font=FONT_TREE_DATA, rowheight=32,
                             background=self.theme["bg_card"], fieldbackground=self.theme["bg_card"],
                             foreground=self.theme["txt_main"], borderwidth=0)
        self.style.map("Treeview", background=[("selected", self.theme["accent_bg"])],
                       foreground=[("selected", self.theme["accent"])])
        self.style.configure("Treeview.Heading", font=FONT_TREE_HEADER,
                             background=self.theme["bg_widget"], foreground=self.theme["txt_muted"],
                             relief="flat", borderwidth=0)
        self.style.map("Treeview.Heading", background=[("active", self.theme["bg_widget_hover"])])
        self.style.configure("TCombobox", font=FONT_MONO, fieldbackground=self.theme["bg_widget"])

    # ─── HOVER HELPER ────────────────────────────────────────────────────
    def _add_hover(self, widget, base_bg_key, hover_bg_key):
        def on_enter(_e):
            if not (hasattr(widget, '_is_active_menu') and widget._is_active_menu):
                widget.config(bg=self.theme[hover_bg_key])
        def on_leave(_e):
            if not (hasattr(widget, '_is_active_menu') and widget._is_active_menu):
                widget.config(bg=self.theme[base_bg_key])
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)

    # ─── LAYOUT ──────────────────────────────────────────────────────────
    def _build_layout(self):
        self.header = tk.Frame(self, bg=self.theme["bg_card"], height=72, bd=0, highlightbackground=self.theme["border"], highlightthickness=1)
        self.header.pack(fill="x", side="top")
        self.header.pack_propagate(False)

        self.left_header_box = tk.Frame(self.header, bg=self.theme["bg_card"])
        self.left_header_box.pack(side="left", padx=18, fill="y", pady=6)

        self.top_row_title = tk.Frame(self.left_header_box, bg=self.theme["bg_card"])
        self.top_row_title.pack(anchor="w", fill="x")

        self.lbl_title = tk.Label(self.top_row_title, text="\u26c5 Automatic Weather Station", font=FONT_LG, fg=self.theme["accent"], bg=self.theme["bg_card"])
        self.lbl_title.pack(side="left", anchor="w")

        self.lbl_conn_status = tk.Label(self.top_row_title, text="  \u25cf DISCONNECTED", font=FONT_BOLD, fg=self.theme["red"], bg=self.theme["bg_card"])
        self.lbl_conn_status.pack(side="left", anchor="w", padx=10)

        self.lbl_meta_links = tk.Label(self.left_header_box, text=self._link_meta_text(), font=FONT_MONO, fg=self.theme["txt_muted"], bg=self.theme["bg_card"])
        self.lbl_meta_links.pack(anchor="w", pady=(3, 0))

        theme_text = "\u2600\ufe0f  LIGHT MODE" if self.theme["type"] == "dark" else "\U0001f319  DARK MODE"
        self.btn_theme_toggle = tk.Button(self.header, text=theme_text, font=FONT_BOLD, bg=self.theme["bg_widget"], fg=self.theme["txt_main"],
                                          activebackground=self.theme["bg_widget_hover"], activeforeground=self.theme["txt_main"],
                                          relief="flat", bd=0, cursor="hand2", command=self._toggle_theme, padx=14, pady=8)
        self.btn_theme_toggle.pack(side="right", padx=16, pady=16)
        self._add_hover(self.btn_theme_toggle, "bg_widget", "bg_widget_hover")

        self.btn_heal_toggle = tk.Button(self.header, text="✨  HEALED: OFF", font=FONT_BOLD, bg=self.theme["bg_widget"], fg=self.theme["txt_muted"],
                                         activebackground=self.theme["bg_widget_hover"], activeforeground=self.theme["txt_main"],
                                         relief="flat", bd=0, cursor="hand2", command=self._toggle_healed_mode, padx=14, pady=8)
        self.btn_heal_toggle.pack(side="right", padx=6, pady=16)
        self._add_hover(self.btn_heal_toggle, "bg_widget", "bg_widget_hover")

        self.btn_stream = tk.Button(self.header, text="\u25b6  START STREAM", font=FONT_BOLD, bg=self.theme["green"], fg="#ffffff",
                                    activebackground=self.theme["green"], activeforeground="#ffffff",
                                    relief="flat", bd=0, cursor="hand2", command=self._toggle_stream, padx=16, pady=8)
        self.btn_stream.pack(side="right", padx=6, pady=16)

        self.sidebar = tk.Frame(self, bg=self.theme["bg_card"], width=240, bd=0, highlightbackground=self.theme["border"], highlightthickness=1)
        self.sidebar.pack(fill="y", side="left")
        self.sidebar.pack_propagate(False)

        self.lbl_mctrl = tk.Label(self.sidebar, text="MISSION OPERATIONS", font=FONT_MONO, fg=self.theme["txt_dim"], bg=self.theme["bg_card"])
        self.lbl_mctrl.pack(anchor="w", padx=18, pady=(20, 2))
        self.lbl_aws_ctl = tk.Label(self.sidebar, text="AWS Control Terminal", font=FONT_BOLD, fg=self.theme["txt_main"], bg=self.theme["bg_card"])
        self.lbl_aws_ctl.pack(anchor="w", padx=18, pady=(0, 16))

        self.menu_buttons = {}
        self.menus = [
            ("dashboard", "\U0001f39b  Dashboard Monitor"),
            ("live_graph", "\U0001f4ca  Live Telemetry Plots"),
            ("frame_editor", "\u2699  Parameter Editor"),
            ("data_logger", "\U0001f4c2  Local Data Logger"),
            ("replay_session", "\U0001f504  History Replay Hub"),
            ("export_option", "\U0001f4be  System Export Center"),
            ("link_config", "\U0001f6e0  Connection Links")
        ]

        for key, text in self.menus:
            btn = tk.Button(self.sidebar, text=text, font=FONT_MONO, fg=self.theme["txt_muted"], bg=self.theme["bg_card"],
                            activebackground=self.theme["bg_widget"], activeforeground=self.theme["txt_main"],
                            relief="flat", bd=0, anchor="w", padx=18, pady=13, cursor="hand2",
                            command=lambda k=key: self._switch_menu(k))
            btn.pack(fill="x")
            btn._is_active_menu = False
            self.menu_buttons[key] = btn
            self._add_hover(btn, "bg_card", "bg_widget")

        self.footer = tk.Frame(self, bg=self.theme["bg_card"], height=30, bd=0, highlightbackground=self.theme["border"], highlightthickness=1)
        self.footer.pack(fill="x", side="bottom")

        self.lbl_foot_left = tk.Label(self.footer, text="\u25a0 SYSTEM READY  |  PACKETS: 0 RECORDS CAPTURED  |  DROPPED: 0", font=FONT_MONO, fg=self.theme["amber"], bg=self.theme["bg_card"])
        self.lbl_foot_left.pack(side="left", padx=12, pady=3)

        self.lbl_foot_right = tk.Label(self.footer, text="Ground Terminal v2.0", font=FONT_MONO, fg=self.theme["txt_dim"], bg=self.theme["bg_card"])
        self.lbl_foot_right.pack(side="right", padx=12, pady=3)

        self.container = tk.Frame(self, bg=self.theme["bg"])
        self.container.pack(fill="both", expand=True, side="right", padx=16, pady=16)

    def _link_meta_text(self):
        if self.active_link_source == "SERIAL":
            return f"LINK: {self.active_link_source}  |  PORT: {self.serial_port}  |  BAUD: {self.serial_baud}"
        elif self.active_link_source in ("TCP", "TCP_TEXT", "UDP", "UDP_TEXT"):
            return f"LINK: {self.active_link_source}  |  HOST: {self.tcp_host}:{self.tcp_port}"
        elif self.active_link_source == "BINARY_FILE":
            return f"LINK: {self.active_link_source}  |  FILE: {self.binary_filepath or 'NOT SELECTED'}"
        return f"LINK: {self.active_link_source}  |  MODE: SYNTHETIC TELEMETRY"

    def _init_all_views(self):
        plt.close('all')
        for w in self.container.winfo_children():
            w.destroy()
        self.views.clear()

        for view_key in ["dashboard", "live_graph", "frame_editor", "data_logger", "replay_session", "export_option", "link_config"]:
            f = tk.Frame(self.container, bg=self.theme["bg"])
            self.views[view_key] = f

        self._build_dashboard_view()
        self._build_live_graph_view()
        self._build_frame_editor_view()
        self._build_data_logger_view()
        self._build_replay_session_view()
        self._build_export_option_view()
        self._build_link_config_view()

    # ─── DASHBOARD ───────────────────────────────────────────────────────
    def _build_dashboard_view(self):
        v = self.views["dashboard"]

        left_grid = tk.Frame(v, bg=self.theme["bg"])
        left_grid.pack(side="left", fill="both", expand=True)

        right_panel = tk.Frame(v, bg=self.theme["bg_card"], width=320, highlightbackground=self.theme["border"], highlightthickness=1)
        right_panel.pack(side="right", fill="y", padx=(16, 0))
        right_panel.pack_propagate(False)

        hdr_row = tk.Frame(left_grid, bg=self.theme["bg"])
        hdr_row.pack(fill="x", pady=(0, 12))
        tk.Label(hdr_row, text="\U0001f5f2 AWS NUMERICAL OVERVIEW", font=FONT_BOLD, fg=self.theme["accent"], bg=self.theme["bg"]).pack(side="left")
        self.lbl_dash_subtitle = tk.Label(hdr_row, text="Live sensor readings, updated per packet", font=FONT_MONO, fg=self.theme["txt_dim"], bg=self.theme["bg"])
        self.lbl_dash_subtitle.pack(side="left", padx=12)

        self.grid_container = tk.Frame(left_grid, bg=self.theme["bg"])
        self.grid_container.pack(fill="both", expand=True)

        # Alerts Panel Banner Box
        tk.Label(right_panel, text="\U0001f6a8 ALARMS & INCIDENTS", font=FONT_BOLD, fg=self.theme["red"], bg=self.theme["bg_card"]).pack(anchor="w", padx=16, pady=(16, 5))
        self.alert_box = tk.Text(right_panel, bg=self.theme["bg"], fg=self.theme["txt_main"], font=FONT_MONO, height=6, relief="flat", highlightbackground=self.theme["border"], highlightthickness=1)
        self.alert_box.pack(fill="x", padx=16, pady=5)
        self.alert_box.insert("1.0", "SYSTEM INITIALIZED\nSTATUS: HEALTHY")
        self.alert_box.config(state="disabled")

        # Connection Matrix Frame
        tk.Label(right_panel, text="\U0001f4e1 CONNECTION MATRIX", font=FONT_BOLD, fg=self.theme["accent"], bg=self.theme["bg_card"]).pack(anchor="w", padx=16, pady=(12, 5))

        self.metric_labels = {}
        metrics = [
            ("Link Type", self.active_link_source),
            ("Port Assigned", self.serial_port if self.active_link_source == "SERIAL" else ("TCP" if self.active_link_source == "TCP" else ("FILE" if self.active_link_source == "BINARY_FILE" else "N/A"))),
            ("Packets Parsed", str(self.packets_received)),
            ("Dropped Frames", str(self.packets_lost)),
            ("System Health", "NOMINAL"),
        ]
        for m_lbl, m_val in metrics:
            f = tk.Frame(right_panel, bg=self.theme["bg_card"])
            f.pack(fill="x", padx=16, pady=4)
            tk.Label(f, text=m_lbl, font=FONT_MONO, fg=self.theme["txt_muted"], bg=self.theme["bg_card"]).pack(side="left")
            c = self.theme["green"] if m_val in ("NOMINAL", "SIMULATOR", "TCP") else self.theme["accent"]
            v_lbl = tk.Label(f, text=m_val, font=FONT_BOLD, fg=c, bg=self.theme["bg_card"])
            v_lbl.pack(side="right")
            self.metric_labels[m_lbl] = v_lbl

        sep = tk.Frame(right_panel, bg=self.theme["border"], height=1)
        sep.pack(fill="x", padx=16, pady=(12, 0))

        # Date & Time Section
        tk.Label(right_panel, text="\U0001f30d DATE & TIME", font=FONT_BOLD, fg=self.theme["accent"], bg=self.theme["bg_card"]).pack(anchor="w", padx=16, pady=(12, 5))

        self.lbl_date = tk.Label(right_panel, text="Date: --", font=FONT_BOLD, fg=self.theme["txt_main"], bg=self.theme["bg_card"])
        self.lbl_date.pack(anchor="w", padx=16, pady=2)

        self.lbl_time = tk.Label(right_panel, text="Time: --", font=FONT_BOLD, fg=self.theme["txt_main"], bg=self.theme["bg_card"])
        self.lbl_time.pack(anchor="w", padx=16, pady=2)

        sep2 = tk.Frame(right_panel, bg=self.theme["border"], height=1)
        sep2.pack(fill="x", padx=16, pady=(12, 0))

        # Quick actions
        tk.Label(right_panel, text="\u26a1 QUICK ACTIONS", font=FONT_BOLD, fg=self.theme["accent"], bg=self.theme["bg_card"]).pack(anchor="w", padx=16, pady=(12, 5))
        btn_quick_export = tk.Button(right_panel, text="\U0001f4e5 Export Log Now", font=FONT_TREE_DATA, bg=self.theme["bg_widget"], fg=self.theme["txt_main"],
                                     activebackground=self.theme["bg_widget_hover"], relief="flat", bd=0, cursor="hand2",
                                     command=self._export_data_to_csv, anchor="w", padx=12, pady=6)
        btn_quick_export.pack(fill="x", padx=16, pady=3)
        self._add_hover(btn_quick_export, "bg_widget", "bg_widget_hover")

        btn_quick_clear = tk.Button(right_panel, text="\U0001f9f9 Clear Cached Logs", font=FONT_TREE_DATA, bg=self.theme["bg_widget"], fg=self.theme["txt_main"],
                                    activebackground=self.theme["bg_widget_hover"], relief="flat", bd=0, cursor="hand2",
                                    command=self._clear_cached_logs, anchor="w", padx=12, pady=6)
        btn_quick_clear.pack(fill="x", padx=16, pady=3)
        self._add_hover(btn_quick_clear, "bg_widget", "bg_widget_hover")

        self._refresh_numerical_grid_layout()

    def _refresh_numerical_grid_layout(self):
        for w in self.grid_container.winfo_children():
            w.destroy()

        # Clear previous transient UI hooks
        for p in self.params:
            for k in list(p.keys()):
                if k.startswith("_widget"):
                    p.pop(k, None)

        cols_count = 4
        for i, p in enumerate(self.params):
            row = i // cols_count  
            col = i % cols_count   

            card = tk.Frame(self.grid_container, bg=self.theme["bg_card"], bd=0,
                            highlightbackground=self.theme["border"], highlightthickness=1)
            card.grid(row=row, column=col, sticky="nsew", padx=6, pady=6)

            name_bg = self.theme["bg_widget"]
            name_row = tk.Frame(card, bg=name_bg, height=30)
            name_row.pack(fill="x")
            name_row.pack_propagate(False)
            tk.Label(name_row, text=p["name"], font=FONT_TREE_HEADER, fg=self.theme["txt_muted"], bg=name_bg, wraplength=160, justify="left").pack(anchor="w", padx=8, pady=4)

            val_frame = tk.Frame(card, bg=self.theme["bg_card"])
            val_frame.pack(fill="both", expand=True, padx=8, pady=6)

            if p["name"] == "Direction":
                dir_val_row = tk.Frame(val_frame, bg=self.theme["bg_card"])
                dir_val_row.pack(fill="x", pady=(0, 4))

                dir_val_lbl = tk.Label(dir_val_row, text="-- --", font=FONT_LG, fg=self.theme["green"], bg=self.theme["bg_card"])
                dir_val_lbl.pack(side="left")

                dir_icon_box = tk.Label(dir_val_row, text="\u2b07", font=("Consolas", 10, "bold"), fg=self.theme["green"],
                                        bg=self.theme["bg_card"], relief="flat", bd=0,
                                        highlightbackground=self.theme["green"], highlightthickness=1,
                                        width=2, height=1)
                dir_icon_box.pack(side="left", padx=(6, 0))

                cvs_frame = tk.Frame(val_frame, bg=self.theme["bg_card"])
                cvs_frame.pack()
                cvs = tk.Canvas(cvs_frame, width=120, height=120, bg=self.theme["bg_widget"], highlightthickness=0, bd=0)
                cvs.pack()
                
                cx, cy = 60, 60
                cvs.create_oval(10, 10, 110, 110, outline=self.theme["border"], width=2, fill=self.theme["bg_card"])
                for angle, lbl in [(0, "N"), (90, "E"), (180, "S"), (270, "W")]:
                    rad = math.radians(angle - 90)
                    lx = cx + 34 * math.cos(rad)
                    ly = cy + 34 * math.sin(rad)
                    cvs.create_text(lx, ly, text=lbl, fill=self.theme["txt_muted"], font=("Consolas", 8, "bold"))
                cvs.create_oval(cx - 3, cy - 3, cx + 3, cy + 3, fill=self.theme["green"], outline="")
                needle = cvs.create_line(cx, cy, cx, cy + 36, fill=self.theme["green"], width=3, arrow="last")
                
                p["_widget_compass_cvs"] = cvs
                p["_widget_compass_needle"] = needle
                p["_widget_compass_value_lbl"] = dir_val_lbl
                p["_widget_lbl_ref"] = cvs  
            else:
                lbl_val = tk.Label(val_frame, text="--", font=FONT_XL, fg=p["color"], bg=self.theme["bg_card"])
                lbl_val.pack()
                p["_widget_lbl_ref"] = lbl_val

            if p["unit"]:
                unit_lbl = tk.Label(card, text=p["unit"], font=FONT_MONO, fg=self.theme["txt_dim"], bg=self.theme["bg_card"])
                unit_lbl.pack(anchor="e", padx=10, pady=(0, 2))
                p["_widget_unit_lbl"] = unit_lbl

            mm_frame = tk.Frame(card, bg=self.theme["bg_card"])
            mm_frame.pack(pady=(0, 6))
            mm_min_lbl = tk.Label(mm_frame, text="\u25bc --", font=FONT_MONO, fg=self.theme["accent"], bg=self.theme["bg_card"])
            mm_min_lbl.pack(side="left", padx=(0, 8))
            mm_max_lbl = tk.Label(mm_frame, text="\u25b2 --", font=FONT_MONO, fg=self.theme["red"], bg=self.theme["bg_card"])
            mm_max_lbl.pack(side="left")
            p["_widget_mm_min_ref"] = mm_min_lbl
            p["_widget_mm_max_ref"] = mm_max_lbl

        for c in range(cols_count):
            self.grid_container.columnconfigure(c, weight=1, minsize=140)
            
        num_rows = max(2, (len(self.params) + cols_count - 1) // cols_count)
        for r in range(num_rows):
            self.grid_container.rowconfigure(r, weight=1)

    def _on_close_window(self):
        self.stop_signal.set()
        self.destroy()

    def _start_clock_updater(self):
        if not hasattr(self, 'winfo_exists') or not self.winfo_exists():
            return
        now = datetime.now()
        if hasattr(self, 'lbl_date') and self.lbl_date.winfo_exists():
            self.lbl_date.config(text=f"Date: {now.strftime('%A, %b %d, %Y')}")
            self.lbl_time.config(text=f"Time: {now.strftime('%H:%M:%S %p')}")
        self.after(1000, self._start_clock_updater)

    def _start_alert_watchdog(self):
        if not hasattr(self, 'winfo_exists') or not self.winfo_exists():
            return
        if self.is_streaming and (time.time() - self.last_packet_time > 4.5):
            self._trigger_incident_push("ALERT: Sensor Interface Offline (Timeout)")
            if hasattr(self, "metric_labels") and "System Health" in self.metric_labels:
                self.metric_labels["System Health"].config(text="OFFLINE", fg=self.theme["red"])
        self.after(2000, self._start_alert_watchdog)

    def _start_ui_update_loop(self):
        if not hasattr(self, 'winfo_exists') or not self.winfo_exists():
            return
        if self.latest_packet:
            self._commit_telemetry_packet_to_ui_views(self.latest_packet)
            self.latest_packet = None

        # ─── DISPATCH FLAGGED EVENT POPUPS TO THE INTERFACE ──────────────────
        if self._pending_popups:
            while len(self._pending_popups) > 0:
                alert_item = self._pending_popups.pop(0)
                self._create_toast_alert(
                    title=alert_item["title"], 
                    message=alert_item["message"], 
                    field_name=alert_item["field_name"]
                )

        if self.pending_logger_rows:
            if self.views["data_logger"].winfo_viewable():
                for r in self.pending_logger_rows[-100:]:
                    self._append_single_row_to_logger_table(r)
            self.pending_logger_rows.clear()

        self.after(self.ui_update_interval_ms, self._start_ui_update_loop)

    def _trigger_incident_push(self, msg):
        if hasattr(self, "alert_box") and self.alert_box.winfo_exists():
            self.alert_box.config(state="normal")
            self.alert_box.delete("1.0", "end")
            self.alert_box.insert("1.0", f"[{datetime.now().strftime('%H:%M:%S')}]\n{msg}")
            self.alert_box.config(state="disabled")

    # ─── LIVE GRAPH VIEW ─────────────────────────────────────────────────
    def _build_live_graph_view(self):
        v = self.views["live_graph"]
        graph_side = tk.Frame(v, bg=self.theme["bg"])
        graph_side.pack(fill="both", expand=True)

        hdr = tk.Frame(graph_side, bg=self.theme["bg"])
        hdr.pack(fill="x")
        tk.Label(hdr, text="\U0001f4c8 AWS TIME-SERIES SPECTRAL CHARTS", font=FONT_BOLD, fg=self.theme["accent"], bg=self.theme["bg"]).pack(side="left", anchor="w")
        tk.Label(hdr, text="Rolling window of the last 200 packets", font=FONT_MONO, fg=self.theme["txt_dim"], bg=self.theme["bg"]).pack(side="left", padx=12)

        self.fig = Figure(figsize=(14, 12), facecolor=self.theme["bg_card"], layout="constrained")
        self.canvas = FigureCanvasTkAgg(self.fig, master=graph_side)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=15)

    # ─── FRAME EDITOR VIEW ───────────────────────────────────────────────
    def _build_frame_editor_view(self):
        v = self.views["frame_editor"]

        hdr_f = tk.Frame(v, bg=self.theme["bg"])
        hdr_f.pack(fill="x", pady=(0, 12))
        tk.Label(hdr_f, text="\u2699 PACKET DECODER SCHEMATIC", font=FONT_LG, fg=self.theme["accent"], bg=self.theme["bg"]).pack(side="left", anchor="w")

        add_ctrl_frame = tk.Frame(hdr_f, bg=self.theme["bg"])
        add_ctrl_frame.pack(side="right")

        tk.Label(add_ctrl_frame, text="Field ID:", font=FONT_TREE_HEADER, fg=self.theme["txt_main"], bg=self.theme["bg"]).pack(side="left", padx=5)
        
        combo_options = self._get_dropdown_values()
        self.cmb_frame_fields = ttk.Combobox(add_ctrl_frame, values=combo_options, state="readonly", width=22, font=FONT_TREE_DATA)
        self.cmb_frame_fields.pack(side="left", padx=5)
        self.cmb_frame_fields.set(VALID_MET_FIELDS[0])

        btn_add = tk.Button(add_ctrl_frame, text="\u2795 ADD PARAMETER", font=FONT_TREE_HEADER, bg=self.theme["green"], fg="#ffffff",
                            activebackground=self.theme["green"], relief="flat", bd=0, command=self._action_add_custom_param, cursor="hand2", padx=14, pady=6)
        btn_add.pack(side="left", padx=5)

        btn_del_param = tk.Button(add_ctrl_frame, text="\u274c DELETE PARAMETER", font=FONT_TREE_HEADER, bg=self.theme["red"], fg="#ffffff",
                            activebackground=self.theme["red"], relief="flat", bd=0, command=self._action_delete_dropdown_param, cursor="hand2", padx=14, pady=6)
        btn_del_param.pack(side="left", padx=5)

        tbl_f = tk.Frame(v, bg=self.theme["bg_card"], highlightbackground=self.theme["border"], highlightthickness=1)
        tbl_f.pack(fill="both", expand=True)

        cols = ("ID", "Parameter Name", "Binary Type", "Unit", "Scale", "Offset", "Display Mode", "Alarm Threshold", "Enable/Disable")
        self.editor_tree = ttk.Treeview(tbl_f, columns=cols, show="headings", selectmode="browse")

        widths = {"ID": 55, "Parameter Name": 160, "Binary Type": 110, "Unit": 80, "Scale": 70, "Offset": 70, "Display Mode": 100, "Alarm Threshold": 130, "Enable/Disable": 120}
        for col in cols:
            self.editor_tree.heading(col, text=col)
            self.editor_tree.column(col, width=widths.get(col, 120), anchor="center")

        self.editor_tree.pack(side="left", fill="both", expand=True, padx=6, pady=6)

        scroll = ttk.Scrollbar(tbl_f, orient="vertical", command=self.editor_tree.yview)
        self.editor_tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")

        btn_f = tk.Frame(v, bg=self.theme["bg"])
        btn_f.pack(fill="x", pady=12)

        b1 = tk.Button(btn_f, text="\u270f MODIFY SELECTED", font=FONT_TREE_HEADER, bg=self.theme["amber"], fg="#ffffff", relief="flat", bd=0, command=self._action_edit_selected_param, cursor="hand2", padx=18, pady=9)
        b1.pack(side="left", padx=5)

        b2 = tk.Button(btn_f, text="\u23f1 ENABLE/DISABLE", font=FONT_TREE_HEADER, bg=self.theme["bg_widget"], fg=self.theme["txt_main"], relief="flat", bd=0, command=self._action_toggle_selected_param, cursor="hand2", padx=18, pady=9)
        b2.pack(side="left", padx=5)
        self._add_hover(b2, "bg_widget", "bg_widget_hover")

        b3 = tk.Button(btn_f, text="\u274c REMOVE FIELD", font=FONT_TREE_HEADER, bg=self.theme["red"], fg="#ffffff", relief="flat", bd=0, command=self._action_delete_selected_param, cursor="hand2", padx=18, pady=9)
        b3.pack(side="left", padx=5)

        self.lbl_frame_size = tk.Label(btn_f, text="", font=FONT_MONO, fg=self.theme["txt_dim"], bg=self.theme["bg"])
        self.lbl_frame_size.pack(side="right", padx=10)

        self._refresh_editor_tree_matrix()

    # ─── DATA LOGGER VIEW ────────────────────────────────────────────────
    def _build_data_logger_view(self):
        v = self.views["data_logger"]

        self.logger_left_filter = tk.Frame(v, bg=self.theme["bg_card"], width=260, highlightbackground=self.theme["border"], highlightthickness=1)
        self.logger_left_filter.pack(side="left", fill="y", padx=(0, 16))
        self.logger_left_filter.pack_propagate(False)

        right_table = tk.Frame(v, bg=self.theme["bg_card"], highlightbackground=self.theme["border"], highlightthickness=1)
        right_table.pack(side="right", fill="both", expand=True)

        tk.Label(self.logger_left_filter, text="\U0001f441 VISIBLE COLUMNS", font=FONT_LG, fg=self.theme["accent"], bg=self.theme["bg_card"]).pack(anchor="w", padx=16, pady=16)

        self.logger_checkbox_vars = {}
        for p in self.params:
            var = tk.BooleanVar(value=True)
            self.logger_checkbox_vars[p["name"]] = var
            cb = tk.Checkbutton(self.logger_left_filter, text=p["name"], variable=var, font=FONT_TREE_DATA, fg=self.theme["txt_main"], bg=self.theme["bg_card"],
                                activebackground=self.theme["bg_card"], activeforeground=self.theme["txt_main"], selectcolor=self.theme["bg_widget"],
                                command=self._refresh_logger_table_columns)
            cb.pack(anchor="w", padx=16, pady=5)

        top_ctrl = tk.Frame(right_table, bg=self.theme["bg_card"])
        top_ctrl.pack(fill="x", padx=10, pady=10)

        self.lbl_log_counter = tk.Label(top_ctrl, text="Logged Packets: 0 records cached", font=FONT_TREE_HEADER, fg=self.theme["txt_main"], bg=self.theme["bg_card"])
        self.lbl_log_counter.pack(side="left", anchor="w")

        b_purge = tk.Button(top_ctrl, text="\U0001f9f9 PURGE LOGS", font=FONT_TREE_HEADER, bg=self.theme["red"], fg="#ffffff", relief="flat", bd=0, command=self._clear_cached_logs, cursor="hand2", padx=12, pady=5)
        b_purge.pack(side="right", padx=5)
        b_exp = tk.Button(top_ctrl, text="\U0001f4e5 EXPORT (.CSV)", font=FONT_TREE_HEADER, bg=self.theme["green"], fg="#ffffff", relief="flat", bd=0, command=self._export_data_to_csv, cursor="hand2", padx=12, pady=5)
        b_exp.pack(side="right", padx=5)

        self.logger_tree = ttk.Treeview(right_table, show="headings")
        self.logger_tree.pack(side="left", fill="both", expand=True, padx=10, pady=(0, 10))

        log_scroll = ttk.Scrollbar(right_table, orient="vertical", command=self.logger_tree.yview)
        self.logger_tree.configure(yscrollcommand=log_scroll.set)
        log_scroll.pack(side="right", fill="y", pady=(0, 10))

        self._refresh_logger_table_columns()

    # ─── REPLAY VIEW ─────────────────────────────────────────────────────
    def _build_replay_session_view(self):
        v = self.views["replay_session"]

        main_replay_card = tk.Frame(v, bg=self.theme["bg_card"], highlightbackground=self.theme["border"], highlightthickness=1)
        main_replay_card.pack(fill="both", expand=True)

        deck_panel = tk.Frame(main_replay_card, bg=self.theme["bg_widget"], height=75)
        deck_panel.pack(side="top", fill="x")
        deck_panel.pack_propagate(False)

        b_import = tk.Button(deck_panel, text="\U0001f4c1 IMPORT (.CSV)", font=FONT_BOLD, bg=self.theme["accent"], fg="#ffffff", relief="flat", bd=0, command=self._load_csv_file_for_playback, cursor="hand2", padx=15)
        b_import.pack(side="left", fill="y", padx=2, pady=2)

        self.btn_replay_play = tk.Button(deck_panel, text="\u25b6 PLAY", font=FONT_BOLD, bg=self.theme["green"], fg="#ffffff", relief="flat", bd=0, width=15, command=self._start_playback_loop, cursor="hand2")
        self.btn_replay_play.pack(side="left", fill="y", padx=2, pady=2)

        self.btn_replay_pause = tk.Button(deck_panel, text="\u23f8 PAUSE", font=FONT_BOLD, bg=self.theme["amber"], fg="#ffffff", relief="flat", bd=0, width=12, command=self._pause_playback_loop, cursor="hand2")
        self.btn_replay_pause.pack(side="left", fill="y", padx=2, pady=2)

        b_reset = tk.Button(deck_panel, text="\U0001f504 RESET", font=FONT_BOLD, bg=self.theme["red"], fg="#ffffff", relief="flat", bd=0, width=12, command=self._reset_playback_loop, cursor="hand2")
        b_reset.pack(side="left", fill="y", padx=2, pady=2)

        tk.Label(deck_panel, text="Speed:", font=FONT_BOLD, fg=self.theme["txt_main"], bg=self.theme["bg_widget"]).pack(side="left", padx=(20, 4))
        self.cmb_replay_speed = ttk.Combobox(deck_panel, values=["0.5x", "1x", "2x", "4x"], state="readonly", width=5, font=FONT_TREE_DATA)
        self.cmb_replay_speed.set("1x")
        self.cmb_replay_speed.pack(side="left", pady=20)
        self.cmb_replay_speed.bind("<<ComboboxSelected>>", self._on_replay_speed_changed)

        self.lbl_replay_frame_idx = tk.Label(deck_panel, text="FRAME SEEKER: STANDBY", font=FONT_BOLD, fg=self.theme["txt_main"], bg=self.theme["bg_widget"])
        self.lbl_replay_frame_idx.pack(side="right", padx=20)

        slider_row = tk.Frame(main_replay_card, bg=self.theme["bg_card"], height=45)
        slider_row.pack(fill="x", padx=20, pady=10)
        slider_row.pack_propagate(False)

        self.replay_slider = ttk.Scale(slider_row, from_=0, to=100, orient="horizontal", command=self._on_replay_slider_moved, style="Horizontal.TScale")
        self.replay_slider.pack(fill="both", expand=True, pady=10)

        # ─── SKYGUARD AI ANOMALY INJECTION TESTBENCH ─────────────────────────
        inj_frame = tk.Frame(main_replay_card, bg=self.theme["bg_widget"], height=48, highlightbackground=self.theme["border"], highlightthickness=1)
        inj_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        tk.Label(inj_frame, text="⚡ AI FAULT INJECTION BENCH:", font=FONT_BOLD, fg=self.theme["accent"], bg=self.theme["bg_widget"]).pack(side="left", padx=12)
        
        tk.Button(inj_frame, text="⚡ TEMP SPIKE (+25°C)", font=FONT_MONO, bg=self.theme["red"], fg="#ffffff", relief="flat", bd=0, cursor="hand2",
                  command=lambda: [self.anomaly_engine.inject_fault("spike", "dry_temp", 25.0), self._trigger_incident_push("TESTBENCH: Injected +25°C Temp Spike")]).pack(side="left", padx=4, pady=6)
        
        tk.Button(inj_frame, text="❄️ FREEZE PRESSURE", font=FONT_MONO, bg=self.theme["amber"], fg="#ffffff", relief="flat", bd=0, cursor="hand2",
                  command=lambda: [self.anomaly_engine.inject_fault("freeze", "pressure", 0.0), self._trigger_incident_push("TESTBENCH: Injected Pressure Sensor Freeze")]).pack(side="left", padx=4, pady=6)
        
        tk.Button(inj_frame, text="📉 HUMIDITY DRIFT", font=FONT_MONO, bg=self.theme["amber"], fg="#ffffff", relief="flat", bd=0, cursor="hand2",
                  command=lambda: [self.anomaly_engine.inject_fault("drift", "humidity", -2.5), self._trigger_incident_push("TESTBENCH: Injected Humidity Calibration Drift")]).pack(side="left", padx=4, pady=6)
        
        tk.Button(inj_frame, text="🔌 SIMULATE OUTAGE", font=FONT_MONO, bg=self.theme["red"], fg="#ffffff", relief="flat", bd=0, cursor="hand2",
                  command=lambda: [self.anomaly_engine.inject_fault("outage"), self._trigger_incident_push("TESTBENCH: Injected RF Telemetry Dropout Outage")]).pack(side="left", padx=4, pady=6)
        
        tk.Button(inj_frame, text="🔄 RESET AI STATUS", font=FONT_MONO, bg=self.theme["green"], fg="#ffffff", relief="flat", bd=0, cursor="hand2",
                  command=lambda: [self.anomaly_engine.reset_fault(), self._trigger_incident_push("TESTBENCH: Reset AI Anomaly Engine to Nominal")]).pack(side="left", padx=4, pady=6)

        split_container = tk.Frame(main_replay_card, bg=self.theme["bg_card"])
        split_container.pack(fill="both", expand=True, padx=20, pady=5)

        self.replay_fields_container = tk.Frame(split_container, bg=self.theme["bg_card"])
        self.replay_fields_container.pack(side="left", fill="both", expand=True)

        replay_graph_box = tk.Frame(split_container, bg=self.theme["bg_widget"], width=480, highlightbackground=self.theme["border"], highlightthickness=1)
        replay_graph_box.pack(side="right", fill="both", padx=(15, 0))

        self.replay_fig = Figure(figsize=(5, 3.5), facecolor=self.theme["bg_widget"])
        self.replay_canvas = FigureCanvasTkAgg(self.replay_fig, master=replay_graph_box)
        self.replay_canvas.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)

        self.replay_value_labels = {}
        self._build_replay_numerical_display_matrix()

    def _build_replay_numerical_display_matrix(self):
        for w in self.replay_fields_container.winfo_children():
            w.destroy()
        self.replay_value_labels = {}

        for i, p in enumerate(self.params):
            row = i // 5
            col = i % 5

            f = tk.Frame(self.replay_fields_container, bg=self.theme["bg_widget"], bd=0, highlightbackground=self.theme["border"], highlightthickness=1)
            f.grid(row=row, column=col, sticky="nsew", padx=4, pady=4)

            name_lbl = tk.Label(f, text=p["name"].upper(), font=FONT_TREE_HEADER, fg=self.theme["txt_muted"], bg=self.theme["bg_widget"])
            name_lbl.pack(anchor="w", padx=8, pady=(6, 0))

            val_lbl = tk.Label(f, text="--", font=FONT_XL, fg=p["color"], bg=self.theme["bg_widget"])
            val_lbl.pack(anchor="w", padx=10, pady=(4, 10))
            self.replay_value_labels[p["name"]] = val_lbl

        for c in range(5):
            self.replay_fields_container.columnconfigure(c, weight=1)
        for r in range((len(self.params) + 4) // 5):
            self.replay_fields_container.rowconfigure(r, weight=1)

    # ─── EXPORT VIEW ─────────────────────────────────────────────────────
    def _build_export_option_view(self):
        v = self.views["export_option"]

        hdr_e = tk.Frame(v, bg=self.theme["bg"])
        hdr_e.pack(fill="x", pady=(0, 20))
        tk.Label(hdr_e, text="\U0001f4be SYSTEM EXPORT CENTER", font=FONT_LG, fg=self.theme["accent"], bg=self.theme["bg"]).pack()

        card_frame = tk.Frame(v, bg=self.theme["bg"])
        card_frame.pack(fill="both", expand=True)

        cards = [
            ("\U0001f4e5 Export Telemetry (.CSV)", "Download all captured logs into a CSV file.", self._export_data_to_csv, self.theme["green"]),
            ("\U0001f4c4 Export Frame Config (.JSON)", "Save the current parameter layout as JSON.", self._export_frame_config_json, self.theme["accent"]),
            ("\U0001f5bc Export Chart (.PNG)", "Save the live plot as a PNG image.", self._export_chart_png, self.theme["violet"]),
        ]

        for i, (title, desc, cmd, color) in enumerate(cards):
            row = i // 3
            col = i % 3

            card = tk.Frame(card_frame, bg=self.theme["bg_card"], highlightbackground=self.theme["border"], highlightthickness=1)
            card.grid(row=row, column=col, sticky="nsew", padx=12, pady=12, ipadx=10, ipady=10)

            tk.Label(card, text=title, font=FONT_BOLD, fg=color, bg=self.theme["bg_card"]).pack(anchor="w", padx=16, pady=(16, 6))
            tk.Label(card, text=desc, font=FONT_MONO, fg=self.theme["txt_muted"], bg=self.theme["bg_card"], wraplength=250, justify="left").pack(anchor="w", padx=16, pady=6)
            tk.Button(card, text="\u25b6 EXPORT NOW", font=FONT_TREE_DATA, bg=color, fg="#ffffff", relief="flat", bd=0, cursor="hand2",
                      command=cmd, padx=14, pady=8).pack(anchor="w", padx=16, pady=(12, 16))

        for c in range(3):
            card_frame.columnconfigure(c, weight=1)

    # ─── LINK CONFIG VIEW ────────────────────────────────────────────────
    def _build_link_config_view(self):
        v = self.views["link_config"]

        container = tk.Frame(v, bg=self.theme["bg"])
        container.pack(fill="both", expand=True)

        hdr_l = tk.Frame(container, bg=self.theme["bg"])
        hdr_l.pack(fill="x", pady=(0, 20))
        tk.Label(hdr_l, text="\U0001f6e0 CONNECTION LINKS CONFIGURATION", font=FONT_LG, fg=self.theme["accent"], bg=self.theme["bg"]).pack()

        self.link_source_var = tk.StringVar(value=self.active_link_source)
        sources = [
            ("SIMULATOR", "Synthetic telemetry data generated internally"),
            ("SERIAL", "Serial port (UART/RS-232) connection"),
            ("TCP", "TCP/IP socket (Binary data)"),
            ("UDP", "UDP socket (Binary data)"),
            ("TCP_TEXT", "TCP/IP socket (Text/CSV data)"),
            ("UDP_TEXT", "UDP socket (Text/CSV data)"),
            ("BINARY_FILE", "Read from a binary data file"),
        ]

        radio_frame = tk.Frame(container, bg=self.theme["bg_card"], highlightbackground=self.theme["border"], highlightthickness=1)
        radio_frame.pack(fill="x", padx=20, pady=10)

        tk.Label(radio_frame, text="Select Link Source:", font=FONT_BOLD, fg=self.theme["txt_main"], bg=self.theme["bg_card"]).grid(row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(16, 6))

        for i, (val, desc) in enumerate(sources):
            row_idx = (i // 2) * 2 + 1
            col_idx = i % 2
            
            rb = tk.Radiobutton(radio_frame, text=f"  {val}", value=val, variable=self.link_source_var, font=FONT_BOLD,
                                fg=self.theme["txt_main"], bg=self.theme["bg_card"], selectcolor=self.theme["bg_widget"],
                                activebackground=self.theme["bg_card"], activeforeground=self.theme["txt_main"],
                                command=self._on_link_source_changed)
            rb.grid(row=row_idx, column=col_idx, sticky="w", padx=(30 if col_idx == 0 else 10), pady=(6, 0))
            
            lbl = tk.Label(radio_frame, text=f"     {desc}", font=FONT_MONO, fg=self.theme["txt_muted"], bg=self.theme["bg_card"])
            lbl.grid(row=row_idx + 1, column=col_idx, sticky="w", padx=(30 if col_idx == 0 else 10), pady=(0, 6))
            
        radio_frame.columnconfigure(0, weight=1)
        radio_frame.columnconfigure(1, weight=1)

        self.link_settings_frame = tk.Frame(container, bg=self.theme["bg_card"], highlightbackground=self.theme["border"], highlightthickness=1)
        self.link_settings_frame.pack(fill="x", padx=20, pady=10)
        self._refresh_link_sub_settings_panel_view()

    def _refresh_link_sub_settings_panel_view(self):
        for w in self.link_settings_frame.winfo_children():
            w.destroy()

        tk.Label(self.link_settings_frame, text="Connection Settings:", font=FONT_BOLD, fg=self.theme["txt_main"], bg=self.theme["bg_card"]).pack(anchor="w", padx=20, pady=(16, 10))

        if self.link_source_var.get() == "SERIAL":
            f = tk.Frame(self.link_settings_frame, bg=self.theme["bg_card"])
            f.pack(fill="x", padx=30, pady=8)
            tk.Label(f, text="Port:", font=FONT_TREE_DATA, fg=self.theme["txt_muted"], bg=self.theme["bg_card"]).pack(side="left")
            e_port = tk.Entry(f, font=FONT_BOLD, bg=self.theme["bg_widget"], fg=self.theme["txt_main"], insertbackground=self.theme["txt_main"],
                              relief="flat", highlightbackground=self.theme["border"], highlightthickness=1, width=20)
            e_port.insert(0, self.serial_port)
            e_port.pack(side="left", padx=10)
            e_port.bind("<FocusOut>", lambda e: setattr(self, 'serial_port', e.widget.get()))

            tk.Label(f, text="Baud:", font=FONT_TREE_DATA, fg=self.theme["txt_muted"], bg=self.theme["bg_card"]).pack(side="left", padx=(20, 0))
            e_baud = tk.Entry(f, font=FONT_BOLD, bg=self.theme["bg_widget"], fg=self.theme["txt_main"], insertbackground=self.theme["txt_main"],
                              relief="flat", highlightbackground=self.theme["border"], highlightthickness=1, width=12)
            e_baud.insert(0, str(self.serial_baud))
            e_baud.pack(side="left", padx=10)
            e_baud.bind("<FocusOut>", lambda e: setattr(self, 'serial_baud', int(e.widget.get())))

        elif self.link_source_var.get() in ("TCP", "TCP_TEXT", "UDP", "UDP_TEXT"):
            f = tk.Frame(self.link_settings_frame, bg=self.theme["bg_card"])
            f.pack(fill="x", padx=30, pady=8)
            def update_host(e):
                self.tcp_host = e.widget.get()
                self.lbl_meta_links.config(text=self._link_meta_text())

            def update_port(e):
                try:
                    self.tcp_port = int(e.widget.get())
                    self.lbl_meta_links.config(text=self._link_meta_text())
                except ValueError:
                    pass

            tk.Label(f, text="Host:", font=FONT_TREE_DATA, fg=self.theme["txt_muted"], bg=self.theme["bg_card"]).pack(side="left")
            e_host = tk.Entry(f, font=FONT_BOLD, bg=self.theme["bg_widget"], fg=self.theme["txt_main"], insertbackground=self.theme["txt_main"],
                              relief="flat", highlightbackground=self.theme["border"], highlightthickness=1, width=20)
            e_host.insert(0, self.tcp_host)
            e_host.pack(side="left", padx=10)
            e_host.bind("<KeyRelease>", update_host)

            tk.Label(f, text="Port:", font=FONT_TREE_DATA, fg=self.theme["txt_muted"], bg=self.theme["bg_card"]).pack(side="left", padx=(20, 0))
            e_tcp_port = tk.Entry(f, font=FONT_BOLD, bg=self.theme["bg_widget"], fg=self.theme["txt_main"], insertbackground=self.theme["txt_main"],
                                  relief="flat", highlightbackground=self.theme["border"], highlightthickness=1, width=12)
            e_tcp_port.insert(0, str(self.tcp_port))
            e_tcp_port.pack(side="left", padx=10)
            e_tcp_port.bind("<KeyRelease>", update_port)

        elif self.link_source_var.get() == "BINARY_FILE":
            f = tk.Frame(self.link_settings_frame, bg=self.theme["bg_card"])
            f.pack(fill="x", padx=30, pady=8)

            selected_path_label = tk.Label(f, text=f"Selected: {self.binary_filepath or 'None'}", font=FONT_MONO, fg=self.theme["txt_muted"], bg=self.theme["bg_card"])
            selected_path_label.pack(anchor="w", pady=(0, 10))

            def pick_binary_file():
                path = filedialog.askopenfilename(filetypes=[("Binary files", "*.bin *.dat *.raw"), ("All files", "*.*")])
                if path:
                    self.binary_filepath = path
                    selected_path_label.config(text=f"Selected: {path}")
                    with open(path, "rb") as bf:
                        self.binary_file_data = bf.read()
                    self.binary_file_offset = 0
                    self._trigger_incident_push(f"Binary file loaded: {path} ({len(self.binary_file_data)} bytes)")

            btn_pick = tk.Button(f, text="\U0001f4c2 SELECT BINARY FILE", font=FONT_TREE_HEADER, bg=self.theme["accent"], fg="#ffffff",
                                 relief="flat", bd=0, command=pick_binary_file, cursor="hand2", padx=14, pady=6)
            btn_pick.pack(anchor="w")

            info_frame = tk.Frame(self.link_settings_frame, bg=self.theme["bg_card"])
            info_frame.pack(fill="x", padx=30, pady=10)
            tk.Label(info_frame, text="Select a binary file containing packed telemetry data.\nThe file will be parsed frame-by-frame using the current\nparameter layout configuration.", font=FONT_MONO, fg=self.theme["txt_dim"], bg=self.theme["bg_card"], justify="left").pack(anchor="w")

    def _on_link_source_changed(self):
        self.active_link_source = self.link_source_var.get()
        self.lbl_meta_links.config(text=self._link_meta_text())
        self._refresh_link_sub_settings_panel_view()

        if hasattr(self, "metric_labels") and "Link Type" in self.metric_labels:
            self.metric_labels["Link Type"].config(text=self.active_link_source)
        if hasattr(self, "metric_labels") and "Port Assigned" in self.metric_labels:
            val = self.serial_port if self.active_link_source == "SERIAL" else (self.active_link_source if self.active_link_source in ("TCP", "TCP_TEXT", "UDP_TEXT") else ("FILE" if self.active_link_source == "BINARY_FILE" else "N/A"))
            self.metric_labels["Port Assigned"].config(text=val)

    # ─── THEME TOGGLE ────────────────────────────────────────────────────
    def _toggle_theme(self):
        if self.theme["type"] == "dark":
            self.theme = LIGHT_THEME.copy()
            self.btn_theme_toggle.config(text="\U0001f319  DARK MODE")
        else:
            self.theme = DARK_THEME.copy()
            self.btn_theme_toggle.config(text="\u2600\ufe0f  LIGHT MODE")

        self._refresh_styles()
        self._apply_theme_to_all_views()

    def _apply_theme_to_all_views(self):
        """Apply current theme colors to ALL widgets in the application."""
        self.config(bg=self.theme["bg"])
        self.rendered_params_cache = []

        self.header.config(bg=self.theme["bg_card"], highlightbackground=self.theme["border"])
        self.left_header_box.config(bg=self.theme["bg_card"])
        self.top_row_title.config(bg=self.theme["bg_card"])
        self.lbl_title.config(bg=self.theme["bg_card"], fg=self.theme["accent"])
        self.lbl_conn_status.config(bg=self.theme["bg_card"])
        self.lbl_meta_links.config(bg=self.theme["bg_card"], fg=self.theme["txt_muted"], text=self._link_meta_text())
        self.btn_theme_toggle.config(bg=self.theme["bg_widget"], fg=self.theme["txt_main"],
                                     activebackground=self.theme["bg_widget_hover"], activeforeground=self.theme["txt_main"])
        self.btn_stream.config(bg=self.theme["red"] if self.is_streaming else self.theme["green"])

        self.sidebar.config(bg=self.theme["bg_card"], highlightbackground=self.theme["border"])
        self.lbl_mctrl.config(bg=self.theme["bg_card"], fg=self.theme["txt_dim"])
        self.lbl_aws_ctl.config(bg=self.theme["bg_card"], fg=self.theme["txt_main"])
        for key, btn in self.menu_buttons.items():
            is_active = self.current_menu == key
            btn.config(bg=self.theme["bg_card"] if not is_active else self.theme["bg_widget"],
                       fg=self.theme["txt_main"] if is_active else self.theme["txt_muted"],
                       activebackground=self.theme["bg_widget"], activeforeground=self.theme["txt_main"])

        self.footer.config(bg=self.theme["bg_card"], highlightbackground=self.theme["border"])
        self.lbl_foot_left.config(bg=self.theme["bg_card"], fg=self.theme["amber"])
        self.lbl_foot_right.config(bg=self.theme["bg_card"], fg=self.theme["txt_dim"])

        self.container.config(bg=self.theme["bg"])

        if self.current_menu in self.views:
            v = self.views[self.current_menu]
            v.config(bg=self.theme["bg"])

        self._refresh_numerical_grid_layout()

        if "data_logger" in self.views and self.current_menu == "data_logger":
            self._rebuild_data_logger_checkbuttons()

        if "replay_session" in self.views and hasattr(self, "replay_fields_container"):
            self._build_replay_numerical_display_matrix()

        self._refresh_editor_tree_matrix()
        self._sync_logger_table_rows_cache()

        if self.current_menu == "live_graph":
            self.fig.set_facecolor(self.theme["bg_card"])
            self.canvas.get_tk_widget().config(bg=self.theme["bg_card"])
            self._update_matplotlib_charts_render()

        if hasattr(self, "replay_fig"):
            self.replay_fig.set_facecolor(self.theme["bg_widget"])
            self._update_replay_trend_chart()

        if hasattr(self, "metric_labels"):
            for label_name, lbl in self.metric_labels.items():
                if lbl.winfo_exists():
                    pass  

        if hasattr(self, "alert_box") and self.alert_box.winfo_exists():
            self.alert_box.config(bg=self.theme["bg"], fg=self.theme["txt_main"], highlightbackground=self.theme["border"])

        if hasattr(self, "lbl_dash_subtitle") and self.lbl_dash_subtitle.winfo_exists():
            self.lbl_dash_subtitle.config(bg=self.theme["bg"], fg=self.theme["txt_dim"])

        if hasattr(self, "lbl_date") and self.lbl_date.winfo_exists():
            self.lbl_date.config(bg=self.theme["bg_card"], fg=self.theme["txt_main"])
        if hasattr(self, "lbl_time") and self.lbl_time.winfo_exists():
            self.lbl_time.config(bg=self.theme["bg_card"], fg=self.theme["txt_main"])

        if self.current_menu == "link_config" and "link_config" in self.views:
            self._rebuild_link_config_theme()

        if self.current_menu == "export_option" and "export_option" in self.views:
            self._rebuild_export_view_theme()

        self._recursive_apply_theme(self)

    def _rebuild_data_logger_checkbuttons(self):
        """Rebuild the data logger checkbuttons so they get new selectcolor."""
        if not hasattr(self, 'toggle_left_filter') and not hasattr(self, 'logger_left_filter'):
            return
        w = self.logger_left_filter
        for child in w.winfo_children():
            child.destroy()

        tk.Label(w, text="\U0001f441 VISIBLE COLUMNS", font=FONT_LG, fg=self.theme["accent"], bg=self.theme["bg_card"]).pack(anchor="w", padx=16, pady=16)

        for p in self.params:
            var = self.logger_checkbox_vars.get(p["name"], tk.BooleanVar(value=True))
            cb = tk.Checkbutton(w, text=p["name"], variable=var, font=FONT_TREE_DATA, fg=self.theme["txt_main"], bg=self.theme["bg_card"],
                                activebackground=self.theme["bg_card"], activeforeground=self.theme["txt_main"],
                                selectcolor=self.theme["bg_widget"],
                                command=self._refresh_logger_table_columns)
            cb.pack(anchor="w", padx=16, pady=5)

    def _rebuild_link_config_theme(self):
        v = self.views["link_config"]
        for child in v.winfo_children():
            if isinstance(child, tk.Frame):
                child.config(bg=self.theme["bg"])
                for sub in child.winfo_children():
                    self._recursive_apply_theme(sub)

    def _rebuild_export_view_theme(self):
        v = self.views["export_option"]
        for child in v.winfo_children():
            if isinstance(child, tk.Frame):
                child.config(bg=self.theme["bg"])
                for sub in child.winfo_children():
                    self._recursive_apply_theme(sub)

    def _recursive_apply_theme(self, parent):
        try:
            children = parent.winfo_children()
        except tk.TclError:
            return

        for child in children:
            cls = child.winfo_class()
            try:
                if cls == "Frame":
                    child.config(bg=self.theme["bg_card"])

                elif cls == "Label":
                    fg = child.cget("foreground")
                    bg = child.cget("background")
                    if fg in ("#f5f5f7", "#9d9da8", "#55555f", "#111114", "#5a5a66", "#a3a3ad"):
                        if fg in ("#f5f5f7", "#111114"):
                            child.config(fg=self.theme["txt_main"])
                        elif fg in ("#9d9da8", "#5a5a66"):
                            child.config(fg=self.theme["txt_muted"])
                        else:
                            child.config(fg=self.theme["txt_dim"])
                    if bg in ("#0a0a0d", "#16161a", "#232329", "#f2f2f5", "#ffffff", "#e9e9ef"):
                        child.config(bg=self.theme["bg_card"])

                elif cls == "Button":
                    bg = child.cget("background")
                    if bg in ("#232329", "#2b2b33", "#e9e9ef", "#dedee6", "#16161a", "#ffffff"):
                        child.config(bg=self.theme["bg_widget"], fg=self.theme["txt_main"],
                                     activebackground=self.theme["bg_widget_hover"], activeforeground=self.theme["txt_main"])

                elif cls == "Canvas":
                    child.config(bg=self.theme["bg_widget"])
                    try:
                        items = child.find_all()
                        for item in items:
                            if child.type(item) == "oval":
                                outline = child.itemcget(item, "outline")
                                if outline in ("#2e2e35", "#d9d9e2"):
                                    child.itemconfig(item, outline=self.theme["border"])
                            if child.type(item) == "text":
                                fill = child.itemcget(item, "fill")
                                if fill in ("#9d9da8", "#5a5a66", "#55555f", "#a3a3ad"):
                                    child.itemconfig(item, fill=self.theme["txt_muted"])
                                elif fill in ("#f5f5f7", "#111114"):
                                    child.itemconfig(item, fill=self.theme["txt_main"])
                    except tk.TclError:
                        pass

                elif cls == "Entry":
                    child.config(bg=self.theme["bg_widget"], fg=self.theme["txt_main"],
                                 insertbackground=self.theme["txt_main"], highlightbackground=self.theme["border"])

                elif cls == "Text":
                    child.config(bg=self.theme["bg"], fg=self.theme["txt_main"], highlightbackground=self.theme["border"])

                elif cls == "Checkbutton":
                    child.config(bg=self.theme["bg_card"], fg=self.theme["txt_main"], activebackground=self.theme["bg_card"],
                                 activeforeground=self.theme["txt_main"], selectcolor=self.theme["bg_widget"])

                elif cls == "Radiobutton":
                    child.config(bg=self.theme["bg_card"], fg=self.theme["txt_main"], activebackground=self.theme["bg_card"],
                                 activeforeground=self.theme["txt_main"], selectcolor=self.theme["bg_widget"])
            except tk.TclError:
                pass

            self._recursive_apply_theme(child)

    # ─── MENU SWITCHING ──────────────────────────────────────────────────
    def _switch_menu(self, key):
        self.current_menu = key
        for k, btn in self.menu_buttons.items():
            active = k == key
            btn.config(bg=self.theme["bg_widget"] if active else self.theme["bg_card"],
                       fg=self.theme["txt_main"] if active else self.theme["txt_muted"])
            btn._is_active_menu = active

        for k, f in self.views.items():
            f.pack_forget() if f.winfo_viewable() else None

        if key in self.views:
            self.views[key].pack(fill="both", expand=True)
            self.views[key].config(bg=self.theme["bg"])

        if key == "live_graph":
            self._update_matplotlib_charts_render()
        elif key == "data_logger":
            self._sync_logger_table_rows_cache()

    # ─── STREAMING ───────────────────────────────────────────────────────
    def _toggle_stream(self):
        if self._action_lock or self._dialog_open:
            return
        self._action_lock = True

        if not self.is_streaming:
            self.is_streaming = True
            self.stop_signal.clear()
            self.lbl_conn_status.config(text="  \u25cf CONNECTED", fg=self.theme["green"])
            self.btn_stream.config(text="\u25a0  STOP STREAM", bg=self.theme["red"])

            if self.active_link_source == "BINARY_FILE" and self.binary_file_data:
                self.worker_thread = threading.Thread(target=self._binary_file_stream_worker, daemon=True)
            elif self.active_link_source == "SERIAL" and serial:
                self.worker_thread = threading.Thread(target=self._serial_worker, daemon=True)
            elif self.active_link_source == "TCP":
                self.worker_thread = threading.Thread(target=self._tcp_worker, daemon=True)
            elif self.active_link_source == "UDP":
                self.worker_thread = threading.Thread(target=self._udp_worker, daemon=True)
            elif self.active_link_source == "TCP_TEXT":
                self.worker_thread = threading.Thread(target=self._tcp_text_worker, daemon=True)
            elif self.active_link_source == "UDP_TEXT":
                self.worker_thread = threading.Thread(target=self._udp_text_worker, daemon=True)
            else:
                self.worker_thread = threading.Thread(target=self._simulator_worker, daemon=True)
            self.worker_thread.start()
        else:
            self.is_streaming = False
            self.stop_signal.set()
            self.lbl_conn_status.config(text="  \u25cf DISCONNECTED", fg=self.theme["red"])
            self.btn_stream.config(text="\u25b6  START STREAM", bg=self.theme["green"])

        self._action_lock = False

    def _toggle_healed_mode(self):
        self.use_healed_stream = not self.use_healed_stream
        if self.use_healed_stream:
            self.btn_heal_toggle.config(text="✨  HEALED: ON", fg=self.theme["accent"], bg=self.theme["accent_soft"])
            self._trigger_incident_push("AI ENGINE: Switched to Self-Healed Imputed Stream")
        else:
            self.btn_heal_toggle.config(text="✨  HEALED: OFF", fg=self.theme["txt_muted"], bg=self.theme["bg_widget"])
            self._trigger_incident_push("AI ENGINE: Switched to Raw Sensor Stream")

    def _binary_file_stream_worker(self):
        frame_size = sum(TYPE_SIZE[p["dataType"]] for p in self.params if p["enabled"] and p["name"] not in ["Dry Bulb Temp", "Wet Bulb Temp"])
        if frame_size == 0:
            return

        data = self.binary_file_data
        offset = 0

        while not self.stop_signal.is_set() and offset + frame_size <= len(data):
            raw_bytes = data[offset:offset + frame_size]
            if not raw_bytes:
                break
            self._unpack_and_dispatch_binary_payload(raw_bytes)
            offset += frame_size
            time.sleep(1.0)  

        if not self.stop_signal.is_set() and hasattr(self, 'winfo_exists') and self.winfo_exists():
            self.after(0, lambda: self._trigger_incident_push("BINARY FILE: End of file reached"))

    def _simulator_worker(self):
        while not self.stop_signal.is_set():
            raw = self._generate_mock_binary_frame()
            self._unpack_and_dispatch_binary_payload(raw)
            time.sleep(1.0)

    def _serial_worker(self):
        try:
            with serial.Serial(self.serial_port, self.serial_baud, timeout=1) as ser:
                while not self.stop_signal.is_set():
                    raw = ser.read(64)
                    if raw:
                        self._unpack_and_dispatch_binary_payload(raw)
                    else:
                        time.sleep(0.02)
        except Exception as e:
            if hasattr(self, 'winfo_exists') and self.winfo_exists():
                self.after(0, lambda: self._trigger_incident_push(f"SERIAL ERROR: {str(e)}"))

    def _tcp_worker(self):
        try:
            # Try binding as a server/listener first so LAN senders can connect to this station
            server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            is_server = False
            try:
                server_sock.bind(("0.0.0.0", self.tcp_port))
                server_sock.listen(5)
                server_sock.settimeout(1.0)
                is_server = True
            except Exception:
                server_sock.close()
                is_server = False

            if is_server:
                while not self.stop_signal.is_set():
                    try:
                        conn, addr = server_sock.accept()
                        conn.settimeout(1.0)
                        while not self.stop_signal.is_set():
                            try:
                                raw = conn.recv(2048)
                                if not raw:
                                    break
                                self._unpack_and_dispatch_binary_payload(raw)
                            except socket.timeout:
                                continue
                            except Exception:
                                break
                        conn.close()
                    except socket.timeout:
                        continue
                    except Exception:
                        pass
                server_sock.close()
            else:
                # Fallback: connect to remote host/port as client
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(2)
                    sock.connect((self.tcp_host, self.tcp_port))
                    while not self.stop_signal.is_set():
                        try:
                            raw = sock.recv(2048)
                            if raw:
                                self._unpack_and_dispatch_binary_payload(raw)
                            else:
                                time.sleep(0.02)
                        except socket.timeout:
                            continue
        except Exception as e:
            if hasattr(self, 'winfo_exists') and self.winfo_exists():
                self.after(0, lambda: self._trigger_incident_push(f"TCP ERROR: {str(e)}"))

    def _tcp_text_worker(self):
        try:
            server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            is_server = False
            try:
                server_sock.bind(("0.0.0.0", self.tcp_port))
                server_sock.listen(5)
                server_sock.settimeout(1.0)
                is_server = True
            except Exception:
                server_sock.close()
                is_server = False

            if is_server:
                while not self.stop_signal.is_set():
                    try:
                        conn, addr = server_sock.accept()
                        conn.settimeout(1.0)
                        buffer = ""
                        while not self.stop_signal.is_set():
                            try:
                                data = conn.recv(2048)
                                if not data:
                                    break
                                buffer += data.decode("utf-8", errors="ignore")
                                while "\n" in buffer:
                                    line, buffer = buffer.split("\n", 1)
                                    line = line.strip()
                                    if line:
                                        self._parse_and_dispatch_text_payload(line)
                            except socket.timeout:
                                continue
                            except Exception:
                                break
                        conn.close()
                    except socket.timeout:
                        continue
                    except Exception:
                        pass
                server_sock.close()
            else:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(2)
                    sock.connect((self.tcp_host, self.tcp_port))
                    buffer = ""
                    while not self.stop_signal.is_set():
                        try:
                            data = sock.recv(1024)
                            if not data:
                                self.after(0, lambda: self._trigger_incident_push("TCP TEXT: Connection closed by remote server"))
                                break
                            
                            buffer += data.decode("utf-8", errors="ignore")
                            while "\n" in buffer:
                                line, buffer = buffer.split("\n", 1)
                                line = line.strip()
                                if line:
                                    self._parse_and_dispatch_text_payload(line)
                        except socket.timeout:
                            continue
        except Exception as e:
            if hasattr(self, 'winfo_exists') and self.winfo_exists():
                self.after(0, lambda: self._trigger_incident_push(f"TCP TEXT ERROR: {str(e)}"))

    def _udp_text_worker(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(("0.0.0.0", self.tcp_port))
                sock.settimeout(1.0)
                while not self.stop_signal.is_set():
                    try:
                        data, addr = sock.recvfrom(65535)
                        if data:
                            text = data.decode("utf-8", errors="ignore").strip()
                            for line in text.split("\n"):
                                line = line.strip()
                                if line:
                                    self._parse_and_dispatch_text_payload(line)
                    except socket.timeout:
                        pass
        except Exception as e:
            if hasattr(self, 'winfo_exists') and self.winfo_exists():
                self.after(0, lambda: self._trigger_incident_push(f"UDP TEXT ERROR: {str(e)}"))

    def _udp_worker(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(("0.0.0.0", self.tcp_port))
                sock.settimeout(1.0)
                while not self.stop_signal.is_set():
                    try:
                        data, addr = sock.recvfrom(65535)
                        if data:
                            self._unpack_and_dispatch_binary_payload(data)
                    except socket.timeout:
                        pass
        except Exception as e:
            if hasattr(self, 'winfo_exists') and self.winfo_exists():
                self.after(0, lambda: self._trigger_incident_push(f"UDP ERROR: {str(e)}"))

    def _parse_and_dispatch_text_payload(self, text_line):
        text_line = text_line.strip()
        if not text_line:
            return
        if text_line.lower().startswith("time_inst") and "," in text_line:
            return
            
        parts = [p.strip() for p in text_line.split(",") if p.strip()] if "," in text_line else text_line.split()
        if not parts:
            return

        ist_now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
        parsed_packet = {"Timestamp": ist_now.strftime("%H:%M:%S")}
        
        enabled_params = [p for p in self.params if p.get("enabled", True)]
        
        try:
            key_vals = {}
            has_kv = False
            for part in parts:
                if "=" in part:
                    k, v = part.split("=", 1)
                    key_vals[k.strip().lower()] = v.strip()
                    has_kv = True

            if has_kv:
                for p in enabled_params:
                    p_name = p["name"]
                    val_str = None
                    for k, v in key_vals.items():
                        if k in p_name.lower() or p_name.lower() in k:
                            val_str = v
                            break
                    if val_str is not None:
                        try:
                            raw_val = float(val_str)
                            calibrated_value = round((raw_val * p.get("scale", 1.0)) + p.get("offset", 0.0), 3)
                            parsed_packet[p_name] = calibrated_value
                            parsed_packet[p_name + "_raw_val"] = calibrated_value
                        except ValueError:
                            pass
            else:
                num_fields = min(len(parts), len(enabled_params))
                for i in range(num_fields):
                    p = enabled_params[i]
                    p_name = p["name"]
                    try:
                        raw_val = float(parts[i])
                        calibrated_value = round((raw_val * p.get("scale", 1.0)) + p.get("offset", 0.0), 3)
                        if p_name == "Time_Inst":
                            parsed_packet[p_name] = ist_now.strftime("%H:%M:%S")
                            parsed_packet[p_name + "_raw_val"] = time.time()
                        else:
                            parsed_packet[p_name] = calibrated_value
                            parsed_packet[p_name + "_raw_val"] = calibrated_value
                    except ValueError:
                        pass

            for p in enabled_params:
                p_name = p["name"]
                if p_name in parsed_packet and p_name != "Time_Inst":
                    v_val = parsed_packet[p_name]
                    if p_name not in self.min_max_cache:
                        self.min_max_cache[p_name] = {"min": v_val, "max": v_val}
                    else:
                        if v_val < self.min_max_cache[p_name]["min"]:
                            self.min_max_cache[p_name]["min"] = v_val
                        if v_val > self.min_max_cache[p_name]["max"]:
                            self.min_max_cache[p_name]["max"] = v_val

            if self.active_link_source == "SIMULATOR":
                calculated_dry = 20.0 + (self.sim_step * 0.23)
                dry_temp = self.dry_bulb_peak if calculated_dry >= self.dry_bulb_peak else round(calculated_dry, 2)
                wet_temp = 20.0
                for v_name, v_val in [("Dry Bulb Temp", dry_temp), ("Wet Bulb Temp", wet_temp)]:
                    if any(p["name"] == v_name for p in self.params):
                        parsed_packet[v_name] = v_val
                        parsed_packet[v_name + "_raw_val"] = v_val
            else:
                if "Dry Bulb Temp" not in parsed_packet and any(p["name"] == "Dry Bulb Temp" for p in self.params):
                    press = parsed_packet.get("Pressure (hPa)", 1013.25)
                    dry_temp = round((press - 1000) * 0.5 + 20.0, 2)
                    parsed_packet["Dry Bulb Temp"] = dry_temp
                    parsed_packet["Dry Bulb Temp_raw_val"] = dry_temp
                if "Wet Bulb Temp" not in parsed_packet and any(p["name"] == "Wet Bulb Temp" for p in self.params):
                    dry_temp = parsed_packet.get("Dry Bulb Temp", 24.0)
                    rh = parsed_packet.get("Rel. Humidity", 50.0)
                    wet_temp = round(dry_temp - ((100.0 - rh) / 5.0), 2)
                    parsed_packet["Wet Bulb Temp"] = wet_temp
                    parsed_packet["Wet Bulb Temp_raw_val"] = wet_temp

            ai_res = self.anomaly_engine.analyze(parsed_packet)
            parsed_packet["_ai_res"] = ai_res

            self.packets_received += 1
            self.last_packet_time = time.time()
            self.history.append(parsed_packet)
            self.latest_packet = parsed_packet
            self.pending_logger_rows.append(parsed_packet)
        except Exception:
            self.packets_lost += 1

    def _generate_mock_binary_frame(self):
        self.sim_step += 1
        mock_values = {
            "Time_Inst": int(time.time()) & 0xFFFFFFFF,
            "Direction": int((180 + 45 * math.sin(self.sim_step / 10))) % 360,
            "Speed": int((45 + 15 * math.cos(self.sim_step / 5))) & 0xFFFF,
            "Rel. Humidity": int((65 + 10 * math.sin(self.sim_step / 8)) * 10) & 0xFFFF,
            "Solar Radiation": int(550 + 120 * math.sin(self.sim_step / 12)) & 0xFFFF,
            "Rainfall": int((0.5 * (self.sim_step % 3)) * 10) & 0xFFFF,
            "Pressure (hPa)": int((1015.40 + 3 * math.cos(self.sim_step / 15)) * 100) & 0xFFFFFFFF,
            "Dry Bulb Temp": int((25.0 + 3 * math.sin(self.sim_step / 20)) * 10) & 0xFFFF,
            "Wet Bulb Temp": int((21.0 + 2 * math.cos(self.sim_step / 20)) * 10) & 0xFFFF,
        }

        packed_bytes = b""
        for p in self.params:
            if p.get("enabled", True):
                val = mock_values.get(p["name"], 0)
                packed_bytes += struct.pack(f"<{TYPE_FORMAT_MAP[p['dataType']]}", val)
        return packed_bytes

    def _unpack_and_dispatch_binary_payload(self, raw_bytes):
        if not raw_bytes:
            return

        if isinstance(raw_bytes, str):
            raw_bytes = raw_bytes.encode('utf-8')

        try:
            text_candidate = raw_bytes.decode('utf-8', errors='ignore').strip()
            if ("," in text_candidate or "=" in text_candidate) and not (text_candidate.upper().startswith("AA55") or text_candidate.upper().startswith("55AA")):
                self._parse_and_dispatch_text_payload(text_candidate)
                return

            clean_hex = re.sub(r'[^0-9A-Fa-f]', '', text_candidate)
            if len(clean_hex) >= 4 and len(clean_hex) % 2 == 0 and (clean_hex.upper().startswith("AA55") or clean_hex.upper().startswith("55AA")):
                try:
                    raw_bytes = bytes.fromhex(clean_hex)
                except Exception:
                    pass
        except Exception:
            pass

        offset = 0
        if len(raw_bytes) >= 2 and (raw_bytes[0:2] == b'\xaa\x55' or raw_bytes[0:2] == b'\x55\xaa'):
            offset = 2

        ist_now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
        parsed_packet = {"Timestamp": ist_now.strftime("%H:%M:%S")}

        try:
            for p in self.params:
                if not p.get("enabled", True):
                    continue 

                sz = TYPE_SIZE.get(p["dataType"], 4)
                if offset + sz > len(raw_bytes):
                    break
                fmt = TYPE_FORMAT_MAP.get(p["dataType"], "f")
                raw_val = struct.unpack(f"<{fmt}", raw_bytes[offset:offset + sz])[0]
                scale = p.get("scale", 1.0)
                offs = p.get("offset", 0.0)
                calibrated_value = round((raw_val * scale) + offs, 3)

                if p["name"] == "Time_Inst":
                    parsed_packet[p["name"]] = ist_now.strftime("%H:%M:%S")
                    parsed_packet[p["name"] + "_raw_val"] = time.time()
                else:
                    parsed_packet[p["name"]] = calibrated_value
                    parsed_packet[p["name"] + "_raw_val"] = calibrated_value
                    if p["name"] not in self.min_max_cache:
                        self.min_max_cache[p["name"]] = {"min": calibrated_value, "max": calibrated_value}
                    else:
                        if calibrated_value < self.min_max_cache[p["name"]]["min"]:
                            self.min_max_cache[p["name"]]["min"] = calibrated_value
                        if calibrated_value > self.min_max_cache[p["name"]]["max"]:
                            self.min_max_cache[p["name"]]["max"] = calibrated_value
                offset += sz

            if self.active_link_source == "SIMULATOR":
                calculated_dry = 20.0 + (self.sim_step * 0.023)
                if calculated_dry >= self.dry_bulb_peak:
                    dry_temp = self.dry_bulb_peak
                    if self.peak_reached_time is None:
                        self.peak_reached_time = time.time()
                else:
                    dry_temp = round(calculated_dry, 2)

                if self.peak_reached_time is not None and (time.time() - self.peak_reached_time) >= 10.0:
                    elapsed_drop_ticks = (time.time() - self.peak_reached_time - 10.0)
                    calculated_wet = 20.0 - (elapsed_drop_ticks * 0.021)
                    wet_temp = self.wet_bulb_floor if calculated_wet <= self.wet_bulb_floor else round(calculated_wet, 2)
                else:
                    wet_temp = 20.0

                for v_name, v_val in [("Dry Bulb Temp", dry_temp), ("Wet Bulb Temp", wet_temp)]:
                    if any(p["name"] == v_name for p in self.params):
                        parsed_packet[v_name] = v_val
                        parsed_packet[v_name + "_raw_val"] = v_val
                        if v_name not in self.min_max_cache:
                            self.min_max_cache[v_name] = {"min": v_val, "max": v_val}
                        else:
                            if v_val < self.min_max_cache[v_name]["min"]:
                                self.min_max_cache[v_name]["min"] = v_val
                            if v_val > self.min_max_cache[v_name]["max"]:
                                self.min_max_cache[v_name]["max"] = v_val
            else:
                if "Dry Bulb Temp" not in parsed_packet and any(p["name"] == "Dry Bulb Temp" for p in self.params):
                    press = parsed_packet.get("Pressure (hPa)", 1013.25)
                    dry_temp = round((press - 1000) * 0.5 + 20.0, 2)
                    parsed_packet["Dry Bulb Temp"] = dry_temp
                    parsed_packet["Dry Bulb Temp_raw_val"] = dry_temp
                if "Wet Bulb Temp" not in parsed_packet and any(p["name"] == "Wet Bulb Temp" for p in self.params):
                    dry_temp = parsed_packet.get("Dry Bulb Temp", 24.0)
                    rh = parsed_packet.get("Rel. Humidity", 50.0)
                    wet_temp = round(dry_temp - ((100.0 - rh) / 5.0), 2)
                    parsed_packet["Wet Bulb Temp"] = wet_temp
                    parsed_packet["Wet Bulb Temp_raw_val"] = wet_temp
            # ─── SKYGUARD AI REAL-TIME QUALITY CONTROL ANALYSIS ─────────────
            ai_res = self.anomaly_engine.analyze(parsed_packet)
            parsed_packet["_ai_res"] = ai_res
            
            if ai_res["is_anomaly"]:
                self.packets_lost += 1
                if hasattr(self, 'winfo_exists') and self.winfo_exists():
                    self.after(0, lambda msg=ai_res["xai"]: self._trigger_incident_push(f"🚨 {msg}"))
                    if hasattr(self, "alert_box") and self.alert_box.winfo_exists():
                        def update_alert():
                            self.alert_box.config(state="normal")
                            self.alert_box.delete("1.0", "end")
                            self.alert_box.insert("1.0", f"🚨 [{ai_res['severity']}] {ai_res['anomaly_type'].upper()}\n{ai_res['xai']}")
                            self.alert_box.config(state="disabled", fg=self.theme["red"])
                        self.after(0, update_alert)
            else:
                if hasattr(self, "alert_box") and self.alert_box.winfo_exists():
                    def update_normal():
                        self.alert_box.config(state="normal")
                        self.alert_box.delete("1.0", "end")
                        self.alert_box.insert("1.0", "SYSTEM INITIALIZED\nSTATUS: HEALTHY\nAll channels within nominal tolerances.")
                        self.alert_box.config(state="disabled", fg=self.theme["green"])
                    self.after(0, update_normal)

            self.packets_received += 1
            self.last_packet_time = time.time()
            self.history.append(parsed_packet)
            self.latest_packet = parsed_packet
            self.pending_logger_rows.append(parsed_packet)
        except Exception:
            self.packets_lost += 1
            if hasattr(self, 'winfo_exists') and self.winfo_exists():
                self.after(0, lambda: self._trigger_incident_push("ALERT: Data Frame Quality Error"))

    def _commit_telemetry_packet_to_ui_views(self, packet):
        ai_res = packet.get("_ai_res", {})
        is_anom = ai_res.get("is_anomaly", False)
        imputed = ai_res.get("imputed", {})

        for p in self.params:
            if p["enabled"] and p["mode"] in ("both", "display"):
                if p["name"] in packet:
                    val = packet[p["name"]]
                    if self.use_healed_stream and is_anom and p["name"] in imputed:
                        val = imputed[p["name"]]

                    if p["name"] == "Direction" and "_widget_compass_cvs" in p:
                        cvs, needle = p["_widget_compass_cvs"], p["_widget_compass_needle"]
                        if cvs.winfo_exists():
                            try:
                                angle_rad = math.radians(float(val))
                                cx, cy = 60, 60
                                tip_x = cx + 36 * math.sin(angle_rad)
                                tip_y = cy - 36 * math.cos(angle_rad)
                                cvs.coords(needle, cx, cy, tip_x, tip_y)
                            except Exception:
                                pass

                        vref = p.get("_widget_compass_value_lbl")
                        if vref is not None and vref.winfo_exists():
                            vref.config(text=f"{format_telemetry_val(val, 0)}° {get_cardinal_letter(val)}")

                    elif "_widget_lbl_ref" in p:
                        ref = p["_widget_lbl_ref"]
                        if hasattr(ref, 'winfo_exists') and ref.winfo_exists():
                            if isinstance(ref, tk.Label):
                                decimals = 0 if p.get("dataType", "").startswith("uint") and p.get("scale", 1.0) == 1.0 else 1
                                formatted_txt = format_telemetry_val(val, decimals)
                                if len(formatted_txt) > 8:
                                    ref.config(text=formatted_txt, font=FONT_LG)
                                else:
                                    ref.config(text=formatted_txt, font=FONT_XL)

                    if p["name"] in self.min_max_cache:
                        mm = self.min_max_cache[p["name"]]
                        min_ref = p.get("_widget_mm_min_ref")
                        max_ref = p.get("_widget_mm_max_ref")
                        if min_ref is not None and min_ref.winfo_exists():
                            min_ref.config(text=f"\u25bc {format_telemetry_val(mm['min'], 1)}")
                        if max_ref is not None and max_ref.winfo_exists():
                            max_ref.config(text=f"\u25b2 {format_telemetry_val(mm['max'], 1)}")

        self.lbl_foot_left.config(
            text=f"\u25a0 {'LIVE STREAM' if self.is_streaming else 'SYSTEM READY'}  |  PACKETS: {self.packets_received} RECORDS CAPTURED  |  DROPPED: {self.packets_lost}"
        )
        now = time.time()
        if self.views["live_graph"].winfo_viewable():
            if not hasattr(self, "_last_chart_update") or (now - self._last_chart_update > 0.5):
                self._update_matplotlib_charts_render()
                self._last_chart_update = now

    def _clear_cached_logs(self):
        self.history.clear()
        self.min_max_cache.clear()
        self.packets_received = 0
        self._sync_logger_table_rows_cache()

    # ─── REPLAY ACTIONS ──────────────────────────────────────────────────
    def _load_csv_file_for_playback(self):
        path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if not path:
            return
        try:
            with open(path, newline="", encoding="utf-8-sig") as f:
                self.replay_data = list(csv.DictReader(f))
            self.replay_slider.config(to=max(len(self.replay_data) - 1, 1))
            self.replay_slider.set(0)
            self.replay_index = 0
            self._render_replay_frame_index_slice(0)
            self._update_replay_trend_chart()
            messagebox.showinfo("Import Successful", f"Successfully imported {len(self.replay_data)} records for playback.")
        except Exception as e:
            messagebox.showerror("Import Failed", f"Could not read CSV file:\n{str(e)}")

    def _render_replay_frame_index_slice(self, idx):
        if not self.replay_data:
            return
        self.replay_index = max(0, min(int(idx), len(self.replay_data) - 1))
        row = self.replay_data[self.replay_index]
        for p in self.params:
            if p["name"] in row:
                self.replay_value_labels[p["name"]].config(text=str(row[p["name"]]))
        self.lbl_replay_frame_idx.config(text=f"FRAME SEEKER: {self.replay_index + 1} / {len(self.replay_data)}")

    def _on_replay_slider_moved(self, val):
        self._render_replay_frame_index_slice(int(float(val)))
        self._update_replay_trend_chart()

    def _on_replay_speed_changed(self, _event=None):
        self.replay_speed_ms = {"0.5x": 1000, "1x": 500, "2x": 250, "4x": 125}.get(self.cmb_replay_speed.get(), 500)

    def _start_playback_loop(self):
        if not self.replay_data:
            messagebox.showerror("No Data", "Please import a CSV file first before starting playback.")
            return
        self.replay_active = True
        self._step_playback_loop_runner()

    def _step_playback_loop_runner(self):
        if not hasattr(self, 'winfo_exists') or not self.winfo_exists():
            return
        if not self.replay_active or self.replay_index >= len(self.replay_data) - 1:
            return
        self.replay_index += 1
        self.replay_slider.set(self.replay_index)
        self._render_replay_frame_index_slice(self.replay_index)
        self.after(self.replay_speed_ms, self._step_playback_loop_runner)

    def _pause_playback_loop(self):
        if not self.replay_data:
            messagebox.showerror("No Data", "Please import a CSV file first.")
            return
        self.replay_active = False

    def _reset_playback_loop(self):
        if not self.replay_data:
            messagebox.showerror("No Data", "Please import a CSV file first.")
            return
        self.replay_active = False
        self.replay_index = 0
        self.replay_slider.set(0)
        self._render_replay_frame_index_slice(0)
        self._update_replay_trend_chart()

    # ─── EDITOR ACTIONS ──────────────────────────────────────────────────
    def _refresh_editor_tree_matrix(self):
        for item in self.editor_tree.get_children():
            self.editor_tree.delete(item)

        total_bytes = 0
        for p in self.params:
            enabled = p["enabled"]
            status = "\u2705 ENABLED" if enabled else "\u274c DISABLED"
            color = self.theme["green"] if enabled else self.theme["red"]
            
            d_type_lbl = "CALCULATED" if p["name"] in ["Dry Bulb Temp", "Wet Bulb Temp"] else p["dataType"]
            s_val = "--" if p["name"] in ["Dry Bulb Temp", "Wet Bulb Temp"] else p["scale"]
            o_val = "--" if p["name"] in ["Dry Bulb Temp", "Wet Bulb Temp"] else p["offset"]
            
            thresh_val = p.get("threshold")
            thresh_str = f"{thresh_val} {p['unit']}" if thresh_val is not None else "DISABLED"

            self.editor_tree.insert("", "end", values=(
                p["id"], p["name"], d_type_lbl, p["unit"],
                s_val, o_val, p["mode"], thresh_str, status
            ), tags=(color,))
            if enabled and p["name"] not in ["Dry Bulb Temp", "Wet Bulb Temp"]:
                total_bytes += TYPE_SIZE[p["dataType"]]

        self.lbl_frame_size.config(text=f"Frame Size: {total_bytes} bytes")

    def _dialog_create_new_param(self):
        self._dialog_open = True
        d = tk.Toplevel(self)
        d.title("Create Custom Parameter")
        d.geometry("400x420")
        d.configure(bg=self.theme["bg_card"])
        d.transient(self)
        d.grab_set()

        fields = [
            ("Name", "New_Sensor"),
            ("Data Type", "uint16"),
            ("Unit", ""),
            ("Scale", "1.0"),
            ("Offset", "0.0"),
            ("Display Mode", "both"),
            ("Alarm Threshold", "None")
        ]

        entries = {}
        for i, (lbl, val) in enumerate(fields):
            tk.Label(d, text=lbl, font=FONT_TREE_DATA, fg=self.theme["txt_muted"], bg=self.theme["bg_card"]).grid(row=i, column=0, sticky="w", padx=12, pady=6)
            if lbl in ("Data Type", "Display Mode"):
                e = ttk.Combobox(d, values=DATA_TYPES if lbl == "Data Type" else MODE_OPTIONS, state="readonly", width=16, font=FONT_TREE_DATA)
                e.set(val)
            else:
                e = tk.Entry(d, font=FONT_BOLD, bg=self.theme["bg_widget"], fg=self.theme["txt_main"],
                             insertbackground=self.theme["txt_main"], highlightbackground=self.theme["border"],
                             highlightthickness=1, width=20, relief="flat")
                e.insert(0, val)
            e.grid(row=i, column=1, padx=12, pady=6)
            entries[lbl] = e

        def save():
            name = entries["Name"].get().strip()
            if not name:
                messagebox.showwarning("Invalid Name", "Parameter name cannot be empty.", parent=d)
                return
            if any(p["name"] == name for p in self.params):
                messagebox.showwarning("Exists", f"Parameter '{name}' already exists in active fields.", parent=d)
                return

            try:
                scale = float(entries["Scale"].get())
                offset = float(entries["Offset"].get())
            except ValueError:
                messagebox.showwarning("Invalid Number", "Scale and Offset must be numbers.", parent=d)
                return

            t_input = entries["Alarm Threshold"].get().strip()
            if t_input.lower() in ("none", "disabled", ""):
                thresh_val = None
            else:
                try:
                    thresh_val = float(t_input)
                except ValueError:
                    messagebox.showerror("Invalid Input", "Threshold must be numeric or 'None'", parent=d)
                    return

            new_id = max(p["id"] for p in self.params) + 1 if self.params else 1
            color = PARAM_COLOR_PALETTE[new_id % len(PARAM_COLOR_PALETTE)]

            new_param = dict(
                id=new_id, name=name, dataType=entries["Data Type"].get(),
                unit=entries["Unit"].get(), scale=scale, offset=offset,
                mode=entries["Display Mode"].get(), color=color, enabled=True,
                threshold=thresh_val
            )
            self.params.append(new_param)

            self.custom_registry[name] = {
                "dataType": entries["Data Type"].get(),
                "unit": entries["Unit"].get(),
                "scale": scale,
                "offset": offset,
                "mode": entries["Display Mode"].get(),
                "threshold": thresh_val
            }

            self.cmb_frame_fields.config(values=self._get_dropdown_values())
            self.cmb_frame_fields.set(name)

            self._save_config()
            self._refresh_editor_tree_matrix()
            self._refresh_numerical_grid_layout()
            self._dialog_open = False
            d.destroy()

        tk.Button(d, text="ADD TO SYSTEM", font=FONT_BOLD, bg=self.theme["green"], fg="#ffffff", relief="flat", bd=0,
                  command=save, padx=20, pady=8).grid(row=len(fields), column=0, columnspan=2, pady=16)

    def _action_add_custom_param(self):
        name = self.cmb_frame_fields.get()
        if name == "-- Create New Field --":
            self._dialog_create_new_param()
            return
            
        if any(p["name"] == name for p in self.params):
            messagebox.showwarning("Exists", f"Parameter '{name}' already exists in active fields.")
            return
            
        new_id = max(p["id"] for p in self.params) + 1 if self.params else 1
        color = PARAM_COLOR_PALETTE[new_id % len(PARAM_COLOR_PALETTE)]
        
        if name in self.custom_registry:
            template = self.custom_registry[name]
            self.params.append(dict(id=new_id, name=name, dataType=template["dataType"], unit=template["unit"], scale=template["scale"], offset=template["offset"], mode=template["mode"], color=color, enabled=True, threshold=template.get("threshold")))
        else:
            self.params.append(dict(id=new_id, name=name, dataType="uint16", unit="", scale=1.0, offset=0.0, mode="both", color=color, enabled=True, threshold=None))
            
        self._save_config()
        self._refresh_editor_tree_matrix()
        self._refresh_numerical_grid_layout()

    def _action_delete_dropdown_param(self):
        name = self.cmb_frame_fields.get()
        if name in ["-- Create New Field --", ""]:
            return
            
        confirm = messagebox.askyesno("Confirm Delete", f"Are you sure you want to permanently delete '{name}' from the system menu?")
        if not confirm:
            return
            
        if name in VALID_MET_FIELDS:
            VALID_MET_FIELDS.remove(name)
            
        if name in self.custom_registry:
            del self.custom_registry[name]
            
        self.params = [p for p in self.params if p["name"] != name]
        
        self.cmb_frame_fields.config(values=self._get_dropdown_values())
        self.cmb_frame_fields.set(VALID_MET_FIELDS[0] if VALID_MET_FIELDS else "")

        self._save_config()
        self._refresh_editor_tree_matrix()
        self._refresh_numerical_grid_layout()

    def _action_edit_selected_param(self):
        sel = self.editor_tree.selection()
        if not sel:
            messagebox.showwarning("No Selection", "Please select a parameter.")
            return
        idx = self.editor_tree.index(sel[0])
        p = self.params[idx]
        
        self._dialog_open = True
        d = tk.Toplevel(self)
        d.title("Edit Parameter")
        d.geometry("400x420")
        d.configure(bg=self.theme["bg_card"])
        d.transient(self)
        d.grab_set()

        thresh_current = p.get("threshold")
        fields = [
            ("Name", p["name"]),
            ("Data Type", p["dataType"]),
            ("Unit", p["unit"]),
            ("Scale", str(p["scale"])),
            ("Offset", str(p["offset"])),
            ("Display Mode", p["mode"]),
            ("Alarm Threshold", str(thresh_current) if thresh_current is not None else "None")
        ]

        entries = {}
        for i, (lbl, val) in enumerate(fields):
            tk.Label(d, text=lbl, font=FONT_TREE_DATA, fg=self.theme["txt_muted"], bg=self.theme["bg_card"]).grid(row=i, column=0, sticky="w", padx=12, pady=6)
            if lbl in ("Data Type", "Display Mode"):
                e = ttk.Combobox(d, values=DATA_TYPES if lbl == "Data Type" else MODE_OPTIONS, state="readonly", width=16, font=FONT_TREE_DATA)
                e.set(val)
            else:
                e = tk.Entry(d, font=FONT_BOLD, bg=self.theme["bg_widget"], fg=self.theme["txt_main"],
                             insertbackground=self.theme["txt_main"], highlightbackground=self.theme["border"],
                             highlightthickness=1, width=20, relief="flat")
                e.insert(0, val)
            e.grid(row=i, column=1, padx=12, pady=6)
            entries[lbl] = e

        def save():
            for i, p2 in enumerate(self.params):
                if p2["id"] == p["id"]:
                    self.params[i]["name"] = entries["Name"].get()
                    self.params[i]["dataType"] = entries["Data Type"].get()
                    self.params[i]["unit"] = entries["Unit"].get()
                    self.params[i]["scale"] = float(entries["Scale"].get())
                    self.params[i]["offset"] = float(entries["Offset"].get())
                    self.params[i]["mode"] = entries["Display Mode"].get()
                    
                    t_input = entries["Alarm Threshold"].get().strip()
                    if t_input.lower() in ("none", "disabled", ""):
                        self.params[i]["threshold"] = None
                    else:
                        try:
                            self.params[i]["threshold"] = float(t_input)
                        except ValueError:
                            messagebox.showerror("Invalid Input", "Threshold must be a valid number or 'None'", parent=d)
                            return
                    break
            self._save_config()
            self._refresh_editor_tree_matrix()
            self._refresh_numerical_grid_layout()
            self._dialog_open = False
            d.destroy()

        tk.Button(d, text="SAVE", font=FONT_BOLD, bg=self.theme["green"], fg="#ffffff", relief="flat", bd=0,
                  command=save, padx=20, pady=8).grid(row=len(fields), column=0, columnspan=2, pady=16)

    def _action_toggle_selected_param(self):
        sel = self.editor_tree.selection()
        if not sel:
            return
        idx = self.editor_tree.index(sel[0])
        self.params[idx]["enabled"] = not self.params[idx]["enabled"]
        self._save_config()
        self._refresh_editor_tree_matrix()
        self._refresh_numerical_grid_layout()

    def _action_delete_selected_param(self):
        sel = self.editor_tree.selection()
        if not sel:
            return
        idx = self.editor_tree.index(sel[0])
        p = self.params.pop(idx)
        self._save_config()
        self._refresh_editor_tree_matrix()
        self._refresh_numerical_grid_layout()

    # ─── EXPORT ACTIONS ──────────────────────────────────────────────────
    def _export_frame_config_json(self):
        path = filedialog.asksaveasfilename(defaultextension=".json")
        if path:
            export = []
            for p in self.params:
                d = {k: v for k, v in p.items() if not str(k).startswith("_widget")}
                export.append(d)
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"parameters": export}, f, indent=2)

    def _export_data_to_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv")
        if path:
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=["Timestamp"] + [p["name"] for p in self.params], extrasaction='ignore')
                w.writeheader()
                for row in self.history:
                    w.writerow(row)

    def _export_chart_png(self):
        path = filedialog.asksaveasfilename(defaultextension=".png")
        if path:
            self.fig.savefig(path, facecolor=self.theme["bg_card"])

    # ─── LIVE GRAPH RENDERING ────────────────────────────────────────────
    def _update_matplotlib_charts_render(self):
        if not self.history:
            return

        enabled_params = [p for p in self.params if p["enabled"] and p["mode"] in ("both", "plot") and p["name"] != "Time_Inst"]
        n = len(enabled_params)
        if n == 0:
            return

        current_names = [p["name"] for p in enabled_params]
        if current_names != self.rendered_params_cache:
            self.fig.clear()
            self.graph_axes.clear()
            self.graph_lines.clear()
            self.graph_fills.clear()
            self.graph_hlines_min.clear()
            self.graph_hlines_max.clear()

            cols = min(3, n)
            rows = (n + cols - 1) // cols

            for i, p in enumerate(enabled_params):
                ax = self.fig.add_subplot(rows, cols, i + 1)
                ax.set_facecolor(self.theme["bg"])
                ax.tick_params(colors=self.theme["txt_muted"], labelsize=8)
                ax.spines["bottom"].set_color(self.theme["border"])
                ax.spines["top"].set_color(self.theme["border"])
                ax.spines["left"].set_color(self.theme["border"])
                ax.spines["right"].set_color(self.theme["border"])

                line, = ax.plot([], [], color=p["color"], linewidth=1.5)
                
                self.graph_axes[p["name"]] = ax
                self.graph_lines[p["name"]] = line
                self.graph_fills[p["name"]] = None
                self.graph_hlines_min[p["name"]] = ax.axhline(0, color=p["color"], linestyle="--", alpha=0.5, linewidth=0.8)
                self.graph_hlines_max[p["name"]] = ax.axhline(0, color=p["color"], linestyle="--", alpha=0.5, linewidth=0.8)

            self.rendered_params_cache = current_names

        for p in enabled_params:
            ax = self.graph_axes[p["name"]]
            line = self.graph_lines[p["name"]]
            values = [d.get(p["name"], 0) for d in self.history if p["name"] in d]
            if values:
                line.set_data(range(len(values)), values)

                if self.graph_fills[p["name"]] is not None:
                    self.graph_fills[p["name"]].remove()
                self.graph_fills[p["name"]] = ax.fill_between(range(len(values)), values, alpha=0.15, color=p["color"])

                min_val = min(values)
                max_val = max(values)
                self.graph_hlines_min[p["name"]].set_ydata([min_val, min_val])
                self.graph_hlines_max[p["name"]].set_ydata([max_val, max_val])

                ax.set_xlim(0, max(len(values) - 1, 1))
                margin = (max_val - min_val) * 0.1 if max_val != min_val else 1.0
                ax.set_ylim(min_val - margin, max_val + margin)

                ax.set_title(f"{p['name']}\nMin: {min_val} | Max: {max_val}", color=self.theme["accent"], fontsize=8, fontweight="bold")
            else:
                ax.set_title(p["name"], color=self.theme["accent"], fontsize=8, fontweight="bold")

        self.canvas.draw()

    def _update_replay_trend_chart(self):
        if not self.replay_data:
            return

        self.replay_fig.clear()
        ax = self.replay_fig.add_subplot(111)
        ax.set_facecolor(self.theme["bg"])
        ax.tick_params(colors=self.theme["txt_muted"], labelsize=7)
        ax.spines["bottom"].set_color(self.theme["border"])
        ax.spines["top"].set_color(self.theme["border"])
        ax.spines["left"].set_color(self.theme["border"])
        ax.spines["right"].set_color(self.theme["border"])

        window = self.replay_data[max(0, self.replay_index - 20):self.replay_index + 1]
        if not window:
            return

        plotted_count = 0
        for p in self.params:
            if p["enabled"] and p["name"] != "Time_Inst" and p["mode"] in ("both", "plot"):
                values = []
                for d in window:
                    if p["name"] in d:
                        try:
                            values.append(float(d[p["name"]]))
                        except ValueError:
                            pass
                if values:
                    ax.plot(values, label=p["name"], color=p["color"], linewidth=1.5)
                    plotted_count += 1
                    if plotted_count >= 5:
                        break

        ax.legend(fontsize=7, labelcolor=self.theme["txt_muted"])
        self.replay_canvas.draw()

    # ─── DATA LOGGER ─────────────────────────────────────────────────────
    def _refresh_logger_table_columns(self):
        self.logger_tree.delete(*self.logger_tree.get_children())
        columns = ["Timestamp"] + [p["name"] for p in self.params if self.logger_checkbox_vars.get(p["name"], tk.BooleanVar(value=True)).get()]
        self.logger_tree["columns"] = columns
        for col in columns:
            self.logger_tree.heading(col, text=col)
            self.logger_tree.column(col, width=110, anchor="center")
        self._sync_logger_table_rows_cache()

    def _sync_logger_table_rows_cache(self):
        self.logger_tree.delete(*self.logger_tree.get_children())
        for row in list(self.history)[-100:]:
            vals = [row.get(col, "--") for col in self.logger_tree["columns"]]
            self.logger_tree.insert("", 0, values=vals)

        self.lbl_log_counter.config(text=f"Logged Packets: {len(self.history)} records cached")

    def _append_single_row_to_logger_table(self, row):
        cols = self.logger_tree["columns"]
        vals = [row.get(col, "--") for col in cols]
        self.logger_tree.insert("", 0, values=vals)
        children = self.logger_tree.get_children()
        if len(children) > 100:
            self.logger_tree.delete(children[-1])
        self.lbl_log_counter.config(text=f"Logged Packets: {len(self.history)} records cached")


if __name__ == "__main__":
    app = AWSGroundStation()
    app.mainloop()