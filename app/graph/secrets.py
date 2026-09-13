from __future__ import annotations

from app.graph.errors import SecureStorageUnavailable
from app.graph.models import GraphSettings


SERVICE_NAME = "EndpointToolbox Microsoft Graph"


class GraphSecretStore:
    def _username(self, settings: GraphSettings) -> str:
        return f"{settings.tenant_id.strip()}:{settings.client_id.strip()}"

    def get_secret(self, settings: GraphSettings) -> str | None:
        keyring = self._keyring()
        return keyring.get_password(SERVICE_NAME, self._username(settings))

    def set_secret(self, settings: GraphSettings, secret: str) -> None:
        if not secret:
            raise SecureStorageUnavailable("Client Secret is empty.")
        keyring = self._keyring()
        keyring.set_password(SERVICE_NAME, self._username(settings), secret)

    def delete_secret(self, settings: GraphSettings) -> None:
        keyring = self._keyring()
        try:
            keyring.delete_password(SERVICE_NAME, self._username(settings))
        except Exception:
            return

    def _keyring(self):
        try:
            import keyring
            from keyring.errors import NoKeyringError
        except Exception as exc:
            raise SecureStorageUnavailable("Install keyring to store Client Secret securely.") from exc

        try:
            backend_name = keyring.get_keyring().__class__.__name__.lower()
            if "fail" in backend_name or "null" in backend_name:
                raise SecureStorageUnavailable("No secure keyring backend is available.")
            return keyring
        except NoKeyringError as exc:
            raise SecureStorageUnavailable("No secure keyring backend is available.") from exc

