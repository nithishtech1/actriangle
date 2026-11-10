# ClimaTwin: Project Spec v2.1 (Make-A-Thon Round 2 — Updated Hardware & Strategy)

*Updated 10 Nov 2026 (21:05 IST). Supersedes v2 hardware BOM (SHT31 $\to$ DHT11) and refines product positioning from competitive research.*

---

## 1. Snapshot

| Item | Value |
|---|---|
| **Event** | Make-A-Thon, Chennai Institute of Technology (CIT) |
| **Track** | Track 2 — Digital Twin |
| **Team TRIANGLE** | Nithish P (Lead Architect / UI), Nikil S (Software), Harish S (Hardware) |
| **Round 2 Deadline** | **11.11.2026** (Finals: 13.11.2026) |
| **Core Model** | First-order Newton pull-down $T_\text{room}(t) = T_\text{final} + (T_0 - T_\text{final})e^{-t/\tau}$ over initial 15 min |
| **Electrical Safety** | **100% low-voltage USB-powered**. Zero mains wiring. Energy/₹ figures are upper-bound runtime estimates, never measured kWh. |

---

## 2. Actual Hardware Bill of Materials (`₹1,281` Verified Invoice)

| # | Part (Per Invoice `INV2223-1599`) | Qty | Cost (₹) | Pinout & Role |
|---|---|---:|---:|---|
| 1 | **ESP32 WROOM NodeMCU (38-Pin)** | 1 | 475.00 | Microcontroller, USB UART @ 115200 baud |
| 2 | **DS18B20 Temperature Probes** | 2 | 266.00 | `P27` (`GPIO27`, shared 1-Wire + 1× `4.7 kΩ`): Supply air + Return grille |
| 3 | **DHT11 Sensor Module** *(replaces SHT31)* | 1 | 114.00 | `P26` (`GPIO26`, onboard pull-up): Mid-room Temp & RH |
| 4 | **4.7 kΩ Resistors** | 10 | 19.00 | `1× 4.7 kΩ` pull-up on `P27` (`Col 24` shared bus to `3V3`) |
| 5 | **Breadboard (GL12 840-pt)** + Jumpers + Type-C | 1 set | 407.08 | Assembly (`Cols 1–29` left half only; rails split at Col 30) |
**Total** | | | **₹1,281** | |

### Hardware Integration Rules (From Bench Diagnostics)
1. **DS18B20 `"sensor not detected"` Fixes on ESP32**:
   - **Unified Pin Plan (`1× 4.7 kΩ` resistor build)**: Share **both DS18B20 yellow leads on `P27` (`GPIO27`)** at `Col 24` with **one `4.7 kΩ` resistor** to `3V3`, and wire the **3-pin DHT11 to `P26` (`GPIO26`)**. Upload [`firmware/climatwin_esp32/climatwin_esp32.ino`](../firmware/climatwin_esp32/climatwin_esp32.ino).
   - **Breadboard Rail Check**: On 840-point GL12 breadboards, `+` and `-` side power rails split at column 30. Keep ALL wiring inside `Cols 1–29` (left half) and bridge left `Top` & `Bottom` rails.
   - **Arduino Core / Power**: Works cleanly on ESP32 Arduino Core (or `v2.0.17` / `OneWireNg` if `getDeviceCount()` misses). If brownout occurs on `3V3`, wire probe **VCC (Red) to `5V`** while keeping the `4.7 kΩ` pull-up to `3V3`.
   - **Stranded Wire Contact**: Push M-F jumper pins firmly into `Col 24`; the unified sketch auto-rescans probes every 5s (`# CHECK [X/2 probes]`).
2. **DHT11 Precision Watch-Out**:
   - Standard DHT11 outputs `1°C` integer steps (`29.0, 28.0`) or `0.1°C` depending on chip revision. Check 5 Serial Monitor lines before starting the AC test.
   - If DHT11 only gives `1°C` integer steps and DS18B20 probes work smoothly at `0.0625°C`, keep `DS18B20` probes calibrated and report DHT11 resolution honestly.
3. **Zero Fabricated Data Policy**:
   - **NEVER** generate random or synthetic numbers inside live mode or firmware to hide disconnected sensors. Use **Replay Mode** (`data/replay/FAKE_*.csv`) as the honest fallback if hardware fails.

---

## 3. Updated Competitive Positioning & Core Differentiator

From competitive market research (Testo, measureQuick, SmartAC, Sensibo, Cielo Breez):
- **What already exists**: Pro tools (Testo/measureQuick) already generate PDF before/after reports for HVAC contractors (₹50k–₹1L+ manifold/clamp kits). Consumer smart remotes (Sensibo/Cielo) already have usage-hour filter timers.
- **ClimaTwin's Defensible White Space**:
  > *"ClimaTwin is the first ₹1,281, zero-mains resident-side Digital Twin that verifies **whether a simple homeowner action (like cleaning a filter) actually restored room cooling**, separates **cold vent air from slow room cooling**, and exports a condition-adjusted **Proof-of-Service / Pre-Visit Technician Brief**."*

### Key Additions (v2.1)
1. **Guided Experiment Workflow** *(Preferred over passive monitoring)*:
   - `Symptom / Lag Detected` $\to$ `Confirmed Action (e.g., Filter Cleaned)` $\to$ `Before vs. After Twin Comparison` $\to$ `Outcome`:
     - **Improvement observed**: Verified speedup certificate (`Cooling X% Faster`).
     - **No clear improvement / Inconclusive**: Auto-generates a concise **Pre-Visit Technician Evidence Brief** (settings, checks already done, vent $\Delta T$ vs. room $\tau$ split) so the homeowner avoids unnecessary gas-refill upsells.
2. **"Cold Outlet / Slow Room" View (Pain Point D)**:
   - Explicitly separates **Supply Vent Drop (`Return − Supply °C`)** from **Room Cooling Speed ($\tau$)** so homeowners aren't misled by cold air coming out of a restricted vent while the room stays warm.
3. **CSV Data Contract Unchanged**:
   - Serial stream remains strictly 5 columns: `ms,probe0_C,probe1_C,room_C,room_RH`.
   - Logged CSV remains 8 columns: `ts_iso,ms,supply_C,return_C,room_C,room_RH,outdoor_C,phase`.
