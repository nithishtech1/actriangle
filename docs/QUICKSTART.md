# Person 3: start ClimaTwin

## 1. Run the software demonstration now

Open a terminal in the project folder. Use Python 3.10 or newer (3.12 was tested).
On Windows, use these commands; activation is optional because the Python path is explicit:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m twin.fit_tau data/replay
.\.venv\Scripts\python.exe -m streamlit run app/dashboard.py
```

If `python` opens the Microsoft Store, install Python from python.org or use `py -3` for the first command.
On Linux/macOS, use `.venv/bin/python` instead of `.venv\Scripts\python.exe`.
The three FAKE CSVs are included. Regenerate only when needed:

```powershell
.\.venv\Scripts\python.exe -m twin.gen_synthetic --overwrite
```

Open http://localhost:8501. Leave **Replay recordings** enabled. Choose the blocked recording
and the clean1 baseline. Check **Play replay** at **10x**, or move **Seek (minutes)** to 15 to inspect
the result immediately. Health should be about 57/100 and the alert banner should appear.
Switch to clean2 to see recovery. Replay never sends a real Telegram message.

Use **Generate report**, then **Download PDF**. Unknown kW/tariff leaves cost uncalculated.
For a demonstration only, enter 1.5 kW and Rs 8/kWh; those are hypothetical, not your AC's settings.

## 2. Collect the first ESP32 recording

Ask the hardware teammate to confirm:

- Actual COM port, 115200 baud, and five-column output: `ms,probe0_C,probe1_C,room_C,room_RH`.
- Which probe is supply/return, and side-by-side sensor offsets.
- Actual room latitude/longitude and a fallback outdoor temperature if internet is unavailable.
- AC setpoint, fan setting, nameplate electrical input kW, and household tariff.

Enter these in `config.py`. Nameplate kW means **electrical input power**, not cooling capacity in kW or tons.
Close Arduino Serial Monitor before opening the logger; only one program can own the port.

```powershell
# Example only: replace COM5 with the connected port.
.\.venv\Scripts\python.exe -m logger.log_serial --port COM5 --phase clean1 --duration-min 5 --setpoint-c 18
.\.venv\Scripts\python.exe tools/check_csv.py data/raw
```

Expect about 50-60 readings in five minutes (firmware spacing is usually about 5.8 seconds).
This short capture checks logging only; the final tau fit needs at least 15 minutes of uninterrupted cooling.
The logger rejects missing sensors, NaN/inf, invalid humidity and out-of-range temperatures; serial startup
headers are ignored. It retries a disconnected port every two seconds. A reboot or reconnect creates a new file.
If a run is interrupted inside the fit window, collect another continuous run instead of merging files.

For offline weather, add `--offline --outdoor-c 33` **only if 33 C is your actual typed estimate**.
Without a valid weather source or fallback, outdoor values are blank; room-temperature fitting still works.
Do not rename synthetic CSVs to remove `FAKE_`.

## 3. Complete the three phases with the team

Capture each phase separately after returning the room to a comparable start temperature:

```powershell
.\.venv\Scripts\python.exe -m logger.log_serial --port COM5 --phase clean1 --duration-min 30 --setpoint-c 18
.\.venv\Scripts\python.exe -m logger.log_serial --port COM5 --phase reset --duration-min 25
.\.venv\Scripts\python.exe -m logger.log_serial --port COM5 --phase blocked --duration-min 30 --setpoint-c 18
.\.venv\Scripts\python.exe -m logger.log_serial --port COM5 --phase reset --duration-min 25
.\.venv\Scripts\python.exe -m logger.log_serial --port COM5 --phase clean2 --duration-min 30 --setpoint-c 18
```

Follow the team's approved hardware procedure; the software does not operate the AC. Keep settings and
room conditions comparable. In the dashboard, turn replay off, choose `data/raw`, select the completed
clean1 baseline, and enable **Follow newest CSV**. Warm-back/reset data is never scored.

Select the exact three cooling CSVs for analysis. Do not pass a folder containing bench/reset/repeated runs:

```powershell
.\.venv\Scripts\python.exe -m twin.analyze data/raw/run_clean1_YYYYMMDD_HHMM.csv data/raw/run_blocked_YYYYMMDD_HHMM.csv data/raw/run_clean2_YYYYMMDD_HHMM.csv --output reports/real_analysis.json
.\.venv\Scripts\python.exe -m report.make_report data/raw/run_clean1_YYYYMMDD_HHMM.csv data/raw/run_blocked_YYYYMMDD_HHMM.csv data/raw/run_clean2_YYYYMMDD_HHMM.csv --output reports/real_report.pdf
```

The placeholders above must be replaced by your actual filenames. The dashboard's three report selectors
are an easier alternative. Save CSVs together with their `.meta.json` and `.weather.jsonl` sidecars.
Inspect tau, clean-run repeatability, return-minus-supply and humidity-drop rate before calibrating.
If tau does not separate blocked from clean, retain an inconclusive verdict and review other signals;
do not quietly choose a threshold that makes the demonstration pass.

## 4. Telegram integration

Copy `.env.example` to `.env`; enter the bot token and chat ID locally. Never paste the token into chat or GitHub.
The existing helper can discover the chat ID after you send the bot a message:

```powershell
.\.venv\Scripts\python.exe tools/telegram_check.py
# Run only when you intend to send a real test message:
.\.venv\Scripts\python.exe tools/telegram_check.py send
```

Restart Streamlit after changing `.env`. Enable **Send live Telegram alerts** in real live mode.
The banner is always primary. A degraded/recovered transition sends once in the current browser session;
network failures are shown in alert history. Multiple dashboard sessions may each send an alert, so use
one operator session during the demo. Automatic delivery and real bench testing have not yet been verified.

## 5. Optional extensions and checks

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip install -r requirements-optional.txt
.\.venv\Scripts\python.exe tools/anomaly_check.py --clean1 data/replay/FAKE_run_clean1_20261109_0900.csv --run data/replay/FAKE_run_blocked_20261109_1005.csv
```

For weather normalization, give the report `--weather-baselines <old_run1.csv> <old_run2.csv>`.
These must be independent blocked/before-service runs with matched conditions, distinct outdoor means
spanning at least 0.5 C, and matching real/FAKE provenance. The clean2 outdoor mean must lie within the
training range. Two points demonstrate a method; they do not validate seasonal accuracy.

## 6. Five-minute replay demonstration

1. Explain that this is a FAKE software rehearsal until the team's real recordings are available.
2. Show clean1 and the formula. Explain that a larger tau means slower room cooling.
3. Select blocked; seek to minute 8 or play at 10x. Watch three minute-spaced fits and the banner.
4. Show the actual-versus-clean-twin gap, then select clean2 for recovery.
5. Generate the report. Explain the unavailable weather normalization and the assumptions behind estimated rupees.

For a real demo, use real recordings for accelerated replay and disclose replay mode. A live 15-minute
pull-down cannot honestly be compressed into five minutes without replay.
