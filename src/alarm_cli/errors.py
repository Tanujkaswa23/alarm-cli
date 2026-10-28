class AlarmError(Exception):
    """Base class for expected, user-facing errors."""


class ValidationError(AlarmError):
    """Invalid user input; the prompt should be asked again."""


class Cancelled(AlarmError):
    """The user cancelled the current action."""
