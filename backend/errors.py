class ServiceError(Exception):
    """A deliberately sanitized message that can be shown to the user."""

    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code
