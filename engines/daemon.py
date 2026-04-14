"""
Background daemon — pre-fetches ESPN scoreboards and team schedules
into SQLite cache so the scanner hot-paths are instant reads.

Architecture:
  Phase 1: Priority leagues (~19 leagues) — warms up in ~30s
  Phase 2: All 112 leagues — continuous refresh cycle
  Phase 3: After each full sweep, short pause then restart
"""
import threading
import time
import datetime
import streamlit as st


@st.cache_resource
def _get_process_state() -> dict:
    """Process-level shared state — survives reruns, shared across sessions."""
    return {
        "warmup_complete":    False,
        "daemon_running":     False,
        "leagues_prefetched": 0,
        "leagues_total":      0,
        "games_cached":       0,
        "teams_cached":       0,
        "last_scan":          "",
        "errors":             [],
        "scan_count":         0,
        "last_sweep_ts":      0.0,
        "current_league":     "",
        "phase":              "initializing",
    }


def get_shared_state() -> dict:
    return _get_process_state()


def _prefetch_league(league_id: str, lname: str, state: dict):
    """Fetch scoreboard + team schedules for one league. Updates shared state."""
    from data_sources.espn_api import fetch_scoreboard, fetch_team_schedule

    try:
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        dates   = [
            (now_utc + datetime.timedelta(days=d)).strftime("%Y%m%d")
            for d in [-1, 0, 1, 2]   # yesterday, today, tomorrow, day after
        ]

        new_teams = 0
        new_games = 0

        for date_str in dates:
            data = fetch_scoreboard(league_id, date_str)
            if not data or not data.get("events"):
                time.sleep(0.05)
                continue

            events = data["events"]
            new_games += len(events)

            for ev in events:
                comps = ev.get("competitions", [])
                if not comps:
                    continue
                for c in comps[0].get("competitors", []):
                    tid = str(c.get("team", {}).get("id", ""))
                    if tid and tid != "0":
                        fetch_team_schedule(league_id, tid)
                        new_teams += 1
                        time.sleep(0.08)   # gentle rate-limiting per team

            time.sleep(0.15)

        state["games_cached"]  = state.get("games_cached", 0) + new_games
        state["teams_cached"]  = state.get("teams_cached", 0) + new_teams
        state["current_league"] = lname

    except Exception as e:
        errs = state.get("errors") or []
        state["errors"] = errs[-14:] + [f"{lname}: {str(e)[:80]}"]


def _prefetch_loop(state: dict):
    from core.constants import LEAGUES, PRIORITY_LEAGUES

    state["daemon_running"]  = True
    state["leagues_total"]   = len(LEAGUES)
    priority_ids             = set(PRIORITY_LEAGUES)
    phase1_done              = False

    while True:
        try:
            # ── Phase 1: priority leagues ─────────────────────────────────────
            if not phase1_done:
                state["phase"]           = "warming_priority"
                priority                 = [l for l in LEAGUES if l[0] in priority_ids]
                state["leagues_prefetched"] = 0

                for lid, lname, _ in priority:
                    _prefetch_league(lid, lname, state)
                    state["leagues_prefetched"] = state.get("leagues_prefetched", 0) + 1
                    time.sleep(0.4)

                state["warmup_complete"] = True
                state["phase"]           = "full_sweep"
                phase1_done              = True
                state["scan_count"]      = state.get("scan_count", 0) + 1
                state["last_sweep_ts"]   = time.time()

            # ── Phase 2: all leagues ──────────────────────────────────────────
            state["phase"]              = "full_sweep"
            state["leagues_prefetched"] = 0

            for lid, lname, _ in LEAGUES:
                _prefetch_league(lid, lname, state)
                state["leagues_prefetched"] = state.get("leagues_prefetched", 0) + 1
                time.sleep(0.8)

            state["last_sweep_ts"] = time.time()
            state["scan_count"]    = state.get("scan_count", 0) + 1
            state["phase"]         = "idle"

            time.sleep(25.0)   # brief pause before re-sweeping

        except Exception as e:
            errs = state.get("errors") or []
            state["errors"] = errs[-14:] + [f"daemon: {str(e)[:120]}"]
            time.sleep(5.0)


@st.cache_resource
def _daemon_holder() -> dict:
    return {"thread": None}


def start_background_daemon(state: dict):
    holder = _daemon_holder()
    if holder["thread"] is not None and holder["thread"].is_alive():
        return
    t = threading.Thread(target=_prefetch_loop, args=(state,), daemon=True)
    t.start()
    holder["thread"] = t
