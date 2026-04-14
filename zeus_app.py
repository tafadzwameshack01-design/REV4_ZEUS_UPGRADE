import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st

try:
    from streamlit_autorefresh import st_autorefresh
    _HAS_AUTOREFRESH = True
except Exception:
    _HAS_AUTOREFRESH = False

import uuid
import json

from core.db import init_db_once, db_execute, db_fetchone
from core.constants import LEAGUES, VERSION, HT_BET_TYPES
from core.time_utils import utc_iso
from engines.daemon import start_background_daemon, get_shared_state
from engines.live_scanner import scan_live_games_now
from engines.pre_match_scanner import scan_all_leagues
from engines.result_tracker import check_and_update_results
from ui.styles import inject_css
from ui.picks_tab import render_picks_tab
from ui.results_tab import render_results_tab
from ui.brain_tab import render_brain_tab
from ui.system_tab import render_system_tab

st.set_page_config(
    page_title=f"ZEUS v{VERSION} — HT Intelligence",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={"About": f"ZEUS v{VERSION} Halftime Intelligence System"},
)

inject_css()

# ── Init ──────────────────────────────────────────────────────────────────────
init_db_once()
_state = get_shared_state()
start_background_daemon(_state)

# ── Auto-refresh every 28s ────────────────────────────────────────────────────
if _HAS_AUTOREFRESH:
    st_autorefresh(interval=28000, limit=None, key="zeus_refresh")

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="zeus-hero">
    <h1>⚡ ZEUS v{VERSION}</h1>
    <div class="subtitle">
        Halftime Intelligence System &nbsp;|&nbsp;
        {len(LEAGUES)} Leagues &nbsp;|&nbsp;
        Multi-Source AI &nbsp;|&nbsp;
        Self-Learning
    </div>
</div>
""", unsafe_allow_html=True)

# ── Fetch data ────────────────────────────────────────────────────────────────
scan_result = scan_all_leagues()
# scan_all_leagues now returns a 6-tuple
if len(scan_result) == 6:
    pre_picks, leagues_hit, games_eval, data_pts, warming, sub_gate = scan_result
else:
    pre_picks, leagues_hit, games_eval, data_pts, warming = scan_result
    sub_gate = []

scan_key  = _state.get("scan_count", 0)
live_picks = scan_live_games_now(state_key=scan_key)

# ── Persist new picks ─────────────────────────────────────────────────────────
def _save_pick(pick: dict):
    table   = "live_picks_log" if pick.get("is_live") else "picks_log"
    match   = pick.get("match", "")
    bt      = pick.get("bet_type", "")
    kickoff = (pick.get("kickoff_utc") or "")[:10]

    existing = db_fetchone(
        f"SELECT id FROM {table} WHERE match=? AND bet_type=? AND substr(kickoff,1,10)=?",
        (match, bt, kickoff),
    )
    if existing:
        return

    pid  = str(uuid.uuid4())[:12]
    cols = {
        "id":          pid,
        "event_id":    pick.get("event_id", ""),
        "match":       match,
        "league":      pick.get("league", ""),
        "league_id":   pick.get("league_id", ""),
        "bet":         pick.get("bet", ""),
        "bet_type":    bt,
        "xg_total":    pick.get("xg_total", 0),
        "confidence":  pick.get("confidence", 0),
        "kickoff":     pick.get("kickoff_utc", ""),
        "factors_json": pick.get("factors_json", "{}"),
        "logged_at":   utc_iso(),
    }
    if pick.get("is_live"):
        cols["minute_made"] = pick.get("minute", 0)

    col_names    = ",".join(cols.keys())
    placeholders = ",".join(["?"] * len(cols))
    db_execute(
        f"INSERT OR IGNORE INTO {table} ({col_names}) VALUES ({placeholders})",
        tuple(cols.values()),
    )

for pick in pre_picks + live_picks:
    _save_pick(pick)

# Non-blocking result resolution
check_and_update_results()

# ── Metrics bar ───────────────────────────────────────────────────────────────
total_picks = len(pre_picks) + len(live_picks)
live_count  = len(live_picks)
warmup_done = _state.get("warmup_complete", False)
phases_icon = {"warming_priority": "🌡️", "full_sweep": "🔄", "idle": "✅", "initializing": "⏳"}
phase_icon  = phases_icon.get(_state.get("phase", "initializing"), "⚙️")

st.markdown(f"""
<div class="metric-bar">
    <div class="metric-item">
        <div class="metric-value">{total_picks}</div>
        <div class="metric-label">Active Picks</div>
    </div>
    <div class="metric-item">
        <div class="metric-value" style="color:#ff3939;">{live_count}</div>
        <div class="metric-label">🔴 Live Now</div>
    </div>
    <div class="metric-item">
        <div class="metric-value">{leagues_hit}</div>
        <div class="metric-label">Leagues Hit</div>
    </div>
    <div class="metric-item">
        <div class="metric-value">{games_eval}</div>
        <div class="metric-label">Games Scanned</div>
    </div>
    <div class="metric-item">
        <div class="metric-value">{data_pts:,}</div>
        <div class="metric-label">Data Points</div>
    </div>
    <div class="metric-item">
        <div class="metric-value">{len(sub_gate)}</div>
        <div class="metric-label">Monitoring</div>
    </div>
    <div class="metric-item">
        <div class="metric-value" style="color:{'#39ff14' if warmup_done else '#ffb300'};">
            {phase_icon}
        </div>
        <div class="metric-label">{'Ready' if warmup_done else 'Warming'}</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "⚡ PICKS & LIVE", "📊 RESULTS", "🧠 AI BRAIN", "🌍 SYSTEM"
])
with tab1:
    render_picks_tab(pre_picks, live_picks, _state, sub_gate)
with tab2:
    render_results_tab()
with tab3:
    render_brain_tab()
with tab4:
    render_system_tab(_state)
