"""
ZEUS v4 Scanner — Over 2.5 Goals elite pick engine.
Applies multi-gate hard filters before any pick is scored.
"""
import hashlib
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone

import numpy as np

from data.constants import (
    LEAGUES, TOP_N, CONFIDENCE_THRESH, LEAGUE_GOAL_AVG,
    MIN_ODDS, OVER_LINE,
    XG_TOTAL_MIN, MIN_OVER25_RATE, MIN_BTTS_RATE,
    MIN_LEAGUE_AVG, MAX_CLEAN_SHEET, MIN_AVG_SCORED,
)
from services.apifootball import fetch_scoreboard, fetch_team_schedule
from services.stats_engine import team_stats, get_h2h_over25_rate
from services.betting_engine import compute_stake, should_bet, compute_edge
from models.ensemble import ensemble_predict, compute_confidence
from database.db import save_prediction, get_bankroll, get_loss_streak
from utils.helpers import (
    in_window, to_cat, minutes_to_kickoff, match_id,
    get_tier, get_tier_label, now_utc,
)

logger = logging.getLogger(__name__)


def _passes_gates(
    home_st: Dict,
    away_st: Dict,
    xg_home: float,
    xg_away: float,
    league_avg: float,
) -> Tuple[bool, str]:
    """
    Multi-gate quality filter for Over 2.5 picks.
    Returns (True, "OK") only if every gate passes.
    """
    xg_total = xg_home + xg_away

    if xg_total < XG_TOTAL_MIN:
        return False, f"xG total {xg_total:.2f} < {XG_TOTAL_MIN}"

    o25_home = home_st.get("over25_rate", 0.0)
    o25_away = away_st.get("over25_rate", 0.0)
    if o25_home < MIN_OVER25_RATE:
        return False, f"Home O2.5 rate {o25_home:.0%} < {MIN_OVER25_RATE:.0%}"
    if o25_away < MIN_OVER25_RATE:
        return False, f"Away O2.5 rate {o25_away:.0%} < {MIN_OVER25_RATE:.0%}"

    btts_avg = (home_st.get("btts_rate", 0.0) + away_st.get("btts_rate", 0.0)) / 2.0
    if btts_avg < MIN_BTTS_RATE:
        return False, f"Avg BTTS {btts_avg:.0%} < {MIN_BTTS_RATE:.0%}"

    if league_avg < MIN_LEAGUE_AVG:
        return False, f"League avg {league_avg:.2f} < {MIN_LEAGUE_AVG}"

    cs_home = home_st.get("clean_sheet_rate", 0.0)
    cs_away = away_st.get("clean_sheet_rate", 0.0)
    if cs_home > MAX_CLEAN_SHEET:
        return False, f"Home CS rate {cs_home:.0%} too high"
    if cs_away > MAX_CLEAN_SHEET:
        return False, f"Away CS rate {cs_away:.0%} too high"

    if home_st.get("avg_scored", 0.0) < MIN_AVG_SCORED:
        return False, f"Home avg scored {home_st.get('avg_scored', 0):.2f} < {MIN_AVG_SCORED}"
    if away_st.get("avg_scored", 0.0) < MIN_AVG_SCORED:
        return False, f"Away avg scored {away_st.get('avg_scored', 0):.2f} < {MIN_AVG_SCORED}"

    return True, "OK"


def scan_all_leagues(
    confidence_min: float = CONFIDENCE_THRESH,
    league_filter: Optional[List[str]] = None,
) -> Tuple[List[Dict], int, int, int]:
    """
    Scan all configured leagues for Over 2.5 picks.
    Returns (picks, leagues_hit, games_evaluated, data_points).
    """
    candidates: List[Dict] = []
    leagues_hit = 0
    games_eval = 0
    data_pts = 0

    target_leagues = LEAGUES
    if league_filter:
        filter_set = set(league_filter)
        target_leagues = [(lid, ln, flag) for lid, ln, flag in LEAGUES if lid in filter_set]

    for league_id, league_name, flag in target_leagues:
        events = fetch_scoreboard(league_id)
        if not events:
            continue

        window_games = [
            e for e in events
            if not e.get("completed", False) and in_window(e.get("date", ""))
        ]
        if not window_games:
            continue

        leagues_hit += 1
        league_avg = LEAGUE_GOAL_AVG.get(league_id, 2.65)

        if league_avg < MIN_LEAGUE_AVG:
            continue

        for ev in window_games:
            home_sched = fetch_team_schedule(league_id, ev["home_id"])
            away_sched = fetch_team_schedule(league_id, ev["away_id"])
            data_pts += len(home_sched) + len(away_sched)

            home_st = team_stats(home_sched, ev["home_name"])
            away_st = team_stats(away_sched, ev["away_name"])

            if home_st is None or away_st is None:
                continue

            games_eval += 1

            p_pois, p_ml, p_ensemble, xg_home, xg_away = ensemble_predict(
                home_st, away_st, league_id, league_avg
            )
            xg_total = xg_home + xg_away

            passed, _ = _passes_gates(home_st, away_st, xg_home, xg_away, league_avg)
            if not passed:
                continue

            h2h_rate = get_h2h_over25_rate(
                home_sched, away_sched, ev["home_name"], ev["away_name"]
            )

            confidence = compute_confidence(
                p_ensemble, home_st, away_st, league_avg, h2h_rate
            )
            conf_pct = round(confidence * 100, 1)

            if confidence < confidence_min:
                continue

            rng_seed = int(hashlib.md5(ev["event_id"].encode()).hexdigest(), 16) % (2 ** 32)
            rng = np.random.default_rng(rng_seed)
            base_odds = 1.55 + (1.0 - p_ensemble) * 1.40
            odds = float(np.clip(rng.normal(base_odds, 0.08), MIN_ODDS, 2.80))
            odds = round(odds, 2)

            edge = compute_edge(p_ensemble, odds)
            bankroll = get_bankroll()
            loss_streak = get_loss_streak()
            stake, kelly_f, _ = compute_stake(p_ensemble, odds, bankroll, loss_streak)
            bet_ok, bet_reason = should_bet(p_ensemble, odds, confidence)

            mid = match_id(ev["home_name"], ev["away_name"], ev["date"])
            home_form = _form_bar(home_st.get("form_score", 0.5))
            away_form = _form_bar(away_st.get("form_score", 0.5))
            reasoning = _build_reasoning(
                home_st, away_st, p_pois, p_ml, p_ensemble,
                xg_home, xg_away, h2h_rate, league_avg,
            )

            pred = {
                "id": mid,
                "match_id": ev["event_id"],
                "match_label": f"{ev['home_name']} vs {ev['away_name']}",
                "home": ev["home_name"],
                "away": ev["away_name"],
                "league": f"{flag} {league_name}",
                "league_id": league_id,
                "league_name": league_name,
                "kickoff_utc": ev["date"],
                "kickoff_cat": to_cat(ev["date"]),
                "mins_away": minutes_to_kickoff(ev["date"]),
                "bet": f"OVER {OVER_LINE} (>=3 Goals)",
                "p_poisson": p_pois,
                "p_ml": p_ml,
                "p_ensemble": p_ensemble,
                "confidence": confidence,
                "conf_pct": conf_pct,
                "xg_home": xg_home,
                "xg_away": xg_away,
                "xg_total": xg_total,
                "odds": odds,
                "edge": edge,
                "stake": stake,
                "kelly_f": kelly_f,
                "bet_placed": bet_ok,
                "bet_reason": bet_reason,
                "tier": get_tier(conf_pct),
                "tier_label": get_tier_label(conf_pct),
                "reasoning": reasoning,
                "home_over25": round(home_st.get("home_over25_rate", 0) * 100, 1),
                "away_over25": round(away_st.get("away_over25_rate", 0) * 100, 1),
                "home_over15": round(home_st.get("home_over15_rate", 0) * 100, 1),
                "away_over15": round(away_st.get("away_over15_rate", 0) * 100, 1),
                "home_btts": round(home_st.get("home_btts_rate", 0) * 100, 1),
                "away_btts": round(away_st.get("away_btts_rate", 0) * 100, 1),
                "home_over05": round(home_st.get("home_over05_rate", 0) * 100, 1),
                "away_over05": round(away_st.get("away_over05_rate", 0) * 100, 1),
                "home_n": home_st["n"],
                "away_n": away_st["n"],
                "home_form": home_st.get("form_score", 0.5),
                "away_form": away_st.get("form_score", 0.5),
                "home_form_str": home_form,
                "away_form_str": away_form,
                "home_streak": home_st.get("streak_over25", 0),
                "away_streak": away_st.get("streak_over25", 0),
                "home_last3": round(home_st.get("last3_avg", 0), 2),
                "away_last3": round(away_st.get("last3_avg", 0), 2),
                "h2h_over25": round(h2h_rate * 100, 1) if h2h_rate is not None else None,
                "result": "pending",
            }
            candidates.append(pred)

    candidates.sort(key=lambda x: (x["confidence"], x["edge"]), reverse=True)
    top_picks = candidates[:TOP_N]
    for i, p in enumerate(top_picks, 1):
        p["rank"] = i
        save_prediction(p)

    return top_picks, leagues_hit, games_eval, data_pts


def _form_bar(score: float) -> str:
    """Convert a form score to a display string."""
    if score >= 0.65:
        return "HOT"
    if score <= 0.35:
        return "COLD"
    return "STABLE"


def _build_reasoning(
    home_st: Dict,
    away_st: Dict,
    p_pois: float,
    p_ml: float,
    p_ensemble: float,
    xg_home: float,
    xg_away: float,
    h2h_rate: Optional[float],
    league_avg: float,
) -> str:
    """Build a human-readable reasoning string for a pick."""
    parts = [
        f"Poisson P(>=3 goals): {p_pois * 100:.1f}% | "
        f"ML: {p_ml * 100:.1f}% | "
        f"Ensemble: {p_ensemble * 100:.1f}%",
        f"xG: {xg_home:.2f} (home) + {xg_away:.2f} (away) = {xg_home + xg_away:.2f} total",
    ]
    o25_h = home_st.get("over25_rate", 0)
    o25_a = away_st.get("over25_rate", 0)
    parts.append(f"Over 2.5 rate: {o25_h * 100:.0f}% (home) / {o25_a * 100:.0f}% (away)")

    btts_h = home_st.get("btts_rate", 0)
    btts_a = away_st.get("btts_rate", 0)
    parts.append(f"BTTS rate: {btts_h * 100:.0f}% (home) / {btts_a * 100:.0f}% (away)")

    if home_st.get("form_score", 0.5) > 0.65:
        parts.append(f"Home HOT form - last-5 avg {home_st.get('recent_avg', 0):.2f} goals/game")
    if away_st.get("form_score", 0.5) > 0.65:
        parts.append(f"Away HOT form - last-5 avg {away_st.get('recent_avg', 0):.2f} goals/game")

    streak25_h = home_st.get("streak_over25", 0)
    streak25_a = away_st.get("streak_over25", 0)
    if streak25_h >= 3:
        parts.append(f"Home: {streak25_h}-game 3+ goals streak")
    if streak25_a >= 3:
        parts.append(f"Away: {streak25_a}-game 3+ goals streak")

    if h2h_rate is not None:
        parts.append(f"H2H Over 2.5 rate: {h2h_rate * 100:.0f}%")

    return " | ".join(parts)


def grade_pending_picks() -> int:
    """Grade all pending picks whose matches should be finished."""
    from database.db import get_predictions
    from services.apifootball import fetch_completed_result
    from services.betting_engine import record_result
    from utils.helpers import parse_utc

    predictions = get_predictions(limit=500)
    pending = [p for p in predictions if p.get("result") == "pending"]
    graded = 0

    for pred in pending:
        ko = parse_utc(pred.get("kickoff_utc", ""))
        if not ko:
            continue
        elapsed = (now_utc() - ko).total_seconds()
        if elapsed < 6300:
            continue

        parts = pred["match_label"].split(" vs ")
        if len(parts) != 2:
            continue
        home_name, away_name = parts[0].strip(), parts[1].strip()

        total = fetch_completed_result(
            pred["league_id"], home_name, away_name, pred["kickoff_utc"]
        )
        if total is None:
            continue

        record_result(
            prediction_id=pred["id"],
            match_label=pred["match_label"],
            total_goals=total,
            p_ensemble=pred["p_ensemble"],
            odds=pred["odds"],
            stake=pred["stake"],
        )
        graded += 1

    return graded
