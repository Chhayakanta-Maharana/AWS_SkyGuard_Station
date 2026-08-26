#ifndef SKYGUARD_EDGE_AI_H
#define SKYGUARD_EDGE_AI_H

#include <math.h>
#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

// Sensor Reading Structure for ESP32 Edge Ingestion
typedef struct {
    uint32_t timestamp;
    float dry_temp;       // °C
    float wet_temp;       // °C
    float humidity;       // %
    float pressure_hpa;   // hPa
    float wind_speed;     // m/s
    uint16_t wind_dir;    // degrees (0-360)
    float solar_rad;      // W/m²
    float rainfall;       // mm
} EdgeSensorReading;

// Anomaly & Edge Inference Result
typedef struct {
    bool is_anomaly;
    uint8_t severity;      // 0: Nominal, 1: Low, 2: Medium, 3: High/Critical
    float confidence;      // 0.0 to 100.0%
    char anomaly_type[24]; // "spike", "freeze", "bounds", "psychrometric", "nominal"
    char xai_reason[128];  // Explainable AI text reasoning for edge logging
    float imputed_temp;    // Self-healed estimated temperature
    float imputed_hum;     // Self-healed estimated humidity
    float imputed_press;   // Self-healed estimated pressure
    float shap_temp_pct;   // SHAP feature contribution % (Temp)
    float shap_hum_pct;    // SHAP feature contribution % (Humidity)
    float shap_press_pct;  // SHAP feature contribution % (Pressure)
} EdgeAnomalyResult;

// Historical Ring Buffer for Microcontrollers (Low RAM footprint < 1KB)
#define EDGE_WINDOW_SIZE 16

typedef struct {
    EdgeSensorReading buffer[EDGE_WINDOW_SIZE];
    uint8_t count;
    uint8_t head;
    // Running statistics
    float sum_temp, sum_hum, sum_press;
    uint8_t freeze_counter;
} EdgeDetectorState;

// Initialize Edge AI Engine
void skyguard_edge_init(EdgeDetectorState *state);

// Analyze single sensor sample on ESP32 in < 15 microseconds
EdgeAnomalyResult skyguard_edge_analyze(EdgeDetectorState *state, const EdgeSensorReading *reading);

#ifdef __cplusplus
}
#endif

#endif // SKYGUARD_EDGE_AI_H
