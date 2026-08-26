package detector

import (
	"fmt"
	"math"
	"sync"
)

type AnomalyResult struct {
	IsAnomaly       bool               `json:"is_anomaly"`
	Severity        string             `json:"severity"`         // "none", "low", "medium", "high"
	Confidence      float64            `json:"confidence"`       // 0 to 100
	AnomalyType     string             `json:"anomaly_type"`     // "spike", "freeze", "out_of_bounds", "multivariate", "none"
	XAIExplanation  string             `json:"xai_explanation"`
	ImputedValues   map[string]float64 `json:"imputed_values"`
	DegradationRisk float64            `json:"degradation_risk"` // 0 to 100
}

type RingBuffer struct {
	data  []map[string]float64
	size  int
	start int
	end   int
	count int
}

func NewRingBuffer(size int) *RingBuffer {
	return &RingBuffer{
		data: make([]map[string]float64, size),
		size: size,
	}
}

func (r *RingBuffer) Push(val map[string]float64) {
	r.data[r.end] = val
	r.end = (r.end + 1) % r.size
	if r.count < r.size {
		r.count++
	} else {
		r.start = (r.start + 1) % r.size
	}
}

func (r *RingBuffer) GetAll() []map[string]float64 {
	res := make([]map[string]float64, r.count)
	for i := 0; i < r.count; i++ {
		res[i] = r.data[(r.start+i)%r.size]
	}
	return res
}

type Detector struct {
	mu           sync.Mutex
	windowSize   int
	history      *RingBuffer
	cleanHistory *RingBuffer
	// Config thresholds
	tempMin, tempMax         float64
	humMin, humMax           float64
	pressMin, pressMax       float64
	maxTempChangePerSec      float64
	maxHumChangePerSec       float64
	maxPressChangePerSec     float64
	freezeCheckCount         int
	consecutiveAnomalyCount map[string]int
}

func NewDetector(windowSize int) *Detector {
	return &Detector{
		windowSize:              windowSize,
		history:                 NewRingBuffer(windowSize),
		cleanHistory:            NewRingBuffer(windowSize),
		tempMin:                 -40.0,
		tempMax:                 55.0,
		humMin:                  0.0,
		humMax:                  100.0,
		pressMin:                900.0,
		pressMax:                1080.0,
		maxTempChangePerSec:     5.0,
		maxHumChangePerSec:      15.0,
		maxPressChangePerSec:    10.0,
		freezeCheckCount:        10,
		consecutiveAnomalyCount: make(map[string]int),
	}
}

func (d *Detector) Analyze(temp, humidity, pressure float64) AnomalyResult {
	d.mu.Lock()
	defer d.mu.Unlock()

	current := map[string]float64{
		"temp_dry":     temp,
		"humidity":     humidity,
		"pressure_hpa": pressure,
	}

	result := AnomalyResult{
		IsAnomaly:      false,
		Severity:       "none",
		Confidence:     0.0,
		AnomalyType:    "none",
		XAIExplanation: "All parameters are behaving within normal limits.",
		ImputedValues: map[string]float64{
			"temp_dry":     temp,
			"humidity":     humidity,
			"pressure_hpa": pressure,
		},
	}

	historyVals := d.history.GetAll()
	cleanVals := d.cleanHistory.GetAll()

	if len(historyVals) < 5 {
		d.history.Push(current)
		d.cleanHistory.Push(current)
		return result
	}

	last := historyVals[len(historyVals)-1]

	// Physical boundary validation
	if temp < d.tempMin || temp > d.tempMax {
		d.flagAnomaly(&result, "out_of_bounds", "high", 99.0,
			fmt.Sprintf("Temperature value %.1f°C is out of physical limits (%.1f to %.1f°C).", temp, d.tempMin, d.tempMax))
		result.ImputedValues["temp_dry"] = d.getImputedValue("temp_dry", cleanVals)
	}
	if humidity < d.humMin || humidity > d.humMax {
		d.flagAnomaly(&result, "out_of_bounds", "high", 99.0,
			fmt.Sprintf("Humidity value %.1f%% is out of physical limits (%.1f to %.1f%%).", humidity, d.humMin, d.humMax))
		result.ImputedValues["humidity"] = d.getImputedValue("humidity", cleanVals)
	}
	if pressure < d.pressMin || pressure > d.pressMax {
		d.flagAnomaly(&result, "out_of_bounds", "high", 99.0,
			fmt.Sprintf("Atmospheric Pressure %.1f hPa is out of physical limits (%.1f to %.1f hPa).", pressure, d.pressMin, d.pressMax))
		result.ImputedValues["pressure_hpa"] = d.getImputedValue("pressure_hpa", cleanVals)
	}

	// Temporal rate-of-change gradient evaluation
	if !result.IsAnomaly {
		dTemp := math.Abs(temp - last["temp_dry"])
		dHum := math.Abs(humidity - last["humidity"])
		dPress := math.Abs(pressure - last["pressure_hpa"])

		if dTemp > d.maxTempChangePerSec {
			d.flagAnomaly(&result, "spike", "high", 95.0,
				fmt.Sprintf("Sudden temperature change (%.1f°C/sec) exceeds physical limit (%.1f°C/sec).", dTemp, d.maxTempChangePerSec))
			result.ImputedValues["temp_dry"] = d.getImputedValue("temp_dry", cleanVals)
		} else if dHum > d.maxHumChangePerSec {
			d.flagAnomaly(&result, "spike", "medium", 90.0,
				fmt.Sprintf("Sudden humidity change (%.1f%%/sec) exceeds physical limit (%.1f%%/sec).", dHum, d.maxHumChangePerSec))
			result.ImputedValues["humidity"] = d.getImputedValue("humidity", cleanVals)
		} else if dPress > d.maxPressChangePerSec {
			d.flagAnomaly(&result, "spike", "high", 95.0,
				fmt.Sprintf("Sudden pressure fluctuation (%.1f hPa/sec) exceeds physical limit (%.1f hPa/sec).", dPress, d.maxPressChangePerSec))
			result.ImputedValues["pressure_hpa"] = d.getImputedValue("pressure_hpa", cleanVals)
		}
	}

	// Sensor lockup and frozen value detection
	if !result.IsAnomaly && len(historyVals) >= d.freezeCheckCount {
		frozenTemp, frozenHum, frozenPress := true, true, true
		startIdx := len(historyVals) - d.freezeCheckCount

		for i := startIdx + 1; i < len(historyVals); i++ {
			if historyVals[i]["temp_dry"] != historyVals[startIdx]["temp_dry"] {
				frozenTemp = false
			}
			if historyVals[i]["humidity"] != historyVals[startIdx]["humidity"] {
				frozenHum = false
			}
			if historyVals[i]["pressure_hpa"] != historyVals[startIdx]["pressure_hpa"] {
				frozenPress = false
			}
		}

		if temp != last["temp_dry"] {
			frozenTemp = false
		}
		if humidity != last["humidity"] {
			frozenHum = false
		}
		if pressure != last["pressure_hpa"] {
			frozenPress = false
		}

		if frozenTemp {
			d.flagAnomaly(&result, "freeze", "medium", 85.0, "Temperature sensor is reporting constant frozen values.")
			result.ImputedValues["temp_dry"] = d.getImputedValue("temp_dry", cleanVals)
		} else if frozenHum {
			d.flagAnomaly(&result, "freeze", "medium", 85.0, "Humidity sensor is reporting constant frozen values.")
			result.ImputedValues["humidity"] = d.getImputedValue("humidity", cleanVals)
		} else if frozenPress {
			d.flagAnomaly(&result, "freeze", "high", 90.0, "Pressure sensor is reporting constant frozen values.")
			result.ImputedValues["pressure_hpa"] = d.getImputedValue("pressure_hpa", cleanVals)
		}
	}

	// Thermodynamic psychrometric equilibrium & multivariate covariance analysis
	if !result.IsAnomaly {
		esDry := 6.112 * math.Exp((17.67*temp)/(temp+243.5))
		wetTemp := temp - ((100.0 - humidity) / 5.0)
		esWet := 6.112 * math.Exp((17.67*wetTemp)/(wetTemp+243.5))
		actVap := esWet - pressure*0.00066*(1.0+0.00115*wetTemp)*(temp-wetTemp)
		theoRH := math.Max(0.0, math.Min(100.0, (actVap/esDry)*100.0))

		if math.Abs(humidity-theoRH) > 35.0 {
			d.flagAnomaly(&result, "multivariate", "high", 91.5,
				fmt.Sprintf("Magnus-Tetens Psychrometric Violation: Reported RH (%.1f%%) diverges from theoretical thermodynamic equilibrium (%.1f%%) by %.1f%%.", humidity, theoRH, math.Abs(humidity-theoRH)))
			result.ImputedValues["humidity"] = d.getImputedValue("humidity", cleanVals)
		}

		if !result.IsAnomaly {
			tMean, tStd := getStats("temp_dry", cleanVals)
			hMean, hStd := getStats("humidity", cleanVals)
			pMean, pStd := getStats("pressure_hpa", cleanVals)

			zT := 0.0
			if tStd > 0.01 {
				zT = math.Abs(temp-tMean) / tStd
			}
			zH := 0.0
			if hStd > 0.01 {
				zH = math.Abs(humidity-hMean) / hStd
			}
			zP := 0.0
			if pStd > 0.01 {
				zP = math.Abs(pressure-pMean) / pStd
			}

			distSq := (zT * zT) + (zH * zH) + (zP * zP)
			if distSq > 9.0 {
				maxZ := math.Max(zT, math.Max(zH, zP))
				explanation := ""

				if maxZ == zT {
					explanation = fmt.Sprintf("Temperature (Z-Score=%.2f) deviates significantly from the current local pressure & humidity trend.", zT)
					result.ImputedValues["temp_dry"] = d.getImputedValue("temp_dry", cleanVals)
				} else if maxZ == zH {
					explanation = fmt.Sprintf("Relative Humidity (Z-Score=%.2f) shows high multivariate inconsistency with temperature variations.", zH)
					result.ImputedValues["humidity"] = d.getImputedValue("humidity", cleanVals)
				} else {
					explanation = fmt.Sprintf("Atmospheric Pressure (Z-Score=%.2f) has diverged from standard physical meteorological correlations.", zP)
					result.ImputedValues["pressure_hpa"] = d.getImputedValue("pressure_hpa", cleanVals)
				}

				d.flagAnomaly(&result, "multivariate", "medium", 50.0+(maxZ*10.0), explanation)
				if result.Confidence > 100 {
					result.Confidence = 99.0
				}
			}
		}
	}

	// 5. Sensor Degradation
	if result.IsAnomaly {
		if result.AnomalyType == "out_of_bounds" || result.AnomalyType == "freeze" {
			d.consecutiveAnomalyCount[result.AnomalyType]++
		}
	} else {
		for k := range d.consecutiveAnomalyCount {
			d.consecutiveAnomalyCount[k] = 0
		}
	}

	maxConsecutive := 0
	for _, cnt := range d.consecutiveAnomalyCount {
		if cnt > maxConsecutive {
			maxConsecutive = cnt
		}
	}
	result.DegradationRisk = math.Min(100.0, float64(maxConsecutive)*10.0)

	// Update clean history
	d.history.Push(current)
	if !result.IsAnomaly {
		d.cleanHistory.Push(current)
	} else {
		cleanImputed := map[string]float64{
			"temp_dry":     result.ImputedValues["temp_dry"],
			"humidity":     result.ImputedValues["humidity"],
			"pressure_hpa": result.ImputedValues["pressure_hpa"],
		}
		d.cleanHistory.Push(cleanImputed)
	}

	return result
}

func (d *Detector) flagAnomaly(res *AnomalyResult, aType, severity string, confidence float64, explanation string) {
	res.IsAnomaly = true
	res.AnomalyType = aType
	res.Severity = severity
	res.Confidence = confidence
	res.XAIExplanation = explanation
}

func (d *Detector) getImputedValue(param string, cleanVals []map[string]float64) float64 {
	if len(cleanVals) == 0 {
		return 0
	}
	sum := 0.0
	weightSum := 0.0
	for i := 0; i < len(cleanVals); i++ {
		weight := float64(i + 1)
		sum += cleanVals[i][param] * weight
		weightSum += weight
	}
	return sum / weightSum
}

func getStats(param string, vals []map[string]float64) (mean, std float64) {
	if len(vals) == 0 {
		return 0, 0
	}
	sum := 0.0
	for _, v := range vals {
		sum += v[param]
	}
	mean = sum / float64(len(vals))

	variance := 0.0
	for _, v := range vals {
		diff := v[param] - mean
		variance += diff * diff
	}
	variance = variance / float64(len(vals))
	std = math.Sqrt(variance)
	return mean, std
}
