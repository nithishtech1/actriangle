# ClimaTwin

Low-cost twin of how fast a home split AC cools a room. An ESP32 with two DS18B20 probes and an SHT31 logs temperature and humidity; software fits a pull-down curve (time constant tau), flags degradation such as a clogged filter, and produces a before/after service report.

Team TRIANGLE, Make-A-Thon (CIT), Track 2 Digital Twin.

**Safety:** nothing in this project connects to mains. All hardware is low-voltage and USB-powered. Energy and rupee figures are **estimates** (runtime x nameplate kW x tariff), never measurements.

## Folders

| Folder | Contents |
|---|---|
| `firmware/` | ESP32 Arduino sketch |
| `logger/` | Serial logger (`log_serial.py`) |
| `twin/` | Synthetic data generator, tau fit, health score |
| `app/` | Streamlit dashboard |
| `report/` | PDF report generator |
| `data/raw/` | Real runs only |
| `data/replay/` | Replay files. Fake files start with `FAKE_` |
| `tools/` | `check_csv.py`, `telegram_check.py` |
| `config.py` | All shared settings (one place) |

## Setup

```
python -m venv .venv
.venv\Scripts\activate          # Windows   (Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env          # then fill in the Telegram values (never commit .env)
```

## Data contract (do not change without telling all three)

One CSV per run, rows about every 5-6 seconds, header exactly:

`ts_iso,ms,supply_C,return_C,room_C,room_RH,outdoor_C,phase`

| Column | Meaning |
|---|---|
| `ts_iso` | Laptop time, ISO 8601 with seconds, e.g. `2026-11-07T14:03:05` |
| `ms` | ESP32 `millis()` at the reading |
| `supply_C` | Supply-air probe, offset-corrected |
| `return_C` | Return-air probe, offset-corrected |
| `room_C`, `room_RH` | SHT31 room temperature and humidity, offset-corrected |
| `outdoor_C` | Outdoor temperature from the weather API (or the typed fallback) |
| `phase` | `clean1`, `blocked`, `clean2`, or `reset` |

- `reset` = the warm-back period between phases, logged but not used for the fit.
- Filename: `run_<phase>_<YYYYMMDD_HHMM>.csv`, e.g. `run_clean1_20261107_1430.csv`.
- The ESP32 prints only `ms,probe0_C,probe1_C,room_C,room_RH`; the logger adds the rest and applies the probe mapping and offsets from `config.py`.
- Offset convention: `corrected = raw + offset`.
- **Time axis:** use `ms` (or `ts_iso`), never the row number. Rows are about 5.8 s apart, not exactly 5 s, because the DS18B20 conversion blocks for roughly 0.75 s.
- If the ESP32 reboots mid-run, `ms` restarts from 0; start a new file instead of continuing.
- `data/raw/bench_sample.csv` (task 43) is the raw 5-column ESP32 output (`ms,probe0_C,probe1_C,room_C,room_RH`); the checker accepts that for files named `bench_*.csv`.
- Check files with: `python tools/check_csv.py data/raw` (a folder) or one or more file names. The script expands wildcards itself, so this also works in PowerShell and cmd.

## Rules

1. Fake data lives in `data/replay/` and its filename starts with `FAKE_`. It is only for testing software and is never shown to judges as a result.
2. Real results come only from `data/raw/`.
3. No secrets in git. Token and chat ID go in `.env`.
4. After the freeze, no new features.

## Status checklist

- [ ] Bench bring-up done (real CSV exists)
- [ ] Three-phase test done
- [ ] Signal that separates blocked from clean decided: ______
- [ ] Dashboard live
- [ ] Report generated from real data
- [ ] Backup video recorded
- [ ] Freeze

## Result (fill after the test, task 86)

- Signal that separated blocked from clean: 
- By how much: 
- Repeatability (clean1 vs clean2): 
