"""
Item Manager Exceptions

Modul-spezifische Errors.
"""
from infrastructure.errors import NotFoundError, ValidationError
from infrastructure.errors.codes import ErrorCodes


class ItemNotFoundError(NotFoundError):
    """Item not found"""
    code = ErrorCodes.ITEM_NOT_FOUND
    message = "Item not found"


class ItemValidationError(ValidationError):
    """Item validation failed"""
    code = ErrorCodes.INVALID_INPUT
    message = "Item validation failed"
