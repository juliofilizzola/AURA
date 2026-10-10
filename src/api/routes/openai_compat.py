"""Rota /v1/chat/completions — compatível com o formato OpenAI Chat Completions.

Esta rota permite usar a Aura como backend em ferramentas que suportam
endpoints OpenAI-compatible (Continue.dev, OpenWebUI, etc.).

Diferenças em relação à rota nativa /api/chat:
- Aceita o formato de mensagens OpenAI (lista de {role, content}).
- Devolve o formato OpenAI (choices, usage, id, created, object).
- O campo `model` do corpo é validado contra AURA_MODEL, assim como em /api/chat.
- Apenas a última mensagem com role='user' é enviada ao motor local.
  A Aura não mantém histórico; mensagens anteriores são descartadas.
- stream=True é aceito no corpo mas ignorado; a resposta é sempre síncrona.
- As mesmas garantias de segurança da rota nativa se aplicam: token obrigatório,
  somente loopback, um pedido por vez e verificação de modelo local.
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from src.schemas.chat import RequestUser
from src.schemas.openai_compat import (
    OpenAIChatRequest,
    OpenAIChatResponse,
    OpenAIChoice,
    OpenAIMessageOut,
)

router = APIRouter(prefix="/v1")


@router.post("/chat/completions", response_model=OpenAIChatResponse)
async def openai_chat_completions(payload: OpenAIChatRequest, request: Request):
    # Extrai a última mensagem com role='user'. Mensagens anteriores (system,
    # assistant) são descartadas: a Aura não suporta histórico de conversa.
    user_messages = [m for m in payload.messages if m.role == "user"]
    if not user_messages:
        return JSONResponse(
            {"detail": "Nenhuma mensagem com role='user' encontrada."},
            status_code=422,
        )

    last_user_msg = user_messages[-1].content
    if not last_user_msg.strip():
        return JSONResponse(
            {"detail": "A mensagem do usuário não pode estar vazia."},
            status_code=422,
        )

    native_request = RequestUser(msg=last_user_msg, model_name=payload.model)
    result = await request.app.state.service.process_request(native_request)

    return OpenAIChatResponse(
        model=payload.model,
        choices=[
            OpenAIChoice(message=OpenAIMessageOut(content=result.result))
        ],
    )
