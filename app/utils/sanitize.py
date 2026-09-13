from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


_CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")


SENSITIVE_KEYS = {
    "authorization",
    "access_token",
    "refresh_token",
    "client_secret",
    "secret",
    "token",
    "id_token",
}


def sanitize_for_export(value: Any) -> Any:
    if isinstance(value, Mapping):
        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if _is_sensitive_key(key_text):
                cleaned[key_text] = "[REDACTED]"
            else:
                cleaned[key_text] = sanitize_for_export(item)
        return cleaned
    if isinstance(value, list):
        return [sanitize_for_export(item) for item in value]
    if isinstance(value, tuple):
        return [sanitize_for_export(item) for item in value]
    return value


def _is_sensitive_key(key: str) -> bool:
    # Graph JSON uses camelCase (clientSecret, accessToken); our own models use
    # snake_case. Normalize both to the same shape before matching so neither leaks.
    normalized = _CAMEL_BOUNDARY.sub("_", key.replace("-", "_")).casefold()
    return normalized in SENSITIVE_KEYS or normalized.endswith("_token") or "authorization" in normalized
