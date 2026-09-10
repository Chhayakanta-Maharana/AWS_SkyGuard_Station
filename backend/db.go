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
	if limit <= 0 {
		limit = 100
	}

	dm.mu.Lock()
	localDB := dm.localDB
	dm.mu.Unlock()

	if localDB == nil {
		return []TelemetryRecord{}
	}

	query := `
		SELECT id, timestamp, station_id, temperature, pressure, humidity,
		       is_anomaly, anomaly_score, anomaly_type, severity,
		       confidence_category, explanation, shap_attributions, sensor_health, created_at
		FROM (
			SELECT * FROM telemetry_logs ORDER BY id DESC LIMIT ?
		) sub
		ORDER BY id ASC
	`

	rows, err := localDB.Query(query, limit)
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
