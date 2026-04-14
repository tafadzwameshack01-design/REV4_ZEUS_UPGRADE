import streamlit as st
import time
import pandas as pd
from core.constants import LEAGUES, VERSION, HT_BET_TYPES
from core.time_utils import now_cat, utc_iso, epoch_now
from core.db import db_fetchone, db_fetchall, get_brain_state


def render_system_tab(_state: dict):
    st.markdown(f"### 🌍 ZEUS v{VERSION} — System Status")

    cat_now      = now_cat().strftime("%Y-%m-%d %H:%M:%S CAT")
    daemon_on    = _state.get("daemon_running", False)
    warmup       = _state.get("warmup_complete", False)
    leagues_pf   = _state.get("leagues_prefetched", 0)
    leagues_tot  = _state.get("leagues_total", len(LEAGUES))
    games_cached = _state.get("games_cached", 0)
    teams_cached = _state.get("teams_cached", 0)
    scan_count   = _state.get("scan_count", 0)
    last_sweep   = _state.get("last_sweep_ts", 0)
    phase        = _state.get("phase", "initializing")
    errors       = _state.get("errors", [])

    sweep_ago = f"{int(time.time() - last_sweep)}s ago" if last_sweep else "Not yet"

    phase_colors = {
        "warming_priority": "#ffb300",
        "full_sweep":       "#00e5ff",
        "idle":             "#39ff14",
        "initializing":     "#888",
    }
    phase_color = phase_colors.get(phase, "#888")

    st.markdown(f"""
    <div class="system-status">
        <div class="sys-row"><span class="sys-lbl">Version</span>
            <span class="sys-val">ZEUS v{VERSION}</span></div>
        <div class="sys-row"><span class="sys-lbl">Current Time (CAT)</span>
            <span class="sys-val">{cat_now}</span></div>
        <div class="sys-row"><span class="sys-lbl">Total Leagues</span>
            <span class="sys-val">{len(LEAGUES)}</span></div>
        <div class="sys-row"><span class="sys-lbl">Daemon</span>
            <span class="sys-val" style="color:{'#39ff14' if daemon_on else '#ffb300'};">
                {'🟢 RUNNING' if daemon_on else '🟡 STARTING'}</span></div>
        <div class="sys-row"><span class="sys-lbl">Phase</span>
            <span class="sys-val" style="color:{phase_color};">{phase.replace('_',' ').upper()}</span></div>
        <div class="sys-row"><span class="sys-lbl">Warmup</span>
            <span class="sys-val" style="color:{'#39ff14' if warmup else '#ffb300'};">
                {'✅ COMPLETE' if warmup else '⏳ IN PROGRESS'}</span></div>
        <div class="sys-row"><span class="sys-lbl">Leagues Prefetched</span>
            <span class="sys-val">{leagues_pf} / {leagues_tot}</span></div>
        <div class="sys-row"><span class="sys-lbl">Games Cached</span>
            <span class="sys-val">{games_cached:,}</span></div>
        <div class="sys-row"><span class="sys-lbl">Teams Cached</span>
            <span class="sys-val">{teams_cached:,}</span></div>
        <div class="sys-row"><span class="sys-lbl">Full Sweeps</span>
            <span class="sys-val">{scan_count}</span></div>
        <div class="sys-row"><span class="sys-lbl">Last Full Sweep</span>
            <span class="sys-val">{sweep_ago}</span></div>
    </div>
    """, unsafe_allow_html=True)

    if errors:
        with st.expander(f"⚠️ Recent errors ({len(errors)})", expanded=False):
            for e in errors[-10:]:
                st.warning(e)

    st.divider()

    # ── Data source health ────────────────────────────────────────────────────
    st.markdown("#### Data Source Status")
    col1, col2 = st.columns(2)
    with col1:
        # ESPN check via recent cache hit
        espn_ok = bool(db_fetchone("SELECT 1 FROM cache_store WHERE cache_key LIKE 'espn_%' LIMIT 1"))
        sofa_ok = bool(db_fetchone("SELECT 1 FROM cache_store WHERE cache_key LIKE 'sofa_%' LIMIT 1"))
        tsdb_ok = bool(db_fetchone("SELECT 1 FROM cache_store WHERE cache_key LIKE 'tsdb_%' LIMIT 1"))
        import os
        ftdata_ok = bool(os.getenv("FOOTBALL_DATA_API_KEY"))

        for name, ok in [("ESPN (primary)", espn_ok), ("SofaScore (secondary)", sofa_ok),
                          ("TheSportsDB (tertiary)", tsdb_ok),
                          ("Football-Data.org", ftdata_ok)]:
            icon  = "🟢" if ok else "⚪"
            color = "#39ff14" if ok else "#555"
            note  = "" if ok else (" (needs API key)" if "Football" in name else " (cache empty)")
            st.markdown(f"<span style='color:{color};'>{icon} {name}{note}</span>",
                        unsafe_allow_html=True)

    with col2:
        st.markdown("**Database Tables**")
        for tbl in ["picks_log", "live_picks_log", "brain_state", "cache_store",
                    "league_accuracy", "prediction_pauses", "weights_history", "scan_log"]:
            row = db_fetchone(f"SELECT COUNT(*) FROM {tbl}")
            cnt = row[0] if row else 0
            st.markdown(f"`{tbl}`: **{cnt:,}** rows")

    st.divider()

    # ── Gate thresholds ───────────────────────────────────────────────────────
    st.markdown("#### Active Gate Thresholds")
    gc1, gc2 = st.columns(2)
    cols_cycle = [gc1, gc2]
    for i, (bt, info) in enumerate(HT_BET_TYPES.items()):
        ge, sw, sl = get_brain_state(bt)
        eff = info["gate"] + ge
        with cols_cycle[i % 2]:
            st.markdown(f"""
            <div style="background:#0a160a;border:1px solid #1a3a1a;border-radius:8px;padding:12px;margin-bottom:8px;">
                <div style="color:#39ff14;font-family:'Orbitron',monospace;font-size:0.85rem;font-weight:700;">
                    {info['label']}
                </div>
                <div style="color:#e0ffe0;font-size:1.2rem;font-family:'Orbitron',monospace;margin-top:4px;">
                    {eff:.1f}%
                </div>
                <div style="color:#555;font-size:0.72rem;margin-top:2px;">
                    Base {info['gate']}% · Adj {ge:+.1f}% · Elite {info.get('elite_gate',87)}%
                </div>
                <div style="color:#555;font-size:0.7rem;">W-streak: {sw} · L-streak: {sl}</div>
            </div>
            """, unsafe_allow_html=True)

    st.divider()

    # ── Scan log ──────────────────────────────────────────────────────────────
    scan_rows = db_fetchall(
        "SELECT scan_type, leagues_hit, games_eval, picks_made, data_points, logged_at "
        "FROM scan_log ORDER BY id DESC LIMIT 20"
    )
    if scan_rows:
        st.markdown("#### Recent Scan Log")
        df = pd.DataFrame(scan_rows, columns=["Type", "Leagues", "Games", "Picks", "DataPts", "Time"])
        st.dataframe(df, use_container_width=True, hide_index=True)

    st.divider()

    # ── All leagues table ─────────────────────────────────────────────────────
    with st.expander(f"📋 All {len(LEAGUES)} Configured Leagues"):
        ldf = pd.DataFrame([
            {"Flag": f, "League": n, "ESPN ID": lid}
            for lid, n, f in LEAGUES
        ])
        st.dataframe(ldf, use_container_width=True, hide_index=True)
