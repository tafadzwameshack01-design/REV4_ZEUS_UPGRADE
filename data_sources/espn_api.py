import requests
import random
import time
import datetime
from typing import Dict, List, Optional
from core.constants import ESPN_BASE, USER_AGENTS
from core.db import cache_get, cache_set
from core.time_utils import today_str_utc, now_utc

def _headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Referer": "https://www.espn.com/",
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "DNT": "1",
    }

def _safe_get(url, timeout=12):
    for attempt in range(3):
        try:
            resp = requests.get(url, headers=_headers(), timeout=timeout)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code == 429:
                time.sleep(15 + random.uniform(0, 5))
                continue
            if resp.status_code == 404:
                return None
        except Exception:
            pass
        if attempt < 2:
            time.sleep(random.uniform(1.0, 2.5))
    return None

def fetch_scoreboard(league_id: str, date_str: str = None) -> Optional[Dict]:
    if date_str is None:
        date_str = today_str_utc()
    cache_key = f"espn_sb_{league_id}_{date_str}"
    cached = cache_get(cache_key)
    if cached:
        return cached
    url = f"{ESPN_BASE}/{league_id}/scoreboard?dates={date_str}"
    data = _safe_get(url)
    if data:
        cache_set(cache_key, data, ttl=90)
    return data

def fetch_scoreboard_live(league_id: str, date_str: str = None) -> Optional[Dict]:
    """Fetch with very short TTL for live game status."""
    if date_str is None:
        date_str = today_str_utc()
    cache_key = f"espn_sb_live_{league_id}_{date_str}"
    cached = cache_get(cache_key)
    if cached:
        return cached
    url = f"{ESPN_BASE}/{league_id}/scoreboard?dates={date_str}"
    data = _safe_get(url)
    if data:
        cache_set(cache_key, data, ttl=25)
    return data

def fetch_team_schedule(league_id: str, team_id: str) -> Optional[Dict]:
    """Fetch raw team schedule JSON (cached 30 min)."""
    if not team_id or team_id == "0":
        return None
    cache_key = f"espn_ts_{league_id}_{team_id}"
    cached = cache_get(cache_key)
    if cached:
        return cached
    url = f"{ESPN_BASE}/{league_id}/teams/{team_id}/schedule"
    data = _safe_get(url)
    if data:
        cache_set(cache_key, data, ttl=1800)
    return data

def fetch_team_schedule_espn_direct(league_id: str, team_id: str) -> List[Dict]:
    """Parse team schedule into normalized game list."""
    raw = fetch_team_schedule(league_id, team_id)
    if not raw:
        return []
    games = []
    for ev in raw.get("events", []):
        comps = ev.get("competitions", [])
        if not comps:
            continue
        comp = comps[0]
        if not comp.get("status", {}).get("type", {}).get("completed", False):
            continue
        competitors = comp.get("competitors", [])
        if len(competitors) < 2:
            continue
        home_c = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0])
        away_c = next((c for c in competitors if c.get("homeAway") == "away"), competitors[1])
        try:
            home_score = int(float(str(home_c.get("score", "0") or "0")))
            away_score = int(float(str(away_c.get("score", "0") or "0")))
        except Exception:
            home_score = away_score = 0

        ht_home = ht_away = -1
        for c in competitors:
            for lx in c.get("linescores", []):
                if str(lx.get("period", "")) == "1":
                    try:
                        val = int(float(str(lx.get("value", lx.get("displayValue", -1)))))
                        if val >= 0:
                            if c.get("homeAway") == "home":
                                ht_home = val
                            else:
                                ht_away = val
                    except Exception:
                        pass

        ht_total = (ht_home + ht_away) if ht_home >= 0 and ht_away >= 0 else -1

        games.append({
            "date": ev.get("date", ""),
            "home_name": home_c.get("team", {}).get("displayName", ""),
            "away_name": away_c.get("team", {}).get("displayName", ""),
            "home_id": str(home_c.get("team", {}).get("id", "")),
            "away_id": str(away_c.get("team", {}).get("id", "")),
            "home_score": home_score,
            "away_score": away_score,
            "ht_home": ht_home,
            "ht_away": ht_away,
            "ht_total": ht_total,
            "source": "espn",
        })
    return games

def extract_upcoming_games(league_id: str, date_str: str = None) -> List[Dict]:
    """Get non-live, non-completed upcoming games from scoreboard cache."""
    data = fetch_scoreboard(league_id, date_str)
    if not data:
        return []
    games = []
    for ev in (data or {}).get("events", []):
        comps = ev.get("competitions", [])
        if not comps:
            continue
        comp = comps[0]
        status = comp.get("status", {}).get("type", {})
        if status.get("completed", False):
            continue
        st_name = status.get("name", "").upper()
        st_desc = status.get("description", "").upper()
        combined = st_name + " " + st_desc
        # Skip live games here — handled by live_scanner
        if any(k in combined for k in ["IN_PROGRESS", "INPROG", "LIVE", "ONGOING"]):
            continue
        competitors = comp.get("competitors", [])
        if len(competitors) < 2:
            continue
        home_c = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0])
        away_c = next((c for c in competitors if c.get("homeAway") == "away"), competitors[1])
        games.append({
            "event_id": ev.get("id", ""),
            "date": ev.get("date", ""),
            "home_id": str(home_c.get("team", {}).get("id", "")),
            "home_name": home_c.get("team", {}).get("displayName", ""),
            "away_id": str(away_c.get("team", {}).get("id", "")),
            "away_name": away_c.get("team", {}).get("displayName", ""),
            "league_id": league_id,
        })
    return games

def extract_live_games(league_id: str, date_str: str = None) -> List[Dict]:
    """Get currently live games from scoreboard. Uses short-TTL cache."""
    if date_str is None:
        date_str = today_str_utc()
    data = fetch_scoreboard_live(league_id, date_str)
    if not data:
        return []
    live = []
    for ev in (data or {}).get("events", []):
        comps = ev.get("competitions", [])
        if not comps:
            continue
        comp = comps[0]
        status = comp.get("status", {})
        st_type = status.get("type", {})
        if st_type.get("completed", False):
            continue
        combined = (st_type.get("name","") + " " + st_type.get("description","")).upper()
        if not any(k in combined for k in ["IN_PROGRESS","INPROG","PROGRESS","LIVE","ONGOING"]):
            continue
        period = status.get("period", 0)
        if period != 1:
            continue
        try:
            minute = int(str(status.get("displayClock","0")).replace("'","").strip().split(":")[0])
        except Exception:
            minute = 0
        if minute < 5 or minute > 42:
            continue
        competitors = comp.get("competitors", [])
        if len(competitors) < 2:
            continue
        home_c = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0])
        away_c = next((c for c in competitors if c.get("homeAway") == "away"), competitors[1])
        try:
            hs = int(float(str(home_c.get("score","0") or "0")))
            as_ = int(float(str(away_c.get("score","0") or "0")))
        except Exception:
            hs = as_ = 0
        # Allow scores up to 1 total — scanner handles bet-type filtering
        if hs + as_ > 2:
            continue
        live.append({
            "event_id":   ev.get("id",""),
            "date":       ev.get("date",""),
            "home_id":    str(home_c.get("team",{}).get("id","")),
            "home_name":  home_c.get("team",{}).get("displayName",""),
            "away_id":    str(away_c.get("team",{}).get("id","")),
            "away_name":  away_c.get("team",{}).get("displayName",""),
            "league_id":  league_id,
            "minute":     minute,
            "home_score": hs,
            "away_score": as_,
            "is_live":    True,
        })
    return live
