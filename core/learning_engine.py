"""
Autonomous Learning Engine.

Updates factor weights after each resolved prediction using gradient-style
adjustments. Incorporates momentum (velocity) to avoid oscillation.
Also manages per-league accuracy penalties and momentum-based pauses.
"""
import json
import os
import time
from typing import Dict
from core.db import db_execute, db_fetchone, db_fetchall, get_brain_state, set_brain_state
from core.time_utils import utc_iso, epoch_now

WEIGHTS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "zeus_weights_v6.json"
)

# Velocity store for each (bet_type, factor) — kept in-memory per process
_velocity: Dict[str, float] = {}
_MOMENTUM = 0.7     # fraction of previous velocity to carry forward
_LR_WIN   = 0.018   # learning rate on win
_LR_LOSS  = 0.028   # learning rate on loss (slightly higher — punish errors more)
_W_MIN    = 0.05
_W_MAX    = 3.5


def load_weights() -> dict:
    try:
        with open(WEIGHTS_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def save_weights(data: dict):
    try:
        os.makedirs(os.path.dirname(WEIGHTS_PATH), exist_ok=True)
        with open(WEIGHTS_PATH, "w") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def update_weights(bet_type: str, factors: Dict, won: bool,
                   confidence: float, ht_total: int, league_id: str = ""):
    weights_data = load_weights()
    bt      = weights_data.get(bet_type, {})
    weights = bt.get("weights", {})

    direction = 1.0 if won else -1.0
    lr        = _LR_WIN if won else _LR_LOSS

    # Confidence-scaled learning rate: high-confidence wrong predictions learn faster
    if not won and confidence > 80:
        lr *= 1.5
    elif won and confidence < 70:
        lr *= 0.7   # lucky win — learn less from it

    for factor_name, factor_value in factors.items():
        if factor_name not in weights:
            continue
        try:
            fv      = float(factor_value)
            old_w   = weights[factor_name]
            vkey    = f"{bet_type}_{factor_name}"

            # Signal: how much did this factor's value deviate from neutral?
            signal  = (fv / 100.0 if fv > 1.0 else fv) - 0.5   # approx deviation
            grad    = lr * direction * signal

            # Apply momentum
            prev_v  = _velocity.get(vkey, 0.0)
            new_v   = _MOMENTUM * prev_v + grad
            _velocity[vkey] = new_v

            new_w   = max(_W_MIN, min(_W_MAX, old_w + new_v))
            weights[factor_name] = round(new_w, 4)
        except (ValueError, TypeError):
            pass

    bt["weights"]            = weights
    bt["total_predictions"]  = bt.get("total_predictions", 0) + 1
    if won:
        bt["wins"]   = bt.get("wins", 0) + 1
    else:
        bt["losses"] = bt.get("losses", 0) + 1

    weights_data[bet_type] = bt
    save_weights(weights_data)

    _update_brain_state(bet_type, won)
    _update_league_accuracy(league_id, bet_type, won)
    _check_momentum_pause(bet_type)

    total = bt["total_predictions"]
    acc   = bt["wins"] / max(total, 1) * 100
    db_execute(
        "INSERT INTO weights_history (bet_type, weights_json, accuracy, logged_at) VALUES (?,?,?,?)",
        (bet_type, json.dumps(weights), acc, utc_iso()),
    )


def _update_brain_state(bet_type: str, won: bool):
    gate_elev, streak_w, streak_l = get_brain_state(bet_type)

    if won:
        streak_w += 1
        streak_l  = 0
        if streak_w >= 3:
            gate_elev = max(-8.0, gate_elev - 0.8)  # loosen gate on winning streak
        if streak_w >= 6:
            gate_elev = max(-12.0, gate_elev - 1.0)
    else:
        streak_l += 1
        streak_w  = 0
        if streak_l >= 2:
            gate_elev = min(8.0,  gate_elev + 1.5)  # tighten gate on losing streak
        if streak_l >= 4:
            gate_elev = min(15.0, gate_elev + 3.0)

    set_brain_state(bet_type, gate_elev, streak_w, streak_l)


def _update_league_accuracy(league_id: str, bet_type: str, won: bool):
    if not league_id:
        return
    col = "wins" if won else "losses"
    db_execute(
        f"""INSERT INTO league_accuracy (league_id, bet_type, {col}, updated_at)
            VALUES (?, ?, 1, ?)
            ON CONFLICT(league_id, bet_type) DO UPDATE SET
            {col} = {col} + 1, updated_at = ?""",
        (league_id, bet_type, utc_iso(), utc_iso()),
    )


def league_accuracy_adjustment(league_id: str, bet_type: str) -> float:
    """Gate adjustment based on league-specific track record (needs 20+ samples)."""
    if not league_id:
        return 0.0
    row = db_fetchone(
        "SELECT wins, losses FROM league_accuracy WHERE league_id=? AND bet_type=?",
        (league_id, bet_type),
    )
    if not row:
        return 0.0
    wins, losses = row
    total = wins + losses
    if total < 20:
        return 0.0
    accuracy = wins / total
    if accuracy < 0.38:
        return 10.0   # severe penalty
    if accuracy < 0.48:
        return 5.0
    if accuracy < 0.55:
        return 2.0
    if accuracy > 0.68:
        return -3.0   # reward well-performing leagues
    return 0.0


def _check_momentum_pause(bet_type: str):
    rows = db_fetchall(
        "SELECT result FROM picks_log WHERE bet_type=? ORDER BY logged_at DESC LIMIT 6",
        (bet_type,),
    )
    if len(rows) >= 5:
        losses = sum(1 for r in rows if r[0] == "LOSS")
        if losses >= 4:
            pause_until = epoch_now() + 7200   # 2-hour cool-off
            db_execute(
                "INSERT OR REPLACE INTO prediction_pauses (bet_type, pause_until, reason) VALUES (?,?,?)",
                (bet_type, pause_until, f"{losses} losses in last {len(rows)} — 2h cooling period"),
            )


def is_bet_type_paused(bet_type: str) -> bool:
    row = db_fetchone(
        "SELECT pause_until FROM prediction_pauses WHERE bet_type=?",
        (bet_type,),
    )
    return bool(row and row[0] > epoch_now())


def get_accuracy_stats() -> dict:
    data  = load_weights()
    stats = {}
    for bt, info in data.items():
        total = info.get("total_predictions", 0)
        wins  = info.get("wins", 0)
        stats[bt] = {
            "total":    total,
            "wins":     wins,
            "losses":   info.get("losses", 0),
            "accuracy": round(wins / max(total, 1) * 100, 1),
            "weights":  info.get("weights", {}),
        }
    return stats


def get_weight_velocity(bet_type: str) -> Dict[str, float]:
    """Return current velocity values for a given bet type (for UI display)."""
    result = {}
    for key, val in _velocity.items():
        if key.startswith(bet_type + "_"):
            factor = key[len(bet_type) + 1:]
            result[factor] = round(val, 5)
    return result
