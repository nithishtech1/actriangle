"""Guided Experiment workflow, Pre-Visit Brief, and Printer Receipt UI components."""
from html import escape
import streamlit as st


def _extract_verdict_summary(assessment: dict | None) -> tuple[dict | None, dict | None, float | None]:
    """Extract before/after records and primary improvement percentage consistently."""
    if not assessment:
        return None, None, None
    by_phase = {r["phase"]: r for r in assessment.get("records", [])}
    before = by_phase.get("blocked")
    after = by_phase.get("clean2")
    pct = assessment.get("normalized_improvement_pct")
    if pct is None:
        pct = assessment.get("raw_improvement_pct")
    return before, after, pct


def render_guided_action_bridge(rule_active: bool, health: float | None, coil_dt: float) -> None:
    """Render frosted-glass CTA bridge guiding the user smoothly into Guided Experiment."""
    if rule_active or (health is not None and health < 80):
        badge = "RECOMMENDED NEXT STEP · GUIDED EXPERIMENT"
        msg = (
            f"Room cool-down lagged while the supply vent stayed cold ({coil_dt:.1f} °C chill drop). "
            "Open the Guided Experiment tab to clean the filter, compare Before vs. After pace, and export proof."
        )
    else:
        badge = "GUIDED EXPERIMENT READY"
        msg = (
            "Current cool-down matches your healthy benchmark. Open the Guided Experiment tab to compare Before & After "
            "maintenance runs under weather normalization or export a Verified Certificate."
        )

    st.markdown(
        f"""
        <div class="ct-glass-hud" style="margin-top:12px; margin-bottom:14px;">
            <div class="ct-mono" style="font-size:12px; font-weight:700; color:var(--ct-accent); letter-spacing:0.05em;">{escape(badge)}</div>
            <div style="font-size:14px; font-weight:500; color:var(--ct-ink); margin-top:4px; line-height:1.55; max-width:66ch; text-wrap:pretty;">{escape(msg)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_guided_stepper(
    action_label: str,
    has_clean1: bool,
    has_blocked: bool,
    has_clean2: bool,
    status: str | None,
    conditions_confirmed: bool = True,
) -> None:
    """Render high-contrast 4-step Guided Experiment roadmap."""
    if status == "improved":
        outcome_sub = "Verified speedup confirmed!"
    elif status == "not_improved":
        outcome_sub = "No speedup — Technician brief ready"
    elif status == "inconclusive":
        outcome_sub = (
            "Waiting for Step 3 confirmation"
            if not conditions_confirmed
            else "Outdoor weather or setup mismatched"
        )
    else:
        outcome_sub = "Select Step 2 & 3 runs"

    steps = [
        ("Step 1 · Reference", "Healthy Baseline", "Loaded ✓" if has_clean1 else "Optional healthy run", has_clean1),
        ("Step 2 · Before", "Slow Cooling Session", "Loaded ✓" if has_blocked else "Select slow cooling run", has_blocked),
        ("Step 3 · Action", action_label, "Loaded ✓" if has_clean2 else "Select post-action run", has_clean2),
        ("Step 4 · Verdict", "Did Cleaning Help?", outcome_sub, status == "improved"),
    ]
    cards = []
    for num, title, sub, done in steps:
        if num.startswith("Step 4"):
            cls = "ct-step ct-step-good" if status == "improved" else ("ct-step ct-step-active" if status else "ct-step")
        else:
            cls = "ct-step ct-step-done" if done else "ct-step"
        cards.append(
            f'<div class="{cls}">'
            f'<div class="ct-step-num ct-mono">{escape(num)}</div>'
            f'<div class="ct-step-title">{escape(title)}</div>'
            f'<div class="ct-step-sub">{escape(sub)}</div>'
            f'</div>'
        )
    st.markdown(f'<div class="ct-stepper">{"".join(cards)}</div>', unsafe_allow_html=True)


def render_service_deck(assessment: dict, conditions_confirmed: bool = True) -> None:
    """Render side-by-side Before vs. After Guided Experiment comparison deck."""
    before, after, headline = _extract_verdict_summary(assessment)
    if not before or not after:
        return

    norm = assessment.get("normalized_improvement_pct")
    status = assessment.get("status", "inconclusive")
    awaiting_confirm = status == "inconclusive" and not conditions_confirmed

    if headline is None:
        headline_str = "—"
        sub_str = "Match outdoor conditions to compare"
    elif headline > 0:
        headline_str = f"{headline:.1f}% Faster"
        if awaiting_confirm:
            sub_str = "Measured speedup · Tick Step 3 box to verify"
        else:
            sub_str = "Weather-normalized comparison" if norm is not None else "Matched outdoor weather (±1 °C)"
    else:
        headline_str = f"{headline:.1f}% Change"
        sub_str = "No clear cooling speedup observed"

    if status == "improved":
        bridge_style = "background: linear-gradient(145deg, #F0F9FF 0%, #FFFFFF 100%); border-color: #38BDF8;"
        bridge_color = "#0284C7"
        outcome_label = "Verified Improvement"
    elif status == "not_improved":
        bridge_style = "background: linear-gradient(145deg, #FFF7ED 0%, #FFFFFF 100%); border-color: #FB923C;"
        bridge_color = "#C2410C"
        outcome_label = "No Clear Improvement"
    elif awaiting_confirm:
        bridge_style = "background: oklch(97.8% 0.016 75); border-color: oklch(78% 0.08 75);"
        bridge_color = "#B45309"
        outcome_label = "Waiting for Confirmation"
    else:
        bridge_style = "background: #FAF9F6; border-color: #D8D4C9;"
        bridge_color = "#3F3B36"
        outcome_label = "Weather / Setup Mismatch"

    def _rows(rec: dict, phase_tag: str) -> str:
        out_str = "N/A" if rec["outdoor_mean_C"] is None else f"{rec['outdoor_mean_C']:.1f} °C"
        return (
            f'<div class="ct-deck-row"><span>Cool-Down Pace</span><strong class="ct-mono">{rec["tau_min"]:.1f} min</strong></div>'
            f'<div class="ct-deck-row"><span>Vent Chill Drop</span><span class="ct-mono">{rec["temperature_split_C"]:.1f} °C</span></div>'
            f'<div class="ct-deck-row"><span>Starting Room Temp</span><span class="ct-mono">{rec["start_C"]:.1f} °C</span></div>'
            f'<div class="ct-deck-row"><span>Outdoor Ambient</span><span class="ct-mono">{out_str}</span></div>'
            f'<div class="ct-kpi-foot ct-mono" style="margin-top:10px;">Run: {escape(phase_tag)} · Fit R² {rec["r2"]:.3f}</div>'
        )

    st.markdown(
        f"""
        <div class="ct-deck">
            <div class="ct-card">
                <div class="ct-kpi-label" style="margin-bottom:8px;">Before Action</div>
                {_rows(before, "blocked")}
            </div>
            <div class="ct-deck-bridge" style="{bridge_style}">
                <div class="ct-kpi-label" style="color:{bridge_color};">{escape(outcome_label)}</div>
                <div class="ct-kpi-val ct-mono" style="font-size:36px; color:{bridge_color}; margin:8px 0;">{escape(headline_str)}</div>
                <div style="font-size:14px; font-weight:600; color:var(--ct-secondary);">{escape(sub_str)}</div>
            </div>
            <div class="ct-card">
                <div class="ct-kpi-label" style="margin-bottom:8px;">After Action</div>
                {_rows(after, "clean2")}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_previsit_brief(assessment: dict, action_label: str) -> None:
    """Render concise Pre-Visit Technician Evidence Brief when performance did not improve."""
    before, after, pct = _extract_verdict_summary(assessment)
    if not before or not after:
        return
    pct_txt = "unavailable" if pct is None else f"{pct:.1f}%"
    st.markdown(
        f"""
        <div class="ct-brief-card">
            <div class="ct-brief-title">Pre-Visit Technician Evidence Brief (Share Before Service)</div>
            <div style="font-size:14px; color:var(--ct-ink); line-height:1.6; text-wrap:pretty;">
                <strong>What was already tried:</strong> {escape(action_label)}<br>
                <strong>Measured cool-down pace:</strong> {before["tau_min"]:.1f} min before vs. {after["tau_min"]:.1f} min after · Net change: <strong class="ct-mono">{escape(pct_txt)}</strong> ({escape(assessment.get("basis", "unavailable"))})<br>
                <strong>Vent chill drop:</strong> {after["temperature_split_C"]:.1f} °C · Show this brief to a technician so they inspect deeper causes instead of guessing.<br>
                <span style="color:var(--ct-secondary); font-size:12px;">Honest scope: Measures room cooling speed under matched conditions; does not diagnose refrigerant leaks or internal hardware faults.</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_printer_receipt_ejection(
    assessment: dict | None,
    action_label: str,
    fake: bool,
    animate: bool = True,
    preloaded: bool = False,
    conditions_confirmed: bool = True,
) -> None:
    """Render mechanical printer slot with pre-loaded stub or animated thermal receipt ejection."""
    status = "inconclusive" if not assessment else assessment.get("status", "inconclusive")
    awaiting_confirm = status == "inconclusive" and not conditions_confirmed
    if status == "improved":
        stamp_cls, stamp_txt = "ct-receipt-stamp ct-stamp-ok", "VERIFIED IMPROVEMENT"
    elif status == "not_improved":
        stamp_cls, stamp_txt = "ct-receipt-stamp ct-stamp-warn", "PRE-VISIT BRIEF"
    elif awaiting_confirm:
        stamp_cls, stamp_txt = "ct-receipt-stamp ct-stamp-warn", "AWAITING CONFIRMATION"
    else:
        stamp_cls, stamp_txt = "ct-receipt-stamp ct-stamp-info", "INCONCLUSIVE LOG"

    before, after, pct = _extract_verdict_summary(assessment)
    pct_str = "N/A" if pct is None else f"{pct:+.1f}%"
    basis_str = "—" if not assessment else assessment.get("basis", "unavailable")
    tau_pair = f"{before['tau_min']:.1f}m → {after['tau_min']:.1f}m" if before and after else "Pending runs"
    dt_after = f"{after['temperature_split_C']:.1f} °C" if after else "—"
    anim_cls = "ct-receipt-paper ct-receipt-animate" if animate else "ct-receipt-paper"
    mode_tag = "SOFTWARE DEMO" if fake else "VERIFIED CAPTURE"

    if preloaded:
        prompt_tail = (
            "Confirm Step 3 conditions, then click <strong>Generate report</strong>."
            if awaiting_confirm
            else "Click <strong>Generate report</strong> above to eject full certificate."
        )
        body_html = (
            f'<div class="ct-receipt-peek ct-mono">'
            f'PAPER LOADED · Speedup: <strong>{escape(pct_str)}</strong> · {prompt_tail}'
            f'</div>'
        )
    else:
        body_html = (
            f'<div class="{anim_cls}">'
            f'<div class="ct-receipt-head">'
            f'<div>'
            f'<div style="font-family:var(--ct-font-display); font-size:16px; font-weight:700; color:var(--ct-ink);">Guided Experiment Certificate</div>'
            f'<div class="ct-mono" style="font-size:12px; color:var(--ct-secondary);">Action: {escape(action_label)}</div>'
            f'</div>'
            f'<span class="{stamp_cls} ct-mono">{escape(stamp_txt)}</span>'
            f'</div>'
            f'<div class="ct-receipt-row"><span>Cool-Down Pace (Before → After)</span><strong class="ct-mono">{escape(tau_pair)}</strong></div>'
            f'<div class="ct-receipt-row"><span>Net Speedup</span><strong class="ct-mono">{escape(pct_str)}</strong></div>'
            f'<div class="ct-receipt-row"><span>Vent Chill Drop (After)</span><strong class="ct-mono">{escape(dt_after)}</strong></div>'
            f'<div class="ct-receipt-row"><span>Comparison Basis</span><span class="ct-mono">{escape(basis_str)}</span></div>'
            f'<div class="ct-receipt-tear"></div>'
            f'</div>'
        )

    st.markdown(
        f"""
        <div class="ct-printer-wrap">
            <div class="ct-printer-slot">
                <span class="ct-printer-slot-label ct-mono">CLIMATWIN EVIDENCE PRINTER · {escape(mode_tag)}</span>
                <span class="ct-printer-led"></span>
            </div>
            <div class="ct-receipt-viewport">{body_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
