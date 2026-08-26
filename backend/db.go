package main

import (
	"database/sql"
	"encoding/json"
	"log"
	"os"
	"path/filepath"
	"sync"
	"time"

	_ "github.com/lib/pq"
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
	records    []TelemetryRecord
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
		dbPath:  dbFile,
		records: make([]TelemetryRecord, 0),
		config: ExternalDBConfig{
			Enabled:       true,
			Provider:      "NEON_POSTGRES",
			ConnectionURL: DefaultNeonURL,
			AutoSync:      true,
		},
	}

	dm.loadRecords()
	dm.loadConfig()
	dm.initNeonPostgreSQL()

	return dm
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

func (dm *DatabaseManager) loadRecords() {
	dm.mu.Lock()
	defer dm.mu.Unlock()

	if _, err := os.Stat(dm.dbPath); os.IsNotExist(err) {
		return
	}

	data, err := os.ReadFile(dm.dbPath)
	if err != nil || len(data) == 0 {
		return
	}

	var recs []TelemetryRecord
	if err := json.Unmarshal(data, &recs); err == nil {
		dm.records = recs
		log.Printf("✓ Local Offline DB (%s) loaded %d records.", filepath.Base(dm.dbPath), len(dm.records))
	}
}

func (dm *DatabaseManager) saveRecordsLocked() {
	data, err := json.MarshalIndent(dm.records, "", "  ")
	if err != nil {
		return
	}
	os.WriteFile(dm.dbPath, data, 0644)
}

func (dm *DatabaseManager) InsertRecord(res AnomalyResult, temp, press, hum float64) TelemetryRecord {
	dm.mu.Lock()

	id := int64(len(dm.records) + 1)
	now := time.Now()

	rec := TelemetryRecord{
		ID:                 id,
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
		CreatedAt:          now.UTC().Format(time.RFC3339),
	}

	dm.records = append(dm.records, rec)
	if len(dm.records) > 10000 {
		dm.records = dm.records[len(dm.records)-10000:]
	}

	dm.saveRecordsLocked()

	neonOK := dm.neonConnOK
	neonDB := dm.neonDB
	dm.mu.Unlock()

	if neonOK && neonDB != nil {
		go func(r TelemetryRecord) {
			shapJSON, _ := json.Marshal(r.ShapAttributions)
			healthJSON, _ := json.Marshal(r.SensorHealth)

			insertSQL := `
			INSERT INTO telemetry_logs (
				timestamp, station_id, temperature, pressure, humidity,
				is_anomaly, anomaly_score, anomaly_type, severity,
				confidence_category, explanation, shap_attributions, sensor_health
			) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)`

			_, err := neonDB.Exec(insertSQL,
				r.Timestamp, r.StationID, r.Temperature, r.Pressure, r.Humidity,
				r.IsAnomaly, r.AnomalyScore, r.AnomalyType, r.Severity,
				r.ConfidenceCategory, r.Explanation, string(shapJSON), string(healthJSON),
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
	recs := make([]TelemetryRecord, len(dm.records))
	copy(recs, dm.records)
	neonOK := dm.neonConnOK
	neonDB := dm.neonDB
	dm.mu.Unlock()

	if !neonOK || neonDB == nil {
		return 0, nil
	}

	synced := 0
	for _, r := range recs {
		shapJSON, _ := json.Marshal(r.ShapAttributions)
		healthJSON, _ := json.Marshal(r.SensorHealth)

		insertSQL := `
		INSERT INTO telemetry_logs (
			timestamp, station_id, temperature, pressure, humidity,
			is_anomaly, anomaly_score, anomaly_type, severity,
			confidence_category, explanation, shap_attributions, sensor_health
		) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)`

		_, err := neonDB.Exec(insertSQL,
			r.Timestamp, r.StationID, r.Temperature, r.Pressure, r.Humidity,
			r.IsAnomaly, r.AnomalyScore, r.AnomalyType, r.Severity,
			r.ConfidenceCategory, r.Explanation, string(shapJSON), string(healthJSON),
		)
		if err == nil {
			synced++
		}
	}
	return synced, nil
}

func (dm *DatabaseManager) GetHistory(limit int) []TelemetryRecord {
	dm.mu.Lock()
	defer dm.mu.Unlock()

	if limit <= 0 || limit > len(dm.records) {
		limit = len(dm.records)
	}

	start := len(dm.records) - limit
	res := make([]TelemetryRecord, limit)
	copy(res, dm.records[start:])
	return res
}

func (dm *DatabaseManager) GetStats() map[string]interface{} {
	dm.mu.Lock()
	defer dm.mu.Unlock()

	total := len(dm.records)
	anomalies := 0
	for _, r := range dm.records {
		if r.IsAnomaly {
			anomalies++
		}
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
