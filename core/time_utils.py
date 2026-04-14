import datetime
import time

CAT_OFFSET = datetime.timedelta(hours=2)

def now_utc() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)

def now_cat() -> datetime.datetime:
    return now_utc() + CAT_OFFSET

def utc_iso() -> str:
    return now_utc().isoformat()

def cat_iso() -> str:
    return now_cat().isoformat()

def minutes_until(iso_str: str) -> float:
    try:
        if iso_str.endswith("Z"):
            iso_str = iso_str[:-1] + "+00:00"
        dt = datetime.datetime.fromisoformat(iso_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return (dt - now_utc()).total_seconds() / 60.0
    except Exception:
        return -9999.0

def in_scan_window(iso_str: str, min_min: int = 10, max_min: int = 1440) -> bool:
    """True if kickoff is between min_min and max_min minutes from now."""
    m = minutes_until(iso_str)
    return min_min <= m <= max_min

def today_str_utc() -> str:
    return now_utc().strftime("%Y%m%d")

def tomorrow_str_utc() -> str:
    return (now_utc() + datetime.timedelta(days=1)).strftime("%Y%m%d")

def date_str_offset(offset_days: int = 0) -> str:
    return (now_utc() + datetime.timedelta(days=offset_days)).strftime("%Y%m%d")

def epoch_now() -> float:
    return time.time()
