import sys
import os

# streamlit_app.py is in TASK-3C/, app/ is in TASK-3C/finance-agent/
_here = os.path.dirname(os.path.abspath(__file__))
_app_root = os.path.join(_here, "finance-agent")
sys.path.insert(0, _app_root)

import streamlit as st
import json
import pandas as pd
from datetime import datetime, timezone
from uuid import uuid4
import time

# ── Direct service imports (no FastAPI needed) ──
from app.services.analyzer import analyze
from app.services.risk_engine import compute_risk
from app.services.decision_engine import decide
from app.services.executor import execute
from app.services.learning import log_case


def _process_one(data):
    analysis = analyze(data)
    risk = compute_risk(data)
    decision = decide(analysis, risk)
    result = execute(decision, data)
    request_id = str(uuid4())
    processed_at = datetime.now(timezone.utc).isoformat()
    log_case(data=data, analysis=analysis, risk=risk,
             decision=decision, result=result,
             request_id=request_id, processed_at=processed_at)
    return {
        "analysis": analysis,
        "risk_score": risk,
        "decision": decision,
        "result": result,
        "meta": {
            "request_id": request_id,
            "processed_at": processed_at,
            "analysis_source": analysis.get("source", "rules_fallback"),
        },
    }

# ─── Page Config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Finance Agent",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600&display=swap');

:root {
    --bg:        #060911;
    --bg-panel:  #0b1018;
    --bg-raised: #0f1623;
    --bg-hover:  #141d2b;
    --border:    #1a2540;
    --border-bright: #243350;
    --text-primary:  #edf2fb;
    --text-secondary:#94a8c8;
    --text-dim:      #4a6080;
    --accent-blue:   #3b82f6;
    --accent-cyan:   #06b6d4;
    --green:  #10b981;
    --yellow: #f59e0b;
    --red:    #ef4444;
    --blue:   #3b82f6;
}

/* ── Kill the white toolbar ribbon at the top ── */
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"],
header[data-testid="stHeader"] {
    background: #060911 !important;
    border-bottom: 1px solid #1a2540 !important;
}
header[data-testid="stHeader"] * { color: #6b84a8 !important; }
/* Hide the deploy button area background */
[data-testid="stAppDeployButton"] { display: none !important; }

/* ── Global reset ── */
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif !important;
    background-color: #060911 !important;
    color: #e8edf5 !important;
}

/* Subtle dot grid — much softer than lines */
.stApp {
    background-color: #060911 !important;
    background-image: radial-gradient(circle, #1a2540 1px, transparent 1px);
    background-size: 28px 28px;
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background-color: var(--bg-panel) !important;
    border-right: 1px solid var(--border) !important;
}
section[data-testid="stSidebar"] * {
    color: var(--text-secondary) !important;
}
section[data-testid="stSidebar"] h3 {
    color: var(--text-primary) !important;
    font-size: 11px !important;
    letter-spacing: 0.15em !important;
    text-transform: uppercase !important;
    font-family: 'Space Mono', monospace !important;
}
section[data-testid="stSidebar"] label {
    font-size: 10px !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
    color: var(--text-dim) !important;
    font-family: 'Space Mono', monospace !important;
}
/* Sidebar radio nav items */
section[data-testid="stSidebar"] .stRadio label {
    font-size: 13px !important;
    letter-spacing: 0.02em !important;
    text-transform: none !important;
    color: var(--text-secondary) !important;
    font-family: 'DM Sans', sans-serif !important;
    padding: 4px 0 !important;
}
section[data-testid="stSidebar"] [aria-checked="true"] ~ * {
    color: var(--accent-blue) !important;
}
section[data-testid="stSidebar"] hr {
    border-color: var(--border) !important;
    margin: 14px 0 !important;
}

/* ── Main content area ── */
.block-container {
    padding: 6rem 2.5rem 2rem 2.5rem !important;
    max-width: 1400px !important;
}

/* ── Page header ── */
.agent-header {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 0 0 20px 0;
    border-bottom: 1px solid var(--border);
    margin-bottom: 28px;
}
.agent-logo-wrap {
    width: 44px;
    height: 44px;
    background: linear-gradient(135deg, #1d4ed8, #0891b2);
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 22px;
    box-shadow: 0 0 20px #1d4ed830;
}
.agent-title {
    font-size: 20px;
    font-weight: 600;
    color: var(--text-primary);
    letter-spacing: -0.01em;
    line-height: 1.2;
}
.agent-sub {
    font-size: 11px;
    color: var(--text-dim);
    font-family: 'Space Mono', monospace;
    letter-spacing: 0.1em;
    margin-top: 2px;
}
.header-status {
    margin-left: auto;
    display: flex;
    align-items: center;
    gap: 6px;
    font-family: 'Space Mono', monospace;
    font-size: 10px;
    color: var(--text-dim);
    letter-spacing: 0.08em;
}
.status-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--green);
    box-shadow: 0 0 6px var(--green);
    animation: pulse 2s ease-in-out infinite;
}
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }

/* ── Section labels ── */
.section-label {
    font-size: 10px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--text-dim);
    font-family: 'Space Mono', monospace;
    margin-bottom: 14px;
    margin-top: 24px;
    display: flex;
    align-items: center;
    gap: 10px;
}
.section-label::after {
    content: '';
    flex: 1;
    height: 1px;
    background: var(--border);
}

/* ── Metric cards ── */
.metric-row { display: flex; gap: 12px; margin-bottom: 24px; flex-wrap: wrap; }
.metric-card {
    flex: 1;
    min-width: 120px;
    background: var(--bg-panel);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 18px 20px;
    position: relative;
    overflow: hidden;
}
.metric-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, transparent, var(--border-bright), transparent);
}
.metric-label {
    font-size: 9px;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    color: var(--text-dim);
    margin-bottom: 8px;
    font-family: 'Space Mono', monospace;
}
.metric-value {
    font-size: 28px;
    font-weight: 700;
    color: var(--text-primary);
    line-height: 1;
    font-family: 'Space Mono', monospace;
    letter-spacing: -0.02em;
}
.metric-value.green  { color: var(--green); }
.metric-value.yellow { color: var(--yellow); }
.metric-value.red    { color: var(--red); }
.metric-value.blue   { color: var(--blue); }

/* ── Decision badges ── */
.badge {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 4px 10px;
    border-radius: 5px;
    font-size: 10px;
    font-weight: 700;
    font-family: 'Space Mono', monospace;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}
.badge::before { content: ''; width: 5px; height: 5px; border-radius: 50%; }
.badge-approve { background: rgba(16,185,129,0.1); color: var(--green);  border: 1px solid rgba(16,185,129,0.25); }
.badge-approve::before { background: var(--green); }
.badge-review  { background: rgba(245,158,11,0.1); color: var(--yellow); border: 1px solid rgba(245,158,11,0.25); }
.badge-review::before  { background: var(--yellow); }
.badge-reject  { background: rgba(239,68,68,0.1);  color: var(--red);    border: 1px solid rgba(239,68,68,0.25); }
.badge-reject::before  { background: var(--red); }

/* ── Result cards ── */
.result-card {
    background: var(--bg-panel);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 22px 24px;
    margin-bottom: 12px;
    transition: border-color 0.2s;
}
.result-card:hover { border-color: var(--border-bright); }
.result-card.approve { border-left: 3px solid var(--green); }
.result-card.review  { border-left: 3px solid var(--yellow); }
.result-card.reject  { border-left: 3px solid var(--red); }

.result-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 14px;
}
.inv-id {
    font-family: 'Space Mono', monospace;
    font-size: 13px;
    font-weight: 700;
    color: var(--text-primary);
    letter-spacing: 0.04em;
}
.risk-bar-bg {
    height: 3px;
    background: var(--border);
    border-radius: 2px;
    margin: 8px 0 16px 0;
}
.risk-bar-fill { height: 3px; border-radius: 2px; }
.detail-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
    font-size: 11px;
}
.detail-item {
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.1em;
    font-family: 'Space Mono', monospace;
    font-size: 9px;
}
.detail-item span {
    display: block;
    color: var(--text-secondary);
    font-weight: 500;
    margin-top: 4px;
    font-size: 12px;
    font-family: 'DM Sans', sans-serif;
    letter-spacing: 0;
    text-transform: none;
}

/* ── Log entries ── */
.log-entry {
    background: var(--bg-panel);
    border: 1px solid var(--border);
    border-radius: 7px;
    padding: 11px 16px;
    margin-bottom: 6px;
    font-family: 'Space Mono', monospace;
    font-size: 11px;
    color: var(--text-dim);
    display: flex;
    align-items: center;
    gap: 12px;
    transition: background 0.15s;
}
.log-entry:hover { background: var(--bg-hover); }
.log-entry .log-id { color: var(--accent-blue); font-weight: 700; }
.log-entry .log-sep { color: var(--border-bright); }
.log-entry .log-decision-approve { color: var(--green); }
.log-entry .log-decision-review  { color: var(--yellow); }
.log-entry .log-decision-reject  { color: var(--red); }
.log-entry .log-risk { color: var(--text-secondary); }

/* ── ALL inputs — brute-force every possible selector ── */
input, textarea, select,
input[type="text"], input[type="number"],
[data-baseweb="input"] input,
[data-baseweb="textarea"] textarea,
.stTextInput input, .stNumberInput input,
.stTextArea textarea {
    background-color: #0f1623 !important;
    background: #0f1623 !important;
    border: 1px solid #1a2540 !important;
    color: #edf2fb !important;
    border-radius: 7px !important;
    font-family: 'Space Mono', monospace !important;
    font-size: 12px !important;
    caret-color: #3b82f6 !important;
}
input:focus, textarea:focus,
[data-baseweb="input"] input:focus {
    border-color: #3b82f6 !important;
    box-shadow: 0 0 0 2px rgba(59,130,246,0.2) !important;
    outline: none !important;
}

/* BaseWeb input containers */
[data-baseweb="input"],
[data-baseweb="base-input"],
[data-baseweb="input"] > div,
[data-baseweb="base-input"] > div {
    background: #0f1623 !important;
    border-color: #1a2540 !important;
    border-radius: 7px !important;
}

/* Selectbox */
[data-baseweb="select"] > div,
[data-baseweb="select"] > div > div {
    background: #0f1623 !important;
    border-color: #1a2540 !important;
    border-radius: 7px !important;
    color: #edf2fb !important;
    font-family: 'Space Mono', monospace !important;
    font-size: 12px !important;
}
[data-baseweb="select"] [data-baseweb="tag"],
[data-baseweb="select"] span,
[data-baseweb="select"] div {
    color: #edf2fb !important;
    background: transparent !important;
}
/* Dropdown list */
[data-baseweb="popover"] { background: #0f1623 !important; border: 1px solid #1a2540 !important; border-radius: 8px !important; }
[data-baseweb="menu"]    { background: #0f1623 !important; }
[role="option"]          { background: #0f1623 !important; color: #edf2fb !important; font-family: 'Space Mono', monospace !important; font-size: 12px !important; }
[role="option"]:hover,
[role="option"][aria-selected="true"] { background: #141d2b !important; }
li[role="option"]        { background: #0f1623 !important; color: #edf2fb !important; }

/* Number input +/- wrapper */
[data-testid="stNumberInput"] > div,
[data-testid="stNumberInput"] [data-baseweb="input"],
[data-testid="stNumberInput"] [data-baseweb="base-input"] {
    background: #0f1623 !important;
    border-color: #1a2540 !important;
}
[data-testid="stNumberInput"] button {
    background: #141d2b !important;
    border: none !important;
    border-left: 1px solid #1a2540 !important;
    color: #6b84a8 !important;
    font-size: 16px !important;
    line-height: 1 !important;
}
[data-testid="stNumberInput"] button:hover { background: #1a2540 !important; color: #edf2fb !important; }

/* Labels — all of them */
label, .stTextInput label, .stNumberInput label,
.stSelectbox label, .stSlider label,
.stCheckbox label, .stTextArea label,
.stFileUploader label, .stRadio label,
p[data-testid="stWidgetLabel"],
[data-testid="stWidgetLabel"] {
    font-size: 10px !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
    color: #4a6080 !important;
    font-family: 'Space Mono', monospace !important;
    font-weight: 400 !important;
}
/* Don't uppercase sidebar nav labels */
section[data-testid="stSidebar"] .stRadio label {
    text-transform: none !important;
    font-size: 13px !important;
    color: #6b84a8 !important;
    letter-spacing: 0.02em !important;
}

/* ── Buttons ── */
.stButton > button {
    background: linear-gradient(135deg, #2563eb, #1d4ed8) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 7px !important;
    font-family: 'Space Mono', monospace !important;
    font-weight: 700 !important;
    font-size: 11px !important;
    letter-spacing: 0.08em !important;
    padding: 10px 22px !important;
    transition: all 0.2s !important;
    box-shadow: 0 2px 12px rgba(37,99,235,0.3) !important;
}
.stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 18px rgba(37,99,235,0.45) !important;
}
.stButton > button:active { transform: translateY(0) !important; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: transparent !important;
    border-bottom: 1px solid var(--border) !important;
    gap: 0 !important;
}
.stTabs [data-baseweb="tab"] {
    font-family: 'Space Mono', monospace !important;
    font-size: 11px !important;
    letter-spacing: 0.08em !important;
    color: var(--text-dim) !important;
    background: transparent !important;
    padding: 10px 20px !important;
    border-bottom: 2px solid transparent !important;
}
.stTabs [aria-selected="true"] {
    color: var(--accent-blue) !important;
    border-bottom-color: var(--accent-blue) !important;
}

/* ── Expander — nuke every white background Streamlit injects ── */
details, [data-testid="stExpander"], [data-testid="stExpanderDetails"] {
    background: var(--bg-panel) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    overflow: hidden !important;
}
details summary, .streamlit-expanderHeader,
[data-testid="stExpander"] > div:first-child {
    background: var(--bg-panel) !important;
    color: var(--text-secondary) !important;
    font-family: 'Space Mono', monospace !important;
    font-size: 12px !important;
    letter-spacing: 0.06em !important;
}
details > div, .streamlit-expanderContent,
[data-testid="stExpander"] > div {
    background: var(--bg-panel) !important;
    border-top: 1px solid var(--border) !important;
}

/* ── Checkbox ── */
[data-testid="stCheckbox"] label {
    color: #6b84a8 !important;
    font-size: 11px !important;
    font-family: 'Space Mono', monospace !important;
    letter-spacing: 0.06em !important;
    text-transform: uppercase !important;
}
[data-baseweb="checkbox"] > div {
    background: #0f1623 !important;
    border-color: #1a2540 !important;
    border-radius: 4px !important;
}
[data-baseweb="checkbox"] > div[data-checked="true"] {
    background: #3b82f6 !important;
    border-color: #3b82f6 !important;
}

/* ── Slider — force blue, kill red ── */
[data-testid="stSlider"] [role="slider"] {
    background: #3b82f6 !important;
    border-color: #3b82f6 !important;
    box-shadow: 0 0 8px rgba(59,130,246,0.4) !important;
}
[data-testid="stSlider"] [data-testid="stTickBar"] { color: #4a6080 !important; font-size: 10px !important; }
/* Filled track portion (BaseWeb uses inline styles — override with attribute) */
[data-testid="stSlider"] div[data-baseweb="slider"] div div div { background: #3b82f6 !important; }
[data-testid="stSlider"] div[data-baseweb="slider"] div div:first-child { background: #1a2540 !important; }

/* ── File uploader ── */
[data-testid="stFileUploader"] section {
    background: var(--bg-raised) !important;
    border: 1px dashed var(--border-bright) !important;
    border-radius: 8px !important;
}

/* ── Native st.metric ── */
[data-testid="metric-container"] {
    background: var(--bg-panel) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    padding: 14px 18px !important;
}
[data-testid="stMetricLabel"] {
    color: var(--text-dim) !important;
    font-family: 'Space Mono', monospace !important;
    font-size: 10px !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
}
[data-testid="stMetricValue"] {
    color: var(--text-primary) !important;
    font-family: 'Space Mono', monospace !important;
    font-weight: 700 !important;
}

/* ── Alert banners ── */
[data-testid="stAlert"] {
    background: var(--bg-raised) !important;
    border-radius: 8px !important;
    border: 1px solid var(--border) !important;
}

/* ── Download button ── */
[data-testid="stDownloadButton"] button {
    background: var(--bg-raised) !important;
    border: 1px solid var(--border) !important;
    color: var(--text-secondary) !important;
    font-family: 'Space Mono', monospace !important;
    font-size: 11px !important;
    border-radius: 7px !important;
}
[data-testid="stDownloadButton"] button:hover {
    border-color: var(--accent-blue) !important;
    color: var(--accent-blue) !important;
}

/* ── Info / success / error ── */
.stAlert {
    border-radius: 8px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 13px !important;
}

/* ── Dataframe ── */
.stDataFrame { border-radius: 8px !important; overflow: hidden !important; }

/* ── Slider ── */
.stSlider [data-baseweb="slider"] { padding: 0 2px !important; }

/* ── HR ── */
hr { border-color: var(--border) !important; }

/* ── Spinner ── */
.stSpinner > div { border-top-color: var(--accent-blue) !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--border-bright); border-radius: 3px; }
</style>
""", unsafe_allow_html=True)

# ─── Config ─────────────────────────────────────────────────────────────────

# ─── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⬡ Navigation")
    page = st.radio(
        "Go to",
        ["Single Invoice", "Batch Processing", "Log Viewer", "Risk Simulator"],
        label_visibility="collapsed"
    )
    st.markdown("---")
    st.markdown("""
    <div style="font-size:10px;color:#4a6080;font-family:'Space Mono',monospace;letter-spacing:0.1em;line-height:1.8;">
    RUNNING STANDALONE<br>No API required.<br>Services run locally.
    </div>
    """, unsafe_allow_html=True)

# ─── Header ──────────────────────────────────────────────────────────────────
st.markdown("""
<div class="agent-header">
  <div class="agent-logo-wrap">⬡</div>
  <div>
    <div class="agent-title">Autonomous Finance Agent</div>
    <div class="agent-sub">INVOICE INTELLIGENCE PLATFORM · v1.1.0</div>
  </div>
  <div class="header-status">
    <div class="status-dot"></div>
    SYSTEM OPERATIONAL
  </div>
</div>
""", unsafe_allow_html=True)


# ─── Helpers ─────────────────────────────────────────────────────────────────
def badge_html(decision):
    mapping = {
        "auto_approve": ("approve", "AUTO APPROVE"),
        "manual_review": ("review", "MANUAL REVIEW"),
        "auto_reject": ("reject", "AUTO REJECT"),
    }
    cls, label = mapping.get(decision, ("review", decision.upper()))
    return f'<span class="badge badge-{cls}">{label}</span>'


def risk_color(score):
    if score < 0.35:
        return "var(--green)"
    elif score < 0.65:
        return "var(--yellow)"
    else:
        return "var(--red)"


def risk_color_class(score):
    if score < 0.35: return "green"
    elif score < 0.65: return "yellow"
    else: return "red"


def card_class(decision):
    if decision == "auto_approve": return "approve"
    elif decision == "auto_reject": return "reject"
    return "review"


def render_result_card(item):
    decision = item.get("decision", "")
    risk = item.get("risk_score", 0)
    analysis = item.get("analysis", {})
    result = item.get("result", {})
    meta = item.get("meta", {})
    data = item.get("data", {})

    inv_id = data.get("invoice_id", meta.get("request_id", "—")[:8])
    vendor = data.get("vendor_id", "—")
    mismatch = data.get("mismatch_type", "—")
    variance = data.get("variance_amount", 0)
    currency = data.get("currency", "USD")

    color = risk_color(risk)
    bar_width = int(risk * 100)
    source = meta.get("analysis_source", "—")

    st.markdown(f"""
    <div class="result-card {card_class(decision)}">
      <div class="result-header">
        <div class="inv-id">{inv_id}</div>
        {badge_html(decision)}
      </div>
      <div class="risk-bar-bg">
        <div class="risk-bar-fill" style="width:{bar_width}%;background:{color};"></div>
      </div>
      <div class="detail-grid">
        <div class="detail-item">RISK SCORE<span class="{risk_color_class(risk)}" style="color:{color};font-size:18px;font-weight:600;">{risk:.3f}</span></div>
        <div class="detail-item">VENDOR<span>{vendor}</span></div>
        <div class="detail-item">MISMATCH<span>{mismatch.replace("_"," ").title()}</span></div>
        <div class="detail-item">VARIANCE<span>{currency} {variance:,.2f}</span></div>
        <div class="detail-item">STATUS<span>{result.get("status","—").upper()}</span></div>
        <div class="detail-item">SOURCE<span>{source}</span></div>
      </div>
      <div style="margin-top:12px;font-size:12px;color:var(--text-secondary);font-style:italic;">
        {analysis.get("explanation","")[:200]}{"…" if len(analysis.get("explanation","")) > 200 else ""}
      </div>
    </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
# PAGE: Single Invoice
# ═══════════════════════════════════════════════════════════════════
if page == "Single Invoice":
    st.markdown('<div class="section-label">Single Invoice Processing</div>', unsafe_allow_html=True)

    with st.expander("📋 Invoice Details", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            invoice_id = st.text_input("Invoice ID", value="INV-2026-0001")
            vendor_id = st.text_input("Vendor ID", value="VEND-ALPHA-01")
            po_id = st.text_input("PO ID", value="PO-10001")
            grn_id = st.text_input("GRN ID", value="GRN-10001")
        with c2:
            mismatch_type = st.selectbox("Mismatch Type", [
                "price_variance", "duplicate", "quantity_variance",
                "tax_variance", "unknown"
            ])
            variance_amount = st.number_input("Variance Amount", value=850.0, step=50.0)
            currency = st.selectbox("Currency", ["USD", "EUR", "GBP", "INR", "JPY"])
            detected_at = st.text_input("Detected At (ISO)", value="2026-03-30T09:15:00Z")
        with c3:
            invoice_total = st.number_input("Invoice Total", value=9500.0, step=100.0)
            expected_total = st.number_input("Expected Total", value=8650.0, step=100.0)
            vendor_risk_score = st.slider("Vendor Risk Score", 0.0, 1.0, 0.22, 0.01)
            prior_disputes = st.number_input("Prior Disputes (90d)", value=1, step=1)
            invoice_count = st.number_input("Invoice Count (90d)", value=24, step=1)

        c4, c5 = st.columns(2)
        with c4:
            is_duplicate = st.checkbox("Is Duplicate Suspected?", value=False)
            duplicate_id = st.text_input("Duplicate Invoice ID (if any)", value="")
        with c5:
            region = st.selectbox("Region", ["NA", "EMEA", "APAC", "LATAM"])
            business_unit = st.selectbox("Business Unit", [
                "manufacturing", "procurement", "operations",
                "projects", "construction", "shared-services"
            ])
            source_system = st.selectbox("Source System", [
                "sap_s4", "oracle_erp", "legacy_ap"
            ])

    if st.button("▶  Process Invoice"):
        payload = {
            "invoice_id": invoice_id,
            "vendor_id": vendor_id,
            "po_id": po_id,
            "grn_id": grn_id,
            "mismatch_type": mismatch_type,
            "variance_amount": variance_amount,
            "currency": currency,
            "detected_at": detected_at,
            "invoice_total": invoice_total,
            "expected_total": expected_total,
            "vendor_risk_score": vendor_risk_score,
            "prior_dispute_count_90d": int(prior_disputes),
            "invoice_count_90d": int(invoice_count),
            "is_duplicate_suspected": is_duplicate,
            "duplicate_invoice_id": duplicate_id if duplicate_id else None,
            "region": region,
            "business_unit": business_unit,
            "source_system": source_system,
            "tags": [],
            "metadata": {},
        }

        with st.spinner("Analyzing invoice..."):
            try:
                start = time.time()
                data = _process_one(payload)
                elapsed = time.time() - start
                item = {**data, "data": payload}

                st.markdown('<div class="section-label">Result</div>', unsafe_allow_html=True)
                render_result_card(item)

                col1, col2, col3 = st.columns(3)
                col1.metric("Risk Score", f"{data['risk_score']:.3f}")
                col2.metric("Decision", data["decision"].replace("_", " ").title())
                col3.metric("Latency", f"{elapsed:.2f}s")

                with st.expander("🔍 Full JSON Response"):
                    st.json(data)
            except Exception as e:
                st.error(f"Error: {e}")


# ═══════════════════════════════════════════════════════════════════
# PAGE: Batch Processing
# ═══════════════════════════════════════════════════════════════════
elif page == "Batch Processing":
    st.markdown('<div class="section-label">Batch Invoice Processing</div>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["📂  Upload JSON", "✏️  Paste JSON"])

    batch_json = None

    with tab1:
        uploaded = st.file_uploader("Upload batch JSON file", type=["json"])
        if uploaded:
            try:
                batch_json = json.load(uploaded)
                st.success(f"Loaded {len(batch_json.get('invoices', []))} invoices")
            except Exception as e:
                st.error(f"Invalid JSON: {e}")

    with tab2:
        raw = st.text_area("Paste batch JSON here", height=200,
            placeholder='{"invoices": [{...}, {...}]}')
        if raw.strip():
            try:
                batch_json = json.loads(raw)
            except Exception as e:
                st.error(f"Invalid JSON: {e}")

    if batch_json:
        invoices = batch_json.get("invoices", [])
        st.info(f"{len(invoices)} invoices ready to process")

        if st.button("▶  Process Batch"):
            with st.spinner(f"Processing {len(invoices)} invoices..."):
                try:
                    outputs = []
                    for inv in invoices:
                        outputs.append(_process_one(inv))

                    avg_risk = sum(item["risk_score"] for item in outputs) / len(outputs)
                    summary = {
                        "total": len(outputs),
                        "auto_approve": sum(1 for item in outputs if item["decision"] == "auto_approve"),
                        "manual_review": sum(1 for item in outputs if item["decision"] == "manual_review"),
                        "auto_reject": sum(1 for item in outputs if item["decision"] == "auto_reject"),
                        "average_risk": round(avg_risk, 3),
                    }
                    data = {"summary": summary, "items": outputs}
                    items = outputs

                    # Summary metrics
                    st.markdown('<div class="section-label">Batch Summary</div>', unsafe_allow_html=True)
                    st.markdown(f"""
                    <div class="metric-row">
                      <div class="metric-card"><div class="metric-label">Total</div><div class="metric-value blue">{summary["total"]}</div></div>
                      <div class="metric-card"><div class="metric-label">Auto Approved</div><div class="metric-value green">{summary["auto_approve"]}</div></div>
                      <div class="metric-card"><div class="metric-label">Manual Review</div><div class="metric-value yellow">{summary["manual_review"]}</div></div>
                      <div class="metric-card"><div class="metric-label">Auto Rejected</div><div class="metric-value red">{summary["auto_reject"]}</div></div>
                      <div class="metric-card"><div class="metric-label">Avg Risk</div><div class="metric-value {risk_color_class(summary["average_risk"])}">{summary["average_risk"]:.3f}</div></div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Per-invoice results sorted by risk
                    st.markdown('<div class="section-label">Invoice Results</div>', unsafe_allow_html=True)
                    items_sorted = sorted(items, key=lambda x: x.get("risk_score", 0), reverse=True)
                    for i, item in enumerate(items_sorted):
                        item["data"] = invoices[i] if i < len(invoices) else {}
                        render_result_card(item)

                    # DataFrame
                    st.markdown('<div class="section-label">Data Table</div>', unsafe_allow_html=True)
                    rows = []
                    for item in items:
                        rows.append({
                            "Invoice ID": item.get("data", {}).get("invoice_id", "—"),
                            "Vendor": item.get("data", {}).get("vendor_id", "—"),
                            "Mismatch": item.get("data", {}).get("mismatch_type", "—"),
                            "Variance ($)": item.get("data", {}).get("variance_amount", 0),
                            "Risk": item.get("risk_score", 0),
                            "Decision": item.get("decision", "—"),
                            "Root Cause": item.get("analysis", {}).get("root_cause", "—"),
                            "Confidence": item.get("analysis", {}).get("confidence", 0),
                        })
                    df = pd.DataFrame(rows)
                    st.dataframe(df, use_container_width=True)

                    with st.expander("📦 Full JSON Response"):
                        st.json(data)
                except Exception as e:
                    st.error(f"Error: {e}")


# ═══════════════════════════════════════════════════════════════════
# PAGE: Log Viewer
# ═══════════════════════════════════════════════════════════════════
elif page == "Log Viewer":
    st.markdown('<div class="section-label">Audit Log Viewer</div>', unsafe_allow_html=True)

    log_file = st.text_input("Log file path", value="data/logs.jsonl")

    uploaded_log = st.file_uploader("Or upload logs.jsonl", type=["jsonl", "json", "txt"])

    lines = []
    if uploaded_log:
        content = uploaded_log.read().decode("utf-8")
        for line in content.strip().splitlines():
            try:
                lines.append(json.loads(line))
            except:
                pass
    elif log_file:
        try:
            with open(log_file, "r") as f:
                for line in f:
                    try:
                        lines.append(json.loads(line))
                    except:
                        pass
        except FileNotFoundError:
            st.warning("Log file not found. Upload one above.")

    if lines:
        # Filter bar
        c1, c2, c3 = st.columns(3)
        with c1:
            filter_decision = st.selectbox("Filter by Decision", ["All", "auto_approve", "manual_review", "auto_reject"])
        with c2:
            filter_source = st.selectbox("Filter by Source", ["All", "groq_llm", "rules_fallback"])
        with c3:
            min_risk = st.slider("Min Risk Score", 0.0, 1.0, 0.0, 0.05)

        filtered = lines
        if filter_decision != "All":
            filtered = [l for l in filtered if l.get("decision") == filter_decision]
        if filter_source != "All":
            filtered = [l for l in filtered if l.get("analysis", {}).get("source") == filter_source]
        filtered = [l for l in filtered if l.get("risk", 0) >= min_risk]

        # Summary metrics from logs
        if filtered:
            decisions = [l.get("decision", "") for l in filtered]
            risks = [l.get("risk", 0) for l in filtered]
            st.markdown(f"""
            <div class="metric-row">
              <div class="metric-card"><div class="metric-label">Log Entries</div><div class="metric-value blue">{len(filtered)}</div></div>
              <div class="metric-card"><div class="metric-label">Approved</div><div class="metric-value green">{decisions.count("auto_approve")}</div></div>
              <div class="metric-card"><div class="metric-label">Review</div><div class="metric-value yellow">{decisions.count("manual_review")}</div></div>
              <div class="metric-card"><div class="metric-label">Rejected</div><div class="metric-value red">{decisions.count("auto_reject")}</div></div>
              <div class="metric-card"><div class="metric-label">Avg Risk</div><div class="metric-value">{sum(risks)/len(risks):.3f}</div></div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('<div class="section-label">Log Entries</div>', unsafe_allow_html=True)
        for entry in reversed(filtered):
            inv_id = entry.get("data", {}).get("invoice_id", entry.get("request_id", "—")[:12])
            decision = entry.get("decision", "—")
            risk = entry.get("risk", 0)
            logged_at = entry.get("logged_at", entry.get("processed_at", "—"))
            source = entry.get("analysis", {}).get("source", "—")
            latency = entry.get("analysis", {}).get("latency_ms")
            latency_str = f"{latency:.0f}ms" if latency else "—"

            d_class = {
                "auto_approve": "log-decision-approve",
                "manual_review": "log-decision-review",
                "auto_reject": "log-decision-reject",
            }.get(decision, "")

            st.markdown(f"""
            <div class="log-entry">
              <span class="log-id">{inv_id}</span>
              <span class="log-sep">·</span><span class="{d_class}">{decision.replace("_"," ").upper()}</span>
              <span class="log-sep">·</span><span class="log-risk">risk {risk:.3f}</span>
              <span class="log-sep">·</span>{source}
              <span class="log-sep">·</span>{latency_str}
              <span class="log-sep">·</span><span style="color:var(--text-dim)">{logged_at[:19] if logged_at != "—" else "—"}</span>
            </div>
            """, unsafe_allow_html=True)

        # Export
        if st.button("⬇  Export Filtered Logs as CSV"):
            rows = []
            for e in filtered:
                rows.append({
                    "invoice_id": e.get("data", {}).get("invoice_id", ""),
                    "vendor_id": e.get("data", {}).get("vendor_id", ""),
                    "mismatch_type": e.get("data", {}).get("mismatch_type", ""),
                    "variance_amount": e.get("data", {}).get("variance_amount", ""),
                    "risk": e.get("risk", ""),
                    "decision": e.get("decision", ""),
                    "source": e.get("analysis", {}).get("source", ""),
                    "confidence": e.get("analysis", {}).get("confidence", ""),
                    "root_cause": e.get("analysis", {}).get("root_cause", ""),
                    "latency_ms": e.get("analysis", {}).get("latency_ms", ""),
                    "logged_at": e.get("logged_at", ""),
                })
            df = pd.DataFrame(rows)
            csv = df.to_csv(index=False)
            st.download_button("Download CSV", csv, "finance_agent_logs.csv", "text/csv")
    else:
        st.info("No log entries to display. Upload a logs.jsonl file or point to one on disk.")

# ═══════════════════════════════════════════════════════════════════
# PAGE: Risk Simulator  (mirrors risk_engine.py + decision_engine.py locally)
# ═══════════════════════════════════════════════════════════════════
elif page == "Risk Simulator":
    st.markdown('<div class="section-label">Risk & Decision Simulator</div>', unsafe_allow_html=True)
    st.markdown(
        "<p style='color:var(--text-secondary);font-size:13px;margin-bottom:20px;'>"
        "Simulate risk scores locally using the same logic as <code>risk_engine.py</code> "
        "and <code>decision_engine.py</code> — no API call needed.</p>",
        unsafe_allow_html=True,
    )

    # ── Local implementations (mirrors the actual service files) ──
    def local_compute_risk(variance_amount, invoice_total, mismatch_type,
                           vendor_risk_score, prior_disputes, is_duplicate):
        score = 0.0
        variance_amount = float(variance_amount or 0)
        invoice_total = float(invoice_total or 0)

        if variance_amount > 5000:
            score += 0.45
        elif variance_amount > 1000:
            score += 0.25

        if invoice_total > 0:
            ratio = variance_amount / invoice_total
            if ratio > 0.2:
                score += 0.2
            elif ratio > 0.08:
                score += 0.1

        if mismatch_type == "duplicate" or is_duplicate:
            score += 0.35

        if vendor_risk_score is not None:
            score += min(max(float(vendor_risk_score), 0.0), 1.0) * 0.2

        if prior_disputes >= 5:
            score += 0.2
        elif prior_disputes >= 2:
            score += 0.1

        return round(min(score, 1.0), 3)

    def local_decide(risk):
        if risk < 0.3:
            return "auto_approve"
        elif risk < 0.7:
            return "manual_review"
        else:
            return "auto_reject"

    # ── Breakdown helper ──
    def score_breakdown(variance_amount, invoice_total, mismatch_type,
                        vendor_risk_score, prior_disputes, is_duplicate):
        items = []
        va = float(variance_amount or 0)
        it = float(invoice_total or 0)

        if va > 5000:
            items.append(("Variance > $5,000", 0.45))
        elif va > 1000:
            items.append(("Variance $1,000–$5,000", 0.25))
        else:
            items.append(("Variance ≤ $1,000", 0.0))

        if it > 0:
            r = va / it
            if r > 0.2:
                items.append((f"Variance ratio {r:.1%} > 20%", 0.20))
            elif r > 0.08:
                items.append((f"Variance ratio {r:.1%} > 8%", 0.10))
            else:
                items.append((f"Variance ratio {r:.1%} ≤ 8%", 0.0))

        if mismatch_type == "duplicate" or is_duplicate:
            items.append(("Duplicate suspected", 0.35))
        else:
            items.append(("Not duplicate", 0.0))

        if vendor_risk_score is not None:
            contrib = round(min(max(float(vendor_risk_score), 0), 1) * 0.2, 3)
            items.append((f"Vendor risk score × 0.2 ({vendor_risk_score:.2f})", contrib))

        if prior_disputes >= 5:
            items.append((f"Prior disputes {prior_disputes} ≥ 5", 0.20))
        elif prior_disputes >= 2:
            items.append((f"Prior disputes {prior_disputes} ≥ 2", 0.10))
        else:
            items.append((f"Prior disputes {prior_disputes} < 2", 0.0))

        return items

    # ── UI ──
    col_l, col_r = st.columns([1, 1], gap="large")

    with col_l:
        st.markdown('<div class="section-label">Input Parameters</div>', unsafe_allow_html=True)
        sim_variance = st.number_input("Variance Amount ($)", value=1500.0, step=100.0, key="sim_var")
        sim_total = st.number_input("Invoice Total ($)", value=10000.0, step=500.0, key="sim_tot")
        sim_mismatch = st.selectbox("Mismatch Type", [
            "price_variance", "duplicate", "quantity_variance", "tax_variance", "unknown"
        ], key="sim_mis")
        sim_vendor_risk = st.slider("Vendor Risk Score", 0.0, 1.0, 0.5, 0.01, key="sim_vrs")
        sim_disputes = st.number_input("Prior Disputes (90d)", value=2, step=1, key="sim_dis")
        sim_duplicate = st.checkbox("Is Duplicate Suspected?", value=False, key="sim_dup")

    risk_val = local_compute_risk(
        sim_variance, sim_total, sim_mismatch,
        sim_vendor_risk, int(sim_disputes), sim_duplicate
    )
    decision_val = local_decide(risk_val)
    breakdown = score_breakdown(
        sim_variance, sim_total, sim_mismatch,
        sim_vendor_risk, int(sim_disputes), sim_duplicate
    )

    with col_r:
        st.markdown('<div class="section-label">Result</div>', unsafe_allow_html=True)
        color = risk_color(risk_val)
        bar_w = int(risk_val * 100)

        st.markdown(f"""
        <div class="result-card {card_class(decision_val)}" style="margin-top:0">
          <div class="result-header">
            <div class="inv-id">SIMULATED INVOICE</div>
            {badge_html(decision_val)}
          </div>
          <div style="font-size:48px;font-weight:700;color:{color};
               font-family:'Space Mono',monospace;line-height:1;margin:12px 0 8px 0;">
            {risk_val:.3f}
          </div>
          <div style="font-size:11px;color:var(--text-secondary);margin-bottom:12px;">RISK SCORE</div>
          <div class="risk-bar-bg">
            <div class="risk-bar-fill" style="width:{bar_w}%;background:{color};"></div>
          </div>
          <div style="display:flex;justify-content:space-between;font-size:10px;
               font-family:'Space Mono',monospace;color:var(--text-dim);margin-top:-8px;">
            <span>0.0 AUTO APPROVE</span><span>0.3</span><span>0.7</span><span>1.0 AUTO REJECT</span>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # Score breakdown table
        st.markdown('<div class="section-label" style="margin-top:20px;">Score Breakdown</div>', unsafe_allow_html=True)
        for label, contrib in breakdown:
            bar_c = "var(--border)" if contrib == 0 else color
            txt_c = "var(--text-dim)" if contrib == 0 else "var(--text-primary)"
            pct = int(contrib * 100)
            st.markdown(f"""
            <div style="display:flex;justify-content:space-between;align-items:center;
                 padding:6px 0;border-bottom:1px solid #111825;">
              <span style="font-size:12px;color:{txt_c};">{label}</span>
              <span style="font-family:'Space Mono',monospace;font-size:12px;
                   color:{bar_c if contrib > 0 else 'var(--text-dim)'};font-weight:600;">
                +{contrib:.2f}
              </span>
            </div>
            """, unsafe_allow_html=True)

        total_check = sum(c for _, c in breakdown)
        st.markdown(f"""
        <div style="display:flex;justify-content:space-between;padding:8px 0;
             font-family:'Space Mono',monospace;">
          <span style="font-size:12px;color:var(--text-secondary);font-weight:600;">TOTAL (capped at 1.0)</span>
          <span style="font-size:14px;color:{color};font-weight:700;">{risk_val:.3f}</span>
        </div>
        """, unsafe_allow_html=True)

    # ── Threshold guide ──
    st.markdown('<div class="section-label" style="margin-top:28px;">Decision Thresholds (decision_engine.py)</div>', unsafe_allow_html=True)
    st.markdown("""
    <div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:20px;">
      <div class="metric-card" style="border-left:3px solid var(--green);">
        <div class="metric-label">Auto Approve</div>
        <div style="font-size:22px;font-weight:700;color:var(--green);font-family:'Space Mono',monospace;">risk &lt; 0.3</div>
        <div style="font-size:11px;color:var(--text-dim);margin-top:6px;">Low variance, trusted vendor,<br>no duplicate flags</div>
      </div>
      <div class="metric-card" style="border-left:3px solid var(--yellow);">
        <div class="metric-label">Manual Review</div>
        <div style="font-size:22px;font-weight:700;color:var(--yellow);font-family:'Space Mono',monospace;">0.3 – 0.7</div>
        <div style="font-size:11px;color:var(--text-dim);margin-top:6px;">Moderate risk signals,<br>human judgment needed</div>
      </div>
      <div class="metric-card" style="border-left:3px solid var(--red);">
        <div class="metric-label">Auto Reject</div>
        <div style="font-size:22px;font-weight:700;color:var(--red);font-family:'Space Mono',monospace;">risk ≥ 0.7</div>
        <div style="font-size:11px;color:var(--text-dim);margin-top:6px;">High risk vendor, duplicate,<br>large variance amount</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

# ─── Footer ──────────────────────────────────────────────────────────────────
st.markdown("""
<div style="margin-top:48px;padding-top:18px;border-top:1px solid var(--border);
text-align:center;font-size:9px;color:var(--text-dim);
font-family:'Space Mono',monospace;letter-spacing:0.14em;">
AUTONOMOUS FINANCE AGENT &nbsp;·&nbsp; INVOICE INTELLIGENCE PLATFORM &nbsp;·&nbsp; v1.1.0
</div>
""", unsafe_allow_html=True)