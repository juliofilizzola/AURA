from abc import abstractmethod, ABC

class AppError(Exception):
    def __init__(self, message: str):
        self.message = message

    @property
    @abstractmethod
    def _status_code(self) -> int:
        pass

    @property
    @abstractmethod
    def _message(self) -> str:  # pragma: no cover
        pass

    @classmethod
    def message(cls: type["AppError"]) -> str:
        return str(cls._message)

    @classmethod
    def status_code(cls: type["AppError"]) -> int:
        return int(cls._status_code.__str__())

    @classmethod
    def to_json(cls: type["AppError"]) -> dict[str, str]:
        return {"message": cls.message()}


class BadRequestError(AppError):
    _status_code: int = 400
    _message: str = "Bad request"