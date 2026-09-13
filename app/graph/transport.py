from __future__ import annotations

import json
import socket
import time
from dataclasses import dataclass
from typing import Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.graph.errors import GraphNetworkError, GraphTimeoutError


@dataclass(frozen=True)
class HttpResponse:
    status_code: int
    headers: Mapping[str, str]
    body: bytes
    duration_ms: int

    def json(self) -> dict:
        if not self.body:
            return {}
        return json.loads(self.body.decode("utf-8"))


class UrlLibTransport:
    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        params: Mapping[str, str] | None = None,
        data: Mapping[str, str] | None = None,
        timeout: int = 30,
    ) -> HttpResponse:
        if params:
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}{urlencode(params)}"
        body = urlencode(data).encode("utf-8") if data is not None else None
        request = Request(url, data=body, headers=dict(headers or {}), method=method.upper())
        started = time.monotonic()
        try:
            with urlopen(request, timeout=timeout) as response:
                duration = int((time.monotonic() - started) * 1000)
                return HttpResponse(response.status, dict(response.headers), response.read(), duration)
        except HTTPError as exc:
            duration = int((time.monotonic() - started) * 1000)
            return HttpResponse(exc.code, dict(exc.headers), exc.read(), duration)
        except socket.timeout as exc:
            raise GraphTimeoutError("Microsoft Graph request timed out.") from exc
        except URLError as exc:
            reason = getattr(exc, "reason", None)
            if isinstance(reason, socket.timeout):
                raise GraphTimeoutError("Microsoft Graph request timed out.") from exc
            raise GraphNetworkError(f"Unable to reach Microsoft Graph: {reason}") from exc

