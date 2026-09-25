from pydantic import BaseModel

class RequestUser(BaseModel):
    msg: str
    model_name: str = "llama3"

class ResponseUser(BaseModel):
    result: str
