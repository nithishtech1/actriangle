from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from twin.fit_tau import detect_cooling_start, FitError
from twin.service import assess_service
from twin.gen_synthetic import generate_run
from tools.prepare_service_demo import prepare


def test_onset_skips_false_decline_before_later_cooling():
    t = np.arange(0, 15, 0.5)
    y = np.where(t < 2, 30 - 0.2*t, 35 - 0.5*np.maximum(t - 4, 0))
    onset = detect_cooling_start(t, y)
    assert t[onset] >= 3.5


def test_onset_rejects_too_sparse_window():
    with pytest.raises(FitError, match='No sustained cooling detected'):
        detect_cooling_start([0, 2], [30, 29])


@pytest.mark.parametrize('failure', ['missing', 'duplicate', 'flat'])
@pytest.mark.parametrize('outdoor', [33, 40, None])
def test_weather_failure_falls_back_only_when_weather_matches(tmp_path, failure, outdoor):
    paths = prepare(tmp_path)
    if failure == 'missing':
        weather = [tmp_path/'FAKE_missing.csv']
    elif failure == 'duplicate':
        weather = [paths[3], paths[3]]
    else:
        df = pd.read_csv(paths[3]); df.room_C = 30; df.to_csv(paths[3], index=False)
        weather = paths[3:]
    df = pd.read_csv(paths[2]); df.outdoor_C = outdoor; df.to_csv(paths[2], index=False)
    result = assess_service(paths[:3], weather_baselines=weather, conditions_confirmed=True)
    assert result['normalized_improvement_pct'] is None
    assert result['expected_old_tau_min'] is None
    assert any('Unavailable:' in w for w in result['warnings'])
    if outdoor == 33:
        assert result['status'] == 'improved'
        assert result['basis'] == 'matched outdoor conditions (raw comparison)'
    else:
        assert result['status'] == 'inconclusive'


@pytest.mark.parametrize('option,value', [('--kw', '0'), ('--kw', '-1'), ('--tariff', '0'), ('--tariff', '-1')])
def test_report_cli_nonpositive_estimate_inputs(tmp_path, monkeypatch, option, value):
    from report import make_report
    paths = prepare(tmp_path/'runs')
    output = tmp_path/'report.pdf'
    monkeypatch.setattr('sys.argv', ['make_report', *map(str, paths[:3]), '--output', str(output),
                                   '--conditions-confirmed', '--kw', '1.5', '--tariff', '8', option, value])
    make_report.main()
    assert output.read_bytes().startswith(b'%PDF')


def test_dashboard_explains_rejected_baseline(tmp_path, monkeypatch):
    import config
    from streamlit.testing.v1 import AppTest
    df = generate_run('clean1', duration_min=10); df.room_C = 30
    df.to_csv(tmp_path/'FAKE_clean1.csv', index=False)
    monkeypatch.setattr(config, 'DATA_RAW', tmp_path)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app/dashboard.py'), default_timeout=60)
    app.run(); app.toggle[0].set_value(False).run()
    assert not app.exception
    assert any('Clean baseline rejected: No sustained cooling detected.' in e.value for e in app.error)
    assert len(app.get('vega_lite_chart')) == 4
