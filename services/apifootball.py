"""
ZEUS v4 — API-Football v3 data service.
Fetches fixtures and results from the API-Sports direct endpoint.
"""
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

import requests
import streamlit as st

from data.constants import APIFOOTBALL_KEY, WINDOW_HOURS

logger = logging.getLogger(__name__)

_BASE = "https://v3.football.api-sports.io"
_HDRS = {
    "x-apisports-key": APIFOOTBALL_KEY,
}

LEAGUE_MAP: Dict[str, tuple] = {
    "eng.1": (39, 2025), "esp.1": (140, 2025), "ger.1": (78, 2025),
    "ita.1": (135, 2025), "fra.1": (61, 2025),
    "eng.2": (40, 2025), "esp.2": (141, 2025), "ger.2": (79, 2025),
    "ita.2": (136, 2025), "fra.2": (62, 2025),
    "ned.1": (88, 2025), "por.1": (94, 2025), "bel.1": (144, 2025),
    "sco.1": (179, 2025), "tur.1": (203, 2025), "rus.1": (235, 2025),
    "aut.1": (218, 2025), "gre.1": (197, 2025), "cze.1": (345, 2025),
    "pol.1": (106, 2025), "den.1": (119, 2025), "swe.1": (113, 2026),
    "nor.1": (103, 2026), "sui.1": (207, 2025), "ukr.1": (333, 2025),
    "srb.1": (286, 2025), "cro.1": (210, 2025),
    "usa.1": (253, 2026), "bra.1": (71, 2026), "arg.1": (128, 2026),
    "mex.1": (262, 2025), "col.1": (239, 2026), "chi.1": (265, 2026),
    "ecu.1": (268, 2026), "per.1": (281, 2026), "uru.1": (278, 2026),
    "ven.1": (232, 2026), "bol.1": (303, 2026),
    "jpn.1": (98, 2026), "kor.1": (292, 2026), "chn.1": (169, 2026),
    "aus.1": (188, 2025), "ind.1": (323, 2025), "sau.1": (307, 2025),
    "egy.1": (233, 2025), "mar.1": (200, 2025), "rsa.1": (288, 2025),
    "nig.1": (363, 2025),
    "uefa.champions": (2, 2025), "uefa.europa": (3, 2025),
    "conmebol.libertadores": (13, 2026),
}


def _get(endpoint: str, params: dict) -> Optional[dict]:
    """Resilient GET with 3 retries and back-off. Fails immediately if no API key."""
    if not APIFOOTBALL_KEY:
        return None

    url = f"{_BASE}/{endpoint}"
    for attempt in range(3):
        try:
            r = requests.get(url, headers=_HDRS, params=params, timeout=8)
            if r.status_code == 401:
                logger.warning("API key unauthorized (401) — check your RapidAPI subscription for api-football.")
                return None
            if r.status_code == 429:
                logger.warning("API rate limit hit (429) — daily quota may be exhausted.")
                return None
            r.raise_for_status()
            return r.json()
        except requests.exceptions.RequestException as exc:
            logger.warning("API request failed (attempt %d/3): %s", attempt + 1, exc)
            if attempt == 2:
                return None
            time.sleep(2.0 * (attempt + 1))
    return None


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _in_window(date_str: str) -> bool:
    """Check if a fixture falls within the scan window."""
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        now = _now_utc()
        return now <= dt <= now + timedelta(hours=WINDOW_HOURS)
    except (ValueError, TypeError):
        return False


def _safe_int(val) -> int:
    try:
        return int(val) if val is not None else 0
    except (TypeError, ValueError):
        return 0


@st.cache_data(ttl=300, show_spinner=False)
def fetch_scoreboard(espn_league_id: str) -> List[Dict]:
    """Return upcoming fixtures within the scan window for a league."""
    mapping = LEAGUE_MAP.get(espn_league_id)
    if not mapping:
        return []
    api_league_id, season = mapping

    data = _get("fixtures", {
        "league": api_league_id,
        "season": season,
        "next": 40,
        "status": "NS",
    })
    if not data or not data.get("response"):
        return []

    events: List[Dict] = []
    for fix in data["response"]:
        date_str = fix.get("fixture", {}).get("date", "")
        if not _in_window(date_str):
            continue
        home = fix["teams"]["home"]
        away = fix["teams"]["away"]
        events.append({
            "event_id": str(fix["fixture"]["id"]),
            "date": date_str,
            "home_id": str(home["id"]),
            "away_id": str(away["id"]),
            "home_name": home["name"],
            "away_name": away["name"],
            "completed": False,
        })
    return events


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_team_schedule(espn_league_id: str, team_id: str) -> List[Dict]:
    """Return the last 25 completed fixtures for a team in a league/season."""
    mapping = LEAGUE_MAP.get(espn_league_id)
    if not mapping:
        return []
    api_league_id, season = mapping

    data = _get("fixtures", {
        "league": api_league_id,
        "season": season,
        "team": team_id,
        "last": 25,
        "status": "FT",
    })
    if not data or not data.get("response"):
        return []

    matches: List[Dict] = []
    for fix in data["response"]:
        ht = fix["teams"]["home"]
        at = fix["teams"]["away"]
        goals = fix.get("goals") or {}
        h_sc = _safe_int(goals.get("home"))
        a_sc = _safe_int(goals.get("away"))

        matches.append({
            "fixture_id": fix["fixture"]["id"],
            "date": fix["fixture"]["date"],
            "home_id": str(ht["id"]),
            "away_id": str(at["id"]),
            "home_name": ht["name"],
            "away_name": at["name"],
            "home_score": h_sc,
            "away_score": a_sc,
            "total_goals": h_sc + a_sc,
            "completed": True,
        })
    return matches


@st.cache_data(ttl=300, show_spinner=False)
def fetch_completed_result(
    espn_league_id: str,
    home_name: str,
    away_name: str,
    kickoff_utc: str,
) -> Optional[int]:
    """
    Look up the final total goals for a completed match.
    Returns total_goals (int) or None if not found/not finished.
    """
    mapping = LEAGUE_MAP.get(espn_league_id)
    if not mapping:
        return None
    api_league_id, season = mapping

    try:
        ko = datetime.fromisoformat(kickoff_utc.replace("Z", "+00:00"))
        date_str = ko.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return None

    data = _get("fixtures", {
        "league": api_league_id,
        "season": season,
        "date": date_str,
        "status": "FT",
    })
    if not data or not data.get("response"):
        return None

    h_low = home_name.lower()
    a_low = away_name.lower()

    for fix in data["response"]:
        fn = fix["teams"]["home"]["name"].lower()
        an = fix["teams"]["away"]["name"].lower()
        if (h_low in fn or fn in h_low) and (a_low in an or an in a_low):
            goals = fix.get("goals") or {}
            return _safe_int(goals.get("home")) + _safe_int(goals.get("away"))

    return None
