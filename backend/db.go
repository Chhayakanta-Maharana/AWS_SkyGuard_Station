package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"math"
	"os"
	"path/filepath"
	"sync"
	"time"

	_ "github.com/lib/pq"
	_ "modernc.org/sqlite"
)

type TelemetryRecord struct {
	ID                 int64              `json:"id"`
	Timestamp          int64              `json:"timestamp"`
	StationID          string             `json:"station_id"`
	Temperature        float64            `json:"temperature"`
	Pressure           float64            `json:"pressure"`
	Humidity           float64            `json:"humidity"`
	IsAnomaly          bool               `json:"is_anomaly"`
	AnomalyScore       float64            `json:"anomaly_score"`
	AnomalyType        string             `json:"anomaly_type"`
	Severity           string             `json:"severity"`
	ConfidenceCategory string             `json:"confidence_category"`
	Explanation        string             `json:"explanation"`
	ShapAttributions   map[string]float64 `json:"shap_attributions"`
	SensorHealth       map[string]float64 `json:"sensor_health"`
	CreatedAt          string             `json:"created_at"`
}

type ExternalDBConfig struct {
	Enabled       bool   `json:"enabled"`
	Provider      string `json:"provider"`       // "NEON_POSTGRES", "SUPABASE", "REST_API"
	ConnectionURL string `json:"connection_url"` // PostgreSQL connection URL
	AutoSync      bool   `json:"auto_sync"`
}

type DatabaseManager struct {
	mu         sync.Mutex
	dbPath     string
	localDB    *sql.DB
	config     ExternalDBConfig
	neonDB     *sql.DB
	neonConnOK bool
}

const DefaultNeonURL = "postgresql://neondb_owner:npg_6SaJqLW7RKvQ@ep-winter-sky-ayfyunqv-pooler.c-5.us-east-2.aws.neon.tech/neondb?sslmode=require"

func NewDatabaseManager(projectDir string) *DatabaseManager {
	dbDir := filepath.Join(projectDir, "database")
	os.MkdirAll(dbDir, 0755)
	dbFile := filepath.Join(dbDir, "skyguard_telemetry.db")

	dm := &DatabaseManager{
		dbPath: dbFile,
		config: ExternalDBConfig{
			Enabled:       true,
			Provider:      "NEON_POSTGRES",
			ConnectionURL: DefaultNeonURL,
			AutoSync:      true,
		},
	}

	dm.initLocalSQLite()
	dm.loadConfig()
	dm.initNeonPostgreSQL()

	return dm
}

func (dm *DatabaseManager) initLocalSQLite() {
	db, err := sql.Open("sqlite", dm.dbPath)
	if err != nil {
		log.Printf("[!] SQLite Local DB Open Error: %v", err)
		return
	}

	// SQLite settings for high performance and concurrency
	db.SetMaxOpenConns(1)
	db.SetMaxIdleConns(1)

	// Enable WAL mode for fast writes without blocking reads
	_, _ = db.Exec("PRAGMA journal_mode=WAL;")
	_, _ = db.Exec("PRAGMA synchronous=NORMAL;")

	createTableSQL := `
	CREATE TABLE IF NOT EXISTS telemetry_logs (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		timestamp INTEGER NOT NULL,
		station_id TEXT,
		temperature REAL,
		pressure REAL,
		humidity REAL,
		is_anomaly INTEGER,
		anomaly_score REAL,
		anomaly_type TEXT,
		severity TEXT,
		confidence_category TEXT,
		explanation TEXT,
		shap_attributions TEXT,
		sensor_health TEXT,
		created_at TEXT
	);
	CREATE INDEX IF NOT EXISTS idx_telemetry_timestamp ON telemetry_logs(timestamp);
	`

	if _, err := db.Exec(createTableSQL); err != nil {
		log.Printf("[-] Failed to create table in SQLite DB: %v", err)
		return
	}

	dm.localDB = db
	log.Printf("✓ Local SQLite DB initialized at: %s (Table 'telemetry_logs' ready)", dm.dbPath)
}

func (dm *DatabaseManager) initNeonPostgreSQL() {
	if !dm.config.Enabled || dm.config.ConnectionURL == "" {
		return
	}

	db, err := sql.Open("postgres", dm.config.ConnectionURL)
	if err != nil {
		log.Printf("[!] Neon DB Open Warning: %v", err)
		return
	}

	db.SetMaxOpenConns(5)
	db.SetMaxIdleConns(2)
	db.SetConnMaxLifetime(5 * time.Minute)

	go func() {
		if err := db.Ping(); err != nil {
			log.Printf("[!] Neon Cloud DB Connection Warning: %v (Offline fallback active)", err)
			return
		}

		dm.mu.Lock()
		dm.neonDB = db
		dm.neonConnOK = true
		dm.mu.Unlock()

		log.Printf("✓ Successfully connected to Neon Cloud PostgreSQL Database!")

		createTableSQL := `
		CREATE TABLE IF NOT EXISTS telemetry_logs (
			id SERIAL PRIMARY KEY,
			timestamp BIGINT NOT NULL,
			station_id VARCHAR(50),
			temperature DOUBLE PRECISION,
			pressure DOUBLE PRECISION,
			humidity DOUBLE PRECISION,
			is_anomaly BOOLEAN,
			anomaly_score DOUBLE PRECISION,
			anomaly_type VARCHAR(100),
			severity VARCHAR(50),
			confidence_category VARCHAR(50),
			explanation TEXT,
			shap_attributions JSONB,
			sensor_health JSONB,
			created_at TIMESTAMPTZ DEFAULT NOW()
		);`

		_, err := db.Exec(createTableSQL)
		if err != nil {
			log.Printf("[-] Failed to create table in Neon DB: %v", err)
		} else {
			log.Printf("✓ Table 'telemetry_logs' verified/created in Neon PostgreSQL DB.")
		}
	}()
}

func (dm *DatabaseManager) InsertRecord(res AnomalyResult, temp, press, hum float64) TelemetryRecord {
	now := time.Now()
	createdAt := now.UTC().Format(time.RFC3339)
	shapJSON, _ := json.Marshal(res.ShapAttributions)
	healthJSON, _ := json.Marshal(res.SensorHealth)

	isAnomalyInt := 0
	if res.IsAnomaly {
		isAnomalyInt = 1
	}

	var insertedID int64

	dm.mu.Lock()
	if dm.localDB != nil {
		insertSQL := `
		INSERT INTO telemetry_logs (
			timestamp, station_id, temperature, pressure, humidity,
			is_anomaly, anomaly_score, anomaly_type, severity,
			confidence_category, explanation, shap_attributions, sensor_health, created_at
		) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
		`
		resExec, err := dm.localDB.Exec(insertSQL,
			now.Unix(), res.StationID, temp, press, hum,
			isAnomalyInt, res.Confidence, res.AnomalyType, res.Severity,
			res.Severity, res.XAIExplanation, string(shapJSON), string(healthJSON), createdAt,
		)
		if err != nil {
			log.Printf("[-] SQLite Insert Error: %v", err)
		} else {
			insertedID, _ = resExec.LastInsertId()
		}
	}

	neonOK := dm.neonConnOK
	neonDB := dm.neonDB
	dm.mu.Unlock()

	rec := TelemetryRecord{
		ID:                 insertedID,
		Timestamp:          now.Unix(),
		StationID:          res.StationID,
		Temperature:        temp,
		Pressure:           press,
		Humidity:           hum,
		IsAnomaly:          res.IsAnomaly,
		AnomalyScore:       res.Confidence,
		AnomalyType:        res.AnomalyType,
		Severity:           res.Severity,
		ConfidenceCategory: res.Severity,
		Explanation:        res.XAIExplanation,
		ShapAttributions:   res.ShapAttributions,
		SensorHealth:       res.SensorHealth,
		CreatedAt:          createdAt,
	}

	if neonOK && neonDB != nil {
		go func(r TelemetryRecord) {
			sJSON, _ := json.Marshal(r.ShapAttributions)
			hJSON, _ := json.Marshal(r.SensorHealth)

			insertSQL := `
			INSERT INTO telemetry_logs (
				timestamp, station_id, temperature, pressure, humidity,
				is_anomaly, anomaly_score, anomaly_type, severity,
				confidence_category, explanation, shap_attributions, sensor_health
			) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)`

			_, err := neonDB.Exec(insertSQL,
				r.Timestamp, r.StationID, r.Temperature, r.Pressure, r.Humidity,
				r.IsAnomaly, r.AnomalyScore, r.AnomalyType, r.Severity,
				r.ConfidenceCategory, r.Explanation, string(sJSON), string(hJSON),
			)

			if err == nil {
				log.Printf("✓ Cloud DB Sync: Inserted Record #%d (Station=%s, IsAnomaly=%v) into Neon PostgreSQL", r.ID, r.StationID, r.IsAnomaly)
			} else {
				log.Printf("[-] Neon DB Sync Error: %v", err)
			}
		}(rec)
	}

	return rec
}

func (dm *DatabaseManager) SyncAllToCloud() (int, error) {
	dm.mu.Lock()
	neonOK := dm.neonConnOK
	neonDB := dm.neonDB
	localDB := dm.localDB
	dm.mu.Unlock()

	if !neonOK || neonDB == nil || localDB == nil {
		return 0, nil
	}

	rows, err := localDB.Query(`
		SELECT timestamp, station_id, temperature, pressure, humidity,
		       is_anomaly, anomaly_score, anomaly_type, severity,
		       confidence_category, explanation, shap_attributions, sensor_health
		FROM telemetry_logs
		ORDER BY id ASC
	`)
	if err != nil {
		return 0, err
	}
	defer rows.Close()

	synced := 0
	for rows.Next() {
		var ts int64
		var stationID, anomType, sev, confCat, expl, shapStr, healthStr string
		var temp, press, hum, anomScore float64
		var isAnomInt int

		if err := rows.Scan(&ts, &stationID, &temp, &press, &hum,
			&isAnomInt, &anomScore, &anomType, &sev, &confCat, &expl, &shapStr, &healthStr); err != nil {
			continue
		}

		insertSQL := `
		INSERT INTO telemetry_logs (
			timestamp, station_id, temperature, pressure, humidity,
			is_anomaly, anomaly_score, anomaly_type, severity,
			confidence_category, explanation, shap_attributions, sensor_health
		) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)`

		_, err := neonDB.Exec(insertSQL,
			ts, stationID, temp, press, hum,
			isAnomInt == 1, anomScore, anomType, sev,
			confCat, expl, shapStr, healthStr,
		)
		if err == nil {
			synced++
		}
	}
	return synced, nil
}

func (dm *DatabaseManager) GetHistory(limit int) []TelemetryRecord {
	return dm.GetHistoryFiltered(limit, "")
}

func (dm *DatabaseManager) GetHistoryFiltered(limit int, stationID string) []TelemetryRecord {
	dm.mu.Lock()
	localDB := dm.localDB
	dm.mu.Unlock()

	if localDB == nil {
		return []TelemetryRecord{}
	}

	var query string
	var rows *sql.Rows
	var err error

	if stationID != "" && stationID != "ALL" {
		query = `
			SELECT id, timestamp, station_id, temperature, pressure, humidity,
			       is_anomaly, anomaly_score, anomaly_type, severity,
			       confidence_category, explanation, shap_attributions, sensor_health, created_at
			FROM (
				SELECT * FROM telemetry_logs WHERE station_id = ? ORDER BY id DESC LIMIT ?
			) sub
			ORDER BY id ASC
		`
		rows, err = localDB.Query(query, stationID, limit)
	} else {
		query = `
			SELECT id, timestamp, station_id, temperature, pressure, humidity,
			       is_anomaly, anomaly_score, anomaly_type, severity,
			       confidence_category, explanation, shap_attributions, sensor_health, created_at
			FROM (
				SELECT * FROM telemetry_logs ORDER BY id DESC LIMIT ?
			) sub
			ORDER BY id ASC
		`
		rows, err = localDB.Query(query, limit)
	}

	if err != nil {
		log.Printf("[-] SQLite GetHistory Query Error: %v", err)
		return []TelemetryRecord{}
	}
	defer rows.Close()

	records := make([]TelemetryRecord, 0, limit)
	for rows.Next() {
		var r TelemetryRecord
		var isAnomInt int
		var shapStr, healthStr sql.NullString
		var createdAt sql.NullString

		err := rows.Scan(
			&r.ID, &r.Timestamp, &r.StationID, &r.Temperature, &r.Pressure, &r.Humidity,
			&isAnomInt, &r.AnomalyScore, &r.AnomalyType, &r.Severity,
			&r.ConfidenceCategory, &r.Explanation, &shapStr, &healthStr, &createdAt,
		)
		if err != nil {
			continue
		}

		r.IsAnomaly = (isAnomInt == 1)
		if createdAt.Valid {
			r.CreatedAt = createdAt.String
		}

		if shapStr.Valid && shapStr.String != "" {
			var shap map[string]float64
			if err := json.Unmarshal([]byte(shapStr.String), &shap); err == nil {
				r.ShapAttributions = shap
			}
		}
		if healthStr.Valid && healthStr.String != "" {
			var health map[string]float64
			if err := json.Unmarshal([]byte(healthStr.String), &health); err == nil {
				r.SensorHealth = health
			}
		}

		records = append(records, r)
	}

	return records
}

type StationInfo struct {
	StationID   string  `json:"station_id"`
	Name        string  `json:"name"`
	Region      string  `json:"region"`
	IsLocal     bool    `json:"is_local"`
	Latitude    float64 `json:"latitude"`
	Longitude   float64 `json:"longitude"`
	DistanceKM  float64 `json:"distance_km"`
	LastSeen    int64   `json:"last_seen"`
	Temperature float64 `json:"temperature"`
	Pressure    float64 `json:"pressure"`
	Humidity    float64 `json:"humidity"`
	IsAnomaly   bool    `json:"is_anomaly"`
	AnomalyType string  `json:"anomaly_type"`
	Status      string  `json:"status"`
}

// Calculate Great-Circle distance in kilometers using the Haversine formula
func calculateHaversine(lat1, lon1, lat2, lon2 float64) float64 {
	const R = 6371.0 // Earth radius in km
	dLat := (lat2 - lat1) * (math.Pi / 180.0)
	dLon := (lon2 - lon1) * (math.Pi / 180.0)

	a := math.Sin(dLat/2)*math.Sin(dLat/2) +
		math.Cos(lat1*(math.Pi/180.0))*math.Cos(lat2*(math.Pi/180.0))*
			math.Sin(dLon/2)*math.Sin(dLon/2)
	c := 2 * math.Atan2(math.Sqrt(a), math.Sqrt(1-a))
	return math.Round(R*c*10) / 10
}

func (dm *DatabaseManager) GetStationList() []StationInfo {
	dm.mu.Lock()
	localDB := dm.localDB
	neonDB := dm.neonDB
	neonOK := dm.neonConnOK
	dm.mu.Unlock()

	const baseLat = 21.4934 // AWS-01 Balasore / Chandipur Ground Station
	const baseLon = 86.9135

	defaultStations := map[string]StationInfo{
		"AWS-01": {StationID: "AWS-01", Name: "AWS-01 Base Ground Station", Region: "Local Proving Ground (Direct Ingest)", IsLocal: true, Status: "ONLINE_LAN", Latitude: 21.4934, Longitude: 86.9135, DistanceKM: 0.0, Temperature: 31.0, Pressure: 1013.2, Humidity: 65.0},
		"AWS-02": {StationID: "AWS-02", Name: "AWS-02 Northern Outpost", Region: "North Meteorological Sector", IsLocal: false, Status: "ONLINE_CLOUD", Latitude: 21.7231, Longitude: 86.9841, DistanceKM: calculateHaversine(baseLat, baseLon, 21.7231, 86.9841), Temperature: 31.2, Pressure: 1013.0, Humidity: 64.6},
		"AWS-03": {StationID: "AWS-03", Name: "AWS-03 Eastern Range Node", Region: "East Coastal Corridor", IsLocal: false, Status: "ONLINE_CLOUD", Latitude: 21.3120, Longitude: 87.1240, DistanceKM: calculateHaversine(baseLat, baseLon, 21.3120, 87.1240), Temperature: 30.9, Pressure: 1013.3, Humidity: 65.2},
		"AWS-04": {StationID: "AWS-04", Name: "AWS-04 Southern Plateau Node", Region: "South Highland Ridge", IsLocal: false, Status: "ONLINE_CLOUD", Latitude: 21.2840, Longitude: 86.7210, DistanceKM: calculateHaversine(baseLat, baseLon, 21.2840, 86.7210), Temperature: 31.1, Pressure: 1013.1, Humidity: 64.8},
		"AWS-05": {StationID: "AWS-05", Name: "AWS-05 Western Desert Outpost", Region: "West Arid Zone Node", IsLocal: false, Status: "ONLINE_CLOUD", Latitude: 21.5540, Longitude: 86.5820, DistanceKM: calculateHaversine(baseLat, baseLon, 21.5540, 86.5820), Temperature: 31.4, Pressure: 1012.8, Humidity: 63.9},
		"AWS-06": {StationID: "AWS-06", Name: "AWS-06 Himalayan Range Node", Region: "North Altitude Sector", IsLocal: false, Status: "ONLINE_CLOUD", Latitude: 21.8410, Longitude: 86.8520, DistanceKM: calculateHaversine(baseLat, baseLon, 21.8410, 86.8520), Temperature: 30.7, Pressure: 1013.5, Humidity: 65.8},
		"AWS-07": {StationID: "AWS-07", Name: "AWS-07 Central Command Outpost", Region: "Central Valley Base", IsLocal: false, Status: "ONLINE_CLOUD", Latitude: 21.4210, Longitude: 87.0120, DistanceKM: calculateHaversine(baseLat, baseLon, 21.4210, 87.0120), Temperature: 31.0, Pressure: 1013.2, Humidity: 65.1},
		"AWS-08": {StationID: "AWS-08", Name: "AWS-08 Island Coastal Beacon", Region: "Offshore Maritime Sector", IsLocal: false, Status: "ONLINE_CLOUD", Latitude: 21.3650, Longitude: 87.2140, DistanceKM: calculateHaversine(baseLat, baseLon, 21.3650, 87.2140), Temperature: 30.8, Pressure: 1013.4, Humidity: 66.0},
		"AWS-09": {StationID: "AWS-09", Name: "AWS-09 Tactical Forward Base", Region: "Forward Proving Perimeter", IsLocal: false, Status: "ONLINE_CLOUD", Latitude: 21.6120, Longitude: 87.0420, DistanceKM: calculateHaversine(baseLat, baseLon, 21.6120, 87.0420), Temperature: 31.3, Pressure: 1012.9, Humidity: 64.2},
		"AWS-10": {StationID: "AWS-10", Name: "AWS-10 Strategic Radar Node", Region: "Aerospace Tracking Sector", IsLocal: false, Status: "ONLINE_CLOUD", Latitude: 21.4820, Longitude: 86.7810, DistanceKM: calculateHaversine(baseLat, baseLon, 21.4820, 86.7810), Temperature: 31.1, Pressure: 1013.1, Humidity: 64.9},
	}

	// 1. Query Local DB for telemetry snapshots
	if localDB != nil {
		rows, err := localDB.Query(`
			SELECT station_id, MAX(timestamp) as last_seen, temperature, pressure, humidity, is_anomaly, anomaly_type
			FROM telemetry_logs
			GROUP BY station_id
		`)
		if err == nil {
			defer rows.Close()
			for rows.Next() {
				var stID, anomType string
				var ts int64
				var temp, press, hum float64
				var isAnomInt int
				if err := rows.Scan(&stID, &ts, &temp, &press, &hum, &isAnomInt, &anomType); err == nil {
					info, exists := defaultStations[stID]
					if !exists {
						info = StationInfo{
							StationID: stID,
							Name:      fmt.Sprintf("%s Cloud Observation Node", stID),
							Region:    "NeonDB Distributed Network",
							IsLocal:   (stID == "AWS-01"),
							Status:    "ONLINE_CLOUD",
						}
					}
					info.LastSeen = ts
					info.Temperature = temp
					info.Pressure = press
					info.Humidity = hum
					info.IsAnomaly = (isAnomInt == 1)
					info.AnomalyType = anomType
					defaultStations[stID] = info
				}
			}
		}
	}

	// 2. Query Neon Cloud PostgreSQL DB if active
	if neonOK && neonDB != nil {
		rows, err := neonDB.Query(`
			SELECT station_id, MAX(timestamp) as last_seen, temperature, pressure, humidity, is_anomaly, anomaly_type
			FROM telemetry_logs
			GROUP BY station_id, temperature, pressure, humidity, is_anomaly, anomaly_type
			ORDER BY last_seen DESC
			LIMIT 30
		`)
		if err == nil {
			defer rows.Close()
			for rows.Next() {
				var stID, anomType string
				var ts int64
				var temp, press, hum float64
				var isAnom bool
				if err := rows.Scan(&stID, &ts, &temp, &press, &hum, &isAnom, &anomType); err == nil {
					info, exists := defaultStations[stID]
					if !exists {
						info = StationInfo{
							StationID: stID,
							Name:      fmt.Sprintf("%s Cloud Station", stID),
							Region:    "NeonDB Cloud Ingest",
							IsLocal:   (stID == "AWS-01"),
							Status:    "ONLINE_CLOUD",
						}
					}
					if ts > info.LastSeen {
						info.LastSeen = ts
						info.Temperature = temp
						info.Pressure = press
						info.Humidity = hum
						info.IsAnomaly = isAnom
						info.AnomalyType = anomType
						defaultStations[stID] = info
					}
				}
			}
		}
	}

	res := make([]StationInfo, 0, len(defaultStations))
	orderedKeys := []string{"AWS-01", "AWS-02", "AWS-03", "AWS-04", "AWS-05", "AWS-06", "AWS-07", "AWS-08", "AWS-09", "AWS-10"}
	for _, id := range orderedKeys {
		if st, ok := defaultStations[id]; ok {
			res = append(res, st)
			delete(defaultStations, id)
		}
	}
	for _, st := range defaultStations {
		res = append(res, st)
	}

	return res
}

func (dm *DatabaseManager) GetStats() map[string]interface{} {
	dm.mu.Lock()
	localDB := dm.localDB
	dm.mu.Unlock()

	total := 0
	anomalies := 0

	if localDB != nil {
		row := localDB.QueryRow(`
			SELECT COUNT(*), COALESCE(SUM(CASE WHEN is_anomaly = 1 THEN 1 ELSE 0 END), 0)
			FROM telemetry_logs
		`)
		_ = row.Scan(&total, &anomalies)
	}

	fi, err := os.Stat(dm.dbPath)
	dbSize := int64(0)
	if err == nil {
		dbSize = fi.Size()
	}

	return map[string]interface{}{
		"total_records":     total,
		"total_anomalies":   anomalies,
		"normal_records":    total - anomalies,
		"db_file_path":      dm.dbPath,
		"db_size_bytes":     dbSize,
		"db_engine":         "SQLite 3 (Local) + Neon PostgreSQL (Cloud)",
		"external_db_sync":  dm.config.Enabled,
		"external_provider": dm.config.Provider,
		"neon_conn_active":  dm.neonConnOK,
		"neon_endpoint":     "ep-winter-sky-ayfyunqv-pooler.c-5.us-east-2.aws.neon.tech",
	}
}

func (dm *DatabaseManager) loadConfig() {
	cfgFile := filepath.Join(filepath.Dir(dm.dbPath), "external_db_config.json")
	if data, err := os.ReadFile(cfgFile); err == nil {
		json.Unmarshal(data, &dm.config)
	}
}

func (dm *DatabaseManager) UpdateConfig(cfg ExternalDBConfig) {
	dm.mu.Lock()
	dm.config = cfg
	cfgFile := filepath.Join(filepath.Dir(dm.dbPath), "external_db_config.json")
	data, _ := json.MarshalIndent(cfg, "", "  ")
	os.WriteFile(cfgFile, data, 0644)
	dm.mu.Unlock()

	dm.initNeonPostgreSQL()
	log.Printf("✓ Database Manager updated config for Neon PostgreSQL Cloud DB.")
}
