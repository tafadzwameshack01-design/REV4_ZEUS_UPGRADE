"""
ZEUS v4 — Kelly Criterion staking engine for Over 2.5 picks.
WIN_THRESHOLD = 3 (match must have >= 3 goals to win Over 2.5 bet).
"""
import hashlib
import logging
import math
from typing import Dict, Optional, Tuple
from datetime import datetime, timezone

import numpy as np

from data.constants import (
    MIN_ODDS, STAKE_FRACTION, MAX_DAILY_EXPOSURE, MAX_CONCURRENT,
    LOSS_HALVE_STREAK, LOSS_HALT_STREAK, INITIAL_BANKROLL, CONFIDENCE_THRESH,
    OVER_LINE,
)
from database.db import (
    get_bankroll, set_bankroll, get_loss_streak, set_loss_streak,
    is_betting_halted, set_betting_halted,
)

logger = logging.getLogger(__name__)

WIN_THRESHOLD = 3


def kelly_fraction(p: float, odds: float) -> float:
    """Calculate the Kelly fraction for a given probability and odds."""
    b = max(0.001, odds - 1.0)
    q = 1.0 - p
    f = (b * p - q) / b
    return max(0.0, min(0.20, f))


def compute_edge(p: float, odds: float) -> float:
    """Calculate the expected edge: p * odds - 1."""
    return round(p * odds - 1.0, 4)


def compute_stake(
    p_ensemble: float,
    odds: float,
    bankroll: Optional[float] = None,
    loss_streak: Optional[int] = None,
) -> Tuple[float, float, float]:
    """
    Calculate the recommended stake using fractional Kelly.
    Returns (stake, kelly_f, edge).
    """
    if bankroll is None:
        bankroll = get_bankroll()
    if loss_streak is None:
        loss_streak = get_loss_streak()
    if bankroll <= 0:
        return 0.0, 0.0, 0.0

    kf = kelly_fraction(p_ensemble, odds)
    edge = compute_edge(p_ensemble, odds)

    if edge <= 0:
        return 0.0, kf, edge

    stake = bankroll * kf * STAKE_FRACTION

    if loss_streak >= LOSS_HALVE_STREAK:
        stake *= 0.5

    max_single = bankroll * 0.08
    stake = max(0.5, min(max_single, stake))

    return round(stake, 2), round(kf, 4), round(edge, 4)


def should_bet(
    p_ensemble: float,
    odds: float,
    confidence: float,
    active_bets: int = 0,
) -> Tuple[bool, str]:
    """Determine whether a bet should be placed. Returns (should_bet, reason)."""
    if is_betting_halted():
        return False, "Betting halted after consecutive losses"

    loss_streak = get_loss_streak()
    if loss_streak >= LOSS_HALT_STREAK:
        set_betting_halted(True)
        return False, f"Betting halted: {loss_streak} consecutive losses"

    if confidence < CONFIDENCE_THRESH:
        return False, f"Confidence {confidence:.3f} below threshold {CONFIDENCE_THRESH}"

    if odds < MIN_ODDS:
        return False, f"Odds {odds:.2f} below minimum {MIN_ODDS}"

    edge = compute_edge(p_ensemble, odds)
    if edge <= 0:
        return False, f"No edge: {edge:.4f}"

    if active_bets >= MAX_CONCURRENT:
        return False, f"Max concurrent bets ({MAX_CONCURRENT}) reached"

    return True, "OK"


def record_result(
    prediction_id: str,
    match_label: str,
    total_goals: int,
    p_ensemble: float,
    odds: float,
    stake: float,
) -> Dict:
    """Record a graded match result and update the bankroll."""
    from database.db import save_result

    bankroll = get_bankroll()
    loss_streak = get_loss_streak()
    won = total_goals >= WIN_THRESHOLD

    if won:
        pnl = stake * (odds - 1.0)
        outcome = "WON"
        new_streak = 0
    else:
        pnl = -stake
        outcome = "LOST"
        new_streak = loss_streak + 1

    new_bankroll = bankroll + pnl
    set_bankroll(new_bankroll, pnl, f"{outcome}: {match_label}")
    set_loss_streak(new_streak)

    if new_streak >= LOSS_HALT_STREAK:
        set_betting_halted(True)

    result_id = hashlib.md5(
        f"{prediction_id}{datetime.now(timezone.utc).isoformat()}".encode()
    ).hexdigest()[:12]

    res = {
        "id": result_id,
        "prediction_id": prediction_id,
        "match_label": match_label,
        "outcome": outcome,
        "total_goals": total_goals,
        "p_ensemble": p_ensemble,
        "odds": odds,
        "stake": stake,
        "pnl": round(pnl, 2),
    }
    save_result(res)

    from models.ml_model import get_model, persist_model

    model = get_model()
    p_sq = p_ensemble ** 0.5
    X = np.array([
        p_sq,
        1.0 - p_sq * 0.5,
        p_sq * 0.85,
        1.0 - p_sq * 0.4,
        0.6,
        min(1.0, p_ensemble * 1.1),
        p_ensemble,
        p_ensemble * 0.9,
    ], dtype=float)
    norm = np.linalg.norm(X)
    if norm > 0:
        X = X / norm
    X = np.clip(X, -3.0, 3.0)
    model.update(X, 1.0 if won else 0.0)
    persist_model()

    return res


def get_roi_stats() -> Dict:
    """Calculate aggregate ROI statistics from graded results."""
    from database.db import get_results

    results = get_results(limit=500)
    if not results:
        return {
            "total": 0, "won": 0, "lost": 0,
            "win_rate": 0.0, "total_staked": 0.0, "total_pnl": 0.0,
            "roi": 0.0, "bankroll": get_bankroll(),
        }
    won = [r for r in results if r["outcome"] == "WON"]
    lost = [r for r in results if r["outcome"] == "LOST"]
    total_staked = sum(r["stake"] for r in results)
    total_pnl = sum(r["pnl"] for r in results)
    graded = len(won) + len(lost)
    roi = total_pnl / max(total_staked, 1.0)
    return {
        "total": len(results),
        "won": len(won),
        "lost": len(lost),
        "win_rate": len(won) / max(graded, 1),
        "total_staked": round(total_staked, 2),
        "total_pnl": round(total_pnl, 2),
        "roi": round(roi, 4),
        "bankroll": get_bankroll(),
    }
