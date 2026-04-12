"""
ZEUS v4 — Over 2.5 Goals Neural Football Intelligence System
Main Streamlit application entry point.
Run with: streamlit run app.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import pandas as pd
import numpy as np
import hashlib
from datetime import datetime, timezone

st.set_page_config(
    page_title="ZEUS ⚽ Neural Football AI v4",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={"About": "ZEUS Neural Football AI v4.0 — Over 2.5 Goals · Poisson + ML · Kelly Betting · 51 Leagues"}
)

# ══════════════════════════════════════════════════════════════════
#  CSS — Stadium-at-Night aesthetic
# ══════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Barlow+Condensed:wght@400;600;700&family=Barlow:wght@400;500&display=swap');

:root {
  --bg:       #050b05;
  --surface:  #0b170b;
  --card:     #0e1c0e;
  --border:   #1a361a;
  --green:    #39ff14;
  --green2:   #00c853;
  --gold:     #ffb300;
  --gold2:    #ff8f00;
  --cyan:     #00e5ff;
  --text:     #d4f0d4;
  --muted:    #587a58;
  --red:      #ff1744;
  --purple:   #ea80fc;
  --blue:     #29b6f6;
}

html, body, .stApp { background: var(--bg) !important; font-family: 'Barlow', sans-serif; }

.stApp::before {
  content: '';
  position: fixed; inset: 0;
  background-image:
    linear-gradient(rgba(57,255,20,0.025) 1px, transparent 1px),
    linear-gradient(90deg, rgba(57,255,20,0.025) 1px, transparent 1px);
  background-size: 60px 60px;
  animation: gridMove 25s linear infinite;
  pointer-events: none; z-index: 0;
}

@keyframes gridMove {
  0%   { background-position: 0 0, 0 0; }
  100% { background-position: 60px 60px, 60px 60px; }
}

#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 0.5rem !important; max-width: 1350px; position: relative; z-index: 1; }

.zeus-hero { text-align: center; padding: 24px 0 10px; }
.zeus-logo {
  font-family: 'Bebas Neue', cursive;
  font-size: 5.5rem; line-height: 1; letter-spacing: 12px;
  background: linear-gradient(135deg, #39ff14 0%, #69ff47 40%, #ffb300 100%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  background-clip: text; display: block;
  animation: logoGlow 4s ease-in-out infinite;
}
@keyframes logoGlow {
  0%,100% { filter: drop-shadow(0 0 8px rgba(57,255,20,0.4)); }
  50%      { filter: drop-shadow(0 0 28px rgba(57,255,20,0.9)); }
}
.zeus-tagline {
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 0.8rem; letter-spacing: 4px;
  text-transform: uppercase; color: var(--muted); margin-top: 4px;
}
.zeus-version {
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 0.68rem; letter-spacing: 3px;
  text-transform: uppercase; color: var(--cyan); margin-top: 2px; opacity: 0.7;
}
.zeus-bar {
  width: 80px; height: 2px;
  background: linear-gradient(90deg, transparent, var(--green), transparent);
  margin: 14px auto 0;
  animation: barPulse 2s ease-in-out infinite;
}
@keyframes barPulse {
  0%,100% { width: 80px; opacity: 0.6; }
  50%      { width: 200px; opacity: 1; }
}

.metrics-row { display: flex; gap: 10px; margin: 14px 0; flex-wrap: wrap; }
.metric-box {
  flex: 1; min-width: 100px;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 12px; padding: 12px 14px; text-align: center;
  transition: border-color 0.3s;
}
.metric-box:hover { border-color: var(--green); }
.metric-val { font-family: 'Bebas Neue', cursive; font-size: 2rem; color: var(--green); line-height: 1; display: block; }
.metric-val.gold   { color: var(--gold); }
.metric-val.cyan   { color: var(--cyan); }
.metric-val.purple { color: var(--purple); }
.metric-val.red    { color: var(--red); }
.metric-val.blue   { color: var(--blue); }
.metric-lbl { font-family: 'Barlow Condensed', sans-serif; font-size: 0.68rem; color: var(--muted); text-transform: uppercase; letter-spacing: 1.5px; }

.scan-line {
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 0.78rem; color: var(--green);
  letter-spacing: 3px; text-transform: uppercase;
  text-align: center; padding: 8px;
  animation: scanFade 0.9s ease-in-out infinite;
}
@keyframes scanFade { 0%,100%{opacity:1;} 50%{opacity:0.2;} }

.pick-card {
  background: var(--card); border: 1px solid var(--border);
  border-radius: 18px; padding: 22px 26px; margin: 14px 0;
  position: relative; overflow: hidden;
  opacity: 0; animation: cardReveal 0.5s ease forwards;
  transition: transform 0.25s, box-shadow 0.25s;
}
.pick-card:hover { transform: translateY(-4px); box-shadow: 0 14px 44px rgba(57,255,20,0.14); }
.pick-card:nth-child(1){animation-delay:0.04s;}
.pick-card:nth-child(2){animation-delay:0.12s;}
.pick-card:nth-child(3){animation-delay:0.20s;}
.pick-card:nth-child(4){animation-delay:0.28s;}
.pick-card:nth-child(5){animation-delay:0.36s;}
.pick-card:nth-child(6){animation-delay:0.44s;}
.pick-card:nth-child(7){animation-delay:0.52s;}
.pick-card:nth-child(8){animation-delay:0.60s;}
@keyframes cardReveal {
  from { opacity:0; transform: translateY(18px); }
  to   { opacity:1; transform: translateY(0); }
}
.pick-card.elite  { border-color: var(--gold); background: linear-gradient(135deg, #0e1c0e 0%, #1a1400 100%); animation: cardReveal 0.5s ease forwards, eliteGlow 3s ease-in-out infinite; }
@keyframes eliteGlow {
  0%,100% { box-shadow: 0 0 16px rgba(255,179,0,0.1); }
  50%      { box-shadow: 0 0 44px rgba(255,179,0,0.32), 0 0 90px rgba(255,179,0,0.07); }
}
.pick-card.strong { border-color: var(--green2); }

.rank-badge { position: absolute; top: 14px; right: 20px; font-family: 'Bebas Neue', cursive; font-size: 4rem; line-height: 1; color: rgba(57,255,20,0.05); pointer-events: none; user-select: none; }
.rank-badge.elite-rank { color: rgba(255,179,0,0.07); }

.card-league { font-family: 'Barlow Condensed', sans-serif; font-size: 0.7rem; letter-spacing: 3px; text-transform: uppercase; color: var(--muted); margin-bottom: 6px; }
.card-teams  { font-family: 'Bebas Neue', cursive; font-size: 2rem; letter-spacing: 3px; color: var(--text); line-height: 1.1; margin-bottom: 10px; }
.card-vs     { color: var(--muted); font-size: 1rem; padding: 0 8px; }
.card-bet    { font-family: 'Barlow Condensed', sans-serif; font-weight: 700; font-size: 1.5rem; letter-spacing: 1px; margin-bottom: 12px; }
.card-bet.elite  { color: var(--gold); }
.card-bet.strong { color: var(--green); }
.card-bet.good   { color: #69ff47; }

.conf-track { background: rgba(255,255,255,0.06); border-radius: 999px; height: 6px; margin: 8px 0 10px; overflow: hidden; }
.conf-fill  { height: 100%; border-radius: 999px; animation: fillBar 1.2s cubic-bezier(0.22,1,0.36,1) forwards; transform-origin: left; }
.conf-fill.elite  { background: linear-gradient(90deg, var(--gold2), var(--gold)); }
.conf-fill.strong { background: linear-gradient(90deg, var(--green2), var(--green)); }
.conf-fill.good   { background: linear-gradient(90deg, #00b341, #39ff14); }
@keyframes fillBar { from { width: 0 !important; } }

.conf-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.conf-pct { font-family: 'Bebas Neue', cursive; font-size: 1.6rem; letter-spacing: 2px; }
.conf-pct.elite  { color: var(--gold); }
.conf-pct.strong { color: var(--green); }
.conf-pct.good   { color: #69ff47; }
.tier-chip { font-family: 'Barlow Condensed', sans-serif; font-size: 0.7rem; font-weight: 700; letter-spacing: 2px; text-transform: uppercase; padding: 3px 10px; border-radius: 999px; }
.tier-chip.elite  { background: rgba(255,179,0,0.15); color: var(--gold); border: 1px solid rgba(255,179,0,0.4); }
.tier-chip.strong { background: rgba(57,255,20,0.1); color: var(--green); border: 1px solid rgba(57,255,20,0.3); }
.tier-chip.good   { background: rgba(105,255,71,0.08); color: #69ff47; border: 1px solid rgba(105,255,71,0.25); }

.pills-row { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 10px; }
.pill { font-family: 'Barlow Condensed', sans-serif; font-size: 0.73rem; letter-spacing: 1px; padding: 3px 9px; border-radius: 6px; white-space: nowrap; }
.pill-time  { background: rgba(57,255,20,0.08);  color: var(--green);  border: 1px solid rgba(57,255,20,0.2); }
.pill-xg    { background: rgba(255,179,0,0.08);  color: var(--gold);   border: 1px solid rgba(255,179,0,0.2); }
.pill-pois  { background: rgba(0,229,255,0.08);  color: var(--cyan);   border: 1px solid rgba(0,229,255,0.2); }
.pill-ml    { background: rgba(234,128,252,0.08);color: var(--purple); border: 1px solid rgba(234,128,252,0.2); }
.pill-over  { background: rgba(0,200,83,0.08);   color: #00c853;       border: 1px solid rgba(0,200,83,0.2); }
.pill-bet   { background: rgba(41,182,246,0.08); color: var(--blue);   border: 1px solid rgba(41,182,246,0.2); }
.pill-edge  { background: rgba(255,64,64,0.08);  color: #ff6464;       border: 1px solid rgba(255,64,64,0.2); }
.pill-games { background: rgba(255,255,255,0.04);color: var(--muted);  border: 1px solid rgba(255,255,255,0.08); }

.ai-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; margin-top: 10px; }
.ai-factor { background: rgba(57,255,20,0.04); border: 1px solid rgba(57,255,20,0.1); border-radius: 8px; padding: 6px 8px; text-align: center; }
.ai-factor-val { font-family: 'Bebas Neue', cursive; font-size: 1.1rem; color: var(--green); display: block; line-height: 1; }
.ai-factor-val.gold   { color: var(--gold); }
.ai-factor-val.cyan   { color: var(--cyan); }
.ai-factor-val.purple { color: var(--purple); }
.ai-factor-val.blue   { color: var(--blue); }
.ai-factor-lbl { font-family: 'Barlow Condensed', sans-serif; font-size: 0.62rem; color: var(--muted); text-transform: uppercase; letter-spacing: 1px; }

.bet-chip { font-family: 'Barlow Condensed', sans-serif; font-size: 0.75rem; font-weight: 700; letter-spacing: 1.5px; padding: 4px 12px; border-radius: 6px; display: inline-block; margin-top: 8px; }
.bet-chip.active { background: rgba(57,255,20,0.15); color: var(--green); border: 1px solid rgba(57,255,20,0.4); }
.bet-chip.skip   { background: rgba(255,255,255,0.04); color: var(--muted); border: 1px solid rgba(255,255,255,0.1); }

.card-reason { font-family: 'Barlow', sans-serif; font-size: 0.8rem; color: var(--muted); margin-top: 10px; line-height: 1.55; border-left: 2px solid var(--border); padding-left: 10px; }
.no-picks { text-align: center; padding: 52px 24px; font-family: 'Barlow Condensed', sans-serif; font-size: 1.1rem; color: var(--muted); letter-spacing: 2px; }
.no-picks-icon { font-size: 3rem; display: block; margin-bottom: 12px; }

.sim-box { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 16px 20px; margin: 10px 0; }
.sim-title { font-family: 'Barlow Condensed', sans-serif; font-size: 0.85rem; letter-spacing: 3px; text-transform: uppercase; color: var(--cyan); margin-bottom: 10px; }

hr { border-color: rgba(57,255,20,0.08) !important; }
.stTabs [data-baseweb="tab-list"] { background: var(--surface); border-radius: 12px; padding: 4px; gap: 2px; border: 1px solid var(--border); }
.stTabs [data-baseweb="tab"] { border-radius: 8px; font-family: 'Barlow Condensed', sans-serif; letter-spacing: 1px; color: var(--muted); font-size: 0.9rem; }
.stTabs [aria-selected="true"] { background: rgba(57,255,20,0.12) !important; color: var(--green) !important; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════
#  BOOT: init DB + simulation on first load
# ══════════════════════════════════════════════════════════════════

@st.cache_resource(show_spinner=False)
def _boot_system():
    from database.db import init_db
    init_db()
    from database.db import get_model_weights
    weights = get_model_weights()
    if weights is None:
        from simulation.sim_engine import run_simulation_loop
        from data.constants import RANDOM_SEED, SIM_MATCHES, SIM_MAX_ITER
        model, metrics, logs = run_simulation_loop(SIM_MATCHES, SIM_MAX_ITER, RANDOM_SEED)
        return metrics, logs
    return {}, []

boot_metrics, boot_logs = _boot_system()


# ══════════════════════════════════════════════════════════════════
#  SCANNER (cached 5 min)
# ══════════════════════════════════════════════════════════════════

@st.cache_data(ttl=300, show_spinner=False)
def _scan(confidence_min: float, league_filter_key: str):
    from services.scanner import scan_all_leagues
    from data.constants import LEAGUES

    show_europe   = league_filter_key[0] == "T"
    show_americas = league_filter_key[1] == "T"
    show_asia     = league_filter_key[2] == "T"
    show_mena     = league_filter_key[3] == "T"
    show_cups     = league_filter_key[4] == "T"

    _EUROPE   = {"eng","esp","ger","ita","fra","ned","por","bel","sco","tur",
                 "rus","aut","gre","cze","pol","den","swe","nor","sui","ukr","srb","cro"}
    _AMERICAS = {"usa","bra","arg","mex","col","chi","ecu","per","uru","ven","bol"}
    _ASIA     = {"jpn","kor","chn","aus","ind","sau"}
    _MENA     = {"egy","mar","rsa","nig"}
    _CUPS     = {"uefa","conmebol"}

    def _keep(lid):
        prefix = lid.split(".")[0]
        if prefix in _EUROPE   and show_europe:   return True
        if prefix in _AMERICAS and show_americas: return True
        if prefix in _ASIA     and show_asia:     return True
        if prefix in _MENA     and show_mena:     return True
        if prefix in _CUPS     and show_cups:     return True
        return False

    active = [lid for lid, _, _ in LEAGUES if _keep(lid)] or None
    return scan_all_leagues(confidence_min=confidence_min, league_filter=active)


def _countdown_iframe(kickoff_utc: str, pick_id: str) -> str:
    return f"""<!DOCTYPE html>
<html><body style="margin:0;background:transparent;">
<span id="cd" style="font-family:monospace;font-size:13px;color:#39ff14;letter-spacing:2px;">⏱ ...</span>
<script>
var t=new Date("{kickoff_utc}");
var el=document.getElementById("cd");
function tick(){{
  var now=new Date(),diff=t-now;
  if(diff<=0){{el.innerHTML="🔴 LIVE NOW";el.style.color="#ff1744";return;}}
  var h=Math.floor(diff/3600000),m=Math.floor((diff%3600000)/60000),s=Math.floor((diff%60000)/1000);
  var p=[];if(h>0)p.push(h+"h");p.push(("0"+m).slice(-2)+"m");p.push(("0"+s).slice(-2)+"s");
  el.innerHTML="⏱ KICKOFF IN "+p.join(" ");
}}
tick();setInterval(tick,1000);
</script></body></html>"""


def render_pick_card(pick: dict):
    tier    = pick["tier"]
    conf    = pick["conf_pct"]
    elite   = tier == "elite"
    pick_id = hashlib.md5(pick["match_label"].encode()).hexdigest()[:6]
    bar_width = min(99, int(conf))

    h2h_pill = ""
    if pick.get("h2h_over25") is not None:
        h2h_pill = f'<span class="pill pill-over">H2H O2.5: {pick["h2h_over25"]:.0f}%</span>'

    streak_html = ""
    if pick.get("home_streak", 0) >= 3:
        streak_html += f'<span class="pill pill-over">🔥 {pick["home"][:12]} {pick["home_streak"]}x</span>'
    if pick.get("away_streak", 0) >= 3:
        streak_html += f'<span class="pill pill-over">🔥 {pick["away"][:12]} {pick["away_streak"]}x</span>'

    bet_chip_cls = "active" if pick.get("bet_placed") else "skip"
    bet_chip_txt = (
        f"✅ BET PLACED — €{pick['stake']:.2f} @ {pick['odds']:.2f} | Edge: +{pick['edge']*100:.1f}%"
        if pick.get("bet_placed") else
        f"⏸ NO BET — {pick.get('bet_reason', '—')}"
    )

    card_html = f"""
<div class="pick-card {tier}">
  <div class="rank-badge {'elite-rank' if elite else ''}">#{pick.get('rank', 0)}</div>
  <div class="card-league">{pick['league']}</div>
  <div class="card-teams">{pick['home']} <span class="card-vs">vs</span> {pick['away']}</div>
  <div class="card-bet {tier}">⚽ OVER 2.5 GOALS (≥3 GOALS SCORED)</div>

  <div class="conf-row">
    <span class="conf-pct {tier}">{conf:.1f}%</span>
    <span class="tier-chip {tier}">{pick['tier_label']}</span>
  </div>
  <div class="conf-track">
    <div class="conf-fill {tier}" style="width:{bar_width}%;"></div>
  </div>

  <div class="ai-grid">
    <div class="ai-factor">
      <span class="ai-factor-val cyan">{pick['p_poisson']*100:.1f}%</span>
      <div class="ai-factor-lbl">Poisson</div>
    </div>
    <div class="ai-factor">
      <span class="ai-factor-val purple">{pick['p_ml']*100:.1f}%</span>
      <div class="ai-factor-lbl">ML Model</div>
    </div>
    <div class="ai-factor">
      <span class="ai-factor-val gold">{pick['xg_total']:.2f}</span>
      <div class="ai-factor-lbl">xG Total</div>
    </div>
    <div class="ai-factor">
      <span class="ai-factor-val">{pick['p_ensemble']*100:.1f}%</span>
      <div class="ai-factor-lbl">Ensemble</div>
    </div>
    <div class="ai-factor">
      <span class="ai-factor-val">{pick.get('home_over25', 0):.0f}%</span>
      <div class="ai-factor-lbl">Home OV2.5</div>
    </div>
    <div class="ai-factor">
      <span class="ai-factor-val">{pick.get('away_over25', 0):.0f}%</span>
      <div class="ai-factor-lbl">Away OV2.5</div>
    </div>
    <div class="ai-factor">
      <span class="ai-factor-val blue">{pick['home_form_str']}</span>
      <div class="ai-factor-lbl">Home Form</div>
    </div>
    <div class="ai-factor">
      <span class="ai-factor-val blue">{pick['away_form_str']}</span>
      <div class="ai-factor-lbl">Away Form</div>
    </div>
  </div>

  <div class="pills-row">
    <span class="pill pill-time">{pick['kickoff_cat']}</span>
    <span class="pill pill-xg">xG {pick['xg_home']:.2f}+{pick['xg_away']:.2f}</span>
    <span class="pill pill-pois">Poisson {pick['p_poisson']*100:.1f}%</span>
    <span class="pill pill-ml">ML {pick['p_ml']*100:.1f}%</span>
    <span class="pill pill-games">{pick['home_n']}+{pick['away_n']} games</span>
    {h2h_pill}
    {streak_html}
  </div>

  <div class="bet-chip {bet_chip_cls}">{bet_chip_txt}</div>
  <div class="card-reason">{pick['reasoning']}</div>
</div>"""
    st.markdown(card_html, unsafe_allow_html=True)
    st.components.v1.html(
        _countdown_iframe(pick["kickoff_utc"], pick_id),
        height=26,
        scrolling=False
    )


# ══════════════════════════════════════════════════════════════════
#  MAIN APP
# ══════════════════════════════════════════════════════════════════

def main():
    try:
        from streamlit_autorefresh import st_autorefresh
        count = st_autorefresh(interval=60_000, key="zeus_v4_refresh")
    except ImportError:
        count = 0

    st.markdown("""
<div class="zeus-hero">
  <span class="zeus-logo">⚽ ZEUS</span>
  <div class="zeus-tagline">Neural Football Intelligence · Over 2.5 Goals · Poisson + ML Ensemble · Kelly Betting</div>
  <div class="zeus-version">v4.0 · Self-Repair Simulation · Venue Splits · H2H · 51 Leagues · Auto-Refresh 60s</div>
  <div class="zeus-bar"></div>
</div>
""", unsafe_allow_html=True)

    tab_picks, tab_betting, tab_results, tab_bankroll, tab_sim, tab_about = st.tabs([
        "🎯 Picks",
        "💰 Betting Engine",
        "🏆 Results",
        "📈 Bankroll",
        "🧪 Simulation",
        "🌍 System"
    ])

    # ── SIDEBAR ──────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("### ⚙️ ZEUS Controls")
        conf_slider = st.slider(
            "Confidence Threshold",
            min_value=0.60, max_value=0.99,
            value=0.78, step=0.01,
            help="Minimum confidence to display a pick"
        )
        st.markdown("---")
        st.caption("Filter by Region")
        show_europe   = st.checkbox("Europe",           value=True)
        show_americas = st.checkbox("Americas",         value=True)
        show_asia     = st.checkbox("Asia/Pacific",     value=False)
        show_mena     = st.checkbox("Middle East/Africa", value=False)
        show_cups     = st.checkbox("Continental Cups", value=True)

    league_filter_key = f"{show_europe}{show_americas}{show_asia}{show_mena}{show_cups}"

    # ══════════════════════════════════════════════════════════════
    #  TAB 1 — PICKS
    # ══════════════════════════════════════════════════════════════
    with tab_picks:
        from utils.helpers import now_utc
        from data.constants import CAT_OFFSET, WINDOW_HOURS
        now_cat = (now_utc() + CAT_OFFSET).strftime("%d %b %Y · %H:%M CAT")
        st.caption(
            f"🕐 {now_cat} &nbsp;·&nbsp; Scanning next {WINDOW_HOURS}h &nbsp;·&nbsp; "
            f"Auto-refresh 60s &nbsp;·&nbsp; Scan #{count if count else '—'}"
        )

        with st.spinner(""):
            st.markdown(
                '<div class="scan-line">⚡ ZEUS v4 NEURAL ENGINE — SCANNING 51 LEAGUES · OVER 2.5 GOALS ⚡</div>',
                unsafe_allow_html=True
            )
            picks, leagues_hit, games_eval, data_pts = _scan(conf_slider, league_filter_key)

        from database.db import get_bankroll
        from services.betting_engine import get_roi_stats
        bk     = get_bankroll()
        roi_st = get_roi_stats()

        elite_cnt  = sum(1 for p in picks if p["tier"] == "elite")
        strong_cnt = sum(1 for p in picks if p["tier"] == "strong")
        bet_cnt    = sum(1 for p in picks if p.get("bet_placed"))

        st.markdown(f"""
<div class="metrics-row">
  <div class="metric-box">
    <span class="metric-val">{len(picks)}</span>
    <div class="metric-lbl">Picks</div>
  </div>
  <div class="metric-box">
    <span class="metric-val gold">{elite_cnt}</span>
    <div class="metric-lbl">🔥 Elite</div>
  </div>
  <div class="metric-box">
    <span class="metric-val">{strong_cnt}</span>
    <div class="metric-lbl">⚡ Strong</div>
  </div>
  <div class="metric-box">
    <span class="metric-val blue">{bet_cnt}</span>
    <div class="metric-lbl">Bets Active</div>
  </div>
  <div class="metric-box">
    <span class="metric-val">{leagues_hit}</span>
    <div class="metric-lbl">Leagues</div>
  </div>
  <div class="metric-box">
    <span class="metric-val">{games_eval}</span>
    <div class="metric-lbl">Evaluated</div>
  </div>
  <div class="metric-box">
    <span class="metric-val cyan">{data_pts:,}</span>
    <div class="metric-lbl">Data Pts</div>
  </div>
  <div class="metric-box">
    <span class="metric-val gold">€{bk:.0f}</span>
    <div class="metric-lbl">Bankroll</div>
  </div>
</div>
""", unsafe_allow_html=True)

        st.markdown("---")

        if not picks:
            st.markdown("""
<div class="no-picks">
  <span class="no-picks-icon">⏳</span>
  No games meet the confidence threshold in the next 6 hours.<br>
  ZEUS is continuously scanning. Adjust the slider or check back later.
</div>
""", unsafe_allow_html=True)
        else:
            c1, c2, c3 = st.columns(3)
            c1.markdown(
                '<span style="font-family:Barlow Condensed;color:#ffb300;font-size:0.85rem;">'
                '🔥 ELITE ≥90% — All 7 factors green · Near-certain O2.5</span>',
                unsafe_allow_html=True
            )
            c2.markdown(
                '<span style="font-family:Barlow Condensed;color:#39ff14;font-size:0.85rem;">'
                '⚡ STRONG 83–89% — Clear Poisson + ML + BTTS signal</span>',
                unsafe_allow_html=True
            )
            c3.markdown(
                '<span style="font-family:Barlow Condensed;color:#69ff47;font-size:0.85rem;">'
                '✅ CONFIDENT 78–82% — Positive xG + venue + Over-2.5 history</span>',
                unsafe_allow_html=True
            )
            st.markdown("---")
            for pick in picks:
                render_pick_card(pick)

    # ══════════════════════════════════════════════════════════════
    #  TAB 2 — BETTING ENGINE
    # ══════════════════════════════════════════════════════════════
    with tab_betting:
        st.subheader("💰 Betting Engine — Risk Management Dashboard")
        from services.betting_engine import get_roi_stats
        from database.db import get_bankroll, get_loss_streak, is_betting_halted
        from data.constants import INITIAL_BANKROLL

        roi_st   = get_roi_stats()
        bankroll = get_bankroll()
        loss_str = get_loss_streak()
        halted   = is_betting_halted()

        m1, m2, m3, m4, m5, m6 = st.columns(6)
        m1.metric("💰 Bankroll",    f"€{bankroll:.2f}", f"{bankroll - INITIAL_BANKROLL:+.2f}")
        m2.metric("📈 ROI",         f"{roi_st['roi']*100:.2f}%")
        m3.metric("✅ Won",          roi_st["won"])
        m4.metric("❌ Lost",         roi_st["lost"])
        m5.metric("🎯 Win Rate",     f"{roi_st['win_rate']*100:.1f}%")
        m6.metric("⚡ Loss Streak",  loss_str)

        if halted:
            st.error("🚨 BETTING HALTED — 4 consecutive losses detected. Reset to resume.")
            if st.button("♻️ Reset Betting Engine"):
                from database.db import set_loss_streak, set_betting_halted
                set_loss_streak(0)
                set_betting_halted(False)
                st.success("Betting engine reset.")
                st.rerun()
        else:
            st.success("✅ Betting engine ACTIVE")

        st.divider()
        st.markdown("**Risk Controls**")
        risk_data = {
            "Parameter": ["Max Daily Exposure", "Max Concurrent Bets", "Minimum Odds",
                          "Kelly Multiplier", "Loss Halve Trigger", "Loss Halt Trigger"],
            "Value":     ["15% bankroll", "5", "1.50", "0.20 (20% Kelly)",
                          "2 consecutive", "4 consecutive"]
        }
        st.dataframe(pd.DataFrame(risk_data), hide_index=True, use_container_width=True)

        st.divider()
        st.markdown("**Kelly Criterion Formula**")
        st.code("""
f* = (b·p - q) / b
Stake = Bankroll × f* × 0.20

Where:
  b = odds - 1
  p = P_ensemble (model probability)
  q = 1 - p

Edge = p × odds - 1   (must be > 0 to bet)
        """, language="text")

        if picks:
            st.divider()
            st.markdown("**Current Session Bets**")
            bet_rows = [p for p in picks if p.get("bet_placed")]
            if bet_rows:
                df_bets = pd.DataFrame([{
                    "Match":      p["match_label"],
                    "P(≥3g)":     f"{p['p_ensemble']*100:.1f}%",
                    "Confidence": f"{p['conf_pct']:.1f}%",
                    "Odds":       p["odds"],
                    "Edge":       f"{p['edge']*100:.1f}%",
                    "Stake (€)":  p["stake"],
                    "Kelly f*":   f"{p['kelly_f']:.4f}",
                } for p in bet_rows])
                st.dataframe(df_bets, hide_index=True, use_container_width=True)
            else:
                st.info("No bets placed in current scan window.")

    # ══════════════════════════════════════════════════════════════
    #  TAB 3 — RESULTS
    # ══════════════════════════════════════════════════════════════
    with tab_results:
        st.subheader("🏆 Pick Results — Graded Outcomes")

        with st.spinner("Grading pending picks…"):
            from services.scanner import grade_pending_picks
            newly = grade_pending_picks()
        if newly:
            st.toast(f"✅ Graded {newly} new pick(s)!", icon="⚽")

        from database.db import get_predictions
        preds = get_predictions(limit=300)
        if not preds:
            st.info("No picks logged yet. Visit 🎯 Picks to generate predictions.")
        else:
            won_list  = [p for p in preds if p.get("result") == "WON"]
            lost_list = [p for p in preds if p.get("result") == "LOST"]
            pend_list = [p for p in preds if p.get("result") == "pending"]
            graded    = len(won_list) + len(lost_list)
            wr        = f"{len(won_list)/max(graded,1)*100:.1f}%"

            r1, r2, r3, r4, r5 = st.columns(5)
            r1.metric("✅ Won",       len(won_list))
            r2.metric("❌ Lost",      len(lost_list))
            r3.metric("⏳ Pending",   len(pend_list))
            r4.metric("Total Graded", graded)
            r5.metric("Win Rate",     wr)
            st.divider()

            if won_list:
                st.markdown("### ✅ Correct Picks")
                for p in won_list:
                    st.markdown(
                        f"⚽ **{p['match_label']}** · {p['league_name']} · "
                        f"P={p['p_ensemble']*100:.1f}% · Conf={p['confidence']*100:.1f}% · "
                        f"Odds={p['odds']:.2f} · "
                        f"<span style='color:#39ff14;font-weight:700;'>WON ✅</span>",
                        unsafe_allow_html=True
                    )
                    st.divider()

            if lost_list:
                st.markdown("### ❌ Missed Picks")
                for p in lost_list:
                    st.markdown(
                        f"⚽ **{p['match_label']}** · {p['league_name']} · "
                        f"P={p['p_ensemble']*100:.1f}% · Conf={p['confidence']*100:.1f}% · "
                        f"Odds={p['odds']:.2f} · "
                        f"<span style='color:#ff1744;font-weight:700;'>LOST ❌</span>",
                        unsafe_allow_html=True
                    )
                    st.divider()

            if pend_list:
                with st.expander(f"⏳ {len(pend_list)} pending picks"):
                    df_p = pd.DataFrame([{
                        "Match":      p["match_label"],
                        "P(≥3g)":     f"{p['p_ensemble']*100:.1f}%",
                        "Confidence": f"{p['confidence']*100:.1f}%",
                        "Kickoff":    p["kickoff_utc"],
                    } for p in pend_list])
                    st.dataframe(df_p, hide_index=True, use_container_width=True)

    # ══════════════════════════════════════════════════════════════
    #  TAB 4 — BANKROLL
    # ══════════════════════════════════════════════════════════════
    with tab_bankroll:
        st.subheader("📈 Bankroll History & Performance")
        from database.db import get_bankroll_history, get_bankroll
        from data.constants import INITIAL_BANKROLL
        history = get_bankroll_history()

        if len(history) < 2:
            st.info("Bankroll history will appear here after bets are graded.")
            st.metric("Current Bankroll", f"€{get_bankroll():.2f}")
        else:
            balances = [INITIAL_BANKROLL] + [h["balance"] for h in history]
            changes  = [h["change"] for h in history]

            b1, b2, b3, b4 = st.columns(4)
            peak      = max(balances)
            curr      = balances[-1]
            total_pnl = curr - INITIAL_BANKROLL
            max_dd    = 0.0
            pk        = INITIAL_BANKROLL
            for b in balances:
                if b > pk:
                    pk = b
                dd = (pk - b) / max(pk, 1.0)
                if dd > max_dd:
                    max_dd = dd

            b1.metric("💰 Current",     f"€{curr:.2f}",  f"{total_pnl:+.2f}")
            b2.metric("📈 Peak",         f"€{peak:.2f}")
            b3.metric("📉 Max Drawdown", f"{max_dd*100:.1f}%")
            b4.metric("🎯 Total P&L",    f"€{total_pnl:+.2f}")

            st.divider()
            st.markdown("**Bankroll Curve**")
            df_bk = pd.DataFrame({"Bet #": range(len(balances)), "Bankroll (€)": balances})
            st.line_chart(df_bk.set_index("Bet #"), color="#39ff14")

            st.markdown("**P&L per Bet**")
            df_pnl = pd.DataFrame({"Bet #": range(1, len(changes)+1), "P&L (€)": changes})
            st.bar_chart(df_pnl.set_index("Bet #"))

            with st.expander("Bankroll Log"):
                df_hist = pd.DataFrame(history)
                if "recorded_at" in df_hist:
                    df_hist["recorded_at"] = df_hist["recorded_at"].str[:19]
                st.dataframe(df_hist[["balance", "change", "reason", "recorded_at"]],
                             hide_index=True, use_container_width=True)

    # ══════════════════════════════════════════════════════════════
    #  TAB 5 — SIMULATION
    # ══════════════════════════════════════════════════════════════
    with tab_sim:
        st.subheader("🧪 Self-Repair Simulation Engine")

        st.markdown("""
<div class="sim-box">
  <div class="sim-title">⚡ Simulation Architecture</div>
  The ZEUS self-repair engine runs BEFORE any predictions are output. It:<br>
  1. Generates <b>5,000 synthetic matches</b> using realistic Poisson distributions calibrated for Over 2.5<br>
  2. Trains logistic regression with <b>online gradient descent</b> (60+ epochs per iteration)<br>
  3. Evaluates: Accuracy, Log Loss, Brier Score, ROI, Max Drawdown, Win Rate<br>
  4. Detects failures: NaN/Inf, ROI &lt; 0, Drawdown &gt; 22%, Accuracy &lt; 80%<br>
  5. Auto-fixes: learning rate, L2 regularization, weight clipping<br>
  6. Repeats up to <b>8 iterations</b> until all conditions pass
</div>
""", unsafe_allow_html=True)

        if boot_metrics:
            st.markdown("**Last Boot Simulation Results**")
            mc = st.columns(6)
            mc[0].metric("Accuracy",     f"{boot_metrics.get('accuracy',0)*100:.2f}%")
            mc[1].metric("Log Loss",     f"{boot_metrics.get('log_loss',0):.4f}")
            mc[2].metric("Brier Score",  f"{boot_metrics.get('brier',0):.4f}")
            mc[3].metric("ROI",          f"{boot_metrics.get('roi',0)*100:.2f}%")
            mc[4].metric("Max Drawdown", f"{boot_metrics.get('max_drawdown',0)*100:.1f}%")
            mc[5].metric("Win Rate",     f"{boot_metrics.get('win_rate',0)*100:.1f}%")

        from database.db import get_simulation_logs
        sim_logs = get_simulation_logs()
        if sim_logs:
            st.divider()
            st.markdown("**Simulation Iteration History**")
            df_sim = pd.DataFrame(sim_logs)
            df_sim["passed"] = df_sim["passed"].map({1: "✅ PASS", 0: "❌ FAIL"})
            display_cols = ["iteration", "n_matches", "accuracy", "log_loss",
                            "brier", "roi", "max_drawdown", "win_rate", "passed", "run_at"]
            display_cols = [c for c in display_cols if c in df_sim.columns]
            st.dataframe(df_sim[display_cols], hide_index=True, use_container_width=True)

        st.divider()
        col_run, _ = st.columns([2, 3])
        with col_run:
            if st.button("🔁 Re-Run Simulation Loop", type="primary"):
                with st.spinner("Running self-repair simulation…"):
                    from simulation.sim_engine import run_simulation_loop
                    from data.constants import RANDOM_SEED, SIM_MATCHES, SIM_MAX_ITER
                    _boot_system.clear()
                    model, metrics, logs = run_simulation_loop(SIM_MATCHES, SIM_MAX_ITER, RANDOM_SEED)
                st.success(
                    f"Done! Accuracy={metrics['accuracy']*100:.2f}% | "
                    f"ROI={metrics['roi']*100:.2f}% | "
                    f"{'✅ PASSED' if metrics['accuracy'] >= 0.80 and not metrics.get('has_nan') else '⚠ Check metrics'}"
                )
                st.rerun()

        st.divider()
        st.markdown("**Model Weights (current)**")
        from database.db import get_model_weights, get_model_bias
        weights = get_model_weights()
        bias    = get_model_bias()
        if weights:
            labels  = ["Home Attack", "Home Defense", "Away Attack", "Away Defense",
                       "League Intensity", "Tempo Score", "Over-2.5 Consistency", "BTTS Score"]
            w_slice = weights[:len(labels)]
            df_w = pd.DataFrame({
                "Feature": labels,
                "Weight":  [round(w, 6) for w in w_slice],
                "Bias":    [round(float(bias), 6)] + [None] * (len(labels) - 1),
            })
            st.dataframe(df_w, hide_index=True, use_container_width=True)

    # ══════════════════════════════════════════════════════════════
    #  TAB 6 — SYSTEM INFO
    # ══════════════════════════════════════════════════════════════
    with tab_about:
        st.subheader("🌍 ZEUS v4 — System Architecture")
        c1, c2 = st.columns(2)

        with c1:
            st.markdown("""
**Prediction Engine — v4.0**

**Target:** Over 2.5 goals (≥3 goals scored) — Y=1 if total_goals ≥ 3

**Feature Vector X (8 dimensions):**
- Home Attack (xG-based, venue-weighted 60/40)
- Home Defense (concede rate)
- Away Attack (xG-based, venue-weighted 60/40)
- Away Defense (concede rate)
- League Intensity (normalized avg goals)
- Tempo Score (xG / 5.0 proxy)
- Over-2.5 Consistency (historical ≥3-goal rate)
- BTTS Score (both-teams-to-score rate)

**Model Layers:**
1. **Poisson Layer** — P(≥3 goals) = 1 − P(0) − P(1) − P(2 goals total)
2. **ML Layer** — Logistic regression: P_ml = σ(w·X + b)
3. **Ensemble** — P_goal = 0.65 × Poisson + 0.35 × ML → clamped [0.01, 0.99]

**7-Factor Confidence Score:**
- Ensemble probability (30%)
- Historical Over-2.5 rate (25%)
- BTTS rate (18%)
- Recent form — last-3 avg goals (12%)
- Clean-sheet penalty (multiplier)
- Variance / stability (multiplier)
- H2H Over-2.5 rate (boost if available)

**Hard Pre-Filters (all must pass):**
- Combined xG ≥ 2.50
- Each team Over-2.5 rate ≥ 50%
- Average BTTS rate ≥ 45%
- League avg goals ≥ 2.50
- Each team clean-sheet rate ≤ 28%
- Each team avg scored ≥ 1.20 goals

**Threshold:** Confidence ≥ 0.78 (configurable)
""")

        with c2:
            st.markdown("""
**Betting Engine**

```
Edge  = P_ensemble × Odds − 1   (only bet if > 0)
f*    = (b·p − q) / b            (Kelly fraction)
Stake = Bankroll × f* × 0.20    (fractional Kelly)
```

**Risk Controls:**
- Max daily exposure: 15% bankroll
- Max concurrent bets: 5
- Minimum odds: 1.50
- After 2 losses → stake halved
- After 4 losses → betting halted

**WIN THRESHOLD: 3 goals**
(Over 2.5 wins when total goals ≥ 3)

**Online Learning:**
- Gradient descent after each graded result
- η = 0.008 with decay 0.997
- L2 regularization: 0.002
- Weight clipping: [−5, +5]

**Self-Repair Loop:**
- 5,000 synthetic matches per iteration
- Up to 8 iterations
- Auto-adjusts: lr, L2, weights
- Minimum accuracy: 80%, ROI ≥ 0, Drawdown ≤ 22%
""")

        st.divider()
        st.subheader("Leagues Monitored (51)")
        from data.constants import LEAGUES, LEAGUE_GOAL_AVG
        league_rows = []
        for lid, lname, flag in LEAGUES:
            region = lid.split(".")[0].upper()
            avg = LEAGUE_GOAL_AVG.get(lid, 2.65)
            league_rows.append({
                "Flag": flag, "League": lname, "Region": region,
                "Avg Goals": avg, "League ID": lid
            })
        df_l = pd.DataFrame(league_rows)
        st.dataframe(df_l, hide_index=True, use_container_width=True)

        st.divider()
        st.caption(
            "**Data:** API-Football v3 via RapidAPI. Scoreboard TTL: 5 min. "
            "Team schedule TTL: 1 hr. Requires ≥8 completed games per team. "
            "Results graded 105+ min after kickoff. "
            "Model persisted to SQLite (zeus_v4.db)."
        )


if __name__ == "__main__":
    main()
