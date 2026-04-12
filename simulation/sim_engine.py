"""
ZEUS v4 — Self-repair simulation engine.
Trains and validates the ML model on synthetic data,
auto-fixing numerical instabilities.
"""
import logging
import math
from typing import Dict, List, Optional, Tuple

import numpy as np

from data.constants import (
    RANDOM_SEED, SIM_MATCHES, SIM_MAX_ITER, FEATURE_DIM,
    LEARNING_RATE, L2_REG, MIN_ACCURACY, MIN_ROI, MAX_DRAWDOWN_LIMIT,
    CONFIDENCE_THRESH, INITIAL_BANKROLL, MIN_ODDS, STAKE_FRACTION,
)
from utils.helpers import brier_score, log_loss_score

logger = logging.getLogger(__name__)


def generate_synthetic_matches(
    n: int, seed: int = RANDOM_SEED
) -> Tuple[np.ndarray, np.ndarray]:
    """Generate synthetic match data calibrated for Over 2.5 analysis."""
    rng = np.random.default_rng(seed)
    lam_home = rng.gamma(shape=2.0, scale=0.85, size=n)
    lam_away = rng.gamma(shape=1.6, scale=0.85, size=n)
    home_goals = rng.poisson(lam_home)
    away_goals = rng.poisson(lam_away)
    total_goals = home_goals + away_goals
    y = (total_goals >= 3).astype(float)

    league_intensity = rng.uniform(0.6, 1.0, n)
    tempo = rng.uniform(0.5, 1.0, n)
    consistency = rng.beta(4, 2, n)
    btts = rng.beta(4, 2, n)
    home_def = rng.gamma(1.5, 0.6, n)
    away_def = rng.gamma(1.3, 0.6, n)

    X = np.column_stack([
        lam_home, home_def, lam_away, away_def,
        league_intensity, tempo, consistency, btts,
    ])
    norms = np.linalg.norm(X, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1, norms)
    X = np.clip(X / norms, -3.0, 3.0)
    return X.astype(np.float64), y.astype(np.float64)


def simulate_betting_roi(
    model,
    X: np.ndarray,
    y: np.ndarray,
    confidence_threshold: float = CONFIDENCE_THRESH,
    stake_fraction: float = STAKE_FRACTION,
    rng: Optional[np.random.Generator] = None,
) -> Tuple[float, float, float, float]:
    """Simulate betting over synthetic data and return ROI metrics."""
    if rng is None:
        rng = np.random.default_rng(RANDOM_SEED)
    bankroll = INITIAL_BANKROLL
    peak = INITIAL_BANKROLL
    max_dd = 0.0
    total_staked = 0.0
    total_pnl = 0.0
    wins = 0
    bets = 0

    for i in range(len(X)):
        p = float(np.dot(model.weights, X[i])) + model.bias
        p = 1.0 / (1.0 + math.exp(-max(-50, min(50, p))))
        p = max(0.01, min(0.99, p))
        confidence = p * 0.9
        if confidence < confidence_threshold:
            continue
        odds = rng.uniform(MIN_ODDS, 2.20)
        edge = p * odds - 1.0
        if edge <= 0:
            continue
        b = odds - 1.0
        q = 1.0 - p
        kelly_f = max(0.0, min(0.25, (b * p - q) / b))
        stake = max(0.5, min(bankroll * 0.10, bankroll * kelly_f * stake_fraction))
        if stake <= 0 or bankroll <= 0:
            break
        if float(y[i]) >= 1.0:
            pnl = stake * (odds - 1.0)
            wins += 1
        else:
            pnl = -stake
        bankroll += pnl
        total_staked += stake
        total_pnl += pnl
        bets += 1
        if bankroll > peak:
            peak = bankroll
        dd = (peak - bankroll) / max(peak, 1.0)
        if dd > max_dd:
            max_dd = dd

    roi = total_pnl / max(total_staked, 1.0)
    win_rate = wins / max(bets, 1)
    return roi, max_dd, win_rate, float(bets)


def evaluate_model(
    model, X: np.ndarray, y: np.ndarray, rng: Optional[np.random.Generator] = None
) -> Dict:
    """Evaluate the model across all quality metrics."""
    preds = model.predict_batch(X)
    preds = np.clip(preds, 1e-7, 1 - 1e-7)
    brier = brier_score(preds.tolist(), y.tolist())
    ll = log_loss_score(preds.tolist(), y.tolist())
    acc = float(np.mean((preds >= 0.5) == (y >= 0.5)))
    roi, max_dd, win_rate, n_bets = simulate_betting_roi(model, X, y, rng=rng)
    return {
        "accuracy": acc,
        "log_loss": ll,
        "brier": brier,
        "roi": roi,
        "max_drawdown": max_dd,
        "win_rate": win_rate,
        "n_bets": n_bets,
        "has_nan": bool(np.any(np.isnan(model.weights)) or np.isnan(model.bias)),
        "has_inf": bool(np.any(np.isinf(model.weights)) or np.isinf(model.bias)),
    }


def detect_failures(metrics: Dict, model) -> List[str]:
    """Detect quality failures that require auto-fix."""
    errors = []
    if metrics["has_nan"]:
        errors.append("NaN values in model weights")
    if metrics["has_inf"]:
        errors.append("Inf values in model weights")
    if metrics["roi"] < MIN_ROI:
        errors.append(f"ROI={metrics['roi']:.3f} below minimum {MIN_ROI}")
    if metrics["max_drawdown"] > MAX_DRAWDOWN_LIMIT:
        errors.append(f"Drawdown={metrics['max_drawdown']:.3f} exceeds limit {MAX_DRAWDOWN_LIMIT}")
    if metrics["accuracy"] < MIN_ACCURACY:
        errors.append(f"Accuracy={metrics['accuracy']:.3f} below minimum {MIN_ACCURACY}")
    return errors


def auto_fix(model, metrics: Dict, errors: List[str], seed: int = RANDOM_SEED):
    """Attempt to repair the model based on detected failures."""
    if metrics["has_nan"] or metrics["has_inf"]:
        logger.warning("Resetting model due to NaN/Inf in weights")
        rng = np.random.default_rng(seed)
        model.weights = rng.normal(0, 0.01, FEATURE_DIM)
        model.bias = 0.0
        model.lr = LEARNING_RATE * 0.5
        return
    if metrics["accuracy"] < MIN_ACCURACY:
        model.lr = min(0.1, model.lr * 1.5)
    if metrics["roi"] < MIN_ROI:
        model.lr = max(0.001, model.lr * 0.8)
        model.l2 = min(0.01, model.l2 * 1.5)
    if metrics["max_drawdown"] > MAX_DRAWDOWN_LIMIT:
        model.l2 = min(0.01, model.l2 * 2.0)
    model.weights = np.clip(model.weights, -3.0, 3.0)
    model.bias = float(np.clip(model.bias, -3.0, 3.0))


def run_simulation_loop(
    n_matches: int = SIM_MATCHES,
    max_iterations: int = SIM_MAX_ITER,
    seed: int = RANDOM_SEED,
) -> Tuple[object, Dict, List[Dict]]:
    """Run the full self-repair simulation loop."""
    from models.ml_model import LogisticRegressionModel
    from database.db import save_simulation_log

    rng = np.random.default_rng(seed)
    model = LogisticRegressionModel(seed=seed)
    final_metrics: Dict = {}
    logs: List[Dict] = []

    for iteration in range(max_iterations):
        iter_seed = seed + iteration * 37
        X, y = generate_synthetic_matches(n_matches, seed=iter_seed)
        split = int(n_matches * 0.8)
        X_train, X_val = X[:split], X[split:]
        y_train, y_val = y[:split], y[split:]

        epochs = 60 + iteration * 10
        for _ in range(epochs):
            idx = rng.permutation(len(X_train))
            for i in idx:
                p = model.predict(X_train[i])
                err = p - float(y_train[i])
                grad = err * X_train[i]
                model.weights -= model.lr * (grad + model.l2 * model.weights)
                model.bias -= model.lr * err
                model.weights = np.clip(model.weights, -5.0, 5.0)
                model.bias = float(np.clip(model.bias, -5.0, 5.0))

        metrics = evaluate_model(model, X_val, y_val, rng=rng)
        final_metrics = metrics
        errors = detect_failures(metrics, model)
        passed = len(errors) == 0

        log_entry = {
            "iteration": iteration + 1,
            "n_matches": n_matches,
            "accuracy": round(metrics["accuracy"], 4),
            "log_loss": round(metrics["log_loss"], 4),
            "brier": round(metrics["brier"], 4),
            "roi": round(metrics["roi"], 4),
            "max_drawdown": round(metrics["max_drawdown"], 4),
            "win_rate": round(metrics["win_rate"], 4),
            "passed": passed,
        }
        logs.append(log_entry)
        save_simulation_log(log_entry)

        if passed:
            logger.info("Simulation passed on iteration %d", iteration + 1)
            break

        auto_fix(model, metrics, errors, seed=iter_seed)

    if not model.is_stable():
        model.reset_if_unstable(seed)

    from database.db import save_model_weights
    w, b = model.get_weights()
    save_model_weights(w, b)

    import models.ml_model as ml_mod
    ml_mod._global_model = model

    return model, final_metrics, logs
