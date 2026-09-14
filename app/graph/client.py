from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Mapping
from urllib.parse import urljoin

from app.graph.auth import ClientCredentialsAuth
from app.graph.errors import (
    GraphAuthenticationError,
    GraphError,
    GraphForbiddenError,
    GraphNetworkError,
    GraphNotFoundError,
    GraphReadOnlyViolation,
    GraphThrottledError,
)
from app.graph.models import GraphRequestLog, GraphResponse
from app.graph.transport import HttpResponse, UrlLibTransport


GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0/"
GRAPH_BETA_BASE_URL = "https://graph.microsoft.com/beta/"
READ_ONLY_METHODS = {"GET"}


@dataclass
class CancellationToken:
    cancelled: bool = False

    def cancel(self) -> None:
        self.cancelled = True


class GraphReadOnlyClient:
    def __init__(
        self,
        auth: ClientCredentialsAuth,
        *,
        transport: UrlLibTransport | None = None,
        base_url: str = GRAPH_BASE_URL,
        timeout: int = 30,
        max_retries: int = 1,
    ):
        self.auth = auth
        self.transport = transport or auth.transport
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries

    def request(
        self,
        method: str,
        path_or_url: str,
        *,
        params: Mapping[str, str] | None = None,
        cancellation: CancellationToken | None = None,
    ) -> GraphResponse:
        method = method.upper()
        if method not in READ_ONLY_METHODS:
            raise GraphReadOnlyViolation(f"La methode HTTP {method} est bloquee par le client Graph en lecture seule.")
        if cancellation and cancellation.cancelled:
            raise GraphNetworkError("Requete annulee avant demarrage.")

        url = self._url(path_or_url)
        attempt = 0
        while True:
            if cancellation and cancellation.cancelled:
                raise GraphNetworkError("Requete annulee.")
            token = self.auth.get_token()
            response = self.transport.request(
                method,
                url,
                headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
                params=params,
                timeout=self.timeout,
            )
            if response.status_code == 429 and attempt < self.max_retries:
                retry_after = int(response.headers.get("Retry-After", "1"))
                time.sleep(min(retry_after, 5))
                attempt += 1
                continue
            return self._handle_response(method, url, response)

    def get(self, path_or_url: str, *, params: Mapping[str, str] | None = None, cancellation: CancellationToken | None = None) -> GraphResponse:
        return self.request("GET", path_or_url, params=params, cancellation=cancellation)

    def get_all(self, path_or_url: str, *, params: Mapping[str, str] | None = None, cancellation: CancellationToken | None = None) -> GraphResponse:
        first = self.get(path_or_url, params=params, cancellation=cancellation)
        data = first.data
        values = list(data.get("value", []))
        logs = [first.log]
        next_link = data.get("@odata.nextLink")
        while next_link:
            page = self.get(str(next_link), cancellation=cancellation)
            values.extend(page.data.get("value", []))
            logs.append(page.log)
            next_link = page.data.get("@odata.nextLink")
        data = dict(data)
        data["value"] = values
        data.pop("@odata.nextLink", None)
        total_duration = sum(log.duration_ms for log in logs)
        merged_log = GraphRequestLog("GET", self._url(path_or_url), 200, total_duration, len(values), api_version=_api_version(self._url(path_or_url)))
        return GraphResponse(data=data, log=merged_log, pages=tuple(logs))

    def _url(self, path_or_url: str) -> str:
        if path_or_url.startswith("https://"):
            return path_or_url
        return urljoin(self.base_url, path_or_url.lstrip("/"))

    def _handle_response(self, method: str, url: str, response: HttpResponse) -> GraphResponse:
        object_count = None
        payload = {}
        try:
            payload = response.json()
            if isinstance(payload.get("value"), list):
                object_count = len(payload["value"])
        except Exception:
            payload = {}
        log = GraphRequestLog(
            method,
            url,
            response.status_code,
            response.duration_ms,
            object_count,
            api_version=_api_version(url),
            request_id=_header(response.headers, "request-id"),
            client_request_id=_header(response.headers, "client-request-id"),
            response_date=_header(response.headers, "date"),
        )
        if response.status_code in {200, 201, 204}:
            return GraphResponse(payload, log)
        message = _graph_error_message(payload) or f"Graph a renvoye le statut HTTP {response.status_code}."
        error_kwargs = dict(
            details=message,
            request_id=log.request_id,
            client_request_id=log.client_request_id,
            response_date=log.response_date,
        )
        if response.status_code == 401:
            raise GraphAuthenticationError(message, status_code=401, **error_kwargs)
        if response.status_code == 403:
            raise GraphForbiddenError(message, status_code=403, **error_kwargs)
        if response.status_code == 404:
            raise GraphNotFoundError(message, status_code=404, **error_kwargs)
        if response.status_code == 429:
            raise GraphThrottledError(message, status_code=429, **error_kwargs)
        raise GraphError(message, status_code=response.status_code, **error_kwargs)


def _graph_error_message(payload: dict) -> str | None:
    error = payload.get("error")
    if isinstance(error, dict):
        message = error.get("message")
        if message:
            return str(message)
    return None


def _header(headers: Mapping[str, str], name: str) -> str | None:
    for key, value in headers.items():
        if key.casefold() == name.casefold():
            return value
    return None


def _api_version(url: str) -> str:
    if "/beta/" in url:
        return "beta"
    return "v1.0"
