"""
Confidence Engine — Poisson-anchored confidence scoring.

DESIGN:
  base_confidence = poisson_probability * 100   (mathematical ground truth)
  factor_adjustment = weighted deviation of stats factors from neutral (0.5)
  confidence = base_confidence + factor_adjustment * BOOST_SCALE

This means:
  - A match where xG/Poisson gives 65% HT probability starts at 65% confidence
  - Strong historical HT stats push it up toward 80-90%
  - Weak stats push it down
  - ELITE picks (>=elite_gate) are genuinely exceptional
"""

import json
import os
from typing import Dict, Optional
from core.constants import HT_BET_TYPES
from core.math_engine import (
    _xg_ht, poisson_ht_over_05, poisson_ht_over_15,
    dixon_coles_adjustment, combined_ht_probability,
)
from core.db import get_brain_state

WEIGHTS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "zeus_weights_v6.json"
)

# Maximum adjustment the stat factors can apply (±% points)
FACTOR_BOOST_SCALE = 30.0


def load_weights() -> dict:
    try:
        with open(WEIGHTS_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def run_gauntlet_and_compute(
    home_st: Dict, away_st: Dict,
    h2h: Optional[Dict],
    bet_type: str,
    xg_h: float, xg_a: float,
    league: str, match: str,
    gate_override: float = None,
    is_live: bool = False,
) -> Optional[Dict]:

    bt = HT_BET_TYPES.get(bet_type)
    if not bt:
        return None

    line      = bt["line"]
    base_gate = bt["gate"]

    weights_data = load_weights()
    bt_weights   = weights_data.get(bet_type, {}).get("weights", {})

    # ── Step 1: Poisson base probability ──────────────────────────────────────
    xg_ht_h, xg_ht_a = _xg_ht(xg_h, xg_a)
    xg_ht_total = xg_ht_h + xg_ht_a

    dc_adj    = dixon_coles_adjustment(xg_h, xg_a)
    if line <= 0.5:
        poisson_p = poisson_ht_over_05(xg_ht_total)
    else:
        poisson_p = poisson_ht_over_15(xg_ht_total)

    # Apply Dixon-Coles mild correction
    poisson_p_dc = max(0.01, min(0.99, poisson_p * dc_adj))

    # ── Step 2: Statistical factor scoring (deviation from neutral) ───────────
    factors      = {}
    total_weight = 0.0
    weighted_dev = 0.0   # weighted deviation from 0.5 neutral

    ht_rate_key = "ht_over_05_rate" if line <= 0.5 else "ht_over_15_rate"

    home_ht_rate = home_st.get(ht_rate_key, 50.0)
    away_ht_rate = away_st.get(ht_rate_key, 50.0)

    # HT over rate — home team
    w = bt_weights.get("ht_over_rate_home", 1.0)
    s = home_ht_rate / 100.0
    factors["ht_over_rate_home"] = {"value": home_ht_rate, "score": round(s, 3), "weight": w}
    weighted_dev += (s - 0.5) * w
    total_weight += w

    # HT over rate — away team
    w = bt_weights.get("ht_over_rate_away", 1.0)
    s = away_ht_rate / 100.0
    factors["ht_over_rate_away"] = {"value": away_ht_rate, "score": round(s, 3), "weight": w}
    weighted_dev += (s - 0.5) * w
    total_weight += w

    # xG total (higher = better for overs)
    w     = bt_weights.get("xg_total", 1.0)
    scale = 2.5 if line <= 0.5 else 3.5
    s     = min(1.0, xg_ht_total / scale)
    factors["xg_total"] = {"value": round(xg_ht_total, 2), "score": round(s, 3), "weight": w}
    weighted_dev += (s - 0.5) * w
    total_weight += w

    # Poisson probability itself as a factor (meta signal)
    w = bt_weights.get("poisson_over", 1.0)
    s = poisson_p
    factors["poisson_over"] = {"value": round(poisson_p * 100, 1), "score": round(s, 3), "weight": w}
    weighted_dev += (s - 0.5) * w
    total_weight += w

    # Dixon-Coles adjustment
    w = bt_weights.get("dixon_coles", 0.8)
    # Normalise dc_adj (range 0.5–1.5) to [0, 1]
    s = min(1.0, max(0.0, (dc_adj - 0.5) / 1.0))
    factors["dixon_coles"] = {"value": round(dc_adj, 3), "score": round(s, 3), "weight": w}
    weighted_dev += (s - 0.5) * w
    total_weight += w

    # Recent form (both teams attacking momentum)
    w        = bt_weights.get("form_recent", 0.9)
    form_avg = (home_st.get("form_recent", 0.5) + away_st.get("form_recent", 0.5)) / 2.0
    s        = form_avg
    factors["form_recent"] = {"value": round(form_avg, 2), "score": round(s, 3), "weight": w}
    weighted_dev += (s - 0.5) * w
    total_weight += w

    # Scoring consistency
    w  = bt_weights.get("scoring_consistency", 0.7)
    sc = (home_st.get("scoring_consistency", 0.5) + away_st.get("scoring_consistency", 0.5)) / 2.0
    s  = sc
    factors["scoring_consistency"] = {"value": round(sc, 2), "score": round(s, 3), "weight": w}
    weighted_dev += (s - 0.5) * w
    total_weight += w

    # Defensive weakness (conceding teams allow more goals)
    w  = bt_weights.get("defensive_weakness", 0.5)
    dw = (home_st.get("defensive_weakness", 0.5) + away_st.get("defensive_weakness", 0.5)) / 2.0
    s  = dw
    factors["defensive_weakness"] = {"value": round(dw, 2), "score": round(s, 3), "weight": w}
    weighted_dev += (s - 0.5) * w
    total_weight += w

    # H2H halftime over rate
    if h2h:
        w        = bt_weights.get("h2h_ht_over_rate", 0.8)
        h2h_rate = h2h.get("h2h_ht_over_rate", 50.0) / 100.0
        s        = h2h_rate
        factors["h2h_ht_over_rate"] = {"value": h2h.get("h2h_ht_over_rate", 50.0), "score": round(s, 3), "weight": w}
        weighted_dev += (s - 0.5) * w
        total_weight += w

    # League avg HT goals
    w       = bt_weights.get("league_avg_ht_goals", 0.6)
    avg_ht  = (home_st.get("avg_ht_goals", 0.6) + away_st.get("avg_ht_goals", 0.6)) / 2.0
    scale_l = 1.2 if line <= 0.5 else 2.2
    s       = min(1.0, avg_ht / scale_l)
    factors["league_avg_ht_goals"] = {"value": round(avg_ht, 2), "score": round(s, 3), "weight": w}
    weighted_dev += (s - 0.5) * w
    total_weight += w

    # ── Step 3: Combine poisson base + factor adjustment ──────────────────────
    norm_dev  = (weighted_dev / total_weight) if total_weight > 0 else 0.0
    factor_adj = norm_dev * FACTOR_BOOST_SCALE   # ±BOOST_SCALE points max

    confidence = poisson_p_dc * 100.0 + factor_adj
    confidence = max(0.0, min(99.0, confidence))

    # ── Step 4: Gate evaluation ───────────────────────────────────────────────
    effective_gate = gate_override if gate_override is not None else base_gate

    gate_elev, _, _ = get_brain_state(bet_type)
    if not is_live:
        effective_gate += gate_elev   # brain raises/lowers gate based on streaks

    from core.learning_engine import league_accuracy_adjustment
    league_id  = home_st.get("league_id", "")
    league_adj = league_accuracy_adjustment(league_id, bet_type)
    effective_gate += league_adj

    if confidence < effective_gate:
        return None

    return {
        "confidence":    round(confidence, 1),
        "factors":       factors,
        "factors_json":  json.dumps({k: v["value"] for k, v in factors.items()}),
        "xg_ht_h":       round(xg_ht_h, 2),
        "xg_ht_a":       round(xg_ht_a, 2),
        "xg_ht_total":   round(xg_ht_total, 2),
        "poisson_prob":  round(poisson_p * 100, 1),
        "poisson_dc":    round(poisson_p_dc * 100, 1),
        "dc_adjustment": round(dc_adj, 3),
        "factor_adj":    round(factor_adj, 2),
        "gate_used":     round(effective_gate, 1),
    }
