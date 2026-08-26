package main

import (
	"encoding/binary"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"math"
	"strconv"
	"strings"
	"time"
)

type DecodedAWS struct {
	Timestamp      int64           `json:"timestamp"` // Unix timestamp in seconds
	TimeInst       uint32          `json:"time_inst"`
	Direction      uint16          `json:"direction"`
	Speed          float64         `json:"speed"`
	DryBulbTemp    float64         `json:"dry_bulb_temp"`
	WetBulbTemp    float64         `json:"wet_bulb_temp"`
	RelHumidity    float64         `json:"rel_humidity"`
	SolarRadiation float64         `json:"solar_radiation"`
	Rainfall       float64         `json:"rainfall"`
	PressureHpa    float64         `json:"pressure_hpa"`
	PressureImu    float64         `json:"pressure_imu"`
	PresentMap     map[string]bool `json:"present_map"`
}

type ParameterField struct {
	ID         int     `json:"id"`
	Name       string  `json:"name"`
	BinaryType string  `json:"binary_type"`
	Unit       string  `json:"unit"`
	Scale      float64 `json:"scale"`
	Offset     float64 `json:"offset"`
	Value      float64 `json:"value"`
	Formatted  string  `json:"formatted"`
	Status     string  `json:"status"`  // "ENABLED" or "DISABLED"
	Present    bool    `json:"present"` // true if in frame, false if missing
}

func (d *DecodedAWS) ToParameterList() []ParameterField {
	if d == nil {
		return []ParameterField{}
	}
	pImu := d.PressureImu
	if pImu == 0 {
		pImu = d.PressureHpa
	}

	isPres := func(key string) bool {
		if d.PresentMap == nil || len(d.PresentMap) == 0 {
			return true // default all present if unspecified
		}
		return d.PresentMap[key]
	}

	getStatus := func(key string) string {
		if isPres(key) {
			return "ENABLED"
		}
		return "DISABLED"
	}

	return []ParameterField{
		{ID: 1, Name: "Time_Inst", BinaryType: "uint32", Unit: "--", Scale: 1, Offset: 0, Value: float64(d.TimeInst), Formatted: fmt.Sprintf("%d", d.TimeInst), Status: getStatus("time_inst"), Present: isPres("time_inst")},
		{ID: 2, Name: "Direction", BinaryType: "uint16", Unit: "DEG", Scale: 1, Offset: 0, Value: float64(d.Direction), Formatted: fmt.Sprintf("%d DEG", d.Direction), Status: getStatus("direction"), Present: isPres("direction")},
		{ID: 3, Name: "Speed", BinaryType: "uint16", Unit: "M/S", Scale: 0.1, Offset: 0, Value: d.Speed, Formatted: fmt.Sprintf("%.1f M/S", d.Speed), Status: getStatus("speed"), Present: isPres("speed")},
		{ID: 4, Name: "Dry Bulb Temp", BinaryType: "int16", Unit: "°C", Scale: 0.1, Offset: 0, Value: d.DryBulbTemp, Formatted: fmt.Sprintf("%.1f °C", d.DryBulbTemp), Status: getStatus("dry_bulb_temp"), Present: isPres("dry_bulb_temp")},
		{ID: 5, Name: "Wet Bulb Temp", BinaryType: "int16", Unit: "°C", Scale: 0.1, Offset: 0, Value: d.WetBulbTemp, Formatted: fmt.Sprintf("%.1f °C", d.WetBulbTemp), Status: getStatus("wet_bulb_temp"), Present: isPres("wet_bulb_temp")},
		{ID: 6, Name: "Rel. Humidity", BinaryType: "uint16", Unit: "%", Scale: 0.1, Offset: 0, Value: d.RelHumidity, Formatted: fmt.Sprintf("%.1f %%", d.RelHumidity), Status: getStatus("rel_humidity"), Present: isPres("rel_humidity")},
		{ID: 7, Name: "Solar Radiation", BinaryType: "uint16", Unit: "W/M²", Scale: 1, Offset: 0, Value: d.SolarRadiation, Formatted: fmt.Sprintf("%.0f W/M²", d.SolarRadiation), Status: getStatus("solar_radiation"), Present: isPres("solar_radiation")},
		{ID: 8, Name: "Rainfall", BinaryType: "uint16", Unit: "MM", Scale: 0.1, Offset: 0, Value: d.Rainfall, Formatted: fmt.Sprintf("%.1f MM", d.Rainfall), Status: getStatus("rainfall"), Present: isPres("rainfall")},
		{ID: 9, Name: "Pressure (IMU)", BinaryType: "float32", Unit: "hPa", Scale: 1, Offset: 0, Value: pImu, Formatted: fmt.Sprintf("%.2f hPa", pImu), Status: getStatus("pressure_imu"), Present: isPres("pressure_imu")},
		{ID: 10, Name: "Pressure (hPa)", BinaryType: "uint32", Unit: "hPa", Scale: 0.01, Offset: 0, Value: d.PressureHpa, Formatted: fmt.Sprintf("%.2f hPa", d.PressureHpa), Status: getStatus("pressure_hpa"), Present: isPres("pressure_hpa")},
	}
}

func (d *DecodedAWS) ToActiveParameterList() []ParameterField {
	all := d.ToParameterList()
	active := make([]ParameterField, 0)
	for _, p := range all {
		if p.Present {
			active = append(active, p)
		}
	}
	return active
}

const ExpectedFrameSize = 31

func ParseAWSFrame(data []byte) (*DecodedAWS, error) {
	if len(data) == 0 {
		return nil, errors.New("empty payload")
	}

	str := strings.TrimSpace(string(data))
	cleanHex := ""
	for _, ch := range str {
		if (ch >= '0' && ch <= '9') || (ch >= 'A' && ch <= 'F') || (ch >= 'a' && ch <= 'f') {
			cleanHex += string(ch)
		}
	}
	if len(cleanHex) >= 4 && len(cleanHex)%2 == 0 && (strings.HasPrefix(strings.ToUpper(cleanHex), "AA55") || strings.HasPrefix(strings.ToUpper(cleanHex), "55AA")) {
		if decodedHex, err := hex.DecodeString(cleanHex); err == nil && len(decodedHex) >= 10 {
			data = decodedHex
		}
	}

	if len(data) >= 10 && (data[0] == 0xAA && data[1] == 0x55 || data[0] == 0x55 && data[1] == 0xAA) {
		return parseBinaryFrame(data)
	}

	if len(data) >= 28 && (len(data)%4 == 0 || len(data)%8 == 0) {
		if raw, err := parseRawBinaryStream(data); err == nil {
			return raw, nil
		}
	}

	if strings.HasPrefix(str, "{") && strings.HasSuffix(str, "}") {
		return parseJSONFrame(str)
	}

	if strings.Contains(str, ",") {
		return parseCSVFrame(str)
	}

	return nil, fmt.Errorf("unrecognized format (byte len: %d)", len(data))
}

func parseBinaryFrame(data []byte) (*DecodedAWS, error) {
	minSize := 24
	if len(data) < minSize {
		return nil, fmt.Errorf("frame size too short: %d bytes", len(data))
	}

	now := time.Now().Unix()

	// Check if this is a 41-byte (or 37+ byte) float32 layout packed as:
	// <HIHffffffff (Sync:2, Time_Inst:4, Direction:2, Speed:4, DryTemp:4, WetTemp:4, Humidity:4, PressureIMU:4, PressureHpa:4, Solar:4, Rain:4, Checksum:1)
	if len(data) >= 36 {
		timeInst := binary.LittleEndian.Uint32(data[2:6])
		dir := binary.LittleEndian.Uint16(data[6:8])
		speed := float64(math.Float32frombits(binary.LittleEndian.Uint32(data[8:12])))
		dryTemp := float64(math.Float32frombits(binary.LittleEndian.Uint32(data[12:16])))
		wetTemp := float64(math.Float32frombits(binary.LittleEndian.Uint32(data[16:20])))
		humidity := float64(math.Float32frombits(binary.LittleEndian.Uint32(data[20:24])))

		// Validate if float32 interpretations fall within valid meteorological physical bounds
		if !math.IsNaN(dryTemp) && dryTemp >= -60 && dryTemp <= 80 &&
			!math.IsNaN(humidity) && humidity >= 0 && humidity <= 100 {

			var pressImu, pressHpa, solar, rain float64
			if len(data) >= 28 {
				pressImu = float64(math.Float32frombits(binary.LittleEndian.Uint32(data[24:28])))
			}
			if len(data) >= 32 {
				pressHpa = float64(math.Float32frombits(binary.LittleEndian.Uint32(data[28:32])))
			}
			if len(data) >= 36 {
				solar = float64(math.Float32frombits(binary.LittleEndian.Uint32(data[32:36])))
			}
			if len(data) >= 40 {
				rain = float64(math.Float32frombits(binary.LittleEndian.Uint32(data[36:40])))
			}

			if pressHpa < 500 || pressHpa > 1100 {
				if pressImu >= 500 && pressImu <= 1100 {
					pressHpa = pressImu
				} else {
					pressHpa = 1013.25
				}
			}
			if pressImu < 500 || pressImu > 1100 {
				pressImu = pressHpa
			}

			presentMap := map[string]bool{
				"time_inst":       true,
				"direction":       true,
				"speed":           true,
				"dry_bulb_temp":   true,
				"wet_bulb_temp":   true,
				"rel_humidity":    true,
				"solar_radiation": true,
				"rainfall":        true,
				"pressure_imu":    true,
				"pressure_hpa":    true,
			}

			return &DecodedAWS{
				Timestamp:      now,
				TimeInst:       timeInst,
				Direction:      dir,
				Speed:          speed,
				DryBulbTemp:    dryTemp,
				WetBulbTemp:    wetTemp,
				RelHumidity:    humidity,
				SolarRadiation: solar,
				Rainfall:       rain,
				PressureHpa:    pressHpa,
				PressureImu:    pressImu,
				PresentMap:     presentMap,
			}, nil
		}
	}

	// Legacy int16 scaled layout (<HIHhhhhhI)
	timeInst := binary.LittleEndian.Uint32(data[2:6])
	dir := binary.LittleEndian.Uint16(data[6:8])
	rawSpeed := binary.LittleEndian.Uint16(data[8:10])

	rawDryTemp := int16(binary.LittleEndian.Uint16(data[10:12]))
	rawWetTemp := int16(binary.LittleEndian.Uint16(data[12:14]))
	rawHumidity := binary.LittleEndian.Uint16(data[14:16])
	rawSolar := binary.LittleEndian.Uint16(data[16:18])
	rawRain := binary.LittleEndian.Uint16(data[18:20])

	var rawPressure uint32
	if len(data) >= 24 {
		rawPressure = binary.LittleEndian.Uint32(data[20:24])
	} else {
		rawPressure = 101325
	}

	dryTemp := float64(rawDryTemp) * 0.1
	wetTemp := float64(rawWetTemp) * 0.1
	humidity := float64(rawHumidity) * 0.1
	speed := float64(rawSpeed) * 0.1
	rain := float64(rawRain) * 0.1
	solar := float64(rawSolar) * 1.0
	pressure := float64(rawPressure) * 0.01

	if pressure < 500 || pressure > 1100 {
		pressure = 1013.25
	}

	presentMap := map[string]bool{
		"time_inst":       true,
		"direction":       true,
		"speed":           true,
		"dry_bulb_temp":   true,
		"wet_bulb_temp":   true,
		"rel_humidity":    true,
		"solar_radiation": true,
		"rainfall":        true,
		"pressure_imu":    true,
		"pressure_hpa":    true,
	}

	return &DecodedAWS{
		Timestamp:      now,
		TimeInst:       timeInst,
		Direction:      dir,
		Speed:          speed,
		DryBulbTemp:    dryTemp,
		WetBulbTemp:    wetTemp,
		RelHumidity:    humidity,
		SolarRadiation: solar,
		Rainfall:       rain,
		PressureHpa:    pressure,
		PressureImu:    pressure,
		PresentMap:     presentMap,
	}, nil
}

func parseRawBinaryStream(data []byte) (*DecodedAWS, error) {
	now := time.Now().Unix()
	if len(data) >= 40 {
		dryTemp := float64(math.Float32frombits(binary.LittleEndian.Uint32(data[0:4])))
		humidity := float64(math.Float32frombits(binary.LittleEndian.Uint32(data[4:8])))
		pressure := float64(math.Float32frombits(binary.LittleEndian.Uint32(data[8:12])))

		if dryTemp >= -50 && dryTemp <= 70 && humidity >= 0 && humidity <= 100 && pressure >= 500 && pressure <= 1100 {
			presentMap := map[string]bool{
				"dry_bulb_temp": true,
				"rel_humidity":  true,
				"pressure_hpa":  true,
				"pressure_imu":  true,
			}
			return &DecodedAWS{
				Timestamp:   now,
				TimeInst:    uint32(now),
				DryBulbTemp: dryTemp,
				WetBulbTemp: dryTemp - 3.0,
				RelHumidity: humidity,
				PressureHpa: pressure,
				PressureImu: pressure,
				PresentMap:  presentMap,
			}, nil
		}
	}
	return nil, errors.New("invalid float binary stream")
}

func parseJSONFrame(jsonStr string) (*DecodedAWS, error) {
	var m map[string]interface{}
	if err := json.Unmarshal([]byte(jsonStr), &m); err != nil {
		return nil, err
	}

	presentMap := make(map[string]bool)

	checkKey := func(standardKey string, jsonKeys ...string) float64 {
		for _, k := range jsonKeys {
			if val, ok := m[k]; ok {
				presentMap[standardKey] = true
				switch v := val.(type) {
				case float64:
					return v
				case string:
					if f, err := strconv.ParseFloat(v, 64); err == nil {
						return f
					}
				}
			}
		}
		return 0
	}

	dryTemp := checkKey("dry_bulb_temp", "dry_bulb_temp", "temp_dry", "temperature", "temp", "t")
	humidity := checkKey("rel_humidity", "rel_humidity", "humidity", "rh", "h")
	pressure := checkKey("pressure_hpa", "pressure_hpa", "pressure", "press", "p")
	wetTemp := checkKey("wet_bulb_temp", "wet_bulb_temp", "wet_temp")
	speed := checkKey("speed", "speed", "wind_speed")
	dir := checkKey("direction", "direction", "wind_dir")
	solar := checkKey("solar_radiation", "solar_radiation", "solar")
	rain := checkKey("rainfall", "rainfall", "rain")

	now := time.Now().Unix()

	if presentMap["pressure_hpa"] {
		presentMap["pressure_imu"] = true
	}

	return &DecodedAWS{
		Timestamp:      now,
		TimeInst:       uint32(now),
		DryBulbTemp:    dryTemp,
		WetBulbTemp:    wetTemp,
		RelHumidity:    humidity,
		PressureHpa:    pressure,
		PressureImu:    pressure,
		Speed:          speed,
		Direction:      uint16(dir),
		SolarRadiation: solar,
		Rainfall:       rain,
		PresentMap:     presentMap,
	}, nil
}

func parseCSVFrame(csvStr string) (*DecodedAWS, error) {
	parts := strings.Split(csvStr, ",")
	if len(parts) < 1 {
		return nil, errors.New("CSV line empty")
	}

	parseFloat := func(s string) float64 {
		f, _ := strconv.ParseFloat(strings.TrimSpace(s), 64)
		return f
	}

	presentMap := make(map[string]bool)
	now := time.Now().Unix()

	var dryTemp, humidity, pressure float64

	if len(parts) == 1 {
		// 1 field: Temp only
		dryTemp = parseFloat(parts[0])
		presentMap["dry_bulb_temp"] = true
	} else if len(parts) == 2 {
		// 2 fields: Temp, Humidity
		dryTemp = parseFloat(parts[0])
		humidity = parseFloat(parts[1])
		presentMap["dry_bulb_temp"] = true
		presentMap["rel_humidity"] = true
	} else if len(parts) >= 3 {
		// 3 fields: Temp, Pressure, Humidity
		dryTemp = parseFloat(parts[0])
		pressure = parseFloat(parts[1])
		humidity = parseFloat(parts[2])
		presentMap["dry_bulb_temp"] = true
		presentMap["pressure_hpa"] = true
		presentMap["pressure_imu"] = true
		presentMap["rel_humidity"] = true
	}

	return &DecodedAWS{
		Timestamp:   now,
		TimeInst:    uint32(now),
		DryBulbTemp: dryTemp,
		PressureHpa: pressure,
		PressureImu: pressure,
		RelHumidity: humidity,
		PresentMap:  presentMap,
	}, nil
}
