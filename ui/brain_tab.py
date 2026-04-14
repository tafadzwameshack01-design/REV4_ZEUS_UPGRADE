import streamlit as st
import pandas as pd
from core.learning_engine import get_accuracy_stats, load_weights, get_weight_velocity
from core.db import get_brain_state, db_fetchall
from core.constants import HT_BET_TYPES


def _bar(value: float, max_val: float = 3.5, width: int = 120) -> str:
    pct = min(100, value / max_val * 100)
    return (
        f'<div style="display:inline-block;background:#0a160a;border-radius:4px;'
        f'width:{width}px;height:10px;vertical-align:middle;border:1px solid #1a3a1a;">'
        f'<div style="background:#39ff14;width:{pct:.0f}%;height:100%;border-radius:4px;"></div></div>'
    )


def render_brain_tab():
    st.markdown("### 🧠 AI Brain — Autonomous Learning Status")

    stats = get_accuracy_stats()

    if not stats:
        st.info("Brain initializing — no weight data yet.")
        return

    for bt, info in stats.items():
        label     = HT_BET_TYPES.get(bt, {}).get("label", bt)
        ge, sw, sl = get_brain_state(bt)
        base_gate = HT_BET_TYPES.get(bt, {}).get("gate", 72)
        eff_gate  = base_gate + ge
        total     = info["total"]
        acc       = info["accuracy"]
        velocity  = get_weight_velocity(bt)

        # Trend indicator
        if total == 0:
            trend = "⚪ No data"
        elif acc >= 60:
            trend = "📈 Performing well"
        elif acc >= 50:
            trend = "➡️ Neutral"
        else:
            trend = "📉 Learning..."

        st.markdown(f"""
        <div class="brain-metric">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px;">
                <div>
                    <span style="color:#39ff14;font-family:'Orbitron',monospace;font-weight:700;font-size:1rem;">{label}</span>
                    <span style="color:#555;font-size:0.75rem;margin-left:10px;">{trend}</span>
                </div>
                <div style="color:#7dff7d;font-size:0.82rem;text-align:right;">
                    Gate: <strong>{eff_gate:.1f}%</strong>
                    <span style="color:#555;"> (base {base_gate} + adj {ge:+.1f})</span>
                </div>
            </div>
            <div style="margin-top:8px;display:flex;gap:2rem;flex-wrap:wrap;">
                <div><span style="color:#999;font-size:0.78rem;">Predictions:</span>
                     <span style="color:#e0ffe0;font-weight:600;"> {total}</span></div>
                <div><span style="color:#999;font-size:0.78rem;">Wins:</span>
                     <span style="color:#39ff14;font-weight:600;"> {info['wins']}</span></div>
                <div><span style="color:#999;font-size:0.78rem;">Losses:</span>
                     <span style="color:#ff3939;font-weight:600;"> {info['losses']}</span></div>
                <div><span style="color:#999;font-size:0.78rem;">Accuracy:</span>
                     <span style="color:#{'39ff14' if acc>=55 else 'ffb300' if acc>=45 else 'ff3939'};font-weight:600;"> {acc}%</span></div>
            </div>
            <div style="margin-top:4px;font-size:0.73rem;color:#555;">
                Win streak: {sw} &nbsp;·&nbsp; Loss streak: {sl}
                {'&nbsp;·&nbsp; <span style="color:#ff3939;">⚠️ Tightened gate</span>' if ge > 3 else ''}
                {'&nbsp;·&nbsp; <span style="color:#39ff14;">🔓 Loosened gate</span>' if ge < -2 else ''}
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ── Weight visualiser ─────────────────────────────────────────────────────
    st.markdown("### Factor Weights")
    weights_data = load_weights()
    for bt, info in weights_data.items():
        label   = HT_BET_TYPES.get(bt, {}).get("label", bt)
        weights = info.get("weights", {})
        vel     = get_weight_velocity(bt)

        with st.expander(f"⚖️ {label} — weight values", expanded=False):
            rows = []
            for k, v in sorted(weights.items(), key=lambda x: -x[1]):
                direction = "▲" if vel.get(k, 0) > 0.0005 else ("▼" if vel.get(k, 0) < -0.0005 else "─")
                rows.append({
                    "Factor":    k,
                    "Weight":    round(v, 4),
                    "Velocity":  round(vel.get(k, 0), 5),
                    "Trend":     direction,
                })
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)

    # ── League accuracy ───────────────────────────────────────────────────────
    st.markdown("### League Accuracy (≥20 samples)")
    league_rows = db_fetchall(
        "SELECT league_id, bet_type, wins, losses FROM league_accuracy "
        "WHERE (wins + losses) >= 20 ORDER BY (wins + losses) DESC LIMIT 25"
    )
    if league_rows:
        la_data = []
        for r in league_rows:
            lid, bt, w, l = r
            total = w + l
            acc   = round(w / max(total, 1) * 100, 1)
            la_data.append({
                "League": lid,
                "Bet Type": bt,
                "W": w, "L": l,
                "Accuracy %": acc,
            })
        df = pd.DataFrame(la_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.caption("League accuracy data will appear after 20+ resolved predictions per league.")

    # ── Weight learning history ───────────────────────────────────────────────
    st.markdown("### Learning History (last 30 updates)")
    hist = db_fetchall(
        "SELECT bet_type, accuracy, logged_at FROM weights_history "
        "ORDER BY id DESC LIMIT 30"
    )
    if hist:
        hist_data = [{"Bet Type": r[0], "Accuracy%": round(float(r[1] or 0), 1),
                      "Updated": (r[2] or "")[:16]} for r in hist]
        st.dataframe(pd.DataFrame(hist_data), use_container_width=True, hide_index=True)
    else:
        st.caption("No learning history yet. Updates appear after results are resolved.")

    # ── Momentum pauses ───────────────────────────────────────────────────────
    st.markdown("### Momentum Pauses")
    pauses = db_fetchall("SELECT bet_type, pause_until, reason FROM prediction_pauses")
    from core.time_utils import epoch_now
    active = [p for p in pauses if p[1] > epoch_now()]
    if active:
        for p in active:
            remaining = int((p[1] - epoch_now()) / 60)
            st.warning(f"⏸️ **{p[0]}** paused — {p[2]} ({remaining}min remaining)")
    else:
        st.success("✅ All bet types active — no momentum pauses.")
