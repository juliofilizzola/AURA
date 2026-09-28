from pydantic import BaseModel, ConfigDict, Field


class RequestUser(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    msg: str = Field(min_length=1, max_length=8000)
    # Compatibility: callers may name only the configured model.
    model_name: str | None = Field(default=None, min_length=1, max_length=128)


class ResponseUser(BaseModel):
    result: str
