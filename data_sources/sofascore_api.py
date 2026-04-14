import requests
import time
from typing import List, Dict, Optional
from core.constants import SOFA_BASE
from core.db import cache_get, cache_set

_last_request = 0.0
_RATE_LIMIT = 1.1

def _sofa_headers():
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.sofascore.com/",
        "Accept": "application/json",
        "x-requested-with": "XMLHttpRequest",
    }

def _rate_limited_get(url, timeout=10):
    global _last_request
    elapsed = time.time() - _last_request
    if elapsed < _RATE_LIMIT:
        time.sleep(_RATE_LIMIT - elapsed)
    _last_request = time.time()
    try:
        resp = requests.get(url, headers=_sofa_headers(), timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None

def fetch_live_events() -> List[Dict]:
    cache_key = "sofa_live_events"
    cached = cache_get(cache_key)
    if cached:
        return cached
    url = f"{SOFA_BASE}/sport/football/events/live"
    data = _rate_limited_get(url)
    if not data:
        return []
    events = data.get("events", [])
    cache_set(cache_key, events, ttl=45)
    return events

def search_team(team_name: str) -> Optional[Dict]:
    cache_key = f"sofa_search_{team_name.lower().replace(' ','_')}"
    cached = cache_get(cache_key)
    if cached:
        return cached
    url = f"{SOFA_BASE}/search/team-player-tournament?q={requests.utils.quote(team_name)}"
    data = _rate_limited_get(url)
    if not data:
        return None
    teams = data.get("teams", [])
    if teams:
        result = teams[0]
        cache_set(cache_key, result, ttl=3600)
        return result
    return None

def fetch_team_events_sofa(team_name: str) -> List[Dict]:
    cache_key = f"sofa_team_events_{team_name.lower().replace(' ','_')}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    team = search_team(team_name)
    if not team:
        return []
    team_id = team.get("id")
    if not team_id:
        return []

    url = f"{SOFA_BASE}/team/{team_id}/events/last/0"
    data = _rate_limited_get(url)
    if not data:
        return []

    games = []
    for ev in data.get("events", []):
        ht = ev.get("homeTeam", {})
        at = ev.get("awayTeam", {})
        hs = ev.get("homeScore", {})
        aws = ev.get("awayScore", {})

        home_score = hs.get("current", 0)
        away_score = aws.get("current", 0)
        ht_home = hs.get("period1", -1)
        ht_away = aws.get("period1", -1)

        try:
            home_score = int(home_score) if home_score is not None else 0
            away_score = int(away_score) if away_score is not None else 0
            ht_home = int(ht_home) if ht_home is not None and ht_home >= 0 else -1
            ht_away = int(ht_away) if ht_away is not None and ht_away >= 0 else -1
        except Exception:
            continue

        ht_total = (ht_home + ht_away) if ht_home >= 0 and ht_away >= 0 else -1

        start_ts = ev.get("startTimestamp", 0)
        import datetime
        try:
            dt = datetime.datetime.fromtimestamp(start_ts, tz=datetime.timezone.utc)
            date_str = dt.isoformat()
        except Exception:
            date_str = ""

        games.append({
            "date": date_str,
            "home_name": ht.get("name", ""),
            "away_name": at.get("name", ""),
            "home_id": str(ht.get("id", "")),
            "away_id": str(at.get("id", "")),
            "home_score": home_score,
            "away_score": away_score,
            "ht_home": ht_home,
            "ht_away": ht_away,
            "ht_total": ht_total,
            "source": "sofascore",
        })

    if games:
        cache_set(cache_key, games, ttl=1800)
    return games
