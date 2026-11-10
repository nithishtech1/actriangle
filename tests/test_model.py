import numpy as np
import pandas as pd
import pytest

import config
from twin.data import DataError, read_run, validate_run
from twin.fit_tau import FitError, fit_tau, twin_overlay
from twin.gen_synthetic import generate_all, generate_run
from twin.health import AlertRule, health_score
from twin.monitor import Monitor
from twin.normalization import fit_weather_model
from twin.analyze import analyze_run, compare_phases, savings_estimate


@pytest.mark.parametrize("phase,tau,seed", [("clean1", 8, 42), ("blocked", 14, 43), ("clean2", 8, 44)])
def test_tau_recovered_within_five_percent(phase, tau, seed):
    result = fit_tau(generate_run(phase, seed=seed))
    assert result.tau_min == pytest.approx(tau, rel=0.05)
    assert result.r2 >= 0.9
    assert 14.8 < result.duration_min <= 15


@pytest.mark.parametrize("phase,tau", [("clean1", 8), ("blocked", 14)])
@pytest.mark.parametrize("seed", [0, 1, 7, 42, 43, 44])
def test_noise_stress_runs_keep_tau_bounded(phase, tau, seed):
    # A 15-minute fit to a 14-minute time constant is weakly identified.
    # The 5% acceptance target applies to the supplied reproducible fixtures;
    # independent random noise must not be claimed to guarantee 5% accuracy.
    result = fit_tau(generate_run(phase, seed=seed))
    assert result.tau_min == pytest.approx(tau, rel=0.20)


def test_flat_and_noisy_curves_rejected():
    frame = generate_run("clean1")
    frame.room_C = 30
    with pytest.raises(FitError, match="No sustained"):
        fit_tau(frame)
    frame.room_C = 30 + np.random.default_rng(8).normal(0, 2, len(frame))
    with pytest.raises(FitError):
        fit_tau(frame)


def test_warmup_detection_and_actual_elapsed_time():
    frame = generate_run("clean1", warmup_min=4, interval_s=7.3)
    result = fit_tau(frame)
    assert 2.5 <= result.start_min <= 5
    assert result.tau_min == pytest.approx(8, rel=0.10)
    # Dropping some rows must not cause time to be reconstructed from row count.
    gapped = frame.drop(frame.index[::8])
    assert fit_tau(gapped).tau_min == pytest.approx(result.tau_min, rel=0.05)


def test_short_reset_and_disconnected_runs_rejected():
    with pytest.raises(FitError, match="Need"):
        fit_tau(generate_run("clean1", duration_min=5))
    frame = generate_run("clean1")
    frame.loc[20, "room_C"] = -127
    with pytest.raises(DataError):
        fit_tau(frame)
    frame = generate_run("clean1")
    frame.phase = "reset"
    with pytest.raises(FitError, match="reset"):
        fit_tau(frame)
    frame = generate_run("clean1").drop(range(50, 65))
    with pytest.raises(FitError, match="Gap"):
        fit_tau(frame)


def test_twin_starts_at_current_temperature():
    baseline = fit_tau(generate_run("clean1"))
    frame = generate_run("blocked")
    frame.room_C += 2
    current = fit_tau(frame)
    predicted = twin_overlay(baseline, current, [current.start_min, current.start_min + 8])
    assert predicted[0] == pytest.approx(current.start_C)
    assert predicted[1] < predicted[0]


def test_alert_cadence_invalid_reset_and_recovery():
    rule = AlertRule()
    assert rule.update(70, 60) is None
    assert rule.update(70, 61) is None
    assert rule.count == 1
    assert rule.update(70, 120) is None
    assert rule.update(None, 180) is None
    assert rule.count == 0
    for stamp in (240, 300):
        assert rule.update(70, stamp) is None
    assert rule.update(70, 360) == "degraded"
    assert rule.update(70, 420) is None
    assert rule.update(85, 480) == "recovered"
    assert rule.update(70, 540) is None
    assert rule.update(70, 720) is None
    assert rule.count == 1
    assert health_score(8, 14) == pytest.approx(57.142857)
    assert health_score(8, 6) == 100
    with pytest.raises(ValueError):
        health_score(8, 0)


def test_incremental_replay_and_batch_replay_agree():
    df = validate_run(generate_run("blocked", seed=43))
    baseline = fit_tau(generate_run("clean1"))
    batch = Monitor(baseline)
    batch_events = batch.advance(df)
    stepped = Monitor(baseline)
    events = []
    for end in range(20, len(df) + 20, 20):
        events.extend(stepped.advance(df.iloc[:end]))
    assert events == batch_events
    assert len(events) == 1 and events[0]["event"] == "degraded"
    assert stepped.health == pytest.approx(batch.health)
    assert stepped.complete
    assert len(stepped.history) == 8
    assert stepped.advance(df) == []


def test_data_contract_reboot_nan_partial_write_and_fake_guard(tmp_path):
    frame = generate_run("clean1")
    frame.loc[15, "ms"] = 0
    with pytest.raises(DataError, match="strictly increasing"):
        validate_run(frame)
    frame = generate_run("clean1")
    frame.loc[1, "ts_iso"] = "not-a-date"
    with pytest.raises(DataError, match="timestamp"):
        validate_run(frame)
    frame = generate_run("clean1").iloc[:10]
    path = tmp_path / "partial.csv"
    path.write_text(frame.to_csv(index=False) + "2026-11-09,unfinished", encoding="utf-8")
    assert len(read_run(path, live=True)) == 10
    with pytest.raises(DataError):
        read_run(path)
    with pytest.raises(ValueError, match="data/raw"):
        generate_all(config.DATA_RAW)


def test_comparison_and_dimensional_savings(tmp_path):
    records = [analyze_run(p) for p in generate_all(tmp_path)]
    comparison = compare_phases(records)
    assert 38 < comparison["raw_improvement_pct"] < 47
    assert comparison["tau_separates"]
    blocked, clean = records[1:]
    estimate = savings_estimate(blocked, clean, kw=1.5, tariff=8)
    assert estimate["estimated_rs"] == pytest.approx(estimate["minutes_saved"] / 60 * 1.5 * 8)
    assert estimate["minutes_saved"] > 0
    assert not savings_estimate(blocked, clean)["available"]
    assert not savings_estimate(blocked, clean, kw=1.5, tariff=8, target=20)["available"]
    with pytest.raises(ValueError, match="exactly one"):
        compare_phases(records[:2])
    records[2]["synthetic"] = False
    with pytest.raises(ValueError, match="FAKE"):
        compare_phases(records)


def test_weather_requires_distinct_same_condition_runs():
    rows = [{"phase": "blocked", "synthetic": True, "outdoor_mean_C": t, "tau_min": tau}
            for t, tau in [(30, 12), (34, 16)]]
    model = fit_weather_model(rows)
    assert model.predict(32) == pytest.approx(14)
    with pytest.raises(ValueError, match="extrapolation"):
        model.predict(40)
    with pytest.raises(ValueError, match="at least two"):
        fit_weather_model(rows[:1])
    with pytest.raises(ValueError, match="distinct"):
        fit_weather_model([rows[0], rows[0]])
    rows[1]["phase"] = "clean2"
    with pytest.raises(ValueError, match="mix clean"):
        fit_weather_model(rows)
