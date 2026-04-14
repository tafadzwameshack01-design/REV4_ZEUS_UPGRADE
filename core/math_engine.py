import math
from typing import Dict, Tuple, Optional

def poisson_prob(lam, k):
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return (lam ** k) * math.exp(-lam) / math.factorial(k)

def poisson_over_prob(lam, line):
    if lam <= 0:
        return 0.0
    under = sum(poisson_prob(lam, k) for k in range(int(line) + 1))
    return max(0.0, min(1.0, 1.0 - under))

def poisson_ht_over_05(xg_ht_total):
    p_zero = poisson_prob(xg_ht_total, 0)
    return max(0.0, min(1.0, 1.0 - p_zero))

def poisson_ht_over_15(xg_ht_total):
    p0 = poisson_prob(xg_ht_total, 0)
    p1 = poisson_prob(xg_ht_total, 1)
    return max(0.0, min(1.0, 1.0 - p0 - p1))

def dixon_coles_adjustment(xg_h, xg_a, rho=-0.13):
    if xg_h <= 0 or xg_a <= 0:
        return 1.0
    p00 = poisson_prob(xg_h, 0) * poisson_prob(xg_a, 0)
    adj = 1.0 + rho * (1.0 / (xg_h * xg_a)) * p00
    return max(0.5, min(1.5, adj))

def _xg_full(home_st: Dict, away_st: Dict) -> Tuple[float, float]:
    h_att = home_st.get("avg_goals_scored", 1.2)
    h_def = home_st.get("avg_goals_conceded", 1.1)
    a_att = away_st.get("avg_goals_scored", 1.0)
    a_def = away_st.get("avg_goals_conceded", 1.2)
    league_avg = home_st.get("league_avg_goals", 2.5) / 2.0
    if league_avg <= 0:
        league_avg = 1.25

    xg_h = (h_att / league_avg) * (a_def / league_avg) * league_avg * 1.05
    xg_a = (a_att / league_avg) * (h_def / league_avg) * league_avg * 0.95

    xg_h = max(0.1, min(4.0, xg_h))
    xg_a = max(0.1, min(4.0, xg_a))
    return round(xg_h, 3), round(xg_a, 3)

def _xg_ht(xg_h_full: float, xg_a_full: float) -> Tuple[float, float]:
    ht_ratio = 0.42
    return round(xg_h_full * ht_ratio, 3), round(xg_a_full * ht_ratio, 3)

def combined_ht_probability(xg_ht_h, xg_ht_a, line, dc_adj=1.0):
    total = xg_ht_h + xg_ht_a
    if line <= 0.5:
        raw = poisson_ht_over_05(total)
    else:
        raw = poisson_ht_over_15(total)
    return max(0.0, min(1.0, raw * dc_adj))
