"""
ZEUS v4 — Logistic regression model with online learning.
"""
import logging
import math
from typing import List, Optional, Tuple

import numpy as np

from data.constants import (
    FEATURE_DIM, LEARNING_RATE, LR_DECAY, L2_REG, WEIGHT_CLIP, RANDOM_SEED,
)

logger = logging.getLogger(__name__)


def sigmoid(x: float) -> float:
    """Numerically stable scalar sigmoid."""
    x = max(-50.0, min(50.0, x))
    return 1.0 / (1.0 + math.exp(-x))


def sigmoid_arr(x: np.ndarray) -> np.ndarray:
    """Vectorized sigmoid with clipping for stability."""
    return 1.0 / (1.0 + np.exp(-np.clip(x, -50, 50)))


class LogisticRegressionModel:
    """Simple logistic regression with L2 regularization and weight clipping."""

    def __init__(self, seed: int = RANDOM_SEED):
        rng = np.random.default_rng(seed)
        self.weights: np.ndarray = rng.normal(0, 0.01, FEATURE_DIM)
        self.bias: float = 0.0
        self.lr: float = LEARNING_RATE
        self.l2: float = L2_REG
        self.n_updates: int = 0
        self.epoch_losses: List[float] = []

    def predict(self, X: np.ndarray) -> float:
        """Single-sample prediction."""
        z = float(np.dot(self.weights, X)) + self.bias
        return sigmoid(z)

    def predict_batch(self, X: np.ndarray) -> np.ndarray:
        """Batch prediction across multiple samples."""
        z = X @ self.weights + self.bias
        return sigmoid_arr(z)

    def update(self, X: np.ndarray, y: float) -> float:
        """Single online gradient descent step. Returns the loss."""
        p = self.predict(X)
        error = p - y
        grad = error * X
        self.weights -= self.lr * (grad + self.l2 * self.weights)
        self.bias -= self.lr * error
        self.weights = np.clip(self.weights, -WEIGHT_CLIP, WEIGHT_CLIP)
        self.bias = float(np.clip(self.bias, -WEIGHT_CLIP, WEIGHT_CLIP))
        self.n_updates += 1
        if self.n_updates % 100 == 0:
            self.lr *= LR_DECAY
        loss = -(y * math.log(max(1e-9, p)) + (1 - y) * math.log(max(1e-9, 1 - p)))
        return loss

    def train_epoch(self, X: np.ndarray, y: np.ndarray) -> float:
        """Train one epoch over shuffled data."""
        indices = np.random.permutation(len(X))
        total_loss = 0.0
        for i in indices:
            total_loss += self.update(X[i], float(y[i]))
        avg = total_loss / max(1, len(X))
        self.epoch_losses.append(avg)
        return avg

    def train(self, X: np.ndarray, y: np.ndarray, epochs: int = 50) -> List[float]:
        """Train for multiple epochs and return per-epoch losses."""
        losses = []
        for _ in range(epochs):
            loss = self.train_epoch(X, y)
            losses.append(loss)
        return losses

    def get_weights(self) -> Tuple[List[float], float]:
        """Return serializable weights and bias."""
        return self.weights.tolist(), self.bias

    def set_weights(self, weights: List[float], bias: float):
        """Restore weights from a serialized form."""
        self.weights = np.clip(np.array(weights, dtype=float), -WEIGHT_CLIP, WEIGHT_CLIP)
        self.bias = float(np.clip(bias, -WEIGHT_CLIP, WEIGHT_CLIP))

    def is_stable(self) -> bool:
        """Check for NaN/Inf in weights or bias."""
        if np.any(np.isnan(self.weights)) or np.isnan(self.bias):
            return False
        if np.any(np.isinf(self.weights)) or np.isinf(self.bias):
            return False
        return True

    def reset_if_unstable(self, seed: int = RANDOM_SEED):
        """Reset to random initialization if numerical instability is detected."""
        if not self.is_stable():
            logger.warning("Model unstable (NaN/Inf detected), resetting weights.")
            rng = np.random.default_rng(seed)
            self.weights = rng.normal(0, 0.01, FEATURE_DIM)
            self.bias = 0.0
            self.lr = LEARNING_RATE * 0.1


_global_model: Optional[LogisticRegressionModel] = None


def get_model() -> LogisticRegressionModel:
    """Return the singleton model, loading persisted weights if available."""
    global _global_model
    if _global_model is None:
        _global_model = LogisticRegressionModel()
        try:
            from database.db import get_model_weights, get_model_bias
            w = get_model_weights()
            b = get_model_bias()
            if w is not None and len(w) == FEATURE_DIM:
                _global_model.set_weights(w, b)
        except Exception as exc:
            logger.warning("Failed to load persisted model: %s", exc)
    return _global_model


def persist_model():
    """Save the current model weights to the database."""
    global _global_model
    if _global_model is not None:
        try:
            from database.db import save_model_weights
            w, b = _global_model.get_weights()
            save_model_weights(w, b)
        except Exception as exc:
            logger.warning("Failed to persist model: %s", exc)
