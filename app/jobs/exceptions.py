class JobException(Exception):
    """Base exception for all Job-related errors."""

    pass


class QueueConnectionError(JobException):
    """Raised when the Queue Adapter fails to connect to the broker."""

    pass


class JobExecutionError(JobException):
    """Raised when a task fails during execution in the worker."""

    pass
