from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.graph.errors import GraphAuthenticationError, GraphConfigurationError
from app.graph.models import GraphSettings, Token
from app.graph.transport import UrlLibTransport


TOKEN_URL_TEMPLATE = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
GRAPH_SCOPE = "https://graph.microsoft.com/.default"


class ClientCredentialsAuth:
    def __init__(self, settings: GraphSettings, secret: str | None, transport: UrlLibTransport | None = None):
        self.settings = settings
        self.secret = secret
        self.transport = transport or UrlLibTransport()
        self._token: Token | None = None

    def get_token(self) -> str:
        if self._token and not self._token.is_expired():
            return self._token.access_token
        if not self.settings.is_configured or not self.secret:
            raise GraphConfigurationError("Tenant ID, Client ID et Client Secret sont requis.")

        response = self.transport.request(
            "POST",
            TOKEN_URL_TEMPLATE.format(tenant_id=self.settings.tenant_id),
            headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
            data={
                "client_id": self.settings.client_id,
                "client_secret": self.secret,
                "grant_type": "client_credentials",
                "scope": GRAPH_SCOPE,
            },
            timeout=30,
        )
        if response.status_code >= 400:
            raise GraphAuthenticationError("Echec du flux OAuth2 client credentials.", status_code=response.status_code)
        payload = response.json()
        access_token = payload.get("access_token")
        expires_in = int(payload.get("expires_in", 3600))
        if not access_token:
            raise GraphAuthenticationError("La reponse OAuth2 ne contient pas d'access token.")
        self._token = Token(
            access_token=str(access_token),
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=max(60, expires_in - 120)),
        )
        return self._token.access_token

