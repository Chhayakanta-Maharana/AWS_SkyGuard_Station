package main

import (
	"bufio"
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"net"
	"net/http"
	"os"
	"path/filepath"
	"sync"
	"sync/atomic"
	"time"
)

type Clients struct {
	mu   sync.Mutex
	list map[chan string]bool
}

type NetworkLinkConfig struct {
	Protocol  string `json:"protocol"` // "UDP", "TCP", "SIMULATOR"
	Host      string `json:"host"`     // e.g. "0.0.0.0"
	Port      int    `json:"port"`     // e.g. 5000
	Format    string `json:"format"`   // "AUTO", "BINARY", "CSV", "JSON"
	Status    string `json:"status"`   // "LISTENING", "RECEIVING_LAN", "SIMULATOR_ACTIVE"
	PacketsIn int64  `json:"packets_in"`
	BytesIn   int64  `json:"bytes_in"`
}

var (
	sim             *Simulator
	det             *Detector
	dbMgr           *DatabaseManager
	clients         = Clients{list: make(map[chan string]bool)}
	statsMu         sync.Mutex
	alertLog        = make([]AlertEvent, 0)
	lastPacketTime  time.Time
	packetSource    = "SIMULATOR"
	packetSourceMu  sync.Mutex

	activeConfig = NetworkLinkConfig{
		Protocol: "UDP",
		Host:     "0.0.0.0",
		Port:     5000,
		Format:   "AUTO",
		Status:   "LISTENING",
	}
	configMu sync.Mutex

	udpConn       *net.UDPConn
	tcpListener   net.Listener
	udpCancelChan chan struct{}
	tcpCancelChan chan struct{}

	totalPacketsCount int64
	totalBytesCount   int64
)

type AlertEvent struct {
	Timestamp   int64              `json:"timestamp"`
	Type        string             `json:"type"`
	Severity    string             `json:"severity"`
	Explanation string             `json:"explanation"`
	Original    map[string]float64 `json:"original"`
	Imputed     map[string]float64 `json:"imputed"`
}

func main() {
	portFlag := flag.String("port", "8080", "Port to serve API and static files")
	staticDirFlag := flag.String("static-dir", "", "Folder containing frontend static assets")
	flag.Parse()

	execDir, _ := os.Getwd()
	possiblePaths := []string{
		"aws_sample_input.txt",
		"../aws_sample_input.txt",
		"../../aws_sample_input.txt",
		filepath.Join(execDir, "aws_sample_input.txt"),
	}

	var dataPath string
	for _, p := range possiblePaths {
		abs, err := filepath.Abs(p)
		if err == nil {
			if _, err := os.Stat(abs); err == nil {
				dataPath = abs
				break
			}
		}
	}

	if dataPath != "" {
		var err error
		sim, err = NewSimulator(dataPath)
		if err != nil {
			fmt.Printf("Warning: Simulator init: %v\n", err)
		}
	}

	det = NewDetector(50)
	dbMgr = NewDatabaseManager(execDir)

	rebindNetworkListeners("0.0.0.0", 5000, "UDP")
	go startSimulationLoop()

	// HTTP Routes
	http.HandleFunc("/api/stream", handleSSE)
	http.HandleFunc("/api/inject", handleInject)
	http.HandleFunc("/api/reset", handleReset)
	http.HandleFunc("/api/stats", handleStats)
	http.HandleFunc("/api/link_config", handleLinkConfig)
	http.HandleFunc("/api/stations", handleStations)

	// Database Management Endpoints
	http.HandleFunc("/api/db/history", handleDBHistory)
	http.HandleFunc("/api/db/stats", handleDBStats)
	http.HandleFunc("/api/db/config", handleDBConfig)
	http.HandleFunc("/api/db/sync", handleDBSync)

	if *staticDirFlag != "" {
		fmt.Printf("Serving static frontend files from: %s\n", *staticDirFlag)
		fileServer := http.FileServer(http.Dir(*staticDirFlag))
		http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
			w.Header().Set("Cache-Control", "no-cache, no-store, must-revalidate")
			w.Header().Set("Pragma", "no-cache")
			w.Header().Set("Expires", "0")
			path := filepath.Join(*staticDirFlag, r.URL.Path)
			info, err := os.Stat(path)
			if err != nil || info.IsDir() {
				http.ServeFile(w, r, filepath.Join(*staticDirFlag, "index.html"))
				return
			}
			fileServer.ServeHTTP(w, r)
		})
	}

	fmt.Printf("AWS SkyGuard Backend running on http://localhost:%s\n", *portFlag)
	log.Fatal(http.ListenAndServe(":"+*portFlag, nil))
}

func handleStations(w http.ResponseWriter, r *http.Request) {
	if enableCors(w, r) {
		return
	}
	stations := dbMgr.GetStationList()
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(stations)
}

func handleDBHistory(w http.ResponseWriter, r *http.Request) {
	if enableCors(w, r) {
		return
	}
	stationID := r.URL.Query().Get("station_id")
	history := dbMgr.GetHistoryFiltered(100, stationID)
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(history)
}

func handleDBStats(w http.ResponseWriter, r *http.Request) {
	if enableCors(w, r) {
		return
	}
	stats := dbMgr.GetStats()
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(stats)
}

func handleDBConfig(w http.ResponseWriter, r *http.Request) {
	if enableCors(w, r) {
		return
	}
	if r.Method == "POST" {
		var cfg ExternalDBConfig
		if err := json.NewDecoder(r.Body).Decode(&cfg); err == nil {
			dbMgr.UpdateConfig(cfg)
			w.Header().Set("Content-Type", "application/json")
			json.NewEncoder(w).Encode(map[string]interface{}{"status": "success", "config": cfg})
			return
		}
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(dbMgr.config)
}

func handleDBSync(w http.ResponseWriter, r *http.Request) {
	if enableCors(w, r) {
		return
	}
	synced, err := dbMgr.SyncAllToCloud()
	w.Header().Set("Content-Type", "application/json")
	if err != nil {
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(map[string]interface{}{"status": "error", "message": err.Error()})
		return
	}
	json.NewEncoder(w).Encode(map[string]interface{}{"status": "success", "synced_records": synced})
}

func rebindNetworkListeners(host string, port int, protocol string) error {
	configMu.Lock()
	defer configMu.Unlock()

	if udpCancelChan != nil {
		close(udpCancelChan)
		udpCancelChan = nil
	}
	if udpConn != nil {
		_ = udpConn.Close()
		udpConn = nil
	}

	if tcpCancelChan != nil {
		close(tcpCancelChan)
		tcpCancelChan = nil
	}
	if tcpListener != nil {
		_ = tcpListener.Close()
		tcpListener = nil
	}

	activeConfig.Protocol = protocol
	activeConfig.Host = host
	activeConfig.Port = port

	if protocol == "UDP" {
		addrStr := fmt.Sprintf("%s:%d", host, port)
		uAddr, err := net.ResolveUDPAddr("udp", addrStr)
		if err != nil {
			return err
		}
		uConn, err := net.ListenUDP("udp", uAddr)
		if err != nil {
			return err
		}
		udpConn = uConn
		udpCancelChan = make(chan struct{})
		activeConfig.Status = "LISTENING"

		go runUDPWorker(udpConn, udpCancelChan, addrStr)

		tcpAddrStr := fmt.Sprintf("%s:%d", host, port+1)
		tListener, err := net.Listen("tcp", tcpAddrStr)
		if err == nil {
			tcpListener = tListener
			tcpCancelChan = make(chan struct{})
			go runTCPWorker(tcpListener, tcpCancelChan, tcpAddrStr)
		}

		packetSourceMu.Lock()
		packetSource = fmt.Sprintf("TCP LAN (%s) / UDP (%s)", tcpAddrStr, addrStr)
		packetSourceMu.Unlock()
	} else if protocol == "SIMULATOR" {
		activeConfig.Status = "SIMULATOR_ACTIVE"
		packetSourceMu.Lock()
		packetSource = "SIMULATOR"
		packetSourceMu.Unlock()
	}

	packetSourceMu.Lock()
	src := packetSource
	packetSourceMu.Unlock()

	broadcastPayload(map[string]interface{}{
		"timestamp": time.Now().Unix(),
		"source":    src,
		"status":    activeConfig.Status,
		"analysis": AnomalyResult{
			IsAnomaly:      false,
			Severity:       "NOMINAL",
			Confidence:     100.0,
			AnomalyType:    "nominal",
			XAIExplanation: fmt.Sprintf("Link switched to %s (%s:%d). Dynamic decoder matrix active.", activeConfig.Protocol, activeConfig.Host, activeConfig.Port),
			ImputedValues:  map[string]float64{},
		},
		"decoded_parameters": []ParameterField{},
		"active_parameters":  []ParameterField{},
	})

	return nil
}

func runUDPWorker(conn *net.UDPConn, cancel chan struct{}, addrStr string) {
	buf := make([]byte, 2048)
	for {
		select {
		case <-cancel:
			return
		default:
		}

		n, remoteAddr, err := conn.ReadFrom(buf)
		if err != nil {
			continue
		}

		if n > 0 {
			atomic.AddInt64(&totalPacketsCount, 1)
			atomic.AddInt64(&totalBytesCount, int64(n))

			packetSourceMu.Lock()
			lastPacketTime = time.Now()
			packetSource = fmt.Sprintf("UDP LAN (%s)", remoteAddr.String())
			packetSourceMu.Unlock()

			reading, err := ParseAWSFrame(buf[:n])
			if err != nil {
				continue
			}

			processAWSReading(reading)
		}
	}
}

func runTCPWorker(listener net.Listener, cancel chan struct{}, addrStr string) {
	for {
		select {
		case <-cancel:
			return
		default:
		}

		conn, err := listener.Accept()
		if err != nil {
			continue
		}

		go handleTCPConnection(conn)
	}
}

func handleTCPConnection(conn net.Conn) {
	defer conn.Close()
	reader := bufio.NewReader(conn)
	buf := make([]byte, 1024)

	for {
		n, err := reader.Read(buf)
		if err != nil {
			break
		}

		if n > 0 {
			atomic.AddInt64(&totalPacketsCount, 1)
			atomic.AddInt64(&totalBytesCount, int64(n))

			packetSourceMu.Lock()
			lastPacketTime = time.Now()
			packetSource = fmt.Sprintf("TCP LAN (%s)", conn.RemoteAddr().String())
			packetSourceMu.Unlock()

			reading, err := ParseAWSFrame(buf[:n])
			if err != nil {
				continue
			}

			processAWSReading(reading)
		}
	}
}

func startSimulationLoop() {
	for {
		time.Sleep(1 * time.Second)

		configMu.Lock()
		proto := activeConfig.Protocol
		configMu.Unlock()

		if proto != "SIMULATOR" {
			continue
		}

		packetSourceMu.Lock()
		packetSource = "SIMULATOR"
		packetSourceMu.Unlock()

		if sim != nil {
			reading, active := sim.GetNextReading()
			if active && reading != nil {
				processAWSReading(reading)
			}
		}
	}
}

func processAWSReading(reading *DecodedAWS) {
	var payload map[string]interface{}
	now := time.Now().Unix()

	packetSourceMu.Lock()
	src := packetSource
	packetSourceMu.Unlock()

	if reading == nil {
		res := AnomalyResult{
			IsAnomaly:      true,
			Severity:       "high",
			Confidence:     100.0,
			AnomalyType:    "outage",
			XAIExplanation: "Communication link failure. No telemetry packets received from AWS.",
			StationID:      "AWS-01",
			ImputedValues: map[string]float64{
				"temp_dry":     0,
				"humidity":     0,
				"pressure_hpa": 0,
			},
		}

		payload = map[string]interface{}{
			"timestamp":          now,
			"source":             src,
			"raw":                nil,
			"analysis":           res,
			"decoded_parameters": []ParameterField{},
			"active_parameters":  []ParameterField{},
		}

		dbMgr.InsertRecord(res, 0, 0, 0)

		statsMu.Lock()
		alertLog = append(alertLog, AlertEvent{
			Timestamp:   now,
			Type:        "outage",
			Severity:    "high",
			Explanation: res.XAIExplanation,
			Original:    nil,
			Imputed:     nil,
		})
		if len(alertLog) > 50 {
			alertLog = alertLog[1:]
		}
		statsMu.Unlock()
	} else {
		stationID := reading.StationID
		if stationID == "" {
			stationID = "AWS-01"
		}
		res := det.AnalyzeSpatial(stationID, reading.DryBulbTemp, reading.RelHumidity, reading.PressureHpa)

		dbMgr.InsertRecord(res, reading.DryBulbTemp, reading.PressureHpa, reading.RelHumidity)

		payload = map[string]interface{}{
			"timestamp":          reading.Timestamp,
			"source":             src,
			"raw":                reading,
			"analysis":           res,
			"decoded_parameters": reading.ToParameterList(),
			"active_parameters":  reading.ToActiveParameterList(),
		}

		if res.IsAnomaly {
			statsMu.Lock()
			alertLog = append(alertLog, AlertEvent{
				Timestamp:   reading.Timestamp,
				Type:        res.AnomalyType,
				Severity:    res.Severity,
				Explanation: res.XAIExplanation,
				Original: map[string]float64{
					"temp_dry":     reading.DryBulbTemp,
					"humidity":     reading.RelHumidity,
					"pressure_hpa": reading.PressureHpa,
				},
				Imputed: res.ImputedValues,
			})
			if len(alertLog) > 50 {
				alertLog = alertLog[1:]
			}
			statsMu.Unlock()
		}
	}

	broadcastPayload(payload)
}

func broadcastPayload(payload map[string]interface{}) {
	jsonBytes, err := json.Marshal(payload)
	if err != nil {
		return
	}

	dataStr := string(jsonBytes)

	clients.mu.Lock()
	for ch := range clients.list {
		select {
		case ch <- dataStr:
		default:
		}
	}
	clients.mu.Unlock()
}

func enableCors(w http.ResponseWriter, r *http.Request) bool {
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS, PUT, DELETE")
	w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization, apikey")
	if r.Method == "OPTIONS" {
		w.WriteHeader(http.StatusOK)
		return true
	}
	return false
}

func handleSSE(w http.ResponseWriter, r *http.Request) {
	if enableCors(w, r) {
		return
	}
	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("Connection", "keep-alive")

	messageChan := make(chan string, 100)

	clients.mu.Lock()
	clients.list[messageChan] = true
	clients.mu.Unlock()

	defer func() {
		clients.mu.Lock()
		delete(clients.list, messageChan)
		clients.mu.Unlock()
		close(messageChan)
	}()

	notify := r.Context().Done()

	for {
		select {
		case <-notify:
			return
		case msg := <-messageChan:
			fmt.Fprintf(w, "data: %s\n\n", msg)
			w.(http.Flusher).Flush()
		}
	}
}

func handleInject(w http.ResponseWriter, r *http.Request) {
	if enableCors(w, r) {
		return
	}
	if r.Method != "POST" {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}
	var req struct {
		AnomalyType string  `json:"anomaly_type"`
		Parameter   string  `json:"parameter"`
		Value       float64 `json:"value"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err == nil && sim != nil {
		if req.Parameter == "" {
			req.Parameter = "temp_dry"
		}
		if req.Value == 0 {
			req.Value = 10.0
		}
		sim.InjectAnomaly(AnomalyConfig{
			Type:      req.AnomalyType,
			Parameter: req.Parameter,
			Value:     req.Value,
		})
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{"status": "injected", "anomaly": req.AnomalyType})
}

func handleReset(w http.ResponseWriter, r *http.Request) {
	if enableCors(w, r) {
		return
	}
	if sim != nil {
		sim.InjectAnomaly(AnomalyConfig{Type: "none"})
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{"status": "cleared"})
}

func handleStats(w http.ResponseWriter, r *http.Request) {
	if enableCors(w, r) {
		return
	}
	statsMu.Lock()
	defer statsMu.Unlock()

	packetSourceMu.Lock()
	src := packetSource
	packetSourceMu.Unlock()

	configMu.Lock()
	cfg := activeConfig
	configMu.Unlock()

	dbStats := dbMgr.GetStats()

	resp := map[string]interface{}{
		"total_packets":      atomic.LoadInt64(&totalPacketsCount),
		"total_bytes":        atomic.LoadInt64(&totalBytesCount),
		"last_packet_source": src,
		"active_link":        cfg,
		"alert_events":       alertLog,
		"database_stats":     dbStats,
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(resp)
}

func handleLinkConfig(w http.ResponseWriter, r *http.Request) {
	if enableCors(w, r) {
		return
	}
	if r.Method == "POST" {
		var req NetworkLinkConfig
		if err := json.NewDecoder(r.Body).Decode(&req); err == nil {
			err := rebindNetworkListeners(req.Host, req.Port, req.Protocol)
			if err != nil {
				w.Header().Set("Content-Type", "application/json")
				w.WriteHeader(http.StatusInternalServerError)
				json.NewEncoder(w).Encode(map[string]string{"error": err.Error()})
				return
			}
		}
	}

	configMu.Lock()
	cfg := activeConfig
	configMu.Unlock()

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(cfg)
}
