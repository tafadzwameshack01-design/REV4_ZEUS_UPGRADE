"""
Stats Engine — computes normalised team statistics from schedule data.

Key metrics:
  - HT over rates (primary signal)
  - xG proxy via goal averages and scoring patterns
  - Form (last 5/10 games)
  - Scoring consistency and defensive weakness
"""
from typing import Dict, List, Optional


def team_stats(schedule: List[Dict], team_name: str, league_id: str) -> Optional[Dict]:
    if not schedule or len(schedule) < 3:
        return None

    goals_scored:    List[float] = []
    goals_conceded:  List[float] = []
    ht_goals_total:  List[int]   = []
    ht_over_05 = 0
    ht_over_15 = 0
    ht_games   = 0
    recent_form: List[int] = []
    last20 = schedule[-20:]

    for g in last20:
        home = (g.get("home_name") or "").lower()
        away = (g.get("away_name") or "").lower()
        tl   = team_name.lower()

        # Fuzzy name match — handles "Manchester City" vs "Man City" etc.
        is_home = (tl in home) or any(
            part in home for part in tl.split() if len(part) > 3
        )
        if not is_home:
            # Double-check by seeing if team name is more in home or away
            is_home = home and tl[:4] in home

        try:
            gs = float(g.get("home_score", 0) if is_home else g.get("away_score", 0))
            gc = float(g.get("away_score", 0) if is_home else g.get("home_score", 0))
        except (TypeError, ValueError):
            continue

        goals_scored.append(gs)
        goals_conceded.append(gc)

        ht_t = g.get("ht_total")
        if ht_t is not None and isinstance(ht_t, (int, float)) and ht_t >= 0:
            ht_goals_total.append(int(ht_t))
            ht_games += 1
            if ht_t >= 1:
                ht_over_05 += 1
            if ht_t >= 2:
                ht_over_15 += 1

        if gs > gc:
            recent_form.append(3)
        elif gs == gc:
            recent_form.append(1)
        else:
            recent_form.append(0)

    if not goals_scored:
        return None

    n       = len(goals_scored)
    avg_gs  = sum(goals_scored) / n
    avg_gc  = sum(goals_conceded) / n
    avg_tot = avg_gs + avg_gc

    # HT rates — use defaults calibrated to league averages when data is sparse
    if ht_games >= 3:
        ht_over_05_rate = (ht_over_05 / ht_games) * 100.0
        ht_over_15_rate = (ht_over_15 / ht_games) * 100.0
        avg_ht_goals    = sum(ht_goals_total) / len(ht_goals_total)
    elif ht_games > 0:
        # Partial data — blend with league average (regression to mean)
        league_avg_05 = 68.0  # ~68% of matches have 1+ goals in HT globally
        league_avg_15 = 28.0
        w = ht_games / 3.0
        ht_over_05_rate = w * (ht_over_05 / ht_games * 100) + (1-w) * league_avg_05
        ht_over_15_rate = w * (ht_over_15 / ht_games * 100) + (1-w) * league_avg_15
        avg_ht_goals    = sum(ht_goals_total) / len(ht_goals_total)
    else:
        # No HT data — estimate from full-time goals (HT ≈ 45% of FT goals)
        est_ht = avg_tot * 0.45
        ht_over_05_rate = max(40.0, min(90.0, 100.0 * (1.0 - _poisson_p0(est_ht))))
        ht_over_15_rate = max(12.0, min(65.0, 100.0 * _poisson_p_over15(est_ht)))
        avg_ht_goals    = est_ht

    last5    = recent_form[-5:] if len(recent_form) >= 5 else recent_form
    form_pts = sum(last5) / max(len(last5), 1) / 3.0   # 0–1

    # Scoring consistency: lower CoV = more consistent scorer
    if avg_gs > 0.1:
        cov  = (sum((g - avg_gs) ** 2 for g in goals_scored) / n) ** 0.5 / avg_gs
        sc   = max(0.0, min(1.0, 1.0 - cov * 0.6))
    else:
        sc = 0.2

    dw = min(1.0, avg_gc / max(avg_tot, 0.5))   # higher = leakier defence

    return {
        "team_name":          team_name,
        "games_analyzed":     n,
        "ht_games_with_data": ht_games,
        "avg_goals_scored":   round(avg_gs, 3),
        "avg_goals_conceded": round(avg_gc, 3),
        "avg_total_goals":    round(avg_tot, 3),
        "ht_over_05_rate":    round(ht_over_05_rate, 1),
        "ht_over_15_rate":    round(ht_over_15_rate, 1),
        "avg_ht_goals":       round(avg_ht_goals, 3),
        "form_recent":        round(form_pts, 3),
        "scoring_consistency": round(sc, 3),
        "defensive_weakness": round(dw, 3),
        "league_avg_goals":   round(avg_tot, 3),
        "league_id":          league_id,
    }


def get_h2h_stats(
    home_sched: List[Dict], away_sched: List[Dict],
    home_name: str, away_name: str,
) -> Optional[Dict]:
    h2h_games: List[Dict] = []
    for g in home_sched + away_sched:
        h = (g.get("home_name") or "").lower()
        a = (g.get("away_name") or "").lower()
        hn, an = home_name.lower(), away_name.lower()
        if (hn[:5] in h and an[:5] in a) or (hn[:5] in a and an[:5] in h):
            h2h_games.append(g)

    # Deduplicate by date
    seen:   set       = set()
    unique: List[Dict] = []
    for g in h2h_games:
        key = (g.get("date") or "")[:10]
        if key and key not in seen:
            seen.add(key)
            unique.append(g)

    if not unique:
        return None

    ht_totals:    List[int]   = []
    ht_over_05                = 0
    total_goals:  List[float] = []

    for g in unique:
        ht_t = g.get("ht_total")
        if ht_t is not None and isinstance(ht_t, (int, float)) and ht_t >= 0:
            ht_totals.append(int(ht_t))
            if ht_t >= 1:
                ht_over_05 += 1
        try:
            total_goals.append(
                float(g.get("home_score") or 0) + float(g.get("away_score") or 0)
            )
        except (TypeError, ValueError):
            pass

    h2h_ht_rate = (ht_over_05 / len(ht_totals) * 100.0) if ht_totals else 50.0

    return {
        "h2h_count":       len(unique),
        "h2h_avg_goals":   round(sum(total_goals) / max(len(total_goals), 1), 2),
        "h2h_ht_over_rate": round(h2h_ht_rate, 1),
        "h2h_avg_ht_goals": round(sum(ht_totals) / max(len(ht_totals), 1), 2),
    }


# ── Helpers ───────────────────────────────────────────────────────────────────
import math

def _poisson_p0(lam: float) -> float:
    return math.exp(-lam) if lam > 0 else 1.0

def _poisson_p_over15(lam: float) -> float:
    if lam <= 0:
        return 0.0
    p0 = math.exp(-lam)
    p1 = lam * p0
    return max(0.0, 1.0 - p0 - p1)
