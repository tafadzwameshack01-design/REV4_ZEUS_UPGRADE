import streamlit as st
from typing import List, Dict
from core.constants import LEAGUES, HT_BET_TYPES
from core.time_utils import today_str_utc
from core.stats_engine import team_stats, get_h2h_stats
from core.confidence_engine import run_gauntlet_and_compute
from core.math_engine import _xg_full
from core.learning_engine import is_bet_type_paused
from data_sources.data_aggregator import get_team_schedule_all_sources

# Live games use lower gates — less time remaining means we need to act faster
LIVE_GATE_OVERRIDES = {
    "HT_OVER_05": 65.0,
    "HT_OVER_15": 57.0,
}


@st.cache_data(ttl=22, show_spinner=False)
def scan_live_games_now(state_key: int = 0) -> List[Dict]:
    """
    Scans all leagues for H1 live games.
    state_key is the daemon scan_count — forces cache refresh each daemon sweep.
    Catches 0-0 games (pure value) and games with low total score.
    """
    from data_sources.espn_api import extract_live_games

    live_picks = []
    seen_games = set()
    today      = today_str_utc()

    for league_id, lname, flag in LEAGUES:
        try:
            candidate_games = extract_live_games(league_id, today)
            if not candidate_games:
                continue

            for game in candidate_games:
                gk = f"live_{game.get('home_id','')}_{game.get('away_id','')}_{today}"
                if gk in seen_games:
                    continue
                seen_games.add(gk)

                hid    = game["home_id"]
                aid    = game["away_id"]
                hname  = game["home_name"]
                aname  = game["away_name"]
                minute = game["minute"]
                hs     = game.get("home_score", 0)
                as_    = game.get("away_score", 0)

                home_sched = get_team_schedule_all_sources(league_id, hid, hname)
                away_sched = get_team_schedule_all_sources(league_id, aid, aname)

                if not home_sched or not away_sched:
                    continue
                if len(home_sched) < 3 or len(away_sched) < 3:
                    continue

                home_st = team_stats(home_sched, hname, league_id)
                away_st = team_stats(away_sched, aname, league_id)
                if home_st is None or away_st is None:
                    continue

                h2h         = get_h2h_stats(home_sched, away_sched, hname, aname)
                xg_h, xg_a = _xg_full(home_st, away_st)

                # Scale xG for remaining first-half time
                remaining   = max(1, 45 - minute)
                time_frac   = remaining / 40.0
                # 0-0 pent-up pressure bonus; small score adds slight dampening
                total_score = hs + as_
                pressure_mult = 1.15 if total_score == 0 else (1.05 if total_score == 1 else 1.0)
                live_xg_h   = xg_h * time_frac * pressure_mult
                live_xg_a   = xg_a * time_frac * pressure_mult

                league_str = f"{flag} {lname}"
                match_str  = f"{hname} vs {aname}"
                score_str  = f"{hs} - {as_}"

                for bet_type in HT_BET_TYPES:
                    if is_bet_type_paused(bet_type):
                        continue

                    # Skip if line is already beaten
                    line = HT_BET_TYPES[bet_type]["line"]
                    if total_score > line:
                        continue

                    result = run_gauntlet_and_compute(
                        home_st, away_st, h2h, bet_type,
                        live_xg_h, live_xg_a,
                        league_str, match_str,
                        gate_override=LIVE_GATE_OVERRIDES.get(bet_type),
                        is_live=True,
                    )
                    if result is None:
                        continue

                    elite_gate = HT_BET_TYPES[bet_type].get("elite_gate", 80.0)
                    tier       = "elite" if result["confidence"] >= elite_gate * 0.9 else "strong"

                    live_picks.append({
                        "match":       match_str,
                        "home":        hname,
                        "away":        aname,
                        "home_id":     hid,
                        "away_id":     aid,
                        "league":      league_str,
                        "league_id":   league_id,
                        "event_id":    game.get("event_id", ""),
                        "kickoff_utc": game.get("date", ""),
                        "bet_type":    bet_type,
                        "bet":         f"LIVE {HT_BET_TYPES[bet_type]['label']}",
                        "xg_h":        round(live_xg_h, 2),
                        "xg_a":        round(live_xg_a, 2),
                        "xg_total":    round(live_xg_h + live_xg_a, 2),
                        "minute":      minute,
                        "score":       score_str,
                        "is_live":     True,
                        "tier":        tier,
                        "tier_label":  "LIVE LOCK" if tier == "elite" else "LIVE PICK",
                        **result,
                    })
        except Exception:
            continue

    live_picks.sort(key=lambda x: x["confidence"], reverse=True)
    return live_picks[:15]
