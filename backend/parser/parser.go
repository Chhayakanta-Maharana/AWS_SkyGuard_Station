package parser

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
	Timestamp      int64   `json:"timestamp"` // Unix timestamp in seconds
	TimeInst       uint32  `json:"time_inst"`
	Direction      uint16  `json:"direction"`
	Speed          float64 `json:"speed"`
	DryBulbTemp    float64 `json:"dry_bulb_temp"`
	WetBulbTemp    float64 `json:"wet_bulb_temp"`
	RelHumidity    float64 `json:"rel_humidity"`
	SolarRadiation float64 `json:"solar_radiation"`
	Rainfall       float64 `json:"rainfall"`
	PressureHpa    float64 `json:"pressure_hpa"`
	PressureImu    float64 `json:"pressure_imu"`
}

const ExpectedFrameSize = 31 // 2 (Sync) + 4 (Time) + 2 (Dir) + 2 (Speed) + 2 (DryTemp) + 2 (WetTemp) + 2 (Humidity) + 2 (Solar) + 2 (Rain) + 4 (Pressure) + 1 (Checksum)

func ParseAWSFrame(data []byte) (*DecodedAWS, error) {
	if len(data) == 0 {
		return nil, errors.New("empty payload")
	}

	// 0. Auto-decode ASCII Hex text (e.g. "AA55...")
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

	// 1. Try Binary Frame Format (0xAA 0x55 Sync Header)
	if len(data) >= 10 && (data[0] == 0xAA && data[1] == 0x55 || data[0] == 0x55 && data[1] == 0xAA) {
		return parseBinaryFrame(data)
	}

	// 2. Try Raw Binary Floats (e.g. 10 float32s = 40 bytes or 10 float64s = 80 bytes)
	if len(data) >= 28 && (len(data)%4 == 0 || len(data)%8 == 0) {
		if raw, err := parseRawBinaryStream(data); err == nil {
			return raw, nil
		}
	}

	// 3. Try JSON Format (e.g. {"dry_bulb_temp": 25.4, ...})
	trimmed := strings.TrimSpace(string(data))
	if strings.HasPrefix(trimmed, "{") && strings.HasSuffix(trimmed, "}") {
		var decoded DecodedAWS
		if err := json.Unmarshal([]byte(trimmed), &decoded); err == nil {
			if decoded.Timestamp == 0 {
				decoded.Timestamp = time.Now().Unix()
			}
			return &decoded, nil
		}
	}

	// 4. Try CSV / Text Format (e.g. "Time,Dir,Speed,Dry,Wet,RH,Solar,Rain,P_IMU,Press")
	if strings.Contains(trimmed, ",") || strings.Contains(trimmed, "\t") || strings.Contains(trimmed, " ") {
		delimiter := ","
		if !strings.Contains(trimmed, ",") && strings.Contains(trimmed, "\t") {
			delimiter = "\t"
		} else if !strings.Contains(trimmed, ",") && strings.Contains(trimmed, " ") {
			delimiter = " "
		}
		
		parts := strings.Split(trimmed, delimiter)
		cleanParts := make([]string, 0)
		for _, p := range parts {
			cp := strings.TrimSpace(p)
			if cp != "" {
				cleanParts = append(cleanParts, cp)
			}
		}
		if len(cleanParts) >= 3 {
			return parseCSVFrame(cleanParts)
		}
	}

	return nil, fmt.Errorf("unrecognized telemetry packet format (%d bytes)", len(data))
}

func parseRawBinaryStream(data []byte) (*DecodedAWS, error) {
	// Try float32 representation (4-bytes each)
	if len(data) >= 32 && len(data)%4 == 0 {
		count := len(data) / 4
		vals := make([]float64, count)
		for i := 0; i < count; i++ {
			bits := binary.LittleEndian.Uint32(data[i*4 : (i+1)*4])
			vals[i] = float64(math.Float32frombits(bits))
		}
		
		// Validate if numbers look like plausible telemetry
		if count >= 8 {
			dry := vals[3]
			press := vals[len(vals)-1]
			if dry >= -50.0 && dry <= 70.0 && press >= 800.0 && press <= 1100.0 {
				return &DecodedAWS{
					Timestamp:      time.Now().Unix(),
					TimeInst:       uint32(vals[0]),
					Direction:      uint16(vals[1]),
					Speed:          vals[2],
					DryBulbTemp:    vals[3],
					WetBulbTemp:    vals[4],
					RelHumidity:    vals[5],
					SolarRadiation: vals[6],
					Rainfall:       vals[7],
					PressureHpa:    press,
					PressureImu:    press,
				}, nil
			}
		}
	}
	return nil, errors.New("raw binary mismatch")
}

func parseBinaryFrame(data []byte) (*DecodedAWS, error) {
	// If 40+ bytes (float32 format from LAN data sender):
	if len(data) >= 40 {
		timeInst := binary.LittleEndian.Uint32(data[2:6])
		dir := binary.LittleEndian.Uint16(data[6:8])
		speed := float64(math.Float32frombits(binary.LittleEndian.Uint32(data[8:12])))
		dryTemp := float64(math.Float32frombits(binary.LittleEndian.Uint32(data[12:16])))
		wetTemp := float64(math.Float32frombits(binary.LittleEndian.Uint32(data[16:20])))
		humidity := float64(math.Float32frombits(binary.LittleEndian.Uint32(data[20:24])))
		pressImu := float64(math.Float32frombits(binary.LittleEndian.Uint32(data[24:28])))
		pressHpa := float64(math.Float32frombits(binary.LittleEndian.Uint32(data[28:32])))
		solar := float64(math.Float32frombits(binary.LittleEndian.Uint32(data[32:36])))
		rain := float64(0.0)
		if len(data) >= 44 {
			rain = float64(math.Float32frombits(binary.LittleEndian.Uint32(data[36:40])))
		}

		return &DecodedAWS{
			Timestamp:      time.Now().Unix(),
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
		}, nil
	}

	if len(data) >= 24 {
		timeInst := binary.LittleEndian.Uint32(data[2:6])
		dir := binary.LittleEndian.Uint16(data[6:8])
		rawSpeed := binary.LittleEndian.Uint16(data[8:10])
		rawDryTemp := binary.LittleEndian.Uint16(data[10:12])
		rawWetTemp := binary.LittleEndian.Uint16(data[12:14])
		rawHumidity := binary.LittleEndian.Uint16(data[14:16])
		rawSolar := binary.LittleEndian.Uint16(data[16:18])
		rawRain := binary.LittleEndian.Uint16(data[18:20])
		rawPressure := binary.LittleEndian.Uint32(data[20:24])

		dryTempSigned := int16(rawDryTemp)
		wetTempSigned := int16(rawWetTemp)

		speed := float64(rawSpeed) * 0.1
		dryTemp := float64(dryTempSigned) * 0.1
		wetTemp := float64(wetTempSigned) * 0.1
		humidity := float64(rawHumidity) * 0.1
		solar := float64(rawSolar) * 1.0
		rain := float64(rawRain) * 0.1
		pressure := float64(rawPressure) * 0.01

		return &DecodedAWS{
			Timestamp:      time.Now().Unix(),
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
		}, nil
	}

	return nil, fmt.Errorf("binary frame too short (%d bytes)", len(data))
}

func parseCSVFrame(parts []string) (*DecodedAWS, error) {
	// Skip header line if sent
	if strings.ToLower(parts[0]) == "time_inst" || strings.Contains(strings.ToLower(parts[0]), "time") {
		return nil, errors.New("header line skipped")
	}

	numCols := len(parts)

	// Format A: Standard aws_sample_input.txt (10 columns):
	// [0: Time_Inst, 1: Direction, 2: Speed, 3: Dry Bulb, 4: Wet Bulb, 5: RH, 6: Solar, 7: Rain, 8: P_IMU, 9: P_hPa]
	if numCols >= 8 {
		timeInst, _ := strconv.ParseUint(strings.TrimSpace(parts[0]), 10, 32)
		dir, _ := strconv.ParseFloat(strings.TrimSpace(parts[1]), 64)
		speed, _ := strconv.ParseFloat(strings.TrimSpace(parts[2]), 64)
		dryTemp, _ := strconv.ParseFloat(strings.TrimSpace(parts[3]), 64)
		wetTemp, _ := strconv.ParseFloat(strings.TrimSpace(parts[4]), 64)
		humidity, _ := strconv.ParseFloat(strings.TrimSpace(parts[5]), 64)
		solar, _ := strconv.ParseFloat(strings.TrimSpace(parts[6]), 64)
		rain, _ := strconv.ParseFloat(strings.TrimSpace(parts[7]), 64)
		
		pressure := 1013.25
		if numCols >= 10 {
			if p, err := strconv.ParseFloat(strings.TrimSpace(parts[9]), 64); err == nil {
				pressure = p
			}
		} else if numCols >= 9 {
			if p, err := strconv.ParseFloat(strings.TrimSpace(parts[8]), 64); err == nil {
				pressure = p
			}
		}

		return &DecodedAWS{
			Timestamp:      time.Now().Unix(),
			TimeInst:       uint32(timeInst),
			Direction:      uint16(dir),
			Speed:          speed,
			DryBulbTemp:    dryTemp,
			WetBulbTemp:    wetTemp,
			RelHumidity:    humidity,
			SolarRadiation: solar,
			Rainfall:       rain,
			PressureHpa:    pressure,
			PressureImu:    pressure,
		}, nil
	}

	// Format B: 3 or 4 parameter stream (Dry, Wet/Press, RH, [Press])
	dryTemp, _ := strconv.ParseFloat(strings.TrimSpace(parts[0]), 64)
	wetTemp, _ := strconv.ParseFloat(strings.TrimSpace(parts[1]), 64)
	humidity, _ := strconv.ParseFloat(strings.TrimSpace(parts[2]), 64)
	pressure := 1013.25
	if numCols >= 4 {
		if p, err := strconv.ParseFloat(strings.TrimSpace(parts[3]), 64); err == nil {
			pressure = p
		}
	}

	return &DecodedAWS{
		Timestamp:      time.Now().Unix(),
		TimeInst:       uint32(time.Now().Unix()),
		Direction:      180,
		Speed:          3.5,
		DryBulbTemp:    dryTemp,
		WetBulbTemp:    wetTemp,
		RelHumidity:    humidity,
		SolarRadiation: 450.0,
		Rainfall:       0.0,
		PressureHpa:    pressure,
		PressureImu:    pressure,
	}, nil
}
