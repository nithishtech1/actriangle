"""Interactive HTML5 room airflow simulation and high-contrast Altair charts."""
import base64
from html import escape
import json
from pathlib import Path
import altair as alt
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from app.ui_styles import PALETTE
from twin.data import DataError, read_run
from twin.fit_tau import FitError, detect_cooling_start


def _load_iframe_fonts_css() -> str:
    """Inline cached base64 WOFF2 fonts so srcDoc iframes work offline without CORS issues."""
    fonts_dir = Path(__file__).resolve().parent / "static" / "fonts"
    specs = (
        ("Inter", "inter.woff2", "400 700"),
        ("Space Grotesk", "space-grotesk.woff2", "600 700"),
        ("JetBrains Mono", "jetbrains-mono.woff2", "500 700"),
    )
    rules = []
    for family, fname, weight in specs:
        font_path = fonts_dir / fname
        if not font_path.exists():
            continue
        b64 = base64.b64encode(font_path.read_bytes()).decode("ascii")
        rules.append(
            f"@font-face{{font-family:'{family}';font-style:normal;font-weight:{weight};"
            f"src:url('data:font/woff2;base64,{b64}') format('woff2');}}"
        )
    return "\n".join(rules)


_IFRAME_FONTS_CSS = _load_iframe_fonts_css()


def render_interactive_ac_widget(
    supply_c: float,
    return_c: float,
    room_c: float,
    room_rh: float,
    health: float | None,
    rule_active: bool,
) -> None:
    """Render 60fps interactive Split-AC & room airflow Digital Twin simulation."""
    is_restricted = bool(rule_active or (health is not None and health < 80))
    payload = json.dumps(
        {
            "supply": round(float(supply_c), 1),
            "ret": round(float(return_c), 1),
            "room": round(float(room_c), 1),
            "rh": round(float(room_rh), 1),
            "dt": round(float(return_c - supply_c), 1),
            "restricted": is_restricted,
        }
    )
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
      {_IFRAME_FONTS_CSS}
      * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', -apple-system, sans-serif; -webkit-font-smoothing: antialiased; }}
      body {{ background: transparent; color: #141413; }}
      .twin-shell {{
        background: oklch(99.5% 0.002 85);
        border: 1px solid oklch(87.0% 0.009 80);
        border-radius: 16px;
        padding: 16px;
        display: flex;
        flex-direction: column;
        gap: 12px;
        transition: background 550ms cubic-bezier(0.22, 1, 0.36, 1), border-color 400ms ease;
      }}
      .twin-shell.warm {{
        background: linear-gradient(155deg, oklch(99.5% 0.002 85) 0%, oklch(96.8% 0.024 42) 100%);
        border-color: oklch(87.0% 0.009 80);
        border-left: 4px solid oklch(63.5% 0.190 42);
      }}
      .twin-shell.cool {{
        background: linear-gradient(155deg, oklch(99.5% 0.002 85) 0%, oklch(96.8% 0.022 228) 100%);
        border-color: oklch(87.0% 0.009 80);
        border-left: 4px solid oklch(58.5% 0.145 228);
      }}
      .stage-top {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 8px;
        flex-wrap: wrap;
      }}
      .stage-title {{
        font-family: 'Space Grotesk', sans-serif;
        font-size: 16px;
        font-weight: 700;
        letter-spacing: -0.02em;
        color: #141413;
      }}
      .mode-switch {{
        display: inline-flex;
        gap: 4px;
        background: #EAE7DF;
        padding: 4px;
        border-radius: 10px;
        border: 1px solid #D8D4C9;
      }}
      .m-btn {{
        border: none;
        background: transparent;
        padding: 6px 12px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 600;
        color: #3F3B36;
        cursor: pointer;
        transition: background-color 140ms ease, color 140ms ease;
      }}
      .m-btn.active {{
        background: #FFFFFF;
        color: #141413;
        box-shadow: 0 1px 3px rgba(20, 20, 19, 0.14);
      }}
      .canvas-box {{
        position: relative;
        width: 100%;
        height: 266px;
        border-radius: 10px;
        border: 1px solid #D8D4C9;
        overflow: hidden;
        background: #F6F5F0;
      }}
      canvas {{
        width: 100%;
        height: 100%;
        display: block;
      }}
      .hud-overlay {{
        position: absolute;
        top: 10px;
        right: 10px;
        background: rgba(255, 255, 255, 0.88);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.96);
        box-shadow: 0 6px 16px rgba(20, 20, 19, 0.08);
        border-radius: 10px;
        padding: 8px 12px;
        text-align: right;
        pointer-events: none;
      }}
      .hud-k {{
        font-size: 12px;
        font-weight: 700;
        color: #3F3B36;
        letter-spacing: 0.04em;
        text-transform: uppercase;
      }}
      .hud-v {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 16px;
        font-weight: 700;
        font-variant-numeric: tabular-nums;
        color: #141413;
        margin-top: 2px;
      }}
      .bottom-strip {{
        display: grid;
        grid-template-columns: auto 1fr;
        gap: 12px;
        align-items: center;
        background: rgba(255, 255, 255, 0.88);
        border: 1px solid #E2DFD7;
        border-radius: 10px;
        padding: 10px 12px;
      }}
      @media (max-width: 560px) {{ .bottom-strip {{ grid-template-columns: 1fr; }} }}
      .probe-tabs {{
        display: flex;
        gap: 6px;
        flex-wrap: wrap;
      }}
      .p-btn {{
        border: 1px solid #D8D4C9;
        background: #FFFFFF;
        padding: 6px 11px;
        border-radius: 8px;
        font-size: 12px;
        font-weight: 600;
        color: #141413;
        cursor: pointer;
        transition: background-color 140ms ease, border-color 140ms ease, color 140ms ease;
      }}
      .p-btn.active {{
        border-color: #141413;
        background: #141413;
        color: #FFFFFF;
      }}
      .probe-note {{
        font-size: 14px;
        color: #3F3B36;
        line-height: 1.5;
        text-wrap: pretty;
      }}
      .probe-note strong {{
        color: #141413;
        font-family: 'JetBrains Mono', monospace;
      }}
    </style>
    </head>
    <body>
    <div id="twinShell" class="twin-shell">
      <div class="stage-top">
        <span class="stage-title">Interactive Room Airflow Twin</span>
        <div class="mode-switch" role="group" aria-label="Simulation preview mode">
          <button class="m-btn active" id="btnLive" onclick="setPreview('live')">Live Run</button>
          <button class="m-btn" id="btnChoked" onclick="setPreview('choked')">Choked Filter</button>
          <button class="m-btn" id="btnClean" onclick="setPreview('clean')">Clean Flow</button>
        </div>
      </div>

      <div class="canvas-box">
        <canvas id="airCanvas"></canvas>
        <div class="hud-overlay">
          <div class="hud-k" id="hudTag">Cold Outlet vs. Room</div>
          <div class="hud-v" id="hudVal">—</div>
        </div>
      </div>

      <div class="bottom-strip">
        <div class="probe-tabs">
          <button class="p-btn active" id="pSupply" onclick="pickProbe('supply')">Supply Vent</button>
          <button class="p-btn" id="pReturn" onclick="pickProbe('return')">Return Air</button>
          <button class="p-btn" id="pRoom" onclick="pickProbe('room')">Room DHT11</button>
        </div>
        <div class="probe-note" id="probeNote">—</div>
      </div>
    </div>

    <script>
      const d = {payload};
      let previewMode = 'live';
      let activeProbe = 'supply';
      let restrictedNow = d.restricted;
      let hueNow = restrictedNow ? 42 : 226;
      let mixNow = restrictedNow ? 1.0 : 0.0;

      const canvas = document.getElementById('airCanvas');
      const ctx = canvas.getContext('2d');
      let W = 0, H = 0;

      function resize() {{
        const rect = canvas.parentElement.getBoundingClientRect();
        const dpr = Math.min(window.devicePixelRatio || 1, 2);
        W = rect.width; H = rect.height;
        canvas.width = W * dpr; canvas.height = H * dpr;
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      }}
      window.addEventListener('resize', resize);
      resize();

      const particles = Array.from({{length: 56}}, () => ({{
        x: 120 + Math.random() * 240,
        y: 112 + Math.random() * 90,
        vx: 1.5,
        vy: 0.4,
        life: Math.random(),
        size: 2.3 + Math.random() * 2.2,
      }}));

      function spawnParticle(p) {{
        p.x = 70 + Math.random() * 140;
        p.y = 112 + Math.random() * 6;
        p.life = 0;
        p.vx = restrictedNow ? (0.45 + Math.random() * 0.55) : (2.2 + Math.random() * 1.3);
        p.vy = restrictedNow ? (0.55 + Math.random() * 0.45) : (0.45 + Math.random() * 0.55);
      }}

      function drawScene() {{
        // Continuous OKLCH hue & thermal mix interpolation
        const targetHue = restrictedNow ? 42 : 226;
        const targetMix = restrictedNow ? 1.0 : 0.0;
        hueNow += (targetHue - hueNow) * 0.08;
        mixNow += (targetMix - mixNow) * 0.08;

        ctx.clearRect(0, 0, W, H);

        // Perceptually constant-lightness OKLCH background wash
        const bgGrad = ctx.createLinearGradient(0, 0, W, H);
        bgGrad.addColorStop(0, `oklch(98.2% 0.014 ${{hueNow.toFixed(1)}})`);
        bgGrad.addColorStop(1, `oklch(94.6% 0.032 ${{hueNow.toFixed(1)}})`);
        ctx.fillStyle = bgGrad;
        ctx.fillRect(0, 0, W, H);

        // Whisper-quiet 16px square-dot engineering matrix (purely schematic depth)
        ctx.fillStyle = `oklch(24% 0.015 ${{hueNow.toFixed(1)}} / 0.075)`;
        for (let gx = 16; gx < W - 12; gx += 16) {{
          for (let gy = 16; gy < H - 18; gy += 16) {{
            ctx.fillRect(gx, gy, 1.3, 1.3);
          }}
        }}

        ctx.strokeStyle = 'oklch(83% 0.01 80)';
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.moveTo(16, H - 18);
        ctx.lineTo(W - 16, H - 18);
        ctx.stroke();

        // Split AC indoor unit cleanly spaced from probe dots
        const acX = 24, acY = 44, acW = 220, acH = 66;
        ctx.fillStyle = '#FFFFFF';
        ctx.strokeStyle = '#141413';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.roundRect(acX, acY, acW, acH, 10);
        ctx.fill();
        ctx.stroke();

        ctx.fillStyle = '#3F3B36';
        ctx.font = '700 10.5px Inter, sans-serif';
        ctx.fillText('INDOOR SPLIT AC EVAPORATOR', acX + 14, acY + 19);

        // Filter bar morphs cleanly along OKLCH hue
        ctx.fillStyle = restrictedNow
          ? `oklch(63% 0.19 ${{hueNow.toFixed(1)}})`
          : 'oklch(91% 0.008 85)';
        ctx.strokeStyle = restrictedNow ? 'oklch(48% 0.16 42)' : 'oklch(62% 0.01 80)';
        ctx.lineWidth = 1.2;
        ctx.beginPath();
        ctx.roundRect(acX + 14, acY + 27, acW - 28, 16, 4);
        ctx.fill();
        ctx.stroke();

        ctx.fillStyle = restrictedNow ? '#FFFFFF' : '#141413';
        ctx.font = '700 10px Inter, sans-serif';
        ctx.fillText(restrictedNow ? 'DUST FILTER CHOKED' : 'CLEAN FILTER · FULL FLOW', acX + 24, acY + 38.5);

        ctx.strokeStyle = '#141413';
        ctx.lineWidth = 2.5;
        ctx.beginPath();
        ctx.moveTo(acX + 24, acY + acH - 8);
        ctx.lineTo(acX + acW - 22, acY + acH - 8);
        ctx.stroke();

        const activeCount = Math.round(56 - mixNow * 34);
        for (let i = 0; i < activeCount; i++) {{
          const p = particles[i];
          p.x += p.vx;
          p.y += p.vy + Math.sin(p.life * 6) * 0.22;
          p.life += 0.017;
          if (restrictedNow && p.x > W * 0.45) p.life += 0.065;
          if (p.x > W - 26 || p.y > H - 22 || p.life > 1.35) spawnParticle(p);

          const alpha = Math.max(0, Math.min(0.88, (1.35 - p.life) * 0.8));
          ctx.fillStyle = `oklch(58% 0.17 ${{hueNow.toFixed(1)}} / ${{alpha.toFixed(2)}})`;
          ctx.beginPath();
          ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
          ctx.fill();
        }}

        // Mid-room DHT11 box
        const rmW = 158, rmH = 58;
        const rmX = Math.max(W - rmW - 20, 268), rmY = H - rmH - 26;
        ctx.fillStyle = '#FFFFFF';
        ctx.strokeStyle = activeProbe === 'room' ? '#EA580C' : '#141413';
        ctx.lineWidth = activeProbe === 'room' ? 2.5 : 1.7;
        ctx.beginPath();
        ctx.roundRect(rmX, rmY, rmW, rmH, 10);
        ctx.fill();
        ctx.stroke();

        ctx.fillStyle = '#141413';
        ctx.font = '700 10.5px Inter, sans-serif';
        ctx.fillText('ROOM ZONE (DHT11)', rmX + 12, rmY + 20);
        ctx.fillStyle = `oklch(50% 0.16 ${{hueNow.toFixed(1)}})`;
        ctx.font = '700 13.5px "JetBrains Mono", monospace';
        ctx.fillText(d.room.toFixed(1) + '°C · ' + d.rh.toFixed(0) + '% RH', rmX + 12, rmY + 41);

        drawNode(124, 24, 'oklch(63% 0.19 42)', 'Return ' + d.ret.toFixed(1) + '°C', activeProbe === 'return');
        drawNode(78, 128, 'oklch(58% 0.15 228)', 'Vent ' + d.supply.toFixed(1) + '°C', activeProbe === 'supply');

        requestAnimationFrame(drawScene);
      }}

      function drawNode(x, y, col, label, selected) {{
        ctx.fillStyle = col;
        ctx.strokeStyle = selected ? '#141413' : '#FFFFFF';
        ctx.lineWidth = selected ? 3 : 2;
        ctx.beginPath();
        ctx.arc(x, y, selected ? 8.5 : 6.5, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();

        ctx.fillStyle = '#141413';
        ctx.font = '700 11.5px "JetBrains Mono", monospace';
        ctx.fillText(label, x + 13, y + 4);
      }}

      function updateText() {{
        const shell = document.getElementById('twinShell');
        shell.className = 'twin-shell ' + (restrictedNow ? 'warm' : 'cool');
        document.getElementById('hudTag').textContent = restrictedNow ? 'COLD VENT · SLOW ROOM' : 'CLEAR AIRFLOW · ON PACE';
        document.getElementById('hudVal').textContent = 'Vent Chill ' + d.dt.toFixed(1) + ' °C';

        const notes = {{
          supply: '<strong>Supply Vent (' + d.supply.toFixed(1) + '°C)</strong> — Blowing ' + d.dt.toFixed(1) + '°C colder than intake air, proving the cooling coil still chills.',
          return: '<strong>Return Intake (' + d.ret.toFixed(1) + '°C)</strong> — Room air returning over the filter slot stays warmer when dust blocks circulation.',
          room: '<strong>Mid-Room DHT11 (' + d.room.toFixed(1) + '°C · ' + d.rh.toFixed(0) + '% RH)</strong> — Placed 1.5 m high; measures how fast the living space cools.'
        }};
        document.getElementById('probeNote').innerHTML = notes[activeProbe];
      }}

      function pickProbe(name) {{
        activeProbe = name;
        ['supply', 'return', 'room'].forEach(k => {{
          document.getElementById('p' + k.charAt(0).toUpperCase() + k.slice(1)).classList.toggle('active', k === name);
        }});
        updateText();
      }}

      function setPreview(mode) {{
        previewMode = mode;
        restrictedNow = (mode === 'choked') ? true : (mode === 'clean' ? false : d.restricted);
        document.getElementById('btnLive').classList.toggle('active', mode === 'live');
        document.getElementById('btnChoked').classList.toggle('active', mode === 'choked');
        document.getElementById('btnClean').classList.toggle('active', mode === 'clean');
        updateText();
      }}

      canvas.addEventListener('click', (e) => {{
        const rect = canvas.getBoundingClientRect();
        const x = e.clientX - rect.left, y = e.clientY - rect.top;
        if (y < 54) pickProbe('return');
        else if (x < rect.width * 0.45 && y < 140) pickProbe('supply');
        else pickProbe('room');
      }});

      updateText();
      requestAnimationFrame(drawScene);
    </script>
    </body>
    </html>
    """
    if hasattr(st, "iframe"):
        st.iframe(html_code, height=455, alt="Interactive Room Airflow Twin")
    else:
        components.html(html_code, height=455)


def _style_chart(chart: alt.Chart) -> alt.Chart:
    """Apply accessible, high-contrast ClimaTwin styling to Altair charts."""
    return (
        chart.configure(background="transparent")
        .configure_view(strokeWidth=0, fill="transparent")
        .configure_axis(
            labelColor=PALETTE["secondary"],
            titleColor=PALETTE["ink"],
            gridColor=PALETTE["grid"],
            domainColor=PALETTE["border"],
            tickColor=PALETTE["border"],
            labelFont="JetBrains Mono, monospace",
            titleFont="Inter, sans-serif",
            labelFontSize=12,
            titleFontSize=14,
            titleFontWeight=600,
        )
        .configure_legend(
            labelColor=PALETTE["ink"],
            labelFont="Inter, sans-serif",
            labelFontSize=14,
            labelFontWeight=600,
        )
    )


def render_twin_overlay_chart(visible_df: pd.DataFrame, twin_values, degraded: bool) -> None:
    """Render clear, high-contrast comparison of actual room temp vs Healthy Twin."""
    frame = pd.DataFrame(
        {
            "elapsed_min": visible_df["elapsed_min"].to_numpy(),
            "Actual Room Temp (°C)": visible_df["room_C"].to_numpy(),
            "Expected Healthy Twin (°C)": twin_values,
        }
    )
    frame["Cooling Lag (°C)"] = frame["Actual Room Temp (°C)"] - frame["Expected Healthy Twin (°C)"]
    rec_color = PALETTE["accent"] if degraded else PALETTE["ink"]
    band_color = PALETTE["accent"] if degraded else PALETTE["cool"]

    hover = alt.selection_point(
        fields=["elapsed_min"],
        nearest=True,
        on="pointerover",
        empty=False,
    )
    band = (
        alt.Chart(frame)
        .mark_area(opacity=0.16, color=band_color)
        .encode(
            x=alt.X("elapsed_min:Q", title="Minutes since compressor start"),
            y=alt.Y("Expected Healthy Twin (°C):Q", scale=alt.Scale(zero=False), title="Mid-Room Temperature (°C)"),
            y2="Actual Room Temp (°C):Q",
        )
    )
    melted = frame.melt(
        id_vars=["elapsed_min"],
        value_vars=["Expected Healthy Twin (°C)", "Actual Room Temp (°C)"],
        var_name="Series",
        value_name="Temp",
    )
    lines = (
        alt.Chart(melted)
        .mark_line(strokeWidth=3.0)
        .encode(
            x=alt.X("elapsed_min:Q", title="Minutes since compressor start"),
            y=alt.Y("Temp:Q", scale=alt.Scale(zero=False), title="Mid-Room Temperature (°C)"),
            color=alt.Color(
                "Series:N",
                scale=alt.Scale(
                    domain=["Expected Healthy Twin (°C)", "Actual Room Temp (°C)"],
                    range=[PALETTE["cool"], rec_color],
                ),
                legend=alt.Legend(orient="top", title=None, labelLimit=320),
            ),
            strokeDash=alt.StrokeDash(
                "Series:N",
                scale=alt.Scale(
                    domain=["Expected Healthy Twin (°C)", "Actual Room Temp (°C)"],
                    range=[[6, 4], [1, 0]],
                ),
                legend=None,
            ),
        )
    )
    rule = (
        alt.Chart(frame)
        .mark_rule(color=PALETTE["secondary"], strokeDash=[3, 3])
        .encode(
            x="elapsed_min:Q",
            opacity=alt.condition(hover, alt.value(0.95), alt.value(0)),
            tooltip=[
                alt.Tooltip("elapsed_min:Q", title="Minute", format=".1f"),
                alt.Tooltip("Actual Room Temp (°C):Q", title="Actual Room (°C)", format=".2f"),
                alt.Tooltip("Expected Healthy Twin (°C):Q", title="Healthy Twin (°C)", format=".2f"),
                alt.Tooltip("Cooling Lag (°C):Q", title="Cooling Deficit (°C)", format="+.2f"),
            ],
        )
        .add_params(hover)
    )
    st.altair_chart(_style_chart((band + lines + rule).properties(height=320)), width="stretch")


def render_experiment_curves_chart(report_paths: list[Path]) -> None:
    """Render overlaid Before Action (blocked) vs After Action (clean2) cooling pull-down curves."""
    series = []
    for path in report_paths:
        try:
            df = read_run(path)
            phase = str(df.phase.iloc[0])
            if phase not in ("blocked", "clean2"):
                continue
            onset = detect_cooling_start(df.elapsed_min.to_numpy(), df.room_C.to_numpy())
            trimmed = df.iloc[onset:].copy()
            trimmed["t_norm"] = trimmed.elapsed_min - float(trimmed.elapsed_min.iloc[0])
            trimmed = trimmed[trimmed["t_norm"] <= 15.2]
            label = "Before Action (Problem)" if phase == "blocked" else "After Action (Cleaned)"
            for _, row in trimmed.iterrows():
                series.append({"min": float(row.t_norm), "Room (°C)": float(row.room_C), "Phase": label})
        except (DataError, FitError, OSError, ValueError):
            continue

    if len({row["Phase"] for row in series}) < 2:
        return

    chart_df = pd.DataFrame(series)
    chart = (
        alt.Chart(chart_df)
        .mark_line(strokeWidth=3.0)
        .encode(
            x=alt.X("min:Q", title="Minutes after cooling started (first 15 min aligned)"),
            y=alt.Y("Room (°C):Q", scale=alt.Scale(zero=False), title="Mid-Room Temp (°C)"),
            color=alt.Color(
                "Phase:N",
                scale=alt.Scale(
                    domain=["Before Action (Problem)", "After Action (Cleaned)"],
                    range=[PALETTE["accent"], PALETTE["cool"]],
                ),
                legend=alt.Legend(orient="top", title=None, labelLimit=320),
            ),
            strokeDash=alt.StrokeDash(
                "Phase:N",
                scale=alt.Scale(
                    domain=["Before Action (Problem)", "After Action (Cleaned)"],
                    range=[[5, 4], [1, 0]],
                ),
                legend=None,
            ),
            tooltip=[
                alt.Tooltip("Phase:N", title="Session"),
                alt.Tooltip("min:Q", title="Cooling Min", format=".1f"),
                alt.Tooltip("Room (°C):Q", title="Temp (°C)", format=".2f"),
            ],
        )
        .properties(height=280)
    )
    st.altair_chart(_style_chart(chart), width="stretch")


def render_sensor_chart(view_df: pd.DataFrame, column: str, title: str, unit: str, color: str) -> None:
    """Render compact high-contrast Altair sensor channel telemetry chart."""
    latest_val = view_df[column].iloc[-1]
    val_str = "—" if pd.isna(latest_val) else f"{float(latest_val):.1f} {unit}"
    st.markdown(
        f'<div class="ct-sensor-head">'
        f'<span style="font-size:14px; font-weight:700; color:#141413;">{escape(title)}</span>'
        f'<span class="ct-mono" style="font-size:14px; font-weight:700; color:#EA580C;">{escape(val_str)}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    data = view_df[["elapsed_min", column]].rename(columns={column: "value"})
    area = (
        alt.Chart(data)
        .mark_area(color=color, opacity=0.12, line={"color": color, "strokeWidth": 2.2})
        .encode(
            x=alt.X("elapsed_min:Q", title="Elapsed minutes"),
            y=alt.Y("value:Q", scale=alt.Scale(zero=False), title=unit),
            tooltip=[
                alt.Tooltip("elapsed_min:Q", title="Min", format=".1f"),
                alt.Tooltip("value:Q", title=title, format=".2f"),
            ],
        )
        .properties(height=185)
    )
    st.altair_chart(_style_chart(area), width="stretch")
