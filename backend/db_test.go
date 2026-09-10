package main

import (
	"os"
	"path/filepath"
	"testing"
)

func TestDatabaseManagerSQLite(t *testing.T) {
	tempDir, err := os.MkdirTemp("", "skyguard_db_test_*")
	if err != nil {
		t.Fatalf("Failed to create temp dir: %v", err)
	}
	defer os.RemoveAll(tempDir)

	dm := NewDatabaseManager(tempDir)
	if dm.localDB == nil {
		t.Fatalf("Expected dm.localDB to be initialized")
	}

	dbFile := filepath.Join(tempDir, "database", "skyguard_telemetry.db")
	if _, err := os.Stat(dbFile); os.IsNotExist(err) {
		t.Fatalf("Expected SQLite DB file to exist at %s", dbFile)
	}

	// Insert test record
	res := AnomalyResult{
		IsAnomaly:      true,
		Confidence:     0.88,
		AnomalyType:    "rapid_pressure_drop",
		Severity:       "HIGH",
		XAIExplanation: "Sudden pressure drop of 8.5 hPa detected.",
		StationID:      "TEST-AWS-01",
		ShapAttributions: map[string]float64{
			"pressure": 0.65,
			"temp":     0.23,
		},
		SensorHealth: map[string]float64{
			"barometer": 0.99,
		},
	}

	rec := dm.InsertRecord(res, 28.5, 995.2, 75.0)
	if rec.ID <= 0 {
		t.Errorf("Expected positive record ID, got %d", rec.ID)
	}

	// Fetch history
	history := dm.GetHistory(10)
	if len(history) != 1 {
		t.Fatalf("Expected 1 history record, got %d", len(history))
	}
	if history[0].StationID != "TEST-AWS-01" {
		t.Errorf("Expected StationID 'TEST-AWS-01', got '%s'", history[0].StationID)
	}
	if !history[0].IsAnomaly {
		t.Errorf("Expected IsAnomaly true")
	}
	if history[0].ShapAttributions["pressure"] != 0.65 {
		t.Errorf("Expected ShapAttributions['pressure']=0.65, got %v", history[0].ShapAttributions["pressure"])
	}

	// Check stats
	stats := dm.GetStats()
	if stats["total_records"].(int) != 1 {
		t.Errorf("Expected total_records=1, got %v", stats["total_records"])
	}
	if stats["total_anomalies"].(int) != 1 {
		t.Errorf("Expected total_anomalies=1, got %v", stats["total_anomalies"])
	}
	if stats["db_size_bytes"].(int64) <= 0 {
		t.Errorf("Expected positive db_size_bytes, got %v", stats["db_size_bytes"])
	}

	_ = dm.localDB.Close()
}
