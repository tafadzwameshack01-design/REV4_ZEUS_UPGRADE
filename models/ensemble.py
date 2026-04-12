"""
ZEUS v4 Ensemble — Over 2.5 Goals predictor.
Combines Poisson + ML with a 7-factor confidence scorer.
"""
import numpy as np
from typing import Dict, Optional, Tuple

from models.poisson_model import p_over_25, compute_lambdas
from models.ml_model import get_model

POISSON_WEIGHT = 0.65
ML_WEIGHT = 0.35


def build_feature_vector(
    home_attack: float,
    home_defense: float,
    away_attack: float,
    away_defense: float,
    league_intensity: float,
    tempo_score: float,
    over25_consistency: float,
    btts_score: float,
) -> np.ndarray:
    """Build and normalize an 8-dimensional feature vector."""
    X = np.array([
        home_attack, home_defense, away_attack, away_defense,
        league_intensity, tempo_score, over25_consistency, btts_score,
    ], dtype=float)
    norm = np.linalg.norm(X)
    if norm > 0:
        X = X / norm
    return np.clip(X, -3.0, 3.0)


def ensemble_predict(
    home_st: Dict,
    away_st: Dict,
    league_id: str,
    league_avg: float = 2.65,
) -> Tuple[float, float, float, float, float]:
    """
    Combined prediction pipeline.
    Returns (p_poisson, p_ml, p_ensemble, xg_home, xg_away).
    """
    lam_home, lam_away = compute_lambdas(
        home_st.get("avg_scored", 1.5),
        home_st.get("avg_conceded", 1.3),
        away_st.get("avg_scored", 1.2),
        away_st.get("avg_conceded", 1.1),
        league_avg,
    )

    p_pois = p_over_25(lam_home, lam_away)

    xg_home = max(0.1, (
        0.60 * home_st.get("home_avg_scored", home_st.get("avg_scored", 1.5))
        + 0.40 * away_st.get("away_avg_conceded", away_st.get("avg_conceded", 1.1))
    ))
    xg_away = max(0.1, (
        0.60 * away_st.get("away_avg_scored", away_st.get("avg_scored", 1.2))
        + 0.40 * home_st.get("home_avg_conceded", home_st.get("avg_conceded", 1.3))
    ))
    xg_total = xg_home + xg_away

    over25_home = home_st.get("over25_rate", 0.50)
    over25_away = away_st.get("over25_rate", 0.50)
    over25_avg = (over25_home + over25_away) / 2.0

    btts_home = home_st.get("btts_rate", 0.50)
    btts_away = away_st.get("btts_rate", 0.50)
    btts_avg = (btts_home + btts_away) / 2.0

    tempo = min(1.0, xg_total / 5.0)
    intensity = min(1.0, league_avg / 4.0)

    X = build_feature_vector(
        home_attack=min(3.0, xg_home),
        home_defense=min(3.0, home_st.get("avg_conceded", 1.3)),
        away_attack=min(3.0, xg_away),
        away_defense=min(3.0, away_st.get("avg_conceded", 1.1)),
        league_intensity=intensity,
        tempo_score=tempo,
        over25_consistency=over25_avg,
        btts_score=btts_avg,
    )

    model = get_model()
    model.reset_if_unstable()
    p_ml = max(0.01, min(0.99, model.predict(X)))

    p_ensemble = POISSON_WEIGHT * p_pois + ML_WEIGHT * p_ml
    p_ensemble = max(0.01, min(0.99, p_ensemble))

    return (
        round(p_pois, 4),
        round(p_ml, 4),
        round(p_ensemble, 4),
        round(xg_home, 3),
        round(xg_away, 3),
    )


def compute_confidence(
    p_ensemble: float,
    home_st: Dict,
    away_st: Dict,
    league_avg: float = 2.65,
    h2h_over25_rate: Optional[float] = None,
) -> float:
    """7-factor confidence score for Over 2.5 predictions."""
    prob_factor = p_ensemble

    o25_home = home_st.get("over25_rate", 0.50)
    o25_away = away_st.get("over25_rate", 0.50)
    o25_factor = (o25_home + o25_away) / 2.0

    btts_home = home_st.get("btts_rate", 0.45)
    btts_away = away_st.get("btts_rate", 0.45)
    btts_factor = (btts_home + btts_away) / 2.0

    last3_home = home_st.get("last3_avg", 2.5)
    last3_away = away_st.get("last3_avg", 2.5)
    form_factor = min(1.0, (last3_home + last3_away) / 2.0 / 4.0)

    cs_home = home_st.get("clean_sheet_rate", 0.2)
    cs_away = away_st.get("clean_sheet_rate", 0.2)
    cs_penalty = 1.0 - (cs_home + cs_away) / 2.0 * 0.7

    variance = np.var([o25_home, o25_away])
    stability = 1.0 / (1.0 + variance * 8.0)

    h2h_boost = 1.0
    if h2h_over25_rate is not None:
        h2h_boost = 0.92 + h2h_over25_rate * 0.15

    league_factor = min(1.0, league_avg / 3.8)

    composite = (
        prob_factor * 0.30
        + o25_factor * 0.25
        + btts_factor * 0.18
        + form_factor * 0.12
        + 0.15
    ) * stability * cs_penalty * league_factor * h2h_boost

    return float(max(0.0, min(0.99, composite)))
