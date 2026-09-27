#!/usr/bin/env python3
"""
SkyGuard AI — Universal LAN Telemetry Data Sender & Ground Testbench
====================================================================
Defense-Grade Telemetry Transmitter and Sensor Emulation Suite
Designed for DRDO / IMD Automated Weather Station Demonstrations.

Features:
- Real-time CSV / TXT Streaming with Synchronous Row-by-Row Visual Tracking
- High-Visibility HUD Cards (Live Temp, Pressure, Humidity, Frame Sequence)
- Direct Ethernet LAN Broadcast (0xAA55 Big-Endian Binary / TCP / JSON)
- Interactive Timeline Scrubber & Anomaly Jump Indexer
- Multi-Station Spatial Network Simulator (AWS-01 to AWS-04)
- Live Packet Hex Inspector & Network Diagnostics
"""

import sys
import os
import time
import struct
import socket
import csv
import json
import threading
from datetime import datetime, timezone
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# Enable Windows High-DPI scaling for ultra-crisp fonts
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

# ─── DEFENSE & AEROSPACE COLOR PALETTE ──────────────────────────────────────
BG_MAIN       = "#0b111e"   # Deep Navy Space Base
BG_PANEL      = "#111a2d"   # Raised Panel Background
BG_CARD       = "#162238"   # Elevated Card Background
BG_INPUT      = "#0e1626"   # Recessed Input Background
BG_HOVER      = "#1e2e4a"   # Hover State

BORDER_SUBTLE = "#1e2c45"   # Inactive Border
BORDER_ACTIVE = "#38bdf8"   # Focused/Active Border
BORDER_CARD   = "#223352"   # Card Perimeter

ACCENT_CYAN   = "#38bdf8"   # High-Tech Primary
ACCENT_GREEN  = "#22c55e"   # Operational / Nominal
ACCENT_AMBER  = "#f59e0b"   # Warning / Drift
ACCENT_RED    = "#f43f5e"   # Anomaly / Fault
ACCENT_BLUE   = "#3b82f6"   # Action Button
ACCENT_PURPLE = "#a855f7"   # Secondary Data

TXT_TITLE     = "#ffffff"   # Header Text
TXT_MAIN      = "#e2e8f0"   # Body Text
TXT_MUTED     = "#94a3b8"   # Secondary Labels
TXT_DIM       = "#64748b"   # Low-contrast metadata

# Typography Presets
FONT_HEADING   = ("Segoe UI", 11, "bold")
FONT_TITLE     = ("Segoe UI", 10, "bold")
FONT_LABEL     = ("Segoe UI", 8, "bold")
FONT_BODY      = ("Segoe UI", 9)
FONT_BOLD      = ("Segoe UI", 9, "bold")
FONT_SUB       = ("Segoe UI", 8)
FONT_MONO      = ("Consolas", 9)
FONT_MONO_BOLD = ("Consolas", 9, "bold")
FONT_MONO_LG   = ("Consolas", 14, "bold")
FONT_MONO_XL   = ("Consolas", 18, "bold")


class SkyGuardTelemetryTransmitter:
    def __init__(self, root):
        self.root = root
        self.root.title("SkyGuard AI — Universal Ground Telemetry Transmitter (LAN/UDP)")
        self.root.geometry("1060x760")
        self.root.minsize(940, 680)
        self.root.configure(bg=BG_MAIN)

        # Transmission Engine State
        self.is_streaming = False
        self.stream_thread = None
        self.packet_count = 0
        self.loaded_data = []
        self.current_row_idx = 0
        self.start_time = None
        self.auto_scroll_log = True

        # Fault Injection Flags
        self.spatial_glitch = False
        self.temp_spike = False
        self.press_freeze = False
        self.rh_drift = False

        # Live Manual Form Variables
        self.val_temp = tk.DoubleVar(value=31.0)
        self.val_wet_temp = tk.DoubleVar(value=25.5)
        self.val_press = tk.DoubleVar(value=1013.2)
        self.val_rh = tk.DoubleVar(value=65.0)
        self.val_station = tk.StringVar(value="AWS-01")

        # Network Config Variables
        self.target_ip = tk.StringVar(value="255.255.255.255")
        self.target_port = tk.IntVar(value=5000)
        self.protocol_mode = tk.StringVar(value="UDP_0xAA55 (Binary 24B)")
        self.stream_freq = tk.DoubleVar(value=1.0)
        self.loop_file = tk.BooleanVar(value=True)

        self.apply_ttk_styles()
        self.setup_ui()
        self.auto_load_default_dataset()

        # 1-second UI Heartbeat timer for elapsed time
        self.update_elapsed_timer()

    def apply_ttk_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(".", background=BG_PANEL, foreground=TXT_MAIN, font=FONT_BODY)
        
        # Notebook / Tabs
        style.configure("TNotebook", background=BG_MAIN, borderwidth=0)
        style.configure("TNotebook.Tab", background=BG_PANEL, foreground=TXT_MUTED, font=FONT_BOLD, padding=[16, 7], borderwidth=0)
        style.map("TNotebook.Tab",
                  background=[("selected", BG_CARD)],
                  foreground=[("selected", ACCENT_CYAN)],
                  bordercolor=[("selected", BORDER_ACTIVE)])

        # Treeview (Dataset Viewer)
        style.configure("Treeview",
                        background=BG_INPUT,
                        foreground=TXT_MAIN,
                        fieldbackground=BG_INPUT,
                        rowheight=24,
                        font=FONT_MONO,
                        borderwidth=0)
        style.configure("Treeview.Heading",
                        background=BG_CARD,
                        foreground=ACCENT_CYAN,
                        font=FONT_LABEL,
                        padding=[6, 4],
                        borderwidth=1,
                        relief="flat")
        style.map("Treeview",
                  background=[("selected", ACCENT_BLUE)],
                  foreground=[("selected", "#ffffff")])

        # Progressbar
        style.configure("Horizontal.TProgressbar",
                        troughcolor=BG_INPUT,
                        background=ACCENT_CYAN,
                        borderwidth=0,
                        thickness=6)

    def setup_ui(self):
        # ─── 1. TOP TITLE & COCKPIT STATUS BAR ──────────────────────────────
        top_bar = tk.Frame(self.root, bg=BG_PANEL, highlightthickness=1, highlightbackground=BORDER_SUBTLE)
        top_bar.pack(fill="x", padx=12, pady=(10, 6))

        # Brand / Title Block
        brand_frame = tk.Frame(top_bar, bg=BG_PANEL)
        brand_frame.pack(side="left", padx=14, pady=10)

        lbl_app = tk.Label(brand_frame, text="⚡ SKYGUARD-TX", font=FONT_HEADING, fg=ACCENT_CYAN, bg=BG_PANEL)
        lbl_app.pack(side="left")

        lbl_sub = tk.Label(brand_frame, text=" | Universal Ground Telemetry Transmitter & Sensor Testbench", font=FONT_BODY, fg=TXT_MUTED, bg=BG_PANEL)
        lbl_sub.pack(side="left", padx=(4, 0))

        # Right-side Real-Time Telemetry Badges
        cockpit_right = tk.Frame(top_bar, bg=BG_PANEL)
        cockpit_right.pack(side="right", padx=14, pady=8)

        # Elapsed Timer Badge
        self.lbl_elapsed = tk.Label(cockpit_right, text="⏱ 00:00:00", font=FONT_MONO, fg=TXT_MUTED, bg=BG_INPUT, padx=8, pady=3)
        self.lbl_elapsed.pack(side="left", padx=4)

        # TX Counter Badge
        self.lbl_tx_counter = tk.Label(cockpit_right, text="TX PKTS: 0", font=FONT_MONO_BOLD, fg=ACCENT_CYAN, bg=BG_INPUT, padx=8, pady=3)
        self.lbl_tx_counter.pack(side="left", padx=4)

        # Live Status Pill
        self.status_pill = tk.Label(cockpit_right, text="● STANDBY", font=FONT_BOLD, fg=TXT_DIM, bg=BG_INPUT, padx=10, pady=3)
        self.status_pill.pack(side="left", padx=(4, 0))

        # ─── 2. NETWORK INTERFACE & TRANSMISSION CONTROL BAR ────────────────
        net_bar = tk.Frame(self.root, bg=BG_CARD, highlightthickness=1, highlightbackground=BORDER_CARD)
        net_bar.pack(fill="x", padx=12, pady=(0, 6))

        # Row 1: Network Form Fields
        f_row = tk.Frame(net_bar, bg=BG_CARD)
        f_row.pack(fill="x", padx=14, pady=8)

        # Target Host IP
        tk.Label(f_row, text="TARGET HOST IP:", font=FONT_LABEL, fg=TXT_MUTED, bg=BG_CARD).pack(side="left", padx=(0, 4))
        self.entry_ip = tk.Entry(f_row, textvariable=self.target_ip, font=FONT_MONO_BOLD, bg=BG_INPUT, fg=TXT_MAIN, insertbackground=TXT_MAIN, width=16, relief="flat", highlightthickness=1, highlightbackground=BORDER_SUBTLE)
        self.entry_ip.pack(side="left", padx=2)

        # Quick Preset Buttons
        btn_bcast = tk.Button(f_row, text="Broadcast", font=("Segoe UI", 8, "bold"), bg=ACCENT_BLUE, fg="#ffffff", activebackground="#2563eb", activeforeground="#ffffff", relief="flat", padx=6, pady=2, command=lambda: self.target_ip.set("255.255.255.255"))
        btn_bcast.pack(side="left", padx=2)

        btn_local = tk.Button(f_row, text="Localhost", font=("Segoe UI", 8), bg=BG_INPUT, fg=TXT_MUTED, activebackground=BG_HOVER, activeforeground=TXT_MAIN, relief="flat", padx=6, pady=2, command=lambda: self.target_ip.set("127.0.0.1"))
        btn_local.pack(side="left", padx=2)

        btn_detect = tk.Button(f_row, text="🔍 My Subnet", font=("Segoe UI", 8), bg=BG_INPUT, fg=TXT_MUTED, activebackground=BG_HOVER, activeforeground=TXT_MAIN, relief="flat", padx=6, pady=2, command=self.detect_local_ip)
        btn_detect.pack(side="left", padx=(2, 12))

        # Port
        tk.Label(f_row, text="PORT:", font=FONT_LABEL, fg=TXT_MUTED, bg=BG_CARD).pack(side="left", padx=(4, 4))
        entry_port = tk.Entry(f_row, textvariable=self.target_port, font=FONT_MONO, bg=BG_INPUT, fg=TXT_MAIN, insertbackground=TXT_MAIN, width=6, relief="flat", highlightthickness=1, highlightbackground=BORDER_SUBTLE)
        entry_port.pack(side="left", padx=(0, 12))

        # Protocol
        tk.Label(f_row, text="PROTOCOL:", font=FONT_LABEL, fg=TXT_MUTED, bg=BG_CARD).pack(side="left", padx=(4, 4))
        combo_proto = ttk.Combobox(f_row, textvariable=self.protocol_mode, values=["UDP_0xAA55 (Binary 24B)", "JSON_STREAM", "TCP_0xAA55"], state="readonly", width=22)
        combo_proto.pack(side="left", padx=(0, 12))

        # Rate
        tk.Label(f_row, text="RATE (Hz):", font=FONT_LABEL, fg=TXT_MUTED, bg=BG_CARD).pack(side="left", padx=(4, 4))
        spin_rate = tk.Spinbox(f_row, from_=0.1, to=20.0, increment=0.5, textvariable=self.stream_freq, font=FONT_MONO, bg=BG_INPUT, fg=TXT_MAIN, width=4, relief="flat", highlightthickness=1, highlightbackground=BORDER_SUBTLE)
        spin_rate.pack(side="left", padx=(0, 14))

        # Master Start/Stop Button
        self.btn_toggle = tk.Button(
            f_row,
            text="▶  START TRANSMISSION",
            font=("Segoe UI", 10, "bold"),
            bg=ACCENT_GREEN,
            fg="#ffffff",
            activebackground="#16a34a",
            activeforeground="#ffffff",
            relief="flat",
            padx=16,
            pady=4,
            cursor="hand2",
            command=self.toggle_transmission
        )
        self.btn_toggle.pack(side="right", padx=(8, 0))

        # ─── 3. TABBED OPERATIONS WORKBENCH ─────────────────────────────────
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=12, pady=(0, 6))

        # Tab 1: CSV / Dataset Real-Time Streamer
        self.tab_file = tk.Frame(self.notebook, bg=BG_PANEL)
        self.notebook.add(self.tab_file, text=" 📁 Real-Time CSV Telemetry Streamer ")
        self.setup_file_streamer_tab(self.tab_file)

        # Tab 2: Multi-Station Spatial Cluster
        self.tab_multi = tk.Frame(self.notebook, bg=BG_PANEL)
        self.notebook.add(self.tab_multi, text=" 🌐 Multi-Station Spatial Grid ")
        self.setup_multi_station_tab(self.tab_multi)

        # Tab 3: Interactive Sliders & Anomaly Lab
        self.tab_manual = tk.Frame(self.notebook, bg=BG_PANEL)
        self.notebook.add(self.tab_manual, text=" 🎛️ Live Sliders & Manual Glitch Bench ")
        self.setup_manual_tab(self.tab_manual)

        # Tab 4: 2-Laptop Setup Guide & Diagnostics
        self.tab_guide = tk.Frame(self.notebook, bg=BG_PANEL)
        self.notebook.add(self.tab_guide, text=" 📡 2-Laptop LAN Setup Guide ")
        self.setup_guide_tab(self.tab_guide)

        # ─── 4. BOTTOM TRANSMISSION TERMINAL & HEX INSPECTOR ────────────────
        bot_frame = tk.Frame(self.root, bg=BG_PANEL, height=135, highlightthickness=1, highlightbackground=BORDER_SUBTLE)
        bot_frame.pack(fill="x", padx=12, pady=(0, 10))

        bot_header = tk.Frame(bot_frame, bg=BG_PANEL)
        bot_header.pack(fill="x", padx=10, pady=(4, 2))

        tk.Label(bot_header, text="🖥️ LIVE TRANSMISSION BUS & PACKET HEX INSPECTOR", font=FONT_LABEL, fg=TXT_MUTED, bg=BG_PANEL).pack(side="left")
        
        # Terminal controls
        btn_clr = tk.Button(bot_header, text="Clear Log", font=("Segoe UI", 7), bg=BG_INPUT, fg=TXT_MUTED, relief="flat", padx=6, pady=1, command=self.clear_log)
        btn_clr.pack(side="right", padx=2)

        self.chk_autoscroll = tk.Checkbutton(bot_header, text="Auto-Scroll", font=("Segoe UI", 7), fg=TXT_MUTED, bg=BG_PANEL, selectcolor=BG_INPUT, activebackground=BG_PANEL, activeforeground=TXT_MAIN, command=self.toggle_autoscroll)
        self.chk_autoscroll.select()
        self.chk_autoscroll.pack(side="right", padx=6)

        # Terminal text window
        self.txt_terminal = tk.Text(bot_frame, bg=BG_INPUT, fg=TXT_MAIN, font=FONT_MONO, height=5, relief="flat", padx=8, pady=4, highlightthickness=0)
        self.txt_terminal.pack(fill="both", expand=True, padx=10, pady=(0, 6))

        # Tag configurations for color-coded terminal messages
        self.txt_terminal.tag_config("tx_ok", foreground=ACCENT_GREEN)
        self.txt_terminal.tag_config("tx_anomaly", foreground=ACCENT_RED, font=FONT_MONO_BOLD)
        self.txt_terminal.tag_config("tx_info", foreground=ACCENT_CYAN)
        self.txt_terminal.tag_config("tx_warn", foreground=ACCENT_AMBER)

    # ────────────────────────────────────────────────────────────────────────
    # TAB 1: REAL-TIME CSV TELEMETRY STREAMER WITH LIVE HUD
    # ────────────────────────────────────────────────────────────────────────
    def setup_file_streamer_tab(self, parent):
        # 1. Dataset Toolbar
        toolbar = tk.Frame(parent, bg=BG_PANEL)
        toolbar.pack(fill="x", padx=12, pady=6)

        btn_load = tk.Button(toolbar, text="📂 Load Custom CSV / TXT...", font=FONT_BOLD, bg=ACCENT_BLUE, fg="#ffffff", relief="flat", padx=10, pady=4, cursor="hand2", command=self.load_dataset_dialog)
        btn_load.pack(side="left")

        btn_default = tk.Button(toolbar, text="⚡ Load 1000-Sample Anomaly Dataset", font=FONT_BOLD, bg=BG_CARD, fg=ACCENT_CYAN, relief="flat", padx=10, pady=4, cursor="hand2", command=self.auto_load_default_dataset)
        btn_default.pack(side="left", padx=8)

        self.lbl_file_status = tk.Label(toolbar, text="No dataset active.", font=FONT_BODY, fg=TXT_MUTED, bg=BG_PANEL)
        self.lbl_file_status.pack(side="left", padx=10)

        chk_loop = tk.Checkbutton(toolbar, text="🔁 Continuous Loop Playback", variable=self.loop_file, font=FONT_BOLD, fg=TXT_MAIN, bg=BG_PANEL, selectcolor=BG_INPUT, activebackground=BG_PANEL, activeforeground=TXT_MAIN)
        chk_loop.pack(side="right")

        # 2. Real-Time HUD Display Card for Currently Transmitting Packet
        hud_card = tk.Frame(parent, bg=BG_CARD, highlightthickness=1, highlightbackground=BORDER_CARD)
        hud_card.pack(fill="x", padx=12, pady=(2, 6))

        hud_title_row = tk.Frame(hud_card, bg=BG_CARD)
        hud_title_row.pack(fill="x", padx=12, pady=(6, 2))

        tk.Label(hud_title_row, text="CURRENT TRANSMITTED TELEMETRY FRAME (REAL-TIME HUD)", font=FONT_LABEL, fg=TXT_MUTED, bg=BG_CARD).pack(side="left")
        
        self.lbl_anomaly_badge = tk.Label(hud_title_row, text="● NOMINAL BASELINE", font=FONT_LABEL, fg=ACCENT_GREEN, bg=BG_INPUT, padx=8, pady=2)
        self.lbl_anomaly_badge.pack(side="right")

        # 5 Large Telemetry Meters in a Single Row
        meters_grid = tk.Frame(hud_card, bg=BG_CARD)
        meters_grid.pack(fill="x", padx=8, pady=(0, 6))

        for col in range(5):
            meters_grid.columnconfigure(col, weight=1)

        # Meter 1: Dry Bulb Temp
        self.meter_temp = self.create_hud_meter(meters_grid, 0, "DRY BULB TEMP", "-- °C", ACCENT_RED)
        # Meter 2: Wet Bulb Temp
        self.meter_wet = self.create_hud_meter(meters_grid, 1, "WET BULB TEMP", "-- °C", ACCENT_AMBER)
        # Meter 3: Rel. Humidity
        self.meter_rh = self.create_hud_meter(meters_grid, 2, "REL. HUMIDITY", "-- %", ACCENT_PURPLE)
        # Meter 4: Pressure (hPa)
        self.meter_press = self.create_hud_meter(meters_grid, 3, "BAROMETRIC PRESSURE", "-- hPa", ACCENT_CYAN)
        # Meter 5: Station & Sequence
        self.meter_seq = self.create_hud_meter(meters_grid, 4, "STREAM PROGRESS", "Row 0 / 0", ACCENT_GREEN)

        # Progress Bar & Timeline Scrubber
        scrub_frame = tk.Frame(hud_card, bg=BG_CARD)
        scrub_frame.pack(fill="x", padx=12, pady=(0, 6))

        self.progress_bar = ttk.Progressbar(scrub_frame, style="Horizontal.TProgressbar", mode="determinate", maximum=100)
        self.progress_bar.pack(fill="x", pady=(0, 4))

        scrub_ctrl = tk.Frame(scrub_frame, bg=BG_CARD)
        scrub_ctrl.pack(fill="x")

        tk.Label(scrub_ctrl, text="Timeline Seek:", font=FONT_LABEL, fg=TXT_MUTED, bg=BG_CARD).pack(side="left")
        
        self.slider_seek = tk.Scale(
            scrub_ctrl,
            from_=0,
            to=100,
            orient="horizontal",
            showvalue=0,
            bg=BG_CARD,
            fg=TXT_MAIN,
            troughcolor=BG_INPUT,
            highlightthickness=0,
            sliderrelief="flat",
            activebackground=ACCENT_CYAN,
            command=self.on_seek_change
        )
        self.slider_seek.pack(side="left", fill="x", expand=True, padx=8)

        self.lbl_seek_val = tk.Label(scrub_ctrl, text="0 / 0", font=FONT_MONO, fg=ACCENT_CYAN, bg=BG_CARD, width=12, anchor="e")
        self.lbl_seek_val.pack(side="right")

        # 3. Synchronized Interactive Dataset Treeview
        tree_frame = tk.Frame(parent, bg=BG_PANEL)
        tree_frame.pack(fill="both", expand=True, padx=12, pady=(0, 6))

        cols = ("status", "idx", "timestamp", "station", "dry_temp", "wet_temp", "pressure", "humidity", "diagnosis")
        self.tree_data = ttk.Treeview(tree_frame, columns=cols, show="headings", selectmode="browse")
        
        self.tree_data.heading("status", text="TX")
        self.tree_data.heading("idx", text="#")
        self.tree_data.heading("timestamp", text="Timestamp (UTC)")
        self.tree_data.heading("station", text="Station ID")
        self.tree_data.heading("dry_temp", text="Dry Temp (°C)")
        self.tree_data.heading("wet_temp", text="Wet Temp (°C)")
        self.tree_data.heading("pressure", text="Pressure (hPa)")
        self.tree_data.heading("humidity", text="Humidity (%)")
        self.tree_data.heading("diagnosis", text="Testbench Diagnosis / Anomaly Note")

        self.tree_data.column("status", width=40, anchor="center")
        self.tree_data.column("idx", width=55, anchor="center")
        self.tree_data.column("timestamp", width=180, anchor="w")
        self.tree_data.column("station", width=85, anchor="center")
        self.tree_data.column("dry_temp", width=105, anchor="center")
        self.tree_data.column("wet_temp", width=105, anchor="center")
        self.tree_data.column("pressure", width=115, anchor="center")
        self.tree_data.column("humidity", width=105, anchor="center")
        self.tree_data.column("diagnosis", width=220, anchor="w")

        # Treeview Row Coloring Tags
        self.tree_data.tag_configure("active_tx", background="#0c4a6e", foreground="#38bdf8")
        self.tree_data.tag_configure("anomaly_row", background="#3b1219", foreground="#fda4af")
        self.tree_data.tag_configure("freeze_row", background="#332408", foreground="#fde68a")
        self.tree_data.tag_configure("even_row", background="#101827")
        self.tree_data.tag_configure("odd_row", background="#0b111e")

        tree_scroll_y = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree_data.yview)
        self.tree_data.configure(yscrollcommand=tree_scroll_y.set)
        
        self.tree_data.pack(side="left", fill="both", expand=True)
        tree_scroll_y.pack(side="right", fill="y")

        self.tree_data.bind("<Double-1>", self.on_tree_row_double_click)

    def create_hud_meter(self, parent, col, title, initial_val, color):
        box = tk.Frame(parent, bg=BG_INPUT, highlightthickness=1, highlightbackground=BORDER_SUBTLE, padx=8, pady=6)
        box.grid(row=0, column=col, padx=4, pady=2, sticky="nsew")

        lbl_t = tk.Label(box, text=title, font=FONT_LABEL, fg=TXT_MUTED, bg=BG_INPUT)
        lbl_t.pack(anchor="w")

        lbl_v = tk.Label(box, text=initial_val, font=FONT_MONO_LG, fg=color, bg=BG_INPUT)
        lbl_v.pack(anchor="w", pady=(2, 0))
        return lbl_v

    # ────────────────────────────────────────────────────────────────────────
    # TAB 2: MULTI-STATION SPATIAL NETWORK SIMULATOR
    # ────────────────────────────────────────────────────────────────────────
    def setup_multi_station_tab(self, parent):
        card = tk.Frame(parent, bg=BG_CARD, highlightthickness=1, highlightbackground=BORDER_CARD)
        card.pack(fill="both", expand=True, padx=12, pady=10)

        tk.Label(card, text="🌐 4-STATION MESOSCALE SPATIAL NETWORK EMULATOR", font=FONT_HEADING, fg=ACCENT_CYAN, bg=BG_CARD).pack(anchor="w", padx=14, pady=(12, 2))
        tk.Label(card, text="Simultaneously transmits synchronized packets for AWS-01 (Target Station), AWS-02 (North), AWS-03 (East), and AWS-04 (South).", font=FONT_BODY, fg=TXT_MUTED, bg=BG_CARD).pack(anchor="w", padx=14, pady=(0, 12))

        # Station Cards Grid
        grid_f = tk.Frame(card, bg=BG_CARD)
        grid_f.pack(fill="x", padx=14, pady=6)

        self.st_card_1 = self.create_station_view_card(grid_f, "AWS-01 (Target Proving Ground)", 31.0, 1013.2, 65.0, 0, is_target=True)
        self.st_card_2 = self.create_station_view_card(grid_f, "AWS-02 (North Outpost)", 31.2, 1013.0, 64.6, 1)
        self.st_card_3 = self.create_station_view_card(grid_f, "AWS-03 (East Range Node)", 30.9, 1013.3, 65.2, 2)
        self.st_card_4 = self.create_station_view_card(grid_f, "AWS-04 (South Meteorological Sector)", 31.1, 1013.1, 64.9, 3)

        # Fault Injection Controls
        inj_panel = tk.Frame(card, bg=BG_INPUT, highlightthickness=1, highlightbackground=BORDER_SUBTLE)
        inj_panel.pack(fill="x", padx=14, pady=(16, 10))

        tk.Label(inj_panel, text="⚡ SPATIAL CONSENSUS FAULT BENCH:", font=FONT_LABEL, fg=ACCENT_AMBER, bg=BG_INPUT).pack(side="left", padx=12, pady=10)

        btn_glitch = tk.Button(inj_panel, text="🚨 Inject AWS-01 Spatial Outlier (55°C)", font=FONT_BOLD, bg=ACCENT_RED, fg="#ffffff", relief="flat", padx=10, pady=5, cursor="hand2", command=self.inject_spatial_glitch)
        btn_glitch.pack(side="left", padx=6, pady=8)

        btn_reset = tk.Button(inj_panel, text="🔄 Reset Nominal Consensus (31°C)", font=FONT_BOLD, bg=ACCENT_GREEN, fg="#ffffff", relief="flat", padx=10, pady=5, cursor="hand2", command=self.reset_spatial_glitch)
        btn_reset.pack(side="left", padx=6, pady=8)

    def create_station_view_card(self, parent, name, temp, press, rh, col, is_target=False):
        parent.columnconfigure(col, weight=1)
        f = tk.Frame(parent, bg=BG_INPUT, highlightthickness=1, highlightbackground=ACCENT_CYAN if is_target else BORDER_SUBTLE, padx=10, pady=10)
        f.grid(row=0, column=col, padx=4, pady=4, sticky="nsew")

        tk.Label(f, text=name, font=FONT_BOLD, fg=ACCENT_CYAN if is_target else TXT_MAIN, bg=BG_INPUT).pack(anchor="w")
        
        lbl_t = tk.Label(f, text=f"Temp: {temp:.1f} °C", font=FONT_MONO_LG, fg=ACCENT_RED if is_target and self.spatial_glitch else TXT_MAIN, bg=BG_INPUT)
        lbl_t.pack(anchor="w", pady=(6, 2))

        lbl_p = tk.Label(f, text=f"Press: {press:.1f} hPa", font=FONT_MONO, fg=TXT_MUTED, bg=BG_INPUT)
        lbl_p.pack(anchor="w", pady=1)

        lbl_h = tk.Label(f, text=f"RH: {rh:.1f} %", font=FONT_MONO, fg=TXT_MUTED, bg=BG_INPUT)
        lbl_h.pack(anchor="w", pady=1)

        return {"lbl_t": lbl_t, "lbl_p": lbl_p, "lbl_h": lbl_h}

    # ────────────────────────────────────────────────────────────────────────
    # TAB 3: LIVE SLIDERS & DIRECT ANOMALY INJECTOR
    # ────────────────────────────────────────────────────────────────────────
    def setup_manual_tab(self, parent):
        card = tk.Frame(parent, bg=BG_CARD, highlightthickness=1, highlightbackground=BORDER_CARD)
        card.pack(fill="both", expand=True, padx=12, pady=10)

        # Sliders
        s_frame = tk.Frame(card, bg=BG_CARD)
        s_frame.pack(fill="x", padx=14, pady=10)

        self.create_interactive_slider(s_frame, "Dry Bulb Temp (°C):", self.val_temp, -40.0, 60.0, 0, ACCENT_RED)
        self.create_interactive_slider(s_frame, "Wet Bulb Temp (°C):", self.val_wet_temp, -40.0, 50.0, 1, ACCENT_AMBER)
        self.create_interactive_slider(s_frame, "Atmospheric Pressure (hPa):", self.val_press, 850.0, 1080.0, 2, ACCENT_CYAN)
        self.create_interactive_slider(s_frame, "Relative Humidity (%):", self.val_rh, 0.0, 100.0, 3, ACCENT_PURPLE)

        # Instant Anomaly Injection Presets
        inj_card = tk.Frame(card, bg=BG_INPUT, highlightthickness=1, highlightbackground=BORDER_SUBTLE)
        inj_card.pack(fill="x", padx=14, pady=(10, 10))

        tk.Label(inj_card, text="⚡ INSTANT SENSOR FAULT GENERATORS:", font=FONT_LABEL, fg=ACCENT_AMBER, bg=BG_INPUT).pack(anchor="w", padx=12, pady=(10, 6))

        btn_row = tk.Frame(inj_card, bg=BG_INPUT)
        btn_row.pack(fill="x", padx=12, pady=(0, 10))

        tk.Button(btn_row, text="Temp Spike (+25°C)", font=FONT_BOLD, bg="#881337", fg="#fda4af", relief="flat", padx=8, pady=4, cursor="hand2", command=lambda: self.val_temp.set(56.8)).pack(side="left", padx=4)
        tk.Button(btn_row, text="Pressure Lockup (1013.25)", font=FONT_BOLD, bg="#78350f", fg="#fde68a", relief="flat", padx=8, pady=4, cursor="hand2", command=lambda: self.val_press.set(1013.25)).pack(side="left", padx=4)
        tk.Button(btn_row, text="Humidity Collapse (12%)", font=FONT_BOLD, bg="#4c1d95", fg="#ddd6fe", relief="flat", padx=8, pady=4, cursor="hand2", command=lambda: self.val_rh.set(12.4)).pack(side="left", padx=4)
        tk.Button(btn_row, text="Sub-Zero Fault (-48°C)", font=FONT_BOLD, bg="#1e3a8a", fg="#bfdbfe", relief="flat", padx=8, pady=4, cursor="hand2", command=lambda: self.val_temp.set(-48.5)).pack(side="left", padx=4)
        tk.Button(btn_row, text="🔄 Reset Nominal (31°C)", font=FONT_BOLD, bg=ACCENT_GREEN, fg="#ffffff", relief="flat", padx=8, pady=4, cursor="hand2", command=self.reset_nominal_sliders).pack(side="right", padx=4)

    def create_interactive_slider(self, parent, label_text, var, from_val, to_val, row, color):
        f = tk.Frame(parent, bg=BG_CARD)
        f.pack(fill="x", pady=4)

        tk.Label(f, text=label_text, font=FONT_BOLD, fg=TXT_MAIN, bg=BG_CARD, width=24, anchor="w").pack(side="left")
        
        scale = tk.Scale(
            f,
            from_=from_val,
            to=to_val,
            resolution=0.1,
            orient="horizontal",
            variable=var,
            font=FONT_MONO,
            bg=BG_CARD,
            fg=TXT_MAIN,
            troughcolor=BG_INPUT,
            highlightthickness=0,
            activebackground=color
        )
        scale.pack(side="left", fill="x", expand=True, padx=10)

        lbl_val = tk.Label(f, textvariable=var, font=FONT_MONO_LG, fg=color, bg=BG_CARD, width=8, anchor="e")
        lbl_val.pack(side="right")

    # ────────────────────────────────────────────────────────────────────────
    # TAB 4: 2-LAPTOP SETUP GUIDE & NETWORK DIAGNOSTICS
    # ────────────────────────────────────────────────────────────────────────
    def setup_guide_tab(self, parent):
        card = tk.Frame(parent, bg=BG_CARD, highlightthickness=1, highlightbackground=BORDER_CARD)
        card.pack(fill="both", expand=True, padx=12, pady=10)

        tk.Label(card, text="📡 2-LAPTOP DIRECT ETHERNET / WI-FI DEMO WORKFLOW", font=FONT_HEADING, fg=ACCENT_CYAN, bg=BG_CARD).pack(anchor="w", padx=14, pady=(12, 6))

        instructions = (
            "1. CONNECT HARDWARE:\n"
            "   • Connect an Ethernet LAN cable directly between Laptop 1 (Ground Station) and Laptop 2 (Data Sender),\n"
            "     OR connect both laptops to the same Wi-Fi router.\n\n"
            "2. CONFIGURE GROUND STATION (LAPTOP 1 / SYSTEM B):\n"
            "   • Launch AWS_SkyGuard_Station.exe on Laptop 1.\n"
            "   • Check Laptop 1's IP address (e.g. 192.168.1.100) using 'ipconfig' in command prompt.\n\n"
            "3. BROADCAST FROM THIS SENDER (LAPTOP 2 / SYSTEM A):\n"
            "   • Enter Laptop 1's IP address in 'Target Host IP' above (or click 'Broadcast' for 255.255.255.255).\n"
            "   • Select '📁 Real-Time CSV Telemetry Streamer' tab and click '▶ START TRANSMISSION'.\n\n"
            "4. LIVE DEMONSTRATION OF AI SELF-HEALING & PREDICTIVE MAINTENANCE:\n"
            "   • Watch the row-by-row streaming progression in the dataset table.\n"
            "   • When rows reach anomaly frames (e.g. Temp 56.5°C or Pressure Freeze), watch Laptop 1's dashboard\n"
            "     instantly flag the fault with XAI SHAP attributions and execute real-time Self-Healing!"
        )

        txt_info = tk.Text(card, font=FONT_MONO, bg=BG_INPUT, fg=TXT_MAIN, relief="flat", padx=14, pady=12, highlightthickness=1, highlightbackground=BORDER_SUBTLE)
        txt_info.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        txt_info.insert("1.0", instructions)
        txt_info.config(state="disabled")

    # ────────────────────────────────────────────────────────────────────────
    # CORE DATASET PARSER & EVENT HANDLERS
    # ────────────────────────────────────────────────────────────────────────
    def auto_load_default_dataset(self):
        default_file = "aws_telemetry_1000_samples.csv"
        # Search current working directory or relative path
        candidates = [
            default_file,
            os.path.join(os.path.dirname(os.path.abspath(__file__)), default_file),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist", default_file)
        ]
        for path in candidates:
            if os.path.exists(path):
                self.load_csv_file(path)
                return

    def load_dataset_dialog(self):
        fpath = filedialog.askopenfilename(
            title="Select Telemetry Dataset (CSV / TXT)",
            filetypes=[("CSV & Data Files", "*.csv *.txt *.log *.dat"), ("All Files", "*.*")]
        )
        if fpath:
            self.load_csv_file(fpath)

    def load_csv_file(self, fpath):
        try:
            self.loaded_data = []
            for row in self.tree_data.get_children():
                self.tree_data.delete(row)

            with open(fpath, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for i, raw_row in enumerate(reader):
                    row = {k.strip().lower(): v.strip() for k, v in raw_row.items() if k}

                    # Dry Bulb Temp
                    t_str = row.get("dry bulb temp") or row.get("dry_bulb_temp") or row.get("temp") or row.get("temperature") or "30.0"
                    t_val = float(t_str)

                    # Wet Bulb Temp
                    w_str = row.get("wet bulb temp") or row.get("wet_bulb_temp") or row.get("wet_temp") or str(round(t_val - 4.5, 2))
                    w_val = float(w_str)

                    # Pressure
                    p_str = row.get("pressure (hpa)") or row.get("pressure(hpa)") or row.get("pressure_hpa") or row.get("pressure") or "1013.2"
                    p_val = float(p_str)
                    
                    p_imu_str = row.get("pressure(imu)") or row.get("pressure_imu") or str(round(p_val * 100.0, 1))
                    p_imu_val = float(p_imu_str)

                    # Humidity
                    h_str = row.get("relative humidity") or row.get("relative_humidity") or row.get("humidity") or "65.0"
                    h_val = float(h_str)

                    st_val = row.get("station id") or row.get("station_id") or row.get("station") or "AWS-01"
                    ts_val = row.get("timestamp") or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

                    # Automated Classification for Visual Tagging
                    is_anomaly = False
                    diagnosis = "Nominal Baseline"
                    tag = "even_row" if i % 2 == 0 else "odd_row"

                    if t_val > 55.0:
                        is_anomaly = True
                        diagnosis = "🚨 TEMP SPIKE / OUT-OF-BOUNDS"
                        tag = "anomaly_row"
                    elif t_val < -40.0:
                        is_anomaly = True
                        diagnosis = "🚨 NEGATIVE TEMP FAULT (-48°C)"
                        tag = "anomaly_row"
                    elif h_val < 20.0:
                        is_anomaly = True
                        diagnosis = "⚠️ HUMIDITY COLLAPSE (12%)"
                        tag = "anomaly_row"
                    elif p_val < 950.0:
                        is_anomaly = True
                        diagnosis = "🚨 PRESSURE GLITCH (910 hPa)"
                        tag = "anomaly_row"

                    record = {
                        "row_idx": i + 1,
                        "timestamp": ts_val,
                        "station_id": st_val,
                        "dry_temp": t_val,
                        "wet_temp": w_val,
                        "pressure": p_val,
                        "pressure_imu": p_imu_val,
                        "humidity": h_val,
                        "diagnosis": diagnosis,
                        "is_anomaly": is_anomaly,
                        "default_tag": tag
                    }
                    self.loaded_data.append(record)

                    item_id = self.tree_data.insert(
                        "",
                        "end",
                        iid=f"row_{i}",
                        values=("○", i + 1, ts_val, st_val, f"{t_val:.2f}", f"{w_val:.2f}", f"{p_val:.2f}", f"{h_val:.2f}", diagnosis),
                        tags=(tag,)
                    )

            count = len(self.loaded_data)
            self.lbl_file_status.config(text=f"Loaded {count} rows from {os.path.basename(fpath)}")
            self.slider_seek.config(to=max(1, count - 1))
            self.lbl_seek_val.config(text=f"Row 1 / {count}")
            self.current_row_idx = 0

            self.log_terminal(f"📁 Dataset loaded: {os.path.basename(fpath)} ({count} telemetry frames ready)", "tx_info")
        except Exception as e:
            messagebox.showerror("File Import Error", f"Could not parse dataset:\n{str(e)}")

    def on_seek_change(self, val):
        idx = int(float(val))
        if 0 <= idx < len(self.loaded_data):
            self.current_row_idx = idx
            self.lbl_seek_val.config(text=f"Row {idx + 1} / {len(self.loaded_data)}")
            if not self.is_streaming:
                self.update_hud_display(self.loaded_data[idx], idx, len(self.loaded_data))

    def on_tree_row_double_click(self, event):
        sel = self.tree_data.selection()
        if sel:
            item_id = sel[0]
            try:
                idx = int(item_id.replace("row_", ""))
                self.slider_seek.set(idx)
            except Exception:
                pass

    def detect_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            # Calculate broadcast address for current subnet (assume /24)
            parts = ip.split(".")
            bcast_ip = f"{parts[0]}.{parts[1]}.{parts[2]}.255"
            self.target_ip.set(bcast_ip)
            self.log_terminal(f"🔍 Local Network Detected: IP={ip} -> Set Subnet Broadcast={bcast_ip}", "tx_info")
        except Exception as e:
            self.target_ip.set("255.255.255.255")
            self.log_terminal(f"⚠️ IP detection fallback: Set to Global Broadcast 255.255.255.255", "tx_warn")

    # ────────────────────────────────────────────────────────────────────────
    # TRANSMISSION ENGINE & SYNCHRONOUS VISUAL TRACKER
    # ────────────────────────────────────────────────────────────────────────
    def toggle_transmission(self):
        if self.is_streaming:
            self.is_streaming = False
            self.btn_toggle.config(text="▶  START TRANSMISSION", bg=ACCENT_GREEN)
            self.status_pill.config(text="● STANDBY", fg=TXT_DIM)
            self.log_terminal("⏹️ Transmission stopped by operator.", "tx_warn")
        else:
            self.is_streaming = True
            self.start_time = time.time()
            self.btn_toggle.config(text="⏹  STOP TRANSMISSION", bg=ACCENT_RED)
            self.status_pill.config(text="● TRANSMITTING LIVE", fg=ACCENT_GREEN)
            self.stream_thread = threading.Thread(target=self.run_tx_loop, daemon=True)
            self.stream_thread.start()
            self.log_terminal(f"🚀 Transmission STARTED -> {self.target_ip.get()}:{self.target_port.get()} via {self.protocol_mode.get()}", "tx_ok")

    def run_tx_loop(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        while self.is_streaming:
            try:
                target_host = self.target_ip.get().strip()
                target_port = int(self.target_port.get())
                proto = self.protocol_mode.get()
                freq = max(0.1, float(self.stream_freq.get()))
                interval = 1.0 / freq

                # Determine active data frame
                active_tab_idx = self.notebook.index(self.notebook.select())
                
                # Tab 1: Dataset Streamer
                if active_tab_idx == 0 and len(self.loaded_data) > 0:
                    rec = self.loaded_data[self.current_row_idx]
                    t_val = rec["dry_temp"]
                    w_val = rec["wet_temp"]
                    p_val = rec["pressure"]
                    h_val = rec["humidity"]
                    st_val = rec["station_id"]
                    
                    # Schedule UI Visual update on Main Thread
                    curr_idx = self.current_row_idx
                    total_rows = len(self.loaded_data)
                    self.root.after(0, self.update_hud_display, rec, curr_idx, total_rows)

                    # Increment sequence
                    if self.loop_file.get():
                        self.current_row_idx = (self.current_row_idx + 1) % total_rows
                    else:
                        self.current_row_idx = min(self.current_row_idx + 1, total_rows - 1)

                # Tab 2: Multi-Station Spatial Simulator
                elif active_tab_idx == 1:
                    stations = ["AWS-01", "AWS-02", "AWS-03", "AWS-04"]
                    st_val = stations[self.packet_count % 4]
                    w_val = 25.5
                    p_val = 1013.2
                    h_val = 65.0
                    if st_val == "AWS-01" and self.spatial_glitch:
                        t_val = 55.0
                    else:
                        t_val = 31.0 + (0.2 if st_val == "AWS-02" else (-0.1 if st_val == "AWS-03" else 0.1))

                # Tab 3: Interactive Manual Sliders
                else:
                    t_val = float(self.val_temp.get())
                    w_val = float(self.val_wet_temp.get())
                    p_val = float(self.val_press.get())
                    h_val = float(self.val_rh.get())
                    st_val = self.val_station.get()

                # Build 24-byte Binary 0xAA55 Frame
                ts = int(time.time())
                payload = struct.pack(">H I f f f f", 0xAA55, ts, t_val, w_val, p_val, h_val)
                crc = sum(payload) % 256
                packet = payload + struct.pack("B B", crc, 0x0A)

                if "JSON" in proto:
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

                # Log to terminal (every frame or formatted log)
                hex_sample = packet[:12].hex().upper()
                is_anom = t_val > 50.0 or t_val < 0.0 or p_val < 950.0 or h_val < 20.0
                tag = "tx_anomaly" if is_anom else "tx_ok"
                log_msg = f"[0xAA55] SEQ: {self.packet_count:05d} | {st_val} | T: {t_val:5.1f}°C | W: {w_val:5.1f}°C | P: {p_val:6.1f}hPa | RH: {h_val:4.1f}% | HEX: 0x{hex_sample}... -> {target_host}:{target_port}"
                self.root.after(0, self.log_terminal, log_msg, tag)

                time.sleep(interval)
            except Exception as e:
                self.root.after(0, self.log_terminal, f"⚠️ Socket Error: {str(e)}", "tx_warn")
                time.sleep(1.0)

        sock.close()

    def update_hud_display(self, rec, row_idx, total_rows):
        # 1. Update large HUD digital readout meters
        t_val = rec["dry_temp"]
        w_val = rec["wet_temp"]
        p_val = rec["pressure"]
        h_val = rec["humidity"]

        self.meter_temp.config(text=f"{t_val:.1f} °C", fg=ACCENT_RED if rec["is_anomaly"] else "#ffffff")
        self.meter_wet.config(text=f"{w_val:.1f} °C")
        self.meter_rh.config(text=f"{h_val:.1f} %", fg=ACCENT_RED if h_val < 20.0 else ACCENT_PURPLE)
        self.meter_press.config(text=f"{p_val:.1f} hPa", fg=ACCENT_RED if p_val < 950.0 else ACCENT_CYAN)
        self.meter_seq.config(text=f"Row {row_idx + 1} / {total_rows}")

        # Anomaly Badge
        if rec["is_anomaly"]:
            self.lbl_anomaly_badge.config(text=f"🚨 {rec['diagnosis']}", fg="#ffffff", bg=ACCENT_RED)
        else:
            self.lbl_anomaly_badge.config(text="● NOMINAL BASELINE", fg=ACCENT_GREEN, bg=BG_INPUT)

        # 2. Update Progress Bar & Scrubber
        pct = (row_idx / max(1, total_rows - 1)) * 100.0
        self.progress_bar["value"] = pct
        self.slider_seek.set(row_idx)
        self.lbl_seek_val.config(text=f"Row {row_idx + 1} / {total_rows}")

        # 3. Highlight and Auto-Scroll Treeview
        item_id = f"row_{row_idx}"
        prev_idx = (row_idx - 1) % total_rows
        prev_id = f"row_{prev_idx}"

        # Reset previous row tag
        if self.tree_data.exists(prev_id) and prev_idx < len(self.loaded_data):
            orig_tag = self.loaded_data[prev_idx]["default_tag"]
            self.tree_data.item(prev_id, tags=(orig_tag,), values=("○", *self.tree_data.item(prev_id, "values")[1:]))

        # Highlight current row
        if self.tree_data.exists(item_id):
            self.tree_data.item(item_id, tags=("active_tx",), values=("▶", *self.tree_data.item(item_id, "values")[1:]))
            self.tree_data.see(item_id)

    def log_terminal(self, msg, tag="tx_ok"):
        t_str = datetime.now().strftime("%H:%M:%S")
        self.txt_terminal.insert("end", f"[{t_str}] {msg}\n", tag)
        if self.auto_scroll_log:
            self.txt_terminal.see("end")
        self.lbl_tx_counter.config(text=f"TX PKTS: {self.packet_count}")

    def clear_log(self):
        self.txt_terminal.delete("1.0", "end")

    def toggle_autoscroll(self):
        self.auto_scroll_log = not self.auto_scroll_log

    def update_elapsed_timer(self):
        if self.is_streaming and self.start_time:
            elapsed = int(time.time() - self.start_time)
            hrs = elapsed // 3600
            mins = (elapsed % 3600) // 60
            secs = elapsed % 60
            self.lbl_elapsed.config(text=f"⏱ {hrs:02d}:{mins:02d}:{secs:02d}")
        self.root.after(1000, self.update_elapsed_timer)

    # ────────────────────────────────────────────────────────────────────────
    # FAULT INJECTION CONTROLLERS
    # ────────────────────────────────────────────────────────────────────────
    def inject_spatial_glitch(self):
        self.spatial_glitch = True
        if hasattr(self, "st_card_1"):
            self.st_card_1["lbl_t"].config(text="Temp: 55.0 °C", fg=ACCENT_RED)
        self.log_terminal("🚨 INJECTED: AWS-01 Spatial Glitch (55.0°C Outlier vs Neighbor 31.0°C)", "tx_anomaly")

    def reset_spatial_glitch(self):
        self.spatial_glitch = False
        if hasattr(self, "st_card_1"):
            self.st_card_1["lbl_t"].config(text="Temp: 31.0 °C", fg=TXT_MAIN)
        self.log_terminal("🔄 RESET: AWS-01 restored to Nominal Spatial Consensus (31.0°C)", "tx_ok")

    def reset_nominal_sliders(self):
        self.val_temp.set(31.0)
        self.val_wet_temp.set(25.5)
        self.val_press.set(1013.2)
        self.val_rh.set(65.0)
        self.log_terminal("🔄 Reset sliders to nominal atmospheric baseline.", "tx_ok")


def main():
    root = tk.Tk()
    app = SkyGuardTelemetryTransmitter(root)
    root.mainloop()

if __name__ == "__main__":
    main()
