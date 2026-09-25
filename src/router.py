from fastapi import APIRouter
from src.schema import RequestUser, ResponseUser
from src.service import ServiceAura

router = APIRouter()
service = ServiceAura(model_name="llama3")
@router.post("/generate", response_model=ResponseUser)
def generate_text(request: RequestUser):
    return service.process_request(request)