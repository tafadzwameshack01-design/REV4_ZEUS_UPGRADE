import sqlite3
import threading
import os
import json
import time

_BASE_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH    = os.path.join(_BASE_DIR, "data", "zeus_v6.db")

# Fallback to /tmp if data/ dir is not writable (Streamlit Cloud)
try:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    _test = os.path.join(os.path.dirname(DB_PATH), ".write_test")
    with open(_test, "w") as f:
        f.write("1")
    os.remove(_test)
except Exception:
    DB_PATH = "/tmp/zeus_v6.db"

_local      = threading.local()
_write_lock = threading.Lock()

SCHEMA_SQL = """
    CREATE TABLE IF NOT EXISTS picks_log (
        id           TEXT PRIMARY KEY,
        event_id     TEXT DEFAULT '',
        match        TEXT,
        league       TEXT,
        league_id    TEXT,
        bet          TEXT,
        bet_type     TEXT,
        xg_total     REAL,
        confidence   REAL,
        kickoff      TEXT,
        result       TEXT DEFAULT 'pending',
        ht_home      INTEGER DEFAULT -1,
        ht_away      INTEGER DEFAULT -1,
        ht_total     INTEGER DEFAULT -1,
        factors_json TEXT DEFAULT '{}',
        logged_at    TEXT
    );
    CREATE TABLE IF NOT EXISTS live_picks_log (
        id           TEXT PRIMARY KEY,
        event_id     TEXT DEFAULT '',
        match        TEXT,
        league       TEXT,
        league_id    TEXT,
        bet          TEXT,
        bet_type     TEXT,
        xg_total     REAL,
        confidence   REAL,
        kickoff      TEXT,
        minute_made  INTEGER DEFAULT 0,
        result       TEXT DEFAULT 'pending',
        ht_home      INTEGER DEFAULT -1,
        ht_away      INTEGER DEFAULT -1,
        ht_total     INTEGER DEFAULT -1,
        factors_json TEXT DEFAULT '{}',
        logged_at    TEXT
    );
    CREATE TABLE IF NOT EXISTS live_monitor (
        event_id   TEXT PRIMARY KEY,
        match      TEXT,
        league     TEXT,
        league_id  TEXT,
        status     TEXT DEFAULT 'live',
        minute     INTEGER DEFAULT 0,
        home_score INTEGER DEFAULT 0,
        away_score INTEGER DEFAULT 0,
        updated_at TEXT
    );
    CREATE TABLE IF NOT EXISTS brain_state (
        bet_type       TEXT PRIMARY KEY,
        gate_elevation REAL DEFAULT 0.0,
        streak_w       INTEGER DEFAULT 0,
        streak_l       INTEGER DEFAULT 0,
        updated_at     TEXT
    );
    CREATE TABLE IF NOT EXISTS cache_store (
        cache_key TEXT PRIMARY KEY,
        data_json TEXT,
        expires_at REAL
    );
    CREATE INDEX IF NOT EXISTS idx_cache_expires ON cache_store(expires_at);
    CREATE TABLE IF NOT EXISTS weights_history (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        bet_type   TEXT,
        weights_json TEXT,
        accuracy   REAL,
        logged_at  TEXT
    );
    CREATE TABLE IF NOT EXISTS scan_log (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        scan_type   TEXT,
        leagues_hit INTEGER DEFAULT 0,
        games_eval  INTEGER DEFAULT 0,
        picks_made  INTEGER DEFAULT 0,
        data_points INTEGER DEFAULT 0,
        logged_at   TEXT
    );
    CREATE TABLE IF NOT EXISTS league_accuracy (
        league_id  TEXT,
        bet_type   TEXT,
        wins       INTEGER DEFAULT 0,
        losses     INTEGER DEFAULT 0,
        updated_at TEXT,
        PRIMARY KEY (league_id, bet_type)
    );
    CREATE TABLE IF NOT EXISTS prediction_pauses (
        bet_type    TEXT PRIMARY KEY,
        pause_until REAL DEFAULT 0.0,
        reason      TEXT DEFAULT ''
    );
"""


def get_db() -> sqlite3.Connection:
    """Thread-local SQLite connection. Schema ensured on first use per thread."""
    if not hasattr(_local, "conn") or _local.conn is None:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=20)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=10000")
        conn.execute("PRAGMA cache_size=-32000")
        conn.execute("PRAGMA temp_store=MEMORY")
        conn.executescript(SCHEMA_SQL)
        conn.commit()
        _local.conn = conn
    return _local.conn


def db_execute(sql: str, params=(), commit: bool = True):
    with _write_lock:
        conn = get_db()
        try:
            cur = conn.execute(sql, params)
            if commit:
                conn.commit()
            return cur
        except Exception:
            return None


def db_fetchall(sql: str, params=()):
    conn = get_db()
    try:
        return conn.execute(sql, params).fetchall()
    except Exception:
        return []


def db_fetchone(sql: str, params=()):
    conn = get_db()
    try:
        return conn.execute(sql, params).fetchone()
    except Exception:
        return None


def init_db_once():
    """Explicit init from main thread — ensures schema + prunes stale entries."""
    conn = get_db()
    with _write_lock:
        try:
            # Prune expired cache (older than 2h)
            conn.execute("DELETE FROM cache_store WHERE expires_at < ?", (time.time() - 7200,))
            # Prune scan log older than 7 days
            conn.execute("DELETE FROM scan_log WHERE logged_at < datetime('now', '-7 days')")
            # Prune weights history older than 30 days
            conn.execute("DELETE FROM weights_history WHERE logged_at < datetime('now', '-30 days')")
            conn.commit()
        except Exception:
            pass


def cache_get(key: str, default=None):
    row = db_fetchone(
        "SELECT data_json FROM cache_store WHERE cache_key=? AND expires_at > ?",
        (key, time.time()),
    )
    if row:
        try:
            return json.loads(row[0])
        except Exception:
            pass
    return default


def cache_set(key: str, data, ttl: int = 300):
    try:
        js = json.dumps(data, default=str)
        with _write_lock:
            conn = get_db()
            conn.execute(
                "INSERT OR REPLACE INTO cache_store (cache_key, data_json, expires_at) VALUES (?,?,?)",
                (key, js, time.time() + ttl),
            )
            conn.commit()
    except Exception:
        pass


def get_brain_state(bet_type: str):
    row = db_fetchone(
        "SELECT gate_elevation, streak_w, streak_l FROM brain_state WHERE bet_type=?",
        (bet_type,),
    )
    if row:
        return float(row[0]), int(row[1]), int(row[2])
    return 0.0, 0, 0


def set_brain_state(bet_type: str, gate_elev: float, streak_w: int, streak_l: int):
    from core.time_utils import utc_iso
    db_execute(
        "INSERT OR REPLACE INTO brain_state "
        "(bet_type, gate_elevation, streak_w, streak_l, updated_at) VALUES (?,?,?,?,?)",
        (bet_type, gate_elev, streak_w, streak_l, utc_iso()),
    )
