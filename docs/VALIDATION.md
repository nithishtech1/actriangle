# Software validation

Tested locally on Windows with Python 3.12.14 on 9 November 2026.

## Results

- **42 automated tests passed** with pytest, including Streamlit AppTest interactions.
- All three included replay CSVs passed the repository checker: **414 rows per file**.
- Dashboard browser check: blocked replay displayed **56.8/100 health**, the sustained-degradation banner,
  all sensor charts and the twin overlay; Generate report exposed a PDF download.
- Two-page FAKE PDF rendered to images and visually checked for readable tables, chart, watermark and page breaks.
- Open-Meteo HTTP request succeeded. Cache, typed fallback and network failure behavior were separately unit tested.
- Five minutes of **simulated serial time**, including a disconnect/reconnect, saved 60 rows across two files.
  This is not a physical ESP32 bench result.
- Optional Isolation Forest trained on clean1 and scored the blocked fixture. Its output stays separate from health.
- `git diff --check` passed.

| FAKE phase | Intended tau (min) | Recovered tau (min) | Absolute error | R2 |
| --- | ---: | ---: | ---: | ---: |
| clean1 | 8.00 | 7.8211 | 2.24% | 0.99846 |
| blocked | 14.00 | 13.7741 | 1.61% | 0.99781 |
| clean2 | 8.00 | 7.8894 | 1.38% | 0.99905 |

The fixtures meet the requested 5% recovery criterion. Raw simulated reduction in tau is 42.72%; clean-run
repeatability differs by 0.87%. These numbers describe generated data only and are not project hardware results.
Additional random-noise stress cases are tested with a wider tolerance: a short noisy window cannot guarantee
5% accuracy for every realization. A high R2 does not prove the fitted tau is accurate.

## Tested direct dependencies

```text
pyserial 3.5
pandas 3.1.1
numpy 2.5.4
scipy 1.18.1
streamlit 1.67.0
matplotlib 3.11.2
requests 2.34.2
fpdf2 2.9.0
pytest 9.2.0
scikit-learn 1.9.1 (optional)
```

The GitHub Actions workflow is configured for Python 3.10/3.12 on Windows/Linux.
The results above are local tests. Check the repository's Actions page for hosted CI results after publishing.

## Remaining validation

Physical serial stability, probe calibration, three real cooling runs, actual Telegram delivery,
real-data threshold calibration and a real Proof-of-Service report are pending. Weather normalization
also needs independent same-condition runs at distinct outdoor temperatures. No production or hardware
accuracy claim follows from these software tests.
