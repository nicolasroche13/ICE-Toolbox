from __future__ import annotations

from app.utils.sanitize import sanitize_for_export


def test_redacts_authorization_header_case_insensitive() -> None:
    payload = {"headers": {"Authorization": "Bearer super-secret-token", "authorization": "Bearer other"}}
    cleaned = sanitize_for_export(payload)
    assert cleaned["headers"]["Authorization"] == "[REDACTED]"
    assert cleaned["headers"]["authorization"] == "[REDACTED]"


def test_redacts_client_secret_and_tokens_nested_in_lists() -> None:
    payload = {
        "sources": [
            {"name": "auth", "client_secret": "abc123"},
            {"name": "auth2", "access_token": "xyz", "refresh_token": "uvw", "id_token": "jwt"},
        ]
    }
    cleaned = sanitize_for_export(payload)
    assert cleaned["sources"][0]["client_secret"] == "[REDACTED]"
    assert cleaned["sources"][1]["access_token"] == "[REDACTED]"
    assert cleaned["sources"][1]["refresh_token"] == "[REDACTED]"
    assert cleaned["sources"][1]["id_token"] == "[REDACTED]"


def test_redacts_keys_ending_in_token_or_containing_authorization() -> None:
    payload = {"graphToken": "secret", "Authorization-Header": "Bearer x", "unrelated": "keep me"}
    cleaned = sanitize_for_export(payload)
    assert cleaned["graphToken"] == "[REDACTED]"
    assert cleaned["Authorization-Header"] == "[REDACTED]"
    assert cleaned["unrelated"] == "keep me"


def test_redacts_camel_case_graph_style_keys() -> None:
    payload = {"clientSecret": "abc123", "accessToken": "xyz", "refreshToken": "uvw", "idToken": "jwt"}
    cleaned = sanitize_for_export(payload)
    assert cleaned["clientSecret"] == "[REDACTED]"
    assert cleaned["accessToken"] == "[REDACTED]"
    assert cleaned["refreshToken"] == "[REDACTED]"
    assert cleaned["idToken"] == "[REDACTED]"


def test_does_not_redact_unrelated_fields() -> None:
    payload = {"deviceName": "PC-1", "complianceState": "compliant", "count": 3}
    cleaned = sanitize_for_export(payload)
    assert cleaned == payload


def test_sanitizes_tuples_like_lists() -> None:
    payload = {"values": ({"secret": "hide-me"}, {"secret": "hide-me-too"})}
    cleaned = sanitize_for_export(payload)
    assert cleaned["values"] == [{"secret": "[REDACTED]"}, {"secret": "[REDACTED]"}]
