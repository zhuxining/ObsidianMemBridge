class MemBridgeError(Exception):
    """Base exception for MemBridge."""


class ValidationError(MemBridgeError):
    """Raised when input fails validation."""


class NotFoundError(MemBridgeError):
    """Raised when a memory document is not found."""
