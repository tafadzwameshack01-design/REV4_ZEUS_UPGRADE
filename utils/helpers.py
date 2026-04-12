"""
ZEUS v4 — Utility functions for time handling, scoring, and classification.
"""
import hashlib
import logging
import math
from datetime import datetime, timezone, timedelta
from typing import List, Optional

import requests

from data.constants import CAT_OFFSET, WINDOW_HOURS, HEADERS

logger = logging.getLogger(__name__)


def safe_mean(lst: list) -> float:
    """Return the arithmetic mean of a list, or 0.0 if empty."""
    if not lst:
        return 0.0
    return float(sum(lst) / len(lst))


def safe_get(url: str, params: Optional[dict] = None, timeout: int = 10) -> Optional[dict]:
    """HTTP GET with 3 retries and exponential back-off."""
    import time

    for attempt in range(3):
        try:
            r = requests.get(url, headers=HEADERS, params=params or {}, timeout=timeout)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.RequestException as exc:
            logger.warning("HTTP request failed (attempt %d/3): %s", attempt + 1, exc)
            if attempt == 2:
                return None
            time.sleep(0.5 * (attempt + 1))
    return None


def now_utc() -> datetime:
    """Return the current UTC datetime."""
    return datetime.now(timezone.utc)


def to_cat(utc_str: str) -> str:
    """Convert a UTC ISO string to Central Africa Time display string."""
    try:
        dt = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
        return (dt + CAT_OFFSET).strftime("%d %b \u00b7 %H:%M CAT")
    except (ValueError, TypeError):
        return "\u2014"


def parse_utc(utc_str: str) -> Optional[datetime]:
    """Parse a UTC ISO string into a timezone-aware datetime."""
    try:
        return datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def in_window(utc_str: str) -> bool:
    """Check if a kickoff time falls within the scanning window."""
    dt = parse_utc(utc_str)
    if not dt:
        return False
    n = now_utc()
    return n <= dt <= n + timedelta(hours=WINDOW_HOURS)


def minutes_to_kickoff(utc_str: str) -> int:
    """Return minutes until kickoff, or 9999 if unparseable."""
    dt = parse_utc(utc_str)
    if not dt:
        return 9999
    return max(0, int((dt - now_utc()).total_seconds() / 60))


def match_id(home: str, away: str, kickoff: str) -> str:
    """Generate a deterministic short ID for a match."""
    raw = f"{home}{away}{kickoff}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def parse_score(raw) -> int:
    """Safely extract an integer score from various formats."""
    if raw is None:
        return 0
    if isinstance(raw, dict):
        raw = raw.get("value", raw.get("displayValue", 0))
    try:
        return int(float(str(raw)))
    except (ValueError, TypeError):
        return 0


def bce_loss(p: float, y: float) -> float:
    """Binary cross-entropy loss for a single prediction."""
    p = max(1e-9, min(1 - 1e-9, p))
    return -(y * math.log(p) + (1 - y) * math.log(1 - p))


def brier_score(predictions: list, actuals: list) -> float:
    """Mean squared error between predictions and actual outcomes."""
    if not predictions:
        return 1.0
    return sum((p - a) ** 2 for p, a in zip(predictions, actuals)) / len(predictions)


def log_loss_score(predictions: list, actuals: list) -> float:
    """Mean log loss across all predictions."""
    if not predictions:
        return 10.0
    return sum(bce_loss(p, a) for p, a in zip(predictions, actuals)) / len(predictions)


def get_tier(conf_pct: float) -> str:
    """Classify confidence percentage into a tier name."""
    from data.constants import TIER_ELITE, TIER_STRONG
    if conf_pct >= TIER_ELITE:
        return "elite"
    if conf_pct >= TIER_STRONG:
        return "strong"
    return "good"


def get_tier_label(conf_pct: float) -> str:
    """Return a display label for the confidence tier."""
    from data.constants import TIER_ELITE, TIER_STRONG
    if conf_pct >= TIER_ELITE:
        return "ELITE"
    if conf_pct >= TIER_STRONG:
        return "STRONG"
    return "CONFIDENT"
