from __future__ import annotations

from app.graph.auth import ClientCredentialsAuth
from app.graph.client import GraphReadOnlyClient
from app.graph.config import GraphConfigStore
from app.graph.errors import GraphConfigurationError
from app.graph.secrets import GraphSecretStore
from app.intune.device_inspector import IntuneDeviceInspectorService


def build_intune_device_inspector(
    config_store: GraphConfigStore | None = None,
    secret_store: GraphSecretStore | None = None,
) -> IntuneDeviceInspectorService:
    config_store = config_store or GraphConfigStore()
    secret_store = secret_store or GraphSecretStore()
    settings = config_store.load()
    if settings is None:
        raise GraphConfigurationError("Microsoft Graph is not configured.")
    secret = secret_store.get_secret(settings)
    if not secret:
        raise GraphConfigurationError("Client Secret is not available in secure storage.")
    auth = ClientCredentialsAuth(settings, secret)
    return IntuneDeviceInspectorService(GraphReadOnlyClient(auth), stale_device_days=settings.stale_device_days)
