"""Errors safe to expose at the API boundary."""


class AppError(Exception):
    def __init__(self, message: str, status_code: int = 503):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class BadRequestError(AppError):
    def __init__(self, message: str = "Solicitação inválida."):
        super().__init__(message, 400)
