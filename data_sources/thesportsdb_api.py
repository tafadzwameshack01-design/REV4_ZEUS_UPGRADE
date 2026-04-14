import requests
from typing import List, Dict, Optional
from core.constants import TSDB_BASE
from core.db import cache_get, cache_set

def _safe_get(url, timeout=10):
    try:
        resp = requests.get(url, timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None

def search_team_tsdb(team_name: str) -> Optional[Dict]:
    cache_key = f"tsdb_search_{team_name.lower().replace(' ','_')}"
    cached = cache_get(cache_key)
    if cached:
        return cached
    url = f"{TSDB_BASE}/searchteams.php?t={requests.utils.quote(team_name)}"
    data = _safe_get(url)
    if not data:
        return None
    teams = data.get("teams")
    if teams and len(teams) > 0:
        result = teams[0]
        cache_set(cache_key, result, ttl=3600)
        return result
    return None

def fetch_team_events_tsdb(team_name: str) -> List[Dict]:
    cache_key = f"tsdb_team_events_{team_name.lower().replace(' ','_')}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    team = search_team_tsdb(team_name)
    if not team:
        return []
    team_id = team.get("idTeam")
    if not team_id:
        return []

    url = f"{TSDB_BASE}/eventslast.php?id={team_id}"
    data = _safe_get(url)
    if not data:
        return []

    results = data.get("results") or []
    games = []
    for ev in results:
        try:
            home_score = int(ev.get("intHomeScore", 0) or 0)
            away_score = int(ev.get("intAwayScore", 0) or 0)
        except Exception:
            continue

        games.append({
            "date": ev.get("dateEvent", "") + "T00:00:00+00:00",
            "home_name": ev.get("strHomeTeam", ""),
            "away_name": ev.get("strAwayTeam", ""),
            "home_id": str(ev.get("idHomeTeam", "")),
            "away_id": str(ev.get("idAwayTeam", "")),
            "home_score": home_score,
            "away_score": away_score,
            "ht_home": -1,
            "ht_away": -1,
            "ht_total": -1,
            "source": "thesportsdb",
        })

    if games:
        cache_set(cache_key, games, ttl=1800)
    return games

def fetch_live_scores_tsdb() -> List[Dict]:
    cache_key = "tsdb_live_scores"
    cached = cache_get(cache_key)
    if cached:
        return cached
    url = f"{TSDB_BASE}/livescore.php?s=Soccer"
    data = _safe_get(url)
    if not data:
        return []
    events = data.get("events") or []
    cache_set(cache_key, events, ttl=60)
    return events
