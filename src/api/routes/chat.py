from fastapi import APIRouter, Request

from src.schemas.chat import RequestUser, ResponseUser

router = APIRouter(prefix="/api")


@router.post("/chat", response_model=ResponseUser)
async def generate_text(payload: RequestUser, request: Request):
    return await request.app.state.service.process_request(payload)


@router.get("/health")
async def health():
    """Liveness only; does not imply that a model is installed or loaded."""
    return {"status": "ok"}
