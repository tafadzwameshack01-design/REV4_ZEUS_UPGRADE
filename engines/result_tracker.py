"""
Result Tracker — resolves pending picks after games complete.

BUG FIX: Original query used `datetime(kickoff) < datetime('now', '+2 hours')`
which incorrectly included FUTURE games. Corrected to check for games that
started 40–180 minutes ago (i.e., HT has already occurred).
"""
import json
from core.constants import HT_BET_TYPES
from core.db import db_execute, db_fetchall
from core.time_utils import utc_iso
from data_sources.espn_api import fetch_scoreboard_live


def check_and_update_results():
    try:
        _check_table("picks_log")
        _check_table("live_picks_log")
    except Exception:
        pass


def _check_table(table_name: str):
    from core.learning_engine import update_weights

    try:
        # Only check games that kicked off between 40 min and 3 hours ago
        # (HT results are available after ~47 min; 3h covers any delays/extra time)
        rows = db_fetchall(
            f"SELECT id, event_id, league_id, kickoff, bet_type, confidence, factors_json "
            f"FROM {table_name} WHERE result='pending' "
            f"AND datetime(kickoff) < datetime('now', '-40 minutes') "
            f"AND datetime(kickoff) > datetime('now', '-4 hours')",
        )

        for row in rows:
            pid, event_id, league_id, kickoff, bet_type, confidence, factors_json = row
            if not event_id or not league_id:
                # No event_id — can't look it up; mark as unresolvable after 3h
                db_execute(
                    f"UPDATE {table_name} SET result='no_data' WHERE id=?", (pid,)
                )
                continue

            date_str = (kickoff or "")[:10].replace("-", "")
            if not date_str or len(date_str) != 8:
                continue

            data = fetch_scoreboard_live(league_id, date_str)
            if not data:
                continue

            for ev in data.get("events", []):
                if str(ev.get("id", "")) != str(event_id):
                    continue

                comp = ev.get("competitions", [{}])[0]
                if not comp.get("status", {}).get("type", {}).get("completed", False):
                    continue

                competitors = comp.get("competitors", [])
                ht_home = ht_away = -1

                for c in competitors:
                    ls = c.get("linescores", [])
                    p1 = next((x for x in ls if str(x.get("period", "")) == "1"), None)
                    if p1:
                        try:
                            score = int(float(str(
                                p1.get("value", p1.get("displayValue", -1))
                            )))
                            if score >= 0:
                                if c.get("homeAway") == "home":
                                    ht_home = score
                                elif c.get("homeAway") == "away":
                                    ht_away = score
                        except Exception:
                            pass

                if ht_home < 0 or ht_away < 0:
                    # Completed but no HT data — try full-time as fallback signal
                    continue

                ht_total = ht_home + ht_away
                if bet_type not in HT_BET_TYPES:
                    continue

                line = HT_BET_TYPES[bet_type]["line"]
                won  = ht_total > line

                try:
                    factors = json.loads(factors_json) if factors_json else {}
                except Exception:
                    factors = {}

                update_weights(
                    bet_type, factors, won,
                    float(confidence or 0), ht_total, league_id,
                )

                result_str = "WIN" if won else "LOSS"
                db_execute(
                    f"UPDATE {table_name} SET result=?, ht_home=?, ht_away=?, ht_total=? WHERE id=?",
                    (result_str, ht_home, ht_away, ht_total, pid),
                )
                break  # found the matching event

    except Exception:
        pass
