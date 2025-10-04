from datetime import datetime, timezone

def parse_iso(s: str) -> datetime:
    """Parses an ISO 8601 string, handling 'Z' for UTC."""
    s = s.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)

def to_utc(dt: datetime) -> datetime:
    """Converts a naive datetime to a timezone-aware UTC datetime."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)

def round_to_slot(dt: datetime, minutes: int) -> datetime:
    """Rounds a datetime down to the nearest slot based on a minute interval."""
    dt_utc = to_utc(dt).astimezone(timezone.utc)
    total_minutes = dt_utc.hour * 60 + dt_utc.minute
    floored_total = (total_minutes // minutes) * minutes
    return dt_utc.replace(
        hour=floored_total // 60,
        minute=floored_total % 60,
        second=0,
        microsecond=0
    )

def db_utc_naive(dt: datetime) -> datetime:
    """Converts a timezone-aware datetime to a naive UTC datetime for DB storage."""
    return to_utc(dt).astimezone(timezone.utc).replace(tzinfo=None)

def api_iso_z(dt: datetime) -> str:
    """Formats a datetime into an ISO 8601 string ending in 'Z' for API responses."""
    return to_utc(dt).astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")