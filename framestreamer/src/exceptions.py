"""Module containing all application specific exceptions"""


class EncodingError(Exception):
    """Raised in relation to image/video encoding errors."""


class InvalidConfigurationError(Exception):
    """Raised when the configuration file can't be parsed."""

class CameraStreamError(Exception):
    """Raised when something unrecoverable happens to a camera stream."""
