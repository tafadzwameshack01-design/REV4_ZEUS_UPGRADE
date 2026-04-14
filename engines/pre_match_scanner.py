import streamlit as st
from typing import List, Dict, Tuple
from core.constants import LEAGUES, HT_BET_TYPES, PRIORITY_LEAGUES, SCAN_WINDOW_MIN, SCAN_WINDOW_MAX
from core.time_utils import in_scan_window, today_str_utc, tomorrow_str_utc
from core.stats_engine import team_stats, get_h2h_stats
from core.confidence_engine import run_gauntlet_and_compute
from core.math_engine import _xg_full
from core.learning_engine import is_bet_type_paused
from data_sources.espn_api import extract_upcoming_games
from data_sources.data_aggregator import get_team_schedule_all_sources
from core.db import db_execute
from core.time_utils import utc_iso


@st.cache_data(ttl=30, show_spinner=False)
def scan_all_leagues() -> Tuple:
    """
    Scans all leagues for pre-match picks (SCAN_WINDOW_MIN–SCAN_WINDOW_MAX window).
    Returns: (picks, leagues_hit, games_eval, data_points, warming, sub_gate_picks)
    """
    picks          = []
    sub_gate_picks = []
    leagues_hit    = 0
    games_eval     = 0
    data_points    = 0
    warming        = False
    seen           = set()

    priority_ids = set(PRIORITY_LEAGUES)
    ordered      = [l for l in LEAGUES if l[0] in priority_ids] + \
                   [l for l in LEAGUES if l[0] not in priority_ids]

    scan_dates = [today_str_utc(), tomorrow_str_utc()]

    for league_id, lname, flag in ordered:
        league_had_games = False
        try:
            for date_str in scan_dates:
                upcoming = extract_upcoming_games(league_id, date_str)
                if not upcoming:
                    continue

                for game in upcoming:
                    if not in_scan_window(game.get("date", ""),
                                          min_min=SCAN_WINDOW_MIN,
                                          max_min=SCAN_WINDOW_MAX):
                        continue

                    gk = f"pre_{game.get('home_id','')}_{game.get('away_id','')}_{date_str}"
                    if gk in seen:
                        continue
                    seen.add(gk)

                    league_had_games = True
                    games_eval += 1

                    hid   = game["home_id"]
                    aid   = game["away_id"]
                    hname = game["home_name"]
                    aname = game["away_name"]

                    home_sched = get_team_schedule_all_sources(league_id, hid, hname)
                    away_sched = get_team_schedule_all_sources(league_id, aid, aname)

                    if not home_sched or not away_sched:
                        warming = True
                        continue
                    if len(home_sched) < 3 or len(away_sched) < 3:
                        continue

                    data_points += len(home_sched) + len(away_sched)

                    home_st = team_stats(home_sched, hname, league_id)
                    away_st = team_stats(away_sched, aname, league_id)
                    if home_st is None or away_st is None:
                        continue

                    h2h        = get_h2h_stats(home_sched, away_sched, hname, aname)
                    xg_h, xg_a = _xg_full(home_st, away_st)
                    league_str  = f"{flag} {lname}"
                    match_str   = f"{hname} vs {aname}"

                    for bet_type in HT_BET_TYPES:
                        if is_bet_type_paused(bet_type):
                            continue

                        gate_val   = HT_BET_TYPES[bet_type]["gate"]
                        elite_gate = HT_BET_TYPES[bet_type].get("elite_gate", 87.0)

                        result = run_gauntlet_and_compute(
                            home_st, away_st, h2h, bet_type,
                            xg_h, xg_a, league_str, match_str,
                        )

                        pick_base = {
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
                            "bet":         HT_BET_TYPES[bet_type]["label"],
                            "xg_h":        round(xg_h, 2),
                            "xg_a":        round(xg_a, 2),
                            "xg_total":    round(xg_h + xg_a, 2),
                            "is_live":     False,
                        }

                        if result is not None:
                            tier = "elite" if result["confidence"] >= elite_gate else "strong"
                            picks.append({
                                **pick_base,
                                "tier":       tier,
                                "tier_label": "ELITE LOCK" if tier == "elite" else "STRONG PICK",
                                **result,
                            })
                        else:
                            # Compute raw confidence for sub-gate monitoring
                            raw_conf = _raw_confidence_estimate(
                                home_st, away_st, h2h, bet_type, xg_h, xg_a
                            )
                            near_gate_threshold = gate_val * 0.88
                            if raw_conf is not None and raw_conf >= near_gate_threshold:
                                sub_gate_picks.append({
                                    **pick_base,
                                    "confidence":   round(raw_conf, 1),
                                    "tier":         "monitoring",
                                    "tier_label":   "MONITORING",
                                    "gate_used":    gate_val,
                                    "factors_json": "{}",
                                    "factor_adj":   0.0,
                                    "poisson_prob": 0.0,
                                })

        except Exception:
            continue

        if league_had_games:
            leagues_hit += 1

    picks.sort(key=lambda x: x["confidence"], reverse=True)
    sub_gate_picks.sort(key=lambda x: x["confidence"], reverse=True)

    try:
        db_execute(
            "INSERT INTO scan_log (scan_type, leagues_hit, games_eval, picks_made, data_points, logged_at) "
            "VALUES (?,?,?,?,?,?)",
            ("pre_match", leagues_hit, games_eval, len(picks), data_points, utc_iso()),
        )
    except Exception:
        pass

    return picks[:25], leagues_hit, games_eval, data_points, warming, sub_gate_picks[:10]


def _raw_confidence_estimate(home_st, away_st, h2h, bet_type, xg_h, xg_a) -> float:
    """Compute raw confidence with gate forced to 0 (no filter)."""
    try:
        result = run_gauntlet_and_compute(
            home_st, away_st, h2h, bet_type,
            xg_h, xg_a, "", "", gate_override=0.0
        )
        return result["confidence"] if result else None
    except Exception:
        return None
