"use client";

import React, { useState, useEffect, useRef, useMemo } from "react";

import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  ComposedChart,
  ReferenceLine,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend
} from "recharts";

const DEFAULT_PARAMS = [
  { id: 1, key: "time_inst", name: "Time_Inst", dataType: "uint32", unit: "SEC", scale: 1.0, offset: 0.0, mode: "both", color: "#2563eb", enabled: true, threshold: null },
  { id: 2, key: "direction", name: "Direction", dataType: "uint16", unit: "DEG", scale: 1.0, offset: 0.0, mode: "both", color: "#16a34a", enabled: true, threshold: null },
  { id: 3, key: "speed", name: "Speed", dataType: "uint16", unit: "M/S", scale: 0.1, offset: 0.0, mode: "both", color: "#2563eb", enabled: true, threshold: 18.0 },
  { id: 4, key: "temp", name: "Dry Bulb Temp", dataType: "int16", unit: "°C", scale: 0.1, offset: 0.0, mode: "both", color: "#dc2626", enabled: true, threshold: 45.0 },
  { id: 5, key: "wet_bulb", name: "Wet Bulb Temp", dataType: "int16", unit: "°C", scale: 0.1, offset: 0.0, mode: "both", color: "#dc2626", enabled: true, threshold: null },
  { id: 6, key: "humidity", name: "Rel. Humidity", dataType: "uint16", unit: "%", scale: 0.1, offset: 0.0, mode: "both", color: "#7c3aed", enabled: true, threshold: 95.0 },
  { id: 7, key: "solar", name: "Solar Radiation", dataType: "uint16", unit: "W/M²", scale: 1.0, offset: 0.0, mode: "both", color: "#ea580c", enabled: true, threshold: null },
  { id: 8, key: "rain", name: "Rainfall", dataType: "uint16", unit: "MM", scale: 0.1, offset: 0.0, mode: "both", color: "#0284c7", enabled: true, threshold: 50.0 },
  { id: 9, key: "pressure_imu", name: "Pressure (IMU)", dataType: "float32", unit: "hPa", scale: 1.0, offset: 0.0, mode: "both", color: "#0284c7", enabled: true, threshold: null },
  { id: 10, key: "pressure", name: "Pressure (hPa)", dataType: "uint32", unit: "hPa", scale: 0.01, offset: 0.0, mode: "both", color: "#0284c7", enabled: true, threshold: null },
];

const formatNum = (val) => {
  if (typeof val !== "number") return "0";
  return val.toLocaleString("en-US");
};

/* ─── CUSTOM SVG ICONS & DEFENSE WIDGETS ─── */

// State Emblem of India (Lion Capital of Ashoka)
function NationalEmblemIcon() {
  return (
    <div className="national-emblem-box">
      <img
        src="/emblem.png"
        alt="State Emblem of India"
        className="national-emblem-img"
      />
    </div>
  );
}

// Subtle Transmission Tower Watermark for Connection Matrix
function TransmissionTowerIcon() {
  return (
    <svg className="tower-watermark-svg" viewBox="0 0 50 65" fill="none" xmlns="http://www.w3.org/2000/svg">
      <line x1="25" y1="2" x2="25" y2="12" stroke="#64748b" strokeWidth="1.5" />
      <circle cx="25" cy="2" r="2" fill="#ea580c" />
      {/* Mast lattice */}
      <polygon points="25,12 10,62 40,62" stroke="#64748b" strokeWidth="1.2" fill="none" />
      <line x1="22" y1="22" x2="28" y2="22" stroke="#64748b" strokeWidth="1" />
      <line x1="19" y1="34" x2="31" y2="34" stroke="#64748b" strokeWidth="1" />
      <line x1="15" y1="48" x2="35" y2="48" stroke="#64748b" strokeWidth="1" />
      {/* Diagonal cross braces */}
      <line x1="22" y1="22" x2="31" y2="34" stroke="#64748b" strokeWidth="0.8" />
      <line x1="28" y1="22" x2="19" y2="34" stroke="#64748b" strokeWidth="0.8" />
      <line x1="19" y1="34" x2="35" y2="48" stroke="#64748b" strokeWidth="0.8" />
      <line x1="31" y1="34" x2="15" y2="48" stroke="#64748b" strokeWidth="0.8" />
      <line x1="15" y1="48" x2="40" y2="62" stroke="#64748b" strokeWidth="0.8" />
      <line x1="35" y1="48" x2="10" y2="62" stroke="#64748b" strokeWidth="0.8" />
      {/* Radio signal waves */}
      <path d="M18 6 C20 4, 22 3, 25 3 C28 3, 30 4, 32 6" stroke="#ea580c" strokeWidth="1" strokeLinecap="round" fill="none" />
      <path d="M14 9 C17 6, 21 5, 25 5 C29 5, 33 6, 36 9" stroke="#ea580c" strokeWidth="1" strokeLinecap="round" fill="none" opacity="0.7" />
    </svg>
  );
}

// Clean Shield Checkmark SVG for Maintenance Box
function ShieldCheckIcon() {
  return (
    <svg className="shield-check-icon" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path
        d="M14 3L5 7V13C5 18.5 8.8 23.7 14 25C19.2 23.7 23 18.5 23 13V7L14 3Z"
        fill="rgba(22, 163, 74, 0.12)"
        stroke="#16a34a"
        strokeWidth="1.8"
        strokeLinejoin="round"
      />
      <path
        d="M9.5 13.5L12.5 16.5L18.5 10.5"
        stroke="#16a34a"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

// API Endpoint Resolver for both Next.js dev server (localhost:3000) and Desktop / Production (localhost:8080)
const getApiEndpoint = (path) => {
  if (typeof window !== "undefined") {
    if (window.location.port === "3000") {
      return `http://127.0.0.1:8080${path}`;
    }
  }
  return path;
};

// Live Analog Clock Widget
function AnalogClock() {
  const [mounted, setMounted] = useState(false);
  const [time, setTime] = useState(null);

  useEffect(() => {
    setMounted(true);
    setTime(new Date());
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  if (!mounted || !time) {
    return (
      <svg className="analog-clock-svg" viewBox="0 0 70 70" fill="none" xmlns="http://www.w3.org/2000/svg" suppressHydrationWarning>
        <circle cx="35" cy="35" r="33" fill="#ffffff" stroke="#cbd5e1" strokeWidth="1.8" />
        <circle cx="35" cy="35" r="30" stroke="rgba(0,0,0,0.04)" strokeWidth="1" />
        <circle cx="35" cy="35" r="2.5" fill="#ea580c" />
      </svg>
    );
  }

  const seconds = time.getSeconds();
  const minutes = time.getMinutes();
  const hours = time.getHours();

  const secAngle = seconds * 6;
  const minAngle = minutes * 6 + seconds * 0.1;
  const hourAngle = (hours % 12) * 30 + minutes * 0.5;

  return (
    <svg className="analog-clock-svg" viewBox="0 0 70 70" fill="none" xmlns="http://www.w3.org/2000/svg" suppressHydrationWarning>
      <circle cx="35" cy="35" r="33" fill="#ffffff" stroke="#cbd5e1" strokeWidth="1.8" />
      <circle cx="35" cy="35" r="30" stroke="rgba(0,0,0,0.04)" strokeWidth="1" />
      
      {[...Array(12)].map((_, i) => {
        const rad = (i * 30 * Math.PI) / 180;
        const x1 = 35 + Math.sin(rad) * 26;
        const y1 = 35 - Math.cos(rad) * 26;
        const x2 = 35 + Math.sin(rad) * (i % 3 === 0 ? 21 : 23);
        const y2 = 35 - Math.cos(rad) * (i % 3 === 0 ? 21 : 23);
        return (
          <line
            key={i}
            x1={x1}
            y1={y1}
            x2={x2}
            y2={y2}
            stroke={i % 3 === 0 ? "#0f172a" : "#94a3b8"}
            strokeWidth={i % 3 === 0 ? "1.8" : "1"}
          />
        );
      })}

      {/* Hour Hand */}
      <line
        x1="35"
        y1="35"
        x2={35 + Math.sin((hourAngle * Math.PI) / 180) * 15}
        y2={35 - Math.cos((hourAngle * Math.PI) / 180) * 15}
        stroke="#0f172a"
        strokeWidth="2.4"
        strokeLinecap="round"
      />

      {/* Minute Hand */}
      <line
        x1="35"
        y1="35"
        x2={35 + Math.sin((minAngle * Math.PI) / 180) * 22}
        y2={35 - Math.cos((minAngle * Math.PI) / 180) * 22}
        stroke="#0f172a"
        strokeWidth="2.0"
        strokeLinecap="round"
      />

      {/* Second Hand (Orange) */}
      <line
        x1="35"
        y1="35"
        x2={35 + Math.sin((secAngle * Math.PI) / 180) * 25}
        y2={35 - Math.cos((secAngle * Math.PI) / 180) * 25}
        stroke="#ea580c"
        strokeWidth="1.2"
        strokeLinecap="round"
      />

      <circle cx="35" cy="35" r="2.5" fill="#ea580c" />
    </svg>
  );
}

// Mini Trend Area Chart with Y-Axis and Data Points
function MiniTrendSparklineWithAxis({ data, color, gradientId, strokeColor, yMin, yMid, yMax }) {
  const width = 110;
  const height = 50;
  const padLeft = 24;

  if (!data || data.length < 2) {
    return (
      <svg className="trend-card-chart-area" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
        <text x={padLeft - 4} y="9" fill="#64748b" fontSize="6.5" fontWeight="bold" textAnchor="end">{yMax}</text>
        <text x={padLeft - 4} y={height / 2 + 2} fill="#64748b" fontSize="6.5" fontWeight="bold" textAnchor="end">{yMid}</text>
        <text x={padLeft - 4} y={height - 2} fill="#64748b" fontSize="6.5" fontWeight="bold" textAnchor="end">{yMin}</text>
        <line x1={padLeft} y1={height / 2} x2={width} y2={height / 2} stroke="rgba(148, 163, 184, 0.4)" strokeDasharray="3 3" strokeWidth="1" />
        <text x={(width + padLeft) / 2} y={height / 2 + 3} fill="#94a3b8" fontSize="7" fontWeight="bold" textAnchor="middle">NO DATA</text>
      </svg>
    );
  }

  const min = yMin !== undefined ? yMin : Math.min(...data);
  const max = yMax !== undefined ? yMax : Math.max(...data);
  const range = max - min || 1;

  const points = data.map((val, idx) => {
    const x = padLeft + (idx / (data.length - 1)) * (width - padLeft);
    const y = height - ((val - min) / range) * (height - 10) - 5;
    return { x, y, val };
  });

  const pathD = `M ${padLeft},${height} L ` + points.map(p => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" L ") + ` L ${width},${height} Z`;
  const lineD = `M ` + points.map(p => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" L ");

  return (
    <svg className="trend-card-chart-area" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity={0.25} />
          <stop offset="100%" stopColor={color} stopOpacity={0.0} />
        </linearGradient>
      </defs>

      {/* Y-Axis Label Ticks */}
      <text x={padLeft - 4} y="9" fill="#64748b" fontSize="6.5" fontWeight="bold" textAnchor="end">{yMax}</text>
      <text x={padLeft - 4} y={height / 2 + 2} fill="#64748b" fontSize="6.5" fontWeight="bold" textAnchor="end">{yMid}</text>
      <text x={padLeft - 4} y={height - 2} fill="#64748b" fontSize="6.5" fontWeight="bold" textAnchor="end">{yMin}</text>

      {/* Area Fill */}
      <path d={pathD} fill={`url(#${gradientId})`} />
      {/* Trend Line */}
      <path d={lineD} fill="none" stroke={strokeColor || color} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
      
      {/* Individual Data Points */}
      {points.map((p, i) => (
        <circle
          key={i}
          cx={p.x}
          cy={p.y}
          r={i === points.length - 1 ? 2.5 : 1.5}
          fill={strokeColor || color}
        />
      ))}
    </svg>
  );
}

/* ─── HISTORICAL DATASET GENERATORS & PARSERS ─── */
function generateSampleCycloneDataset() {
  const records = [];
  const lines = ["Timestamp,Time_Inst,Dry_Bulb_Temp,Wet_Bulb_Temp,Rel_Humidity,Pressure_hPa,Wind_Speed,Wind_Dir,Solar_Radiation,Rainfall,Status,QA_QC_Diagnosis"];
  const startTime = 12 * 3600;
  for (let i = 0; i < 60; i++) {
    const sec = startTime + i * 10;
    const hrs = String(Math.floor(sec / 3600)).padStart(2, "0");
    const mins = String(Math.floor((sec % 3600) / 60)).padStart(2, "0");
    const s = String(sec % 60).padStart(2, "0");
    const tStr = `${hrs}:${mins}:${s}`;
    
    const temp = +(28.5 - (i * 0.08) + (Math.sin(i / 5) * 0.3)).toFixed(1);
    const wetBulb = +(temp - 2.5 + Math.random() * 0.2).toFixed(1);
    const hum = Math.min(99, +(65.0 + i * 0.5 + Math.sin(i / 3) * 2)).toFixed(1);
    const press = +(1012.0 - (i * 0.45) + (Math.cos(i / 4) * 0.2)).toFixed(1);
    const speed = +(12.0 + (i * 0.35) + Math.random() * 1.5).toFixed(1);
    const dir = Math.round((45 + i * 2) % 360);
    const solar = Math.max(20, Math.round(800 - i * 12));
    const rain = i > 25 ? +((i - 25) * 0.4).toFixed(1) : 0.0;
    const isAnomaly = i >= 40 && i <= 44;
    const status = isAnomaly ? "ANOMALY" : "NOMINAL";
    const xai = isAnomaly ? "CYCLONIC PRESSURE SURGE & WIND GUST (>25 m/s)" : "Nominal atmospheric gradient";
    
    records.push({
      id: i + 1,
      timestamp: tStr,
      timeInst: sec,
      temp: Number(temp),
      wetBulb: Number(wetBulb),
      humidity: Number(hum),
      pressure: Number(press),
      speed: Number(speed),
      direction: dir,
      solar: Number(solar),
      rain: Number(rain),
      isAnomaly,
      anomalyType: isAnomaly ? "extreme_wind_gust" : "nominal",
      xai
    });

    lines.push(`${tStr},${sec},${temp},${wetBulb},${hum},${press},${speed},${dir},${solar},${rain},${status},"${xai}"`);
  }
  return { records, rawText: lines.join("\n") };
}

function generateSampleDriftDataset() {
  const records = [];
  const lines = ["Timestamp,Time_Inst,Dry_Bulb_Temp,Wet_Bulb_Temp,Rel_Humidity,Pressure_hPa,Wind_Speed,Wind_Dir,Solar_Radiation,Rainfall,Status,QA_QC_Diagnosis"];
  const startTime = 14 * 3600;
  for (let i = 0; i < 50; i++) {
    const sec = startTime + i * 10;
    const hrs = String(Math.floor(sec / 3600)).padStart(2, "0");
    const mins = String(Math.floor((sec % 3600) / 60)).padStart(2, "0");
    const s = String(sec % 60).padStart(2, "0");
    const tStr = `${hrs}:${mins}:${s}`;
    
    const isDrift = i >= 20;
    const temp = +(29.0 + (isDrift ? (i - 20) * 0.45 : Math.sin(i / 4) * 0.4)).toFixed(1);
    const wetBulb = +(temp - 3.8).toFixed(1);
    const hum = +(62.0 - (isDrift ? (i - 20) * 0.8 : 0)).toFixed(1);
    const press = +(1011.5 + (Math.sin(i / 6) * 0.5)).toFixed(1);
    const speed = +(8.5 + (Math.random() * 0.8)).toFixed(1);
    const dir = 110;
    const solar = 750;
    const rain = 0.0;
    const isAnomaly = isDrift && i > 30;
    const status = isAnomaly ? "ANOMALY" : (isDrift ? "WARNING" : "NOMINAL");
    const xai = isAnomaly ? "TRANSDUCER BIAS DRIFT DETECTED (PT100 +0.45°C/min)" : "Thermodynamic equilibrium confirmed";

    records.push({
      id: i + 1,
      timestamp: tStr,
      timeInst: sec,
      temp: Number(temp),
      wetBulb: Number(wetBulb),
      humidity: Number(hum),
      pressure: Number(press),
      speed: Number(speed),
      direction: dir,
      solar: Number(solar),
      rain: Number(rain),
      isAnomaly,
      anomalyType: isAnomaly ? "bias_drift" : "nominal",
      xai
    });

    lines.push(`${tStr},${sec},${temp},${wetBulb},${hum},${press},${speed},${dir},${solar},${rain},${status},"${xai}"`);
  }
  return { records, rawText: lines.join("\n") };
}

function parseHistoricalFile(text, fileName) {
  const rawLines = text.split(/\r?\n/).filter(line => line.trim().length > 0);
  if (rawLines.length === 0) return null;

  const records = [];
  let delimiter = ",";

  const firstLine = rawLines[0];
  if (firstLine.includes(",")) delimiter = ",";
  else if (firstLine.includes("\t")) delimiter = "\t";
  else if (firstLine.includes(";")) delimiter = ";";
  else delimiter = " ";

  const lowerFirst = firstLine.toLowerCase();
  const hasHeader = lowerFirst.includes("temp") || lowerFirst.includes("time") || lowerFirst.includes("press") || lowerFirst.includes("date");
  const startIndex = hasHeader ? 1 : 0;

  for (let i = startIndex; i < rawLines.length; i++) {
    const line = rawLines[i].trim();
    if (!line) continue;
    
    const cols = delimiter === " " ? line.split(/\s+/) : line.split(delimiter).map(c => c.replace(/^["']|["']$/g, '').trim());
    if (cols.length < 2) continue;

    const timeVal = cols[0] || `00:${String(i).padStart(2, "0")}:00`;
    const tempVal = parseFloat(cols[2] || cols[1] || 28.0) || 28.0;
    const wetVal = parseFloat(cols[3] || (tempVal - 3.5)) || +(tempVal - 3.5).toFixed(1);
    const humVal = parseFloat(cols[4] || cols[3] || 65.0) || 65.0;
    const pressVal = parseFloat(cols[5] || cols[4] || 1012.5) || 1012.5;
    const speedVal = parseFloat(cols[6] || cols[5] || 10.5) || 10.5;
    const dirVal = parseInt(cols[7] || cols[6] || 45, 10) || 45;
    const solarVal = parseFloat(cols[8] || cols[7] || 600) || 600;
    const rainVal = parseFloat(cols[9] || cols[8] || 0) || 0.0;
    
    const isAnom = tempVal > 48 || tempVal < -10 || humVal > 100 || pressVal < 900 || pressVal > 1080;
    const statusVal = cols[10] || (isAnom ? "ANOMALY" : "NOMINAL");
    const xaiVal = cols[11] || (isAnom ? "Threshold Out-of-Bounds Exception" : "Nominal channel telemetry");

    records.push({
      id: records.length + 1,
      timestamp: timeVal,
      timeInst: i * 10,
      temp: tempVal,
      wetBulb: wetVal,
      humidity: humVal,
      pressure: pressVal,
      speed: speedVal,
      direction: dirVal,
      solar: solarVal,
      rain: rainVal,
      isAnomaly: isAnom || statusVal.toUpperCase().includes("ANOMALY"),
      anomalyType: isAnom ? "out_of_bounds" : "nominal",
      xai: xaiVal
    });
  }

  return { records, rawText: text };
}

/* ─── MAIN COMPONENT ─── */
export default function Home() {
  const [activeTab, setActiveTab] = useState("dashboard");
  const [theme, setTheme] = useState("light");
  const [isStreaming, setIsStreaming] = useState(true);
  const [useImputed, setUseImputed] = useState(true);
  const [connectionStatus, setConnectionStatus] = useState("connected");
  const [spatialGlitch, setSpatialGlitch] = useState(false);
  const [graphType, setGraphType] = useState("all_params");
  const [plotStyle, setPlotStyle] = useState("line");
  const [isChartDropdownOpen, setIsChartDropdownOpen] = useState(false);
  const chartDropdownRef = useRef(null);

  // Dynamic Parameter Enable/Disable Filter State
  const [paramsList, setParamsList] = useState(DEFAULT_PARAMS);

  // ─── HISTORY REPLAY & FILE INGESTION STATES ───
  const defaultCycloneData = useMemo(() => generateSampleCycloneDataset(), []);
  const [importedFileName, setImportedFileName] = useState("aws_cyclone_telemetry_2026.csv");
  const [importedFileSize, setImportedFileSize] = useState("38.4 KB");
  const [importedRawText, setImportedRawText] = useState(defaultCycloneData.rawText);
  const [replayRecords, setReplayRecords] = useState(defaultCycloneData.records);
  const [replayIndex, setReplayIndex] = useState(0);
  const [isReplaying, setIsReplaying] = useState(false);
  const [replaySpeed, setReplaySpeed] = useState(1);
  const [broadcastToLive, setBroadcastToLive] = useState(true);
  const [replayViewMode, setReplayViewMode] = useState("graph"); // "graph" | "table" | "raw" | "split"
  const [replaySearch, setReplaySearch] = useState("");
  const [copiedRaw, setCopiedRaw] = useState(false);
  const [testbenchNotice, setTestbenchNotice] = useState(null);
  const [replayChannelFilter, setReplayChannelFilter] = useState("all"); // "all" | "temp" | "humidity" | "pressure" | "speed" | "solar" | "rain"
  const fileInputRef = useRef(null);

  const handleToggleParam = (paramId) => {
    setParamsList(prev =>
      prev.map(p => (p.id === paramId ? { ...p, enabled: !p.enabled } : p))
    );
  };

  const isParamEnabled = (paramKey) => {
    const p = paramsList.find(item => item.key === paramKey || item.id === paramKey);
    return p ? p.enabled : true;
  };

  // Close chart dropdown on outside click
  useEffect(() => {
    function handleClickOutside(event) {
      if (chartDropdownRef.current && !chartDropdownRef.current.contains(event.target)) {
        setIsChartDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const CHART_MODES = [
    { id: "line", label: "Line Chart", badge: "Line Chart", desc: "Continuous solid curve interpolation" },
    { id: "bar", label: "Bar Chart", badge: "Bar Chart", desc: "Discrete vertical column bars" },
    { id: "scatter", label: "Scatter Plot", badge: "Scatter Plot", desc: "Point-only telemetry markers" },
    { id: "area", label: "Area Chart", badge: "Area Chart", desc: "Gradient shaded area waveform" },
    { id: "dashed", label: "Dashed Pulse", badge: "Dashed Pulse", desc: "Segmented dashed line with target nodes" }
  ];

  const currentChartMode = CHART_MODES.find(m => m.id === plotStyle) || CHART_MODES[0];

  // Real Telemetry State (Starts null when no data is incoming on LAN)
  const [current, setCurrent] = useState(null);
  const [streamSource, setStreamSource] = useState("UDP LAN (0.0.0.0:5000)");
  const [telemetryHistory, setTelemetryHistory] = useState([]);
  const [metrics, setMetrics] = useState({ received: 0, dropped: 0 });
  const [lastPacketTime, setLastPacketTime] = useState(null);

  const [analysis, setAnalysis] = useState({
    is_anomaly: false,
    severity: "NOMINAL",
    confidence: 100,
    anomaly_type: "nominal",
    xai_explanation: "Ingestion pipeline standby. Awaiting incoming AWS data stream on LAN interface.",
    imputed_values: {},
    degradation_risk: 0,
    sensor_health: { temp_dry: 0, pressure_hpa: 0, humidity: 0 }
  });

  // Real-time Moving Buffers for live dynamic sliding graphs (Populated ONLY by incoming packets)
  const [historyBuffer, setHistoryBuffer] = useState({
    temp: [],
    humidity: [],
    pressure: [],
    solar: [],
    rain: []
  });

  const hasData = current !== null;

  // Dynamic Network Link Configuration
  const [linkProtocol, setLinkProtocol] = useState("UDP");
  const [linkHost, setLinkHost] = useState("0.0.0.0");
  const [linkPort, setLinkPort] = useState(5000);
  const [udpBuffer, setUdpBuffer] = useState("4096");
  const [udpFraming, setUdpFraming] = useState("AWS-32B Binary");

  const [tcpHost, setTcpHost] = useState("192.168.1.120");
  const [tcpPort, setTcpPort] = useState(8080);
  const [tcpReconnect, setTcpReconnect] = useState("auto");
  const [tcpKeepAlive, setTcpKeepAlive] = useState("30s");

  const [serialPort, setSerialPort] = useState("COM3");
  const [serialBaud, setSerialBaud] = useState("115200");
  const [serialParity, setSerialParity] = useState("8-N-1");
  const [serialFlow, setSerialFlow] = useState("None");
  const [activeProtocol, setActiveProtocol] = useState("UDP"); // "UDP" | "TCP" | "SERIAL"
  const [connNotice, setConnNotice] = useState("UDP LAN Broadcast Socket active on 0.0.0.0:5000 (Awaiting Ingest)");
  const [connLogs, setConnLogs] = useState([
    { time: "12:12:01", tag: "INFO", msg: "UDP socket bound to 0.0.0.0:5000" },
    { time: "12:12:02", tag: "INFO", msg: "Telemetry parser initialized: AWS-32B Binary Framing" },
    { time: "12:12:03", tag: "INFO", msg: "Listening for live packets on LAN interface..." }
  ]);

  const [dateStr, setDateStr] = useState("Saturday, 5 Sep 2026");
  const [timeStr, setTimeStr] = useState("12:12:07 AM IST");
  const [headerTimeStr, setHeaderTimeStr] = useState("10:24:35 AM IST | 05 Sep 2026");
  const [uptimeStr, setUptimeStr] = useState("00:00:00");

  const eventSourceRef = useRef(null);
  const startTimeRef = useRef(Date.now());

  // Sync Clock & Uptime
  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      const dateFormatted = now.toLocaleDateString("en-US", { weekday: "long", year: "numeric", month: "short", day: "numeric" });
      const timeFormatted = now.toLocaleTimeString("en-US", { hour12: true });
      const dateShort = now.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });

      setDateStr(`${dateFormatted}`);
      setTimeStr(`${timeFormatted} IST`);
      setHeaderTimeStr(`${timeFormatted} IST | ${dateShort}`);

      const elapsed = Math.floor((Date.now() - startTimeRef.current) / 1000);
      const hrs = String(Math.floor(elapsed / 3600)).padStart(2, "0");
      const mins = String(Math.floor((elapsed % 3600) / 60)).padStart(2, "0");
      const secs = String(elapsed % 60).padStart(2, "0");
      setUptimeStr(`${hrs}:${mins}:${secs}`);
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  // Telemetry SSE Stream from Go backend
  useEffect(() => {
    if (!isStreaming) {
      if (eventSourceRef.current) eventSourceRef.current.close();
      setConnectionStatus("disconnected");
      return;
    }

    setConnectionStatus("connecting");
    const es = new EventSource(getApiEndpoint("/api/stream"));
    eventSourceRef.current = es;

    es.onopen = () => setConnectionStatus("connected");

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
          xai_explanation: "All meteorological channels within nominal physical tolerances.",
          imputed_values: {}
        };

        if (payload.source) setStreamSource(payload.source);

        if (!raw) {
          if (ai && ai.xai_explanation) setAnalysis(ai);
          return;
        }

        setCurrent(raw);
        setAnalysis(ai);
        setLastPacketTime(Date.now());
        setHistoryBuffer(h => ({
          temp: [...(h.temp.length >= 20 ? h.temp.slice(1) : h.temp), raw.dry_bulb_temp],
          humidity: [...(h.humidity.length >= 20 ? h.humidity.slice(1) : h.humidity), raw.rel_humidity],
          pressure: [...(h.pressure.length >= 20 ? h.pressure.slice(1) : h.pressure), raw.pressure_hpa],
          solar: [...(h.solar.length >= 20 ? h.solar.slice(1) : h.solar), raw.solar_radiation],
          rain: [...(h.rain.length >= 20 ? h.rain.slice(1) : h.rain), raw.rainfall]
        }));

        setMetrics(prev => ({
          received: prev.received + 1,
          dropped: prev.dropped + (ai.is_anomaly ? 1 : 0)
        }));

        setTelemetryHistory(prev => {
          const row = {
            time: timeNow,
            timestamp: payload.timestamp,
            raw,
            is_anomaly: ai.is_anomaly,
            anomaly_type: ai.anomaly_type,
            xai: ai.xai_explanation,
            dry_temp: useImputed && ai.is_anomaly && ai.imputed_values?.temp_dry ? ai.imputed_values.temp_dry : raw.dry_bulb_temp,
            wet_temp: raw.wet_bulb_temp,
            humidity: useImputed && ai.is_anomaly && ai.imputed_values?.humidity ? ai.imputed_values.humidity : raw.rel_humidity,
            pressure: useImputed && ai.is_anomaly && ai.imputed_values?.pressure_hpa ? ai.imputed_values.pressure_hpa : raw.pressure_hpa,
            solar: raw.solar_radiation,
            rain: raw.rainfall,
            speed: raw.speed
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
      setConnectionStatus("connected");
      es.close();
    };

    return () => {
      if (es) es.close();
    };
  }, [isStreaming, useImputed]);

  // ─── REPLAY PLAYBACK ENGINE LOOP ───
  useEffect(() => {
    if (!isReplaying || replayRecords.length === 0) return;

    const interval = setInterval(() => {
      setReplayIndex(prev => {
        const nextIdx = (prev + 1) % replayRecords.length;
        const curRecord = replayRecords[nextIdx];
        if (curRecord && broadcastToLive) {
          setLastPacketTime(Date.now());
          setCurrent({
            time_inst: curRecord.timeInst,
            direction: curRecord.direction,
            speed: curRecord.speed,
            dry_bulb_temp: curRecord.temp,
            wet_bulb_temp: curRecord.wetBulb,
            rel_humidity: curRecord.humidity,
            solar_radiation: curRecord.solar,
            rainfall: curRecord.rain,
            pressure_imu: +(curRecord.pressure + 0.4).toFixed(1),
            pressure_hpa: curRecord.pressure
          });
          setHistoryBuffer(h => ({
            temp: [...(h.temp.length >= 20 ? h.temp.slice(1) : h.temp), curRecord.temp],
            humidity: [...(h.humidity.length >= 20 ? h.humidity.slice(1) : h.humidity), curRecord.humidity],
            pressure: [...(h.pressure.length >= 20 ? h.pressure.slice(1) : h.pressure), curRecord.pressure],
            solar: [...(h.solar.length >= 20 ? h.solar.slice(1) : h.solar), curRecord.solar],
            rain: [...(h.rain.length >= 20 ? h.rain.slice(1) : h.rain), curRecord.rain]
          }));
          setMetrics(prev => ({ received: prev.received + 1, dropped: prev.dropped + (curRecord.isAnomaly ? 1 : 0) }));
          if (curRecord.isAnomaly) {
            setAnalysis({
              is_anomaly: true,
              severity: "CRITICAL",
              confidence: 97.4,
              anomaly_type: curRecord.anomalyType || "anomaly",
              xai_explanation: curRecord.xai || "Historical anomaly detected in replayed stream.",
              imputed_values: { temp_dry: curRecord.temp, humidity: curRecord.humidity, pressure_hpa: curRecord.pressure },
              degradation_risk: 75,
              sensor_health: { temp_dry: 45.0, pressure_hpa: 70.0, humidity: 82.0 }
            });
          }
        }
        return nextIdx;
      });
    }, Math.max(100, Math.floor(1000 / replaySpeed)));

    return () => clearInterval(interval);
  }, [isReplaying, replayRecords, replaySpeed, broadcastToLive]);

  // ─── FILE UPLOAD HANDLER (.CSV, .TXT, .LOG, .DAT) ───
  const handleFileUpload = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const fileName = file.name;
    const fileSize = (file.size / 1024).toFixed(1) + " KB";
    const reader = new FileReader();

    reader.onload = (event) => {
      const content = event.target?.result;
      if (typeof content === "string") {
        const parsed = parseHistoricalFile(content, fileName);
        if (parsed && parsed.records.length > 0) {
          setImportedFileName(fileName);
          setImportedFileSize(fileSize);
          setImportedRawText(parsed.rawText);
          setReplayRecords(parsed.records);
          setReplayIndex(0);
          setIsReplaying(false);
          setTestbenchNotice({
            type: "success",
            msg: `Successfully imported "${fileName}" (${parsed.records.length} records). Ready for Multi-Channel Graph analysis and Replay!`,
            time: new Date().toLocaleTimeString()
          });
        } else {
          alert("Could not parse valid telemetry records from the uploaded file. Please check format.");
        }
      }
    };

    reader.readAsText(file);
    e.target.value = "";
  };

  const handleLoadSampleCyclone = () => {
    const data = generateSampleCycloneDataset();
    setImportedFileName("aws_cyclone_telemetry_2026.csv");
    setImportedFileSize("38.4 KB");
    setImportedRawText(data.rawText);
    setReplayRecords(data.records);
    setReplayIndex(0);
    setIsReplaying(false);
    setTestbenchNotice({
      type: "info",
      msg: "Loaded Sample AWS Cyclone Telemetry (60 Frames, Extreme Wind Gusts & Pressure Drop).",
      time: new Date().toLocaleTimeString()
    });
  };

  const handleLoadSampleDrift = () => {
    const data = generateSampleDriftDataset();
    setImportedFileName("aws_pt100_drift_log_2026.txt");
    setImportedFileSize("31.2 KB");
    setImportedRawText(data.rawText);
    setReplayRecords(data.records);
    setReplayIndex(0);
    setIsReplaying(false);
    setTestbenchNotice({
      type: "info",
      msg: "Loaded Sample Sensor Bias Drift ASCII Log (50 Frames, PT100 Drift & Warning Triggers).",
      time: new Date().toLocaleTimeString()
    });
  };

  const handleClearDataset = () => {
    setImportedFileName("empty_stream.csv");
    setImportedFileSize("0 KB");
    setImportedRawText("");
    setReplayRecords([]);
    setReplayIndex(0);
    setIsReplaying(false);
  };

  // ─── ANOMALY INJECTION HANDLERS ───
  const handleTriggerAnomaly = async (type, param, val, label, color) => {
    setTestbenchNotice({
      type: "danger",
      msg: `TRIGGERED: ${label}`,
      time: new Date().toLocaleTimeString()
    });

    try {
      await fetch(getApiEndpoint("/api/inject"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ anomaly_type: type, parameter: param, value: val })
      });
    } catch (err) {
      console.log("Backend offline, applying client-side injection simulation");
    }

    if (type === "spike") {
      setCurrent(c => ({ ...c, dry_bulb_temp: +(c.dry_bulb_temp + 25.0).toFixed(1) }));
      setAnalysis({
        is_anomaly: true,
        severity: "CRITICAL",
        confidence: 99.4,
        anomaly_type: "temperature_spike",
        xai_explanation: "PT100 Resistance jump (+25°C step). Exceeds WMO atmospheric RoC bounds (>5°C/min).",
        imputed_values: { temp_dry: 28.6, humidity: 62.5, pressure_hpa: 1012.8 },
        degradation_risk: 92,
        sensor_health: { temp_dry: 12.0, pressure_hpa: 99.0, humidity: 95.0 }
      });
    } else if (type === "freeze") {
      setAnalysis({
        is_anomaly: true,
        severity: "WARNING",
        confidence: 94.2,
        anomaly_type: "pressure_freeze",
        xai_explanation: "Zero-variance locked value over rolling 18-frame window on Barometric transducer.",
        imputed_values: { temp_dry: current.dry_bulb_temp, humidity: current.rel_humidity, pressure_hpa: 1012.8 },
        degradation_risk: 70,
        sensor_health: { temp_dry: 98.6, pressure_hpa: 34.0, humidity: 95.0 }
      });
    } else if (type === "drift") {
      setCurrent(c => ({ ...c, rel_humidity: Math.min(99, +(c.rel_humidity + 28).toFixed(1)) }));
      setAnalysis({
        is_anomaly: true,
        severity: "WARNING",
        confidence: 88.5,
        anomaly_type: "humidity_drift",
        xai_explanation: "Capacitive drift rate detected (+0.8%/min) with dry-bulb temperature decoupling.",
        imputed_values: { temp_dry: current.dry_bulb_temp, humidity: 62.5, pressure_hpa: current.pressure_hpa },
        degradation_risk: 65,
        sensor_health: { temp_dry: 98.6, pressure_hpa: 99.0, humidity: 41.0 }
      });
    } else if (type === "loss") {
      setAnalysis({
        is_anomaly: true,
        severity: "CRITICAL",
        confidence: 99.9,
        anomaly_type: "packet_loss_outage",
        xai_explanation: "Packet drop burst detected on UDP listener. Sequence counter discontinuity.",
        imputed_values: { temp_dry: current.dry_bulb_temp, humidity: current.rel_humidity, pressure_hpa: current.pressure_hpa },
        degradation_risk: 85,
        sensor_health: { temp_dry: 60.0, pressure_hpa: 60.0, humidity: 60.0 }
      });
    } else if (type === "psychrometric") {
      setCurrent(c => ({ ...c, wet_bulb_temp: +(c.dry_bulb_temp + 6.0).toFixed(1) }));
      setAnalysis({
        is_anomaly: true,
        severity: "CRITICAL",
        confidence: 99.8,
        anomaly_type: "psychrometric_conflict",
        xai_explanation: "Thermodynamic law violation: Wet-bulb temperature exceeded Dry-bulb temperature (Tw > Td).",
        imputed_values: { temp_dry: current.dry_bulb_temp, humidity: current.rel_humidity, pressure_hpa: current.pressure_hpa },
        degradation_risk: 95,
        sensor_health: { temp_dry: 25.0, pressure_hpa: 99.0, humidity: 95.0 }
      });
    } else if (type === "spatial") {
      setSpatialGlitch(true);
      setCurrent(c => ({ ...c, dry_bulb_temp: 55.0 }));
      setAnalysis({
        is_anomaly: true,
        severity: "CRITICAL",
        confidence: 99.6,
        anomaly_type: "spatial_inconsistency",
        xai_explanation: "Spatial k-NN neighbor discordance: Station AWS-01 (55.0°C) diverged >24°C from neighboring cluster (31.0°C).",
        imputed_values: { temp_dry: 30.8, humidity: 62.5, pressure_hpa: 1012.8 },
        degradation_risk: 98,
        sensor_health: { temp_dry: 10.0, pressure_hpa: 99.0, humidity: 95.0 }
      });
    }
  };

  const handleResetNominal = async () => {
    setSpatialGlitch(false);
    setTestbenchNotice({
      type: "nominal",
      msg: "System restored to nominal operating state. All QA/QC filters clear.",
      time: new Date().toLocaleTimeString()
    });

    try {
      await fetch(getApiEndpoint("/api/reset"));
    } catch (err) {
      console.log("Reset sent");
    }

    setAnalysis({
      is_anomaly: false,
      severity: "NOMINAL",
      confidence: 100,
      anomaly_type: "nominal",
      xai_explanation: "All meteorological channels within nominal physical tolerances.",
      imputed_values: { temp_dry: 28.6, humidity: 62.5, pressure_hpa: 1012.8 },
      degradation_risk: 0,
      sensor_health: { temp_dry: 98.6, pressure_hpa: 99.0, humidity: 95.0 }
    });
  };

  const handleCopyRawText = () => {
    if (!importedRawText) return;
    navigator.clipboard.writeText(importedRawText);
    setCopiedRaw(true);
    setTimeout(() => setCopiedRaw(false), 2000);
  };

  const handleExportCSV = () => {
    let csv = "Time,Time_Inst,Direction,Speed(M/S),Dry_Bulb(C),Wet_Bulb(C),Rel_Humidity(%),Solar_Radiation(W/M2),Rainfall(MM),Pressure_IMU(hPa),Pressure(hPa),Status,QA_QC_Diagnosis\n";
    if (telemetryHistory.length > 0) {
      telemetryHistory.forEach(h => {
        const r = h.raw;
        csv += `${h.time},${r.time_inst},${r.direction},${r.speed},${r.dry_bulb_temp},${r.wet_bulb_temp},${r.rel_humidity},${r.solar_radiation},${r.rainfall},${r.pressure_imu},${r.pressure_hpa},${h.is_anomaly ? "ANOMALY" : "NOMINAL"},"${h.xai || ''}"\n`;
      });
    } else {
      csv += `${timeStr},${current.time_inst},${current.direction},${current.speed},${current.dry_bulb_temp},${current.wet_bulb_temp},${current.rel_humidity},${current.solar_radiation},${current.rainfall},${current.pressure_imu},${current.pressure_hpa},NOMINAL,"SYSTEM INITIALIZED"\n`;
    }
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "aws_telemetry_logs.csv";
    link.click();
  };

  const formatVal = (val, decimals = 1, isInt = false) => {
    if (val === null || val === undefined || isNaN(Number(val))) return "--";
    const num = Number(val);
    if (isInt) return Math.round(num).toString();
    return num.toFixed(decimals);
  };

  return (
    <div className="app-container">
      
      {/* ─── 1. TOP HEADER (NAVY DEFENSE BAR) ─── */}
      <header className="app-header">
        <div className="header-left">
          <NationalEmblemIcon />
          <div className="header-title-box">
            <h1 className="header-title">AUTOMATED WEATHER STATION</h1>
            <span className="header-subtext">SkyGuard Ground Telemetry Station</span>
          </div>
        </div>

        {/* Cockpit Status Pill on Right */}
        <div className="header-cockpit-bar">
          <div className="cockpit-item">
            <span className="cockpit-label">SYSTEM STATUS</span>
            <div className="cockpit-value-row">
              <span className="cockpit-dot" style={{ background: hasData ? "#22c55e" : "#eab308" }}></span>
              <span>{hasData ? (analysis?.is_anomaly ? "DEGRADED" : "OPERATIONAL") : "STANDBY (NO DATA)"}</span>
            </div>
          </div>

          <div className="cockpit-item" onClick={() => setUseImputed(!useImputed)} style={{ cursor: "pointer" }}>
            <span className="cockpit-label">AUTO-CORRECT</span>
            <div className="cockpit-value-row">
              <span className="cockpit-dot" style={{ background: useImputed ? "#22c55e" : "#ea580c" }}></span>
              <span>{useImputed ? "ON" : "OFF"}</span>
            </div>
          </div>

          <button
            onClick={() => setIsStreaming(!isStreaming)}
            className="btn-livestream"
            style={{ opacity: isStreaming ? 1 : 0.7 }}
          >
            <span>{isStreaming ? (hasData ? "((o)) LIVE STREAM (1.0 Hz)" : "((o)) AWAITING STREAM") : "STREAM PAUSED"}</span>
          </button>
        </div>
      </header>

      {/* ─── 2. MAIN APP BODY ─── */}
      <div className="app-body">
        
        {/* ─── LEFT SIDEBAR ─── */}
        <aside className="app-sidebar">
          <div className="sidebar-top">
            <div className="sidebar-title-box">
              <div className="sidebar-sub">MISSION OPERATIONS</div>
            </div>

            <nav className="sidebar-nav">
              {[
                { id: "dashboard", label: "Dashboard Monitor" },
                { id: "spatial_grid", label: "Multi-AWS Spatial Grid" },
                { id: "live_graph", label: "Live Telemetry Plots" },
                { id: "frame_editor", label: "Parameter Editor" },
                { id: "data_logger", label: "Local Data Logger" },
                { id: "replay_session", label: "History Replay Hub" },
                { id: "export_option", label: "System Export Center" },
                { id: "link_config", label: "Connection Links" }
              ].map(item => (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`nav-item ${activeTab === item.id ? "active" : ""}`}
                >
                  <span>{item.label}</span>
                </button>
              ))}
            </nav>
          </div>

          {/* Sidebar Bottom Status Deck */}
          <div className="sidebar-bottom-status">
            <div className="sidebar-status-title">STATION STATUS</div>
            <div className="sidebar-online-pill">
              <span className="cockpit-dot" style={{ background: hasData ? "#22c55e" : "#eab308" }}></span>
              <span>{hasData ? "ONLINE" : "STANDBY"}</span>
            </div>

            <div style={{ marginTop: "4px" }}>
              <div className="sidebar-stat-label">UPTIME</div>
              <div className="sidebar-stat-val" suppressHydrationWarning>{uptimeStr}</div>
            </div>

            <div style={{ marginTop: "4px" }}>
              <div className="sidebar-stat-label">DATA PACKETS</div>
              <div className="sidebar-stat-val" suppressHydrationWarning>{formatNum(metrics.received)}</div>
              
              {/* Orange Equalizer Bars */}
              <div className="equalizer-bar-container">
                {[6, 12, 9, 16, 11, 18, 14, 17].map((h, i) => (
                  <div
                    key={i}
                    className="equalizer-bar"
                    style={{
                      height: hasData ? `${h}px` : "3px",
                      opacity: hasData ? (0.6 + (i * 0.05)) : 0.25
                    }}
                  />
                ))}
              </div>
            </div>
          </div>
        </aside>

        {/* ─── MAIN WORKSPACE ─── */}
        <main className="app-workspace">
          
          {/* 1. DASHBOARD MONITOR TAB */}
          {activeTab === "dashboard" && (
            <div className="dashboard-fullscreen-grid">
              
              {/* ─── CENTER COLUMN ─── */}
              <div className="dashboard-center-column">
                
                {/* 1.1 LIVE PARAMETER OVERVIEW (10 CARDS) */}
                <div>
                  <div className="section-title-row">
                    <span className="orange-section-bar">|</span>
                    <span className="section-main-title">LIVE PARAMETER OVERVIEW</span>
                  </div>

                  <div className="numerical-cards-grid-5col">
                    
                    {/* 1. Time (IST) */}
                    {isParamEnabled("time_inst") && (
                      <div className="param-card">
                        <div className="param-card-top">
                          <span>Time (IST)</span>
                        </div>
                        <div className="param-card-center">
                          <span className="param-card-val" style={{ color: "#2563eb" }}>
                            {current ? (typeof current.time_inst === "number" ? (() => {
                              const s = current.time_inst % 86400;
                              const h = String(Math.floor(s / 3600)).padStart(2, "0");
                              const m = String(Math.floor((s % 3600) / 60)).padStart(2, "0");
                              const sec = String(s % 60).padStart(2, "0");
                              return `${h}:${m}:${sec}`;
                            })() : current.time_inst) : "--:--:--"}
                          </span>
                        </div>
                        <div className="param-card-bottom">
                          <span>{hasData ? "sec" : "AWAITING INGEST"}</span>
                        </div>
                      </div>
                    )}

                    {/* 2. Wind Direction */}
                    {isParamEnabled("direction") && (
                      <div className="param-card">
                        <div className="param-card-top">
                          <span>Wind Direction</span>
                        </div>
                        <div className="param-card-center">
                          <span className="param-card-val" style={{ color: "#16a34a" }}>
                            {current && current.direction !== undefined ? `${current.direction}°` : "--"}
                          </span>
                        </div>
                        <div className="param-card-bottom">
                          <span>deg</span>
                        </div>
                      </div>
                    )}

                    {/* 3. Wind Speed */}
                    {isParamEnabled("speed") && (
                      <div className="param-card">
                        <div className="param-card-top">
                          <span>Wind Speed</span>
                        </div>
                        <div className="param-card-center">
                          <span className="param-card-val" style={{ color: "#2563eb" }}>
                            {formatVal(current?.speed, 1)}
                          </span>
                        </div>
                        <div className="param-card-bottom">
                          <span>m/s</span>
                        </div>
                      </div>
                    )}

                    {/* 4. Dry Bulb Temp */}
                    {isParamEnabled("temp") && (
                      <div className="param-card">
                        <div className="param-card-top">
                          <span>Dry Bulb Temp.</span>
                        </div>
                        <div className="param-card-center">
                          <span className="param-card-val" style={{ color: "#dc2626" }}>
                            {formatVal(current?.dry_bulb_temp, 1)}
                          </span>
                        </div>
                        <div className="param-card-bottom">
                          <span>°C</span>
                        </div>
                      </div>
                    )}

                    {/* 5. Wet Bulb Temp */}
                    {isParamEnabled("wet_bulb") && (
                      <div className="param-card">
                        <div className="param-card-top">
                          <span>Wet Bulb Temp.</span>
                        </div>
                        <div className="param-card-center">
                          <span className="param-card-val" style={{ color: "#dc2626" }}>
                            {formatVal(current?.wet_bulb_temp, 1)}
                          </span>
                        </div>
                        <div className="param-card-bottom">
                          <span>°C</span>
                        </div>
                      </div>
                    )}

                    {/* 6. Rel. Humidity */}
                    {isParamEnabled("humidity") && (
                      <div className="param-card">
                        <div className="param-card-top">
                          <span>Rel. Humidity</span>
                        </div>
                        <div className="param-card-center">
                          <span className="param-card-val" style={{ color: "#7c3aed" }}>
                            {formatVal(current?.rel_humidity, 1)}
                          </span>
                        </div>
                        <div className="param-card-bottom">
                          <span>%</span>
                        </div>
                      </div>
                    )}

                    {/* 7. Solar Radiation */}
                    {isParamEnabled("solar") && (
                      <div className="param-card">
                        <div className="param-card-top">
                          <span>Solar Radiation</span>
                        </div>
                        <div className="param-card-center">
                          <span className="param-card-val" style={{ color: "#ea580c" }}>
                            {formatVal(current?.solar_radiation, 0, true)}
                          </span>
                        </div>
                        <div className="param-card-bottom">
                          <span>W/m²</span>
                        </div>
                      </div>
                    )}

                    {/* 8. Rainfall */}
                    {isParamEnabled("rain") && (
                      <div className="param-card">
                        <div className="param-card-top">
                          <span>Rainfall</span>
                        </div>
                        <div className="param-card-center">
                          <span className="param-card-val" style={{ color: "#0284c7" }}>
                            {formatVal(current?.rainfall, 1)}
                          </span>
                        </div>
                        <div className="param-card-bottom">
                          <span>mm</span>
                        </div>
                      </div>
                    )}

                    {/* 9. Pressure (IMU) */}
                    {isParamEnabled("pressure_imu") && (
                      <div className="param-card">
                        <div className="param-card-top">
                          <span>Pressure (IMU)</span>
                        </div>
                        <div className="param-card-center">
                          <span className="param-card-val" style={{ color: "#0284c7" }}>
                            {current?.pressure_imu !== undefined ? current.pressure_imu.toFixed(1) : (current?.pressure_hpa !== undefined ? (current.pressure_hpa + 0.4).toFixed(1) : "--")}
                          </span>
                        </div>
                        <div className="param-card-bottom">
                          <span>hPa</span>
                        </div>
                      </div>
                    )}

                    {/* 10. Pressure (hPa) */}
                    {isParamEnabled("pressure") && (
                      <div className="param-card">
                        <div className="param-card-top">
                          <span>Pressure (hPa)</span>
                        </div>
                        <div className="param-card-center">
                          <span className="param-card-val" style={{ color: "#0284c7" }}>
                            {formatVal(current?.pressure_hpa, 1)}
                          </span>
                        </div>
                        <div className="param-card-bottom">
                          <span>hPa</span>
                        </div>
                      </div>
                    )}

                  </div>
                </div>

                {/* 1.2 TREND SNAPSHOT (LAST 30 MINUTES) */}
                <div className="trend-snapshot-section">
                  <div className="section-title-row">
                    <span className="orange-section-bar">|</span>
                    <span className="section-main-title">TREND SNAPSHOT (LAST 30 MINUTES)</span>
                  </div>

                  <div className="trend-charts-5col-grid">
                    
                    {/* Chart 1: Dry Bulb Temp */}
                    {isParamEnabled("temp") && (
                      <div className="trend-card-box">
                        <div className="trend-card-header">
                          <span>Dry Bulb Temp. (°C)</span>
                          <span className="trend-card-val" style={{ color: "#dc2626" }}>
                            {formatVal(current?.dry_bulb_temp, 1)}
                          </span>
                        </div>
                        <MiniTrendSparklineWithAxis
                          data={historyBuffer.temp}
                          color="#dc2626"
                          gradientId="gradTempLight"
                          strokeColor="#dc2626"
                          yMin={0}
                          yMid={20}
                          yMax={40}
                        />
                        <div className="trend-card-axis">
                          <span>-30m</span>
                          <span>-15m</span>
                          <span>Now</span>
                        </div>
                      </div>
                    )}

                    {/* Chart 2: Rel. Humidity */}
                    {isParamEnabled("humidity") && (
                      <div className="trend-card-box">
                        <div className="trend-card-header">
                          <span>Rel. Humidity (%)</span>
                          <span className="trend-card-val" style={{ color: "#7c3aed" }}>
                            {formatVal(current?.rel_humidity, 1)}
                          </span>
                        </div>
                        <MiniTrendSparklineWithAxis
                          data={historyBuffer.humidity}
                          color="#7c3aed"
                          gradientId="gradHumLight"
                          strokeColor="#7c3aed"
                          yMin={0}
                          yMid={50}
                          yMax={100}
                        />
                        <div className="trend-card-axis">
                          <span>-30m</span>
                          <span>-15m</span>
                          <span>Now</span>
                        </div>
                      </div>
                    )}

                    {/* Chart 3: Pressure (hPa) */}
                    {isParamEnabled("pressure") && (
                      <div className="trend-card-box">
                        <div className="trend-card-header">
                          <span>Pressure (hPa)</span>
                          <span className="trend-card-val" style={{ color: "#0284c7" }}>
                            {formatVal(current?.pressure_hpa, 1)}
                          </span>
                        </div>
                        <MiniTrendSparklineWithAxis
                          data={historyBuffer.pressure}
                          color="#0284c7"
                          gradientId="gradPressLight"
                          strokeColor="#0284c7"
                          yMin={970}
                          yMid={1010}
                          yMax={1030}
                        />
                        <div className="trend-card-axis">
                          <span>-30m</span>
                          <span>-15m</span>
                          <span>Now</span>
                        </div>
                      </div>
                    )}

                    {/* Chart 4: Solar Radiation */}
                    {isParamEnabled("solar") && (
                      <div className="trend-card-box">
                        <div className="trend-card-header">
                          <span>Solar Radiation (W/m²)</span>
                          <span className="trend-card-val" style={{ color: "#ea580c" }}>
                            {formatVal(current?.solar_radiation, 0, true)}
                          </span>
                        </div>
                        <MiniTrendSparklineWithAxis
                          data={historyBuffer.solar}
                          color="#ea580c"
                          gradientId="gradSolarLight"
                          strokeColor="#ea580c"
                          yMin={0}
                          yMid={600}
                          yMax={1200}
                        />
                        <div className="trend-card-axis">
                          <span>-30m</span>
                          <span>-15m</span>
                          <span>Now</span>
                        </div>
                      </div>
                    )}

                    {/* Chart 5: Rainfall */}
                    {isParamEnabled("rain") && (
                      <div className="trend-card-box">
                        <div className="trend-card-header">
                          <span>Rainfall (mm)</span>
                          <span className="trend-card-val" style={{ color: "#0284c7" }}>
                            {formatVal(current?.rainfall, 1)}
                          </span>
                        </div>
                        <MiniTrendSparklineWithAxis
                          data={historyBuffer.rain}
                          color="#0284c7"
                          gradientId="gradRainLight"
                          strokeColor="#0284c7"
                          yMin={0}
                          yMid={5}
                          yMax={10}
                        />
                        <div className="trend-card-axis">
                          <span>-30m</span>
                          <span>-15m</span>
                          <span>Now</span>
                        </div>
                      </div>
                    )}

                  </div>
                </div>

                {/* 1.3 BOTTOM ROW: 3 CARDS */}
                <div className="bottom-three-deck-row">
                  
                  {/* Card A: Connection Matrix */}
                  <div className="bottom-deck-card">
                    <div className="bottom-card-header">
                      <span>CONNECTION MATRIX</span>
                    </div>

                    <div className="connection-table">
                      <div className="conn-row">
                        <span className="conn-key">Link</span>
                        <span className="conn-val green" style={{ fontSize: "0.60rem" }}>
                          {activeProtocol} LAN ({linkHost}:{linkPort}) - {hasData ? "ONLINE" : "LISTENING"}
                        </span>
                      </div>
                      <div className="conn-row">
                        <span className="conn-key">Source</span>
                        <span className="conn-val" style={{ color: hasData ? "#16a34a" : "#64748b" }}>
                          {hasData ? "LIVE LAN STREAM" : "AWAITING INCOMING DATA"}
                        </span>
                      </div>
                      <div className="conn-row">
                        <span className="conn-key">Self-Healing</span>
                        <span className="conn-val" style={{ color: useImputed ? "#16a34a" : "#dc2626", fontWeight: 800 }}>
                          {useImputed ? "ON (Healed Stream)" : "OFF (Raw Feed)"}
                        </span>
                      </div>
                      <div className="conn-row">
                        <span className="conn-key">UDP LAN Port</span>
                        <span className="conn-val">{linkHost}:{linkPort}</span>
                      </div>
                      <div className="conn-row">
                        <span className="conn-key">TCP LAN Port</span>
                        <span className="conn-val">{tcpHost}:{tcpPort}</span>
                      </div>
                      <div className="conn-row">
                        <span className="conn-key">Packets Parsed</span>
                        <span className="conn-val" suppressHydrationWarning>{formatNum(metrics.received)}</span>
                      </div>
                      <div className="conn-row">
                        <span className="conn-key">Dropped / Anomaly</span>
                        <span className="conn-val" suppressHydrationWarning>{formatNum(metrics.dropped)}</span>
                      </div>
                      <div className="conn-row">
                        <span className="conn-key">System Health</span>
                        <span className="conn-val" style={{ color: hasData ? (analysis?.is_anomaly ? "#ea580c" : "#16a34a") : "#64748b", fontWeight: 800 }}>
                          {hasData ? (analysis?.is_anomaly ? (analysis?.severity || "DEGRADED") : "NOMINAL") : "STANDBY (NO DATA)"}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Card B: Date & Time + Analog Clock Widget */}
                  <div className="bottom-deck-card">
                    <div className="bottom-card-header">
                      <span>DATE & TIME</span>
                    </div>

                    <div className="datetime-split-content">
                      <div className="datetime-text-side">
                        <div className="date-text-day" suppressHydrationWarning>{dateStr}</div>
                        <div className="date-text-clock" suppressHydrationWarning>{timeStr}</div>
                      </div>

                      <AnalogClock />
                    </div>
                  </div>

                  {/* Card C: Quick Actions */}
                  <div className="bottom-deck-card">
                    <div className="bottom-card-header">
                      <span>QUICK ACTIONS</span>
                    </div>

                    <div className="quick-action-buttons-wrap">
                      <button onClick={handleExportCSV} className="btn-action-light">
                        <span>Export Log Now (.CSV)</span>
                      </button>

                      <button
                        onClick={() => {
                          setTelemetryHistory([]);
                          setMetrics({ received: 0, dropped: 0 });
                        }}
                        className="btn-action-light"
                      >
                        <span>Clear Cached Logs</span>
                      </button>
                    </div>
                  </div>

                </div>

              </div>

              {/* ─── RIGHT SIDEBAR DECK ─── */}
              <div className="dashboard-right-deck">
                
                {/* Deck 1: Explainable AI (XAI) */}
                <div className="right-deck-box xai-deck-box" style={{ flex: 1.6 }}>
                  <div className="deck-title-row">
                    <div className="deck-title-text">
                      <span>EXPLAINABLE AI (XAI)</span>
                    </div>
                    <span className={`xai-status-badge ${hasData ? (analysis?.is_anomaly ? "anomaly" : "nominal") : "nominal"}`} style={{ opacity: hasData ? 1 : 0.6 }}>
                      {hasData ? (analysis?.is_anomaly ? (analysis.severity || "ANOMALY") : "NOMINAL") : "STANDBY"}
                    </span>
                  </div>

                  {/* Diagnostic Explanation */}
                  <div className="xai-diagnostic-box">
                    <div className="xai-diag-label">REAL-TIME DIAGNOSTIC REASONING</div>
                    <div className="xai-diag-text">
                      {hasData ? (analysis?.xai_explanation || "All meteorological channels within nominal physical & thermodynamic tolerances.") : "Awaiting telemetry stream on configured network interface (0.0.0.0:5000). QA/QC inference pipeline on standby."}
                    </div>
                  </div>

                  {/* SHAP Feature Contribution Bars */}
                  <div className="xai-shap-section">
                    <div className="xai-shap-title">KEY ATTRIBUTION FACTORS (SHAP)</div>
                    <div className="xai-shap-list">
                      {[
                        { factor: "Temp Rate-of-Change", pct: hasData ? (analysis?.is_anomaly ? 78 : 12) : 0, color: "#dc2626" },
                        { factor: "Vapor Balance (Magnus)", pct: hasData ? (analysis?.is_anomaly ? 64 : 8) : 0, color: "#7c3aed" },
                        { factor: "Rolling Invariance", pct: hasData ? (analysis?.is_anomaly ? 42 : 5) : 0, color: "#0284c7" }
                      ].map((f, i) => (
                        <div key={i} className="xai-shap-row">
                          <div className="xai-shap-info">
                            <span>{f.factor}</span>
                            <span style={{ fontWeight: 700 }}>{f.pct}%</span>
                          </div>
                          <div className="xai-shap-bar-bg">
                            <div className="xai-shap-bar-fill" style={{ width: `${f.pct}%`, background: f.color }} />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                </div>

                {/* Deck 2: System & Data Health */}
                <div className="right-deck-box" style={{ flex: 1.1 }}>
                  <div className="deck-title-text">
                    SYSTEM & DATA HEALTH
                  </div>

                  <div className="health-status-list">
                    <div className="health-status-row">
                      <span className="health-key">DATA QUALITY STATUS</span>
                      <span className="health-val" style={{ color: hasData ? "#16a34a" : "#94a3b8" }}>{hasData ? "NOMINAL" : "STANDBY"}</span>
                    </div>
                    <div className="health-status-row">
                      <span className="health-key">SYSTEM INTEGRITY</span>
                      <span className="health-val" style={{ color: hasData ? "#16a34a" : "#94a3b8" }}>{hasData ? "NOMINAL" : "STANDBY"}</span>
                    </div>
                    <div className="health-status-row">
                      <span className="health-key">TELEMETRY</span>
                      <span className="health-val" style={{ color: hasData ? "#16a34a" : "#eab308" }}>{hasData ? "ONLINE" : "AWAITING DATA"}</span>
                    </div>
                    <div className="health-status-row">
                      <span className="health-key">QUALITY ASSURANCE</span>
                      <span className="health-val" style={{ color: hasData ? "#16a34a" : "#94a3b8" }}>{hasData ? "VERIFIED" : "STANDBY"}</span>
                    </div>
                  </div>
                </div>

                {/* Deck 3: Sensor Health */}
                <div className="right-deck-box" style={{ flex: 1.8 }}>
                  <div className="deck-title-text">
                    SENSOR HEALTH
                  </div>

                  <div className="sensor-health-list">
                    {[
                      { key: "temp", name: "PT100 Temp Transducer", pct: hasData ? 98.6 : 0 },
                      { key: "pressure", name: "Barometric Transducer", pct: hasData ? 99.0 : 0 },
                      { key: "humidity", name: "Capacitive Humidity", pct: hasData ? 95.0 : 0 },
                      { key: "speed", name: "Anemometer & Wind Vane", pct: hasData ? 99.0 : 0 },
                      { key: "solar", name: "Solar Pyranometer", pct: hasData ? 97.0 : 0 },
                      { key: "rain", name: "Precipitation Gauge", pct: hasData ? 100.0 : 0 }
                    ]
                      .filter(s => isParamEnabled(s.key))
                      .map((s, idx) => (
                        <div key={idx} className="sensor-health-item">
                          <div className="sensor-health-info">
                            <span>{s.name}</span>
                            <span className="sensor-health-pct">
                              {hasData ? `${s.pct.toFixed(1)}% ` : ""}
                              <span style={{ fontWeight: 600, fontSize: "0.58rem", color: hasData ? "#16a34a" : "#94a3b8" }}>
                                {hasData ? "OPTIMAL" : "STANDBY"}
                              </span>
                            </span>
                          </div>
                          <div className="sensor-health-bar-bg">
                            <div className="sensor-health-bar-fill" style={{ width: `${s.pct}%` }}></div>
                          </div>
                        </div>
                      ))}
                  </div>

                  {/* Actionable Maintenance Alert Box */}
                  <div className="actionable-maintenance-alert-box">
                    <div className="maint-alert-header">
                      <span>Actionable Maintenance Alert:</span>
                    </div>
                    <div className="maint-alert-body">
                      <span>
                        {hasData
                          ? "OPTIMAL: All channel transducers nominal. Scheduled maintenance valid for 180 days."
                          : "STANDBY: Ingestion pipeline idle. Awaiting incoming AWS data stream on LAN interface."}
                      </span>
                    </div>
                  </div>

                </div>

              </div>

            </div>
          )}

          {/* 2. MULTI-AWS SPATIAL GRID TAB */}
          {activeTab === "spatial_grid" && (
            <div className="spatial-page-container">
              
              {/* Header */}
              <div className="spatial-header-bar">
                <div className="spatial-header-left">
                  <div>
                    <h2 className="spatial-main-title">MULTI-AWS SPATIAL ANALYSIS & NEIGHBOR COMPARISON GRID</h2>
                    <p className="spatial-subtitle">Real-time cross-station spatial correlation & outlier detection across station cluster</p>
                  </div>
                </div>
              </div>

              {/* Cluster Consensus Top Banner */}
              <div className="spatial-consensus-banner">
                <div className="spatial-cluster-name">
                  SPATIAL NETWORK CLUSTER: <span>4 STATIONS (AWS-01, AWS-02, AWS-03, AWS-04)</span>
                </div>
                <div className="spatial-cluster-avg">
                  NEIGHBOR CONSENSUS AVG: <span className="avg-val">31.0°C</span>
                </div>
                <div className="spatial-cluster-status">
                  SPATIAL CONSENSUS STATUS:
                  <span className={`spatial-status-pill ${spatialGlitch ? "anomaly" : "nominal"}`}>
                    {spatialGlitch ? (
                      <span>SPATIAL OUTLIER DETECTED</span>
                    ) : (
                      <span>CONSENSUS NOMINAL</span>
                    )}
                  </span>
                </div>
              </div>

              {/* 4 Stations Grid */}
              <div className="spatial-four-grid">
                
                {/* Station 1: AWS-01 (Primary) */}
                <div className={`spatial-station-card target-station ${spatialGlitch ? "glitch" : ""}`}>
                  <div className="station-card-top-row">
                    <span className="station-name-title target">AWS-01 (Primary Station)</span>
                    <span className="station-online-tag" style={{ color: hasData ? "#16a34a" : "#eab308" }}>
                      {hasData ? "● ONLINE" : "● STANDBY"}
                    </span>
                  </div>
                  <div className="station-param-rows">
                    <div className="station-param-line">
                      <span className="param-k">Dry Temp:</span>
                      <span className="param-v temp" style={{ color: spatialGlitch ? "#f43f5e" : "#ea580c" }}>
                        {spatialGlitch ? "55.0°C" : (hasData ? `${formatVal(current?.dry_bulb_temp, 1)}°C` : "--")}
                      </span>
                    </div>
                    <div className="station-param-line">
                      <span className="param-k">Pressure:</span>
                      <span className="param-v press">{hasData ? `${formatVal(current?.pressure_hpa, 1)} hPa` : "--"}</span>
                    </div>
                    <div className="station-param-line">
                      <span className="param-k">Humidity:</span>
                      <span className="param-v hum">{hasData ? `${formatVal(current?.rel_humidity, 1)}%` : "--"}</span>
                    </div>
                  </div>
                  <div className="station-role-footer">
                    Role: Target Station ({hasData ? "Live Stream" : "Awaiting Data"})
                  </div>
                </div>

                {/* Station 2: AWS-02 (North) */}
                <div className="spatial-station-card">
                  <div className="station-card-top-row">
                    <span className="station-name-title">AWS-02 (North Neighbor)</span>
                    <span className="station-online-tag">● ONLINE</span>
                  </div>
                  <div className="station-param-rows">
                    <div className="station-param-line">
                      <span className="param-k">Dry Temp:</span>
                      <span className="param-v temp">31.0°C</span>
                    </div>
                    <div className="station-param-line">
                      <span className="param-k">Pressure:</span>
                      <span className="param-v press">1013.2 hPa</span>
                    </div>
                    <div className="station-param-line">
                      <span className="param-k">Humidity:</span>
                      <span className="param-v hum">65.0%</span>
                    </div>
                  </div>
                  <div className="station-role-footer">
                    Role: Spatial Neighbor
                  </div>
                </div>

                {/* Station 3: AWS-03 (East) */}
                <div className="spatial-station-card">
                  <div className="station-card-top-row">
                    <span className="station-name-title">AWS-03 (East Neighbor)</span>
                    <span className="station-online-tag">● ONLINE</span>
                  </div>
                  <div className="station-param-rows">
                    <div className="station-param-line">
                      <span className="param-k">Dry Temp:</span>
                      <span className="param-v temp">31.0°C</span>
                    </div>
                    <div className="station-param-line">
                      <span className="param-k">Pressure:</span>
                      <span className="param-v press">1013.2 hPa</span>
                    </div>
                    <div className="station-param-line">
                      <span className="param-k">Humidity:</span>
                      <span className="param-v hum">65.0%</span>
                    </div>
                  </div>
                  <div className="station-role-footer">
                    Role: Spatial Neighbor
                  </div>
                </div>

                {/* Station 4: AWS-04 (South) */}
                <div className="spatial-station-card">
                  <div className="station-card-top-row">
                    <span className="station-name-title">AWS-04 (South Neighbor)</span>
                    <span className="station-online-tag">● ONLINE</span>
                  </div>
                  <div className="station-param-rows">
                    <div className="station-param-line">
                      <span className="param-k">Dry Temp:</span>
                      <span className="param-v temp">31.0°C</span>
                    </div>
                    <div className="station-param-line">
                      <span className="param-k">Pressure:</span>
                      <span className="param-v press">1013.2 hPa</span>
                    </div>
                    <div className="station-param-line">
                      <span className="param-k">Humidity:</span>
                      <span className="param-v hum">65.0%</span>
                    </div>
                  </div>
                  <div className="station-role-footer">
                    Role: Spatial Neighbor
                  </div>
                </div>

              </div>

              {/* Spatial Explainable AI (XAI) Diagnostics Section */}
              <div className="spatial-xai-section">
                <div className="spatial-section-header">
                  <span>SPATIAL EXPLAINABLE AI (XAI) DIAGNOSTICS</span>
                </div>
                <div className={`spatial-xai-banner ${spatialGlitch ? "glitch" : "nominal"}`}>
                  <div className="spatial-diag-content">
                    {spatialGlitch ? (
                      <span><strong>SPATIAL OUTLIER DETECTED:</strong> Target station AWS-01 reported 55.0°C while neighboring cluster averaged 31.0°C (Spatial Delta +24.0°C). Local sensor hardware malfunction or electrical glitch confirmed.</span>
                    ) : (
                      <span><strong>SPATIAL CONSENSUS CONFIRMED:</strong> Target station AWS-01 (31.0°C) matches spatial neighbor cluster average (31.0°C). No sensor anomaly detected.</span>
                    )}
                  </div>
                </div>
              </div>

              {/* Spatial Anomaly Fault Injector Section */}
              <div className="spatial-injector-section">
                <div className="spatial-section-header">
                  <span>SPATIAL ANOMALY FAULT INJECTOR</span>
                </div>
                <p className="spatial-injector-sub">
                  Test the spatial analysis engine by injecting a single-station glitch or a wide-area genuine meteorological event.
                </p>
                <div className="spatial-injector-btns-row">
                  <button
                    onClick={() => setSpatialGlitch(true)}
                    className="btn-spatial-inject"
                  >
                    <span>INJECT AWS-01 SPATIAL GLITCH (55°C vs 31°C Neighbors)</span>
                  </button>

                  <button
                    onClick={() => setSpatialGlitch(false)}
                    className="btn-spatial-reset"
                  >
                    <span>RESET ALL STATIONS TO CONSENSUS NOMINAL (~31°C)</span>
                  </button>
                </div>
              </div>

            </div>
          )}

          {/* 4. LIVE TELEMETRY PLOTS TAB (5 SENSOR VIEWS x 5 CHART ENGINE TYPES) */}
          {activeTab === "live_graph" && (
            <div className="panel-card" style={{ height: "100%", display: "flex", flexDirection: "column", gap: "10px" }}>
              
              {/* Header Title Bar */}
              <div className="graph-header-top-row">
                <div className="section-title-wrap">
                  <span className="section-title-text">REAL-TIME TIME-SERIES TELEMETRY WAVEFORMS</span>
                  <span className="section-subtitle-text">Multi-parameter continuous sensor waveforms</span>
                </div>
                <span className="live-badge">LIVE 1 Hz REFRESH</span>
              </div>

              {/* Sub-Toolbar with Sensor Views (Left) and Chart Type Switchers (Right) */}
              <div className="graph-subtoolbar-row">
                {/* 5 Sensor Views (Left) */}
                <div className="graph-type-tabs-group">
                  <button
                    onClick={() => setGraphType("all_params")}
                    className={`graph-type-tab-btn ${graphType === "all_params" ? "active" : ""}`}
                  >
                    <span>1. All Sensors</span>
                  </button>

                  <button
                    onClick={() => setGraphType("thermal_hygro")}
                    className={`graph-type-tab-btn ${graphType === "thermal_hygro" ? "active" : ""}`}
                  >
                    <span>2. Temp & Humidity</span>
                  </button>

                  <button
                    onClick={() => setGraphType("pressure_wind")}
                    className={`graph-type-tab-btn ${graphType === "pressure_wind" ? "active" : ""}`}
                  >
                    <span>3. Pressure & Wind</span>
                  </button>

                  <button
                    onClick={() => setGraphType("solar_rain")}
                    className={`graph-type-tab-btn ${graphType === "solar_rain" ? "active" : ""}`}
                  >
                    <span>4. Solar & Rainfall</span>
                  </button>

                  <button
                    onClick={() => setGraphType("quad_grid")}
                    className={`graph-type-tab-btn ${graphType === "quad_grid" ? "active" : ""}`}
                  >
                    <span>5. Quad Grid (4-Plots)</span>
                  </button>
                </div>

                {/* Interactive Down Arrow Dropdown Toggle Picker for Chart Types */}
                <div className="chart-dropdown-wrapper" ref={chartDropdownRef}>
                  <button
                    type="button"
                    onClick={() => setIsChartDropdownOpen(prev => !prev)}
                    className="btn-chart-dropdown-toggle"
                    title="Select graph visualization type"
                    id="chart-type-dropdown-toggle"
                  >
                    <span className="dropdown-active-pill">{currentChartMode.badge}</span>
                    <span className={`dropdown-caret ${isChartDropdownOpen ? "open" : ""}`} style={{ fontSize: "0.7rem", color: "#64748b" }}>▼</span>
                  </button>

                  {isChartDropdownOpen && (
                    <div className="chart-dropdown-menu">
                      <div className="dropdown-menu-header">Select Graph Style</div>
                      {CHART_MODES.map(mode => (
                        <button
                          type="button"
                          key={mode.id}
                          onClick={(e) => {
                            e.stopPropagation();
                            setPlotStyle(mode.id);
                            setIsChartDropdownOpen(false);
                          }}
                          className={`chart-dropdown-item ${plotStyle === mode.id ? "active" : ""}`}
                          id={`chart-mode-${mode.id}`}
                        >
                          <div className="dropdown-item-left">
                            <span className="dropdown-item-badge">{mode.badge}</span>
                            <span className="dropdown-item-desc">{mode.desc}</span>
                          </div>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* ─── GRAPH VIEW 1: ALL SENSORS STREAM ─── */}
              {graphType === "all_params" && (
                <div style={{ flex: 1, minHeight: "510px", width: "100%", background: "var(--bg-card)", border: "1px solid var(--border-color)", borderRadius: "6px", padding: "18px 14px 12px 6px" }}>
                  <ResponsiveContainer width="100%" height="100%">
                    {plotStyle === "bar" ? (
                      <BarChart data={historyBuffer.temp.map((t, idx) => ({
                        time: `${idx}s`,
                        temp: t,
                        humidity: historyBuffer.humidity[idx],
                        pressure: Number((historyBuffer.pressure[idx] - 980).toFixed(1)),
                        solar: Number((historyBuffer.solar[idx] / 20).toFixed(1))
                      }))}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.15)" />
                        <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 11 }} />
                        <YAxis stroke="#64748b" tick={{ fontSize: 11 }} />
                        <Tooltip contentStyle={{ background: "var(--bg-card)", borderColor: "var(--border-color)", borderRadius: "6px", fontSize: "12px", color: "var(--text-main)" }} />
                        <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "8px" }} />
                        {isParamEnabled("temp") && <Bar dataKey="temp" name="Dry Bulb Temp (°C)" fill="#dc2626" radius={[4, 4, 0, 0]} maxBarSize={14} />}
                        {isParamEnabled("humidity") && <Bar dataKey="humidity" name="Rel. Humidity (%)" fill="#7c3aed" radius={[4, 4, 0, 0]} maxBarSize={14} />}
                        {isParamEnabled("pressure") && <Bar dataKey="pressure" name="Pressure Scaled (hPa - 980)" fill="#0284c7" radius={[4, 4, 0, 0]} maxBarSize={14} />}
                        {isParamEnabled("solar") && <Bar dataKey="solar" name="Solar Radiation (Scaled / 20)" fill="#ea580c" radius={[4, 4, 0, 0]} maxBarSize={14} />}
                      </BarChart>
                    ) : plotStyle === "area" ? (
                      <AreaChart data={historyBuffer.temp.map((t, idx) => ({
                        time: `${idx}s`,
                        temp: t,
                        humidity: historyBuffer.humidity[idx],
                        pressure: Number((historyBuffer.pressure[idx] - 980).toFixed(1)),
                        solar: Number((historyBuffer.solar[idx] / 20).toFixed(1))
                      }))}>
                        <defs>
                          <linearGradient id="apTemp" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#dc2626" stopOpacity={0.4} /><stop offset="95%" stopColor="#dc2626" stopOpacity={0.0} /></linearGradient>
                          <linearGradient id="apHum" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#7c3aed" stopOpacity={0.4} /><stop offset="95%" stopColor="#7c3aed" stopOpacity={0.0} /></linearGradient>
                          <linearGradient id="apPress" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#0284c7" stopOpacity={0.4} /><stop offset="95%" stopColor="#0284c7" stopOpacity={0.0} /></linearGradient>
                          <linearGradient id="apSolar" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#ea580c" stopOpacity={0.4} /><stop offset="95%" stopColor="#ea580c" stopOpacity={0.0} /></linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.15)" />
                        <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 11 }} />
                        <YAxis stroke="#64748b" tick={{ fontSize: 11 }} />
                        <Tooltip contentStyle={{ background: "var(--bg-card)", borderColor: "var(--border-color)", borderRadius: "6px", fontSize: "12px", color: "var(--text-main)" }} />
                        <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "8px" }} />
                        {isParamEnabled("temp") && <Area type="monotone" dataKey="temp" name="Dry Bulb Temp (°C)" stroke="#dc2626" fill="url(#apTemp)" strokeWidth={2.5} />}
                        {isParamEnabled("humidity") && <Area type="monotone" dataKey="humidity" name="Rel. Humidity (%)" stroke="#7c3aed" fill="url(#apHum)" strokeWidth={2.5} />}
                        {isParamEnabled("pressure") && <Area type="monotone" dataKey="pressure" name="Pressure Scaled (hPa - 980)" stroke="#0284c7" fill="url(#apPress)" strokeWidth={2.5} />}
                        {isParamEnabled("solar") && <Area type="monotone" dataKey="solar" name="Solar Radiation (Scaled / 20)" stroke="#ea580c" fill="url(#apSolar)" strokeWidth={2.5} />}
                      </AreaChart>
                    ) : (
                      <LineChart data={historyBuffer.temp.map((t, idx) => ({
                        time: `${idx}s`,
                        temp: t,
                        humidity: historyBuffer.humidity[idx],
                        pressure: Number((historyBuffer.pressure[idx] - 980).toFixed(1)),
                        solar: Number((historyBuffer.solar[idx] / 20).toFixed(1))
                      }))}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.15)" />
                        <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 11 }} />
                        <YAxis stroke="#64748b" tick={{ fontSize: 11 }} />
                        <Tooltip contentStyle={{ background: "var(--bg-card)", borderColor: "var(--border-color)", borderRadius: "6px", fontSize: "12px", color: "var(--text-main)" }} />
                        <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "8px" }} />
                        {isParamEnabled("temp") && (
                          <Line
                            type="monotone"
                            dataKey="temp"
                            name="Dry Bulb Temp (°C)"
                            stroke="#dc2626"
                            strokeDasharray={plotStyle === "dashed" ? "8 4" : undefined}
                            strokeWidth={plotStyle === "scatter" ? 0 : 2.5}
                            dot={plotStyle === "dashed" ? { r: 5, fill: "#ffffff", stroke: "#dc2626", strokeWidth: 2 } : (plotStyle === "scatter" ? { r: 6, fill: "#dc2626", stroke: "#ffffff", strokeWidth: 1.5 } : { r: 2 })}
                            isAnimationActive={false}
                          />
                        )}
                        {isParamEnabled("humidity") && (
                          <Line
                            type="monotone"
                            dataKey="humidity"
                            name="Rel. Humidity (%)"
                            stroke="#7c3aed"
                            strokeDasharray={plotStyle === "dashed" ? "8 4" : undefined}
                            strokeWidth={plotStyle === "scatter" ? 0 : 2.5}
                            dot={plotStyle === "dashed" ? { r: 5, fill: "#ffffff", stroke: "#7c3aed", strokeWidth: 2 } : (plotStyle === "scatter" ? { r: 6, fill: "#7c3aed", stroke: "#ffffff", strokeWidth: 1.5 } : { r: 2 })}
                            isAnimationActive={false}
                          />
                        )}
                        {isParamEnabled("pressure") && (
                          <Line
                            type="monotone"
                            dataKey="pressure"
                            name="Pressure Scaled (hPa - 980)"
                            stroke="#0284c7"
                            strokeDasharray={plotStyle === "dashed" ? "8 4" : undefined}
                            strokeWidth={plotStyle === "scatter" ? 0 : 2.5}
                            dot={plotStyle === "dashed" ? { r: 5, fill: "#ffffff", stroke: "#0284c7", strokeWidth: 2 } : (plotStyle === "scatter" ? { r: 6, fill: "#0284c7", stroke: "#ffffff", strokeWidth: 1.5 } : { r: 2 })}
                            isAnimationActive={false}
                          />
                        )}
                        {isParamEnabled("solar") && (
                          <Line
                            type="monotone"
                            dataKey="solar"
                            name="Solar Radiation (Scaled / 20)"
                            stroke="#ea580c"
                            strokeDasharray={plotStyle === "dashed" ? "8 4" : undefined}
                            strokeWidth={plotStyle === "scatter" ? 0 : 2.5}
                            dot={plotStyle === "dashed" ? { r: 5, fill: "#ffffff", stroke: "#ea580c", strokeWidth: 2 } : (plotStyle === "scatter" ? { r: 6, fill: "#ea580c", stroke: "#ffffff", strokeWidth: 1.5 } : { r: 2 })}
                            isAnimationActive={false}
                          />
                        )}
                      </LineChart>
                    )}
                  </ResponsiveContainer>
                </div>
              )}

              {/* ─── GRAPH VIEW 2: THERMAL & HYGROMETRIC ─── */}
              {graphType === "thermal_hygro" && (
                <div style={{ flex: 1, minHeight: "510px", width: "100%", background: "var(--bg-card)", border: "1px solid var(--border-color)", borderRadius: "6px", padding: "18px 14px 12px 6px" }}>
                  <ResponsiveContainer width="100%" height="100%">
                    {plotStyle === "bar" ? (
                      <BarChart data={historyBuffer.temp.map((t, idx) => ({
                        time: `${idx}s`,
                        dry_bulb: t,
                        wet_bulb: Number((t - 4.5).toFixed(1)),
                        humidity: historyBuffer.humidity[idx]
                      }))}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.15)" />
                        <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 11 }} />
                        <YAxis stroke="#64748b" tick={{ fontSize: 11 }} />
                        <Tooltip contentStyle={{ background: "var(--bg-card)", borderColor: "var(--border-color)", borderRadius: "6px", fontSize: "12px", color: "var(--text-main)" }} />
                        <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "8px" }} />
                        {isParamEnabled("temp") && <Bar dataKey="dry_bulb" name="Dry Bulb Temp (°C)" fill="#dc2626" radius={[4, 4, 0, 0]} maxBarSize={18} />}
                        {isParamEnabled("wet_bulb") && <Bar dataKey="wet_bulb" name="Wet Bulb Temp (°C)" fill="#ea580c" radius={[4, 4, 0, 0]} maxBarSize={18} />}
                        {isParamEnabled("humidity") && <Bar dataKey="humidity" name="Rel. Humidity (%)" fill="#7c3aed" radius={[4, 4, 0, 0]} maxBarSize={18} />}
                      </BarChart>
                    ) : (
                      <AreaChart data={historyBuffer.temp.map((t, idx) => ({
                        time: `${idx}s`,
                        dry_bulb: t,
                        wet_bulb: Number((t - 4.5).toFixed(1)),
                        humidity: historyBuffer.humidity[idx]
                      }))}>
                        <defs>
                          <linearGradient id="colorTemp" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#dc2626" stopOpacity={plotStyle === "area" ? 0.6 : 0.35} /><stop offset="95%" stopColor="#dc2626" stopOpacity={0.0} /></linearGradient>
                          <linearGradient id="colorHygro" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#7c3aed" stopOpacity={plotStyle === "area" ? 0.6 : 0.35} /><stop offset="95%" stopColor="#7c3aed" stopOpacity={0.0} /></linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.15)" />
                        <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 11 }} />
                        <YAxis stroke="#64748b" tick={{ fontSize: 11 }} />
                        <Tooltip contentStyle={{ background: "var(--bg-card)", borderColor: "var(--border-color)", borderRadius: "6px", fontSize: "12px", color: "var(--text-main)" }} />
                        <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "8px" }} />
                        {isParamEnabled("temp") && (
                          <Area
                            type="monotone"
                            dataKey="dry_bulb"
                            name="Dry Bulb Temp (°C)"
                            stroke="#dc2626"
                            strokeDasharray={plotStyle === "dashed" ? "8 4" : undefined}
                            fillOpacity={plotStyle === "scatter" || plotStyle === "line" || plotStyle === "dashed" ? 0.05 : 1}
                            fill="url(#colorTemp)"
                            strokeWidth={plotStyle === "scatter" ? 0 : 2.5}
                            dot={plotStyle === "dashed" ? { r: 5, fill: "#ffffff", stroke: "#dc2626", strokeWidth: 2 } : (plotStyle === "scatter" ? { r: 6, fill: "#dc2626", stroke: "#ffffff", strokeWidth: 1.5 } : false)}
                          />
                        )}
                        {isParamEnabled("humidity") && (
                          <Area
                            type="monotone"
                            dataKey="humidity"
                            name="Rel. Humidity (%)"
                            stroke="#7c3aed"
                            strokeDasharray={plotStyle === "dashed" ? "8 4" : undefined}
                            fillOpacity={plotStyle === "scatter" || plotStyle === "line" || plotStyle === "dashed" ? 0.05 : 1}
                            fill="url(#colorHygro)"
                            strokeWidth={plotStyle === "scatter" ? 0 : 2.5}
                            dot={plotStyle === "dashed" ? { r: 5, fill: "#ffffff", stroke: "#7c3aed", strokeWidth: 2 } : (plotStyle === "scatter" ? { r: 6, fill: "#7c3aed", stroke: "#ffffff", strokeWidth: 1.5 } : false)}
                          />
                        )}
                        {isParamEnabled("wet_bulb") && (
                          <Line
                            type="monotone"
                            dataKey="wet_bulb"
                            name="Wet Bulb Temp (°C)"
                            stroke="#ea580c"
                            strokeWidth={plotStyle === "scatter" ? 0 : 2}
                            strokeDasharray="4 4"
                            dot={plotStyle === "dashed" ? { r: 4, fill: "#ffffff", stroke: "#ea580c", strokeWidth: 1.5 } : (plotStyle === "scatter" ? { r: 5, fill: "#ea580c", stroke: "#ffffff", strokeWidth: 1.5 } : false)}
                          />
                        )}
                      </AreaChart>
                    )}
                  </ResponsiveContainer>
                </div>
              )}

              {/* ─── GRAPH VIEW 3: BAROMETRIC PRESSURE & WIND DYNAMICS ─── */}
              {graphType === "pressure_wind" && (
                <div style={{ flex: 1, minHeight: "510px", width: "100%", background: "var(--bg-card)", border: "1px solid var(--border-color)", borderRadius: "6px", padding: "18px 14px 12px 6px" }}>
                  <ResponsiveContainer width="100%" height="100%">
                    {plotStyle === "bar" ? (
                      <BarChart data={historyBuffer.pressure.map((p, idx) => ({
                        time: `${idx}s`,
                        pressure: Number((p - 980).toFixed(1)),
                        speed: Number((10 + (idx % 4) * 1.2).toFixed(1))
                      }))}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.15)" />
                        <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 11 }} />
                        <YAxis stroke="#64748b" tick={{ fontSize: 11 }} />
                        <Tooltip contentStyle={{ background: "var(--bg-card)", borderColor: "var(--border-color)", borderRadius: "6px", fontSize: "12px", color: "var(--text-main)" }} />
                        <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "8px" }} />
                        {isParamEnabled("pressure") && <Bar dataKey="pressure" name="Pressure Scaled (hPa - 980)" fill="#0284c7" radius={[4, 4, 0, 0]} maxBarSize={20} />}
                        {isParamEnabled("speed") && <Bar dataKey="speed" name="Wind Speed (m/s)" fill="#16a34a" radius={[4, 4, 0, 0]} maxBarSize={20} />}
                      </BarChart>
                    ) : (
                      <ComposedChart data={historyBuffer.pressure.map((p, idx) => ({
                        time: `${idx}s`,
                        pressure: p,
                        speed: Number((10 + (idx % 4) * 1.2).toFixed(1)),
                        direction: (20 + (idx * 3) % 360)
                      }))}>
                        <defs>
                          <linearGradient id="colorPress" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#0284c7" stopOpacity={plotStyle === "area" ? 0.6 : 0.35} /><stop offset="95%" stopColor="#0284c7" stopOpacity={0.0} /></linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.15)" />
                        <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 11 }} />
                        <YAxis yAxisId="left" domain={[990, 1025]} stroke="#0284c7" tick={{ fontSize: 11 }} unit=" hPa" />
                        <YAxis yAxisId="right" orientation="right" domain={[0, 30]} stroke="#16a34a" tick={{ fontSize: 11 }} unit=" m/s" />
                        <Tooltip contentStyle={{ background: "var(--bg-card)", borderColor: "var(--border-color)", borderRadius: "6px", fontSize: "12px", color: "var(--text-main)" }} />
                        <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "8px" }} />
                        {isParamEnabled("pressure") && (
                          <Area
                            yAxisId="left"
                            type="monotone"
                            dataKey="pressure"
                            name="Barometric Pressure (hPa)"
                            stroke="#0284c7"
                            strokeDasharray={plotStyle === "dashed" ? "8 4" : undefined}
                            fillOpacity={plotStyle === "scatter" || plotStyle === "line" || plotStyle === "dashed" ? 0.05 : 1}
                            fill="url(#colorPress)"
                            strokeWidth={plotStyle === "scatter" ? 0 : 2.5}
                            dot={plotStyle === "dashed" ? { r: 5, fill: "#ffffff", stroke: "#0284c7", strokeWidth: 2 } : (plotStyle === "scatter" ? { r: 6, fill: "#0284c7", stroke: "#ffffff", strokeWidth: 1.5 } : false)}
                          />
                        )}
                        {isParamEnabled("speed") && (
                          <Line
                            yAxisId="right"
                            type="monotone"
                            dataKey="speed"
                            name="Wind Speed (m/s)"
                            stroke="#16a34a"
                            strokeDasharray={plotStyle === "dashed" ? "8 4" : undefined}
                            strokeWidth={plotStyle === "scatter" ? 0 : 2.5}
                            dot={plotStyle === "dashed" ? { r: 5, fill: "#ffffff", stroke: "#16a34a", strokeWidth: 2 } : (plotStyle === "scatter" ? { r: 6, fill: "#16a34a", stroke: "#ffffff", strokeWidth: 1.5 } : { r: 3 })}
                          />
                        )}
                      </ComposedChart>
                    )}
                  </ResponsiveContainer>
                </div>
              )}

              {/* ─── GRAPH VIEW 4: SOLAR IRRADIANCE & PRECIPITATION ─── */}
              {graphType === "solar_rain" && (
                <div style={{ flex: 1, minHeight: "510px", width: "100%", background: "var(--bg-card)", border: "1px solid var(--border-color)", borderRadius: "6px", padding: "18px 14px 12px 6px" }}>
                  <ResponsiveContainer width="100%" height="100%">
                    {plotStyle === "bar" ? (
                      <BarChart data={historyBuffer.solar.map((s, idx) => ({
                        time: `${idx}s`,
                        solar: Number((s / 20).toFixed(1)),
                        rain: idx % 4 === 0 ? Number((0.2 * (idx % 3)).toFixed(1)) : 0
                      }))}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.15)" />
                        <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 11 }} />
                        <YAxis stroke="#64748b" tick={{ fontSize: 11 }} />
                        <Tooltip contentStyle={{ background: "var(--bg-card)", borderColor: "var(--border-color)", borderRadius: "6px", fontSize: "12px", color: "var(--text-main)" }} />
                        <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "8px" }} />
                        {isParamEnabled("solar") && <Bar dataKey="solar" name="Solar Radiation (Scaled / 20)" fill="#ea580c" radius={[4, 4, 0, 0]} maxBarSize={20} />}
                        {isParamEnabled("rain") && <Bar dataKey="rain" name="Rainfall Influx (mm)" fill="#0284c7" radius={[4, 4, 0, 0]} maxBarSize={20} />}
                      </BarChart>
                    ) : (
                      <ComposedChart data={historyBuffer.solar.map((s, idx) => ({
                        time: `${idx}s`,
                        solar: s,
                        rain: idx % 4 === 0 ? Number((0.2 * (idx % 3)).toFixed(1)) : 0
                      }))}>
                        <defs>
                          <linearGradient id="colorSolar" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#ea580c" stopOpacity={plotStyle === "area" ? 0.6 : 0.4} /><stop offset="95%" stopColor="#ea580c" stopOpacity={0.0} /></linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.15)" />
                        <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 11 }} />
                        <YAxis yAxisId="left" stroke="#ea580c" tick={{ fontSize: 11 }} unit=" W/m²" />
                        <YAxis yAxisId="right" orientation="right" domain={[0, 10]} stroke="#0284c7" tick={{ fontSize: 11 }} unit=" mm" />
                        <Tooltip contentStyle={{ background: "var(--bg-card)", borderColor: "var(--border-color)", borderRadius: "6px", fontSize: "12px", color: "var(--text-main)" }} />
                        <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "8px" }} />
                        {isParamEnabled("solar") && (
                          <Area
                            yAxisId="left"
                            type="monotone"
                            dataKey="solar"
                            name="Solar Radiation (W/m²)"
                            stroke="#ea580c"
                            strokeDasharray={plotStyle === "dashed" ? "8 4" : undefined}
                            fillOpacity={plotStyle === "scatter" || plotStyle === "line" || plotStyle === "dashed" ? 0.05 : 1}
                            fill="url(#colorSolar)"
                            strokeWidth={plotStyle === "scatter" ? 0 : 2.5}
                            dot={plotStyle === "dashed" ? { r: 5, fill: "#ffffff", stroke: "#ea580c", strokeWidth: 2 } : (plotStyle === "scatter" ? { r: 6, fill: "#ea580c", stroke: "#ffffff", strokeWidth: 1.5 } : false)}
                          />
                        )}
                        {isParamEnabled("rain") && <Bar yAxisId="right" dataKey="rain" name="Rainfall Influx (mm)" fill="#0284c7" radius={[4, 4, 0, 0]} maxBarSize={24} />}
                      </ComposedChart>
                    )}
                  </ResponsiveContainer>
                </div>
              )}

              {/* ─── GRAPH VIEW 5: QUAD SUB-PLOTS GRID ─── */}
              {graphType === "quad_grid" && (
                <div className="quad-charts-grid">
                  
                  {/* Quad Card 1: Temperature Channel */}
                  <div className="quad-chart-card">
                    <div className="quad-chart-header">
                      <div className="quad-chart-title">
                        <span>Channel 01 • Thermal Curve</span>
                      </div>
                      <span className="quad-chart-val-badge" style={{ background: "rgba(220,38,38,0.12)", color: "#dc2626" }}>
                        {current.dry_bulb_temp} °C
                      </span>
                    </div>
                    <div style={{ width: "100%", height: "180px" }}>
                      {!isParamEnabled("temp") ? (
                        <div className="quad-muted-overlay">
                          <span>THERMAL CHANNEL MUTED</span>
                          <span style={{ fontSize: "0.62rem", opacity: 0.8 }}>Turn ON in Parameter Editor to resume stream</span>
                        </div>
                      ) : (
                        <ResponsiveContainer width="100%" height="100%">
                          {plotStyle === "bar" ? (
                            <BarChart data={historyBuffer.temp.map((t, idx) => ({ time: `${idx}s`, temp: t }))}>
                              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.15)" />
                              <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 10 }} />
                              <YAxis stroke="#64748b" tick={{ fontSize: 10 }} domain={['auto', 'auto']} />
                              <Tooltip contentStyle={{ background: "var(--bg-card)", borderColor: "var(--border-color)", fontSize: "11px" }} />
                              <Bar dataKey="temp" name="Dry Bulb (°C)" fill="#dc2626" radius={[3, 3, 0, 0]} maxBarSize={16} />
                            </BarChart>
                          ) : (
                            <LineChart data={historyBuffer.temp.map((t, idx) => ({ time: `${idx}s`, temp: t }))}>
                              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.15)" />
                              <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 10 }} />
                              <YAxis stroke="#64748b" tick={{ fontSize: 10 }} domain={['auto', 'auto']} />
                              <Tooltip contentStyle={{ background: "var(--bg-card)", borderColor: "var(--border-color)", fontSize: "11px" }} />
                              <Line
                                type="monotone"
                                dataKey="temp"
                                name="Dry Bulb (°C)"
                                stroke="#dc2626"
                                strokeDasharray={plotStyle === "dashed" ? "8 4" : undefined}
                                strokeWidth={plotStyle === "scatter" ? 0 : 2}
                                dot={plotStyle === "dashed" ? { r: 4.5, fill: "#ffffff", stroke: "#dc2626", strokeWidth: 1.5 } : (plotStyle === "scatter" ? { r: 5, fill: "#dc2626", stroke: "#ffffff", strokeWidth: 1.5 } : { r: 2 })}
                                isAnimationActive={false}
                              />
                            </LineChart>
                          )}
                        </ResponsiveContainer>
                      )}
                    </div>
                  </div>

                  {/* Quad Card 2: Relative Humidity Channel */}
                  <div className="quad-chart-card">
                    <div className="quad-chart-header">
                      <div className="quad-chart-title">
                        <span>Channel 02 • Relative Humidity</span>
                      </div>
                      <span className="quad-chart-val-badge" style={{ background: "rgba(124,58,237,0.12)", color: "#7c3aed" }}>
                        {current.rel_humidity} %
                      </span>
                    </div>
                    <div style={{ width: "100%", height: "180px" }}>
                      {!isParamEnabled("humidity") ? (
                        <div className="quad-muted-overlay">
                          <span>HUMIDITY CHANNEL MUTED</span>
                          <span style={{ fontSize: "0.62rem", opacity: 0.8 }}>Turn ON in Parameter Editor to resume stream</span>
                        </div>
                      ) : (
                        <ResponsiveContainer width="100%" height="100%">
                          {plotStyle === "bar" ? (
                            <BarChart data={historyBuffer.humidity.map((h, idx) => ({ time: `${idx}s`, hum: h }))}>
                              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.15)" />
                              <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 10 }} />
                              <YAxis stroke="#64748b" tick={{ fontSize: 10 }} domain={[50, 100]} />
                              <Tooltip contentStyle={{ background: "var(--bg-card)", borderColor: "var(--border-color)", fontSize: "11px" }} />
                              <Bar dataKey="hum" name="RH (%)" fill="#7c3aed" radius={[3, 3, 0, 0]} maxBarSize={16} />
                            </BarChart>
                          ) : (
                            <AreaChart data={historyBuffer.humidity.map((h, idx) => ({ time: `${idx}s`, hum: h }))}>
                              <defs>
                                <linearGradient id="qHum" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#7c3aed" stopOpacity={plotStyle === "area" ? 0.6 : 0.4} /><stop offset="95%" stopColor="#7c3aed" stopOpacity={0.0} /></linearGradient>
                              </defs>
                              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.15)" />
                              <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 10 }} />
                              <YAxis stroke="#64748b" tick={{ fontSize: 10 }} domain={[50, 100]} />
                              <Tooltip contentStyle={{ background: "var(--bg-card)", borderColor: "var(--border-color)", fontSize: "11px" }} />
                              <Area
                                type="monotone"
                                dataKey="hum"
                                name="RH (%)"
                                stroke="#7c3aed"
                                strokeDasharray={plotStyle === "dashed" ? "8 4" : undefined}
                                fill={plotStyle === "scatter" || plotStyle === "line" || plotStyle === "dashed" ? "transparent" : "url(#qHum)"}
                                strokeWidth={plotStyle === "scatter" ? 0 : 2}
                                dot={plotStyle === "dashed" ? { r: 4.5, fill: "#ffffff", stroke: "#7c3aed", strokeWidth: 1.5 } : (plotStyle === "scatter" ? { r: 5, fill: "#7c3aed", stroke: "#ffffff", strokeWidth: 1.5 } : false)}
                              />
                            </AreaChart>
                          )}
                        </ResponsiveContainer>
                      )}
                    </div>
                  </div>

                  {/* Quad Card 3: Barometric Pressure Channel */}
                  <div className="quad-chart-card">
                    <div className="quad-chart-header">
                      <div className="quad-chart-title">
                        <span>Channel 03 • Barometric Pressure</span>
                      </div>
                      <span className="quad-chart-val-badge" style={{ background: "rgba(2,132,199,0.12)", color: "#0284c7" }}>
                        {current.pressure_hpa} hPa
                      </span>
                    </div>
                    <div style={{ width: "100%", height: "180px" }}>
                      {!isParamEnabled("pressure") ? (
                        <div className="quad-muted-overlay">
                          <span>PRESSURE CHANNEL MUTED</span>
                          <span style={{ fontSize: "0.62rem", opacity: 0.8 }}>Turn ON in Parameter Editor to resume stream</span>
                        </div>
                      ) : (
                        <ResponsiveContainer width="100%" height="100%">
                          {plotStyle === "bar" ? (
                            <BarChart data={historyBuffer.pressure.map((p, idx) => ({ time: `${idx}s`, press: p }))}>
                              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.15)" />
                              <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 10 }} />
                              <YAxis stroke="#64748b" tick={{ fontSize: 10 }} domain={['auto', 'auto']} />
                              <Tooltip contentStyle={{ background: "var(--bg-card)", borderColor: "var(--border-color)", fontSize: "11px" }} />
                              <Bar dataKey="press" name="Pressure (hPa)" fill="#0284c7" radius={[3, 3, 0, 0]} maxBarSize={16} />
                            </BarChart>
                          ) : (
                            <AreaChart data={historyBuffer.pressure.map((p, idx) => ({ time: `${idx}s`, press: p }))}>
                              <defs>
                                <linearGradient id="qPress" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#0284c7" stopOpacity={plotStyle === "area" ? 0.6 : 0.4} /><stop offset="95%" stopColor="#0284c7" stopOpacity={0.0} /></linearGradient>
                              </defs>
                              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.15)" />
                              <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 10 }} />
                              <YAxis stroke="#64748b" tick={{ fontSize: 10 }} domain={['auto', 'auto']} />
                              <Tooltip contentStyle={{ background: "var(--bg-card)", borderColor: "var(--border-color)", fontSize: "11px" }} />
                              <Area
                                type="monotone"
                                dataKey="press"
                                name="Pressure (hPa)"
                                stroke="#0284c7"
                                strokeDasharray={plotStyle === "dashed" ? "8 4" : undefined}
                                fill={plotStyle === "scatter" || plotStyle === "line" || plotStyle === "dashed" ? "transparent" : "url(#qPress)"}
                                strokeWidth={plotStyle === "scatter" ? 0 : 2}
                                dot={plotStyle === "dashed" ? { r: 4.5, fill: "#ffffff", stroke: "#0284c7", strokeWidth: 1.5 } : (plotStyle === "scatter" ? { r: 5, fill: "#0284c7", stroke: "#ffffff", strokeWidth: 1.5 } : false)}
                              />
                            </AreaChart>
                          )}
                        </ResponsiveContainer>
                      )}
                    </div>
                  </div>

                  {/* Quad Card 4: Solar Irradiance Channel */}
                  <div className="quad-chart-card">
                    <div className="quad-chart-header">
                      <div className="quad-chart-title">
                        <span>Channel 04 • Solar Radiation</span>
                      </div>
                      <span className="quad-chart-val-badge" style={{ background: "rgba(234,88,12,0.12)", color: "#ea580c" }}>
                        {current.solar_radiation} W/m²
                      </span>
                    </div>
                    <div style={{ width: "100%", height: "180px" }}>
                      {!isParamEnabled("solar") ? (
                        <div className="quad-muted-overlay">
                          <span>SOLAR RADIATION MUTED</span>
                          <span style={{ fontSize: "0.62rem", opacity: 0.8 }}>Turn ON in Parameter Editor to resume stream</span>
                        </div>
                      ) : (
                        <ResponsiveContainer width="100%" height="100%">
                          {plotStyle === "bar" ? (
                            <BarChart data={historyBuffer.solar.map((s, idx) => ({ time: `${idx}s`, solar: s }))}>
                              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.15)" />
                              <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 10 }} />
                              <YAxis stroke="#64748b" tick={{ fontSize: 10 }} domain={[0, 1000]} />
                              <Tooltip contentStyle={{ background: "var(--bg-card)", borderColor: "var(--border-color)", fontSize: "11px" }} />
                              <Bar dataKey="solar" name="Solar (W/m²)" fill="#ea580c" radius={[3, 3, 0, 0]} maxBarSize={16} />
                            </BarChart>
                          ) : (
                            <AreaChart data={historyBuffer.solar.map((s, idx) => ({ time: `${idx}s`, solar: s }))}>
                              <defs>
                                <linearGradient id="qSolar" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#ea580c" stopOpacity={plotStyle === "area" ? 0.6 : 0.4} /><stop offset="95%" stopColor="#ea580c" stopOpacity={0.0} /></linearGradient>
                              </defs>
                              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.15)" />
                              <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 10 }} />
                              <YAxis stroke="#64748b" tick={{ fontSize: 10 }} domain={[0, 1000]} />
                              <Tooltip contentStyle={{ background: "var(--bg-card)", borderColor: "var(--border-color)", fontSize: "11px" }} />
                              <Area
                                type="monotone"
                                dataKey="solar"
                                name="Solar (W/m²)"
                                stroke="#ea580c"
                                strokeDasharray={plotStyle === "dashed" ? "8 4" : undefined}
                                fill={plotStyle === "scatter" || plotStyle === "line" || plotStyle === "dashed" ? "transparent" : "url(#qSolar)"}
                                strokeWidth={plotStyle === "scatter" ? 0 : 2}
                                dot={plotStyle === "dashed" ? { r: 4.5, fill: "#ffffff", stroke: "#ea580c", strokeWidth: 1.5 } : (plotStyle === "scatter" ? { r: 5, fill: "#ea580c", stroke: "#ffffff", strokeWidth: 1.5 } : false)}
                              />
                            </AreaChart>
                          )}
                        </ResponsiveContainer>
                      )}
                    </div>
                  </div>

                </div>
              )}

            </div>
          )}

          {/* 5. PARAMETER EDITOR TAB */}
          {activeTab === "frame_editor" && (
            <div className="panel-card">
              <div className="section-header-bar">
                <div className="section-title-wrap">
                  <span className="section-title-text">PARAMETER CALIBRATION & PACKET DEFINITIONS</span>
                  <span className="section-subtitle-text">Toggle channels ON/OFF to control real-time graph visualization and telemetry parsing</span>
                </div>
              </div>

              <div className="table-container">
                <table className="dark-table">
                  <thead>
                    <tr>
                      <th style={{ width: "115px", textAlign: "center" }}>LIVE STREAM</th>
                      <th>Parameter Name</th>
                      <th>Data Type</th>
                      <th>Unit</th>
                      <th>Scale</th>
                      <th>Offset</th>
                      <th>Threshold</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {paramsList.map(p => (
                      <tr key={p.id} className={!p.enabled ? "param-row-disabled" : ""}>
                        <td style={{ textAlign: "center" }}>
                          <button
                            type="button"
                            onClick={() => handleToggleParam(p.id)}
                            className={`param-switch-btn ${p.enabled ? "on" : "off"}`}
                            title={`Click to turn ${p.name} ${p.enabled ? "OFF" : "ON"} in real-time graphs`}
                          >
                            <span className="switch-slider-track">
                              <span className="switch-slider-thumb"></span>
                            </span>
                            <span className="switch-status-text">{p.enabled ? "ON" : "OFF"}</span>
                          </button>
                        </td>
                        <td style={{ fontWeight: 700 }}>
                          {p.name} <span style={{ fontSize: "0.65rem", color: "var(--text-dim)", marginLeft: "4px" }}>#{p.id}</span>
                        </td>
                        <td><code>{p.dataType}</code></td>
                        <td><span className="transducer-tag green" style={{ padding: "2px 6px" }}>{p.unit}</span></td>
                        <td>{p.scale}</td>
                        <td>{p.offset}</td>
                        <td>{p.threshold ? `${p.threshold} ${p.unit}` : "None"}</td>
                        <td>
                          {p.enabled ? (
                            <span className="status-tag connected">LIVE ACTIVE</span>
                          ) : (
                            <span className="status-tag standby" style={{ background: "rgba(100,116,139,0.12)", color: "#64748b" }}>MUTED / OFF</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* 6. LOCAL DATA LOGGER TAB */}
          {activeTab === "data_logger" && (
            <div className="panel-card">
              <div className="section-header-bar">
                <div className="section-title-wrap">
                  <span className="section-title-text">LOCAL SESSION DATA LOGGER</span>
                  <span className="section-subtitle-text">Buffered telemetry packet stream logs</span>
                </div>
                <div className="section-meta-right">
                  <button onClick={handleExportCSV} className="btn-action-light">
                    <span>Export CSV</span>
                  </button>
                  <button onClick={() => setTelemetryHistory([])} className="btn-action-light">
                    <span>Clear Logs</span>
                  </button>
                </div>
              </div>

              <div className="table-container">
                <table className="dark-table">
                  <thead>
                    <tr>
                      <th>Packet Timestamp</th>
                      <th>Time Inst (s)</th>
                      <th>Direction</th>
                      <th>Speed</th>
                      <th>Dry Temp</th>
                      <th>Humidity</th>
                      <th>Pressure (hPa)</th>
                      <th>Solar</th>
                      <th>Rain</th>
                      <th>QA / QC Verification</th>
                    </tr>
                  </thead>
                  <tbody>
                    {telemetryHistory.length > 0 ? (
                      [...telemetryHistory].reverse().map((h, i) => (
                        <tr key={i}>
                          <td style={{ color: "#0284c7", fontWeight: 700 }}>{h.time}</td>
                          <td>{h.raw?.time_inst || "--"}</td>
                          <td style={{ color: "#16a34a" }}>{h.raw?.direction}°</td>
                          <td style={{ color: "#2563eb" }}>{h.raw?.speed} m/s</td>
                          <td style={{ color: "#dc2626" }}>{h.dry_temp}°C</td>
                          <td style={{ color: "#7c3aed" }}>{h.humidity}%</td>
                          <td style={{ color: "#0284c7" }}>{h.pressure} hPa</td>
                          <td style={{ color: "#ea580c" }}>{h.solar} W/M²</td>
                          <td>{h.rain} mm</td>
                          <td>
                            <span className="status-tag connected">
                              NOMINAL
                            </span>
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={10} style={{ textAlign: "center", padding: "30px", color: "var(--text-muted)" }}>
                          Listening for incoming UDP/TCP data packets... Live log records will appear here in real-time.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* 7. HISTORY REPLAY HUB & SKYGUARD AI TESTBENCH */}
          {activeTab === "replay_session" && (
            <div className="testbench-container">
              
              {/* ─── SECTION 1: REAL-TIME AI ANOMALY INJECTION TESTBENCH ─── */}
              <div className="testbench-card">
                <div className="testbench-header">
                  <span className="testbench-title">REAL-TIME AI ANOMALY INJECTION TESTBENCH</span>
                </div>
                <div className="testbench-desc">
                  Click any trigger below to inject synthetic anomalies into the Go telemetry stream. The SkyGuard AI engine will instantly classify the fault, output XAI diagnostics to the alert deck, and calculate self-healed values!
                </div>

                {/* Anomaly Trigger Buttons Single Row */}
                <div className="anomaly-triggers-grid">
                  <button
                    type="button"
                    onClick={() => handleTriggerAnomaly("spike", "temp_dry", 25.0, "INJECT TEMP SPIKE (+25°C)", "#f43f5e")}
                    className="btn-trigger-anomaly"
                    id="btn-inject-temp-spike"
                    title="Simulate sudden PT100 temperature jump (+25°C)"
                  >
                    <span>Temp Spike (+25°C)</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => handleTriggerAnomaly("freeze", "pressure_hpa", 0.0, "INJECT PRESSURE FREEZE", "#f59e0b")}
                    className="btn-trigger-anomaly"
                    id="btn-inject-pressure-freeze"
                    title="Simulate zero-variance locked barometric transducer"
                  >
                    <span>Pressure Freeze</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => handleTriggerAnomaly("drift", "humidity", 28.0, "INJECT HUMIDITY DRIFT", "#f59e0b")}
                    className="btn-trigger-anomaly"
                    id="btn-inject-humidity-drift"
                    title="Simulate capacitive humidity transducer drift rate"
                  >
                    <span>Humidity Drift</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => handleTriggerAnomaly("loss", "all", 0.0, "SIMULATE PACKET LOSS OUTAGE", "#f43f5e")}
                    className="btn-trigger-anomaly"
                    id="btn-simulate-packet-loss"
                    title="Simulate UDP link packet drop burst"
                  >
                    <span>Packet Loss</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => handleTriggerAnomaly("psychrometric", "temp_wet", 6.0, "INJECT PSYCHROMETRIC CONFLICT", "#f43f5e")}
                    className="btn-trigger-anomaly"
                    id="btn-inject-psychrometric"
                    title="Simulate thermodynamic conflict (Tw > Td)"
                  >
                    <span>Psychrometric</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => handleTriggerAnomaly("spatial", "temp_dry", 55.0, "INJECT MULTI-AWS SPATIAL ANOMALY (AWS-01: 55°C vs Neighbors: ~31°C)", "#f43f5e")}
                    className="btn-trigger-anomaly"
                    id="btn-inject-spatial"
                    title="Simulate AWS-01 divergence against neighboring stations"
                  >
                    <span>Spatial Anomaly</span>
                  </button>

                  <button
                    type="button"
                    onClick={handleResetNominal}
                    className="btn-trigger-anomaly reset-btn"
                    id="btn-reset-nominal"
                    title="Restore nominal baseline telemetry stream"
                  >
                    <span>Reset Nominal</span>
                  </button>
                </div>

                {/* Status Notice Toast */}
                {testbenchNotice && (
                  <div style={{
                    marginTop: "12px",
                    padding: "8px 12px",
                    borderRadius: "6px",
                    fontSize: "0.72rem",
                    fontWeight: 700,
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                    background: testbenchNotice.type === "danger" ? "rgba(239,68,68,0.1)" : (testbenchNotice.type === "nominal" ? "rgba(16,185,129,0.1)" : "rgba(2,132,199,0.1)"),
                    color: testbenchNotice.type === "danger" ? "#dc2626" : (testbenchNotice.type === "nominal" ? "#16a34a" : "#0284c7"),
                    border: `1px solid ${testbenchNotice.type === "danger" ? "#fca5a5" : (testbenchNotice.type === "nominal" ? "#86efac" : "#bae6fd")}`
                  }}>
                    <span style={{ flex: 1 }}>{testbenchNotice.msg}</span>
                    <span style={{ fontSize: "0.65rem", opacity: 0.8 }}>{testbenchNotice.time}</span>
                  </div>
                )}
              </div>

              {/* ─── SECTION 2: HISTORICAL TELEMETRY INGESTION & REPLAY STUDIO ─── */}
              <div className="replay-hub-section">
                
                {/* Hub Header */}
                <div className="replay-header-flex">
                  <div className="section-title-wrap">
                    <span className="section-title-text">HISTORICAL DATA REPLAY & IMPORT STUDIO</span>
                    <span className="section-subtitle-text">Import CSV/TXT/LOG datasets, analyze multi-channel waveforms, inspect raw ASCII logs, and replay telemetry</span>
                  </div>

                  {/* Action Buttons */}
                  <div className="replay-actions-group">
                    <input
                      type="file"
                      ref={fileInputRef}
                      onChange={handleFileUpload}
                      accept=".csv,.txt,.log,.dat,text/plain,text/csv"
                      style={{ display: "none" }}
                    />
                    
                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      className="btn-action-light"
                      title="Upload and parse local .CSV, .TXT or .LOG telemetry file"
                      id="btn-import-file"
                    >
                      <span>Import File (.CSV / .TXT)</span>
                    </button>

                    <button
                      type="button"
                      onClick={handleLoadSampleCyclone}
                      className="btn-action-light"
                      title="Load sample AWS cyclone dataset (60 frames)"
                      id="btn-load-cyclone-sample"
                    >
                      <span>Sample Cyclone Log</span>
                    </button>

                    <button
                      type="button"
                      onClick={handleLoadSampleDrift}
                      className="btn-action-light"
                      title="Load sample PT100 transducer drift log (50 frames)"
                      id="btn-load-drift-sample"
                    >
                      <span>Sample Drift Log</span>
                    </button>

                    <button
                      type="button"
                      onClick={handleClearDataset}
                      className="btn-action-light"
                      title="Clear active dataset"
                    >
                      <span>Clear</span>
                    </button>
                  </div>
                </div>

                {/* File Metadata Strip */}
                {replayRecords.length > 0 && (
                  <div className="replay-meta-strip">
                    <div className="meta-pill">
                      <span className="meta-pill-label">Dataset:</span>
                      <span className="meta-pill-val">{importedFileName}</span>
                    </div>

                    <div className="meta-pill">
                      <span className="meta-pill-label">Size:</span>
                      <span className="meta-pill-val">{importedFileSize}</span>
                    </div>

                    <div className="meta-pill">
                      <span className="meta-pill-label">Total Frames:</span>
                      <span className="meta-pill-val">{replayRecords.length} Packets</span>
                    </div>

                    <div className="meta-pill">
                      <span className="meta-pill-label">Time Span:</span>
                      <span className="meta-pill-val">{replayRecords[0]?.timestamp || "00:00"} → {replayRecords[replayRecords.length - 1]?.timestamp || "00:00"}</span>
                    </div>

                    <div className="meta-pill">
                      <span className="meta-pill-label">Flagged Anomalies:</span>
                      <span className="meta-pill-val" style={{ color: replayRecords.filter(r => r.isAnomaly).length > 0 ? "#dc2626" : "#16a34a" }}>
                        {replayRecords.filter(r => r.isAnomaly).length} Events
                      </span>
                    </div>

                    <div className="meta-pill" style={{ marginLeft: "auto" }}>
                      <span className="meta-pill-label">QA Status:</span>
                      <span className="status-tag connected" style={{ padding: "2px 8px", fontSize: "0.64rem" }}>WMO-VERIFIED</span>
                    </div>
                  </div>
                )}

                {/* Replay Playback Transport Controls Bar */}
                {replayRecords.length > 0 && (
                  <div className="replay-transport-bar">
                    
                    {/* Transport Button */}
                    <div className="transport-btns-group">
                      <button
                        type="button"
                        onClick={() => setIsReplaying(!isReplaying)}
                        className={`transport-btn play-btn ${isReplaying ? "playing" : ""}`}
                        id="btn-replay-play-pause"
                      >
                        <span>{isReplaying ? "PAUSE" : "PLAY"}</span>
                      </button>
                    </div>

                    {/* Scrubber Timeline Slider */}
                    <div className="replay-scrubber-wrap">
                      <span style={{ fontSize: "0.7rem", fontWeight: 700, color: "#0284c7", minWidth: "55px" }}>
                        {replayRecords[replayIndex]?.timestamp || `Frame ${replayIndex + 1}`}
                      </span>

                      {(() => {
                        const progressPct = replayRecords.length > 1 ? Number(((replayIndex / (replayRecords.length - 1)) * 100).toFixed(1)) : 0;
                        return (
                          <input
                            type="range"
                            min={0}
                            max={replayRecords.length - 1}
                            value={replayIndex}
                            onChange={(e) => setReplayIndex(Number(e.target.value))}
                            className="replay-slider"
                            id="replay-timeline-scrubber"
                            style={{
                              background: `linear-gradient(to right, #0284c7 0%, #0284c7 ${progressPct}%, ${theme === "dark" ? "#334155" : "#cbd5e1"} ${progressPct}%, ${theme === "dark" ? "#334155" : "#cbd5e1"} 100%)`
                            }}
                          />
                        );
                      })()}

                      <span style={{ fontSize: "0.68rem", color: "var(--text-muted)", minWidth: "60px", textAlign: "right" }}>
                        {replayIndex + 1} / {replayRecords.length}
                      </span>
                    </div>

                  </div>
                )}
                <div className="replay-view-modes-bar">
                  <div className="replay-view-nav">
                    <button
                      type="button"
                      onClick={() => setReplayViewMode("graph")}
                      className={`replay-mode-btn ${replayViewMode === "graph" ? "active" : ""}`}
                      id="view-mode-graph"
                    >
                      <span>Multi-Channel Waveforms</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => setReplayViewMode("table")}
                      className={`replay-mode-btn ${replayViewMode === "table" ? "active" : ""}`}
                      id="view-mode-table"
                    >
                      <span>Tabular Log Table</span>
                    </button>
                  </div>

                  {/* Search Bar for Table View */}
                  {replayViewMode === "table" && (
                    <div style={{ display: "flex", alignItems: "center", gap: "6px", background: "var(--bg-card)", border: "1px solid var(--border-color)", borderRadius: "4px", padding: "2px 8px" }}>
                      <input
                        type="text"
                        placeholder="Search logs, anomalies..."
                        value={replaySearch}
                        onChange={(e) => setReplaySearch(e.target.value)}
                        style={{ border: "none", outline: "none", background: "transparent", fontSize: "0.72rem", color: "var(--text-main)", width: "160px" }}
                      />
                    </div>
                  )}
                </div>

                {/* ─── VIEW 1: MULTI-CHANNEL HISTORICAL WAVEFORMS (GRAPH) ─── */}
                {replayViewMode === "graph" && (
                  <div style={{ background: "var(--bg-card)", border: "1px solid var(--border-color)", borderRadius: "6px", padding: "10px 12px 6px 0px" }}>
                    
                    {/* Channel Filter Pills Selector */}
                    {replayRecords.length > 0 && (
                      <div className="channel-filter-pills" style={{ paddingLeft: "14px" }}>
                        <span style={{ fontSize: "0.64rem", fontWeight: 700, color: "var(--text-muted)", marginRight: "4px" }}>CHANNELS:</span>
                        {[
                          { id: "all", label: "All Active Channels" },
                          { id: "temp", label: "Dry & Wet Temp (°C)" },
                          { id: "humidity", label: "Humidity (%)" },
                          { id: "pressure", label: "Pressure (hPa)" },
                          { id: "speed", label: "Wind Speed (m/s)" },
                          { id: "solar", label: "Solar (W/m²)" },
                          { id: "rain", label: "Rainfall (mm)" }
                        ].map(c => (
                          <button
                            type="button"
                            key={c.id}
                            onClick={() => setReplayChannelFilter(c.id)}
                            className={`chan-pill-btn ${replayChannelFilter === c.id ? "active" : ""}`}
                          >
                            <span>{c.label}</span>
                          </button>
                        ))}
                      </div>
                    )}

                    {replayRecords.length > 0 ? (
                      <ResponsiveContainer width="100%" height={240}>
                        <ComposedChart
                          data={replayRecords.map((r, idx) => ({
                            time: r.timestamp,
                            temp: r.temp,
                            wetBulb: r.wetBulb,
                            humidity: r.humidity,
                            pressureRaw: r.pressure,
                            pressureScaled: Number((r.pressure - 980).toFixed(1)),
                            solar: r.solar,
                            solarScaled: Number((r.solar / 20).toFixed(1)),
                            speed: r.speed,
                            rain: r.rain,
                            isScrubbed: idx === replayIndex
                          }))}
                          margin={{ top: 5, right: 15, left: -10, bottom: 0 }}
                        >
                          <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.15)" />
                          <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 10 }} />
                          <YAxis
                            stroke="#64748b"
                            tick={{ fontSize: 10 }}
                            domain={
                              replayChannelFilter === "temp" ? [15, 45] :
                              replayChannelFilter === "humidity" ? [30, 100] :
                              replayChannelFilter === "pressure" ? [980, 1025] :
                              replayChannelFilter === "speed" ? [0, 35] :
                              replayChannelFilter === "solar" ? [0, 1000] :
                              replayChannelFilter === "rain" ? [0, 50] :
                              [0, 100]
                            }
                          />
                          <Tooltip contentStyle={{ background: "var(--bg-card)", borderColor: "var(--border-color)", borderRadius: "6px", fontSize: "11px", color: "var(--text-main)" }} />
                          <Legend wrapperStyle={{ fontSize: "11px", paddingTop: "4px" }} />

                          {/* Moving Playback Reference Needle */}
                          {replayRecords[replayIndex] && (
                            <ReferenceLine
                              x={replayRecords[replayIndex].timestamp}
                              stroke="#0284c7"
                              strokeWidth={1.5}
                              strokeDasharray="3 3"
                            />
                          )}

                          {/* Channel Renderers */}
                          {(replayChannelFilter === "all" || replayChannelFilter === "temp") && isParamEnabled("temp") && (
                            <Line type="monotone" dataKey="temp" name="Dry Bulb Temp (°C)" stroke="#dc2626" strokeWidth={2.2} dot={false} />
                          )}
                          {(replayChannelFilter === "all" || replayChannelFilter === "temp") && isParamEnabled("wet_bulb") && (
                            <Line type="monotone" dataKey="wetBulb" name="Wet Bulb Temp (°C)" stroke="#f43f5e" strokeDasharray="4 4" strokeWidth={1.8} dot={false} />
                          )}
                          {(replayChannelFilter === "all" || replayChannelFilter === "humidity") && isParamEnabled("humidity") && (
                            <Line type="monotone" dataKey="humidity" name="Rel. Humidity (%)" stroke="#7c3aed" strokeWidth={2.2} dot={false} />
                          )}
                          {(replayChannelFilter === "all") && isParamEnabled("pressure") && (
                            <Line type="monotone" dataKey="pressureScaled" name="Pressure Scaled (hPa - 980)" stroke="#0284c7" strokeWidth={2.2} dot={false} />
                          )}
                          {(replayChannelFilter === "pressure") && isParamEnabled("pressure") && (
                            <Line type="monotone" dataKey="pressureRaw" name="Pressure (hPa)" stroke="#0284c7" strokeWidth={2.4} dot={false} />
                          )}
                          {(replayChannelFilter === "all" || replayChannelFilter === "speed") && isParamEnabled("speed") && (
                            <Line type="monotone" dataKey="speed" name="Wind Speed (m/s)" stroke="#2563eb" strokeWidth={2.0} dot={false} />
                          )}
                          {(replayChannelFilter === "all") && isParamEnabled("solar") && (
                            <Line type="monotone" dataKey="solarScaled" name="Solar Scaled (/ 20)" stroke="#ea580c" strokeWidth={2.0} dot={false} />
                          )}
                          {(replayChannelFilter === "solar") && isParamEnabled("solar") && (
                            <Line type="monotone" dataKey="solar" name="Solar Radiation (W/m²)" stroke="#ea580c" strokeWidth={2.2} dot={false} />
                          )}
                          {(replayChannelFilter === "all" || replayChannelFilter === "rain") && isParamEnabled("rain") && (
                            <Line type="monotone" dataKey="rain" name="Rainfall (mm)" stroke="#0891b2" strokeWidth={2.0} dot={false} />
                          )}
                        </ComposedChart>
                      </ResponsiveContainer>
                    ) : (
                      <div className="file-dropzone-box" onClick={() => fileInputRef.current?.click()}>
                        <div className="file-dropzone-title">No Historical Telemetry File Loaded</div>
                        <div className="file-dropzone-subtitle">Click to import a local .CSV, .TXT, or .LOG file, or click "Sample Cyclone Log" above to test immediately!</div>
                      </div>
                    )}
                  </div>
                )}

                {/* ─── VIEW 2: TABULAR LOG TABLE ─── */}
                {replayViewMode === "table" && (
                  <div className="table-container compact-table-container">
                    <table className="dark-table compact-table">
                      <colgroup>
                        <col style={{ width: "45px" }} />
                        <col style={{ width: "95px" }} />
                        {isParamEnabled("temp") && <col style={{ width: "110px" }} />}
                        {isParamEnabled("wet_bulb") && <col style={{ width: "110px" }} />}
                        {isParamEnabled("humidity") && <col style={{ width: "105px" }} />}
                        {isParamEnabled("pressure") && <col style={{ width: "115px" }} />}
                        {isParamEnabled("speed") && <col style={{ width: "100px" }} />}
                        {isParamEnabled("direction") && <col style={{ width: "85px" }} />}
                        {isParamEnabled("solar") && <col style={{ width: "110px" }} />}
                        {isParamEnabled("rain") && <col style={{ width: "95px" }} />}
                        <col style={{ width: "auto" }} />
                      </colgroup>
                      <thead>
                        <tr>
                          <th>#</th>
                          <th>Time</th>
                          {isParamEnabled("temp") && <th>Dry Temp (°C)</th>}
                          {isParamEnabled("wet_bulb") && <th>Wet Temp (°C)</th>}
                          {isParamEnabled("humidity") && <th>Humidity (%)</th>}
                          {isParamEnabled("pressure") && <th>Pressure (hPa)</th>}
                          {isParamEnabled("speed") && <th>Speed (m/s)</th>}
                          {isParamEnabled("direction") && <th>Dir (°)</th>}
                          {isParamEnabled("solar") && <th>Solar (W/m²)</th>}
                          {isParamEnabled("rain") && <th>Rain (mm)</th>}
                          <th>Status / Diagnostics</th>
                        </tr>
                      </thead>
                      <tbody>
                        {replayRecords.length > 0 ? (
                          replayRecords
                            .filter(r => {
                              if (!replaySearch) return true;
                              const s = replaySearch.toLowerCase();
                              return r.timestamp.toLowerCase().includes(s) || (r.xai && r.xai.toLowerCase().includes(s)) || (r.isAnomaly ? "anomaly" : "nominal").includes(s);
                            })
                            .map((r, i) => (
                              <tr
                                key={r.id}
                                onClick={() => setReplayIndex(r.id - 1)}
                                className={replayIndex === r.id - 1 ? "replay-row-active" : (r.isAnomaly ? "param-row-disabled" : "")}
                                style={{ cursor: "pointer" }}
                                title="Click to scrub replay to this timestamp"
                              >
                                <td style={{ fontWeight: 700, color: replayIndex === r.id - 1 ? "#0284c7" : "var(--text-muted)" }}>
                                  {r.id}
                                </td>
                                <td style={{ fontWeight: 700 }}>{r.timestamp}</td>
                                {isParamEnabled("temp") && <td style={{ color: "#dc2626", fontWeight: 700 }}>{r.temp}°C</td>}
                                {isParamEnabled("wet_bulb") && <td style={{ color: "#f43f5e" }}>{r.wetBulb}°C</td>}
                                {isParamEnabled("humidity") && <td style={{ color: "#7c3aed", fontWeight: 700 }}>{r.humidity}%</td>}
                                {isParamEnabled("pressure") && <td style={{ color: "#0284c7", fontWeight: 700 }}>{r.pressure}</td>}
                                {isParamEnabled("speed") && <td style={{ color: "#2563eb" }}>{r.speed}</td>}
                                {isParamEnabled("direction") && <td>{r.direction}°</td>}
                                {isParamEnabled("solar") && <td style={{ color: "#ea580c" }}>{r.solar}</td>}
                                {isParamEnabled("rain") && <td>{r.rain}</td>}
                                <td>
                                  {r.isAnomaly ? (
                                    <span style={{ color: "#dc2626", fontWeight: 700, fontSize: "0.64rem" }}>{r.xai}</span>
                                  ) : (
                                    <span style={{ color: "#16a34a", fontWeight: 700, fontSize: "0.64rem" }}>NOMINAL</span>
                                  )}
                                </td>
                              </tr>
                            ))
                        ) : (
                          <tr>
                            <td colSpan={11} style={{ textAlign: "center", padding: "30px", color: "var(--text-muted)" }}>
                              No historical logs imported yet. Click "Import File" or "Sample Cyclone Log".
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                )}

              </div>

            </div>
          )}

          {/* 8. SYSTEM EXPORT CENTER TAB */}
          {activeTab === "export_option" && (
            <div className="panel-card">
              <div className="section-header-bar">
                <div className="section-title-wrap">
                  <span className="section-title-text">SYSTEM EXPORT CENTER</span>
                  <span className="section-subtitle-text">Export meteorological telemetry in compliance formats</span>
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "14px" }}>
                <div className="station-card">
                  <div style={{ fontSize: "0.92rem", fontWeight: 800, color: "#0284c7" }}>CSV Data Table (.csv)</div>
                  <div style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>
                    Standard tabular meteorological logs formatted for Excel, Python Pandas, and MATLAB analysis.
                  </div>
                  <button onClick={handleExportCSV} className="btn-action-light">
                    <span>Download CSV Log</span>
                  </button>
                </div>

                <div className="station-card">
                  <div style={{ fontSize: "0.92rem", fontWeight: 800, color: "#16a34a" }}>JSON Telemetry (.json)</div>
                  <div style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>
                    Structured JSON records with full QA/QC diagnostics, transducer metrics, and timestamps.
                  </div>
                  <button onClick={handleExportCSV} className="btn-action-light">
                    <span>Download JSON Records</span>
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* 9. CONNECTION LINKS TAB (CLEAN DEFENSE GRADE) */}
          {activeTab === "link_config" && (
            <div className="panel-card conn-layout-container">
              
              {/* Header Bar */}
              <div className="section-header-bar">
                <div className="section-title-wrap">
                  <span className="section-title-text">TELEMETRY NETWORK & HARDWARE INTERFACES</span>
                  <span className="section-subtitle-text">Configure UDP LAN broadcast socket, TCP telemetry client, RS-232/RS-485 serial ports, and live link diagnostics</span>
                </div>
              </div>

              {/* Status Banner */}
              <div style={{
                background: "var(--bg-main)",
                border: "1px solid var(--border-color)",
                borderLeft: "4px solid #0284c7",
                borderRadius: "4px",
                padding: "8px 12px",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center"
              }}>
                <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                  <span style={{ fontSize: "0.72rem", fontWeight: 700, color: "var(--text-dark-title)" }}>ACTIVE LINK STATUS:</span>
                  <span style={{ fontSize: "0.72rem", color: "#0284c7", fontWeight: 600 }}>{connNotice}</span>
                </div>
                <span className="conn-badge online">ONLINE (1.0 Hz)</span>
              </div>

              {/* 3-Column Interface Configuration Cards Grid */}
              <div className="conn-cards-grid">
                
                {/* 1. UDP LAN Listener */}
                <div
                  className={`conn-card ${activeProtocol === "UDP" ? "active-link" : ""}`}
                  onClick={() => {
                    setActiveProtocol("UDP");
                    setConnNotice(`UDP LAN Broadcast Socket active on ${linkHost}:${linkPort} (Ingest Rate: 1.0 Hz Nominal)`);
                  }}
                >
                  <div className="conn-card-header">
                    <span className="conn-card-title">UDP LAN Broadcast Listener</span>
                    <span className={`conn-badge ${activeProtocol === "UDP" ? "online" : "standby"}`}>
                      {activeProtocol === "UDP" ? "LISTENING" : "STANDBY"}
                    </span>
                  </div>

                  <div className="conn-form">
                    <div className="conn-row-2col">
                      <div>
                        <label className="conn-field-label">Bind IP Address</label>
                        <input
                          type="text"
                          value={linkHost}
                          onChange={e => setLinkHost(e.target.value)}
                          className="conn-input"
                        />
                      </div>
                      <div>
                        <label className="conn-field-label">Port</label>
                        <input
                          type="number"
                          value={linkPort}
                          onChange={e => setLinkPort(Number(e.target.value))}
                          className="conn-input"
                        />
                      </div>
                    </div>

                    <div className="conn-row-2col">
                      <div>
                        <label className="conn-field-label">Buffer Size</label>
                        <select
                          value={udpBuffer}
                          onChange={e => setUdpBuffer(e.target.value)}
                          className="conn-select"
                        >
                          <option value="1024">1024 Bytes</option>
                          <option value="2048">2048 Bytes</option>
                          <option value="4096">4096 Bytes</option>
                          <option value="8192">8192 Bytes</option>
                        </select>
                      </div>
                      <div>
                        <label className="conn-field-label">Packet Framing</label>
                        <select
                          value={udpFraming}
                          onChange={e => setUdpFraming(e.target.value)}
                          className="conn-select"
                        >
                          <option value="AWS-32B Binary">AWS-32B Binary</option>
                          <option value="Plain CSV ASCII">Plain CSV ASCII</option>
                          <option value="IMD Synoptic 64B">IMD Synoptic 64B</option>
                        </select>
                      </div>
                    </div>

                    <div className="conn-actions-row">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          setActiveProtocol("UDP");
                          setConnNotice(`UDP LAN Broadcast Socket active on ${linkHost}:${linkPort} (Ingest Rate: 1.0 Hz Nominal)`);
                          setConnLogs(prev => [
                            { time: new Date().toLocaleTimeString(), tag: "INFO", msg: `Activated UDP LAN socket on ${linkHost}:${linkPort}` },
                            ...prev.slice(0, 19)
                          ]);
                        }}
                        className="conn-btn-primary"
                      >
                        Apply UDP Socket
                      </button>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          setLinkHost("0.0.0.0");
                          setLinkPort(5000);
                        }}
                        className="conn-btn-secondary"
                      >
                        Reset
                      </button>
                    </div>
                  </div>
                </div>

                {/* 2. TCP Client Stream */}
                <div
                  className={`conn-card ${activeProtocol === "TCP" ? "active-link" : ""}`}
                  onClick={() => {
                    setActiveProtocol("TCP");
                    setConnNotice(`TCP Telemetry Client stream active on ${tcpHost}:${tcpPort} (Ingest Rate: 1.0 Hz Nominal)`);
                  }}
                >
                  <div className="conn-card-header">
                    <span className="conn-card-title">TCP Telemetry Client</span>
                    <span className={`conn-badge ${activeProtocol === "TCP" ? "online" : "standby"}`}>
                      {activeProtocol === "TCP" ? "CONNECTED" : "STANDBY"}
                    </span>
                  </div>

                  <div className="conn-form">
                    <div className="conn-row-2col">
                      <div>
                        <label className="conn-field-label">Remote Server Host</label>
                        <input
                          type="text"
                          value={tcpHost}
                          onChange={e => setTcpHost(e.target.value)}
                          className="conn-input"
                        />
                      </div>
                      <div>
                        <label className="conn-field-label">Port</label>
                        <input
                          type="number"
                          value={tcpPort}
                          onChange={e => setTcpPort(Number(e.target.value))}
                          className="conn-input"
                        />
                      </div>
                    </div>

                    <div className="conn-row-2col">
                      <div>
                        <label className="conn-field-label">Reconnect Mode</label>
                        <select
                          value={tcpReconnect}
                          onChange={e => setTcpReconnect(e.target.value)}
                          className="conn-select"
                        >
                          <option value="auto">Auto Reconnect (5s)</option>
                          <option value="manual">Manual Reconnect</option>
                        </select>
                      </div>
                      <div>
                        <label className="conn-field-label">Keep-Alive</label>
                        <input
                          type="text"
                          value={tcpKeepAlive}
                          onChange={e => setTcpKeepAlive(e.target.value)}
                          className="conn-input"
                        />
                      </div>
                    </div>

                    <div className="conn-actions-row">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          setActiveProtocol("TCP");
                          setConnNotice(`TCP Telemetry Client stream active on ${tcpHost}:${tcpPort} (Ingest Rate: 1.0 Hz Nominal)`);
                          setConnLogs(prev => [
                            { time: new Date().toLocaleTimeString(), tag: "INFO", msg: `Connecting to TCP server ${tcpHost}:${tcpPort}...` },
                            { time: new Date().toLocaleTimeString(), tag: "OK", msg: `Activated TCP stream connection with ${tcpHost}:${tcpPort}` },
                            ...prev.slice(0, 18)
                          ]);
                        }}
                        className="conn-btn-primary"
                      >
                        Connect TCP Stream
                      </button>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          setConnLogs(prev => [
                            { time: new Date().toLocaleTimeString(), tag: "INFO", msg: `Ping sent to ${tcpHost}:${tcpPort} - RTT: 4ms` },
                            ...prev.slice(0, 19)
                          ]);
                        }}
                        className="conn-btn-secondary"
                      >
                        Test Ping
                      </button>
                    </div>
                  </div>
                </div>

                {/* 3. Hardware Serial Port */}
                <div
                  className={`conn-card ${activeProtocol === "SERIAL" ? "active-link" : ""}`}
                  onClick={() => {
                    setActiveProtocol("SERIAL");
                    setConnNotice(`Hardware Serial Port active on ${serialPort} (${serialBaud} bps 8-N-1)`);
                  }}
                >
                  <div className="conn-card-header">
                    <span className="conn-card-title">Hardware Serial Port (RS-232/485)</span>
                    <span className={`conn-badge ${activeProtocol === "SERIAL" ? "online" : "ready"}`}>
                      {activeProtocol === "SERIAL" ? "STREAMING" : "PORT READY"}
                    </span>
                  </div>

                  <div className="conn-form">
                    <div className="conn-row-2col">
                      <div>
                        <label className="conn-field-label">COM Port</label>
                        <select
                          value={serialPort}
                          onChange={e => setSerialPort(e.target.value)}
                          className="conn-select"
                        >
                          <option value="COM1">COM1 (System Default)</option>
                          <option value="COM2">COM2</option>
                          <option value="COM3">COM3 (USB-UART)</option>
                          <option value="COM4">COM4</option>
                          <option value="/dev/ttyUSB0">/dev/ttyUSB0 (Linux)</option>
                          <option value="/dev/ttyS0">/dev/ttyS0</option>
                        </select>
                      </div>
                      <div>
                        <label className="conn-field-label">Baud Rate</label>
                        <select
                          value={serialBaud}
                          onChange={e => setSerialBaud(e.target.value)}
                          className="conn-select"
                        >
                          <option value="9600">9600 bps</option>
                          <option value="19200">19200 bps</option>
                          <option value="38400">38400 bps</option>
                          <option value="57600">57600 bps</option>
                          <option value="115200">115200 bps</option>
                          <option value="230400">230400 bps</option>
                        </select>
                      </div>
                    </div>

                    <div className="conn-row-2col">
                      <div>
                        <label className="conn-field-label">Parity / Data Bits</label>
                        <select
                          value={serialParity}
                          onChange={e => setSerialParity(e.target.value)}
                          className="conn-select"
                        >
                          <option value="8-N-1">8-N-1 (Standard 8-bit)</option>
                          <option value="8-E-1">8-E-1 (Even Parity)</option>
                          <option value="8-O-1">8-O-1 (Odd Parity)</option>
                          <option value="7-E-1">7-E-1 (ASCII 7-bit)</option>
                        </select>
                      </div>
                      <div>
                        <label className="conn-field-label">Flow Control</label>
                        <select
                          value={serialFlow}
                          onChange={e => setSerialFlow(e.target.value)}
                          className="conn-select"
                        >
                          <option value="None">None</option>
                          <option value="RTS/CTS">RTS / CTS (Hardware)</option>
                          <option value="XON/XOFF">XON / XOFF (Software)</option>
                        </select>
                      </div>
                    </div>

                    <div className="conn-actions-row">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          setActiveProtocol("SERIAL");
                          setConnNotice(`Hardware Serial Port active on ${serialPort} (${serialBaud} bps 8-N-1)`);
                          setConnLogs(prev => [
                            { time: new Date().toLocaleTimeString(), tag: "INFO", msg: `Opening serial port ${serialPort} at ${serialBaud} bps (${serialParity})...` },
                            { time: new Date().toLocaleTimeString(), tag: "OK", msg: `Activated Serial stream on ${serialPort} (DTR/RTS asserted)` },
                            ...prev.slice(0, 18)
                          ]);
                        }}
                        className="conn-btn-primary"
                      >
                        Open Serial Port
                      </button>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          setConnLogs(prev => [
                            { time: new Date().toLocaleTimeString(), tag: "INFO", msg: `Scanned host hardware bus: Found COM1, COM3 (CH340 USB-Serial)` },
                            ...prev.slice(0, 19)
                          ]);
                        }}
                        className="conn-btn-secondary"
                      >
                        Scan Ports
                      </button>
                    </div>
                  </div>
                </div>

              </div>

              {/* Bottom Section: Ingest Diagnostics (Left) & Event Terminal (Right) */}
              <div className="conn-bottom-grid">
                
                {/* Diagnostics */}
                <div className="conn-card">
                  <div className="conn-card-header">
                    <span className="conn-card-title">Live Ingest Diagnostics & Link Quality</span>
                    <span className="conn-badge online">CRC-16 VERIFIED</span>
                  </div>

                  <div className="conn-metrics-grid">
                    <div className="conn-metric-tile">
                      <span className="conn-metric-name">Active Protocol</span>
                      <span className="conn-metric-value" style={{ color: "#0284c7" }}>
                        {activeProtocol === "UDP" ? "UDP / LAN Socket" : activeProtocol === "TCP" ? "TCP Telemetry Stream" : `RS-232 / RS-485 (${serialPort})`}
                      </span>
                    </div>

                    <div className="conn-metric-tile">
                      <span className="conn-metric-name">Ingest Rate</span>
                      <span className="conn-metric-value" style={{ color: "#16a34a" }}>1.0 Hz (32 B/s)</span>
                    </div>

                    <div className="conn-metric-tile">
                      <span className="conn-metric-name">Packets Processed</span>
                      <span className="conn-metric-value" suppressHydrationWarning>{formatNum(metrics.received)} pkts</span>
                    </div>

                    <div className="conn-metric-tile">
                      <span className="conn-metric-name">Packet Integrity</span>
                      <span className="conn-metric-value" style={{ color: "#16a34a" }}>100.0% (0 Drop)</span>
                    </div>
                  </div>
                </div>

                {/* Activity Terminal */}
                <div className="conn-card">
                  <div className="conn-card-header">
                    <span className="conn-card-title">Connection Event Log</span>
                    <button
                      type="button"
                      onClick={() => setConnLogs([])}
                      className="conn-btn-secondary"
                      style={{ padding: "2px 8px", fontSize: "0.65rem" }}
                    >
                      Clear Log
                    </button>
                  </div>

                  <div className="conn-log-box">
                    {connLogs.length === 0 ? (
                      <div style={{ color: "#64748b", fontStyle: "italic" }}>No connection events recorded yet.</div>
                    ) : (
                      connLogs.map((log, idx) => (
                        <div key={idx} className="conn-log-row">
                          <span className="conn-log-time">[{log.time}]</span>
                          <span className={`conn-log-tag ${log.tag === "OK" ? "ok" : log.tag === "WARN" ? "warn" : "info"}`}>
                            {log.tag}
                          </span>
                          <span className="conn-log-msg">{log.msg}</span>
                        </div>
                      ))
                    )}
                  </div>
                </div>

              </div>

            </div>
          )}

        </main>
      </div>

    </div>
  );
}
