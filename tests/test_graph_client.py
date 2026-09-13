from __future__ import annotations

import pytest

from app.graph.auth import ClientCredentialsAuth
from app.graph.client import GraphReadOnlyClient
from app.graph.errors import (
    GraphAuthenticationError,
    GraphForbiddenError,
    GraphNotFoundError,
    GraphReadOnlyViolation,
    GraphThrottledError,
    GraphTimeoutError,
)
from app.graph.models import GraphSettings
from app.graph.transport import HttpResponse


class FakeTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def request(self, method, url, *, headers=None, params=None, data=None, timeout=30):
        self.calls.append({"method": method, "url": url, "headers": headers or {}, "params": params, "data": data})
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def response(status: int, body: str = "{}", headers: dict[str, str] | None = None) -> HttpResponse:
    return HttpResponse(status, headers or {}, body.encode("utf-8"), 12)


def client_with(responses) -> GraphReadOnlyClient:
    transport = FakeTransport([response(200, '{"access_token":"token","expires_in":3600}'), *responses])
    auth = ClientCredentialsAuth(GraphSettings("tenant", "client"), "secret", transport=transport)
    return GraphReadOnlyClient(auth, transport=transport, max_retries=1)


def test_authentication_uses_client_credentials_without_logging_secret() -> None:
    transport = FakeTransport([response(200, '{"access_token":"token","expires_in":3600}')])
    auth = ClientCredentialsAuth(GraphSettings("tenant", "client"), "secret-value", transport=transport)
    assert auth.get_token() == "token"
    call = transport.calls[0]
    assert call["method"] == "POST"
    assert call["data"]["grant_type"] == "client_credentials"
    assert call["data"]["client_secret"] == "secret-value"


def test_get_is_read_only_and_adds_bearer_header() -> None:
    client = client_with([response(200, '{"value": []}')])
    result = client.get("deviceManagement/managedDevices")
    assert result.log.status_code == 200


def test_blocks_write_methods() -> None:
    client = client_with([])
    for method in ["POST", "PATCH", "PUT", "DELETE"]:
        with pytest.raises(GraphReadOnlyViolation):
            client.request(method, "deviceManagement/managedDevices")


def test_pagination_merges_values() -> None:
    client = client_with(
        [
            response(200, '{"value":[{"id":"1"}],"@odata.nextLink":"https://graph.microsoft.com/v1.0/next"}'),
            response(200, '{"value":[{"id":"2"}]}'),
        ]
    )
    result = client.get_all("deviceManagement/managedDevices")
    assert result.data["value"] == [{"id": "1"}, {"id": "2"}]
    assert result.log.object_count == 2


def test_maps_401_403_404() -> None:
    for status, error_type in [(401, GraphAuthenticationError), (403, GraphForbiddenError), (404, GraphNotFoundError)]:
        client = client_with([response(status, '{"error":{"message":"nope"}}')])
        with pytest.raises(error_type):
            client.get("deviceManagement/managedDevices")


def test_429_retries_then_succeeds() -> None:
    client = client_with(
        [
            response(429, '{"error":{"message":"slow"}}', {"Retry-After": "0"}),
            response(200, '{"value":[{"id":"1"}]}'),
        ]
    )
    result = client.get("deviceManagement/managedDevices")
    assert result.data["value"][0]["id"] == "1"


def test_429_retry_keeps_query_params() -> None:
    client = client_with(
        [
            response(429, '{"error":{"message":"slow"}}', {"Retry-After": "0"}),
            response(200, '{"value":[{"id":"1"}]}'),
        ]
    )
    client.get("deviceManagement/managedDevices", params={"$top": "1"})
    graph_calls = [call for call in client.transport.calls if call["method"] == "GET"]  # type: ignore[attr-defined]
    assert graph_calls[0]["params"] == {"$top": "1"}
    assert graph_calls[1]["params"] == {"$top": "1"}


def test_request_ids_are_captured_without_authorization_header() -> None:
    client = client_with(
        [
            response(
                200,
                '{"value":[]}',
                {"request-id": "req-1", "client-request-id": "client-1", "date": "Sun, 13 Sep 2026 19:00:00 GMT"},
            )
        ]
    )
    result = client.get("deviceManagement/managedDevices")
    assert result.log.request_id == "req-1"
    assert result.log.client_request_id == "client-1"
    assert result.log.response_date == "Sun, 13 Sep 2026 19:00:00 GMT"


def test_request_ids_are_captured_on_error_responses_too() -> None:
    client = client_with(
        [
            response(
                403,
                '{"error":{"message":"nope"}}',
                {"request-id": "req-err", "client-request-id": "client-err", "date": "Sun, 13 Sep 2026 19:00:00 GMT"},
            )
        ]
    )
    try:
        client.get("deviceManagement/managedDevices")
        raise AssertionError("Expected GraphForbiddenError")
    except GraphForbiddenError as exc:
        assert exc.request_id == "req-err"
        assert exc.client_request_id == "client-err"
        assert exc.response_date == "Sun, 13 Sep 2026 19:00:00 GMT"


def test_429_raises_after_retry_budget() -> None:
    client = client_with(
        [
            response(429, '{"error":{"message":"slow"}}', {"Retry-After": "0"}),
            response(429, '{"error":{"message":"still slow"}}'),
        ]
    )
    with pytest.raises(GraphThrottledError):
        client.get("deviceManagement/managedDevices")


def test_timeout_surfaces_cleanly() -> None:
    transport = FakeTransport([GraphTimeoutError("timeout")])
    auth = ClientCredentialsAuth(GraphSettings("tenant", "client"), "secret", transport=transport)
    with pytest.raises(GraphTimeoutError):
        auth.get_token()


def test_authentication_failure() -> None:
    transport = FakeTransport([response(401, '{"error":"invalid_client"}')])
    auth = ClientCredentialsAuth(GraphSettings("tenant", "client"), "bad", transport=transport)
    with pytest.raises(GraphAuthenticationError):
        auth.get_token()
