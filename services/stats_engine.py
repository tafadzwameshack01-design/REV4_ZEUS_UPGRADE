"""
ZEUS v4 — Per-team statistics engine focused on Over 2.5 goals.
"""
from typing import Dict, List, Optional

from utils.helpers import safe_mean
from data.constants import MIN_GAMES


def team_stats(games: List[Dict], team_name: str) -> Optional[Dict]:
    """
    Compute comprehensive stats for a team from their completed fixtures.
    Returns None if insufficient data (fewer than MIN_GAMES completed matches).
    """
    completed = [
        g for g in games
        if g.get("home_score") is not None and g.get("away_score") is not None
    ]
    if len(completed) < MIN_GAMES:
        return None

    home_games = [g for g in completed if g.get("home_name", "") == team_name]
    away_games = [g for g in completed if g.get("away_name", "") == team_name]

    def _split_stats(game_list, is_home):
        if not game_list:
            return None, None, None, None, None, None, None
        scored = [g["home_score"] if is_home else g["away_score"] for g in game_list]
        conceded = [g["away_score"] if is_home else g["home_score"] for g in game_list]
        totals = [s + c for s, c in zip(scored, conceded)]
        n = len(game_list)
        avg_sc = safe_mean(scored)
        avg_co = safe_mean(conceded)
        over05 = sum(1 for t in totals if t >= 1) / n
        over15 = sum(1 for t in totals if t >= 2) / n
        over25 = sum(1 for t in totals if t >= 3) / n
        btts = sum(1 for s, c in zip(scored, conceded) if s > 0 and c > 0) / n
        return avg_sc, avg_co, over05, over15, over25, btts, n

    h_avg_sc, h_avg_co, h_o05, h_o15, h_o25, h_btts, nh = _split_stats(home_games, True)
    a_avg_sc, a_avg_co, a_o05, a_o15, a_o25, a_btts, na = _split_stats(away_games, False)

    all_sc, all_co, all_tot = [], [], []
    for g in completed:
        is_home = g.get("home_name", "") == team_name
        sc = g["home_score"] if is_home else g["away_score"]
        co = g["away_score"] if is_home else g["home_score"]
        all_sc.append(sc)
        all_co.append(co)
        all_tot.append(sc + co)

    n = len(completed)
    avg_sc = safe_mean(all_sc)
    avg_co = safe_mean(all_co)
    avg_tot = safe_mean(all_tot)
    over05_rate = sum(1 for t in all_tot if t >= 1) / n
    over15_rate = sum(1 for t in all_tot if t >= 2) / n
    over25_rate = sum(1 for t in all_tot if t >= 3) / n
    btts_rate = sum(1 for s, c in zip(all_sc, all_co) if s > 0 and c > 0) / n

    recent5 = all_tot[-5:] if n >= 5 else all_tot
    older = all_tot[:-5] if n > 5 else all_tot
    recent_avg = safe_mean(recent5)
    older_avg = safe_mean(older)
    form_score = max(0.0, min(1.0, 0.5 + (recent_avg - older_avg) / 4.0))
    last3_avg = safe_mean(all_tot[-3:]) if n >= 3 else avg_tot

    streak_over25 = 0
    for t in reversed(all_tot):
        if t >= 3:
            streak_over25 += 1
        else:
            break

    streak_over15 = 0
    for t in reversed(all_tot):
        if t >= 2:
            streak_over15 += 1
        else:
            break

    streak_over = 0
    for t in reversed(all_tot):
        if t >= 1:
            streak_over += 1
        else:
            break

    clean_sheet_rate = sum(1 for c in all_co if c == 0) / n

    return {
        "n": n,
        "n_home": nh if nh is not None else 0,
        "n_away": na if na is not None else 0,
        "avg_scored": avg_sc,
        "avg_conceded": avg_co,
        "avg_total": avg_tot,
        "over05_rate": over05_rate,
        "over15_rate": over15_rate,
        "over25_rate": over25_rate,
        "btts_rate": btts_rate,
        "clean_sheet_rate": clean_sheet_rate,
        "home_avg_scored": h_avg_sc if h_avg_sc is not None else avg_sc,
        "home_avg_conceded": h_avg_co if h_avg_co is not None else avg_co,
        "home_over05_rate": h_o05 if h_o05 is not None else over05_rate,
        "home_over15_rate": h_o15 if h_o15 is not None else over15_rate,
        "home_over25_rate": h_o25 if h_o25 is not None else over25_rate,
        "home_btts_rate": h_btts if h_btts is not None else btts_rate,
        "away_avg_scored": a_avg_sc if a_avg_sc is not None else avg_sc,
        "away_avg_conceded": a_avg_co if a_avg_co is not None else avg_co,
        "away_over05_rate": a_o05 if a_o05 is not None else over05_rate,
        "away_over15_rate": a_o15 if a_o15 is not None else over15_rate,
        "away_over25_rate": a_o25 if a_o25 is not None else over25_rate,
        "away_btts_rate": a_btts if a_btts is not None else btts_rate,
        "form_score": form_score,
        "recent_avg": recent_avg,
        "last3_avg": last3_avg,
        "streak_over": streak_over,
        "streak_over15": streak_over15,
        "streak_over25": streak_over25,
    }


def get_h2h_over25_rate(
    home_sched: List[Dict],
    away_sched: List[Dict],
    home_name: str,
    away_name: str,
) -> Optional[float]:
    """Return the head-to-head Over-2.5 rate (games with >= 3 goals)."""
    seen = set()
    h2h_totals = []
    for g in home_sched + away_sched:
        if g.get("home_score") is None or g.get("away_score") is None:
            continue
        gkey = f"{g.get('date', '')}_{g.get('home_name', '')}_{g.get('away_name', '')}"
        if gkey in seen:
            continue
        seen.add(gkey)
        names = {g.get("home_name", ""), g.get("away_name", "")}
        if {home_name, away_name} == names:
            h2h_totals.append(g["home_score"] + g["away_score"])
    if len(h2h_totals) >= 3:
        return round(sum(1 for t in h2h_totals if t >= 3) / len(h2h_totals), 4)
    return None
