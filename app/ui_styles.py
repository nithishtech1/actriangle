"""Design tokens, local webfont loading, and modular typography CSS for ClimaTwin."""
import streamlit as st

PALETTE = {
    "bg": "#F4F3EF",
    "surface": "#FFFFFF",
    "surface_alt": "#EAE7DF",
    "ink": "#141413",
    "secondary": "#3F3B36",
    "muted": "#57534E",
    "border": "#D8D4C9",
    "grid": "#E8E4DA",
    "accent": "#EA580C",
    "cool": "#0284C7",
    "ok": "#15803D",
    "warn": "#B45309",
    "bad": "#DC2626",
}


def inject_styles() -> None:
    """Inject local @font-face rules and enforce the 12/14/16/20/28/36 modular type scale."""
    css_block = """<style>
@font-face {
    font-family: 'Inter';
    font-style: normal;
    font-weight: 400 700;
    font-display: swap;
    src: url('/app/static/fonts/inter.woff2') format('woff2');
}
@font-face {
    font-family: 'Space Grotesk';
    font-style: normal;
    font-weight: 600 700;
    font-display: swap;
    src: url('/app/static/fonts/space-grotesk.woff2') format('woff2');
}
@font-face {
    font-family: 'JetBrains Mono';
    font-style: normal;
    font-weight: 500 700;
    font-display: swap;
    src: url('/app/static/fonts/jetbrains-mono.woff2') format('woff2');
}
:root {
    --ct-bg: oklch(96.4% 0.006 85);
    --ct-surface: oklch(99.5% 0.002 85);
    --ct-recessed: oklch(93.2% 0.008 85);
    --ct-ink: oklch(19.5% 0.008 60);
    --ct-secondary: oklch(34.0% 0.010 60);
    --ct-muted: oklch(44.0% 0.008 60);
    --ct-border: oklch(87.0% 0.009 80);
    --ct-accent: oklch(63.5% 0.190 42);
    --ct-cool: oklch(58.5% 0.145 232);
    --ct-font-display: 'Space Grotesk', 'Inter', -apple-system, sans-serif;
    --ct-font-body: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    --ct-font-mono: 'JetBrains Mono', ui-monospace, SFMono-Regular, monospace;
    --ct-fs-xs: 12px;
    --ct-fs-sm: 14px;
    --ct-fs-base: 16px;
    --ct-fs-lg: 20px;
    --ct-fs-xl: 28px;
    --ct-fs-2xl: 36px;
    --ct-ease: cubic-bezier(0.22, 1, 0.36, 1);
}
#MainMenu, footer, [data-testid="stDecoration"], [data-testid="stStatusWidget"], [data-testid="stToolbar"] {
    display: none !important;
}
header[data-testid="stHeader"] {
    background: transparent !important;
    height: 0.4rem !important;
}
html {
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    text-rendering: optimizeLegibility;
}
html, body, .stApp, [data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] li, [data-testid="stWidgetLabel"] p {
    font-family: var(--ct-font-body) !important;
    color: var(--ct-ink);
}
.stApp {
    background-color: var(--ct-bg);
}
.block-container {
    padding-top: 1.1rem !important;
    padding-bottom: 2.5rem;
    max-width: 1360px;
}
h1, h2, h3, .ct-title, .ct-brand-title {
    font-family: var(--ct-font-display) !important;
    text-wrap: balance;
    letter-spacing: -0.025em;
    line-height: 1.2;
    color: var(--ct-ink) !important;
}
h2, [data-testid="stSubheader"] {
    font-size: var(--ct-fs-lg) !important;
    font-weight: 700 !important;
}
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li {
    font-size: var(--ct-fs-sm);
    line-height: 1.6;
    text-wrap: pretty;
    color: var(--ct-ink);
}
.ct-prose {
    max-width: 66ch;
    font-size: var(--ct-fs-sm);
    line-height: 1.6;
    text-wrap: pretty;
    color: var(--ct-secondary);
}
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {
    font-size: var(--ct-fs-sm) !important;
    line-height: 1.55 !important;
    text-wrap: pretty;
    color: var(--ct-secondary) !important;
    opacity: 1 !important;
    max-width: 68ch;
}
.ct-mono {
    font-family: var(--ct-font-mono) !important;
    font-variant-numeric: tabular-nums;
}
[data-testid="stSliderThumbValue"],
[data-testid="stSliderTickBarMin"],
[data-testid="stSliderTickBarMax"] {
    white-space: nowrap !important;
    width: auto !important;
    min-width: max-content !important;
    font-family: var(--ct-font-mono) !important;
    font-size: var(--ct-fs-xs) !important;
    line-height: 1.2 !important;
}
[data-testid="stSidebar"] {
    background-color: var(--ct-recessed);
    border-right: 1px solid var(--ct-border);
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h2,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3 {
    font-size: var(--ct-fs-base) !important;
    font-weight: 700 !important;
    letter-spacing: -0.015em !important;
    color: var(--ct-ink) !important;
}
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
    font-size: var(--ct-fs-sm) !important;
    font-weight: 600 !important;
    color: var(--ct-ink) !important;
}
[data-testid="stAlert"] {
    background-color: var(--ct-surface) !important;
    border: 1px solid var(--ct-border) !important;
    border-left-width: 4px !important;
    border-radius: 12px !important;
    padding: 10px 16px !important;
    box-shadow: 0 2px 6px rgba(20, 20, 19, 0.04) !important;
    margin-bottom: 10px !important;
}
[data-testid="stAlert"] p {
    font-size: var(--ct-fs-sm) !important;
    font-weight: 600 !important;
    line-height: 1.5 !important;
    text-wrap: pretty;
    color: var(--ct-ink) !important;
}
.ct-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    padding: 14px 20px;
    background: var(--ct-surface);
    border: 1px solid var(--ct-border);
    border-radius: 16px;
    box-shadow: 0 2px 6px rgba(20, 20, 19, 0.04);
    margin-bottom: 12px;
}
.ct-brand {
    display: flex;
    align-items: center;
    gap: 14px;
}
.ct-logo {
    width: 40px;
    height: 40px;
    border-radius: 10px;
    background: var(--ct-ink);
    color: #FFFFFF;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}
.ct-brand-title {
    font-size: var(--ct-fs-lg);
    font-weight: 700;
    line-height: 1.15;
}
.ct-brand-sub {
    font-size: var(--ct-fs-sm);
    font-weight: 500;
    color: var(--ct-secondary);
    margin-top: 2px;
    line-height: 1.4;
}
.ct-pill {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 6px 14px;
    border-radius: 999px;
    font-size: var(--ct-fs-xs);
    font-weight: 700;
    letter-spacing: 0.05em;
    border: 1px solid var(--ct-border);
    background: var(--ct-bg);
    color: var(--ct-ink);
    white-space: nowrap;
}
.ct-pill-live {
    background: oklch(96.5% 0.025 148);
    border-color: oklch(80% 0.08 148);
    color: oklch(38% 0.12 148);
}
.ct-pill-warn {
    background: oklch(96.8% 0.024 42);
    border-color: oklch(82% 0.09 42);
    color: oklch(44% 0.14 42);
}
.ct-dot {
    width: 8px;
    height: 8px;
    border-radius: 999px;
    background: currentColor;
}
.ct-card {
    background: var(--ct-surface);
    border: 1px solid var(--ct-border);
    border-radius: 16px;
    padding: 20px;
    box-shadow: 0 2px 8px rgba(20, 20, 19, 0.04);
    transition: border-color 180ms var(--ct-ease), box-shadow 180ms var(--ct-ease), background 500ms var(--ct-ease);
}
.ct-console-warm {
    background: linear-gradient(155deg, oklch(99.5% 0.002 85) 0%, oklch(96.8% 0.024 42) 100%);
    border-color: var(--ct-border);
    border-left: 4px solid var(--ct-accent);
}
.ct-console-cool {
    background: linear-gradient(155deg, oklch(99.5% 0.002 85) 0%, oklch(96.8% 0.022 228) 100%);
    border-color: var(--ct-border);
    border-left: 4px solid var(--ct-cool);
}
.ct-verdict-row {
    display: flex;
    align-items: center;
    gap: 18px;
    flex-wrap: wrap;
}
.ct-split-metrics {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
    margin-top: 16px;
}
.ct-mini-stat {
    background: rgba(255, 255, 255, 0.88);
    border: 1px solid var(--ct-border);
    border-radius: 10px;
    padding: 12px 14px;
}
.ct-kpi-label {
    font-size: var(--ct-fs-xs);
    font-weight: 700;
    color: var(--ct-secondary);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    line-height: 1.3;
}
.ct-kpi-val {
    font-family: var(--ct-font-display);
    font-size: var(--ct-fs-xl);
    font-weight: 700;
    letter-spacing: -0.02em;
    color: var(--ct-ink);
    line-height: 1.15;
    margin-top: 4px;
}
.ct-mini-stat .ct-kpi-val {
    font-size: 22px;
    white-space: nowrap;
}
.ct-kpi-foot {
    font-size: var(--ct-fs-xs);
    font-weight: 600;
    color: var(--ct-secondary);
    margin-top: 4px;
    line-height: 1.4;
}
.ct-tip {
    position: relative;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 22px;
    height: 22px;
    border-radius: 999px;
    border: 1px solid #BDB7AA;
    background: var(--ct-bg);
    color: var(--ct-ink);
    font-size: var(--ct-fs-xs);
    font-weight: 700;
    cursor: help;
    flex-shrink: 0;
}
.ct-tip:hover, .ct-tip:focus {
    border-color: var(--ct-accent);
    color: var(--ct-accent);
    outline: none;
}
.ct-tip-box {
    visibility: hidden;
    opacity: 0;
    position: absolute;
    bottom: calc(100% + 8px);
    right: 0;
    width: 260px;
    padding: 10px 12px;
    border-radius: 10px;
    background: #141413;
    color: #FAF8F4;
    font-size: var(--ct-fs-sm);
    font-weight: 400;
    line-height: 1.5;
    text-align: left;
    z-index: 99;
    pointer-events: none;
    box-shadow: 0 10px 24px rgba(20, 20, 19, 0.22);
    transition: opacity 140ms var(--ct-ease), transform 140ms var(--ct-ease);
    transform: translateY(4px);
}
.ct-tip:hover .ct-tip-box, .ct-tip:focus .ct-tip-box {
    visibility: visible;
    opacity: 1;
    transform: translateY(0);
}
.ct-glass-hud {
    background: rgba(255, 255, 255, 0.86);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid var(--ct-border);
    border-left: 4px solid var(--ct-cool);
    box-shadow: 0 8px 24px rgba(20, 20, 19, 0.05);
    border-radius: 12px;
    padding: 14px 18px;
}
.ct-guide-note {
    background: oklch(97.8% 0.008 228);
    border: 1px solid oklch(90% 0.03 228);
    border-left: 4px solid var(--ct-cool);
    border-radius: 10px;
    padding: 10px 14px;
    margin: 6px 0 12px 0;
    font-size: var(--ct-fs-sm);
    line-height: 1.55;
    max-width: 68ch;
    text-wrap: pretty;
    color: var(--ct-ink);
}
.ct-stepper {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 12px;
    margin: 12px 0 16px 0;
}
@media (max-width: 820px) {
    .ct-stepper { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
.ct-step {
    background: var(--ct-surface);
    border: 1px solid var(--ct-border);
    border-radius: 12px;
    padding: 14px 16px;
    transition: background 240ms var(--ct-ease), border-color 240ms var(--ct-ease);
}
.ct-step-done {
    border-color: var(--ct-border);
    background: oklch(97.5% 0.006 85);
}
.ct-step-active {
    border-color: var(--ct-accent);
    border-left: 4px solid var(--ct-accent);
    background: oklch(97.2% 0.020 42);
}
.ct-step-good {
    border-color: var(--ct-cool);
    border-left: 4px solid var(--ct-cool);
    background: oklch(97.2% 0.020 228);
}
.ct-step-num {
    font-size: var(--ct-fs-xs);
    font-weight: 700;
    color: var(--ct-secondary);
    letter-spacing: 0.05em;
    text-transform: uppercase;
}
.ct-step-title {
    font-family: var(--ct-font-display);
    font-size: var(--ct-fs-base);
    font-weight: 700;
    color: var(--ct-ink);
    margin-top: 4px;
    text-wrap: balance;
}
.ct-step-sub {
    font-size: var(--ct-fs-sm);
    color: var(--ct-secondary);
    margin-top: 4px;
    line-height: 1.45;
    text-wrap: pretty;
}
.ct-deck {
    display: grid;
    grid-template-columns: 1fr 0.95fr 1fr;
    gap: 14px;
    margin: 14px 0 18px 0;
    padding: 14px;
    border-radius: 18px;
    border: 1px solid var(--ct-border);
    background-color: oklch(98.2% 0.004 85);
    background-image: radial-gradient(oklch(24% 0.01 80 / 0.085) 1px, transparent 1px);
    background-size: 16px 16px;
}
@media (max-width: 820px) {
    .ct-deck { grid-template-columns: 1fr; }
}
.ct-deck-bridge {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    border: 1px solid var(--ct-border);
    border-radius: 16px;
    padding: 20px;
}
.ct-deck-row {
    display: flex;
    justify-content: space-between;
    padding: 8px 0;
    border-bottom: 1px solid #EAE6DD;
    font-size: var(--ct-fs-sm);
    color: var(--ct-ink);
}
.ct-deck-row:last-child { border-bottom: none; }
.ct-brief-card {
    background: oklch(97.6% 0.015 42);
    border: 1px solid var(--ct-border);
    border-left: 4px solid var(--ct-accent);
    border-radius: 12px;
    padding: 16px 20px;
    margin: 12px 0 16px 0;
    max-width: 72ch;
}
.ct-brief-title {
    font-family: var(--ct-font-display);
    font-size: var(--ct-fs-base);
    font-weight: 700;
    color: oklch(42% 0.14 42);
    margin-bottom: 6px;
}
[data-testid="stTabs"] [role="tablist"],
.stTabs [data-baseweb="tab-list"] {
    gap: 6px;
    background: var(--ct-recessed) !important;
    padding: 4px !important;
    border-radius: 12px !important;
    border: 1px solid var(--ct-border) !important;
    width: fit-content;
    margin-bottom: 12px;
}
[data-testid="stTabs"] [role="tab"],
.stTabs [data-baseweb="tab"] {
    padding: 9px 20px !important;
    font-family: var(--ct-font-display) !important;
    font-size: var(--ct-fs-base) !important;
    font-weight: 600 !important;
    color: var(--ct-secondary) !important;
    border-radius: 8px !important;
    border: none !important;
    background: transparent !important;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"],
.stTabs [aria-selected="true"] {
    background: var(--ct-surface) !important;
    color: var(--ct-ink) !important;
    font-weight: 700 !important;
    box-shadow: 0 2px 6px rgba(20, 20, 19, 0.10) !important;
}
[data-testid="stTabs"] [data-baseweb="tab-highlight"],
[data-testid="stTabs"] [data-baseweb="tab-border"],
.stTabs [data-baseweb="tab-highlight"],
.stTabs [data-baseweb="tab-border"] {
    display: none !important;
}
div.stButton > button {
    border-radius: 10px;
    min-height: 42px;
    font-family: var(--ct-font-body) !important;
    font-weight: 600 !important;
    font-size: var(--ct-fs-sm) !important;
    border: 1px solid #C5C0B4;
    transition: transform 140ms var(--ct-ease), background-color 140ms ease;
}
div.stButton > button:active {
    transform: scale(0.98);
}
.ct-printer-wrap {
    max-width: 580px;
    margin: 14px 0 14px 0;
}
.ct-printer-slot {
    height: 24px;
    background: linear-gradient(180deg, #272725 0%, #141413 100%);
    border-radius: 10px 10px 3px 3px;
    border: 1px solid #141413;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 14px;
    position: relative;
    z-index: 2;
    box-shadow: 0 4px 10px rgba(20, 20, 19, 0.18);
}
.ct-printer-slot-label {
    font-size: var(--ct-fs-xs);
    font-weight: 700;
    letter-spacing: 0.06em;
    color: #F4F3EF;
    text-transform: uppercase;
}
.ct-printer-led {
    width: 8px;
    height: 8px;
    border-radius: 999px;
    background: #22C55E;
    box-shadow: 0 0 8px #22C55E;
}
.ct-receipt-viewport {
    overflow: hidden;
    padding: 0 10px 8px 10px;
}
@keyframes ct-eject {
    0% { transform: translateY(-92%); opacity: 0.2; }
    100% { transform: translateY(0); opacity: 1; }
}
.ct-receipt-paper {
    background: #FFFFFF;
    border: 1px solid var(--ct-border);
    border-top: none;
    padding: 18px 20px;
    box-shadow: 0 12px 26px rgba(20, 20, 19, 0.09);
    border-radius: 0 0 10px 10px;
}
.ct-receipt-peek {
    background: oklch(98.2% 0.004 85);
    border: 1px solid var(--ct-border);
    border-top: none;
    padding: 10px 18px;
    border-radius: 0 0 8px 8px;
    font-size: var(--ct-fs-xs);
    color: var(--ct-secondary);
}
.ct-receipt-animate {
    animation: ct-eject 540ms var(--ct-ease) both;
}
.ct-receipt-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1.5px dashed #BDB7AA;
    padding-bottom: 10px;
    margin-bottom: 10px;
}
.ct-receipt-stamp {
    font-size: var(--ct-fs-xs);
    font-weight: 700;
    padding: 4px 10px;
    border-radius: 6px;
    letter-spacing: 0.04em;
}
.ct-stamp-ok { background: #DCFCE7; color: #166534; border: 1px solid #86EFAC; }
.ct-stamp-warn { background: #FFEDD5; color: #9A3412; border: 1px solid #FDBA74; }
.ct-stamp-info { background: #E0F2FE; color: #075985; border: 1px solid #7DD3FC; }
.ct-receipt-row {
    display: flex;
    justify-content: space-between;
    font-size: var(--ct-fs-sm);
    padding: 4px 0;
    color: var(--ct-ink);
}
.ct-receipt-tear {
    margin-top: 12px;
    height: 8px;
    background: repeating-linear-gradient(-45deg, transparent 0 6px, #D8D4C9 6px 12px);
    opacity: 0.65;
    border-radius: 2px;
}
@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        transition-duration: 0.01ms !important;
        animation-duration: 0.01ms !important;
    }
}
</style>"""
    if hasattr(st, "html"):
        st.html(css_block)
    else:
        st.markdown(css_block, unsafe_allow_html=True)
