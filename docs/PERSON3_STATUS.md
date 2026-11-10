# Person 3 task status

Status as of 9 November 2026. The user has not yet retrieved ESP32 data.

| Tasks | Implementation / verification | Status |
| --- | --- | --- |
| 8 | Requirements installed into an isolated local Python 3.12 environment | Done for software testing |
| 44-45 | Newton cooling generator; three 40-minute FAKE CSVs; clean tau 8, blocked tau 14, noise 0.1 C | Done |
| 46-49 | Serial parsing, mapping/offsets, timestamps/phases, weather cache/fallback, per-row flush, reconnect/reboot split | Implemented and simulated |
| 50 | Five minutes of simulated serial time with 60 rows and a disconnect/reconnect | Software test passed; physical bench test pending |
| 51-52 | Cooling onset, 3-sample median, first 15-minute curve_fit, R2/quality gates; supplied tau recovered within 5% | Done |
| 53-55 | Health ratio, twin from current start temperature, three consecutive 60-second fits; gap/invalid/duplicate handling | Done |
| 56-60 | Streamlit live/replay, 10x speed, four charts, gauge, overlay and status banner | Implemented and tested |
| 61 | Telegram transition delivery with redacted errors, opt-in live mode, disabled in replay | Mock tested; actual bot delivery pending |
| 62-66 | PDF download/CLI, conditions, tau, overlay, improvement, estimated Rs, FAKE watermark | Done; sample rendered and inspected |
| 82-85 | Analysis CLI, repeatability/separation check, supporting signals, configurable thresholds | Ready; real-data analysis/calibration pending |
| 87-92 | Real CSV replay, live file follow, stale data status, report generation, outdoor-range note | Software ready; physical end-to-end and real report pending |
| 94 optional | Same-condition outdoor regression, minimum distinct temperatures, no extrapolation | Implemented and unit tested; real weather runs pending |
| 95 optional | Isolation Forest trained on clean1 only, separate anomaly-check CLI | Implemented and tested as secondary flag |

## Intentionally still pending

- Real bench capture, accurate mapping/offsets and actual AC/room settings.
- Three comparable hardware phases and selection/calibration of the signal based on those results.
- Actual Telegram delivery to the team's bot/chat.
- Verified report from real measurements and any defensible weather adjustment.

Firmware, wiring, hardware operation, account creation, teammate invitations and final submission are
outside the Person 3 software implementation. No real results were fabricated to mark these tasks complete.

## Acceptance evidence

See `VALIDATION.md`. Automated tests cover malformed readings, weather outages, interrupted capture,
cooling fit quality, irregular timestamps, replay equivalence, alert cadence, report generation and dashboard actions.
All FAKE filenames remain clearly marked. `data/raw` contains no fabricated measurements.
