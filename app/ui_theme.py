"""High-contrast UI theme facade, header, thermal stage banner, and Verdict Console."""
from html import escape
import math
import pandas as pd
import streamlit as st

from app.ui_experiment import (
    render_guided_action_bridge,
    render_guided_stepper,
    render_previsit_brief,
    render_printer_receipt_ejection,
    render_service_deck,
)
from app.ui_styles import PALETTE, inject_styles
from app.ui_widgets import (
    render_experiment_curves_chart,
    render_interactive_ac_widget,
    render_sensor_chart,
    render_twin_overlay_chart,
)

__all__ = [
    "PALETTE",
    "inject_styles",
    "render_experiment_curves_chart",
    "render_guided_action_bridge",
    "render_guided_stepper",
    "render_header",
    "render_interactive_ac_widget",
    "render_previsit_brief",
    "render_printer_receipt_ejection",
    "render_sensor_chart",
    "render_service_deck",
    "render_thermal_stage_banner",
    "render_twin_overlay_chart",
    "render_verdict_console",
]

_THERMO_SVG = (
    '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" '
    'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
    'stroke-linejoin="round" aria-hidden="true">'
    '<path d="M14 4v10.54a4 4 0 1 1-4 0V4a2 2 0 0 1 4 0Z"/></svg>'
)


def _tip(text: str) -> str:
    """Render accessible ? hover tooltip badge for metric formulas."""
    safe = escape(text)
    return (
        f'<span class="ct-tip" tabindex="0" aria-label="{safe}">?'
        f'<span class="ct-tip-box">{safe}</span></span>'
    )


def render_header(mode_label: str, status_tone: str) -> None:
    """Render ClimaTwin top brand bar with crisp high-contrast mode badge."""
    pill_cls = (
        "ct-pill ct-pill-live"
        if status_tone == "live"
        else ("ct-pill ct-pill-warn" if status_tone == "warn" else "ct-pill")
    )
    st.markdown(
        f"""
        <div class="ct-header">
            <div class="ct-brand">
                <div class="ct-logo">{_THERMO_SVG}</div>
                <div>
                    <div class="ct-brand-title">ClimaTwin</div>
                    <div class="ct-brand-sub">Home Split-AC Digital Twin &amp; Guided Maintenance Experiment</div>
                </div>
            </div>
            <div class="{pill_cls} ct-mono">
                <span class="ct-dot"></span>
                <span>{escape(mode_label)}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_thermal_stage_banner(
    health: float | None,
    current_tau: float | None,
    baseline_tau: float,
    coil_dt: float,
    rule_active: bool,
) -> None:
    """Render warm-to-cool shifting hero strip explaining current cooling behavior at a glance."""
    if rule_active or (health is not None and health < 80):
        stage_cls = "ct-stage ct-stage-warm"
        tag = "AIRFLOW BOTTLENECK · ROOM COOLING SLOWED"
        headline = (
            f"Supply vent blows cold ({coil_dt:.1f} °C chill drop), yet room cool-down slowed to {current_tau:.1f}m vs normal {baseline_tau:.1f}m"
            if current_tau is not None
            else f"Vent chill drop holds at {coil_dt:.1f} °C while room response lags normal pace"
        )
    elif health is not None:
        stage_cls = "ct-stage ct-stage-cool"
        tag = "NORMAL COOLING · CLEAR AIRFLOW"
        pace_note = f"{current_tau:.1f}m vs normal {baseline_tau:.1f}m" if current_tau is not None else f"normal {baseline_tau:.1f}m"
        headline = f"Cold vent ({coil_dt:.1f} °C chill drop) cools mid-room on pace ({pace_note})"
    else:
        stage_cls = "ct-stage ct-stage-neutral"
        tag = "WARMING UP TWIN FIT"
        headline = f"Measuring first 8 minutes of pull-down against {baseline_tau:.1f}m healthy baseline (Vent chill {coil_dt:.1f} °C)"

    st.markdown(
        f"""
        <div class="{stage_cls}">
            <div>
                <div class="ct-mono" style="font-size:12px; font-weight:700; letter-spacing:0.04em; color:#3F3B36;">{escape(tag)}</div>
                <div style="font-family:var(--ct-font-display); font-size:17px; font-weight:700; color:#141413; margin-top:3px;">{escape(headline)}</div>
            </div>
            <div class="ct-glass-hud ct-mono" style="padding:8px 14px; font-size:13px; font-weight:700; color:#141413; white-space:nowrap;">
                Vent Chill: {coil_dt:.1f}°C &nbsp;|&nbsp; Healthy Pace: {baseline_tau:.1f}m
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_verdict_console(
    health: float | None,
    baseline_tau: float,
    current_tau: float | None,
    coil_dt: float | None,
    outdoor_c: float | None,
    r2_val: float | None,
    rule_active: bool,
    show_guidance: bool = True,
) -> None:
    """Render unified right-hand Verdict Console: Health dial, Cold Outlet vs Slow Room metrics, modular type."""
    arc_len = 204.2  # pi * 65
    if health is None or not math.isfinite(health):
        pct = 0.0
        stroke_color = "#BDB7AA"
        score_text = "—"
        console_cls = "ct-card"
        verdict_title = "Collecting Initial Fit"
        verdict_color = PALETTE["secondary"]
        explain = "Once 8 minutes of continuous cooling are captured, ClimaTwin compares your current cool-down pace against the healthy baseline."
    else:
        pct = max(0.0, min(100.0, float(health)))
        score_text = f"{pct:.0f}"
        if rule_active:
            stroke_color = PALETTE["bad"]
            console_cls = "ct-card ct-console-warm"
            verdict_title = "Airflow Restriction Likely"
            verdict_color = PALETTE["bad"]
            explain = "Room cool-down stayed below 80/100 while the vent remained cold. Test cleaning the filter in Guided Experiment."
        elif pct < 80:
            stroke_color = PALETTE["warn"]
            console_cls = "ct-card ct-console-warm"
            verdict_title = "Slower Than Healthy Pace"
            verdict_color = PALETTE["warn"]
            explain = "Cooling pace dipped below 80/100; tracking consecutive 60s checks to confirm sustained airflow lag."
        else:
            stroke_color = PALETTE["ok"]
            console_cls = "ct-card ct-console-cool"
            verdict_title = "Healthy Cooling Pace"
            verdict_color = PALETTE["ok"]
            explain = "Mid-room cool-down matches your healthy baseline speed with strong air circulation."

    offset = arc_len * (1.0 - pct / 100.0)
    if current_tau is None:
        speed_val = "Awaiting fit"
        speed_foot = f"Normal pace {baseline_tau:.1f}m"
    else:
        pct_diff = (current_tau - baseline_tau) / baseline_tau * 100.0
        if pct_diff > 5.0:
            speed_val = f"{pct_diff:.0f}% Slower"
        elif pct_diff < -5.0:
            speed_val = f"{-pct_diff:.0f}% Faster"
        else:
            speed_val = "On Pace"
        speed_foot = f"{current_tau:.1f}m vs normal {baseline_tau:.1f}m"

    dt_val = "—" if coil_dt is None else f"{coil_dt:.1f} °C"
    if coil_dt is None:
        dt_foot = "Intake to vent drop"
    elif coil_dt >= 5.0:
        dt_foot = "Drop · Coil Cold"
    elif coil_dt >= 0.0:
        dt_foot = "Mild intake−vent drop"
    else:
        dt_foot = "No cooling drop"
    out_val = "Unavailable" if outdoor_c is None or pd.isna(outdoor_c) else f"{float(outdoor_c):.1f} °C"
    r2_txt = "—" if r2_val is None else f"Fit R² {r2_val:.3f}"

    tip_gauge = _tip("Health = min(100, 100 × τ_baseline / τ_now). Alerts when < 80 across 3 consecutive checks.") if show_guidance else ""
    tip_split = _tip("Cold Vent (Return − Supply) proves the cooling coil chills; slow room cool-down pace (τ) exposes choked airflow.") if show_guidance else ""
    explain_html = (
        f'<div style="font-size:14px; color:var(--ct-secondary); line-height:1.55; text-wrap:pretty; max-width:44ch; margin-top:6px;">{escape(explain)}</div>'
        if show_guidance
        else ""
    )

    st.markdown(
        f"""
        <div class="{console_cls}" style="height:100%;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                <span class="ct-kpi-label">Cooling Verdict Console</span>
                {tip_gauge}
            </div>
            <div class="ct-verdict-row">
                <svg width="166" height="104" viewBox="0 0 166 104" role="img" aria-label="Health score {escape(score_text)} of 100">
                    <path d="M 18 86 A 65 65 0 0 1 148 86" fill="none" stroke="#E2DFD7" stroke-width="13" stroke-linecap="round"/>
                    <path d="M 18 86 A 65 65 0 0 1 148 86" fill="none" stroke="{stroke_color}" stroke-width="13"
                          stroke-linecap="round" stroke-dasharray="{arc_len:.2f}" stroke-dashoffset="{offset:.2f}"
                          style="transition: stroke-dashoffset 280ms cubic-bezier(0.22, 1, 0.36, 1), stroke 220ms ease;"/>
                    <text x="83" y="72" text-anchor="middle" class="ct-mono" font-size="36" font-weight="700" fill="#141413">{escape(score_text)}</text>
                    <text x="83" y="94" text-anchor="middle" font-size="12" font-weight="600" fill="#3F3B36">/ 100 Health</text>
                </svg>
                <div style="flex:1; min-width:160px;">
                    <div style="font-family:var(--ct-font-display); font-size:20px; font-weight:700; letter-spacing:-0.02em; color:{verdict_color}; line-height:1.25; text-wrap:balance;">{escape(verdict_title)}</div>
                    {explain_html}
                </div>
            </div>
            <div class="ct-split-metrics">
                <div class="ct-mini-stat">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span class="ct-kpi-label">Room Cool-Down Pace</span>
                        {tip_split}
                    </div>
                    <div class="ct-kpi-val">{escape(speed_val)}</div>
                    <div class="ct-kpi-foot ct-mono">{escape(speed_foot)}</div>
                </div>
                <div class="ct-mini-stat">
                    <div class="ct-kpi-label">Vent Output Chill</div>
                    <div class="ct-kpi-val ct-mono">{escape(dt_val)}</div>
                    <div class="ct-kpi-foot">{escape(dt_foot)}</div>
                </div>
            </div>
            <div class="ct-mono" style="margin-top:14px; padding-top:10px; border-top:1px solid var(--ct-border); font-size:12px; font-weight:600; color:var(--ct-secondary); display:flex; justify-content:space-between;">
                <span>Outdoor: {escape(out_val)}</span>
                <span>{escape(r2_txt)}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
