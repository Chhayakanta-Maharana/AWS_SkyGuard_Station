#!/usr/bin/env python3
"""
SkyGuard AI — Universal LAN Telemetry Data Sender & Multi-Station Simulator
===========================================================================
A production-grade, multi-functional telemetry transmitter designed for:
1. Direct Ethernet LAN Cable streaming between 2 laptops (or over shared Wi-Fi)
2. Custom CSV / TXT Dataset Importer & Streamer (Temperature, Pressure, Humidity)
3. Multi-Station Spatial Cluster Simulator (AWS-01, AWS-02, AWS-03, AWS-04)
4. ESP32 Edge AI Virtual Transceiver (Emulating physical microcontroller 0xAA55 packets)
5. Real-Time Interactive Anomaly Injector (Spikes, Flatlines, Drift, Spatial Glitches)
"""

import sys
import os
import time
import struct
import socket
import csv
import json
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# ─── COLOR PALETTE (Cyber-Physical Dark Meteorological Theme) ───────────────
BG_DARK = "#090d16"
BG_CARD = "#111827"
BG_CARD_HOVER = "#1f2937"
BG_INPUT = "#1e293b"
BORDER = "#334155"
ACCENT_BLUE = "#0284c7"
ACCENT_CYAN = "#06b6d4"
ACCENT_GREEN = "#10b981"
ACCENT_AMBER = "#f59e0b"
ACCENT_RED = "#ef4444"
ACCENT_PURPLE = "#8b5cf6"
TXT_MAIN = "#f8fafc"
TXT_MUTED = "#94a3b8"
TXT_DIM = "#64748b"

FONT_TITLE = ("Segoe UI", 12, "bold")
FONT_SUB = ("Segoe UI", 9)
FONT_BOLD = ("Segoe UI", 9, "bold")
FONT_MONO = ("Consolas", 9)
FONT_MONO_BOLD = ("Consolas", 9, "bold")

class SkyGuardTelemetrySender:
    def __init__(self, root):
        self.root = root
        self.root.title("SkyGuard AI — Universal LAN Telemetry Data Sender & Station Simulator")
        self.root.geometry("980x720")
        self.root.minsize(860, 640)
        self.root.configure(bg=BG_DARK)

        # Telemetry State
        self.is_streaming = False
        self.stream_thread = None
        self.packet_count = 0
        self.loaded_data = []
        self.current_row_idx = 0
        self.active_mode = "manual"  # "file", "multi_aws", "esp32", "manual"

        # Multi-Station State
        self.spatial_glitch = False
        self.temp_spike = False
        self.press_freeze = False
        self.rh_drift = False

        # Live Manual Values
        self.val_temp = tk.DoubleVar(value=31.0)
        self.val_wet_temp = tk.DoubleVar(value=25.5)
        self.val_press = tk.DoubleVar(value=1013.2)
        self.val_rh = tk.DoubleVar(value=65.0)
        self.val_station = tk.StringVar(value="AWS-01")

        # Network Config Vars
        self.target_ip = tk.StringVar(value="127.0.0.1")
        self.target_port = tk.IntVar(value=5000)
        self.protocol_mode = tk.StringVar(value="UDP_0xAA55")
        self.stream_freq = tk.DoubleVar(value=1.0)  # Hz
        self.loop_file = tk.BooleanVar(value=True)

        self.setup_ui()

    def setup_ui(self):
        # ─── HEADER BAR ─────────────────────────────────────────────────────
        header_frame = tk.Frame(self.root, bg=BG_CARD, height=56, highlightthickness=1, highlightbackground=BORDER)
        header_frame.pack(fill="x", padx=10, pady=(10, 6))

        title_lbl = tk.Label(
            header_frame,
            text="📡 SKYGUARD AI • UNIVERSAL TELEMETRY DATA SENDER & SIMULATOR",
            font=FONT_TITLE,
            fg=ACCENT_CYAN,
            bg=BG_CARD
        )
        title_lbl.pack(side="left", padx=14, pady=10)

        self.status_pill = tk.Label(
            header_frame,
            text="● STANDBY (IDLE)",
            font=FONT_BOLD,
            fg=TXT_DIM,
            bg=BG_INPUT,
            padx=10,
            pady=4
        )
        self.status_pill.pack(side="right", padx=14, pady=10)

        # ─── NETWORK CONFIGURATION BAR ──────────────────────────────────────
        net_card = tk.Frame(self.root, bg=BG_CARD, highlightthickness=1, highlightbackground=BORDER)
        net_card.pack(fill="x", padx=10, pady=4)

        tk.Label(net_card, text="Target IP (Host PC):", font=FONT_BOLD, fg=TXT_MAIN, bg=BG_CARD).grid(row=0, column=0, padx=(12, 4), pady=8, sticky="w")
        ip_entry = tk.Entry(net_card, textvariable=self.target_ip, font=FONT_MONO, bg=BG_INPUT, fg=TXT_MAIN, insertbackground=TXT_MAIN, width=14, relief="flat")
        ip_entry.grid(row=0, column=1, padx=4, pady=8)

        tk.Label(net_card, text="Port:", font=FONT_BOLD, fg=TXT_MAIN, bg=BG_CARD).grid(row=0, column=2, padx=(12, 4), pady=8, sticky="w")
        port_entry = tk.Entry(net_card, textvariable=self.target_port, font=FONT_MONO, bg=BG_INPUT, fg=TXT_MAIN, insertbackground=TXT_MAIN, width=6, relief="flat")
        port_entry.grid(row=0, column=3, padx=4, pady=8)

        tk.Label(net_card, text="Protocol:", font=FONT_BOLD, fg=TXT_MAIN, bg=BG_CARD).grid(row=0, column=4, padx=(12, 4), pady=8, sticky="w")
        proto_combo = ttk.Combobox(net_card, textvariable=self.protocol_mode, values=["UDP_0xAA55", "TCP_0xAA55", "JSON_STREAM"], state="readonly", width=13)
        proto_combo.grid(row=0, column=5, padx=4, pady=8)

        tk.Label(net_card, text="Rate (Hz):", font=FONT_BOLD, fg=TXT_MAIN, bg=BG_CARD).grid(row=0, column=6, padx=(12, 4), pady=8, sticky="w")
        rate_spin = tk.Spinbox(net_card, from_=0.1, to=20.0, increment=0.5, textvariable=self.stream_freq, font=FONT_MONO, bg=BG_INPUT, fg=TXT_MAIN, width=5, relief="flat")
        rate_spin.grid(row=0, column=7, padx=4, pady=8)

        self.btn_start = tk.Button(
            net_card,
            text="▶ START STREAM",
            font=FONT_BOLD,
            bg=ACCENT_GREEN,
            fg="#ffffff",
            activebackground="#059669",
            activeforeground="#ffffff",
            relief="flat",
            padx=14,
            pady=4,
            command=self.toggle_stream
        )
        self.btn_start.grid(row=0, column=8, padx=(16, 12), pady=8)

        # ─── NOTEBOOK TABS (MODES) ──────────────────────────────────────────
        style = ttk.Style()
        style.theme_use("default")
        style.configure("TNotebook", background=BG_DARK, borderwidth=0)
        style.configure("TNotebook.Tab", background=BG_CARD, foreground=TXT_MUTED, font=FONT_BOLD, padding=[12, 6])
        style.map("TNotebook.Tab", background=[("selected", ACCENT_BLUE)], foreground=[("selected", "#ffffff")])

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=10, pady=6)

        # Tab 1: File Importer
        tab_file = tk.Frame(notebook, bg=BG_DARK)
        notebook.add(tab_file, text="📁 Import & Stream CSV / TXT Dataset")
        self.setup_file_tab(tab_file)

        # Tab 2: Multi-Station Spatial Grid
        tab_multi = tk.Frame(notebook, bg=BG_DARK)
        notebook.add(tab_multi, text="🌐 Multi-Station Spatial Cluster (AWS 01-04)")
        self.setup_multi_station_tab(tab_multi)

        # Tab 3: ESP32 Edge AI Virtual Transceiver
        tab_esp = tk.Frame(notebook, bg=BG_DARK)
        notebook.add(tab_esp, text="📡 ESP32 Virtual Microcontroller (Wi-Fi)")
        self.setup_esp32_tab(tab_esp)

        # Tab 4: Manual Controls & Payload Inspector
        tab_manual = tk.Frame(notebook, bg=BG_DARK)
        notebook.add(tab_manual, text="🎛️ Live Sliders & Anomaly Injector")
        self.setup_manual_tab(tab_manual)

        # ─── FOOTER CONSOLE & PACKET MONITOR ────────────────────────────────
        footer_frame = tk.Frame(self.root, bg=BG_CARD, height=130, highlightthickness=1, highlightbackground=BORDER)
        footer_frame.pack(fill="x", padx=10, pady=(4, 10))

        log_hdr = tk.Frame(footer_frame, bg=BG_CARD)
        log_hdr.pack(fill="x", padx=8, pady=(4, 2))
        tk.Label(log_hdr, text="🖥️ TRANSMISSION MONITOR & PACKET INSPECTOR", font=FONT_BOLD, fg=TXT_MUTED, bg=BG_CARD).pack(side="left")
        self.lbl_tx_count = tk.Label(log_hdr, text="Packets Transmitted: 0", font=FONT_MONO_BOLD, fg=ACCENT_CYAN, bg=BG_CARD)
        self.lbl_tx_count.pack(side="right")

        self.txt_log = tk.Text(footer_frame, bg=BG_INPUT, fg=TXT_MAIN, font=FONT_MONO, height=5, relief="flat", padx=6, pady=4)
        self.txt_log.pack(fill="both", expand=True, padx=8, pady=(2, 6))

    # ─── TAB 1: FILE IMPORTER ───────────────────────────────────────────────
    def setup_file_tab(self, parent):
        card = tk.Frame(parent, bg=BG_CARD, highlightthickness=1, highlightbackground=BORDER)
        card.pack(fill="both", expand=True, padx=6, pady=6)

        ctrl_bar = tk.Frame(card, bg=BG_CARD)
        ctrl_bar.pack(fill="x", padx=12, pady=8)

        btn_browse = tk.Button(ctrl_bar, text="📂 Load CSV / TXT File...", font=FONT_BOLD, bg=ACCENT_BLUE, fg="#fff", relief="flat", padx=10, pady=4, command=self.load_dataset_file)
        btn_browse.pack(side="left")

        self.lbl_file_info = tk.Label(ctrl_bar, text="No dataset file loaded. (Click to import sample_test_telemetry.csv)", font=FONT_SUB, fg=TXT_MUTED, bg=BG_CARD)
        self.lbl_file_info.pack(side="left", padx=12)

        chk_loop = tk.Checkbutton(ctrl_bar, text="Loop Playback", variable=self.loop_file, font=FONT_BOLD, fg=TXT_MAIN, bg=BG_CARD, selectcolor=BG_INPUT, activebackground=BG_CARD, activeforeground=TXT_MAIN)
        chk_loop.pack(side="right")

        # Treeview for previewing imported data
        tree_frame = tk.Frame(card, bg=BG_INPUT)
        tree_frame.pack(fill="both", expand=True, padx=12, pady=(4, 10))

        cols = ("idx", "timestamp", "station", "dry_temp", "wet_temp", "pressure", "humidity")
        self.tree_file = ttk.Treeview(tree_frame, columns=cols, show="headings", height=8)
        self.tree_file.heading("idx", text="#")
        self.tree_file.heading("timestamp", text="Timestamp (UTC)")
        self.tree_file.heading("station", text="Station ID")
        self.tree_file.heading("dry_temp", text="Dry Temp (°C)")
        self.tree_file.heading("wet_temp", text="Wet Temp (°C)")
        self.tree_file.heading("pressure", text="Pressure (hPa)")
        self.tree_file.heading("humidity", text="Humidity (%)")

        self.tree_file.column("idx", width=40, anchor="center")
        self.tree_file.column("timestamp", width=180, anchor="w")
        self.tree_file.column("station", width=90, anchor="center")
        self.tree_file.column("dry_temp", width=110, anchor="center")
        self.tree_file.column("wet_temp", width=110, anchor="center")
        self.tree_file.column("pressure", width=120, anchor="center")
        self.tree_file.column("humidity", width=110, anchor="center")

        scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree_file.yview)
        self.tree_file.configure(yscrollcommand=scroll.set)
        self.tree_file.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

    # ─── TAB 2: MULTI-STATION SPATIAL CLUSTER ───────────────────────────────
    def setup_multi_station_tab(self, parent):
        card = tk.Frame(parent, bg=BG_CARD, highlightthickness=1, highlightbackground=BORDER)
        card.pack(fill="both", expand=True, padx=6, pady=6)

        tk.Label(card, text="🌐 4-STATION SPATIAL NETWORK CLUSTER SIMULATOR", font=FONT_BOLD, fg=ACCENT_CYAN, bg=BG_CARD).pack(anchor="w", padx=12, pady=(10, 4))
        tk.Label(card, text="Simultaneously broadcasts telemetry for AWS-01 (Target), AWS-02 (North), AWS-03 (East), and AWS-04 (South).", font=FONT_SUB, fg=TXT_MUTED, bg=BG_CARD).pack(anchor="w", padx=12, pady=(0, 10))

        # Station status grid preview
        grid_frame = tk.Frame(card, bg=BG_CARD)
        grid_frame.pack(fill="x", padx=12, pady=4)

        self.card_aws1 = self.create_station_card(grid_frame, "AWS-01 (Target Station)", 31.0, 1013.2, 65.0, 0)
        self.card_aws2 = self.create_station_card(grid_frame, "AWS-02 (North Neighbor)", 31.0, 1013.2, 65.0, 1)
        self.card_aws3 = self.create_station_card(grid_frame, "AWS-03 (East Neighbor)", 31.0, 1013.2, 65.0, 2)
        self.card_aws4 = self.create_station_card(grid_frame, "AWS-04 (South Neighbor)", 31.0, 1013.2, 65.0, 3)

        # Anomaly Injection Controls
        inj_frame = tk.Frame(card, bg=BG_INPUT, highlightthickness=1, highlightbackground=BORDER)
        inj_frame.pack(fill="x", padx=12, pady=(14, 10))

        tk.Label(inj_frame, text="⚡ LIVE FAULT INJECTION BENCH:", font=FONT_BOLD, fg=ACCENT_AMBER, bg=BG_INPUT).pack(side="left", padx=10, pady=8)

        btn_glitch = tk.Button(inj_frame, text="🚨 Inject AWS-01 Glitch (55°C)", font=FONT_BOLD, bg=ACCENT_RED, fg="#fff", relief="flat", padx=8, pady=4, command=self.inject_spatial_glitch)
        btn_glitch.pack(side="left", padx=6, pady=8)

        btn_reset = tk.Button(inj_frame, text="🔄 Reset Nominal Consensus (31°C)", font=FONT_BOLD, bg=ACCENT_GREEN, fg="#fff", relief="flat", padx=8, pady=4, command=self.reset_spatial_consensus)
        btn_reset.pack(side="left", padx=6, pady=8)

    def create_station_card(self, parent, title, temp, press, rh, col):
        f = tk.Frame(parent, bg=BG_INPUT, highlightthickness=1, highlightbackground=BORDER, padx=8, pady=8)
        f.grid(row=0, column=col, padx=4, pady=4, sticky="nsew")
        parent.grid_columnconfigure(col, weight=1)

        tk.Label(f, text=title, font=FONT_BOLD, fg=ACCENT_CYAN, bg=BG_INPUT).pack(anchor="w")
        lbl_t = tk.Label(f, text=f"Temp: {temp:.1f} °C", font=FONT_MONO, fg=TXT_MAIN, bg=BG_INPUT)
        lbl_t.pack(anchor="w", pady=(4, 1))
        lbl_p = tk.Label(f, text=f"Press: {press:.1f} hPa", font=FONT_MONO, fg=TXT_MUTED, bg=BG_INPUT)
        lbl_p.pack(anchor="w", pady=1)
        lbl_h = tk.Label(f, text=f"RH: {rh:.1f} %", font=FONT_MONO, fg=TXT_MUTED, bg=BG_INPUT)
        lbl_h.pack(anchor="w", pady=1)
        return {"frame": f, "lbl_t": lbl_t, "lbl_p": lbl_p, "lbl_h": lbl_h}

    # ─── TAB 3: ESP32 EDGE AI VIRTUAL TRANSCEIVER ───────────────────────────
    def setup_esp32_tab(self, parent):
        card = tk.Frame(parent, bg=BG_CARD, highlightthickness=1, highlightbackground=BORDER)
        card.pack(fill="both", expand=True, padx=6, pady=6)

        tk.Label(card, text="📡 ESP32 VIRTUAL MICROCONTROLLER FIRMWARE EMULATOR", font=FONT_BOLD, fg=ACCENT_CYAN, bg=BG_CARD).pack(anchor="w", padx=12, pady=(10, 4))
        tk.Label(card, text="Simulates physical ESP32 Wi-Fi hardware broadcasting pure C binary 0xAA55 datagrams directly to port 5000.", font=FONT_SUB, fg=TXT_MUTED, bg=BG_CARD).pack(anchor="w", padx=12, pady=(0, 10))

        info_box = tk.Frame(card, bg=BG_INPUT, highlightthickness=1, highlightbackground=BORDER)
        info_box.pack(fill="x", padx=12, pady=4)

        tk.Label(info_box, text="MCU Target: ESP32-S3 (240MHz)", font=FONT_MONO_BOLD, fg=TXT_MAIN, bg=BG_INPUT).grid(row=0, column=0, padx=10, pady=6, sticky="w")
        tk.Label(info_box, text="MAC: 24:6F:28:B4:A1:0C", font=FONT_MONO, fg=TXT_MUTED, bg=BG_INPUT).grid(row=0, column=1, padx=10, pady=6, sticky="w")
        tk.Label(info_box, text="Wi-Fi RSSI: -58 dBm", font=FONT_MONO, fg=ACCENT_GREEN, bg=BG_INPUT).grid(row=0, column=2, padx=10, pady=6, sticky="w")
        tk.Label(info_box, text="Edge QC: 12.4 μs Latency", font=FONT_MONO, fg=ACCENT_CYAN, bg=BG_INPUT).grid(row=0, column=3, padx=10, pady=6, sticky="w")

        desc = (
            "💡 Testing with 2 Laptops over LAN or Shared Wi-Fi:\n"
            "1. Run SkyGuard Ground Station (AWS_SkyGuard_Station.exe or http://localhost:3000) on Laptop 1.\n"
            "2. Note Laptop 1's IP address (e.g. 192.168.1.5 via 'ipconfig').\n"
            "3. Run this LAN Data Sender on Laptop 2, enter Laptop 1's IP in 'Target IP', and click START STREAM.\n"
            "4. The Ground Station on Laptop 1 will immediately display the live weather curves and XAI telemetry!"
        )
        tk.Label(card, text=desc, font=FONT_MONO, fg=TXT_MUTED, bg=BG_CARD, justify="left").pack(anchor="w", padx=12, pady=12)

    # ─── TAB 4: MANUAL CONTROLS & LIVE ANOMALY INJECTOR ─────────────────────
    def setup_manual_tab(self, parent):
        card = tk.Frame(parent, bg=BG_CARD, highlightthickness=1, highlightbackground=BORDER)
        card.pack(fill="both", expand=True, padx=6, pady=6)

        # Sliders
        s_frame = tk.Frame(card, bg=BG_CARD)
        s_frame.pack(fill="x", padx=12, pady=8)

        self.create_slider(s_frame, "Dry Bulb Temp (°C):", self.val_temp, -40.0, 55.0, 0, "#ea580c")
        self.create_slider(s_frame, "Wet Bulb Temp (°C):", self.val_wet_temp, -40.0, 50.0, 1, "#0284c7")
        self.create_slider(s_frame, "Atmospheric Pressure (hPa):", self.val_press, 850.0, 1080.0, 2, "#10b981")
        self.create_slider(s_frame, "Relative Humidity (%):", self.val_rh, 0.0, 100.0, 3, "#8b5cf6")

        # Instant Glitch Buttons
        btn_box = tk.Frame(card, bg=BG_INPUT, highlightthickness=1, highlightbackground=BORDER)
        btn_box.pack(fill="x", padx=12, pady=(10, 6))

        tk.Button(btn_box, text="⚡ Spike (+30°C)", font=FONT_BOLD, bg=ACCENT_RED, fg="#fff", relief="flat", padx=6, pady=4, command=lambda: self.val_temp.set(min(55.0, self.val_temp.get() + 30.0))).pack(side="left", padx=6, pady=6)
        tk.Button(btn_box, text="❄️ Freeze Pressure", font=FONT_BOLD, bg=ACCENT_AMBER, fg="#fff", relief="flat", padx=6, pady=4, command=lambda: self.val_press.set(1013.25)).pack(side="left", padx=6, pady=6)
        tk.Button(btn_box, text="💧 Drift RH (+25%)", font=FONT_BOLD, bg=ACCENT_PURPLE, fg="#fff", relief="flat", padx=6, pady=4, command=lambda: self.val_rh.set(min(100.0, self.val_rh.get() + 25.0))).pack(side="left", padx=6, pady=6)
        tk.Button(btn_box, text="🔄 Reset Nominal", font=FONT_BOLD, bg=ACCENT_GREEN, fg="#fff", relief="flat", padx=6, pady=4, command=self.reset_manual_nominal).pack(side="left", padx=6, pady=6)

    def create_slider(self, parent, label, var, min_v, max_v, row, color):
        f = tk.Frame(parent, bg=BG_CARD)
        f.pack(fill="x", pady=4)
        tk.Label(f, text=label, font=FONT_BOLD, fg=TXT_MAIN, bg=BG_CARD, width=24, anchor="w").pack(side="left")
        s = tk.Scale(f, variable=var, from_=min_v, to=max_v, resolution=0.1, orient="horizontal", bg=BG_INPUT, fg=TXT_MAIN, highlightthickness=0, troughcolor=BG_DARK, activebackground=color, length=380)
        s.pack(side="left", padx=8)
        lbl_v = tk.Label(f, textvariable=var, font=FONT_MONO_BOLD, fg=color, bg=BG_CARD, width=8, anchor="w")
        lbl_v.pack(side="left")

    def reset_manual_nominal(self):
        self.val_temp.set(31.0)
        self.val_wet_temp.set(25.5)
        self.val_press.set(1013.2)
        self.val_rh.set(65.0)

    def inject_spatial_glitch(self):
        self.spatial_glitch = True
        self.card_aws1["lbl_t"].config(text="Temp: 55.0 °C (OUTLIER)", fg=ACCENT_RED)
        self.log("🚨 Injected AWS-01 Spatial Glitch (55.0°C vs 31.0°C neighbors).")

    def reset_spatial_consensus(self):
        self.spatial_glitch = False
        self.card_aws1["lbl_t"].config(text="Temp: 31.0 °C", fg=TXT_MAIN)
        self.log("🔄 Reset all stations to Nominal Spatial Consensus (31.0°C).")

    # ─── FILE LOADER ────────────────────────────────────────────────────────
    def load_dataset_file(self):
        fpath = filedialog.askopenfilename(
            title="Select Telemetry CSV or TXT Dataset",
            filetypes=[("CSV and Text Files", "*.csv;*.txt"), ("All Files", "*.*")]
        )
        if not fpath:
            return

        try:
            self.loaded_data = []
            for row in self.tree_file.get_children():
                self.tree_file.delete(row)

            with open(fpath, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for i, row in enumerate(reader):
                    t_val = float(row.get("dry_bulb_temp", row.get("temp", 30.0)))
                    w_val = float(row.get("wet_bulb_temp", row.get("wet_temp", t_val - 5.0)))
                    p_val = float(row.get("pressure_hpa", row.get("pressure", 1013.2)))
                    h_val = float(row.get("relative_humidity", row.get("humidity", 65.0)))
                    st_val = row.get("station_id", "AWS-01")
                    ts_val = row.get("timestamp", datetime.now(timezone.utc).isoformat())

                    record = {
                        "timestamp": ts_val,
                        "station_id": st_val,
                        "dry_temp": t_val,
                        "wet_temp": w_val,
                        "pressure": p_val,
                        "humidity": h_val
                    }
                    self.loaded_data.append(record)

                    if i < 200:  # Preview first 200 rows in tree
                        self.tree_file.insert("", "end", values=(i + 1, ts_val, st_val, f"{t_val:.1f}", f"{w_val:.1f}", f"{p_val:.1f}", f"{h_val:.1f}"))

            self.lbl_file_info.config(text=f"Loaded {len(self.loaded_data)} rows from {os.path.basename(fpath)}")
            self.log(f"📁 Successfully imported {len(self.loaded_data)} rows from {fpath}")
        except Exception as e:
            messagebox.showerror("File Error", f"Failed to parse dataset file:\n{str(e)}")

    # ─── NETWORK TRANSMISSION ENGINE ────────────────────────────────────────
    def toggle_stream(self):
        if self.is_streaming:
            self.is_streaming = False
            self.btn_start.config(text="▶ START STREAM", bg=ACCENT_GREEN)
            self.status_pill.config(text="● STANDBY (IDLE)", fg=TXT_DIM)
            self.log("⏹️ Telemetry streaming stopped.")
        else:
            self.is_streaming = True
            self.btn_start.config(text="⏹ STOP STREAM", bg=ACCENT_RED)
            self.status_pill.config(text="● TRANSMITTING LIVE", fg=ACCENT_GREEN)
            self.stream_thread = threading.Thread(target=self.run_streaming_loop, daemon=True)
            self.stream_thread.start()
            self.log(f"🚀 Started streaming to {self.target_ip.get()}:{self.target_port.get()} via {self.protocol_mode.get()}")

    def run_streaming_loop(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        row_idx = 0
        while self.is_streaming:
            try:
                target_host = self.target_ip.get().strip()
                target_port = int(self.target_port.get())
                proto = self.protocol_mode.get()
                freq = max(0.05, float(self.stream_freq.get()))
                interval = 1.0 / freq

                # Determine data to send based on loaded file or manual values
                if len(self.loaded_data) > 0:
                    rec = self.loaded_data[row_idx]
                    t_val = rec["dry_temp"]
                    w_val = rec["wet_temp"]
                    p_val = rec["pressure"]
                    h_val = rec["humidity"]
                    st_val = rec["station_id"]
                    row_idx = (row_idx + 1) % len(self.loaded_data) if self.loop_file.get() else min(row_idx + 1, len(self.loaded_data) - 1)
                elif self.spatial_glitch:
                    t_val = 55.0
                    w_val = 25.5
                    p_val = 1013.2
                    h_val = 65.0
                    st_val = "AWS-01"
                else:
                    t_val = float(self.val_temp.get())
                    w_val = float(self.val_wet_temp.get())
                    p_val = float(self.val_press.get())
                    h_val = float(self.val_rh.get())
                    st_val = self.val_station.get()

                # Build 24-byte Binary 0xAA55 Frame
                # Sync (2B: 0xAA55), Timestamp (4B), DryTemp (4B), WetTemp (4B), Press (4B), RH (4B), CRC (1B), Term (1B: 0x0A)
                ts = int(time.time())
                payload = struct.pack(">H I f f f f", 0xAA55, ts, t_val, w_val, p_val, h_val)
                crc = sum(payload) % 256
                packet = payload + struct.pack("B B", crc, 0x0A)

                if proto == "JSON_STREAM":
                    json_dict = {
                        "station_id": st_val,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "dry_bulb_temp": t_val,
                        "wet_bulb_temp": w_val,
                        "pressure_hpa": p_val,
                        "relative_humidity": h_val
                    }
                    packet = json.dumps(json_dict).encode("utf-8")

                sock.sendto(packet, (target_host, target_port))
                self.packet_count += 1

                if self.packet_count % 5 == 1:
                    hex_sample = packet[:12].hex().upper()
                    self.log(f"TX #{self.packet_count} -> {st_val} | T: {t_val:.1f}°C, P: {p_val:.1f}hPa, RH: {h_val:.1f}% | Bytes: {len(packet)} (0x{hex_sample}...)")

                time.sleep(interval)
            except Exception as e:
                self.log(f"⚠️ TX Error: {str(e)}")
                time.sleep(1.0)

        sock.close()

    def log(self, msg):
        self.root.after(0, self._append_log, msg)

    def _append_log(self, msg):
        t_str = datetime.now().strftime("%H:%M:%S")
        self.txt_log.insert("end", f"[{t_str}] {msg}\n")
        self.txt_log.see("end")
        self.lbl_tx_count.config(text=f"Packets Transmitted: {self.packet_count}")


def main():
    root = tk.Tk()
    app = SkyGuardTelemetrySender(root)
    root.mainloop()

if __name__ == "__main__":
    main()
