"""Business errors shared by every router.

A router raises ApiError; main.py turns it into an ErrorOut response, so the
browser (app.js) only has to understand one error format.
"""


class ApiError(Exception):
    def __init__(self, status_code: int, error_code: str, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
