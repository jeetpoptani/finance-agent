import sys, os, json, time, io, base64
from datetime import datetime, timezone
from uuid import uuid4
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# ── path setup ──────────────────────────────────────────────────────────────
_here     = os.path.dirname(os.path.abspath(__file__))
_app_root = os.path.join(_here, "finance-agent")
sys.path.insert(0, _app_root)

import streamlit as st
import pandas as pd

from app.services.analyzer       import analyze
from app.services.risk_engine    import compute_risk
from app.services.decision_engine import decide
from app.services.executor       import execute
from app.services.learning       import log_case

# scanner lives next to this file
try:
    from scanner import scan_invoice
    SCANNER_OK = True
except ImportError:
    SCANNER_OK = False

# ── page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Finance Agent",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ════════════════════════════════════════════════════════════════════════════
#  LIGHT THEME CSS  — clean, airy, big readable text
# ════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

/* ── Tokens ── */
:root {
    --bg:          #F5F7FA;
    --surface:     #FFFFFF;
    --surface2:    #F0F2F6;
    --border:      #DDE1EA;
    --border-dark: #C5CAD6;
    --text-1:      #111827;
    --text-2:      #374151;
    --text-3:      #6B7280;
    --text-4:      #9CA3AF;
    --blue:        #2563EB;
    --blue-lt:     #EFF6FF;
    --green:       #059669;
    --green-lt:    #ECFDF5;
    --amber:       #D97706;
    --amber-lt:    #FFFBEB;
    --red:         #DC2626;
    --red-lt:      #FEF2F2;
    --purple:      #7C3AED;
    --purple-lt:   #F5F3FF;
    --radius:      12px;
    --shadow:      0 1px 3px rgba(0,0,0,.08), 0 4px 16px rgba(0,0,0,.04);
    --shadow-md:   0 4px 12px rgba(0,0,0,.10), 0 8px 32px rgba(0,0,0,.06);
}

/* ── Global reset ── */
html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    background-color: var(--bg) !important;
    color: var(--text-1) !important;
}
.stApp {
    background-color: var(--bg) !important;
}

/* ── Toolbar / header ── */
[data-testid="stToolbar"],
[data-testid="stDecoration"],
header[data-testid="stHeader"] {
    background: var(--surface) !important;
    border-bottom: 1px solid var(--border) !important;
}
[data-testid="stAppDeployButton"] { display:none !important; }

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 1px solid var(--border) !important;
}
section[data-testid="stSidebar"] * { color: var(--text-2) !important; }
section[data-testid="stSidebar"] h3 {
    color: var(--text-1) !important;
    font-size: 13px !important;
    font-weight: 700 !important;
    letter-spacing: .03em !important;
}
section[data-testid="stSidebar"] .stRadio label {
    font-size: 15px !important;
    font-weight: 500 !important;
    color: var(--text-2) !important;
    padding: 6px 0 !important;
    text-transform: none !important;
    letter-spacing: 0 !important;
}
section[data-testid="stSidebar"] hr { border-color: var(--border) !important; }

/* ── Block container ── */
.block-container {
    padding: 5rem 2.5rem 3rem 2.5rem !important;
    max-width: 1400px !important;
}

/* ── Typography — ALL headings bigger ── */
h1 { font-size: 2rem   !important; font-weight: 800 !important; color: var(--text-1) !important; line-height: 1.2 !important; }
h2 { font-size: 1.5rem !important; font-weight: 700 !important; color: var(--text-1) !important; }
h3 { font-size: 1.2rem !important; font-weight: 600 !important; color: var(--text-1) !important; }
p, li { font-size: 15px !important; color: var(--text-2) !important; line-height: 1.7 !important; }

/* ── Section header ── */
.sec-head {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: .12em;
    text-transform: uppercase;
    color: var(--text-4);
    margin: 28px 0 14px 0;
    display: flex;
    align-items: center;
    gap: 10px;
}
.sec-head::after { content:''; flex:1; height:1px; background:var(--border); }

/* ── Page title bar ── */
.page-banner {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 22px 28px;
    display: flex;
    align-items: center;
    gap: 18px;
    margin-bottom: 28px;
    box-shadow: var(--shadow);
}
.banner-icon {
    width: 52px; height: 52px;
    background: linear-gradient(135deg, #2563EB, #0EA5E9);
    border-radius: 14px;
    display: flex; align-items: center; justify-content: center;
    font-size: 24px;
    flex-shrink: 0;
}
.banner-title { font-size: 22px; font-weight: 800; color: var(--text-1); line-height: 1.2; }
.banner-sub   { font-size: 13px; color: var(--text-3); margin-top: 3px; font-family: 'JetBrains Mono', monospace; }
.banner-pill {
    margin-left: auto;
    display: flex; align-items: center; gap: 7px;
    background: var(--green-lt);
    color: var(--green);
    border-radius: 20px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 600;
}
.pulse {
    width: 7px; height: 7px; border-radius: 50%;
    background: var(--green);
    animation: pulse 2s ease-in-out infinite;
}
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.3} }

/* ── Stat cards ── */
.stat-grid { display: grid; grid-template-columns: repeat(auto-fit,minmax(150px,1fr)); gap: 14px; margin-bottom: 24px; }
.stat-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 20px 22px;
    box-shadow: var(--shadow);
}
.stat-label { font-size: 12px; font-weight: 600; color: var(--text-4); text-transform: uppercase; letter-spacing: .08em; margin-bottom: 8px; }
.stat-value { font-size: 32px; font-weight: 800; line-height: 1; font-family: 'JetBrains Mono', monospace; }
.stat-value.blue   { color: var(--blue); }
.stat-value.green  { color: var(--green); }
.stat-value.amber  { color: var(--amber); }
.stat-value.red    { color: var(--red); }
.stat-value.purple { color: var(--purple); }

/* ── Decision badges ── */
.badge {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 5px 12px; border-radius: 20px;
    font-size: 12px; font-weight: 700;
    letter-spacing: .04em; text-transform: uppercase;
}
.badge::before { content:''; width:6px; height:6px; border-radius:50%; }
.badge-approve { background:var(--green-lt);  color:var(--green);  border:1px solid #A7F3D0; }
.badge-approve::before { background:var(--green); }
.badge-review  { background:var(--amber-lt);  color:var(--amber);  border:1px solid #FDE68A; }
.badge-review::before  { background:var(--amber); }
.badge-reject  { background:var(--red-lt);    color:var(--red);    border:1px solid #FECACA; }
.badge-reject::before  { background:var(--red); }

/* ── Result card ── */
.result-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 24px 26px;
    margin-bottom: 14px;
    box-shadow: var(--shadow);
    transition: box-shadow .2s, border-color .2s;
}
.result-card:hover { box-shadow: var(--shadow-md); border-color: var(--border-dark); }
.result-card.approve { border-left: 4px solid var(--green); }
.result-card.review  { border-left: 4px solid var(--amber); }
.result-card.reject  { border-left: 4px solid var(--red); }
.result-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; }
.inv-id { font-family:'JetBrains Mono',monospace; font-size:14px; font-weight:600; color:var(--text-1); }
.risk-track { height:5px; background:var(--border); border-radius:3px; margin:12px 0 18px; }
.risk-fill  { height:5px; border-radius:3px; }
.detail-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:14px; }
.detail-item { font-size:11px; font-weight:700; letter-spacing:.08em; text-transform:uppercase; color:var(--text-4); }
.detail-item span { display:block; font-size:14px; font-weight:500; color:var(--text-2); margin-top:4px; text-transform:none; letter-spacing:0; }
.explanation {
    margin-top: 14px;
    padding: 12px 16px;
    background: var(--surface2);
    border-radius: 8px;
    font-size: 14px;
    color: var(--text-2);
    line-height: 1.65;
    font-style: italic;
}

/* ── Log entries ── */
.log-row {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 9px;
    padding: 12px 18px;
    margin-bottom: 7px;
    display: flex;
    align-items: center;
    gap: 14px;
    font-size: 13px;
    transition: background .15s;
}
.log-row:hover { background: var(--surface2); }
.log-id { font-family:'JetBrains Mono',monospace; font-weight:600; color:var(--blue); font-size:13px; }
.log-sep { color:var(--border-dark); }
.d-approve { color:var(--green); font-weight:700; }
.d-review  { color:var(--amber); font-weight:700; }
.d-reject  { color:var(--red);   font-weight:700; }
.log-risk  { color:var(--text-3); }

/* ── Scan feed card ── */
.scan-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 9px;
    padding: 11px 16px;
    margin-bottom: 6px;
    font-size: 13px;
    display: flex;
    align-items: flex-start;
    gap: 12px;
    box-shadow: var(--shadow);
    animation: slideIn .2s ease;
}
@keyframes slideIn { from{opacity:0;transform:translateY(-4px)} to{opacity:1;transform:none} }
.scan-file { font-family:'JetBrains Mono',monospace; font-weight:600; color:var(--blue); flex-shrink:0; }
.scan-body  { flex:1; color:var(--text-2); }
.scan-meta  { font-size:11px; color:var(--text-4); margin-top:3px; font-family:'JetBrains Mono',monospace; }

/* ── Inputs — light theme ── */
input, textarea, select,
[data-baseweb="input"] input,
[data-baseweb="textarea"] textarea,
.stTextInput input, .stNumberInput input, .stTextArea textarea {
    background: var(--surface) !important;
    border: 1.5px solid var(--border) !important;
    color: var(--text-1) !important;
    border-radius: 8px !important;
    font-size: 14px !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}
input:focus, textarea:focus {
    border-color: var(--blue) !important;
    box-shadow: 0 0 0 3px rgba(37,99,235,.12) !important;
    outline: none !important;
}
[data-baseweb="input"], [data-baseweb="base-input"],
[data-baseweb="input"] > div, [data-baseweb="base-input"] > div {
    background: var(--surface) !important;
    border-color: var(--border) !important;
    border-radius: 8px !important;
}
[data-baseweb="select"] > div, [data-baseweb="select"] > div > div {
    background: var(--surface) !important;
    border-color: var(--border) !important;
    border-radius: 8px !important;
    color: var(--text-1) !important;
    font-size: 14px !important;
}
[data-baseweb="select"] span, [data-baseweb="select"] div { color:var(--text-1) !important; }
[data-baseweb="popover"] { background:var(--surface) !important; border:1px solid var(--border) !important; border-radius:10px !important; box-shadow:var(--shadow-md) !important; }
[data-baseweb="menu"]    { background:var(--surface) !important; }
[role="option"]          { background:var(--surface) !important; color:var(--text-1) !important; font-size:14px !important; }
[role="option"]:hover, [role="option"][aria-selected="true"] { background:var(--blue-lt) !important; }
[data-testid="stNumberInput"] > div, [data-testid="stNumberInput"] [data-baseweb="input"] { background:var(--surface) !important; border-color:var(--border) !important; }
[data-testid="stNumberInput"] button { background:var(--surface2) !important; border:none !important; border-left:1px solid var(--border) !important; color:var(--text-3) !important; }
[data-testid="stNumberInput"] button:hover { background:var(--border) !important; color:var(--text-1) !important; }

/* Labels */
label, .stTextInput label, .stNumberInput label, .stSelectbox label,
.stSlider label, .stCheckbox label, .stTextArea label,
.stFileUploader label, .stRadio label,
[data-testid="stWidgetLabel"] {
    font-size: 13px !important;
    font-weight: 600 !important;
    color: var(--text-2) !important;
    text-transform: none !important;
    letter-spacing: 0 !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}

/* Buttons */
.stButton > button {
    background: var(--blue) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 9px !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-weight: 700 !important;
    font-size: 14px !important;
    padding: 11px 26px !important;
    transition: all .18s !important;
    box-shadow: 0 2px 8px rgba(37,99,235,.25) !important;
    letter-spacing: .01em !important;
}
.stButton > button:hover { background: #1d4ed8 !important; box-shadow: 0 4px 16px rgba(37,99,235,.38) !important; transform:translateY(-1px) !important; }
.stButton > button:active { transform:translateY(0) !important; }

/* Progress */
[data-testid="stProgressBar"] > div { background:var(--border) !important; border-radius:6px !important; }
[data-testid="stProgressBar"] > div > div { background:var(--blue) !important; border-radius:6px !important; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] { background:transparent !important; border-bottom:2px solid var(--border) !important; }
.stTabs [data-baseweb="tab"] { font-size:14px !important; font-weight:600 !important; color:var(--text-3) !important; background:transparent !important; padding:10px 20px !important; border-bottom:2px solid transparent !important; margin-bottom:-2px !important; }
.stTabs [aria-selected="true"] { color:var(--blue) !important; border-bottom-color:var(--blue) !important; }

/* Expander */
details, [data-testid="stExpander"] { background:var(--surface) !important; border:1px solid var(--border) !important; border-radius:var(--radius) !important; box-shadow:var(--shadow) !important; }
details summary, [data-testid="stExpander"] > div:first-child { background:var(--surface) !important; color:var(--text-2) !important; font-size:14px !important; font-weight:600 !important; }
[data-testid="stExpander"] > div { background:var(--surface) !important; border-top:1px solid var(--border) !important; }

/* Checkbox */
[data-baseweb="checkbox"] > div { background:var(--surface) !important; border-color:var(--border-dark) !important; border-radius:5px !important; }
[data-baseweb="checkbox"] > div[data-checked="true"] { background:var(--blue) !important; border-color:var(--blue) !important; }

/* Slider */
[data-testid="stSlider"] [role="slider"] { background:var(--blue) !important; border-color:var(--blue) !important; box-shadow:0 0 0 3px rgba(37,99,235,.18) !important; }

/* File uploader */
[data-testid="stFileUploader"] section {
    background: var(--blue-lt) !important;
    border: 2px dashed #93C5FD !important;
    border-radius: 12px !important;
    transition: border-color .2s, background .2s !important;
}
[data-testid="stFileUploader"] section:hover { border-color:var(--blue) !important; background:#EFF6FF !important; }

/* Native metrics */
[data-testid="metric-container"] { background:var(--surface) !important; border:1px solid var(--border) !important; border-radius:var(--radius) !important; padding:18px !important; box-shadow:var(--shadow) !important; }
[data-testid="stMetricLabel"]  { font-size:12px !important; font-weight:700 !important; color:var(--text-4) !important; text-transform:uppercase !important; letter-spacing:.06em !important; }
[data-testid="stMetricValue"]  { font-size:28px !important; font-weight:800 !important; color:var(--text-1) !important; font-family:'JetBrains Mono',monospace !important; }

/* Alerts */
[data-testid="stAlert"] { background:var(--surface) !important; border-radius:10px !important; font-size:14px !important; }

/* Download btn */
[data-testid="stDownloadButton"] button { background:var(--surface2) !important; border:1.5px solid var(--border) !important; color:var(--text-2) !important; font-size:13px !important; font-weight:600 !important; border-radius:8px !important; }
[data-testid="stDownloadButton"] button:hover { border-color:var(--blue) !important; color:var(--blue) !important; background:var(--blue-lt) !important; }

/* Dataframe */
.stDataFrame { border-radius:var(--radius) !important; overflow:hidden !important; border:1px solid var(--border) !important; box-shadow:var(--shadow) !important; }

/* HR */
hr { border-color:var(--border) !important; }

/* Spinner */
.stSpinner > div { border-top-color:var(--blue) !important; }

/* Scrollbar */
::-webkit-scrollbar { width:6px; height:6px; }
::-webkit-scrollbar-track { background:var(--surface2); }
::-webkit-scrollbar-thumb { background:var(--border-dark); border-radius:4px; }
</style>
""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ════════════════════════════════════════════════════════════════════════════
def _process_one(data: dict) -> dict:
    analysis    = analyze(data)
    risk        = compute_risk(data)
    decision    = decide(analysis, risk)
    result      = execute(decision, data)
    request_id  = str(uuid4())
    processed_at = datetime.now(timezone.utc).isoformat()
    log_case(data=data, analysis=analysis, risk=risk,
             decision=decision, result=result,
             request_id=request_id, processed_at=processed_at)
    return {"analysis": analysis, "risk_score": risk, "decision": decision,
            "result": result,
            "meta": {"request_id": request_id, "processed_at": processed_at,
                     "analysis_source": analysis.get("source","rules_fallback")}}


def _badge(decision):
    m = {"auto_approve":("approve","✅ Auto Approve"),
         "manual_review":("review","🔍 Manual Review"),
         "auto_reject":  ("reject","❌ Auto Reject")}
    cls, label = m.get(decision, ("review", decision.replace("_"," ").title()))
    return f'<span class="badge badge-{cls}">{label}</span>'


def _risk_color(s):
    return "var(--green)" if s < .35 else ("var(--amber)" if s < .65 else "var(--red)")


def _card_cls(d):
    return {"auto_approve":"approve","auto_reject":"reject"}.get(d,"review")


def _risk_cls(s):
    return "green" if s < .35 else ("amber" if s < .65 else "red")


def render_result_card(item):
    d   = item.get("decision","")
    risk = item.get("risk_score", 0)
    an  = item.get("analysis",{})
    res = item.get("result",{})
    meta= item.get("meta",{})
    data= item.get("data",{})

    inv_id   = data.get("invoice_id", meta.get("request_id","—")[:8])
    vendor   = data.get("vendor_id","—")
    mismatch = data.get("mismatch_type","—").replace("_"," ").title()
    variance = data.get("variance_amount",0)
    currency = data.get("currency","USD")
    color    = _risk_color(risk)
    bw       = int(risk*100)
    source   = meta.get("analysis_source","—")
    expl     = an.get("explanation","")

    st.markdown(f"""
    <div class="result-card {_card_cls(d)}">
      <div class="result-header">
        <div class="inv-id">{inv_id}</div>
        {_badge(d)}
      </div>
      <div class="risk-track">
        <div class="risk-fill" style="width:{bw}%;background:{color};"></div>
      </div>
      <div class="detail-grid">
        <div class="detail-item">Risk Score
          <span style="font-size:22px;font-weight:800;color:{color};font-family:'JetBrains Mono',monospace;">{risk:.3f}</span>
        </div>
        <div class="detail-item">Vendor<span>{vendor}</span></div>
        <div class="detail-item">Mismatch<span>{mismatch}</span></div>
        <div class="detail-item">Variance<span>{currency} {variance:,.2f}</span></div>
        <div class="detail-item">Status<span>{res.get("status","—").upper()}</span></div>
        <div class="detail-item">AI Source<span>{source}</span></div>
      </div>
      {"<div class='explanation'>" + expl[:260] + ("…" if len(expl)>260 else "") + "</div>" if expl else ""}
    </div>
    """, unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### ⬡ Finance Agent")
    page = st.radio(
        "nav",
        ["Single Invoice", "Batch Processing", "Invoice Scanner",
         "Log Viewer", "Risk Simulator"],
        label_visibility="collapsed",
    )
    st.markdown("---")
    st.markdown(
        "<div style='font-size:13px;color:#9CA3AF;line-height:1.9;'>"
        "Services run locally.<br>Groq API optional.</div>",
        unsafe_allow_html=True,
    )

# ════════════════════════════════════════════════════════════════════════════
#  BANNER
# ════════════════════════════════════════════════════════════════════════════
PAGE_ICONS = {
    "Single Invoice":    "📄",
    "Batch Processing":  "📦",
    "Invoice Scanner":   "🔍",
    "Log Viewer":        "📋",
    "Risk Simulator":    "⚙️",
}
PAGE_SUBS = {
    "Single Invoice":    "Fill in invoice details and run the full AI pipeline",
    "Batch Processing":  "Upload a JSON file with many invoices, process all at once",
    "Invoice Scanner":   "Upload real invoice images or PDFs — AI scans & processes automatically",
    "Log Viewer":        "Review past decisions, filter by risk / decision type, export CSV",
    "Risk Simulator":    "Adjust parameters with sliders and see risk score change live",
}
st.markdown(f"""
<div class="page-banner">
  <div class="banner-icon">{PAGE_ICONS.get(page,"⬡")}</div>
  <div>
    <div class="banner-title">{page}</div>
    <div class="banner-sub">{PAGE_SUBS.get(page,"")}</div>
  </div>
  <div class="banner-pill"><div class="pulse"></div>System Operational</div>
</div>
""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
#  PAGE: Single Invoice
# ════════════════════════════════════════════════════════════════════════════
if page == "Single Invoice":
    with st.expander("📋 Invoice Details", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            invoice_id   = st.text_input("Invoice ID",   value="INV-2026-0001")
            vendor_id    = st.text_input("Vendor ID",    value="VEND-ALPHA-01")
            po_id        = st.text_input("PO ID",        value="PO-10001")
            grn_id       = st.text_input("GRN ID",       value="GRN-10001")
        with c2:
            mismatch_type   = st.selectbox("Mismatch Type",
                ["price_variance","duplicate","quantity_variance","tax_variance","unknown"])
            variance_amount = st.number_input("Variance Amount ($)", value=850.0, step=50.0)
            currency        = st.selectbox("Currency", ["USD","EUR","GBP","INR","JPY"])
            detected_at     = st.text_input("Detected At (ISO)", value="2026-03-30T09:15:00Z")
        with c3:
            invoice_total    = st.number_input("Invoice Total ($)",   value=9500.0,  step=100.0)
            expected_total   = st.number_input("Expected Total ($)",  value=8650.0,  step=100.0)
            vendor_risk_score= st.slider("Vendor Risk Score", 0.0, 1.0, 0.22, 0.01)
            prior_disputes   = st.number_input("Prior Disputes (90d)", value=1, step=1)
            invoice_count    = st.number_input("Invoice Count (90d)",  value=24, step=1)

        c4, c5 = st.columns(2)
        with c4:
            is_duplicate   = st.checkbox("Is Duplicate Suspected?")
            duplicate_id   = st.text_input("Duplicate Invoice ID (if any)", value="")
        with c5:
            region        = st.selectbox("Region", ["NA","EMEA","APAC","LATAM"])
            business_unit = st.selectbox("Business Unit",
                ["manufacturing","procurement","operations","projects","construction","shared-services"])
            source_system = st.selectbox("Source System", ["sap_s4","oracle_erp","legacy_ap"])

    if st.button("▶  Process Invoice", width="stretch"):
        payload = {
            "invoice_id": invoice_id, "vendor_id": vendor_id,
            "po_id": po_id, "grn_id": grn_id,
            "mismatch_type": mismatch_type, "variance_amount": variance_amount,
            "currency": currency, "detected_at": detected_at,
            "invoice_total": invoice_total, "expected_total": expected_total,
            "vendor_risk_score": vendor_risk_score,
            "prior_dispute_count_90d": int(prior_disputes),
            "invoice_count_90d": int(invoice_count),
            "is_duplicate_suspected": is_duplicate,
            "duplicate_invoice_id": duplicate_id or None,
            "region": region, "business_unit": business_unit,
            "source_system": source_system, "tags": [], "metadata": {},
        }
        with st.spinner("Analyzing invoice…"):
            try:
                t0   = time.time()
                data = _process_one(payload)
                elapsed = time.time() - t0
                render_result_card({**data, "data": payload})
                c1, c2, c3 = st.columns(3)
                c1.metric("Risk Score", f"{data['risk_score']:.3f}")
                c2.metric("Decision",   data["decision"].replace("_"," ").title())
                c3.metric("Latency",    f"{elapsed:.2f}s")
                with st.expander("🔍 Full JSON Response"):
                    st.json(data)
            except Exception as e:
                st.error(f"Error: {e}")


# ════════════════════════════════════════════════════════════════════════════
#  PAGE: Batch Processing
# ════════════════════════════════════════════════════════════════════════════
elif page == "Batch Processing":
    st.markdown('<div class="sec-head">Upload JSON Batch</div>', unsafe_allow_html=True)
    st.markdown(
        "Upload a JSON file with key `invoices` — an array of invoice objects.",
        unsafe_allow_html=False,
    )
    uploaded_file = st.file_uploader("Choose JSON file", type=["json"])
    batch_json = None
    if uploaded_file:
        try:
            batch_json = json.loads(uploaded_file.read().decode("utf-8"))
        except Exception as e:
            st.error(f"Invalid JSON: {e}")

    if batch_json:
        invoices = batch_json.get("invoices", [])
        st.info(f"**{len(invoices)} invoices** ready to process.")

        if st.button("▶  Process Batch", width="stretch"):
            with st.spinner(f"Processing {len(invoices)} invoices…"):
                try:
                    outputs = [_process_one(inv) for inv in invoices]
                    avg_risk = sum(i["risk_score"] for i in outputs) / len(outputs)
                    summary  = {
                        "total":        len(outputs),
                        "auto_approve": sum(1 for i in outputs if i["decision"]=="auto_approve"),
                        "manual_review":sum(1 for i in outputs if i["decision"]=="manual_review"),
                        "auto_reject":  sum(1 for i in outputs if i["decision"]=="auto_reject"),
                        "average_risk": round(avg_risk, 3),
                    }
                    st.markdown('<div class="sec-head">Batch Summary</div>', unsafe_allow_html=True)
                    st.markdown(f"""
                    <div class="stat-grid">
                      <div class="stat-card"><div class="stat-label">Total</div><div class="stat-value blue">{summary["total"]}</div></div>
                      <div class="stat-card"><div class="stat-label">Auto Approved</div><div class="stat-value green">{summary["auto_approve"]}</div></div>
                      <div class="stat-card"><div class="stat-label">Manual Review</div><div class="stat-value amber">{summary["manual_review"]}</div></div>
                      <div class="stat-card"><div class="stat-label">Auto Rejected</div><div class="stat-value red">{summary["auto_reject"]}</div></div>
                      <div class="stat-card"><div class="stat-label">Avg Risk</div><div class="stat-value {_risk_cls(summary["average_risk"])}">{summary["average_risk"]:.3f}</div></div>
                    </div>
                    """, unsafe_allow_html=True)

                    st.markdown('<div class="sec-head">Invoice Results (sorted by risk)</div>', unsafe_allow_html=True)
                    sorted_out = sorted(outputs, key=lambda x: x.get("risk_score",0), reverse=True)
                    for i, item in enumerate(sorted_out):
                        item["data"] = invoices[i] if i < len(invoices) else {}
                        render_result_card(item)

                    st.markdown('<div class="sec-head">Data Table</div>', unsafe_allow_html=True)
                    rows = [{"Invoice ID":  item.get("data",{}).get("invoice_id","—"),
                             "Vendor":      item.get("data",{}).get("vendor_id","—"),
                             "Mismatch":    item.get("data",{}).get("mismatch_type","—"),
                             "Variance ($)":item.get("data",{}).get("variance_amount",0),
                             "Risk":        item.get("risk_score",0),
                             "Decision":    item.get("decision","—"),
                             "Root Cause":  item.get("analysis",{}).get("root_cause","—"),
                             "Confidence":  item.get("analysis",{}).get("confidence",0)}
                            for item in outputs]
                    st.dataframe(pd.DataFrame(rows), width="stretch")
                    with st.expander("📦 Full JSON Response"):
                        st.json({"summary": summary, "items": outputs})
                except Exception as e:
                    st.error(f"Error: {e}")


# ════════════════════════════════════════════════════════════════════════════
#  PAGE: Invoice Scanner  ← NEW
# ════════════════════════════════════════════════════════════════════════════
elif page == "Invoice Scanner":
    if not SCANNER_OK:
        st.error(
            "⚠️ `scanner.py` not found next to `streamlit_app.py`. "
            "Place `scanner.py` in the same folder as this file and restart."
        )
        st.stop()

    # ── Settings row ────────────────────────────────────────────────────────
    col_up, col_cfg = st.columns([3, 1], gap="large")
    with col_up:
        uploaded_files = st.file_uploader(
            "Drop invoice images or PDFs here — select as many as you like",
            type=["jpg","jpeg","png","webp","gif","pdf"],
            accept_multiple_files=True,
            help="JPEG · PNG · WEBP · GIF · PDF",
        )
    with col_cfg:
        st.markdown("**⚙ Settings**")
        max_workers  = st.slider("Concurrent threads", 1, 16, 8)
        show_feed    = st.checkbox("Live activity feed", value=True)
        show_preview = st.checkbox("Show image previews", value=True)

    if not uploaded_files:
        st.markdown("""
        <div style="background:var(--blue-lt);border:1.5px dashed #93C5FD;border-radius:12px;
             padding:36px;text-align:center;color:var(--text-3);font-size:15px;margin-top:10px;">
          Upload invoice files above to get started.<br>
          <span style="font-size:13px;">Supports JPEG · PNG · PDF · WEBP — hundreds or thousands at once</span>
        </div>
        """, unsafe_allow_html=True)
        st.stop()

    # ── Preview strip ────────────────────────────────────────────────────────
    if show_preview and uploaded_files:
        st.markdown('<div class="sec-head">File Preview</div>', unsafe_allow_html=True)
        imgs = [f for f in uploaded_files
                if f.name.lower().endswith((".jpg",".jpeg",".png",".webp"))]
        if imgs:
            cols = st.columns(min(len(imgs), 6))
            for i, f in enumerate(imgs[:6]):
                with cols[i]:
                    st.image(f.read(), use_container_width=True, caption=f.name[:20])
                    f.seek(0)  # reset for later reading

    total = len(uploaded_files)
    st.success(f"**{total} file(s)** ready — click **Run Scanner** to process all automatically.")

    if not st.button("▶  Run Scanner", type="primary", width="stretch"):
        st.stop()

    # ── Collect bytes ────────────────────────────────────────────────────────
    files = []
    for f in uploaded_files:
        f.seek(0)
        files.append((f.name, f.read()))

    # ── Live UI slots ────────────────────────────────────────────────────────
    st.markdown('<div class="sec-head">Live Processing</div>', unsafe_allow_html=True)
    prog_label   = st.empty()
    progress_bar = st.progress(0.0)

    st.markdown('<div class="sec-head">AI Decisions</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    s_approve = c1.empty(); s_review = c2.empty()
    s_reject  = c3.empty(); s_errors = c4.empty()

    if show_feed:
        st.markdown('<div class="sec-head">Activity Feed</div>', unsafe_allow_html=True)
        feed_slot = st.empty()

    live  = {"auto_approve":0,"manual_review":0,"auto_reject":0,"error":0}
    feed_lines: list[str] = []
    t_start = time.perf_counter()

    DECISION_ICON = {"auto_approve":"✅","auto_reject":"❌","manual_review":"🔍","error":"⚠️"}
    DECISION_COL  = {"auto_approve":"var(--green)","auto_reject":"var(--red)",
                     "manual_review":"var(--amber)","error":"var(--purple)"}

    def _tile(val, label, color):
        return (f'<div class="stat-card" style="text-align:center;">'
                f'<div class="stat-label">{label}</div>'
                f'<div class="stat-value" style="color:{color};font-size:2.4rem;">{val}</div></div>')

    def _refresh_tiles():
        s_approve.markdown(_tile(live["auto_approve"],  "Auto Approved",  "var(--green)"),  unsafe_allow_html=True)
        s_review .markdown(_tile(live["manual_review"], "Manual Review",  "var(--amber)"),  unsafe_allow_html=True)
        s_reject .markdown(_tile(live["auto_reject"],   "Auto Rejected",  "var(--red)"),    unsafe_allow_html=True)
        s_errors .markdown(_tile(live["error"],         "Errors",         "var(--purple)"), unsafe_allow_html=True)

    _refresh_tiles()

    # ── Concurrent run ────────────────────────────────────────────────────────
    # scan_invoice_pages() returns one result per page for multi-page PDFs,
    # and a one-element list for images — so we always get the right row count.
    from scanner import scan_invoice_pages

    def _run_one_file(fname, fbytes):
        """Return a list of pipeline results — one per invoice page."""
        page_results = scan_invoice_pages(fbytes, fname)
        output = []
        for scanned in page_results:
            analysis = analyze(scanned)
            risk     = compute_risk(scanned)
            decision = decide(analysis, risk)
            result   = execute(decision, scanned)
            req_id   = str(uuid4())
            proc_at  = datetime.now(timezone.utc).isoformat()
            log_case(data=scanned, analysis=analysis, risk=risk, decision=decision,
                     result=result, request_id=req_id, processed_at=proc_at)
            output.append({
                "filename":      scanned.get("_filename", fname),
                "scanned_fields":scanned,
                "analysis":      analysis,
                "risk_score":    risk,
                "decision":      decision,
                "result":        result,
                "meta": {
                    "request_id":  req_id,
                    "processed_at":proc_at,
                    "scan_source": scanned.get("_scan_source","unknown"),
                    "page_number": scanned.get("_page_number", 1),
                    "total_pages": scanned.get("_total_pages", 1),
                    "source_file": scanned.get("_source_file", fname),
                },
            })
        return output

    # results_list holds *expanded* rows (one per invoice page, not per file)
    results_list: list[dict] = []
    results_lock = __import__("threading").Lock()

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_map = {pool.submit(_run_one_file, fname, fbytes): (fname, fbytes)
                      for fname, fbytes in files}

        done_count = 0
        for future in as_completed(future_map):
            fname, _ = future_map[future]
            try:
                page_rows = future.result()
            except Exception as exc:
                page_rows = [{"filename":fname,"error":str(exc),"decision":"error",
                               "risk_score":0.0,"analysis":{"root_cause":"error","explanation":str(exc)},
                               "scanned_fields":{},"meta":{}}]

            with results_lock:
                results_list.extend(page_rows)

            done_count += 1

            # ── Update tiles & feed — iterate over each page row ──
            for res in page_rows:
                dec = res.get("decision","error")
                live[dec] = live.get(dec,0) + 1

                if show_feed:
                    sf    = res.get("scanned_fields",{})
                    meta  = res.get("meta",{})
                    inv   = sf.get("invoice_id", res.get("filename", fname))
                    pg    = meta.get("page_number","")
                    tp    = meta.get("total_pages","")
                    pg_str = f" p{pg}/{tp}" if tp and int(tp) > 1 else ""
                    risk  = res.get("risk_score",0)
                    root  = res.get("analysis",{}).get("root_cause","—")
                    expl  = res.get("analysis",{}).get("explanation","")[:100]
                    dcol  = DECISION_COL.get(dec,"var(--text-3)")
                    icon  = DECISION_ICON.get(dec,"⚠️")
                    rc    = _risk_color(risk)
                    disp_name = res.get("filename", fname)[:28]
                    scan_src   = sf.get("_scan_source", "")
                    scan_notes = sf.get("notes", "")
                    is_fallback = scan_src == "fallback"
                    # Show the actual scan failure reason if it fell back
                    detail = scan_notes[:120] if is_fallback else expl[:100]
                    fallback_warn = (
                        f' &nbsp;·&nbsp; <span style="color:var(--red);font-weight:600;">'
                        f'⚠ scan fallback</span>'
                    ) if is_fallback else ""
                    card = (
                        f'<div class="scan-card" style="{"border-left:3px solid var(--red);" if is_fallback else ""}">'
                        f'<span class="scan-file">{disp_name}{pg_str}</span>'
                        f'<div class="scan-body">'
                        f'<span style="color:{dcol};font-weight:700;">{icon} {dec.replace("_"," ").upper()}</span>'
                        f' &nbsp;·&nbsp; risk <b style="color:{rc}">{risk:.2f}</b>'
                        f' &nbsp;·&nbsp; <span style="color:var(--blue)">{root}</span>'
                        f'{fallback_warn}'
                        f'<div class="scan-meta" style="{"color:var(--red);" if is_fallback else ""}">'
                        f'{inv} &nbsp;—&nbsp; {detail}</div>'
                        f'</div></div>'
                    )
                    feed_lines.insert(0, card)
                    if len(feed_lines) > 80: feed_lines.pop()

            _refresh_tiles()
            if show_feed:
                feed_slot.markdown("".join(feed_lines), unsafe_allow_html=True)

            # ── Progress (tracks files, not pages) ──
            elapsed = time.perf_counter() - t_start
            eta = (elapsed/done_count)*(total-done_count) if done_count else 0
            total_rows = len(results_list)
            prog_label.markdown(
                f'<div style="font-size:14px;color:var(--text-3);margin-bottom:6px;">'
                f'Files <b style="color:var(--text-1)">{done_count}/{total}</b> &nbsp;·&nbsp; '
                f'<b style="color:var(--text-1)">{total_rows}</b> invoices extracted &nbsp;·&nbsp; '
                f'{done_count/total*100:.0f}% &nbsp;·&nbsp; '
                f'⏱ {elapsed:.0f}s elapsed &nbsp;·&nbsp; ETA {eta:.0f}s</div>',
                unsafe_allow_html=True,
            )
            progress_bar.progress(done_count / total)

    elapsed_total = time.perf_counter() - t_start
    total_rows = len(results_list)
    prog_label.markdown(
        f'<div style="font-size:14px;color:var(--green);font-weight:700;">'
        f'✅ Done — {total} files · {total_rows} invoices in {elapsed_total:.1f}s '
        f'({total_rows/elapsed_total:.1f} invoices/sec)</div>',
        unsafe_allow_html=True,
    )
    progress_bar.progress(1.0)

    # ── Results dashboard ────────────────────────────────────────────────────
    st.markdown('<div class="sec-head">Results Dashboard</div>', unsafe_allow_html=True)
    valid  = [r for r in results_list if r and "error" not in r]
    errors = [r for r in results_list if r and "error" in r]
    avg_r  = sum(r["risk_score"] for r in valid)/len(valid) if valid else 0.0

    st.markdown(f"""
    <div class="stat-grid">
      <div class="stat-card"><div class="stat-label">Total Scanned</div><div class="stat-value blue">{len(results_list)}</div></div>
      <div class="stat-card"><div class="stat-label">Auto Approved</div><div class="stat-value green">{live["auto_approve"]}</div></div>
      <div class="stat-card"><div class="stat-label">Manual Review</div><div class="stat-value amber">{live["manual_review"]}</div></div>
      <div class="stat-card"><div class="stat-label">Auto Rejected</div><div class="stat-value red">{live["auto_reject"]}</div></div>
      <div class="stat-card"><div class="stat-label">Avg Risk</div><div class="stat-value {_risk_cls(avg_r)}">{avg_r:.3f}</div></div>
    </div>
    """, unsafe_allow_html=True)

    # Charts
    if valid:
        ch1, ch2 = st.columns(2)
        from collections import Counter
        with ch1:
            st.markdown("**Root cause breakdown**")
            rc = Counter(r["analysis"].get("root_cause","unknown") for r in valid)
            st.bar_chart(pd.DataFrame(rc.items(), columns=["Cause","Count"]).set_index("Cause"))
        with ch2:
            st.markdown("**Risk score distribution**")
            risk_series = pd.Series([r["risk_score"] for r in valid], name="risk")
            bins = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
            labels = [f"{b:.1f}-{bins[i+1]:.1f}" for i, b in enumerate(bins[:-1])]
            bucketed = pd.cut(risk_series, bins=bins, labels=labels, include_lowest=True)
            dist_df = bucketed.value_counts().reindex(labels, fill_value=0).rename("Count").reset_index()
            dist_df.columns = ["Risk Range", "Count"]
            st.bar_chart(dist_df.set_index("Risk Range"))

    # Table
    st.markdown('<div class="sec-head">All Results</div>', unsafe_allow_html=True)
    rows = []
    for r in results_list:
        if not r: continue
        sf = r.get("scanned_fields",{})
        rows.append({
            "File":           r.get("filename",""),
            "Invoice ID":     sf.get("invoice_id","—"),
            "Vendor":         sf.get("vendor_id","—"),
            "Invoice Total":  sf.get("invoice_total",0),
            "Variance ($)":   sf.get("variance_amount",0),
            "Mismatch":       sf.get("mismatch_type","—"),
            "Risk Score":     r.get("risk_score",0.0),
            "Decision":       r.get("decision","error"),
            "Root Cause":     r.get("analysis",{}).get("root_cause","—"),
            "Explanation":    r.get("analysis",{}).get("explanation",r.get("error",""))[:120],
            "Scan Source":    r.get("meta",{}).get("scan_source","—"),
            "Page":           r.get("meta",{}).get("page_number",""),
            "Source File":    r.get("meta",{}).get("source_file", r.get("filename","")),
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, width='stretch', height=420)

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("⬇ Download Results CSV", data=csv,
                       file_name="scanner_results.csv", mime="text/csv",
                       width="stretch")

    # ── Scan quality diagnostics ────────────────────────────────────────────
    fallback_rows = [r for r in results_list if r and r.get("scanned_fields",{}).get("_scan_source") == "fallback"]
    groq_rows     = [r for r in results_list if r and r.get("scanned_fields",{}).get("_scan_source") == "groq_vision"]

    if fallback_rows:
        st.warning(
            f"⚠️ **{len(fallback_rows)} of {len(results_list)} invoices used fallback data** "
            f"(Groq vision scan failed). Risk scores for these are unreliable (always ~0.1 → auto-approve). "
            f"See details below."
        )
        with st.expander(f"🔍 Scan failure details ({len(fallback_rows)} pages)"):
            for r in fallback_rows:
                sf    = r.get("scanned_fields", {})
                fname = r.get("filename", "?")
                note  = sf.get("notes", "unknown error")
                st.markdown(f"- **`{fname}`** — {note}")
            st.markdown("---")
            st.markdown(
                "**How to fix:**\n"
                "1. Check your `GROQ_API_KEY` is set correctly in `.env`\n"
                "2. Check Groq API status at https://console.groq.com\n"
                "3. Lower **Concurrent threads** to 2-3 to avoid rate limits\n"
                "4. Make sure `pymupdf` is installed: `pip install pymupdf`"
            )
    elif groq_rows:
        st.success(f"✅ All {len(groq_rows)} pages scanned successfully via Groq Vision.")

    if errors:
        with st.expander(f"⚠️ {len(errors)} pipeline errors"):
            for e in errors:
                st.markdown(f"- **{e['filename']}** — `{e.get('error','')}`")


# ════════════════════════════════════════════════════════════════════════════
#  PAGE: Log Viewer
# ════════════════════════════════════════════════════════════════════════════
elif page == "Log Viewer":
    log_file     = st.text_input("Log file path", value="data/logs.jsonl")
    uploaded_log = st.file_uploader("Or upload logs.jsonl", type=["jsonl","json","txt"])

    lines = []
    if uploaded_log:
        for line in uploaded_log.read().decode("utf-8").strip().splitlines():
            try: lines.append(json.loads(line))
            except: pass
    elif log_file:
        try:
            with open(log_file) as f:
                for line in f:
                    try: lines.append(json.loads(line))
                    except: pass
        except FileNotFoundError:
            st.warning("Log file not found. Upload one above.")

    if lines:
        c1, c2, c3 = st.columns(3)
        with c1: fd = st.selectbox("Filter: Decision", ["All","auto_approve","manual_review","auto_reject"])
        with c2: fs = st.selectbox("Filter: Source",   ["All","groq_llm","groq_vision","rules_fallback"])
        with c3: mr = st.slider("Min Risk", 0.0, 1.0, 0.0, 0.05)

        filtered = [l for l in lines
                    if (fd == "All" or l.get("decision") == fd)
                    and (fs == "All" or l.get("analysis",{}).get("source") == fs)
                    and l.get("risk",0) >= mr]

        if filtered:
            decisions = [l.get("decision","") for l in filtered]
            risks     = [l.get("risk",0)      for l in filtered]
            st.markdown(f"""
            <div class="stat-grid">
              <div class="stat-card"><div class="stat-label">Entries</div><div class="stat-value blue">{len(filtered)}</div></div>
              <div class="stat-card"><div class="stat-label">Approved</div><div class="stat-value green">{decisions.count("auto_approve")}</div></div>
              <div class="stat-card"><div class="stat-label">Review</div><div class="stat-value amber">{decisions.count("manual_review")}</div></div>
              <div class="stat-card"><div class="stat-label">Rejected</div><div class="stat-value red">{decisions.count("auto_reject")}</div></div>
              <div class="stat-card"><div class="stat-label">Avg Risk</div><div class="stat-value">{sum(risks)/len(risks):.3f}</div></div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('<div class="sec-head">Log Entries (newest first)</div>', unsafe_allow_html=True)
        for entry in reversed(filtered):
            inv_id  = entry.get("data",{}).get("invoice_id", entry.get("request_id","—")[:12])
            dec     = entry.get("decision","—")
            risk    = entry.get("risk",0)
            src     = entry.get("analysis",{}).get("source","—")
            lat     = entry.get("analysis",{}).get("latency_ms")
            lat_str = f"{lat:.0f}ms" if lat else "—"
            logged  = entry.get("logged_at", entry.get("processed_at","—"))
            dc_cls  = {"auto_approve":"d-approve","manual_review":"d-review","auto_reject":"d-reject"}.get(dec,"")
            st.markdown(f"""
            <div class="log-row">
              <span class="log-id">{inv_id}</span>
              <span class="log-sep">·</span>
              <span class="{dc_cls}">{dec.replace("_"," ").upper()}</span>
              <span class="log-sep">·</span>
              <span class="log-risk">risk {risk:.3f}</span>
              <span class="log-sep">·</span>{src}
              <span class="log-sep">·</span>{lat_str}
              <span class="log-sep">·</span>
              <span style="color:var(--text-4)">{str(logged)[:19]}</span>
            </div>
            """, unsafe_allow_html=True)

        if st.button("⬇ Export Filtered Logs as CSV"):
            rows = [{"invoice_id":  e.get("data",{}).get("invoice_id",""),
                     "vendor_id":   e.get("data",{}).get("vendor_id",""),
                     "mismatch_type":e.get("data",{}).get("mismatch_type",""),
                     "variance_amount":e.get("data",{}).get("variance_amount",""),
                     "risk":        e.get("risk",""),
                     "decision":    e.get("decision",""),
                     "source":      e.get("analysis",{}).get("source",""),
                     "confidence":  e.get("analysis",{}).get("confidence",""),
                     "root_cause":  e.get("analysis",{}).get("root_cause",""),
                     "latency_ms":  e.get("analysis",{}).get("latency_ms",""),
                     "logged_at":   e.get("logged_at","")}
                    for e in filtered]
            csv = pd.DataFrame(rows).to_csv(index=False)
            st.download_button("Download CSV", csv, "finance_agent_logs.csv", "text/csv")
    else:
        st.info("No log entries yet. Process some invoices first, or upload a logs.jsonl file.")


# ════════════════════════════════════════════════════════════════════════════
#  PAGE: Risk Simulator
# ════════════════════════════════════════════════════════════════════════════
elif page == "Risk Simulator":
    st.markdown(
        "<p style='font-size:15px;color:var(--text-3);margin-bottom:20px;'>"
        "Simulate risk scores using the same logic as <code>risk_engine.py</code> — no API call needed.</p>",
        unsafe_allow_html=True,
    )

    def _local_risk(va, it, mt, vrs, pd_, dup):
        s = 0.0
        va = float(va or 0); it = float(it or 0)
        if va > 5000: s += 0.45
        elif va > 1000: s += 0.25
        if it > 0:
            r = va/it
            if r > .2: s += .2
            elif r > .08: s += .1
        if mt == "duplicate" or dup: s += .35
        if vrs is not None: s += min(max(float(vrs),0),1) * .2
        if pd_ >= 5: s += .2
        elif pd_ >= 2: s += .1
        return round(min(s, 1.0), 3)

    def _local_decide(r):
        return "auto_approve" if r < .3 else ("auto_reject" if r >= .7 else "manual_review")

    def _breakdown(va, it, mt, vrs, pd_, dup):
        items = []
        va = float(va or 0); it = float(it or 0)
        if va > 5000:   items.append(("Variance > $5,000",      0.45))
        elif va > 1000: items.append(("Variance $1,000–$5,000", 0.25))
        else:           items.append(("Variance ≤ $1,000",      0.00))
        if it > 0:
            ratio = va/it
            if ratio > .2:    items.append((f"Variance ratio {ratio:.1%} > 20%", .20))
            elif ratio > .08: items.append((f"Variance ratio {ratio:.1%} > 8%",  .10))
            else:             items.append((f"Variance ratio {ratio:.1%} ≤ 8%",  .00))
        if mt == "duplicate" or dup: items.append(("Duplicate suspected",  .35))
        else:                        items.append(("Not duplicate",         .00))
        if vrs is not None:
            c = round(min(max(float(vrs),0),1)*.2,3)
            items.append((f"Vendor risk × 0.2 ({vrs:.2f})", c))
        if pd_ >= 5:   items.append((f"Prior disputes {pd_} ≥ 5", .20))
        elif pd_ >= 2: items.append((f"Prior disputes {pd_} ≥ 2", .10))
        else:          items.append((f"Prior disputes {pd_} < 2", .00))
        return items

    col_l, col_r = st.columns([1,1], gap="large")

    with col_l:
        st.markdown('<div class="sec-head">Input Parameters</div>', unsafe_allow_html=True)
        sim_var  = st.number_input("Variance Amount ($)",   value=1500.0, step=100.0)
        sim_tot  = st.number_input("Invoice Total ($)",     value=10000.0,step=500.0)
        sim_mis  = st.selectbox("Mismatch Type",
            ["price_variance","duplicate","quantity_variance","tax_variance","unknown"])
        sim_vrs  = st.slider("Vendor Risk Score", 0.0, 1.0, 0.5, 0.01)
        sim_dis  = st.number_input("Prior Disputes (90d)", value=2, step=1)
        sim_dup  = st.checkbox("Is Duplicate Suspected?")

    rv  = _local_risk(sim_var, sim_tot, sim_mis, sim_vrs, int(sim_dis), sim_dup)
    dv  = _local_decide(rv)
    brd = _breakdown(sim_var, sim_tot, sim_mis, sim_vrs, int(sim_dis), sim_dup)
    col = _risk_color(rv)
    bw  = int(rv*100)

    with col_r:
        st.markdown('<div class="sec-head">Result</div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="result-card {_card_cls(dv)}" style="margin-top:0">
          <div class="result-header">
            <div class="inv-id">Simulated Invoice</div>
            {_badge(dv)}
          </div>
          <div style="font-size:56px;font-weight:800;color:{col};
               font-family:'JetBrains Mono',monospace;line-height:1;margin:10px 0 6px;">
            {rv:.3f}
          </div>
          <div style="font-size:13px;color:var(--text-4);font-weight:600;
               text-transform:uppercase;letter-spacing:.08em;margin-bottom:14px;">Risk Score</div>
          <div class="risk-track">
            <div class="risk-fill" style="width:{bw}%;background:{col};"></div>
          </div>
          <div style="display:flex;justify-content:space-between;font-size:11px;
               color:var(--text-4);font-weight:600;text-transform:uppercase;letter-spacing:.06em;">
            <span>0.0 Approve</span><span>0.3</span><span>0.7</span><span>1.0 Reject</span>
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="sec-head" style="margin-top:20px;">Score Breakdown</div>', unsafe_allow_html=True)
        for label, contrib in brd:
            c = col if contrib > 0 else "var(--border-dark)"
            tc = "var(--text-1)" if contrib > 0 else "var(--text-4)"
            st.markdown(f"""
            <div style="display:flex;justify-content:space-between;align-items:center;
                 padding:8px 0;border-bottom:1px solid var(--border);">
              <span style="font-size:14px;color:{tc};">{label}</span>
              <span style="font-family:'JetBrains Mono',monospace;font-size:14px;
                   color:{c};font-weight:700;">+{contrib:.2f}</span>
            </div>
            """, unsafe_allow_html=True)
        st.markdown(f"""
        <div style="display:flex;justify-content:space-between;padding:10px 0;margin-top:4px;">
          <span style="font-size:15px;font-weight:700;color:var(--text-2);">Total (capped at 1.0)</span>
          <span style="font-size:18px;font-weight:800;color:{col};
               font-family:'JetBrains Mono',monospace;">{rv:.3f}</span>
        </div>
        """, unsafe_allow_html=True)

    # Threshold guide
    st.markdown('<div class="sec-head" style="margin-top:28px;">Decision Thresholds</div>', unsafe_allow_html=True)
    st.markdown("""
    <div style="display:flex;gap:14px;flex-wrap:wrap;margin-bottom:20px;">
      <div class="stat-card" style="border-left:4px solid var(--green);flex:1;min-width:180px;">
        <div class="stat-label">Auto Approve</div>
        <div style="font-size:22px;font-weight:800;color:var(--green);font-family:'JetBrains Mono',monospace;">risk &lt; 0.3</div>
        <div style="font-size:13px;color:var(--text-3);margin-top:8px;">Low variance, trusted vendor,<br>no duplicate flags</div>
      </div>
      <div class="stat-card" style="border-left:4px solid var(--amber);flex:1;min-width:180px;">
        <div class="stat-label">Manual Review</div>
        <div style="font-size:22px;font-weight:800;color:var(--amber);font-family:'JetBrains Mono',monospace;">0.3 – 0.7</div>
        <div style="font-size:13px;color:var(--text-3);margin-top:8px;">Moderate risk — human<br>judgment needed</div>
      </div>
      <div class="stat-card" style="border-left:4px solid var(--red);flex:1;min-width:180px;">
        <div class="stat-label">Auto Reject</div>
        <div style="font-size:22px;font-weight:800;color:var(--red);font-family:'JetBrains Mono',monospace;">risk ≥ 0.7</div>
        <div style="font-size:13px;color:var(--text-3);margin-top:8px;">High risk vendor, duplicate,<br>large variance amount</div>
      </div>
    </div>
    """, unsafe_allow_html=True)


# ── Footer ──────────────────────────────────────────────────────────────────
st.markdown("""
<div style="margin-top:56px;padding-top:20px;border-top:1px solid var(--border);
text-align:center;font-size:12px;color:var(--text-4);
font-family:'JetBrains Mono',monospace;letter-spacing:.08em;">
Autonomous Finance Agent &nbsp;·&nbsp; Invoice Intelligence Platform &nbsp;·&nbsp; v1.2.0
</div>
""", unsafe_allow_html=True)