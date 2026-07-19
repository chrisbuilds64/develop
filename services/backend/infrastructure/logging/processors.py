"""
Custom Logging Processors

Processors for sensitive data filtering and additional context.
"""
import re
from typing import Any, Dict


def mask_sensitive_data(logger, method_name, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mask sensitive data in log events.

    Masks:
    - Passwords (any field containing 'password')
    - Tokens (any field containing 'token', 'api_key', 'secret')
    - Credit cards (any field containing 'card', 'cc')
    - Email addresses (partially masked)

    Args:
        logger: Logger instance
        method_name: Name of the logging method called
        event_dict: Event dictionary to process

    Returns:
        Modified event dictionary with sensitive data masked
    """
    # Fields to completely mask
    sensitive_keys = {
        'password', 'passwd', 'pwd',
        'token', 'access_token', 'refresh_token', 'auth_token',
        'api_key', 'apikey', 'secret', 'secret_key',
        'credit_card', 'card_number', 'cc', 'cvv', 'cvc',
        'ssn', 'social_security',
    }

    # Fields to partially mask (show first 4 chars)
    partial_mask_keys = {
        'email', 'phone', 'mobile',
    }

    for key, value in event_dict.items():
        if not isinstance(value, str):
            continue

        key_lower = key.lower()

        # Complete masking
        if any(sensitive in key_lower for sensitive in sensitive_keys):
            event_dict[key] = "***REDACTED***"

        # Partial masking (show first 4 chars)
        elif any(partial in key_lower for partial in partial_mask_keys):
            if len(value) > 4:
                event_dict[key] = value[:4] + "***"
            else:
                event_dict[key] = "***"

        # Detect and mask email patterns in strings
        elif '@' in value and '.' in value:
            event_dict[key] = _mask_email(value)

        # Detect and mask token-like patterns (long alphanumeric strings)
        elif _looks_like_token(value):
            if len(value) > 8:
                event_dict[key] = value[:4] + "..." + value[-4:]
            else:
                event_dict[key] = "***REDACTED***"

    return event_dict


def _mask_email(email: str) -> str:
    """
    Partially mask email address.

    Example: user@example.com -> u***@example.com
    """
    if '@' not in email:
        return email

    try:
        local, domain = email.split('@', 1)
        if len(local) > 1:
            masked_local = local[0] + '***'
        else:
            masked_local = '***'
        return f"{masked_local}@{domain}"
    except Exception:
        return "***@***.***"


def _looks_like_token(value: str) -> bool:
    """
    Detect if a string looks like a token/API key.

    Heuristics:
    - Length > 32 characters
    - Contains mix of letters and numbers
    - No spaces
    - All alphanumeric (plus dashes/underscores)
    """
    if len(value) < 32:
        return False

    if ' ' in value:
        return False

    # Check if it's mostly alphanumeric
    alphanumeric = sum(c.isalnum() for c in value)
    if alphanumeric / len(value) < 0.8:
        return False

    # Check for mix of letters and numbers
    has_letter = any(c.isalpha() for c in value)
    has_digit = any(c.isdigit() for c in value)

    return has_letter and has_digit


def add_app_context(logger, method_name, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add application-level context to log events.

    Adds:
    - app_name: Application name
    - environment: Current environment

    Args:
        logger: Logger instance
        method_name: Name of the logging method called
        event_dict: Event dictionary to process

    Returns:
        Modified event dictionary with app context
    """
    import os

    # Only add if not already present
    if 'app_name' not in event_dict:
        event_dict['app_name'] = 'chrisbuilds64-api'

    # Add environment if not present (and not in contextvars)
    if 'environment' not in event_dict:
        env = os.getenv('ENVIRONMENT', 'development')
        event_dict['environment'] = env

    return event_dict


def add_git_commit(logger, method_name, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add git commit SHA to log events (useful for production debugging).

    Reads from GIT_COMMIT environment variable (set during build).

    Args:
        logger: Logger instance
        method_name: Name of the logging method called
        event_dict: Event dictionary to process

    Returns:
        Modified event dictionary with git commit (if available)
    """
    import os

    git_commit = os.getenv('GIT_COMMIT')
    if git_commit and 'git_commit' not in event_dict:
        # Show first 8 chars of commit SHA
        event_dict['git_commit'] = git_commit[:8] if len(git_commit) > 8 else git_commit

    return event_dict


def censor_sql_passwords(logger, method_name, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Censor passwords in SQL connection strings.

    Example:
      postgresql://user:password@localhost/db
      -> postgresql://user:***@localhost/db

    Args:
        logger: Logger instance
        method_name: Name of the logging method called
        event_dict: Event dictionary to process

    Returns:
        Modified event dictionary with censored SQL strings
    """
    sql_pattern = re.compile(
        r'((?:postgresql|mysql|mariadb|sqlite)://[^:]+:)([^@]+)(@.+)'
    )

    for key, value in event_dict.items():
        if isinstance(value, str):
            # Check if it looks like a database URL
            if '://' in value and '@' in value:
                event_dict[key] = sql_pattern.sub(r'\1***\3', value)

    return event_dict


# Example: User-specific processor (for future auth integration)
def add_user_context(logger, method_name, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add user context from contextvars (after authentication).

    This is a placeholder for future authentication integration.
    Currently does nothing (no auth system implemented yet).

    Args:
        logger: Logger instance
        method_name: Name of the logging method called
        event_dict: Event dictionary to process

    Returns:
        Event dictionary (unchanged for now)
    """
    # TODO: Implement when auth system is ready
    # from infrastructure.logging.context import get_user_id
    # user_id = get_user_id()
    # if user_id and 'user_id' not in event_dict:
    #     event_dict['user_id'] = user_id

    return event_dict
