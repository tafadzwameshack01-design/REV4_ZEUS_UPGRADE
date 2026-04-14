"""
Football-Data.org API — 4th data source.
Provides accurate HT scores for European competitions.
Requires FOOTBALL_DATA_API_KEY environment variable (free tier: 10 req/min).
Without a key this module returns empty lists silently.
"""
import os
import requests
from typing import List, Dict, Optional
from core.db import cache_get, cache_set
from core.constants import FTDATA_BASE

# Map ESPN league IDs to football-data.org competition IDs
_LEAGUE_MAP = {
    "eng.1": "PL",    "esp.1": "PD",    "ger.1": "BL1",
    "ita.1": "SA",    "fra.1": "FL1",   "ned.1": "DED",
    "por.1": "PPL",   "bel.1": "BSA",   "eng.2": "ELC",
    "sco.1": "PL",
    "uefa.champions": "CL",
    "uefa.europa":    "EL",
}


def _get_api_key() -> str:
    return os.getenv("FOOTBALL_DATA_API_KEY", "")


def _headers() -> dict:
    key = _get_api_key()
    h = {
        "Accept": "application/json",
        "User-Agent": "ZEUS-HT-Intelligence/6.1",
    }
    if key:
        h["X-Auth-Token"] = key
    return h


def _safe_get(url: str, timeout: int = 10) -> Optional[dict]:
    if not _get_api_key():
        return None
    try:
        r = requests.get(url, headers=_headers(), timeout=timeout)
        if r.status_code == 200:
            return r.json()
        if r.status_code == 429:
            import time
            time.sleep(65)
    except Exception:
        pass
    return None


def _parse_match(m: dict) -> Optional[Dict]:
    try:
        score  = m.get("score", {})
        ht     = score.get("halfTime", {}) or {}
        ft     = score.get("fullTime", {}) or {}
        ht_h   = ht.get("home")
        ht_a   = ht.get("away")
        ft_h   = ft.get("home")
        ft_a   = ft.get("away")

        ht_home  = int(ht_h) if ht_h is not None else -1
        ht_away  = int(ht_a) if ht_a is not None else -1
        ht_total = (ht_home + ht_away) if ht_home >= 0 and ht_away >= 0 else -1

        return {
            "date":       m.get("utcDate", ""),
            "home_name":  m.get("homeTeam", {}).get("name", ""),
            "away_name":  m.get("awayTeam", {}).get("name", ""),
            "home_id":    str(m.get("homeTeam", {}).get("id", "")),
            "away_id":    str(m.get("awayTeam", {}).get("id", "")),
            "home_score": int(ft_h) if ft_h is not None else 0,
            "away_score": int(ft_a) if ft_a is not None else 0,
            "ht_home":    ht_home,
            "ht_away":    ht_away,
            "ht_total":   ht_total,
            "source":     "footballdata",
        }
    except Exception:
        return None


def fetch_live_matches() -> List[Dict]:
    if not _get_api_key():
        return []
    ck = "ftdata_live"
    cached = cache_get(ck)
    if cached is not None:
        return cached
    data = _safe_get(f"{FTDATA_BASE}/matches?status=LIVE")
    if not data:
        return []
    result = [g for g in (_parse_match(m) for m in data.get("matches", [])) if g]
    cache_set(ck, result, ttl=60)
    return result


def fetch_team_matches(team_id: str, limit: int = 15) -> List[Dict]:
    """Fetch by numeric football-data.org team ID."""
    if not _get_api_key() or not team_id:
        return []
    ck = f"ftdata_team_{team_id}"
    cached = cache_get(ck)
    if cached is not None:
        return cached
    url  = f"{FTDATA_BASE}/teams/{team_id}/matches?status=FINISHED&limit={limit}"
    data = _safe_get(url)
    if not data:
        return []
    result = [g for g in (_parse_match(m) for m in data.get("matches", [])) if g]
    if result:
        cache_set(ck, result, ttl=1800)
    return result


def fetch_team_matches_by_name(team_name: str) -> List[Dict]:
    """Search for a team by name and fetch their recent matches."""
    if not _get_api_key() or not team_name:
        return []
    ck = f"ftdata_name_{team_name.lower().replace(' ','_')}"
    cached = cache_get(ck)
    if cached is not None:
        return cached

    search_data = _safe_get(f"{FTDATA_BASE}/teams?name={requests.utils.quote(team_name)}")
    if not search_data:
        return []
    teams = search_data.get("teams", [])
    if not teams:
        return []
    team_id = str(teams[0].get("id", ""))
    result  = fetch_team_matches(team_id, limit=20)
    if result:
        cache_set(ck, result, ttl=3600)
    return result


def fetch_competition_matches(league_id: str, matchday: int = None) -> List[Dict]:
    """Fetch matches for a mapped competition."""
    comp_id = _LEAGUE_MAP.get(league_id)
    if not comp_id or not _get_api_key():
        return []
    ck = f"ftdata_comp_{comp_id}_{matchday or 'latest'}"
    cached = cache_get(ck)
    if cached is not None:
        return cached
    url  = f"{FTDATA_BASE}/competitions/{comp_id}/matches?status=FINISHED"
    if matchday:
        url += f"&matchday={matchday}"
    data = _safe_get(url)
    if not data:
        return []
    result = [g for g in (_parse_match(m) for m in data.get("matches", [])) if g]
    if result:
        cache_set(ck, result, ttl=1800)
    return result
