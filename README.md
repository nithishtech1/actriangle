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

For the completed service-verification workflow, start with [SERVICE_DEMO.md](docs/SERVICE_DEMO.md).
The dashboard and PDF share one verdict, with comparable-condition checks and optional weather normalization.

The Person 3 software is implemented. Start with [the quick-start guide](docs/QUICKSTART.md).
See [task-by-task status](docs/PERSON3_STATUS.md) for what is software-tested and what still needs the ESP32.
There are **no real hardware results yet**. The included `FAKE_` recordings are software fixtures.

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
- If reconnects or restarts occur within the same minute, the logger adds `_01`, `_02`, etc. rather than overwrite a run. The CSV columns are unchanged.
- The ESP32 prints only `ms,probe0_C,probe1_C,room_C,room_RH`; the logger adds the rest and applies the probe mapping and offsets from `config.py`.
- Offset convention: `corrected = raw + offset`.
- **Time axis:** use `ms` (or `ts_iso`), never the row number. Rows are about 5.8 s apart, not exactly 5 s, because the DS18B20 conversion blocks for roughly 0.75 s.
- If the ESP32 reboots mid-run, `ms` restarts from 0; start a new file instead of continuing.
- The logger performs that split automatically, and also starts a new file after a serial disconnection. Each row is flushed immediately. `.meta.json` and `.weather.jsonl` sidecars record settings and weather provenance without adding CSV columns.
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

## Software commands

Run from this repository's root after installing dependencies:

```sh
python -m twin.gen_synthetic                 # included files already exist; use --overwrite only to regenerate
python -m twin.fit_tau data/replay
python -m twin.analyze data/replay
python -m streamlit run app/dashboard.py
python -m logger.log_serial --port COM5 --phase clean1 --duration-min 30 --setpoint-c 18
python -m report.make_report data/replay --output reports/FAKE_report.pdf
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

The dashboard offers live CSV monitoring, 10x replay, four sensor charts, a health gauge,
the clean twin overlay, a persistent alert banner, opt-in live Telegram delivery and PDF download.
Replay never sends Telegram messages. A FAKE banner and report watermark follow `FAKE_` source files.

## Model boundaries

The offline fit uses a 3-sample median and the first 15 minutes of detected room cooling.
Fits with R2 < 0.90, large sample gaps, little cooling, or poorly constrained parameters are rejected.
Live/replay fits use increasing windows at recording minutes 8 through 15, once per minute.
Only fresh, valid fits count toward the three-fit alert; rapid UI refreshes cannot create extra confirmations.
After the initial window, the result is held and clearly labelled. This is an initial pull-down monitor:
it does **not** detect a blockage newly introduced during later steady-state operation. Start a new,
comparable cooling run for each phase. Do not promise an immediate fault alert in a five-minute live demo.

The supplied 8/14/8-minute fixtures meet the 5% recovery target. Independent noise can cause larger
errors, especially when estimating a 14-minute time constant from only 15 minutes. A high R2 alone
does not establish tau accuracy. Reported fit uncertainty is diagnostic, not a validated confidence interval.

Outdoor normalization requires repeated **same-condition before-service** runs at different outdoor
temperatures. Never regress across clean1/blocked/clean2 as though their difference came from weather.
The report prints `unavailable` without that evidence and refuses extrapolation. The optional
Isolation Forest is a separate unusual-reading flag, trained on clean1 only; it never changes the service verdict.

Cost is estimated for a common start and target: `minutes_saved / 60 * nameplate_kW * tariff_Rs_per_kWh`.
No kW, tariff or AC setpoint is guessed. The included demonstration report uses explicitly hypothetical
1.5 kW and Rs 8/kWh; do not reuse those numbers as measurements.

## API references

- [SciPy curve_fit](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.curve_fit.html)
- [Open-Meteo current weather](https://open-meteo.com/en/docs) - temperature_2m, refreshed every 10 minutes; credit Open-Meteo when presenting its data.
- [Streamlit fragments](https://docs.streamlit.io/develop/api-reference/execution-flow/st.fragment) - independent dashboard refresh.
- [Telegram sendMessage](https://core.telegram.org/bots/api#sendmessage) - credentials remain in `.env`.
