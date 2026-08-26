"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  LayoutDashboard,
  Activity,
  Database,
  Sliders,
  AlertTriangle,
  CheckCircle,
  Wind,
  Compass,
  Sun,
  CloudRain,
  Cpu,
  RefreshCw,
  Clock,
  Info,
  Thermometer,
  Droplets,
  Gauge,
  Shield,
  FileText,
  Search,
  Download,
  Settings,
  SlidersHorizontal,
  FolderOpen
} from "lucide-react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend
} from "recharts";

const DEFAULT_PARAMS = [
  { id: 1, name: "Time_Inst", dataType: "uint32", unit: "", scale: 1.0, offset: 0.0, mode: "both", color: "#3b82f6", enabled: true, threshold: null },
  { id: 2, name: "Direction", dataType: "uint16", unit: "DEG", scale: 1.0, offset: 0.0, mode: "both", color: "#10b981", enabled: true, threshold: null },
  { id: 3, name: "Speed", dataType: "uint16", unit: "M/S", scale: 0.1, offset: 0.0, mode: "both", color: "#f59e0b", enabled: true, threshold: 5.5 },
  { id: 4, name: "Dry Bulb Temp", dataType: "int16", unit: "°C", scale: 0.1, offset: 0.0, mode: "both", color: "#ef4444", enabled: true, threshold: 36.8 },
  { id: 5, name: "Wet Bulb Temp", dataType: "int16", unit: "°C", scale: 0.1, offset: 0.0, mode: "both", color: "#ec4899", enabled: true, threshold: null },
  { id: 6, name: "Rel. Humidity", dataType: "uint16", unit: "%", scale: 0.1, offset: 0.0, mode: "both", color: "#a855f7", enabled: true, threshold: 85.0 },
  { id: 7, name: "Solar Radiation", dataType: "uint16", unit: "W/M²", scale: 1.0, offset: 0.0, mode: "both", color: "#eab308", enabled: true, threshold: null },
  { id: 8, name: "Rainfall", dataType: "uint16", unit: "MM", scale: 0.1, offset: 0.0, mode: "both", color: "#22d3ee", enabled: true, threshold: 2.0 },
  { id: 9, name: "Pressure (IMU)", dataType: "float32", unit: "hPa", scale: 1.0, offset: 0.0, mode: "both", color: "#3b82f6", enabled: true, threshold: null },
  { id: 10, name: "Pressure (hPa)", dataType: "uint32", unit: "hPa", scale: 0.01, offset: 0.0, mode: "both", color: "#8b5cf6", enabled: true, threshold: null },
];

export default function Home() {
  const [activeTab, setActiveTab] = useState("dashboard");
  const [theme, setTheme] = useState("dark");
  const [isStreaming, setIsStreaming] = useState(true);
  const [useImputed, setUseImputed] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState("disconnected");
  
  const [current, setCurrent] = useState(null);
  const [streamSource, setStreamSource] = useState("UDP LAN (0.0.0.0:5000) - READY FOR LAN CABLE");
  const [telemetryHistory, setTelemetryHistory] = useState([]);
  const [metrics, setMetrics] = useState({ received: 0, dropped: 0 });
  const [minMax, setMinMax] = useState({});
  const [activeParameters, setActiveParameters] = useState([]);

  const isCardActive = (cardName) => {
    if (!activeParameters || activeParameters.length === 0) return true;
    return activeParameters.some(p => (p.name === cardName || p.Name === cardName) && (p.present || p.Present || p.status === "ENABLED" || p.Status === "ENABLED"));
  };

  const [analysis, setAnalysis] = useState({
    is_anomaly: false,
    severity: "NOMINAL",
    confidence: 100,
    anomaly_type: "nominal",
    xai_explanation: "SYSTEM INITIALIZED\nSTATUS: HEALTHY\nAll meteorological channels within nominal physical tolerances.",
    imputed_values: { temp_dry: 25.0, humidity: 55.0, pressure_hpa: 1013.25 }
  });

  // Dynamic Network Link Configuration
  const [linkProtocol, setLinkProtocol] = useState("UDP");
  const [linkHost, setLinkHost] = useState("0.0.0.0");
  const [linkPort, setLinkPort] = useState(5000);
  const [linkFormat, setLinkFormat] = useState("AUTO");
  const [linkStatusMsg, setLinkStatusMsg] = useState("");
  const [linkLiveStats, setLinkLiveStats] = useState({ packets_in: 0, bytes_in: 0, status: "LISTENING" });

  const [dateStr, setDateStr] = useState("");
  const [timeStr, setTimeStr] = useState("");
  const [loggerFilter, setLoggerFilter] = useState("");
  const [loggerCols, setLoggerCols] = useState({
    "Time_Inst": true,
    "Direction": true,
    "Speed": true,
    "Dry Bulb Temp": true,
    "Wet Bulb Temp": true,
    "Rel. Humidity": true,
    "Solar Radiation": true,
    "Rainfall": true,
    "Pressure (IMU)": true,
    "Pressure (hPa)": true
  });

  const eventSourceRef = useRef(null);

  // Clock
  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setDateStr(now.toLocaleDateString("en-US", { weekday: "long", year: "numeric", month: "short", day: "numeric" }));
      setTimeStr(now.toLocaleTimeString("en-US", { hour12: true }));
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  // Sync Theme
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  // Telemetry SSE Stream
  useEffect(() => {
    if (!isStreaming) {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
      setConnectionStatus("disconnected");
      return;
    }

    setConnectionStatus("connecting");
    const es = new EventSource("/api/stream");
    eventSourceRef.current = es;

    es.onopen = () => {
      setConnectionStatus("connected");
    };

    es.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        const timeNow = new Date(payload.timestamp * 1000).toLocaleTimeString("en-US", { hour12: false });
        
        let raw = payload.raw;
        const ai = payload.analysis || {
          is_anomaly: false,
          severity: "NOMINAL",
          confidence: 100,
          anomaly_type: "nominal",
          xai_explanation: "SYSTEM INITIALIZED\nSTATUS: HEALTHY",
          imputed_values: {}
        };

        if (payload.source) {
          setStreamSource(payload.source);
        }

        if (payload.active_parameters && payload.active_parameters.length > 0) {
          setActiveParameters(payload.active_parameters);
        } else if (payload.decoded_parameters && payload.decoded_parameters.length > 0) {
          setActiveParameters(payload.decoded_parameters.filter(p => p.present || p.Present || p.status === "ENABLED" || p.Status === "ENABLED"));
        }

        if (!raw) {
          if (ai && ai.xai_explanation) {
            setAnalysis(ai);
          }
          return;
        }

        setCurrent(raw);
        setAnalysis(ai);
        setMetrics(prev => ({
          received: prev.received + 1,
          dropped: prev.dropped + (ai.is_anomaly ? 1 : 0)
        }));

        // Min/Max cache
        setMinMax(prev => {
          const next = { ...prev };
          const map = {
            "Speed": raw.speed,
            "Dry Bulb Temp": raw.dry_bulb_temp,
            "Wet Bulb Temp": raw.wet_bulb_temp,
            "Rel. Humidity": raw.rel_humidity,
            "Solar Radiation": raw.solar_radiation,
            "Rainfall": raw.rainfall,
            "Pressure (IMU)": raw.pressure_imu,
            "Pressure (hPa)": raw.pressure_hpa
          };
          for (const [k, v] of Object.entries(map)) {
            if (v !== undefined && v !== null) {
              if (!next[k]) {
                next[k] = { min: v, max: v };
              } else {
                next[k] = { min: Math.min(next[k].min, v), max: Math.max(next[k].max, v) };
              }
            }
          }
          return next;
        });

        // History
        setTelemetryHistory(prev => {
          const row = {
            time: timeNow,
            timestamp: payload.timestamp,
            raw,
            is_anomaly: ai.is_anomaly,
            anomaly_type: ai.anomaly_type,
            xai: ai.xai_explanation,
            // Plot parameters
            dry_temp: useImputed && ai.is_anomaly && ai.imputed_values?.temp_dry ? ai.imputed_values.temp_dry : raw.dry_bulb_temp,
            wet_temp: raw.wet_bulb_temp,
            humidity: useImputed && ai.is_anomaly && ai.imputed_values?.humidity ? ai.imputed_values.humidity : raw.rel_humidity,
            pressure: useImputed && ai.is_anomaly && ai.imputed_values?.pressure_hpa ? ai.imputed_values.pressure_hpa : raw.pressure_hpa
          };
          const nextList = [...prev, row];
          if (nextList.length > 50) nextList.shift();
          return nextList;
        });
      } catch (err) {
        console.error("SSE parse error:", err);
      }
    };

    es.onerror = () => {
      setConnectionStatus("disconnected");
      es.close();
      setTimeout(() => {
        if (isStreaming) {
          // Reconnect logic
        }
      }, 3000);
    };

    return () => {
      if (es) es.close();
    };
  }, [isStreaming, useImputed]);

  // Fault Injection Triggers
  const injectFault = async (type, parameter, value) => {
    try {
      await fetch("/api/inject", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ type, parameter, value })
      });
    } catch (e) {
      console.error(e);
    }
  };

  const injectSpatialFault = async (stationId = "AWS-01", tempVal = 55.0) => {
    try {
      await fetch("/api/inject", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ type: "spatial", station_id: stationId, value: tempVal })
      });
    } catch (e) {
      console.error(e);
    }
  };

  const resetFault = async () => {
    try {
      await fetch("/api/reset", { method: "POST" });
    } catch (e) {
      console.error(e);
    }
  };

  // Load initial config from backend on mount
  useEffect(() => {
    const fetchInitialConfig = async () => {
      try {
        const res = await fetch("/api/link_config");
        const data = await res.json();
        if (data && data.protocol) {
          setLinkProtocol(data.protocol);
          setLinkHost(data.host || "0.0.0.0");
          setLinkPort(data.port || 5000);
          setLinkFormat(data.format || "AUTO");
          setLinkLiveStats(data);
          if (data.protocol === "UDP" || data.protocol === "TCP") {
            setStreamSource(`${data.protocol} LAN (${data.host || "0.0.0.0"}:${data.port || 5000}) - LISTENING FOR CABLE DATA`);
          } else {
            setStreamSource("SIMULATOR (AUTO-FAILOVER)");
          }
        }
      } catch (err) {
        console.error("Initial link config fetch failed:", err);
      }
    };
    fetchInitialConfig();
  }, []);

  const handleSelectProtocol = async (protoId) => {
    setLinkProtocol(protoId);
    const targetPort = protoId === "TCP" ? 5001 : 5000;
    if (protoId === "TCP" && linkPort === 5000) {
      setLinkPort(5001);
    } else if (protoId === "UDP" && linkPort === 5001) {
      setLinkPort(5000);
    }

    if (protoId === "UDP" || protoId === "TCP") {
      setStreamSource(`${protoId} LAN (${linkHost}:${targetPort}) - LISTENING FOR CABLE DATA`);
    } else {
      setStreamSource("SIMULATOR (AUTO-FAILOVER)");
    }
    setLinkStatusMsg(`Switching to ${protoId}...`);

    try {
      const res = await fetch("/api/link_config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          protocol: protoId,
          host: linkHost,
          port: targetPort,
          format: linkFormat
        })
      });
      const data = await res.json();
      if (data.status === "success") {
        setLinkStatusMsg(`✅ Switched to ${data.config.protocol} on ${data.config.host}:${data.config.port}`);
        setLinkLiveStats(data.config);
      } else {
        setLinkStatusMsg(`❌ Error: ${data.error || "Failed to bind"}`);
      }
    } catch (err) {
      setLinkStatusMsg(`❌ Request failed: ${err.message}`);
    }
  };

  const handleApplyLinkConfig = async () => {
    try {
      setLinkStatusMsg("Rebinding network socket...");
      const res = await fetch("/api/link_config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          protocol: linkProtocol,
          host: linkHost,
          port: parseInt(linkPort, 10) || 5000,
          format: linkFormat
        })
      });
      const data = await res.json();
      if (data.status === "success") {
        setLinkStatusMsg(`✅ Successfully bound ${data.config.protocol} on ${data.config.host}:${data.config.port}`);
        setLinkLiveStats(data.config);
        if (data.config.protocol === "UDP" || data.config.protocol === "TCP") {
          setStreamSource(`${data.config.protocol} LAN (${data.config.host}:${data.config.port}) - LISTENING FOR CABLE DATA`);
        } else {
          setStreamSource("SIMULATOR (AUTO-FAILOVER)");
        }
      } else {
        setLinkStatusMsg(`❌ Error: ${data.error || "Failed to bind"}`);
      }
    } catch (err) {
      setLinkStatusMsg(`❌ Request failed: ${err.message}`);
    }
  };

  const fetchLinkStats = async () => {
    try {
      const res = await fetch("/api/link_config");
      const data = await res.json();
      if (data) {
        setLinkLiveStats(data);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleExportCSV = () => {
    if (telemetryHistory.length === 0) return;
    let csv = "Time,Time_Inst,Direction,Speed(M/S),Dry_Bulb(C),Wet_Bulb(C),Rel_Humidity(%),Solar_Radiation(W/M2),Rainfall(MM),Pressure_IMU(hPa),Pressure(hPa),Anomaly,XAI_Diagnosis\n";
    telemetryHistory.forEach(h => {
      const r = h.raw;
      csv += `${h.time},${r.time_inst},${r.direction},${r.speed},${r.dry_bulb_temp},${r.wet_bulb_temp},${r.rel_humidity},${r.solar_radiation},${r.rainfall},${r.pressure_imu},${r.pressure_hpa},${h.is_anomaly ? "ANOMALY" : "NOMINAL"},"${h.xai || ''}"\n`;
    });
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "aws_telemetry_logs.csv";
    link.click();
  };

  const isConnected = connectionStatus === "connected";
  const needleRotation = current ? current.direction : 0;

  // Cardinal direction helper
  const getCardinal = (deg) => {
    const d = (deg % 360 + 360) % 360;
    const letters = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"];
    return letters[Math.floor((d + 22.5) / 45) % 8];
  };

  // Safe numerical formatter to prevent layout overflow with huge floats/exponents
  const formatVal = (val, decimals = 1, isInt = false) => {
    if (val === null || val === undefined || isNaN(Number(val))) return "--";
    const num = Number(val);
    if (Math.abs(num) >= 1e5 || (Math.abs(num) > 0 && Math.abs(num) < 1e-3)) {
      return num.toExponential(2);
    }
    if (isInt) {
      return Math.round(num).toString();
    }
    return num.toFixed(decimals);
  };

  const formatMinMax = (mm, decimals = 1) => {
    if (!mm || mm.min === undefined || mm.max === undefined) return "▼ -- ▲ --";
    return `▼ ${formatVal(mm.min, decimals)} ▲ ${formatVal(mm.max, decimals)}`;
  };

  return (
    <div className="app-container">
      {/* ─── TOP HEADER ─── */}
      <header className="app-header">
        <div className="header-left">
          <div className="header-title-box">
            <div className="header-title-row">
              <span className="header-title">☁️ Automated Weather Station</span>
              <span className={`status-tag ${isConnected ? "connected" : "disconnected"}`}>
                ● {connectionStatus.toUpperCase()}
              </span>
            </div>
            <span className="header-subtext">
              SOURCE: {streamSource.toUpperCase()} | UDP 5000 / TCP 5001 | SKYGUARD AI ACTIVE
            </span>
          </div>
        </div>

        <div className="header-actions">
          <button
            onClick={() => setIsStreaming(!isStreaming)}
            className={`btn-action ${isStreaming ? "btn-stream-stop" : "btn-stream-start"}`}
          >
            {isStreaming ? "■ STOP STREAM" : "▶ START STREAM"}
          </button>

          <button
            onClick={() => setUseImputed(!useImputed)}
            className={`btn-action ${useImputed ? "btn-healed-active" : ""}`}
          >
            {useImputed ? "✨ HEALED: ON" : "✨ HEALED: OFF"}
          </button>

          <button
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            className="btn-action"
          >
            {theme === "dark" ? "☀️ LIGHT MODE" : "🌙 DARK MODE"}
          </button>
        </div>
      </header>

      {/* ─── APP BODY ─── */}
      <div className="app-body">
        {/* ─── LEFT SIDEBAR ─── */}
        <aside className="app-sidebar">
          <div className="sidebar-title-box">
            <div className="sidebar-sub">MISSION OPERATIONS</div>
            <div className="sidebar-heading">AWS Control Terminal</div>
          </div>

          <nav className="sidebar-nav">
            {[
              { id: "dashboard", label: "Dashboard Monitor", icon: <LayoutDashboard size={15} /> },
              { id: "spatial_grid", label: "Multi-AWS Spatial Grid", icon: <Compass size={15} /> },
              { id: "live_graph", label: "Live Telemetry Plots", icon: <Activity size={15} /> },
              { id: "frame_editor", label: "Parameter Editor", icon: <Settings size={15} /> },
              { id: "data_logger", label: "Local Data Logger", icon: <Database size={15} /> },
              { id: "replay_session", label: "History Replay Hub", icon: <SlidersHorizontal size={15} /> },
              { id: "export_option", label: "System Export Center", icon: <Download size={15} /> },
              { id: "link_config", label: "Connection Links", icon: <Sliders size={15} /> }
            ].map(item => (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`nav-item ${activeTab === item.id ? "active" : ""}`}
              >
                {item.icon}
                <span>{item.label}</span>
              </button>
            ))}
          </nav>
        </aside>

        {/* ─── MAIN WORKSPACE ─── */}
        <main className="app-workspace">
          
          {/* 1. DASHBOARD MONITOR */}
          {activeTab === "dashboard" && (
            <div className="dashboard-layout">
              {/* Left Column: 10 Numerical Cards */}
              <div className="dashboard-main-column">
                <div className="section-header">
                  <span className="section-title">📊 AWS NUMERICAL OVERVIEW</span>
                  <span className="section-subtitle">Live sensor readings, updated per packet</span>
                </div>

                <div className="cards-grid-5x2">
                  {/* Card 1: Time_Inst */}
                  {isCardActive("Time_Inst") && (
                    <div className="metric-card">
                      <span className="card-title">Time_Inst</span>
                      <div className="card-value-box">
                        <span className="card-number" style={{ color: "#3b82f6" }}>
                          {current ? formatVal(current.time_inst, 0, true) : "-- --"}
                        </span>
                      </div>
                      <div className="card-footer">
                        <span className="minmax-badge">▼ -- ▲ --</span>
                        <span>SEC</span>
                      </div>
                    </div>
                  )}

                  {/* Card 2: Direction (Compass Dial) */}
                  {isCardActive("Direction") && (
                    <div className="metric-card">
                      <span className="card-title">Direction</span>
                      <div className="card-value-box" style={{ flexDirection: "column", gap: "4px" }}>
                        <span style={{ fontSize: "0.95rem", fontWeight: "bold", color: "#10b981", maxWidth: "100%", overflow: "hidden", textOverflow: "ellipsis" }}>
                          {current ? `${formatVal(current.direction, 0, true)}° ${getCardinal(current.direction)}` : "-- --"}
                        </span>
                        <div className="compass-box">
                          <span className="compass-cardinal compass-n">N</span>
                          <span className="compass-cardinal compass-e">E</span>
                          <span className="compass-cardinal compass-s">S</span>
                          <span className="compass-cardinal compass-w">W</span>
                          <div
                            className="compass-needle"
                            style={{ transform: `rotate(${needleRotation}deg)` }}
                          />
                        </div>
                      </div>
                      <div className="card-footer">
                        <span className="minmax-badge">▼ -- ▲ --</span>
                        <span>DEG</span>
                      </div>
                    </div>
                  )}

                  {/* Card 3: Speed */}
                  {isCardActive("Speed") && (
                    <div className="metric-card">
                      <span className="card-title">Speed</span>
                      <div className="card-value-box">
                        <span className="card-number" style={{ color: "#f59e0b" }}>
                          {current ? formatVal(current.speed, 1) : "--"}
                        </span>
                      </div>
                      <div className="card-footer">
                        <span className="minmax-badge">
                          {formatMinMax(minMax["Speed"], 1)}
                        </span>
                        <span>M/S</span>
                      </div>
                    </div>
                  )}

                  {/* Card 4: Dry Bulb Temp */}
                  {isCardActive("Dry Bulb Temp") && (
                    <div className={`metric-card ${analysis.is_anomaly && (analysis.anomaly_type.includes("temp") || analysis.anomaly_type.includes("bounds") || analysis.anomaly_type.includes("spike") || analysis.anomaly_type.includes("freeze") || analysis.anomaly_type.includes("multivariate")) ? (useImputed ? "healed-active" : "anomaly-active") : ""}`}>
                      <span className="card-title">Dry Bulb Temp</span>
                      <div className="card-value-box" style={{ flexDirection: "column", gap: "2px" }}>
                        <span className="card-number" style={{ color: useImputed && analysis.is_anomaly && analysis.imputed_values?.temp_dry !== undefined ? "#22d3ee" : "#ef4444" }}>
                          {current ? (useImputed && analysis.is_anomaly && analysis.imputed_values?.temp_dry !== undefined ? formatVal(analysis.imputed_values.temp_dry, 1) : formatVal(current.dry_bulb_temp, 1)) : "--"}
                        </span>
                        {useImputed && analysis.is_anomaly && analysis.imputed_values?.temp_dry !== undefined && (
                          <span style={{ fontSize: "0.6rem", color: "#22d3ee", fontWeight: "bold" }}>
                            🛡️ HEALED <small style={{ color: "#ef4444", textDecoration: "line-through" }}>({formatVal(current.dry_bulb_temp, 1)}°C)</small>
                          </span>
                        )}
                      </div>
                      <div className="card-footer">
                        <span className="minmax-badge">
                          {formatMinMax(minMax["Dry Bulb Temp"], 1)}
                        </span>
                        <span>°C</span>
                      </div>
                    </div>
                  )}

                  {/* Card 5: Wet Bulb Temp */}
                  {isCardActive("Wet Bulb Temp") && (
                    <div className="metric-card">
                      <span className="card-title">Wet Bulb Temp</span>
                      <div className="card-value-box">
                        <span className="card-number" style={{ color: "#ec4899" }}>
                          {current ? formatVal(current.wet_bulb_temp, 1) : "--"}
                        </span>
                      </div>
                      <div className="card-footer">
                        <span className="minmax-badge">
                          {formatMinMax(minMax["Wet Bulb Temp"], 1)}
                        </span>
                        <span>°C</span>
                      </div>
                    </div>
                  )}

                  {/* Card 6: Rel. Humidity */}
                  {isCardActive("Rel. Humidity") && (
                    <div className={`metric-card ${analysis.is_anomaly && (analysis.anomaly_type.includes("humidity") || analysis.anomaly_type.includes("multivariate") || analysis.anomaly_type.includes("bounds")) ? (useImputed ? "healed-active" : "anomaly-active") : ""}`}>
                      <span className="card-title">Rel. Humidity</span>
                      <div className="card-value-box" style={{ flexDirection: "column", gap: "2px" }}>
                        <span className="card-number" style={{ color: useImputed && analysis.is_anomaly && analysis.imputed_values?.humidity !== undefined ? "#22d3ee" : "#a855f7" }}>
                          {current ? (useImputed && analysis.is_anomaly && analysis.imputed_values?.humidity !== undefined ? formatVal(analysis.imputed_values.humidity, 1) : formatVal(current.rel_humidity, 1)) : "--"}
                        </span>
                        {useImputed && analysis.is_anomaly && analysis.imputed_values?.humidity !== undefined && (
                          <span style={{ fontSize: "0.6rem", color: "#22d3ee", fontWeight: "bold" }}>
                            🛡️ HEALED <small style={{ color: "#ef4444", textDecoration: "line-through" }}>({formatVal(current.rel_humidity, 1)}%)</small>
                          </span>
                        )}
                      </div>
                      <div className="card-footer">
                        <span className="minmax-badge">
                          {formatMinMax(minMax["Rel. Humidity"], 1)}
                        </span>
                        <span>%</span>
                      </div>
                    </div>
                  )}

                  {/* Card 7: Solar Radiation */}
                  {isCardActive("Solar Radiation") && (
                    <div className="metric-card">
                      <span className="card-title">Solar Radiation</span>
                      <div className="card-value-box">
                        <span className="card-number" style={{ color: "#eab308" }}>
                          {current ? formatVal(current.solar_radiation, 0) : "--"}
                        </span>
                      </div>
                      <div className="card-footer">
                        <span className="minmax-badge">
                          {formatMinMax(minMax["Solar Radiation"], 0)}
                        </span>
                        <span>W/M²</span>
                      </div>
                    </div>
                  )}

                  {/* Card 8: Rainfall */}
                  {isCardActive("Rainfall") && (
                    <div className="metric-card">
                      <span className="card-title">Rainfall</span>
                      <div className="card-value-box">
                        <span className="card-number" style={{ color: "#22d3ee" }}>
                          {current ? formatVal(current.rainfall, 1) : "--"}
                        </span>
                      </div>
                      <div className="card-footer">
                        <span className="minmax-badge">
                          {formatMinMax(minMax["Rainfall"], 1)}
                        </span>
                        <span>MM</span>
                      </div>
                    </div>
                  )}

                  {/* Card 9: Pressure (IMU) */}
                  {isCardActive("Pressure (IMU)") && (
                    <div className="metric-card">
                      <span className="card-title">Pressure (IMU)</span>
                      <div className="card-value-box">
                        <span className="card-number" style={{ color: "#3b82f6" }}>
                          {current ? formatVal(current.pressure_imu, 1) : "--"}
                        </span>
                      </div>
                      <div className="card-footer">
                        <span className="minmax-badge">
                          {formatMinMax(minMax["Pressure (IMU)"], 1)}
                        </span>
                        <span>hPa</span>
                      </div>
                    </div>
                  )}

                  {/* Card 10: Pressure (hPa) */}
                  {isCardActive("Pressure (hPa)") && (
                    <div className={`metric-card ${analysis.is_anomaly && (analysis.anomaly_type.includes("pressure") || analysis.anomaly_type.includes("bounds") || analysis.anomaly_type.includes("spike") || analysis.anomaly_type.includes("freeze")) ? (useImputed ? "healed-active" : "anomaly-active") : ""}`}>
                      <span className="card-title">Pressure (hPa)</span>
                      <div className="card-value-box" style={{ flexDirection: "column", gap: "2px" }}>
                        <span className="card-number" style={{ color: useImputed && analysis.is_anomaly && analysis.imputed_values?.pressure_hpa !== undefined ? "#22d3ee" : "#8b5cf6" }}>
                          {current ? (useImputed && analysis.is_anomaly && analysis.imputed_values?.pressure_hpa !== undefined ? formatVal(analysis.imputed_values.pressure_hpa, 1) : formatVal(current.pressure_hpa, 1)) : "--"}
                        </span>
                        {useImputed && analysis.is_anomaly && analysis.imputed_values?.pressure_hpa !== undefined && (
                          <span style={{ fontSize: "0.6rem", color: "#22d3ee", fontWeight: "bold" }}>
                            🛡️ HEALED <small style={{ color: "#ef4444", textDecoration: "line-through" }}>({formatVal(current.pressure_hpa, 1)} hPa)</small>
                          </span>
                        )}
                      </div>
                      <div className="card-footer">
                        <span className="minmax-badge">
                          {formatMinMax(minMax["Pressure (hPa)"], 1)}
                        </span>
                        <span>hPa</span>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Right Column: Information Deck */}
              <div className="dashboard-right-deck">
                {/* 1. Alarms & Explainable AI Root Cause */}
                <div className="deck-card">
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span className="deck-title alarm">🚨 EXPLAINABLE AI (XAI) DIAGNOSTICS</span>
                    <span className={`status-tag ${analysis.is_anomaly ? "disconnected" : "connected"}`}>
                      {analysis.is_anomaly ? `CONF: ${analysis.confidence.toFixed(0)}%` : "STATUS: NOMINAL"}
                    </span>
                  </div>
                  
                  <div className={`alarm-textbox ${analysis.is_anomaly ? "alert" : ""}`} style={{ fontSize: "0.72rem", lineHeight: "1.4" }}>
                    <div style={{ fontWeight: "bold", marginBottom: "4px", color: analysis.is_anomaly ? "#ef4444" : "#22c55e" }}>
                      {analysis.is_anomaly ? `🚨 [${analysis.severity.toUpperCase()}] ${analysis.anomaly_type.toUpperCase()} FAULT` : "✅ SYSTEM STATUS: HEALTHY"}
                    </div>
                    {analysis.xai_explanation}
                  </div>

                  {/* SHAP & LIME Explainable AI Breakdown */}
                  {analysis.is_anomaly && (
                    <div style={{ marginTop: "8px", padding: "8px", background: "rgba(0,0,0,0.3)", borderRadius: "4px", border: "1px solid var(--border-soft)" }}>
                      <span style={{ fontSize: "0.65rem", fontWeight: "bold", color: "var(--accent-cyan)", display: "block", marginBottom: "4px" }}>
                        📊 SHAP (KERNEL SHAPLEY) FEATURE ATTRIBUTION:
                      </span>
                      <div style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "0.62rem" }}>
                        <div style={{ display: "flex", justifyContent: "space-between" }}>
                          <span>Temperature (PT100) Attribution:</span>
                          <span style={{ color: "#ef4444", fontWeight: "bold" }}>
                            +{analysis.shap_attributions?.temp_dry ? analysis.shap_attributions.temp_dry.toFixed(1) : "0.0"}%
                          </span>
                        </div>
                        <div style={{ display: "flex", justifyContent: "space-between" }}>
                          <span>Relative Humidity Attribution:</span>
                          <span style={{ color: "#a855f7", fontWeight: "bold" }}>
                            +{analysis.shap_attributions?.humidity ? analysis.shap_attributions.humidity.toFixed(1) : "0.0"}%
                          </span>
                        </div>
                        <div style={{ display: "flex", justifyContent: "space-between" }}>
                          <span>Barometric Pressure Attribution:</span>
                          <span style={{ color: "#3b82f6", fontWeight: "bold" }}>
                            +{analysis.shap_attributions?.pressure_hpa ? analysis.shap_attributions.pressure_hpa.toFixed(1) : "0.0"}%
                          </span>
                        </div>
                      </div>

                      {/* LIME Local Interpretable Model Explanation */}
                      {analysis.lime_local_model && (
                        <div style={{ marginTop: "6px", paddingTop: "6px", borderTop: "1px dashed rgba(255,255,255,0.1)" }}>
                          <span style={{ fontSize: "0.62rem", fontWeight: "bold", color: "#f59e0b", display: "block", marginBottom: "2px" }}>
                            🍋 LIME LOCAL SURROGATE EQUATION:
                          </span>
                          <code style={{ fontSize: "0.58rem", color: "var(--text-muted)", display: "block", wordBreak: "break-all", background: "rgba(0,0,0,0.4)", padding: "4px", borderRadius: "3px" }}>
                            {analysis.lime_local_model}
                          </code>
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* 2. Sensor Health & Maintenance Status */}
                <div className="deck-card">
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span className="deck-title cyan">🩺 SENSOR HEALTH & MAINTENANCE DIAGNOSTICS</span>
                    <span style={{ fontSize: "0.65rem", color: analysis.degradation_risk > 50 ? "#ef4444" : "#22c55e", fontWeight: "bold" }}>
                      RISK: {analysis.degradation_risk ? analysis.degradation_risk.toFixed(0) : 0}%
                    </span>
                  </div>

                  <div style={{ display: "flex", flexDirection: "column", gap: "6px", marginTop: "8px" }}>
                    {[
                      { name: "🌡️ PT100 Temp Transducer", health: analysis.sensor_health?.temp_dry ?? (analysis.is_anomaly && analysis.anomaly_type.includes("temp") ? 72 : 98), key: "temp" },
                      { name: "📊 Barometric Transducer", health: analysis.sensor_health?.pressure_hpa ?? (analysis.is_anomaly && analysis.anomaly_type.includes("pressure") ? 68 : 99), key: "pressure" },
                      { name: "💧 Capacitive Humidity", health: analysis.sensor_health?.humidity ?? (analysis.is_anomaly && analysis.anomaly_type.includes("humidity") ? 75 : 95), key: "humidity" },
                      { name: "💨 Anemometer & Wind Vane", health: 99, key: "wind" },
                      { name: "☀️ Solar Pyranometer", health: 97, key: "solar" },
                      { name: "🌧️ Precipitation Gauge", health: 100, key: "rain" }
                    ].map((s, idx) => {
                      const hVal = Number(s.health);
                      const statusTag = hVal > 85 ? "OPTIMAL" : hVal > 65 ? "DEGRADED" : "CRITICAL";
                      return (
                        <div key={idx} style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
                          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.65rem" }}>
                            <span style={{ color: "var(--text-main)" }}>{s.name}</span>
                            <span style={{ fontWeight: "bold", color: hVal > 85 ? "#22c55e" : hVal > 65 ? "#f59e0b" : "#ef4444" }}>
                              {hVal.toFixed(1)}% ({statusTag})
                            </span>
                          </div>
                          <div style={{ width: "100%", height: "4px", background: "var(--bg-widget)", borderRadius: "2px", overflow: "hidden" }}>
                            <div style={{ width: `${Math.min(100, Math.max(0, hVal))}%`, height: "100%", background: hVal > 85 ? "#22c55e" : hVal > 65 ? "#f59e0b" : "#ef4444" }} />
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  <div style={{ marginTop: "10px", padding: "8px", background: "var(--bg-widget)", borderRadius: "4px", fontSize: "0.68rem", color: "var(--text-main)", borderLeft: "3px solid #22d3ee" }}>
                    <strong>🛠️ Actionable Maintenance Alert:</strong>
                    <div style={{ marginTop: "3px", color: analysis.maintenance_alert?.includes("⚠️") ? "#f59e0b" : "#22c55e" }}>
                      {analysis.maintenance_alert || "✅ OPTIMAL: All channel transducers nominal. Scheduled maintenance valid for 180 days."}
                    </div>
                  </div>
                </div>

                {/* 3. Connection Matrix */}
                <div className="deck-card">
                  <span className="deck-title cyan">🧬 CONNECTION MATRIX</span>
                  <div className="matrix-list">
                    <div className="matrix-row">
                      <span className="matrix-label">Link Source</span>
                      <span className="matrix-value green">{streamSource}</span>
                    </div>
                    <div className="matrix-row">
                      <span className="matrix-label">Self-Healing</span>
                      <span className={`matrix-value ${useImputed ? "green" : "red"}`}>
                        {useImputed ? "🛡️ ACTIVE (Auto-Impute)" : "OFF (Raw Feed)"}
                      </span>
                    </div>
                    <div className="matrix-row">
                      <span className="matrix-label">UDP LAN Port</span>
                      <span className="matrix-value">0.0.0.0:5000</span>
                    </div>
                    <div className="matrix-row">
                      <span className="matrix-label">TCP LAN Port</span>
                      <span className="matrix-value">0.0.0.0:5001</span>
                    </div>
                    <div className="matrix-row">
                      <span className="matrix-label">Packets Parsed</span>
                      <span className="matrix-value">{metrics.received}</span>
                    </div>
                    <div className="matrix-row">
                      <span className="matrix-label">Dropped / Anomaly</span>
                      <span className="matrix-value">{metrics.dropped}</span>
                    </div>
                    <div className="matrix-row">
                      <span className="matrix-label">System Health</span>
                      <span className={`matrix-value ${analysis.is_anomaly ? (useImputed ? "green" : "red") : "green"}`}>
                        {analysis.is_anomaly ? (useImputed ? "HEALED (AUTONOMOUS)" : "DEGRADED") : "NOMINAL"}
                      </span>
                    </div>
                  </div>
                </div>

                {/* 4. Date & Time */}
                <div className="deck-card">
                  <span className="deck-title cyan">🌐 DATE & TIME</span>
                  <div className="matrix-list">
                    <div className="matrix-row">
                      <span className="matrix-label">Date:</span>
                      <span className="matrix-value">{dateStr}</span>
                    </div>
                    <div className="matrix-row">
                      <span className="matrix-label">Time:</span>
                      <span className="matrix-value">{timeStr}</span>
                    </div>
                  </div>
                </div>

                {/* 5. Quick Actions */}
                <div className="deck-card">
                  <span className="deck-title cyan">⚡ QUICK ACTIONS</span>
                  <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                    <button onClick={handleExportCSV} className="quick-btn">
                      <Download size={13} /> Export Log Now (.CSV)
                    </button>
                    <button
                      onClick={() => {
                        setTelemetryHistory([]);
                        setMetrics({ received: 0, dropped: 0 });
                      }}
                      className="quick-btn"
                    >
                      <RefreshCw size={13} /> Clear Cached Logs
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* 1.5 MULTI-AWS SPATIAL ANALYSIS NETWORK GRID */}
          {activeTab === "spatial_grid" && (
            <div className="panel-card" style={{ gap: "16px" }}>
              <div className="section-header">
                <span className="section-title">🌐 MULTI-AWS SPATIAL ANALYSIS & NEIGHBOR COMPARISON GRID</span>
                <span className="section-subtitle">Real-time cross-station spatial correlation & outlier detection across station cluster</span>
              </div>

              {/* Top Summary Banner */}
              <div className="deck-card" style={{ background: "var(--bg-widget)", border: "1px solid var(--border-color)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "10px" }}>
                  <div>
                    <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>SPATIAL NETWORK CLUSTER: </span>
                    <span style={{ fontWeight: "bold", color: "#22d3ee", marginLeft: "6px" }}>4 STATIONS (AWS-01, AWS-02, AWS-03, AWS-04)</span>
                  </div>
                  <div>
                    <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>NEIGHBOR CONSENSUS AVG: </span>
                    <span style={{ fontWeight: "bold", color: "#22c55e", marginLeft: "6px" }}>
                      {analysis.spatial_neighbor_avg ? formatVal(analysis.spatial_neighbor_avg) + "°C" : "31.0°C"}
                    </span>
                  </div>
                  <div>
                    <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>SPATIAL CONSENSUS STATUS: </span>
                    <span className={`matrix-value ${analysis.is_spatial_anomaly ? "red" : "green"}`} style={{ marginLeft: "6px", padding: "3px 8px", borderRadius: "4px", background: analysis.is_spatial_anomaly ? "var(--red-soft)" : "var(--green-soft)" }}>
                      {analysis.is_spatial_anomaly ? "🚨 SPATIAL OUTLIER DETECTED" : "✅ CONSENSUS NOMINAL"}
                    </span>
                  </div>
                </div>
              </div>

              {/* 4 Station Cluster Cards */}
              <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "14px" }}>
                {[
                  { id: "AWS-01", name: "AWS-01 (Primary Station)", role: "Target Station", isTarget: true },
                  { id: "AWS-02", name: "AWS-02 (North Neighbor)", role: "Spatial Neighbor", isTarget: false },
                  { id: "AWS-03", name: "AWS-03 (East Neighbor)", role: "Spatial Neighbor", isTarget: false },
                  { id: "AWS-04", name: "AWS-04 (South Neighbor)", role: "Spatial Neighbor", isTarget: false },
                ].map((st) => {
                  const netData = analysis.spatial_network && analysis.spatial_network[st.id] ? analysis.spatial_network[st.id] : { temp_dry: st.isTarget ? (current ? current.dry_bulb_temp : 31.0) : 31.0, humidity: 65.0, pressure_hpa: 1013.2 };
                  const isAnom = st.isTarget && analysis.is_spatial_anomaly;

                  return (
                    <div
                      key={st.id}
                      className="metric-card"
                      style={{
                        border: `1.5px solid ${isAnom ? "#f43f5e" : (st.isTarget ? "#22d3ee" : "var(--border-color)")}`,
                        background: isAnom ? "var(--red-soft)" : "var(--bg-card)",
                        boxShadow: isAnom ? "0 0 12px rgba(244, 63, 94, 0.3)" : "none"
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <span className="card-title" style={{ color: isAnom ? "#f43f5e" : (st.isTarget ? "#22d3ee" : "var(--text-main)") }}>
                          {st.name}
                        </span>
                        <span className={`matrix-value ${isAnom ? "red" : "green"}`} style={{ fontSize: "0.65rem" }}>
                          {isAnom ? "🚨 OUTLIER" : "● ONLINE"}
                        </span>
                      </div>

                      <div style={{ margin: "12px 0", display: "flex", flexDirection: "column", gap: "6px" }}>
                        <div style={{ display: "flex", justifyContent: "space-between" }}>
                          <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Dry Temp:</span>
                          <span style={{ fontWeight: "bold", fontSize: "1.1rem", color: isAnom ? "#f43f5e" : "#ef4444" }}>
                            {formatVal(netData.temp_dry)}°C
                          </span>
                        </div>
                        <div style={{ display: "flex", justifyContent: "space-between" }}>
                          <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Pressure:</span>
                          <span style={{ fontWeight: "bold", fontSize: "0.85rem", color: "#8b5cf6" }}>
                            {formatVal(netData.pressure_hpa)} hPa
                          </span>
                        </div>
                        <div style={{ display: "flex", justifyContent: "space-between" }}>
                          <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Humidity:</span>
                          <span style={{ fontWeight: "bold", fontSize: "0.85rem", color: "#a855f7" }}>
                            {formatVal(netData.humidity)}%
                          </span>
                        </div>
                      </div>

                      <div className="card-footer" style={{ borderTop: "1px solid var(--border-color)", paddingTop: "6px" }}>
                        <span style={{ fontSize: "0.65rem", color: "var(--text-dim)" }}>Role: {st.role}</span>
                        {st.isTarget && analysis.spatial_delta > 0 && (
                          <span style={{ fontSize: "0.65rem", fontWeight: "bold", color: isAnom ? "#f43f5e" : "#22c55e" }}>
                            Δ Spatial: {formatVal(analysis.spatial_delta)}°C
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Spatial XAI Reasoning Card */}
              <div className="deck-card">
                <span className="deck-title cyan">🧠 SPATIAL EXPLAINABLE AI (XAI) DIAGNOSTICS</span>
                <p style={{ fontSize: "0.8rem", color: "var(--text-main)", lineHeight: "1.5", marginTop: "8px", background: "var(--bg-widget)", padding: "10px", borderRadius: "6px", fontFamily: "monospace" }}>
                  {analysis.is_spatial_anomaly
                    ? analysis.xai_explanation
                    : `✅ SPATIAL CONSENSUS CONFIRMED: Target station AWS-01 (${formatVal(current ? current.dry_bulb_temp : 31)}°C) matches spatial neighbor cluster average (${formatVal(analysis.spatial_neighbor_avg || 31)}°C). No sensor anomaly detected.`}
                </p>
              </div>

              {/* Live Spatial Testbench Controls */}
              <div className="deck-card">
                <span className="deck-title cyan">⚡ SPATIAL ANOMALY FAULT INJECTOR</span>
                <p style={{ fontSize: "0.72rem", color: "var(--text-muted)", marginBottom: "10px" }}>
                  Test the spatial analysis engine by injecting a single-station glitch or a wide-area genuine meteorological event.
                </p>

                <div className="bench-grid">
                  <button
                    onClick={() => injectSpatialFault("AWS-01", 55.0)}
                    className="btn-bench red"
                  >
                    ⚡ INJECT AWS-01 SPATIAL GLITCH (55°C vs 31°C Neighbors)
                  </button>

                  <button
                    onClick={() => resetFault()}
                    className="btn-bench green"
                  >
                    🔄 RESET ALL STATIONS TO CONSENSUS NOMINAL (~31°C)
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* 2. LIVE TELEMETRY PLOTS */}
          {activeTab === "live_graph" && (
            <div className="panel-card">
              <div className="section-header">
                <span className="section-title">📈 REAL-TIME TIME-SERIES SPECTRAL CHARTS</span>
                <span className="section-subtitle">Visualizing live multi-channel sensor feeds {useImputed ? "(🛡️ Displaying AI-Healed Inferred Telemetry)" : "(Raw Telemetry)"}</span>
              </div>

              <div style={{ flex: 1, minHeight: "450px" }}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={telemetryHistory}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#2e2e35" />
                    <XAxis dataKey="time" stroke="#9d9da8" fontSize={10} />
                    <YAxis stroke="#9d9da8" fontSize={10} />
                    <Tooltip
                      contentStyle={{ backgroundColor: "#16161a", borderColor: "#2e2e35", color: "#fff", fontSize: "0.75rem" }}
                    />
                    <Legend wrapperStyle={{ fontSize: "0.75rem", paddingTop: "10px" }} />
                    <Line type="monotone" name="Dry Temp (°C)" dataKey="dry_temp" stroke="#ef4444" strokeWidth={2} dot={false} />
                    <Line type="monotone" name="Wet Temp (°C)" dataKey="wet_temp" stroke="#ec4899" strokeWidth={2} dot={false} />
                    <Line type="monotone" name="Rel. Humidity (%)" dataKey="humidity" stroke="#a855f7" strokeWidth={2} dot={false} />
                    <Line type="monotone" name="Pressure (hPa)" dataKey="pressure" stroke="#3b82f6" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* 3. PARAMETER EDITOR */}
          {activeTab === "frame_editor" && (
            <div className="panel-card">
              <div className="section-header">
                <span className="section-title">⚙️ PACKET DECODER SCHEMATIC MATRIX</span>
                <span className="section-subtitle">Manage binary schema, calibrations, and thresholds</span>
              </div>

              <div className="table-container">
                <table className="aws-table">
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Parameter Name</th>
                      <th>Binary Type</th>
                      <th>Unit</th>
                      <th>Scale</th>
                      <th>Offset</th>
                      <th>Display Mode</th>
                      <th>Alarm Threshold</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {DEFAULT_PARAMS.map(p => (
                      <tr key={p.id}>
                        <td>{p.id}</td>
                        <td style={{ fontWeight: "bold", color: p.color }}>{p.name}</td>
                        <td>{p.dataType}</td>
                        <td>{p.unit || "--"}</td>
                        <td>{p.scale}</td>
                        <td>{p.offset}</td>
                        <td>{p.mode}</td>
                        <td>{p.threshold !== null ? `${p.threshold} ${p.unit}` : "DISABLED"}</td>
                        <td style={{ color: "#22c55e", fontWeight: "bold" }}>ENABLED</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* 4. LOCAL DATA LOGGER */}
          {activeTab === "data_logger" && (
            <div className="panel-card">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div className="section-header">
                  <span className="section-title">📁 LOCAL SESSION DATA LOGGER</span>
                  <span className="section-subtitle">Logged {telemetryHistory.length} frame records {useImputed ? "(🛡️ Self-Healing Imputation Mode: ACTIVE)" : "(Raw Telemetry Mode)"}</span>
                </div>

                <div style={{ display: "flex", gap: "8px" }}>
                  <button onClick={handleExportCSV} className="btn-action btn-stream-start">
                    <Download size={12} /> EXPORT CSV
                  </button>
                  <button
                    onClick={() => { setTelemetryHistory([]); setMetrics({ received: 0, dropped: 0 }); }}
                    className="btn-action btn-stream-stop"
                  >
                    <RefreshCw size={12} /> PURGE
                  </button>
                </div>
              </div>

              <div className="table-container">
                <table className="aws-table">
                  <thead>
                    <tr>
                      <th>Index</th>
                      <th>Time</th>
                      <th>Dry Temp (°C)</th>
                      <th>Wet Temp (°C)</th>
                      <th>Rel. Humidity (%)</th>
                      <th>Pressure (hPa)</th>
                      <th>Speed (M/S)</th>
                      <th>Direction (DEG)</th>
                      <th>Solar (W/M²)</th>
                      <th>Rain (MM)</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {telemetryHistory.length === 0 ? (
                      <tr>
                        <td colSpan={11} style={{ textAlign: "center", padding: "30px", color: "#9d9da8" }}>
                          No records cached. Stream is active.
                        </td>
                      </tr>
                    ) : (
                      [...telemetryHistory].reverse().map((row, idx) => (
                        <tr key={idx} className={row.is_anomaly ? (useImputed ? "healed-row" : "anomaly-row") : ""}>
                          <td>#{telemetryHistory.length - idx}</td>
                          <td>{row.time}</td>
                          <td>
                            {useImputed && row.is_anomaly && row.imputed_values?.temp_dry !== undefined ? (
                              <span style={{ color: "#22d3ee", fontWeight: "bold" }}>
                                {formatVal(row.imputed_values.temp_dry, 1)} <small style={{ color: "#ef4444", textDecoration: "line-through" }}>({formatVal(row.raw.dry_bulb_temp, 1)})</small>
                              </span>
                            ) : (
                              formatVal(row.raw.dry_bulb_temp, 1)
                            )}
                          </td>
                          <td>{formatVal(row.raw.wet_bulb_temp, 1)}</td>
                          <td>
                            {useImputed && row.is_anomaly && row.imputed_values?.humidity !== undefined ? (
                              <span style={{ color: "#22d3ee", fontWeight: "bold" }}>
                                {formatVal(row.imputed_values.humidity, 1)} <small style={{ color: "#ef4444", textDecoration: "line-through" }}>({formatVal(row.raw.rel_humidity, 1)})</small>
                              </span>
                            ) : (
                              formatVal(row.raw.rel_humidity, 1)
                            )}
                          </td>
                          <td>
                            {useImputed && row.is_anomaly && row.imputed_values?.pressure_hpa !== undefined ? (
                              <span style={{ color: "#22d3ee", fontWeight: "bold" }}>
                                {formatVal(row.imputed_values.pressure_hpa, 1)} <small style={{ color: "#ef4444", textDecoration: "line-through" }}>({formatVal(row.raw.pressure_hpa, 1)})</small>
                              </span>
                            ) : (
                              formatVal(row.raw.pressure_hpa, 1)
                            )}
                          </td>
                          <td>{formatVal(row.raw.speed, 1)}</td>
                          <td>{formatVal(row.raw.direction, 0, true)}°</td>
                          <td>{formatVal(row.raw.solar_radiation, 0)}</td>
                          <td>{formatVal(row.raw.rainfall, 1)}</td>
                          <td style={{ fontWeight: "bold" }}>
                            {row.is_anomaly ? (
                              useImputed ? (
                                <span style={{ color: "#22d3ee" }}>🛡️ HEALED ({row.anomaly_type.toUpperCase()})</span>
                              ) : (
                                <span style={{ color: "#ef4444" }}>🚨 {row.anomaly_type.toUpperCase()}</span>
                              )
                            ) : (
                              <span style={{ color: "#22c55e" }}>✅ NOMINAL</span>
                            )}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* 5. HISTORY REPLAY HUB & TESTBENCH */}
          {activeTab === "replay_session" && (
            <div className="panel-card">
              <div className="section-header">
                <span className="section-title">🔄 HISTORY REPLAY & SKYGUARD AI TESTBENCH</span>
                <span className="section-subtitle">Simulate real-time faults, spikes, drifts, and outages</span>
              </div>

              <div className="deck-card" style={{ marginTop: "10px" }}>
                <span className="deck-title cyan">⚡ REAL-TIME AI ANOMALY INJECTION TESTBENCH</span>
                <p style={{ fontSize: "0.72rem", color: "var(--text-muted)", lineHeight: "1.4" }}>
                  Click any trigger below to inject synthetic anomalies into the Go telemetry stream. The SkyGuard AI engine will instantly classify the fault, output XAI diagnostics to the alert deck, and calculate self-healed values!
                </p>

                <div className="bench-grid">
                  <button
                    onClick={() => injectFault("spike", "temp_dry", 25.0)}
                    className="btn-bench red"
                  >
                    ⚡ INJECT TEMP SPIKE (+25°C)
                  </button>

                  <button
                    onClick={() => injectFault("freeze", "pressure_hpa", 0)}
                    className="btn-bench amber"
                  >
                    ❄️ INJECT PRESSURE FREEZE
                  </button>

                  <button
                    onClick={() => injectFault("drift", "humidity", -2.5)}
                    className="btn-bench amber"
                  >
                    📉 INJECT HUMIDITY DRIFT
                  </button>

                  <button
                    onClick={() => injectFault("outage", "", 0)}
                    className="btn-bench red"
                  >
                    🔌 SIMULATE PACKET LOSS OUTAGE
                  </button>

                  <button
                    onClick={() => injectFault("spike", "humidity", -70.0)}
                    className="btn-bench red"
                  >
                    ⚠️ INJECT PSYCHROMETRIC CONFLICT
                  </button>

                  <button
                    onClick={() => injectSpatialFault("AWS-01", 55.0)}
                    className="btn-bench red"
                    style={{ gridColumn: "span 2", fontWeight: "bold" }}
                  >
                    🌐 INJECT MULTI-AWS SPATIAL ANOMALY (AWS-01: 55°C vs Neighbors: ~31°C)
                  </button>

                  <button
                    onClick={resetFault}
                    className="btn-bench green"
                  >
                    🔄 RESET TO NOMINAL
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* 6. SYSTEM EXPORT CENTER */}
          {activeTab === "export_option" && (
            <div className="panel-card">
              <div className="section-header">
                <span className="section-title">💾 SYSTEM EXPORT CENTER</span>
                <span className="section-subtitle">Export telemetry session data and decoder configurations</span>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "16px", marginTop: "10px" }}>
                <div className="deck-card">
                  <span className="deck-title green">📥 Export Telemetry (.CSV)</span>
                  <p style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>
                    Download all captured frame logs, sensor readings, and anomaly tags as a CSV document.
                  </p>
                  <button onClick={handleExportCSV} className="btn-action btn-stream-start" style={{ marginTop: "10px" }}>
                    <Download size={12} /> DOWNLOAD CSV
                  </button>
                </div>

                <div className="deck-card">
                  <span className="deck-title cyan">📄 Export Frame Config (.JSON)</span>
                  <p style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>
                    Save the active parameter decoder schema, byte offsets, and scales as a reusable JSON file.
                  </p>
                  <button
                    onClick={() => {
                      const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(DEFAULT_PARAMS, null, 2));
                      const a = document.createElement("a");
                      a.href = dataStr;
                      a.download = "aws_frame_config.json";
                      a.click();
                    }}
                    className="btn-action"
                    style={{ marginTop: "10px" }}
                  >
                    <FileText size={12} /> DOWNLOAD JSON
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* 7. CONNECTION LINKS */}
          {activeTab === "link_config" && (
            <div className="panel-card" style={{ gap: "20px" }}>
              <div className="section-header">
                <span className="section-title">🛠️ TELEMETRY NETWORK SOCKET CONFIGURATION</span>
                <span className="section-subtitle">Configure LAN Cable IP, Port, and Protocol bindings in real time</span>
              </div>

              {/* Protocol Selector Tabs */}
              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "12px" }}>
                {[
                  { id: "UDP", title: "📡 UDP Datagram Socket", desc: "Low-latency hardware telemetry over LAN cable. Target port for AWS dataloggers." },
                  { id: "TCP", title: "🔌 TCP Stream Socket", desc: "Reliable, connection-oriented stream for remote IP telemetry links." },
                  { id: "SIMULATOR", title: "🔄 Auto-Failover Simulator", desc: "Synthetic dataset loop with real-time AI fault injection support." }
                ].map(p => (
                  <div
                    key={p.id}
                    onClick={() => handleSelectProtocol(p.id)}
                    style={{
                      padding: "14px",
                      background: linkProtocol === p.id ? "var(--bg-widget)" : "var(--bg-card)",
                      border: `1px solid ${linkProtocol === p.id ? "var(--accent-cyan)" : "var(--border-color)"}`,
                      borderRadius: "6px",
                      cursor: "pointer",
                      transition: "all 0.15s ease"
                    }}
                  >
                    <div style={{ fontWeight: "bold", fontSize: "0.8rem", color: linkProtocol === p.id ? "var(--accent-cyan)" : "var(--text-main)" }}>
                      {p.title}
                    </div>
                    <div style={{ fontSize: "0.68rem", color: "var(--text-muted)", marginTop: "4px" }}>
                      {p.desc}
                    </div>
                  </div>
                ))}
              </div>

              {/* Connection Parameters Form */}
              <div className="deck-card" style={{ padding: "18px" }}>
                <span className="deck-title cyan">⚙️ SOCKET & PORT CONFIGURATION PARAMETERS</span>
                
                <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "14px", marginTop: "12px" }}>
                  {/* Host Binding */}
                  <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                    <label style={{ fontSize: "0.7rem", color: "var(--text-muted)", fontWeight: "bold" }}>INGESTION HOST IP</label>
                    <input
                      type="text"
                      value={linkHost}
                      onChange={e => setLinkHost(e.target.value)}
                      style={{
                        background: "var(--bg-main)",
                        border: "1px solid var(--border-color)",
                        borderRadius: "4px",
                        padding: "8px 10px",
                        color: "var(--text-main)",
                        fontFamily: "inherit",
                        fontSize: "0.75rem"
                      }}
                    />
                    <span style={{ fontSize: "0.62rem", color: "var(--text-dim)" }}>Use 0.0.0.0 for all LAN interfaces</span>
                  </div>

                  {/* Port Number */}
                  <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                    <label style={{ fontSize: "0.7rem", color: "var(--text-muted)", fontWeight: "bold" }}>NETWORK PORT NUMBER</label>
                    <input
                      type="number"
                      value={linkPort}
                      onChange={e => setLinkPort(e.target.value)}
                      style={{
                        background: "var(--bg-main)",
                        border: "1px solid var(--border-color)",
                        borderRadius: "4px",
                        padding: "8px 10px",
                        color: "var(--accent-cyan)",
                        fontWeight: "bold",
                        fontFamily: "inherit",
                        fontSize: "0.75rem"
                      }}
                    />
                    <span style={{ fontSize: "0.62rem", color: "var(--text-dim)" }}>Default: 5000 (UDP) / 5001 (TCP)</span>
                  </div>

                  {/* Protocol */}
                  <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                    <label style={{ fontSize: "0.7rem", color: "var(--text-muted)", fontWeight: "bold" }}>TRANSPORT PROTOCOL</label>
                    <select
                      value={linkProtocol}
                      onChange={e => setLinkProtocol(e.target.value)}
                      style={{
                        background: "var(--bg-main)",
                        border: "1px solid var(--border-color)",
                        borderRadius: "4px",
                        padding: "8px 10px",
                        color: "var(--text-main)",
                        fontFamily: "inherit",
                        fontSize: "0.75rem"
                      }}
                    >
                      <option value="UDP">UDP Datagram</option>
                      <option value="TCP">TCP Stream</option>
                      <option value="SIMULATOR">Simulator Fallback</option>
                    </select>
                    <span style={{ fontSize: "0.62rem", color: "var(--text-dim)" }}>Socket Transport Layer</span>
                  </div>

                  {/* Payload Format */}
                  <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                    <label style={{ fontSize: "0.7rem", color: "var(--text-muted)", fontWeight: "bold" }}>PAYLOAD AUTO-DECODER</label>
                    <select
                      value={linkFormat}
                      onChange={e => setLinkFormat(e.target.value)}
                      style={{
                        background: "var(--bg-main)",
                        border: "1px solid var(--border-color)",
                        borderRadius: "4px",
                        padding: "8px 10px",
                        color: "var(--text-main)",
                        fontFamily: "inherit",
                        fontSize: "0.75rem"
                      }}
                    >
                      <option value="AUTO">AUTO-DETECT (Binary/CSV/JSON)</option>
                      <option value="BINARY">BINARY AWS (0xAA 0x55)</option>
                      <option value="CSV">CSV TEXT STREAM</option>
                      <option value="JSON">JSON OBJECT</option>
                    </select>
                    <span style={{ fontSize: "0.62rem", color: "var(--text-dim)" }}>Zero-overhead frame decoder</span>
                  </div>
                </div>

                {/* Action Buttons */}
                <div style={{ display: "flex", alignItems: "center", gap: "10px", marginTop: "16px" }}>
                  <button
                    onClick={handleApplyLinkConfig}
                    className="btn-action btn-stream-start"
                    style={{ padding: "9px 18px", fontSize: "0.75rem" }}
                  >
                    💾 APPLY & REBIND PORT
                  </button>

                  <button
                    onClick={fetchLinkStats}
                    className="btn-action"
                    style={{ padding: "9px 18px", fontSize: "0.75rem" }}
                  >
                    🔄 REFRESH SOCKET STATUS
                  </button>

                  {linkStatusMsg && (
                    <span style={{ fontSize: "0.75rem", fontWeight: "bold", color: linkStatusMsg.includes("✅") ? "var(--accent-green)" : "var(--accent-red)" }}>
                      {linkStatusMsg}
                    </span>
                  )}
                </div>
              </div>

              {/* Real LAN Cable Testing Box */}
              <div className="deck-card" style={{ padding: "16px" }}>
                <span className="deck-title green">🌐 SEND LIVE DATA OVER LAN CABLE</span>
                <p style={{ fontSize: "0.72rem", color: "var(--text-muted)", lineHeight: "1.4" }}>
                  To feed live sensor data through an Ethernet LAN cable to this station, send packets to <strong style={{ color: "var(--accent-cyan)" }}>{linkHost}:{linkPort} ({linkProtocol})</strong>:
                </p>

                <div style={{ background: "var(--bg-main)", padding: "10px 14px", borderRadius: "4px", marginTop: "8px", border: "1px solid var(--border-soft)", fontSize: "0.7rem", color: "var(--accent-green)" }}>
                  <code>
                    # PowerShell UDP LAN Test Command:<br />
                    $u = New-Object System.Net.Sockets.UdpClient; $u.Connect(&quot;127.0.0.1&quot;, {linkPort}); $b = [Text.Encoding]::ASCII.GetBytes(&quot;26.5,19.8,62.1,1013.25,4.2,180&quot;); $u.Send($b, $b.Length); $u.Close()
                  </code>
                </div>
              </div>
            </div>
          )}

        </main>
      </div>

      {/* ─── FOOTER ─── */}
      <footer className="app-footer">
        <div className="footer-left">
          <span style={{ color: isConnected ? "var(--accent-amber)" : "var(--accent-red)" }}>
            ■ {isConnected ? "SYSTEM READY" : "INGESTION CHANNEL OFFLINE"}
          </span>
          <span>PACKETS: {metrics.received} RECORDS CAPTURED</span>
          <span>DROPPED: {metrics.dropped}</span>
        </div>

        <div>
          <span>Ground Terminal v2.0 | Next.js + Go Lang | SkyGuard AI</span>
        </div>
      </footer>
    </div>
  );
}
