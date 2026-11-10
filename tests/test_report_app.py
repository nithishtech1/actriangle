from pathlib import Path
import pytest

from twin.gen_synthetic import generate_all
from report.make_report import build_report


def test_report_bytes_and_incomplete_input(tmp_path):
    paths = generate_all(tmp_path)
    pdf = build_report(paths, kw=1.5, tariff=8, setpoint=18)
    assert pdf.startswith(b"%PDF") and len(pdf) > 20000
    with pytest.raises(ValueError, match="exactly one"):
        build_report(paths[:2])
    assert build_report(paths).startswith(b"%PDF")


def test_dashboard_replay_alert_and_report():
    from streamlit.testing.v1 import AppTest
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app" / "dashboard.py"), default_timeout=60)
    app.run()
    assert not app.exception
    app.slider(key="seek").set_value(20.0).run()
    assert not app.exception
    assert any("degradation detected" in item.value for item in app.error)
    assert any(item.value == "FAKE DATA · Software demonstration only. These are simulated readings, not hardware results." for item in app.warning)
    button = next(item for item in app.button if item.label == "Generate report")
    button.click().run()
    assert not app.exception
    assert app.session_state.report_bytes.startswith(b"%PDF")


def test_optional_anomaly_trains_only_on_clean():
    pytest.importorskip("sklearn")
    from twin.anomaly import HealthyAnomalyModel
    from twin.gen_synthetic import generate_run
    clean, blocked = generate_run("clean1"), generate_run("blocked")
    with pytest.raises(ValueError, match="clean1 only"):
        HealthyAnomalyModel().fit(blocked)
    model = HealthyAnomalyModel().fit(clean)
    assert len(model.score(blocked)) == len(blocked)
