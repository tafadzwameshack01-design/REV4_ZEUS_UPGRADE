import streamlit as st
from typing import List, Dict

def _conf_color(conf: float) -> str:
    if conf >= 90: return "#ffb300"
    if conf >= 80: return "#39ff14"
    if conf >= 72: return "#7dff7d"
    return "#4daa4d"

def render_live_pick_card(pick: Dict):
    conf    = pick.get("confidence", 0)
    color   = _conf_color(conf)
    poisson = pick.get("poisson_prob", 0)
    st.markdown(f"""
    <div class="live-card">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;">
            <div>
                <span class="live-badge">🔴 LIVE</span>
                <span class="minute-badge">&nbsp;{pick.get('minute', 0)}'&nbsp;</span>
                <span style="color:#aaa;font-size:0.78rem;margin-left:6px;">
                    Score: <strong style="color:#fff;">{pick.get('score','0 - 0')}</strong>
                </span>
            </div>
            <div style="font-family:'Orbitron',monospace;font-size:1.6rem;font-weight:900;color:{color};">
                {conf:.1f}%
            </div>
        </div>
        <div style="font-size:1.15rem;font-weight:700;color:#fff;margin-top:6px;">
            {pick.get('match','')}
        </div>
        <div style="color:#ff9999;font-size:0.75rem;letter-spacing:1.5px;text-transform:uppercase;">
            {pick.get('league','')}
        </div>
        <div style="margin-top:8px;display:flex;gap:14px;flex-wrap:wrap;align-items:center;">
            <span style="color:#ff7777;font-weight:700;font-size:0.95rem;">{pick.get('bet','')}</span>
            <span style="color:#aaa;font-size:0.82rem;">xG HT: <strong style="color:#ffb300;">{pick.get('xg_total',0):.2f}</strong></span>
            <span style="color:#aaa;font-size:0.82rem;">Poisson: <strong style="color:#00e5ff;">{poisson:.1f}%</strong></span>
            <span style="color:#aaa;font-size:0.82rem;">Gate: <strong style="color:#888;">{pick.get('gate_used',0):.1f}%</strong></span>
        </div>
        <div style="margin-top:5px;font-size:0.72rem;color:#ff9999;letter-spacing:1px;">
            {pick.get('tier_label','LIVE')} &nbsp;·&nbsp; Factor adj: {pick.get('factor_adj',0):+.1f}%
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_pick_card(pick: Dict):
    conf    = pick.get("confidence", 0)
    color   = _conf_color(conf)
    poisson = pick.get("poisson_prob", 0)
    tier    = pick.get("tier", "strong")
    ko_str  = (pick.get("kickoff_utc") or "")[:16].replace("T", " ")
    fa      = pick.get("factor_adj", 0)
    st.markdown(f"""
    <div class="pick-card tier-{tier}">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;">
            <div style="flex:1;">
                <div style="font-size:1.1rem;font-weight:700;color:#e0ffe0;">{pick.get('match','')}</div>
                <div style="color:#7dff7d;font-size:0.73rem;letter-spacing:1.5px;text-transform:uppercase;margin-top:2px;">
                    {pick.get('league','')}
                </div>
            </div>
            <div style="font-family:'Orbitron',monospace;font-size:1.65rem;font-weight:900;color:{color};margin-left:12px;">
                {conf:.1f}%
            </div>
        </div>
        <div style="margin-top:9px;display:flex;gap:14px;flex-wrap:wrap;align-items:center;">
            <span style="color:#39ff14;font-weight:700;font-size:0.95rem;">{pick.get('bet','')}</span>
            <span style="color:#aaa;font-size:0.82rem;">xG: <strong style="color:#ffb300;">{pick.get('xg_total',0):.2f}</strong></span>
            <span style="color:#aaa;font-size:0.82rem;">Poisson: <strong style="color:#00e5ff;">{poisson:.1f}%</strong></span>
            <span style="color:#aaa;font-size:0.82rem;">KO: <strong style="color:#e0ffe0;">{ko_str}</strong></span>
        </div>
        <div style="margin-top:5px;font-size:0.72rem;color:#4dff4d;letter-spacing:1px;">
            {pick.get('tier_label','PICK')}
            &nbsp;·&nbsp; Gate: {pick.get('gate_used',0):.1f}%
            &nbsp;·&nbsp; Adj: {fa:+.1f}%
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_monitoring_card(pick: Dict):
    """Below-gate picks that are close to qualifying."""
    conf = pick.get("confidence", 0)
    gate = pick.get("gate_used", pick.get("gate_used", 72))
    gap  = gate - conf
    ko_str = (pick.get("kickoff_utc") or "")[:16].replace("T", " ")
    st.markdown(f"""
    <div style="background:#0a0f0a;border:1px dashed #2a4a2a;border-radius:10px;
         padding:10px 14px;margin:6px 0;opacity:0.85;">
        <div style="display:flex;justify-content:space-between;align-items:center;">
            <div>
                <span style="color:#7dff7d;font-size:0.95rem;font-weight:600;">{pick.get('match','')}</span>
                <span style="color:#4a6a4a;font-size:0.72rem;margin-left:8px;">{pick.get('league','')}</span>
            </div>
            <div style="font-family:'Orbitron',monospace;font-size:1rem;color:#4a8a4a;">
                {conf:.1f}%
                <span style="font-size:0.65rem;color:#3a5a3a;"> (-{gap:.1f})</span>
            </div>
        </div>
        <div style="font-size:0.78rem;color:#3a6a3a;margin-top:3px;">
            {pick.get('bet','')} &nbsp;·&nbsp; KO: {ko_str}
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_warmup_screen(state: dict):
    leagues_pf = state.get("leagues_prefetched", 0)
    games_c    = state.get("games_cached", 0)
    teams_c    = state.get("teams_cached", 0)
    phase      = state.get("phase", "initializing")
    phase_labels = {
        "initializing":    "Starting up...",
        "warming_priority": "Warming priority leagues...",
        "full_sweep":       "Running full sweep...",
        "idle":             "Idle — awaiting next sweep",
    }
    phase_str = phase_labels.get(phase, phase)
    from core.constants import LEAGUES
    total = len(LEAGUES)
    pct   = int(min(100, leagues_pf / max(total, 1) * 100))
    st.markdown(f"""
    <div class="warmup-screen">
        <div style="font-size:3rem;">⚡</div>
        <h3 style="color:#39ff14;font-family:'Orbitron',monospace;margin-top:0.8rem;letter-spacing:3px;">
            ZEUS INITIALIZING
        </h3>
        <p style="color:#7dff7d;">{phase_str}</p>
        <div style="background:#1a2a1a;border-radius:8px;height:8px;margin:12px auto;max-width:320px;overflow:hidden;">
            <div style="background:#39ff14;height:100%;width:{pct}%;transition:width 1s;border-radius:8px;"></div>
        </div>
        <p style="color:#39ff14;font-family:'Orbitron',monospace;font-size:1rem;">
            {leagues_pf} / {total} leagues &nbsp;·&nbsp; {games_c:,} games &nbsp;·&nbsp; {teams_c:,} teams
        </p>
        <p style="color:#555;font-size:0.8rem;margin-top:0.5rem;">
            Priority leagues warm in ~30s. All picks appear automatically after warmup.
        </p>
    </div>
    """, unsafe_allow_html=True)

def render_picks_tab(pre_picks: List[Dict], live_picks: List[Dict],
                     _state: dict, sub_gate: List[Dict] = None):
    warmup_done = _state.get("warmup_complete", False)
    sub_gate    = sub_gate or []

    # ── LIVE SECTION ──────────────────────────────────────────────────────────
    if live_picks:
        st.markdown("""
        <div style="background:rgba(255,57,57,0.08);border:1px solid #ff3939;border-radius:10px;
             padding:10px 16px;margin-bottom:12px;text-align:center;">
            <span style="color:#ff3939;font-family:'Orbitron',monospace;font-weight:700;letter-spacing:3px;font-size:0.9rem;">
                🔴 LIVE NOW — FIRST HALF IN PROGRESS
            </span>
        </div>
        """, unsafe_allow_html=True)
        for pick in live_picks:
            render_live_pick_card(pick)

    # ── PRE-MATCH SECTION ─────────────────────────────────────────────────────
    if pre_picks:
        st.markdown("""
        <div style="background:rgba(57,255,20,0.05);border:1px solid #39ff14;border-radius:10px;
             padding:10px 16px;margin:12px 0;text-align:center;">
            <span style="color:#39ff14;font-family:'Orbitron',monospace;font-weight:700;letter-spacing:3px;font-size:0.9rem;">
                ⚡ PRE-MATCH PICKS
            </span>
        </div>
        """, unsafe_allow_html=True)
        for pick in pre_picks:
            render_pick_card(pick)

    # ── MONITORING SECTION ────────────────────────────────────────────────────
    if sub_gate and warmup_done:
        with st.expander(f"🔍 Monitoring ({len(sub_gate)} near-gate games)", expanded=False):
            st.caption("These games are close to qualifying but haven't cleared the confidence gate yet. Refreshes every 28s.")
            for pick in sub_gate:
                render_monitoring_card(pick)

    # ── EMPTY STATE ───────────────────────────────────────────────────────────
    if not live_picks and not pre_picks:
        if warmup_done:
            st.markdown("""
            <div class="no-picks">
                <div style="font-size:2.5rem;margin-bottom:8px;">🔍</div>
                No picks meeting quality gates right now.<br>
                <span style="font-size:0.82rem;color:#4e724e;">
                    Scanning all leagues every 28 seconds.<br>
                    Picks appear the moment confidence gates are cleared.
                </span>
            </div>
            """, unsafe_allow_html=True)
        else:
            render_warmup_screen(_state)
