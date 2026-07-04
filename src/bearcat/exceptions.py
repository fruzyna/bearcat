"""Contains exceptions defined by the module."""


class CommandNotFound(Exception):
    """Exception raised when a command returns an error."""
    pass


class CommandInvalid(Exception):
    """Exception raised when a command used an invalid set of parameters or requires program mode."""
    pass


class UnexpectedResultError(Exception):
    """Exception raised when a command does not return an expected result."""
    pass


class InsufficientPermissionsError(Exception):
    """Exception raised when the user does not have permission to access the scanner."""
    pass


class UnsupportedModel(Exception):
    """Exception raised when the detected scanner does not report a supported model number."""
    pass

class ScannerNotFound(Exception):
    """Exception raise when a scanner cannot be detected."""
    pass
