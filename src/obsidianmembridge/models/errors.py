class MemBridgeError(Exception):
    """Base exception for ObsidianMemBridge."""


class ValidationError(MemBridgeError):
    """Raised when input fails validation."""


class NotFoundError(MemBridgeError):
    """Raised when a memory document is not found."""
