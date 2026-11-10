"""Local ClimaTwin dashboard: streamlit run app/dashboard.py."""
from datetime import datetime
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd
import streamlit as st
import config
from app.notifications import send_telegram
from report.make_report import build_report
from twin.data import DataError, is_fake, read_run
from twin.fit_tau import FitError, fit_tau, twin_overlay
from twin.monitor import Monitor
from twin.service import assess_service

st.set_page_config(page_title="ClimaTwin | Cooling performance", page_icon="❄️", layout="wide")
st.title("ClimaTwin")
st.caption("TEAM TRIANGLE  /  Cooling performance, made visible")


def run_paths(folder):
    return sorted(Path(folder).glob("*.csv"))


def phase_files(paths, phase, fake):
    result = []
    for path in paths:
        if is_fake(path) != fake or path.name.startswith("bench_"):
            continue
        try:
            if read_run(path, live=True).phase.iloc[0] == phase:
                result.append(path)
        except (DataError, OSError):
            continue
    return result


with st.sidebar:
    st.header("Recording controls")
    replay = st.toggle("Replay recordings", value=True)
    folder = st.text_input("CSV folder", value=str(config.DATA_REPLAY if replay else config.DATA_RAW),
                           key="replay_folder" if replay else "live_folder")
    files = [p for p in run_paths(folder) if not p.name.startswith("bench_")]
    if not files:
        st.info("No run CSVs yet. Generate replay data or start the serial logger, then refresh.")
        st.code("python -m twin.gen_synthetic" if replay else "python -m logger.log_serial --port COM5 --phase clean1")
        st.button("Refresh files")
        st.stop()
    follow = st.checkbox("Follow newest CSV", value=True) if not replay else False
    selected = st.selectbox("Recording", files, format_func=lambda p: p.name, disabled=follow)
    if follow:
        selected = max(files, key=lambda p: p.stat().st_mtime_ns)
    fake = is_fake(selected)
    baseline_options = phase_files(files, "clean1", fake)
    if not baseline_options:
        st.warning("A matching clean1 CSV is required to learn the baseline.")
    baseline_path = st.selectbox("Clean1 baseline", baseline_options, format_func=lambda p: p.name) if baseline_options else None
    speed = st.select_slider("Replay speed", options=[1, 5, 10, 20], value=10) if replay else 1
    notifications = st.checkbox("Send live Telegram alerts", value=False, disabled=replay or fake,
                                 help="Requires your bot token and chat ID in .env. Replay never sends.")
    st.caption("Weather: Open-Meteo (CC BY 4.0), or configured fallback. See logger sidecars.")
    st.markdown("[Weather data source](https://open-meteo.com/)")

if fake:
    st.warning("FAKE DATA · Software demonstration only. These are simulated readings, not hardware results.")
else:
    st.info("RECORDED DATA · " + ("Replay of an ESP32 run." if replay else "Watching the logger's CSV."))

try:
    source = read_run(selected, live=not replay)

except (DataError, FitError, OSError) as exc:
    st.info(f"Waiting for usable recordings: {exc}")
    st.button("Refresh baseline")
    st.stop()

baseline = None
baseline_error = None
baseline_duration = None
try:
    if baseline_path:
        baseline_frame = read_run(baseline_path, live=not replay)
        baseline_duration = float(baseline_frame.elapsed_min.iloc[-1])
        baseline = fit_tau(baseline_frame)
except (DataError, FitError, OSError) as exc:
    baseline_error = str(exc)
identity = (str(selected), str(baseline_path), baseline.tau_min if baseline else None, replay)
if st.session_state.get("identity") != identity:
    st.session_state.identity = identity
    st.session_state.monitor = Monitor(baseline) if baseline else None
    st.session_state.cursor = 0.0
    st.session_state.last_tick = time.monotonic()
    st.session_state.notices = []
    st.session_state.seek = 0.0

duration = float(source.elapsed_min.iloc[-1])
if replay:
    def seek_changed():
        st.session_state.cursor = float(st.session_state.seek)
        st.session_state.monitor = Monitor(baseline) if baseline else None
        st.session_state.last_tick = time.monotonic()
        st.session_state.notices = []

    controls = st.columns([1, 1, 4])
    with controls[0]:
        playing = st.checkbox("Play replay", value=False)
    with controls[1]:
        if st.button("Restart"):
            st.session_state.seek = 0.0
            seek_changed()
    with controls[2]:
        st.slider("Seek (minutes)", min_value=0.0, max_value=max(0.1, duration),
                  step=0.1, key="seek", on_change=seek_changed)
else:
    playing = False


@st.fragment(run_every=1)
def monitor_panel():
    path = selected
    if not replay and follow:
        latest_files = [p for p in run_paths(folder) if not p.name.startswith("bench_")]
        if latest_files:
            path = max(latest_files, key=lambda p: p.stat().st_mtime_ns)
        if path != selected:
            st.rerun(scope="app")
    try:
        df = source if replay else read_run(path, live=True)
    except (DataError, OSError) as exc:
        st.warning(f"Waiting for logger: {exc}")
        return
    now = time.monotonic()
    dt = now - st.session_state.last_tick
    st.session_state.last_tick = now
    if replay:
        if playing:
            st.session_state.cursor = min(duration, st.session_state.cursor + dt * speed / 60)
        view = df[df.elapsed_min <= st.session_state.cursor + 0.00001]
        st.caption(f"Replay: {st.session_state.cursor:.1f} / {duration:.1f} minutes at {speed}x")
    else:
        view = df
        st.caption(f"Live file: {path.name}")
    if view.empty:
        st.info("Waiting for the first sample.")
        return
    left, right = st.columns(2)
    for column, title, unit, container in (
        ("supply_C", "Supply air", "°C", left), ("return_C", "Return air", "°C", right),
        ("room_C", "Room temperature", "°C", left), ("room_RH", "Room humidity", "% RH", right),
    ):
        with container:
            st.subheader(title)
            st.line_chart(view.set_index("elapsed_min")[[column]], height=180,
                          x_label="Elapsed minutes", y_label=unit)
    if df.phase.iloc[0] == "reset":
        st.info("Warm-back / reset phase. Sensor monitoring continues; health fitting is paused.")
        return
    if baseline is None:
        current_baseline_error = baseline_error
        current_baseline_duration = baseline_duration
        try:
            if baseline_path:
                baseline_frame = read_run(baseline_path, live=True)
                current_baseline_duration = float(baseline_frame.elapsed_min.iloc[-1])
                fit_tau(baseline_frame)
                st.rerun(scope="app")
        except (DataError, FitError, OSError) as exc:
            current_baseline_error = str(exc)
        if current_baseline_error and (current_baseline_duration is None or current_baseline_duration > 5):
            st.error(f"Clean baseline rejected: {current_baseline_error}")
        else:
            st.info("Collecting baseline: live sensors are available. Health needs a valid 15-minute clean1 run.")
        return
    monitor = st.session_state.monitor
    if monitor.history and view.elapsed_min.iloc[-1] < monitor.history[-1]["elapsed_min"]:
        monitor = st.session_state.monitor = Monitor(baseline) if baseline else None
    events = monitor.advance(view)
    stale = not replay and time.time() - path.stat().st_mtime > 30
    for event in events:
        description = f"{event['event'].title()} at {event['at_seconds']/60:.0f} min; health {event['health']:.1f}/100."
        st.session_state.notices.append(description)
        recent = view.elapsed_min.iloc[-1] * 60 - event["at_seconds"] <= 90
        if notifications and not replay and not fake and not stale and recent:
            delivery = send_telegram("ClimaTwin: " + description + " Cooling-performance proxy; inspect the AC.")
            st.session_state.notices.append(delivery.detail)
    if stale:
        st.warning("No new sensor rows for over 30 seconds. Showing the last recorded result; check the logger.")
    if monitor.health is None:
        st.info(monitor.reason)
    elif monitor.rule.active:
        st.error("Cooling degradation detected · Health below 80 for three consecutive minute fits.")
    elif monitor.health < config.HEALTH_ALERT_THRESHOLD:
        st.warning(f"Cooling slower than baseline · {monitor.rule.count}/3 low-health fits.")
    else:
        st.success("Cooling matches the clean baseline within the current alert threshold.")
    values = st.columns(4)
    values[0].metric("Cooling health / 100", "—" if monitor.health is None else f"{monitor.health:.1f}")
    values[1].metric("Current tau", "—" if monitor.latest is None else f"{monitor.latest.tau_min:.2f} min")
    values[2].metric("Clean baseline tau", f"{baseline.tau_min:.2f} min")
    outdoor = view.outdoor_C.iloc[-1]
    values[3].metric("Outdoor temperature", "Unavailable" if pd.isna(outdoor) else f"{outdoor:.1f} °C")
    st.progress(0.0 if monitor.health is None else monitor.health / 100,
                text="Cooling health gauge · time-constant ratio, not measured efficiency")
    if monitor.complete:
        st.caption("Initial 15-minute pull-down evaluated. Result is held; a new cooling run is needed for a new assessment.")
    else:
        st.caption("Provisional fits from minute 8; final fit uses the first 15 minutes. Alert cadence follows recording time.")
    st.subheader("Live room response / clean twin")
    if monitor.latest is not None:
        visible = view[(view.elapsed_min >= monitor.latest.start_min) &
                       (view.elapsed_min <= monitor.latest.start_min + 15)]
        overlay = pd.DataFrame({"Recorded room °C": visible.room_C.to_numpy(),
                                "Clean twin °C": twin_overlay(baseline, monitor.latest, visible.elapsed_min)},
                               index=visible.elapsed_min.to_numpy())
        overlay.index.name = "Elapsed minutes"
        st.line_chart(overlay, height=270)
        st.caption(f"Twin starts at this run's fitted {monitor.latest.start_C:.2f} °C. "
                   f"Current R² {monitor.latest.r2:.3f}; clean final temperature {baseline.final_C:.2f} °C.")
    else:
        st.info("The overlay appears after the first acceptable cooling fit.")
    if st.session_state.notices:
        with st.expander("Alert and delivery history"):
            for text in st.session_state.notices[-12:]:
                st.write(text)


monitor_panel()

st.divider()
st.subheader("Proof-of-Service report")
st.caption("Uses complete selected recordings, independently of the replay position. Select one run per phase.")
report_paths = []
selectors = st.columns(3)
for column, phase in zip(selectors, ("clean1", "blocked", "clean2")):
    options = phase_files(files, phase, fake)
    with column:
        choice = st.selectbox(f"Report: {phase}", options, format_func=lambda p: p.name, key=f"report_{phase}") if options else None
        if choice:
            report_paths.append(choice)
        else:
            st.caption(f"No {phase} run available yet.")
estimate_fields = st.columns(4)
kw = estimate_fields[0].number_input("AC nameplate kW (0 = unknown)", 0.0, 50.0,
                                    float(config.AC_NAMEPLATE_KW or 0), step=0.1)
tariff = estimate_fields[1].number_input("Tariff ₹/kWh (0 = unknown)", 0.0, 100.0,
                                        float(config.TARIFF_RS_PER_KWH or 0), step=0.5)
target = estimate_fields[2].number_input("Estimate target °C", 16.0, 35.0, 26.0, step=0.5)
setpoint = estimate_fields[3].number_input("AC setpoint °C (0 = unknown)", 0.0, 35.0,
                                          float(config.SETPOINT_C or 0), step=1.0)
st.caption("Service check: blocked = before service; clean2 = after service; clean1 = healthy reference.")
confirmed = st.checkbox("I confirm the same AC, fan setting, doors/windows, occupancy and comparable solar conditions", key="conditions_confirmed")
weather_folder = st.text_input("Before-service weather training folder (optional)", value=str(Path(folder) / "weather"))
weather_options = phase_files(run_paths(weather_folder), "blocked", fake)
weather_paths = st.multiselect("Weather training recordings", weather_options, format_func=lambda p: p.name)
assessment = None
if len(report_paths) == 3:
    try:
        assessment = assess_service(report_paths, weather_baselines=weather_paths,
                                    setpoint=setpoint or None, conditions_confirmed=confirmed)
        getattr(st, {"improved": "success", "not_improved": "warning", "inconclusive": "info"}[assessment["status"]])(assessment["label"])
        for reason in assessment["reasons"]:
            st.write(reason)
        st.caption("Comparison basis: " + assessment["basis"])
        st.caption(assessment["weather_detail"])
        cols = st.columns(2)
        for col, label, key in [(cols[0], "Raw tau reduction", "raw_improvement_pct"), (cols[1], "Weather-normalized tau reduction", "normalized_improvement_pct")]:
            col.metric(label, "Unavailable" if assessment[key] is None else f"{assessment[key]:.1f}%")
        st.caption("Cooling performance evidence cannot certify every service procedure. Decision margins are provisional.")
    except (DataError, FitError, ValueError, OSError) as exc:
        st.info(f"Service check unavailable: {exc}")
report_key = (tuple((str(p), p.stat().st_mtime_ns) for p in report_paths), kw, tariff, target, setpoint, confirmed, tuple((str(p), p.stat().st_mtime_ns) for p in weather_paths))
if st.button("Generate report", disabled=len(report_paths) != 3):
    try:
        st.session_state.report_bytes = build_report(report_paths, kw=kw or None, tariff=tariff or None,
                                                     target=target, setpoint=setpoint or None,
                                                     weather_baselines=weather_paths, conditions_confirmed=confirmed)
        st.session_state.report_key = report_key
        st.success("Report generated. Download below.")
    except (DataError, FitError, ValueError, OSError) as exc:
        st.error(f"Report needs valid complete runs: {exc}")
if st.session_state.get("report_key") == report_key and st.session_state.get("report_bytes"):
    st.download_button("Download PDF", st.session_state.report_bytes,
                        file_name=("FAKE_" if fake else "") + "ClimaTwin_report.pdf", mime="application/pdf")
st.caption("No measured power or fault diagnosis. Real-data calibration and hardware verification remain required.")
