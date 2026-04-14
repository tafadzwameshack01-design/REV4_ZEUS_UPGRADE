import streamlit as st

def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Inter:wght@300;400;500;600;700&display=swap');

    /* ── Global ── */
    html, body, [data-testid="stApp"] {
        background-color: #040b04 !important;
    }
    [data-testid="stMainBlockContainer"] { padding-top: 0 !important; }

    /* ── Hero ── */
    .zeus-hero {
        text-align: center;
        padding: 1.6rem 0 1rem 0;
        background: linear-gradient(135deg, #020702 0%, #081508 50%, #020702 100%);
        border-bottom: 2px solid #39ff14;
        margin-bottom: 1rem;
    }
    .zeus-hero h1 {
        font-family: 'Orbitron', monospace;
        font-size: 2.6rem;
        color: #39ff14;
        text-shadow: 0 0 24px #39ff1499, 0 0 48px #39ff1433;
        margin: 0;
        letter-spacing: 5px;
    }
    .zeus-hero .subtitle {
        font-family: 'Inter', sans-serif;
        color: #7dff7d;
        font-size: 0.8rem;
        margin-top: 0.4rem;
        letter-spacing: 2px;
        text-transform: uppercase;
    }

    /* ── Metric bar ── */
    .metric-bar {
        display: flex;
        justify-content: center;
        flex-wrap: wrap;
        gap: 1.4rem;
        padding: 0.9rem 1rem;
        background: #0a160a;
        border-radius: 10px;
        margin-bottom: 1rem;
        border: 1px solid #1a3a1a;
    }
    .metric-item { text-align: center; }
    .metric-value {
        font-family: 'Orbitron', monospace;
        font-size: 1.7rem;
        color: #39ff14;
        font-weight: 700;
        line-height: 1.2;
    }
    .metric-label {
        font-family: 'Inter', sans-serif;
        font-size: 0.65rem;
        color: #7dff7d;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* ── Pick cards ── */
    .pick-card {
        background: linear-gradient(145deg, #0a1f0a, #0d250d);
        border: 1px solid #1a4a1a;
        border-radius: 14px;
        padding: 1.1rem 1.3rem;
        margin-bottom: 0.75rem;
        transition: border-color 0.25s, box-shadow 0.25s;
    }
    .pick-card:hover {
        border-color: #39ff14;
        box-shadow: 0 0 18px #39ff1422;
    }
    .pick-card.tier-elite {
        border-color: #ffb300;
        background: linear-gradient(145deg, #0d1b0d, #1a1400);
        animation: eliteGlow 3s ease-in-out infinite;
    }
    @keyframes eliteGlow {
        0%,100% { box-shadow: 0 0 10px rgba(255,179,0,0.12); }
        50%      { box-shadow: 0 0 32px rgba(255,179,0,0.32); }
    }
    .pick-card.tier-strong  { border-left: 4px solid #39ff14; }
    .pick-card.tier-monitoring { border-left: 4px solid #2a5a2a; opacity: 0.8; }

    /* ── Live cards ── */
    .live-card {
        background: linear-gradient(135deg, #1a0505, #250808);
        border: 1px solid #ff3939;
        border-radius: 14px;
        padding: 1.1rem 1.3rem;
        margin-bottom: 0.75rem;
        animation: liveGlow 1.8s ease-in-out infinite;
    }
    @keyframes liveGlow {
        0%,100% { box-shadow: 0 0 8px rgba(255,57,57,0.18); }
        50%      { box-shadow: 0 0 28px rgba(255,57,57,0.48); }
    }
    .live-badge {
        background: #ff3939;
        color: #fff;
        font-family: 'Orbitron', monospace;
        font-size: 0.62rem;
        font-weight: 700;
        padding: 2px 8px;
        border-radius: 4px;
        letter-spacing: 2px;
        animation: blink 1.4s infinite;
    }
    @keyframes blink {
        0%,100% { opacity: 1; }
        50%      { opacity: 0.45; }
    }
    .minute-badge {
        background: rgba(255,57,57,0.18);
        color: #ff9999;
        font-family: 'Orbitron', monospace;
        font-size: 0.75rem;
        padding: 2px 7px;
        border-radius: 4px;
        border: 1px solid rgba(255,57,57,0.25);
        margin-left: 4px;
    }

    /* ── Warmup / empty ── */
    .warmup-screen {
        text-align: center;
        padding: 3.5rem 2rem;
        background: rgba(0,229,255,0.025);
        border: 1px solid rgba(0,229,255,0.12);
        border-radius: 14px;
        margin: 1.5rem 0;
    }
    .no-picks {
        text-align: center;
        padding: 3.5rem 2rem;
        color: #7dff7d;
        font-family: 'Orbitron', monospace;
        font-size: 0.9rem;
        letter-spacing: 1.5px;
        line-height: 2;
        background: #0a160a;
        border-radius: 14px;
        border: 1px dashed #1a4a1a;
    }

    /* ── Brain & system cards ── */
    .brain-metric {
        background: #0a160a;
        border: 1px solid #1a3a1a;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.6rem;
    }
    .system-status {
        background: #0a160a;
        border: 1px solid #1a3a1a;
        border-radius: 12px;
        padding: 1rem 1.3rem;
        margin-bottom: 1rem;
    }
    .sys-row {
        display: flex;
        justify-content: space-between;
        padding: 5px 0;
        border-bottom: 1px solid rgba(57,255,20,0.04);
    }
    .sys-lbl { color: #7dff7d; font-size: 0.82rem; }
    .sys-val { color: #e0ffe0; font-size: 0.82rem; font-weight: 600; }

    /* ── Streamlit overrides ── */
    .stTabs [data-baseweb="tab"] {
        font-family: 'Orbitron', monospace !important;
        font-size: 0.78rem !important;
        letter-spacing: 1px !important;
        color: #7dff7d !important;
    }
    .stTabs [aria-selected="true"] {
        color: #39ff14 !important;
        border-bottom: 2px solid #39ff14 !important;
    }
    [data-testid="metric-container"] {
        background: #0a160a;
        border: 1px solid #1a3a1a;
        border-radius: 8px;
        padding: 0.6rem 0.8rem;
    }
    </style>
    """, unsafe_allow_html=True)
