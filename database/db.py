"""
ZEUS v4 — SQLite database layer with context-managed connections.
"""
import sqlite3
import json
import logging
import time
from contextlib import contextmanager
from typing import Any, Optional, Dict, List
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_DB_PATH = "zeus_v4.db"


@contextmanager
def _connection():
    """Context manager ensuring connections are always properly closed."""
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def get_connection() -> sqlite3.Connection:
    """Return a raw connection (legacy compatibility)."""
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the database schema and seed default state."""
    with _connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS api_cache (
                cache_key TEXT PRIMARY KEY,
                data      TEXT NOT NULL,
                ts        REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS matches (
                id          TEXT PRIMARY KEY,
                home_team   TEXT NOT NULL,
                away_team   TEXT NOT NULL,
                league_id   TEXT NOT NULL,
                league_name TEXT NOT NULL,
                kickoff_utc TEXT NOT NULL,
                home_score  INTEGER,
                away_score  INTEGER,
                total_goals INTEGER,
                status      TEXT DEFAULT 'scheduled',
                created_at  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS predictions (
                id             TEXT PRIMARY KEY,
                match_id       TEXT NOT NULL,
                match_label    TEXT NOT NULL,
                league_id      TEXT NOT NULL,
                league_name    TEXT NOT NULL,
                kickoff_utc    TEXT NOT NULL,
                p_poisson      REAL NOT NULL,
                p_ml           REAL NOT NULL,
                p_ensemble     REAL NOT NULL,
                confidence     REAL NOT NULL,
                xg_home        REAL NOT NULL,
                xg_away        REAL NOT NULL,
                xg_total       REAL NOT NULL,
                odds           REAL NOT NULL,
                edge           REAL NOT NULL,
                stake          REAL NOT NULL,
                kelly_f        REAL NOT NULL,
                bet_placed     INTEGER DEFAULT 0,
                result         TEXT DEFAULT 'pending',
                created_at     TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS results (
                id             TEXT PRIMARY KEY,
                prediction_id  TEXT NOT NULL,
                match_label    TEXT NOT NULL,
                outcome        TEXT NOT NULL,
                total_goals    INTEGER NOT NULL,
                p_ensemble     REAL NOT NULL,
                odds           REAL NOT NULL,
                stake          REAL NOT NULL,
                pnl            REAL NOT NULL,
                graded_at      TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS bankroll_history (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                balance    REAL NOT NULL,
                change     REAL NOT NULL,
                reason     TEXT NOT NULL,
                recorded_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS model_state (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS simulation_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                iteration   INTEGER NOT NULL,
                n_matches   INTEGER NOT NULL,
                accuracy    REAL NOT NULL,
                log_loss    REAL NOT NULL,
                brier       REAL NOT NULL,
                roi         REAL NOT NULL,
                max_drawdown REAL NOT NULL,
                win_rate    REAL NOT NULL,
                passed      INTEGER NOT NULL,
                run_at      TEXT NOT NULL
            );
        """)
        _migrate(conn)
        conn.commit()


def _migrate(conn: sqlite3.Connection):
    """Seed default model_state rows if missing."""
    try:
        bal = conn.execute(
            "SELECT value FROM model_state WHERE key='bankroll'"
        ).fetchone()
        if bal is None:
            from data.constants import INITIAL_BANKROLL
            conn.execute(
                "INSERT OR IGNORE INTO model_state VALUES ('bankroll', ?)",
                (str(INITIAL_BANKROLL),),
            )
            conn.execute(
                "INSERT OR IGNORE INTO model_state VALUES ('loss_streak', '0')"
            )
            conn.execute(
                "INSERT OR IGNORE INTO model_state VALUES ('daily_exposure', '0.0')"
            )
            conn.execute(
                "INSERT OR IGNORE INTO model_state VALUES ('betting_halted', 'false')"
            )
    except sqlite3.Error as exc:
        logger.error("Migration failed: %s", exc)


def cache_get(key: str, ttl: int) -> Optional[Any]:
    """Retrieve a cached value if it exists and hasn't expired."""
    try:
        with _connection() as conn:
            row = conn.execute(
                "SELECT data, ts FROM api_cache WHERE cache_key=?", (key,)
            ).fetchone()
            if row and (time.time() - row["ts"]) < ttl:
                return json.loads(row["data"])
    except (sqlite3.Error, json.JSONDecodeError) as exc:
        logger.warning("Cache get failed for key=%s: %s", key, exc)
    return None


def cache_set(key: str, data: Any):
    """Store a value in the cache with the current timestamp."""
    try:
        with _connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO api_cache VALUES (?,?,?)",
                (key, json.dumps(data, default=str), time.time()),
            )
            conn.commit()
    except (sqlite3.Error, TypeError) as exc:
        logger.warning("Cache set failed for key=%s: %s", key, exc)


def get_bankroll() -> float:
    """Return the current bankroll balance."""
    try:
        with _connection() as conn:
            row = conn.execute(
                "SELECT value FROM model_state WHERE key='bankroll'"
            ).fetchone()
            if row:
                return float(row["value"])
    except (sqlite3.Error, ValueError) as exc:
        logger.warning("Failed to read bankroll: %s", exc)
    from data.constants import INITIAL_BANKROLL
    return INITIAL_BANKROLL


def set_bankroll(amount: float, change: float, reason: str):
    """Update the bankroll and record the change in history."""
    now = datetime.now(timezone.utc).isoformat()
    try:
        with _connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO model_state VALUES ('bankroll', ?)",
                (str(amount),),
            )
            conn.execute(
                "INSERT INTO bankroll_history (balance, change, reason, recorded_at) VALUES (?,?,?,?)",
                (amount, change, reason, now),
            )
            conn.commit()
    except sqlite3.Error as exc:
        logger.error("Failed to set bankroll: %s", exc)


def get_loss_streak() -> int:
    """Return the current consecutive loss count."""
    try:
        with _connection() as conn:
            row = conn.execute(
                "SELECT value FROM model_state WHERE key='loss_streak'"
            ).fetchone()
            return int(row["value"]) if row else 0
    except (sqlite3.Error, ValueError):
        return 0


def set_loss_streak(n: int):
    """Update the consecutive loss counter."""
    try:
        with _connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO model_state VALUES ('loss_streak', ?)",
                (str(n),),
            )
            conn.commit()
    except sqlite3.Error as exc:
        logger.error("Failed to set loss streak: %s", exc)


def is_betting_halted() -> bool:
    """Check whether the betting engine is currently halted."""
    try:
        with _connection() as conn:
            row = conn.execute(
                "SELECT value FROM model_state WHERE key='betting_halted'"
            ).fetchone()
            return row["value"].lower() == "true" if row else False
    except sqlite3.Error:
        return False


def set_betting_halted(state: bool):
    """Enable or disable the betting halt flag."""
    try:
        with _connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO model_state VALUES ('betting_halted', ?)",
                ("true" if state else "false",),
            )
            conn.commit()
    except sqlite3.Error as exc:
        logger.error("Failed to set betting_halted: %s", exc)


def save_prediction(pred: Dict):
    """Persist a prediction record (insert-or-ignore to avoid duplicates)."""
    try:
        with _connection() as conn:
            conn.execute("""
                INSERT OR IGNORE INTO predictions
                (id, match_id, match_label, league_id, league_name, kickoff_utc,
                 p_poisson, p_ml, p_ensemble, confidence, xg_home, xg_away, xg_total,
                 odds, edge, stake, kelly_f, bet_placed, result, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                pred["id"], pred.get("match_id", pred["id"]),
                pred["match_label"], pred["league_id"], pred["league_name"],
                pred["kickoff_utc"],
                pred["p_poisson"], pred["p_ml"], pred["p_ensemble"],
                pred["confidence"], pred["xg_home"], pred["xg_away"], pred["xg_total"],
                pred["odds"], pred["edge"], pred["stake"], pred["kelly_f"],
                1 if pred.get("bet_placed") else 0,
                pred.get("result", "pending"),
                datetime.now(timezone.utc).isoformat(),
            ))
            conn.commit()
    except sqlite3.Error as exc:
        logger.error("Failed to save prediction: %s", exc)


def get_predictions(limit: int = 200) -> List[Dict]:
    """Retrieve recent predictions ordered by creation time."""
    try:
        with _connection() as conn:
            rows = conn.execute(
                "SELECT * FROM predictions ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]
    except sqlite3.Error as exc:
        logger.error("Failed to get predictions: %s", exc)
        return []


def save_result(res: Dict):
    """Persist a graded result and update the linked prediction."""
    try:
        with _connection() as conn:
            conn.execute("""
                INSERT OR IGNORE INTO results
                (id, prediction_id, match_label, outcome, total_goals,
                 p_ensemble, odds, stake, pnl, graded_at)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (
                res["id"], res["prediction_id"], res["match_label"],
                res["outcome"], res["total_goals"],
                res["p_ensemble"], res["odds"], res["stake"], res["pnl"],
                datetime.now(timezone.utc).isoformat(),
            ))
            conn.execute(
                "UPDATE predictions SET result=? WHERE id=?",
                (res["outcome"], res["prediction_id"]),
            )
            conn.commit()
    except sqlite3.Error as exc:
        logger.error("Failed to save result: %s", exc)


def get_results(limit: int = 300) -> List[Dict]:
    """Retrieve graded results ordered by time."""
    try:
        with _connection() as conn:
            rows = conn.execute(
                "SELECT * FROM results ORDER BY graded_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]
    except sqlite3.Error as exc:
        logger.error("Failed to get results: %s", exc)
        return []


def get_bankroll_history() -> List[Dict]:
    """Return full bankroll change history."""
    try:
        with _connection() as conn:
            rows = conn.execute(
                "SELECT * FROM bankroll_history ORDER BY id ASC"
            ).fetchall()
            return [dict(r) for r in rows]
    except sqlite3.Error:
        return []


def save_simulation_log(log: Dict):
    """Record a simulation iteration result."""
    try:
        with _connection() as conn:
            conn.execute("""
                INSERT INTO simulation_log
                (iteration, n_matches, accuracy, log_loss, brier, roi,
                 max_drawdown, win_rate, passed, run_at)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (
                log["iteration"], log["n_matches"],
                log["accuracy"], log["log_loss"], log["brier"],
                log["roi"], log["max_drawdown"], log["win_rate"],
                1 if log["passed"] else 0,
                datetime.now(timezone.utc).isoformat(),
            ))
            conn.commit()
    except sqlite3.Error as exc:
        logger.error("Failed to save simulation log: %s", exc)


def get_simulation_logs() -> List[Dict]:
    """Retrieve recent simulation logs."""
    try:
        with _connection() as conn:
            rows = conn.execute(
                "SELECT * FROM simulation_log ORDER BY id DESC LIMIT 50"
            ).fetchall()
            return [dict(r) for r in rows]
    except sqlite3.Error:
        return []


def get_model_weights() -> Optional[List[float]]:
    """Load persisted ML model weights."""
    try:
        with _connection() as conn:
            row = conn.execute(
                "SELECT value FROM model_state WHERE key='weights'"
            ).fetchone()
            if row:
                return json.loads(row["value"])
    except (sqlite3.Error, json.JSONDecodeError) as exc:
        logger.warning("Failed to load model weights: %s", exc)
    return None


def save_model_weights(weights: List[float], bias: float):
    """Persist ML model weights and bias."""
    try:
        with _connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO model_state VALUES ('weights', ?)",
                (json.dumps(weights),),
            )
            conn.execute(
                "INSERT OR REPLACE INTO model_state VALUES ('bias', ?)",
                (str(bias),),
            )
            conn.commit()
    except sqlite3.Error as exc:
        logger.error("Failed to save model weights: %s", exc)


def get_model_bias() -> float:
    """Load the persisted ML model bias term."""
    try:
        with _connection() as conn:
            row = conn.execute(
                "SELECT value FROM model_state WHERE key='bias'"
            ).fetchone()
            return float(row["value"]) if row else 0.0
    except (sqlite3.Error, ValueError):
        return 0.0
