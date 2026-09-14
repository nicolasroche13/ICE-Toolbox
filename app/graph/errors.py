from __future__ import annotations


class GraphError(Exception):
    user_message = "La requete Microsoft Graph a echoue."

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        details: str | None = None,
        request_id: str | None = None,
        client_request_id: str | None = None,
        response_date: str | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.details = details or message
        self.request_id = request_id
        self.client_request_id = client_request_id
        self.response_date = response_date


class GraphConfigurationError(GraphError):
    user_message = "Microsoft Graph n'est pas configure."


class GraphAuthenticationError(GraphError):
    user_message = "Echec de l'authentification. Verifiez le Tenant ID, le Client ID et le Client Secret."


class GraphForbiddenError(GraphError):
    user_message = (
        "403 Forbidden. Endpoint Toolbox est authentifie mais l'App Registration ne dispose pas "
        "de la permission Graph requise."
    )


class GraphNotFoundError(GraphError):
    user_message = "L'objet Microsoft Graph demande est introuvable."


class GraphThrottledError(GraphError):
    user_message = "Microsoft Graph a limite la requete (throttling). La nouvelle tentative n'a pas abouti."


class GraphNetworkError(GraphError):
    user_message = "Erreur reseau. Impossible de joindre Microsoft Graph."


class GraphTimeoutError(GraphNetworkError):
    user_message = "Delai reseau depasse. Microsoft Graph n'a pas repondu a temps."


class GraphReadOnlyViolation(GraphError):
    user_message = "Methode Microsoft Graph non autorisee bloquee. Endpoint Toolbox est en lecture seule."


class SecureStorageUnavailable(GraphError):
    user_message = "Le stockage securise des secrets est indisponible. Le Client Secret n'a pas ete enregistre."

