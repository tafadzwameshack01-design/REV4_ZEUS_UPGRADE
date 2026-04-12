"""
ZEUS v4 — Poisson probability functions for Over 2.5 goal lines.
Primary target: P(total goals >= 3).
"""
import math
from typing import Tuple


def _pmf(k: int, lam: float) -> float:
    """Poisson probability mass function: P(X = k)."""
    if lam <= 0.0:
        return 1.0 if k == 0 else 0.0
    try:
        return (lam ** k) * math.exp(-lam) / math.factorial(k)
    except (OverflowError, ValueError):
        return 0.0


def p_over_05(lam_home: float, lam_away: float) -> float:
    """P(total goals >= 1)."""
    lh, la = max(0.01, lam_home), max(0.01, lam_away)
    p_zero = _pmf(0, lh) * _pmf(0, la)
    return float(max(0.01, min(0.99, 1.0 - p_zero)))


def p_over_15(lam_home: float, lam_away: float) -> float:
    """P(total goals >= 2)."""
    lh, la = max(0.01, lam_home), max(0.01, lam_away)
    p0 = _pmf(0, lh) * _pmf(0, la)
    p1 = _pmf(1, lh) * _pmf(0, la) + _pmf(0, lh) * _pmf(1, la)
    return float(max(0.01, min(0.99, 1.0 - p0 - p1)))


def p_over_25(lam_home: float, lam_away: float) -> float:
    """P(total goals >= 3) — primary signal for Over 2.5 market."""
    lh, la = max(0.01, lam_home), max(0.01, lam_away)
    p_under = 0.0
    for h in range(4):
        for a in range(4):
            if h + a <= 2:
                p_under += _pmf(h, lh) * _pmf(a, la)
    return float(max(0.01, min(0.99, 1.0 - p_under)))


def compute_lambdas(
    home_attack: float,
    home_defense: float,
    away_attack: float,
    away_defense: float,
    league_avg: float = 2.65,
) -> Tuple[float, float]:
    """
    Dixon-Coles-style lambda estimation with home advantage.
    Returns (lambda_home, lambda_away).
    """
    half_avg = max(0.1, league_avg / 2.0)
    home_factor = 1.15
    lam_home = max(0.1, home_attack * (away_defense / half_avg) * home_factor)
    lam_away = max(0.1, away_attack * (home_defense / half_avg))
    return round(lam_home, 4), round(lam_away, 4)


def simulate_over25(
    lam_home: float, lam_away: float, n_sims: int = 5000
) -> float:
    """Monte-Carlo cross-check for P(total >= 3)."""
    import random

    random.seed(42)

    def poisson_sample(lam: float) -> int:
        L = math.exp(-lam)
        k, p = 0, 1.0
        while p > L:
            k += 1
            p *= random.random()
        return k - 1

    hits = sum(
        1
        for _ in range(n_sims)
        if poisson_sample(lam_home) + poisson_sample(lam_away) >= 3
    )
    return round(hits / n_sims, 4)
