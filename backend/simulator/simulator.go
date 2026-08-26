package simulator

import (
	"encoding/binary"
	"encoding/csv"
	"fmt"
	"io"
	"math"
	"os"
	"strconv"
	"sync"
	"time"

	"aws-backend/parser"
)

type AnomalyConfig struct {
	Type      string  // "spike", "freeze", "drift", "outage", "none"
	Parameter string  // "temp_dry", "humidity", "pressure_hpa"
	Value     float64 // Spike offset or drift rate
}

type Simulator struct {
	mu           sync.Mutex
	filePath     string
	records      []parser.DecodedAWS
	currentIndex int
	anomaly      AnomalyConfig
	driftSum     float64
	frozenVals   map[string]float64
}

func NewSimulator(filePath string) (*Simulator, error) {
	sim := &Simulator{
		filePath:   filePath,
		records:    make([]parser.DecodedAWS, 0),
		anomaly:    AnomalyConfig{Type: "none"},
		frozenVals: make(map[string]float64),
	}

	err := sim.loadRecords()
	if err != nil {
		return nil, err
	}

	return sim, nil
}

func (s *Simulator) loadRecords() error {
	file, err := os.Open(s.filePath)
	if err != nil {
		return err
	}
	defer file.Close()

	reader := csv.NewReader(file)
	// Skip header
	_, err = reader.Read()
	if err != nil {
		return err
	}

	for {
		record, err := reader.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			return err
		}

		if len(record) < 10 {
			continue
		}

		ts, _ := strconv.ParseInt(record[0], 10, 64)
		dir, _ := strconv.ParseFloat(record[1], 64)
		speed, _ := strconv.ParseFloat(record[2], 64)
		tempDry, _ := strconv.ParseFloat(record[3], 64)
		tempWet, _ := strconv.ParseFloat(record[4], 64)
		humidity, _ := strconv.ParseFloat(record[5], 64)
		solar, _ := strconv.ParseFloat(record[6], 64)
		rain, _ := strconv.ParseFloat(record[7], 64)
		pImu, _ := strconv.ParseFloat(record[8], 64)
		pHpa, _ := strconv.ParseFloat(record[9], 64)

		s.records = append(s.records, parser.DecodedAWS{
			Timestamp:      ts,
			TimeInst:       uint32(ts),
			Direction:      uint16(dir),
			Speed:          speed,
			DryBulbTemp:    tempDry,
			WetBulbTemp:    tempWet,
			RelHumidity:    humidity,
			SolarRadiation: solar,
			Rainfall:       rain,
			PressureImu:    pImu,
			PressureHpa:    pHpa,
		})
	}

	if len(s.records) == 0 {
		return fmt.Errorf("no records found in AWS input file")
	}

	return nil
}

func (s *Simulator) InjectAnomaly(config AnomalyConfig) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.anomaly = config
	s.driftSum = 0
	s.frozenVals = make(map[string]float64)
}

func (s *Simulator) GetNextReading() (*parser.DecodedAWS, bool) {
	s.mu.Lock()
	defer s.mu.Unlock()

	if len(s.records) == 0 {
		return nil, false
	}

	raw := s.records[s.currentIndex]
	s.currentIndex = (s.currentIndex + 1) % len(s.records)

	raw.Timestamp = time.Now().Unix()
	raw.TimeInst = uint32(raw.Timestamp)

	if s.anomaly.Type == "outage" {
		return nil, true
	}

	s.applyAnomalies(&raw)

	return &raw, true
}

func (s *Simulator) applyAnomalies(t *parser.DecodedAWS) {
	if s.anomaly.Type == "none" {
		return
	}

	switch s.anomaly.Type {
	case "spike":
		if s.anomaly.Parameter == "temp_dry" {
			t.DryBulbTemp += s.anomaly.Value
		} else if s.anomaly.Parameter == "humidity" {
			t.RelHumidity += s.anomaly.Value
			if t.RelHumidity < 0 {
				t.RelHumidity = 0
			} else if t.RelHumidity > 100 {
				t.RelHumidity = 100
			}
		} else if s.anomaly.Parameter == "pressure_hpa" {
			t.PressureHpa += s.anomaly.Value
		}

	case "drift":
		s.driftSum += s.anomaly.Value
		if s.anomaly.Parameter == "temp_dry" {
			t.DryBulbTemp += s.driftSum
		} else if s.anomaly.Parameter == "humidity" {
			t.RelHumidity += s.driftSum
			if t.RelHumidity < 0 {
				t.RelHumidity = 0
			} else if t.RelHumidity > 100 {
				t.RelHumidity = 100
			}
		} else if s.anomaly.Parameter == "pressure_hpa" {
			t.PressureHpa += s.driftSum
		}

	case "freeze":
		if _, ok := s.frozenVals["temp_dry"]; !ok {
			s.frozenVals["temp_dry"] = t.DryBulbTemp
			s.frozenVals["humidity"] = t.RelHumidity
			s.frozenVals["pressure_hpa"] = t.PressureHpa
		}

		if s.anomaly.Parameter == "temp_dry" {
			t.DryBulbTemp = s.frozenVals["temp_dry"]
		} else if s.anomaly.Parameter == "humidity" {
			t.RelHumidity = s.frozenVals["humidity"]
		} else if s.anomaly.Parameter == "pressure_hpa" {
			t.PressureHpa = s.frozenVals["pressure_hpa"]
		}
	}
}

// PackToBinary encodes a DecodedAWS struct into the raw 31-byte binary packet format (matching aws_station_config.json)
func PackToBinary(d *parser.DecodedAWS) []byte {
	buf := make([]byte, parser.ExpectedFrameSize)

	// Sync Header: AA 55
	buf[0] = 0xAA
	buf[1] = 0x55

	// Scale variables back
	rawSpeed := uint16(math.Round(d.Speed / 0.1))
	rawDryTemp := int16(math.Round(d.DryBulbTemp / 0.1))
	rawWetTemp := int16(math.Round(d.WetBulbTemp / 0.1))
	rawHumidity := uint16(math.Round(d.RelHumidity / 0.1))
	rawSolar := uint16(math.Round(d.SolarRadiation / 1.0))
	rawRain := uint16(math.Round(d.Rainfall / 0.1))
	rawPressure := uint32(math.Round(d.PressureHpa / 0.01))

	binary.LittleEndian.PutUint32(buf[2:6], d.TimeInst)
	binary.LittleEndian.PutUint16(buf[6:8], d.Direction)
	binary.LittleEndian.PutUint16(buf[8:10], rawSpeed)
	binary.LittleEndian.PutUint16(buf[10:12], uint16(rawDryTemp))
	binary.LittleEndian.PutUint16(buf[12:14], uint16(rawWetTemp))
	binary.LittleEndian.PutUint16(buf[14:16], rawHumidity)
	binary.LittleEndian.PutUint16(buf[16:18], rawSolar)
	binary.LittleEndian.PutUint16(buf[18:20], rawRain)
	binary.LittleEndian.PutUint32(buf[20:24], rawPressure)

	// Calculate checksum8
	sum := 0
	for i := 0; i < parser.ExpectedFrameSize-1; i++ {
		sum += int(buf[i])
	}
	buf[parser.ExpectedFrameSize-1] = uint8(sum % 256)

	return buf
}
