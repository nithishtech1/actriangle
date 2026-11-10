# Service verification: run this prototype

The agreed prototype compares separate, controlled cooling runs. It reports
**Cooling performance improved**, **No clear cooling improvement**, or
**Inconclusive**. This is evidence about room cooling performance; it cannot
certify every maintenance procedure or identify all AC faults.

## Start

From the repository folder, install requirements.txt into your Python environment.
Then run:

```powershell
python tools/prepare_service_demo.py
python -m streamlit run app/dashboard.py
```

The preparation command overwrites only the project's named FAKE demo recordings.
It adds synthetic 31 C / 35 C before-service weather examples under data/replay/weather.
All outputs remain labeled FAKE. They are software demonstrations, not real results.

## Five-minute presentation

1. Disclose that this is accelerated replay of synthetic recordings until real AC recordings exist.
2. Select blocked and clean1. Seek to minute 15 or play at 10x to show the sensor charts,
   twin overlay, health gauge and alert banner.
3. In the service section, select clean1 (healthy reference), blocked (before service),
   and clean2 (after service). The CSV phase contract is unchanged.
4. Confirm the shared AC/fan/room conditions. Synthetic metadata records setpoint 18 C.
   The matched-weather raw verdict should show improvement.
5. Select both weather training recordings. Show raw versus weather-normalized reduction
   in tau and the shared verdict. The two-point regression demonstrates the method only.
6. Generate and download the PDF. Uncheck the conditions confirmation to demonstrate
   that missing evidence yields an inconclusive result rather than a success claim.

## Real test handoff

- Keep the same AC, setpoint, fan, doors/windows, occupancy and comparable solar load.
- Start before/after phases within 1 C of one another; log 30 minutes each under sustained cooling.
- Use clean1 for the healthy reference, blocked for before service, clean2 for after service.
  Labels describe the test phases and do not diagnose a blocked filter automatically.
- Record actual setpoints with logger --setpoint-c. Sidecar setpoints take precedence over
  a report-wide fallback. Optional sidecar fan_setting/test_unit identify matching settings.
- Use real CSVs plus sidecars from data/raw. Turn replay off to watch live raw sensors while
  the baseline is collected. Health becomes available only after a valid baseline exists.
- The continuous-cooling guard rejects early plateaus or warming in three-minute segments.
  A conservative rejection means repeat the run; it does not diagnose compressor state.
- Without weather training, outdoor means must be within 1 C and outdoor coverage >=90%.
  For normalization select independent, non-overlapping before-service runs with the same
  settings, distinct outdoor means spanning >=0.5 C, and a range containing after-service weather.
- The 15% improvement threshold, 1 C start/weather tolerances and tau-uncertainty guard
  are provisional prototype policies in config.py. Validate them with real repeated runs.
- Live monitoring assesses the initial pull-down; later operation requires a new comparable
  run. The short presentation uses disclosed replay rather than promising instant detection.
- Configure Telegram locally as described in QUICKSTART.md. Replay never sends messages.

CLI report:

```powershell
python -m report.make_report data/replay --output reports/FAKE_service.pdf --conditions-confirmed --weather-baselines data/replay/weather
```

The dashboard and PDF call the same assessment function. Missing conditions, mismatched
weather, invalid fits or unsupported weather extrapolation produce an inconclusive result.
Nameplate input kW and tariff are optional; cost is an estimate and is withheld for an
inconclusive comparison. Real delivery and real AC acceptance require the hardware team.
