from __future__ import annotations


class GraphError(Exception):
    user_message = "Microsoft Graph request failed."

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
    user_message = "Microsoft Graph is not configured."


class GraphAuthenticationError(GraphError):
    user_message = "Authentication failed. Verify Tenant ID, Client ID and Client Secret."


class GraphForbiddenError(GraphError):
    user_message = (
        "403 Forbidden. Endpoint Toolbox is authenticated but the application registration "
        "does not have the required Graph permission."
    )


class GraphNotFoundError(GraphError):
    user_message = "The requested Microsoft Graph object was not found."


class GraphThrottledError(GraphError):
    user_message = "Microsoft Graph throttled the request. Retrying did not complete successfully."


class GraphNetworkError(GraphError):
    user_message = "Network error. Unable to reach Microsoft Graph."


class GraphTimeoutError(GraphNetworkError):
    user_message = "Network timeout. Microsoft Graph did not respond in time."


class GraphReadOnlyViolation(GraphError):
    user_message = "Blocked unsafe Microsoft Graph method. Endpoint Toolbox is read-only."


class SecureStorageUnavailable(GraphError):
    user_message = "Secure secret storage is unavailable. Client Secret was not saved."

