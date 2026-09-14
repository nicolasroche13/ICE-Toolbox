from __future__ import annotations

from app.autopilot.inspector import AutopilotInspectorService
from app.graph.auth import ClientCredentialsAuth
from app.graph.client import GraphReadOnlyClient
from app.graph.config import GraphConfigStore
from app.graph.errors import GraphConfigurationError
from app.graph.models import GraphSettings
from app.graph.secrets import GraphSecretStore
from app.intune.device_inspector import IntuneDeviceInspectorService


def _resolve_auth(
    config_store: GraphConfigStore | None, secret_store: GraphSecretStore | None
) -> tuple[ClientCredentialsAuth, GraphSettings]:
    config_store = config_store or GraphConfigStore()
    secret_store = secret_store or GraphSecretStore()
    settings = config_store.load()
    if settings is None:
        raise GraphConfigurationError("Microsoft Graph n'est pas configure.")
    secret = secret_store.get_secret(settings)
    if not secret:
        raise GraphConfigurationError("Le Client Secret n'est pas disponible dans le stockage securise.")
    return ClientCredentialsAuth(settings, secret), settings


def build_intune_device_inspector(
    config_store: GraphConfigStore | None = None,
    secret_store: GraphSecretStore | None = None,
) -> IntuneDeviceInspectorService:
    auth, settings = _resolve_auth(config_store, secret_store)
    return IntuneDeviceInspectorService(GraphReadOnlyClient(auth), stale_device_days=settings.stale_device_days)


def build_autopilot_inspector(
    config_store: GraphConfigStore | None = None,
    secret_store: GraphSecretStore | None = None,
) -> AutopilotInspectorService:
    auth, settings = _resolve_auth(config_store, secret_store)
    return AutopilotInspectorService(GraphReadOnlyClient(auth), stale_device_days=settings.stale_device_days)
