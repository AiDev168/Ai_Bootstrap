"""User-facing errors raised by template and generation services."""


class BootstrapError(Exception):
    """Base class for expected application errors."""


class InvalidProjectNameError(BootstrapError):
    """Raised when a project name is empty or unsafe."""


class TemplateNotFoundError(BootstrapError):
    """Raised when a requested template is not present in the catalog."""


class UnsupportedTemplateError(BootstrapError):
    """Raised when generation is not implemented for a known template."""


class DestinationConflictError(BootstrapError):
    """Raised when the requested project destination already exists."""


class GenerationError(BootstrapError):
    """Raised when project files cannot be created safely."""
