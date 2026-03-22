"""Custom exception hierarchy for Lens Studio CLI."""


class LSCLIError(Exception):
    """Base exception for all Lens Studio CLI errors."""


class ProjectNotFoundError(LSCLIError):
    """Raised when a project file or directory does not exist."""


class ProjectExistsError(LSCLIError):
    """Raised when attempting to create a project that already exists."""


class InvalidProjectNameError(LSCLIError):
    """Raised when a project name contains invalid characters or is empty."""


class InvalidTemplateError(LSCLIError):
    """Raised when an unknown template is specified."""


class LensStudioNotFoundError(LSCLIError):
    """Raised when the Lens Studio application cannot be found."""


class ValidationError(LSCLIError):
    """Raised for general input validation failures."""


class BuildError(LSCLIError):
    """Raised when a lens build or export fails."""
