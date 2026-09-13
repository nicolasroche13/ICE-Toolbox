from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


JsonObject = dict[str, Any]


@dataclass(frozen=True)
class GraphSettings:
    tenant_id: str
    client_id: str
    stale_device_days: int = 7

    @property
    def is_configured(self) -> bool:
        return bool(self.tenant_id.strip() and self.client_id.strip())


@dataclass(frozen=True)
class Token:
    access_token: str
    expires_at: datetime

    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) >= self.expires_at


@dataclass(frozen=True)
class GraphRequestLog:
    method: str
    url: str
    status_code: int | None
    duration_ms: int
    object_count: int | None = None
    source: str = "Graph"
    api_version: str = "v1.0"
    request_id: str | None = None
    client_request_id: str | None = None
    response_date: str | None = None


@dataclass(frozen=True)
class GraphResponse:
    data: JsonObject
    log: GraphRequestLog
    pages: tuple[GraphRequestLog, ...] = field(default_factory=tuple)
