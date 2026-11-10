import numpy as np
import pytest
from pathlib import Path
from twin.fit_tau import fit_tau, FitError
from twin.gen_synthetic import generate_run
from twin.service import assess_service
from tools.prepare_service_demo import prepare
from report.make_report import build_report


@pytest.mark.parametrize('stop', [3, 5, 7, 10])
def test_plateau_never_becomes_fast_healthy_tau(stop):
    df = generate_run('clean1', noise=0)
    df.room_C = 22 + 8*np.exp(-np.minimum(df.ms/60000, stop)/8)
    with pytest.raises(FitError, match='plateaued'):
        fit_tau(df)


def test_verdict_requires_conditions_and_weather(tmp_path):
    paths = prepare(tmp_path)
    assert assess_service(paths[:3])['status'] == 'inconclusive'
    assert assess_service(paths[:3], conditions_confirmed=True)['status'] == 'improved'
    normalized = assess_service(paths[:3], weather_baselines=paths[3:], conditions_confirmed=True)
    assert normalized['status'] == 'improved'
    assert normalized['normalized_improvement_pct'] > 15
    assert normalized['basis'] == 'weather-normalized'
    import pandas as pd
    after = pd.read_csv(paths[2]); after.outdoor_C = 40; after.to_csv(paths[2], index=False)
    assert assess_service(paths[:3], conditions_confirmed=True)['status'] == 'inconclusive'
    assert assess_service(paths[:3], weather_baselines=paths[3:], conditions_confirmed=True)['status'] == 'inconclusive'


def test_no_improvement_and_interruption(tmp_path):
    paths = prepare(tmp_path)
    import pandas as pd
    before = pd.read_csv(paths[1]); after = pd.read_csv(paths[2])
    after.room_C = before.room_C
    after.to_csv(paths[2], index=False)
    assert assess_service(paths[:3], conditions_confirmed=True)['status'] == 'not_improved'
    after.room_C = 24 + 6*np.exp(-np.minimum(after.ms/60000, 5)/14)
    after.to_csv(paths[2], index=False)
    result = assess_service(paths[:3], conditions_confirmed=True)
    assert result['status'] == 'inconclusive'
    assert any('plateaued' in x for x in result['reasons'])
    assert build_report(paths[:3], conditions_confirmed=True).startswith(b'%PDF')


def test_live_charts_without_ready_baseline(tmp_path, monkeypatch):
    import config
    from streamlit.testing.v1 import AppTest
    generate_run('clean1', duration_min=5).to_csv(tmp_path/'FAKE_first.csv', index=False)
    monkeypatch.setattr(config, 'DATA_RAW', tmp_path)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app/dashboard.py'), default_timeout=60)
    app.run(); app.toggle[0].set_value(False).run()
    assert not app.exception
    assert any('Collecting baseline' in x.value for x in app.info)
    assert len(app.get('vega_lite_chart')) == 4


def test_dashboard_normalized_verdict_and_download():
    from streamlit.testing.v1 import AppTest
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app/dashboard.py'), default_timeout=60)
    app.run()
    app.checkbox(key='conditions_confirmed').set_value(True).run()
    widget = app.multiselect[0]
    import config
    widget.set_value(sorted((config.DATA_REPLAY/'weather').glob('*.csv'))).run()
    assert not app.exception
    assert any('Cooling performance improved' in x.value for x in app.success)
    assert any('weather-normalized' in x.value for x in app.caption)
    next(b for b in app.button if b.label == 'Generate report').click().run()
    assert not app.exception
    assert app.session_state.report_bytes.startswith(b'%PDF')
