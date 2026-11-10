"""Local ClimaTwin dashboard: streamlit run app/dashboard.py."""
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd
import streamlit as st
import config
from app.notifications import send_telegram
from app.ui_theme import (
    PALETTE,
    inject_styles,
    render_experiment_curves_chart,
    render_guided_action_bridge,
    render_guided_stepper,
    render_header,
    render_interactive_ac_widget,
    render_previsit_brief,
    render_printer_receipt_ejection,
    render_sensor_chart,
    render_service_deck,
    render_twin_overlay_chart,
    render_verdict_console,
)
from twin.data import DataError, is_fake, read_run
from twin.fit_tau import FitError, fit_tau, twin_overlay
from twin.monitor import Monitor
from twin.service import assess_service

st.set_page_config(page_title="ClimaTwin | Cooling performance", layout="wide")
inject_styles()

PHASE_LABELS = {
    "clean1": "Healthy Reference (clean1)",
    "blocked": "Before Service (blocked)",
    "clean2": "After Service (clean2)",
}


def resolve_safe_folder(user_input: str, default_folder: Path) -> Path:
    """Resolve user-supplied folder safely within project or configured data roots."""
    if not user_input or user_input.startswith("\\\\") or user_input.startswith("//"):
        return default_folder.resolve()
    try:
        candidate = Path(user_input).resolve()
    except (ValueError, OSError):
        return default_folder.resolve()
    allowed_roots = (
        config.ROOT.resolve(),
        config.DATA_RAW.resolve(),
        config.DATA_REPLAY.resolve(),
    )
    if any(candidate == root or candidate.is_relative_to(root) for root in allowed_roots):
        return candidate
    return default_folder.resolve()


def _was_folder_restricted(user_input: str, resolved_folder: Path) -> bool:
    """Return True when user_input was overridden to a safe fallback root."""
    if not user_input:
        return False
    try:
        return str(resolved_folder) != str(Path(user_input).resolve())
    except (ValueError, OSError):
        return True


def run_paths(folder: Path) -> list[Path]:
    return sorted(Path(folder).glob("*.csv"))


def phase_files(paths: list[Path], phase: str, fake: bool) -> list[Path]:
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


def render_four_sensor_charts(view: pd.DataFrame) -> None:
    """Render the 2x2 sensor telemetry channel grid."""
    left, right = st.columns(2)
    channels = (
        ("supply_C", "Supply vent air", "°C", PALETTE["cool"], left),
        ("return_C", "Return intake air", "°C", PALETTE["accent"], right),
        ("room_C", "Room temperature", "°C", PALETTE["ink"], left),
        ("room_RH", "Room humidity", "% RH", PALETTE["secondary"], right),
    )
    for column, title, unit, color, container in channels:
        with container:
            render_sensor_chart(view, column, title, unit, color)


with st.sidebar:
    st.header("Recording controls")
    replay = st.toggle("Replay recordings", value=True)
    default_dir = config.DATA_REPLAY if replay else config.DATA_RAW
    raw_folder = st.text_input(
        "CSV folder",
        value=str(default_dir),
        key="replay_folder" if replay else "live_folder",
    )
    folder = resolve_safe_folder(raw_folder, default_dir)
    if _was_folder_restricted(raw_folder, folder):
        st.caption("Restricted folder path to configured workspace/data directory.")
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
    baseline_path = (
        st.selectbox("Healthy baseline (clean1)", baseline_options, format_func=lambda p: p.name)
        if baseline_options
        else None
    )
    speed = st.select_slider("Replay speed", options=[1, 5, 10, 20], value=10) if replay else 1
    notifications = st.checkbox(
        "Send live Telegram alerts",
        value=False,
        disabled=replay or fake,
        help="Requires your bot token and chat ID in .env. Replay never sends.",
    )
    st.divider()
    st.subheader("Display & guidance")
    show_guidance = st.checkbox(
        "Show plain-English guidance",
        value=True,
        key="show_guidance",
        help="Show inline chart instructions, formula tooltips, and next-step cues.",
    )
    st.caption("Weather: Open-Meteo (CC BY 4.0), or configured fallback.")
    st.markdown("[Weather data source](https://open-meteo.com/)")
    with st.expander("Hardware & model details", expanded=False):
        st.markdown(
            "- **Hardware:** ESP32 WROOM NodeMCU 38-Pin (5V USB, zero mains), 2× DS18B20 probes (P27 / GPIO27), 1× DHT11 mid-room sensor (P26 / GPIO26).\n"
            "- **Physics Fit:** Fits initial 15-min pull-down $T(t) = T_\\text{final} + (T_0 - T_\\text{final})e^{-t/\\tau}$ ($R^2 \\ge 0.90$).\n"
            "- **Energy Note:** Cost figures estimate runtime savings × nameplate kW × tariff; not measured power."
        )

if replay:
    mode_label = f"REPLAY · {speed}x ({'SIMULATED' if fake else 'RECORDED'})"
    status_tone = "warn" if fake else "neutral"
else:
    is_fresh = time.time() - selected.stat().st_mtime <= 30
    mode_label = "LIVE STREAM · ACTIVE" if is_fresh else "LIVE FILE · STANDBY"
    status_tone = "live" if is_fresh else "warn"

render_header(mode_label, status_tone)

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

duration = float(source.elapsed_min.iloc[-1])
identity = (str(selected), str(baseline_path), baseline.tau_min if baseline else None, replay)
if st.session_state.get("identity") != identity:
    initial_seek = round(min(18.0, duration), 1) if replay and baseline is not None else 0.0
    st.session_state.identity = identity
    st.session_state.monitor = Monitor(baseline) if baseline else None
    st.session_state.cursor = initial_seek
    st.session_state.last_tick = time.monotonic()
    st.session_state.notices = []
    st.session_state.seek = initial_seek

tab_twin, tab_service = st.tabs(["Live Cooling Twin", "Guided Experiment"])

with tab_twin:
    if replay:
        def seek_changed():
            st.session_state.cursor = float(st.session_state.seek)
            st.session_state.monitor = Monitor(baseline) if baseline else None
            st.session_state.last_tick = time.monotonic()
            st.session_state.notices = []

        def jump_to(target_min: float):
            st.session_state.seek = round(min(max(0.0, target_min), max(0.1, duration)), 1)
            seek_changed()

        controls = st.columns([1.0, 0.85, 0.95, 1.05, 3.2])
        with controls[0]:
            playing = st.checkbox("Play replay", value=False)
        with controls[1]:
            if st.button("0m Start"):
                jump_to(0.0)
        with controls[2]:
            if st.button("8m First Fit"):
                jump_to(9.0)
        with controls[3]:
            if st.button("20m Degraded"):
                jump_to(20.0)
        with controls[4]:
            st.slider(
                "Timeline (minutes)",
                min_value=0.0,
                max_value=max(0.1, duration),
                step=0.1,
                key="seek",
                on_change=seek_changed,
            )
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
            st.caption(f"Replay timeline: {st.session_state.cursor:.1f} / {duration:.1f} min at {speed}x playback")
        else:
            view = df
            st.caption(f"Live file: {path.name}")
        if view.empty:
            st.info("Waiting for the first sample.")
            return

        if df.phase.iloc[0] == "reset":
            st.info("Warm-back / reset phase. Sensor monitoring continues; health fitting is paused.")
            render_four_sensor_charts(view)
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
            render_four_sensor_charts(view)
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
            st.error(
                f"Airflow Restriction Likely (degradation detected) · Health {monitor.health:.1f}/100 across 3 consecutive 60s checks."
            )
        elif monitor.health < config.HEALTH_ALERT_THRESHOLD:
            st.warning(f"Cooling slower than baseline · {monitor.rule.count}/3 low-health checks.")
        else:
            st.success("Cooling matches the clean baseline within normal speed tolerance.")

        coil_dt = float(view.return_C.iloc[-1] - view.supply_C.iloc[-1])
        outdoor = view.outdoor_C.iloc[-1]
        current_tau = None if monitor.latest is None else monitor.latest.tau_min
        current_r2 = None if monitor.latest is None else monitor.latest.r2

        hero_left, hero_right = st.columns([1.45, 1.0])
        with hero_left:
            render_interactive_ac_widget(
                supply_c=float(view.supply_C.iloc[-1]),
                return_c=float(view.return_C.iloc[-1]),
                room_c=float(view.room_C.iloc[-1]),
                room_rh=float(view.room_RH.iloc[-1]),
                health=monitor.health,
                rule_active=monitor.rule.active,
            )
        with hero_right:
            render_verdict_console(
                health=monitor.health,
                baseline_tau=baseline.tau_min,
                current_tau=current_tau,
                coil_dt=coil_dt,
                outdoor_c=outdoor,
                r2_val=current_r2,
                rule_active=monitor.rule.active,
                show_guidance=show_guidance,
            )

        st.subheader("How Your Room Cooled vs. Expected Healthy Twin")
        if monitor.latest is not None:
            if show_guidance:
                st.markdown(
                    '<div class="ct-prose">Dashed blue line = expected healthy pull-down speed from your current temperature. '
                    'Shaded gap between curves = lost cooling performance.</div>',
                    unsafe_allow_html=True,
                )
            visible = view[
                (view.elapsed_min >= monitor.latest.start_min)
                & (view.elapsed_min <= monitor.latest.start_min + 15)
            ]
            twin_vals = twin_overlay(baseline, monitor.latest, visible.elapsed_min)
            render_twin_overlay_chart(visible, twin_vals, degraded=monitor.rule.active)
            if show_guidance:
                render_guided_action_bridge(monitor.rule.active, monitor.health, coil_dt)
        else:
            st.info("The twin divergence curve appears once the first 8-minute cooling pull-down window is recorded.")

        with st.expander("Individual Sensor Channels (Supply Vent, Return Intake, Room Temp, Humidity)", expanded=False):
            render_four_sensor_charts(view)

        if st.session_state.notices:
            with st.expander("Alert & Telegram log"):
                for text in st.session_state.notices[-12:]:
                    st.write(text)

    monitor_panel()

with tab_service:
    @st.fragment
    def experiment_panel():
        st.subheader("Guided Experiment: Did Cleaning Actually Help?")
        if show_guidance:
            st.markdown(
                '<div class="ct-prose">Follow one simple test before calling a technician: run your slow session, perform '
                '<strong>one action</strong> (such as cleaning the dust filter), and compare before-and-after cooling under matched weather.</div>',
                unsafe_allow_html=True,
            )
        stepper_slot = st.container()

        guided_action = st.selectbox(
            "Step 3 · Action tested",
            [
                "Filter cleaned (air-path intervention)",
                "Intake grille / fan louvers cleared",
                "Technician service visit completed",
            ],
            key="guided_action",
        )
        confirmed = st.checkbox(
            "I confirm the same AC, fan setting, doors/windows, occupancy and comparable solar conditions",
            key="conditions_confirmed",
        )

        results_slot = st.container()

        with st.expander("Session Recordings, Weather Normalization & Cost Inputs", expanded=False):
            report_paths = []
            selected_phases = set()
            selectors = st.columns(3)
            for column, phase in zip(selectors, ("clean1", "blocked", "clean2")):
                options = phase_files(files, phase, fake)
                with column:
                    choice = (
                        st.selectbox(
                            PHASE_LABELS[phase],
                            options,
                            format_func=lambda p: p.name,
                            key=f"report_{phase}",
                        )
                        if options
                        else None
                    )
                    if choice:
                        report_paths.append(choice)
                        selected_phases.add(phase)
                    else:
                        st.caption(f"No {phase} run available yet.")

            estimate_fields = st.columns(4)
            kw = estimate_fields[0].number_input(
                "AC nameplate kW (0 = unknown)",
                0.0,
                50.0,
                float(config.AC_NAMEPLATE_KW or 0),
                step=0.1,
            )
            tariff = estimate_fields[1].number_input(
                "Tariff ₹/kWh (0 = unknown)",
                0.0,
                100.0,
                float(config.TARIFF_RS_PER_KWH or 0),
                step=0.5,
            )
            target = estimate_fields[2].number_input("Estimate target °C", 16.0, 35.0, 26.0, step=0.5)
            setpoint = estimate_fields[3].number_input(
                "AC setpoint °C (0 = unknown)",
                0.0,
                35.0,
                float(config.SETPOINT_C or 0),
                step=1.0,
            )
            raw_weather_folder = st.text_input(
                "Before-service weather training folder (optional)",
                value=str(folder / "weather"),
            )
            weather_folder = resolve_safe_folder(raw_weather_folder, folder / "weather")
            weather_options = phase_files(run_paths(weather_folder), "blocked", fake)
            weather_paths = st.multiselect(
                "Weather training recordings",
                weather_options,
                format_func=lambda p: p.name,
            )

        assessment = None
        with results_slot:
            if len(report_paths) == 3:
                try:
                    assessment = assess_service(
                        report_paths,
                        weather_baselines=weather_paths,
                        setpoint=setpoint or None,
                        conditions_confirmed=confirmed,
                    )
                    raw_pct = assessment.get("raw_improvement_pct")
                    if assessment["status"] == "inconclusive" and not confirmed:
                        pct_note = f"{raw_pct:.1f}% speedup measured so far — " if raw_pct is not None else ""
                        st.info(
                            f"Waiting for condition confirmation: {pct_note}tick the Step 3 checkbox above if both runs used the same fan speed and room setup."
                        )
                    else:
                        badge_fn = getattr(
                            st,
                            {"improved": "success", "not_improved": "warning", "inconclusive": "info"}[assessment["status"]],
                        )
                        badge_fn(assessment["label"])
                    st.markdown("#### Before vs. After Cooling Pull-Down Comparison")
                    render_experiment_curves_chart(report_paths)
                    render_service_deck(assessment, conditions_confirmed=confirmed)
                    if assessment["status"] == "not_improved" or (assessment["status"] == "inconclusive" and confirmed):
                        render_previsit_brief(assessment, guided_action)
                    for reason in assessment["reasons"]:
                        if not confirmed and reason.startswith("Confirm the same AC"):
                            continue
                        st.write(reason)
                    st.caption("Comparison basis: " + assessment["basis"])
                    st.caption(assessment["weather_detail"])
                    cols = st.columns(2)
                    for col, label, key in [
                        (cols[0], "Raw cooling-time improvement", "raw_improvement_pct"),
                        (cols[1], "Weather-normalized improvement", "normalized_improvement_pct"),
                    ]:
                        col.metric(label, "Unavailable" if assessment[key] is None else f"{assessment[key]:.1f}%")
                except (DataError, FitError, ValueError, OSError) as exc:
                    st.info(f"Experiment comparison unavailable: {exc}")

            report_key = (
                tuple((str(p), p.stat().st_mtime_ns) for p in report_paths),
                kw,
                tariff,
                target,
                setpoint,
                confirmed,
                tuple((str(p), p.stat().st_mtime_ns) for p in weather_paths),
            )
            if st.button("Generate report", type="primary", disabled=len(report_paths) != 3):
                try:
                    from report.make_report import build_report

                    st.session_state.report_bytes = build_report(
                        report_paths,
                        kw=kw or None,
                        tariff=tariff or None,
                        target=target,
                        setpoint=setpoint or None,
                        weather_baselines=weather_paths,
                        conditions_confirmed=confirmed,
                    )
                    st.session_state.report_key = report_key
                    st.session_state.report_just_generated = True
                    st.success("Report generated. Download below.")
                except (DataError, FitError, ValueError, OSError, ImportError) as exc:
                    st.error(f"Report needs valid complete runs: {exc}")

            if st.session_state.get("report_key") == report_key and st.session_state.get("report_bytes"):
                animate_receipt = bool(st.session_state.pop("report_just_generated", False))
                render_printer_receipt_ejection(
                    assessment,
                    guided_action,
                    fake,
                    animate=animate_receipt,
                    preloaded=False,
                    conditions_confirmed=confirmed,
                )
                st.download_button(
                    "Download PDF",
                    st.session_state.report_bytes,
                    file_name=("FAKE_" if fake else "") + "ClimaTwin_report.pdf",
                    mime="application/pdf",
                )
            elif len(report_paths) == 3:
                render_printer_receipt_ejection(
                    assessment,
                    guided_action,
                    fake,
                    animate=False,
                    preloaded=True,
                    conditions_confirmed=confirmed,
                )
            st.caption("Cooling-performance proof only; no measured electrical power or internal fault diagnosis.")

        with stepper_slot:
            render_guided_stepper(
                guided_action,
                "clean1" in selected_phases,
                "blocked" in selected_phases,
                "clean2" in selected_phases,
                None if not assessment else assessment.get("status"),
                conditions_confirmed=confirmed,
            )

    experiment_panel()
