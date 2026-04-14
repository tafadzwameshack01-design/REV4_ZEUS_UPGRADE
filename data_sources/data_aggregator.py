"""
Data Aggregator — multi-source team schedule fetcher.

SOURCE PRIORITY:
  1. ESPN (primary — daemon pre-caches, instant reads)
  2. SofaScore (secondary — best HT data, rate-limited 1.1s/req)
  3. TheSportsDB (tertiary — lightweight fallback)
  4. Football-Data.org (quaternary — HT data where API key available)

SofaScore is only called when ESPN has < 5 HT-scored games.
Football-Data.org requires FOOTBALL_DATA_API_KEY env var.
"""
from typing import List, Dict


def get_team_schedule_all_sources(
    league_id: str, team_id: str, team_name: str
) -> List[Dict]:
    from data_sources.espn_api import fetch_team_schedule_espn_direct

    all_games: List[Dict] = []
    seen_keys: set        = set()

    def _add(games: List[Dict]):
        for g in games:
            k = f"{(g.get('date',''))[:10]}_{g.get('home_name','').lower()}_{g.get('away_name','').lower()}"
            if k not in seen_keys:
                seen_keys.add(k)
                all_games.append(g)
            else:
                # Merge HT data into existing entry if it's missing
                for ex in all_games:
                    ek = f"{(ex.get('date',''))[:10]}_{ex.get('home_name','').lower()}_{ex.get('away_name','').lower()}"
                    if ek == k and ex.get("ht_total", -1) < 0 and g.get("ht_total", -1) >= 0:
                        ex["ht_home"]  = g.get("ht_home", -1)
                        ex["ht_away"]  = g.get("ht_away", -1)
                        ex["ht_total"] = g.get("ht_total", -1)
                        break

    # ── Source 1: ESPN ─────────────────────────────────────────────────────────
    try:
        _add(fetch_team_schedule_espn_direct(league_id, team_id))
    except Exception:
        pass

    # ── Source 2: SofaScore (when HT data is thin) ────────────────────────────
    ht_count = sum(1 for g in all_games if g.get("ht_total", -1) >= 0)
    if ht_count < 6 or len(all_games) < 6:
        try:
            from data_sources.sofascore_api import fetch_team_events_sofa
            _add(fetch_team_events_sofa(team_name))
        except Exception:
            pass

    # ── Source 3: TheSportsDB (thin schedule backup) ──────────────────────────
    if len(all_games) < 8:
        try:
            from data_sources.thesportsdb_api import fetch_team_events_tsdb
            _add(fetch_team_events_tsdb(team_name))
        except Exception:
            pass

    # ── Source 4: Football-Data.org (HT data enrichment) ─────────────────────
    ht_count = sum(1 for g in all_games if g.get("ht_total", -1) >= 0)
    if ht_count < 5:
        try:
            from data_sources.footballdata_api import fetch_team_matches_by_name
            _add(fetch_team_matches_by_name(team_name))
        except Exception:
            pass

    all_games.sort(key=lambda g: g.get("date", ""))
    return all_games[-40:]   # keep last 40 matches
