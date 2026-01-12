"""
Error Codes

Zentrale Definition aller Error Codes.
"""


class ErrorCodes:
    """
    Alle Error Codes an einer Stelle.

    Format: EXXXX
    - E1xxx: Validation Errors
    - E2xxx: NotFound Errors
    - E3xxx: Auth Errors
    - E4xxx: Adapter Errors
    - E5xxx: Internal Errors
    """

    # === Validation (E1xxx) ===
    INVALID_INPUT = "E1001"
    MISSING_REQUIRED_FIELD = "E1002"
    FORMAT_ERROR = "E1003"
    VALUE_OUT_OF_RANGE = "E1004"

    # === NotFound (E2xxx) ===
    ITEM_NOT_FOUND = "E2001"
    USER_NOT_FOUND = "E2002"
    WORKFLOW_NOT_FOUND = "E2003"
    SESSION_NOT_FOUND = "E2004"

    # === Auth (E3xxx) ===
    INVALID_TOKEN = "E3001"
    TOKEN_EXPIRED = "E3002"
    INSUFFICIENT_PERMISSIONS = "E3003"
    INVALID_CREDENTIALS = "E3004"

    # === Adapter (E4xxx) ===
    DATABASE_UNAVAILABLE = "E4001"
    AUTH_PROVIDER_ERROR = "E4002"
    AI_PROVIDER_ERROR = "E4003"
    EXTERNAL_SERVICE_TIMEOUT = "E4004"

    # === Internal (E5xxx) ===
    UNEXPECTED_ERROR = "E5001"
    CONFIGURATION_ERROR = "E5002"
    STATE_ERROR = "E5003"
