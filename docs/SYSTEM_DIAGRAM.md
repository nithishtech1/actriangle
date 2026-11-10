# ClimaTwin: System Architecture Diagram (Task 101)

**Team TRIANGLE** | CIT Make-A-Thon (Track 2: Digital Twin)  
**Authors**: Nithish P (Lead Architect), Nikil S (Software Lead), Harish S (Hardware Lead)  
**Document Version**: 2.0 (Prototype Specification)  

---

## 1. End-to-End System Architecture

```mermaid
flowchart TD
    subgraph S1["1. PHYSICAL HARDWARE & ENVIRONMENT"]
        AC["Split AC Evaporator & Room Airflow"]
        P1["DS18B20 #1: Supply Vent Air<br/>(5-8 cm in free airflow)"]
        P2["DS18B20 #2: Return Grille Air<br/>(Intake airflow)"]
        SHT["DHT11: Room Temp & Humidity<br/>(1.5 m high, mid-room wire lead)"]
        ESP["ESP32 WROOM NodeMCU 38-Pin<br/>(P27 / GPIO27: 1-Wire, P26 / GPIO26: DHT11)"]
        METEO["Open-Meteo REST API<br/>(10-min cache, typed fallback)"]

        AC --> P1
        AC --> P2
        AC --> SHT
        P1 -->|"1-Wire Bus (4.7 kΩ pull-up on P27)"| ESP
        P2 -->|"1-Wire Bus (shared P27 pin)"| ESP
        SHT -->|"Digital Single-Wire (P26 / GPIO26)"| ESP
    end

    subgraph S2["2. INGESTION & DATA STORAGE LAYER"]
        SER["USB Serial Stream (115200 baud)<br/>Format: ms, probe0, probe1, room_C, room_RH"]
        LOGGER["Python Serial Logger (logger/log_serial.py)<br/>Offset Correction, Monotonic Guard, Per-Row Flush"]
        CSV["CSV Storage (data/raw / data/replay)<br/>8 Columns: ts_iso, ms, supply, return, room, RH, outdoor, phase"]
        META["Sidecar Metadata (*.meta.json)<br/>AC Setpoint, Offsets, Probe Roles, Unit ID"]

        ESP -->|"USB Data Cable"| SER
        SER --> LOGGER
        METEO -->|"HTTP GET"| LOGGER
        LOGGER --> CSV
        LOGGER --> META
    end

    subgraph S3["3. DIGITAL TWIN CORE & ANALYTICS (twin/)"]
        ONSET["Cooling Onset Detection<br/>(Piecewise linear change-point search)"]
        SMOOTH["3-Sample Median Filter<br/>(Transient spike suppression)"]
        FIT["Newton Cooling Curve Fitting (fit_tau.py)<br/>T(t) = T_final + (T0 - T_final)·exp(-t/τ)<br/>SciPy curve_fit over first 15 mins"]
        HEALTH["Health Score Index (health.py)<br/>Health = min(100, 100 · τ_baseline / τ_now)"]
        NORM["Weather Normalization (normalization.py)<br/>Counterfactual Regression: τ = m·T_outdoor + c"]
        ANOMALY["Secondary Anomaly Detection (anomaly.py)<br/>Isolation Forest (clean1 baseline only)"]

        CSV --> ONSET
        CSV --> SMOOTH
        SMOOTH --> FIT
        ONSET --> FIT
        FIT --> HEALTH
        FIT --> NORM
        CSV --> ANOMALY
    end

    subgraph S4["4. DASHBOARD & PROOF OF SERVICE"]
        DASH["Streamlit Dashboard (app/dashboard.py)<br/>Live File Watcher + 10x Accelerated Replay"]
        CHARTS["4 Telemetry Charts<br/>Supply, Return, Room Temp, Humidity"]
        OVERLAY["Digital Twin Live Overlay Plot<br/>Clean Twin Reference Curve vs. Live Response"]
        GAUGE["Health Progress Gauge & Status Banner<br/>(3-consecutive-fit degradation alarm)"]
        TG["Telegram Alerts (app/notifications.py)<br/>Bot notification on sustained degradation"]
        PDF["Proof-of-Service Report (report/make_report.py)<br/>2-Page PDF: Before vs. After Service<br/>Normalized Δτ% & Estimated energy impact"]

        CSV --> CHARTS
        DASH --> CHARTS
        DASH --> OVERLAY
        DASH --> GAUGE
        FIT --> OVERLAY
        HEALTH --> GAUGE
        GAUGE -->|"Alert Trigger"| TG
        NORM --> PDF
        HEALTH --> PDF
        DASH -->|"Generate Report"| PDF
    end
```

---

## 2. Hardware Wiring & Pin Mapping Reference

| Component | Interface | ESP32 Pin | Wiring Specifications | Operating Notes |
|---|---|---|---|---|
| **DS18B20 #1 (Supply Probe)** | 1-Wire | `P27` (`GPIO27`) | $4.7\text{ k}\Omega$ pull-up to $3\text{V}3$, GND to GND | Positioned 5–8 cm in discharge airflow; shares `Col 24` bus on breadboard. |
| **DS18B20 #2 (Return Probe)** | 1-Wire | `P27` (`GPIO27`) | Shared 1-Wire bus, same $4.7\text{ k}\Omega$ pull-up | Mounted on intake grille; cold-bottle pinch test confirms probe index. |
| **DHT11 (Room Temp & RH)** | Digital 1-Wire | `DATA: P26` (`GPIO26`) | $3\text{V}3$ VCC, GND to GND (onboard pull-up) | Placed mid-room at 1.5 m height away from direct AC draft and ESP32 heat. |
| **USB Serial Interface** | UART | Micro-USB | Baud rate: $115200$ | Continuous raw 5-column transmission every $\sim 5.8\text{ s}$ (`delay(5000)` + DS18B20 conversion). |

---

## 3. Data Contract Pipeline

```
[ESP32 Firmware]
  │
  ▼ Raw Serial Line (ASCII)
  "ms,probe0_C,probe1_C,room_C,room_RH\r\n"
  │
[logger/log_serial.py]
  ├── Corrects sensor offsets: T_corrected = T_raw + offset
  ├── Assigns probe roles (probe0 = supply/return, probe1 = return/supply)
  ├── Queries Open-Meteo REST API for outdoor temperature (10-minute cache)
  ├── Detects microcontroller reboots / millis wrap (ms < previous_ms)
  └── Immediately flushes row to disk
  │
  ▼ Repository CSV Standard (data/raw/run_<phase>_<timestamp>.csv)
  Columns: [ts_iso, ms, supply_C, return_C, room_C, room_RH, outdoor_C, phase]
  Sidecar: run_<phase>_<timestamp>.meta.json (Setpoint, sensor offsets, fan setting, unit ID)
```

---

## 4. Digital Twin Mathematical Model Summary

1. **Newton Cooling Formulation**:
   $$T_\text{room}(t) = T_\text{final} + (T_0 - T_\text{final}) \cdot e^{-t/\tau}$$
   - $t$: Elapsed time in minutes since detected cooling onset.
   - $T_0$: Fitted room temperature at cooling onset.
   - $T_\text{final}$: Asymptotic steady-state room temperature.
   - $\tau$ (Tau): Thermal pull-down time constant (Minutes). Larger $\tau =$ slower cooling $=$ degraded performance.

2. **Cooling Health Score**:
   $$\text{Health} = \min\left(100.0, \; 100 \times \frac{\tau_\text{baseline}}{\tau_\text{now}}\right)$$
   - $\text{Health} = 100$: Identical or faster cooling compared to healthy baseline.
   - $\text{Health} < 80$: Flags cooling degradation. Alert fires after 3 consecutive 60-second fits below threshold.

3. **Weather-Normalized Service Verification**:
   - Pre-service regression: $\tau_\text{expected} = m \cdot T_\text{outdoor} + c$
   - Performance Improvement:
     $$\Delta \tau_\text{normalized} = \frac{\tau_\text{expected} - \tau_\text{actual}}{\tau_\text{expected}} \times 100\%$$
