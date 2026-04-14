import streamlit as st
import pandas as pd
from core.db import db_fetchall


def render_results_tab():
    st.markdown("### 📊 Results & Performance")

    rows = db_fetchall(
        "SELECT match, league, bet, bet_type, confidence, result, ht_total, kickoff, logged_at "
        "FROM picks_log ORDER BY logged_at DESC LIMIT 100"
    )
    live_rows = db_fetchall(
        "SELECT match, league, bet, bet_type, confidence, result, ht_total, kickoff, logged_at "
        "FROM live_picks_log ORDER BY logged_at DESC LIMIT 100"
    )

    all_rows = []
    for r in rows:
        ht = r[6] if (r[6] is not None and r[6] >= 0) else "-"
        all_rows.append({
            "Match":      r[0],
            "League":     r[1],
            "Bet":        r[2],
            "Conf%":      round(float(r[4] or 0), 1),
            "Result":     r[5] or "pending",
            "HT Goals":   ht,
            "Kickoff":    (r[7] or "")[:16].replace("T", " "),
            "Type":       "Pre-Match",
        })
    for r in live_rows:
        ht = r[6] if (r[6] is not None and r[6] >= 0) else "-"
        all_rows.append({
            "Match":      r[0],
            "League":     r[1],
            "Bet":        r[2],
            "Conf%":      round(float(r[4] or 0), 1),
            "Result":     r[5] or "pending",
            "HT Goals":   ht,
            "Kickoff":    (r[7] or "")[:16].replace("T", " "),
            "Type":       "🔴 LIVE",
        })

    wins    = sum(1 for r in all_rows if r["Result"] == "WIN")
    losses  = sum(1 for r in all_rows if r["Result"] == "LOSS")
    pending = sum(1 for r in all_rows if r["Result"] == "pending")
    total   = wins + losses
    acc     = round(wins / max(total, 1) * 100, 1)

    # ── Summary metrics ───────────────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: st.metric("✅ Wins",    wins)
    with c2: st.metric("❌ Losses",  losses)
    with c3: st.metric("⏳ Pending", pending)
    with c4: st.metric("🎯 Accuracy", f"{acc}%", delta=f"{wins}/{total}" if total else None)
    with c5: st.metric("📋 Total",   len(all_rows))

    # ── Bet-type breakdown ────────────────────────────────────────────────────
    if total > 0:
        from core.constants import HT_BET_TYPES
        st.markdown("#### Breakdown by Bet Type")
        bt_cols = st.columns(len(HT_BET_TYPES))
        for i, (bt, btinfo) in enumerate(HT_BET_TYPES.items()):
            bt_rows = [r for r in all_rows if bt in r["Bet"] and r["Result"] in ("WIN","LOSS")]
            bt_w    = sum(1 for r in bt_rows if r["Result"] == "WIN")
            bt_l    = len(bt_rows) - bt_w
            bt_acc  = round(bt_w / max(len(bt_rows), 1) * 100, 1)
            with bt_cols[i]:
                st.markdown(f"""
                <div style="background:#0a160a;border:1px solid #1a3a1a;border-radius:8px;padding:10px;text-align:center;">
                    <div style="color:#7dff7d;font-size:0.7rem;letter-spacing:1px;">{btinfo['label']}</div>
                    <div style="font-family:'Orbitron',monospace;font-size:1.4rem;color:#39ff14;">{bt_acc}%</div>
                    <div style="color:#555;font-size:0.7rem;">{bt_w}W / {bt_l}L</div>
                </div>
                """, unsafe_allow_html=True)

        # ── Trend chart ───────────────────────────────────────────────────────
        resolved = [r for r in reversed(all_rows) if r["Result"] in ("WIN","LOSS")]
        if len(resolved) >= 3:
            st.markdown("#### Running Accuracy Trend")
            running_acc = []
            rw = 0
            for idx, r in enumerate(resolved, 1):
                if r["Result"] == "WIN":
                    rw += 1
                running_acc.append(round(rw / idx * 100, 1))

            import streamlit as _st
            _st.line_chart(
                {"Accuracy %": running_acc},
                use_container_width=True,
                height=160,
            )

    # ── Full table ────────────────────────────────────────────────────────────
    if all_rows:
        st.markdown("#### All Picks")
        df = pd.DataFrame(all_rows)
        # Colour-code Result column
        def _style(val):
            if val == "WIN":    return "color:#39ff14;font-weight:700"
            if val == "LOSS":   return "color:#ff3939;font-weight:700"
            if val == "pending": return "color:#ffb300"
            return "color:#888"
        st.dataframe(
            df.style.applymap(_style, subset=["Result"]),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No results yet. Picks appear here as games complete.")
