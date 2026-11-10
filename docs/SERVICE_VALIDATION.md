# Service prototype validation — 10 November 2026

The service workflow uses controlled before/after cooling runs with a healthy reference.
It preserves the existing CSV phases and scaffold. Live charts now operate during baseline
collection. The dashboard and PDF use the same conditions, weather and tau assessment.

50 tests passed across the full suite and targeted UI reruns (48 passed initially;
the baseline-chart assertion used an outdated Streamlit element name and was corrected;
both the corrected test and the added normalized-report UI test passed).

Regression cases reject cooling curves that plateau at minutes 3, 5, 7 or 10 instead
of accepting a spuriously fast tau. Verdict tests cover missing condition confirmation,
matched weather, normalized improvement, absent improvement, extrapolation refusal,
interrupted cooling and an inconclusive PDF. UI checks cover baseline collection charts,
replay alerts, weather selection and PDF generation/download availability.

The two-page synthetic service PDF was rendered and visually inspected. Its fixture
comparison gives 42.7% raw and approximately 43.0% normalized reduction in tau.
These are generated software results only. Cost is uncalculated without actual power/tariff.

Real AC recordings, threshold calibration, physical bench stability, actual Telegram
delivery and real service verification remain pending. The continuous-cooling and
comparison tolerances are conservative prototype eligibility rules, not validated
statistical confidence or a measurement of compressor state.

See SERVICE_DEMO.md for the operator workflow and real-data handoff.
