from __future__ import annotations

import pytest

from app.graph.errors import SecureStorageUnavailable
from app.graph.models import GraphSettings
from app.graph.secrets import GraphSecretStore


class FakeKeyring:
    """In-memory stand-in for the OS credential manager (Keychain / Credential Manager)."""

    def __init__(self) -> None:
        self._store: dict[tuple[str, str], str] = {}

    def get_password(self, service: str, username: str) -> str | None:
        return self._store.get((service, username))

    def set_password(self, service: str, username: str, password: str) -> None:
        self._store[(service, username)] = password

    def delete_password(self, service: str, username: str) -> None:
        if (service, username) not in self._store:
            raise Exception("not found")
        del self._store[(service, username)]


def _settings(tenant: str = "tenant-1", client: str = "client-1") -> GraphSettings:
    return GraphSettings(tenant_id=tenant, client_id=client)


def _store_with_fake_keyring(fake: FakeKeyring) -> GraphSecretStore:
    store = GraphSecretStore()
    store._keyring = lambda: fake  # type: ignore[method-assign]
    return store


def test_secret_present_round_trips() -> None:
    store = _store_with_fake_keyring(FakeKeyring())
    settings = _settings()
    store.set_secret(settings, "s3cr3t")
    assert store.get_secret(settings) == "s3cr3t"


def test_secret_absent_returns_none_without_raising() -> None:
    store = _store_with_fake_keyring(FakeKeyring())
    settings = _settings()
    assert store.get_secret(settings) is None


def test_secret_deleted_is_no_longer_retrievable() -> None:
    store = _store_with_fake_keyring(FakeKeyring())
    settings = _settings()
    store.set_secret(settings, "s3cr3t")
    store.delete_secret(settings)
    assert store.get_secret(settings) is None


def test_delete_secret_on_missing_entry_does_not_raise() -> None:
    store = _store_with_fake_keyring(FakeKeyring())
    settings = _settings()
    store.delete_secret(settings)


def test_secret_update_overwrites_previous_value() -> None:
    store = _store_with_fake_keyring(FakeKeyring())
    settings = _settings()
    store.set_secret(settings, "old-secret")
    store.set_secret(settings, "new-secret")
    assert store.get_secret(settings) == "new-secret"


def test_secrets_are_isolated_per_tenant_and_client() -> None:
    fake = FakeKeyring()
    store = _store_with_fake_keyring(fake)
    store.set_secret(_settings("tenant-a", "client-a"), "secret-a")
    store.set_secret(_settings("tenant-b", "client-b"), "secret-b")
    assert store.get_secret(_settings("tenant-a", "client-a")) == "secret-a"
    assert store.get_secret(_settings("tenant-b", "client-b")) == "secret-b"


def test_set_secret_rejects_empty_value() -> None:
    store = _store_with_fake_keyring(FakeKeyring())
    with pytest.raises(SecureStorageUnavailable):
        store.set_secret(_settings(), "")


def test_credential_manager_inaccessible_on_get_raises_secure_storage_unavailable() -> None:
    store = GraphSecretStore()

    def _unavailable():
        raise SecureStorageUnavailable("Aucun backend keyring securise n'est disponible.")

    store._keyring = _unavailable  # type: ignore[method-assign]
    with pytest.raises(SecureStorageUnavailable):
        store.get_secret(_settings())


def test_credential_manager_inaccessible_on_set_raises_secure_storage_unavailable() -> None:
    store = GraphSecretStore()

    def _unavailable():
        raise SecureStorageUnavailable("Aucun backend keyring securise n'est disponible.")

    store._keyring = _unavailable  # type: ignore[method-assign]
    with pytest.raises(SecureStorageUnavailable):
        store.set_secret(_settings(), "s3cr3t")


def test_credential_manager_inaccessible_on_delete_raises_secure_storage_unavailable() -> None:
    # delete_secret only swallows a missing keyring *entry* (already-deleted secret);
    # the backend itself being unavailable still propagates, exactly like get/set,
    # so callers (see MainWindow.clear_configuration) can surface it consistently.
    store = GraphSecretStore()

    def _unavailable():
        raise SecureStorageUnavailable("Aucun backend keyring securise n'est disponible.")

    store._keyring = _unavailable  # type: ignore[method-assign]
    with pytest.raises(SecureStorageUnavailable):
        store.delete_secret(_settings())
