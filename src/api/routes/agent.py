"""Rota /api/agent — endpoint nativo com tool calling e memória de sessão.

Requer AURA_AGENT_ENABLED=true para estar ativa.
As ferramentas individuais são ativadas por suas respectivas variáveis.
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from src.schemas.agent import AgentRequest, AgentResponse
from src.core.errors import BadRequestError

router = APIRouter(prefix="/api")


@router.post("/agent", response_model=AgentResponse)
async def agent_chat(payload: AgentRequest, request: Request):
    """Endpoint de agente com tool calling e histórico de sessão opcional."""
    service = getattr(request.app.state, "agent_service", None)
    if service is None:
        return JSONResponse(
            {"detail": "Agente não habilitado. Defina AURA_AGENT_ENABLED=true."},
            status_code=503,
        )

    if payload.model_name not in (None, request.app.state.settings.model_name):
        raise BadRequestError("Use o modelo configurado no servidor.")

    result, tools_called = await service.run(
        user_message=payload.msg,
        session_id=payload.session_id,
    )

    return AgentResponse(
        result=result,
        tools_called=tools_called,
        session_id=payload.session_id,
    )


@router.delete("/agent/session/{session_id}")
async def clear_session(session_id: str, request: Request):
    """Remove o histórico de uma sessão da memória."""
    store = getattr(request.app.state, "session_store", None)
    if store is None:
        return JSONResponse(
            {"detail": "Agente não habilitado."},
            status_code=503,
        )
    store.clear(session_id)
    return {"detail": f"Sessão '{session_id}' removida."}
