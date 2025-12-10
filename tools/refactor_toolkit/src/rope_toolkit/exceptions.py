"""Custom exceptions."""


class RopeToolkitException(Exception):
    """Base exception for rope toolkit."""
    pass


class IndexException(RopeToolkitException):
    """Exception during indexing."""
    pass


class ServiceException(RopeToolkitException):
    """Exception in service layer."""
    pass


class StorageException(RopeToolkitException):
    """Exception in storage layer."""
    pass


class OperationException(RopeToolkitException):
    """Exception in refactoring operation."""
    pass


class ConfigException(RopeToolkitException):
    """Exception in configuration."""
    pass
