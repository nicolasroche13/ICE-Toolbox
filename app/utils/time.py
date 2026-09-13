from __future__ import annotations

from datetime import datetime, timezone


def parse_graph_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def relative_datetime(value: str | None, *, now: datetime | None = None) -> str:
    parsed = parse_graph_datetime(value)
    if not parsed:
        return "Not available"
    current = now or datetime.now(timezone.utc)
    seconds = int((current - parsed).total_seconds())
    suffix = "ago" if seconds >= 0 else "from now"
    seconds = abs(seconds)
    if seconds < 60:
        return f"{seconds} seconds {suffix}"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} minutes {suffix}"
    hours = minutes // 60
    if hours < 48:
        return f"{hours} hours {suffix}"
    days = hours // 24
    return f"{days} days {suffix}"
