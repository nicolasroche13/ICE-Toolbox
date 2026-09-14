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
        return "Non disponible"
    current = now or datetime.now(timezone.utc)
    seconds = int((current - parsed).total_seconds())
    suffix = "il y a" if seconds >= 0 else "dans"
    seconds = abs(seconds)
    if seconds < 60:
        return f"{suffix} {seconds} secondes"
    minutes = seconds // 60
    if minutes < 60:
        return f"{suffix} {minutes} minutes"
    hours = minutes // 60
    if hours < 48:
        return f"{suffix} {hours} heures"
    days = hours // 24
    return f"{suffix} {days} jours"
