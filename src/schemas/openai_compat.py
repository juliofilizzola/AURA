"""Schemas compatíveis com o formato OpenAI Chat Completions API (não streaming).

O subconjunto implementado é o mínimo necessário para que ferramentas como
Continue.dev, OpenWebUI e clientes genéricos reconheçam a Aura como um
backend OpenAI-compatible. Campos extras enviados pelo cliente são ignorados
(extra='ignore') para não bloquear integrações que incluam campos opcionais.

Apenas a última mensagem com role='user' é encaminhada ao modelo; a Aura não
mantém histórico nem contexto entre chamadas.
"""

from __future__ import annotations

import time
import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Entrada
# ---------------------------------------------------------------------------

class OpenAIMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=0, max_length=8000)


class OpenAIChatRequest(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    model: str = Field(min_length=1, max_length=128)
    messages: list[OpenAIMessage] = Field(min_length=1, max_length=64)
    # stream=True não é suportado; o campo é aceito apenas para não rejeitar
    # clientes que o enviam por padrão — a resposta sempre será não-streaming.
    stream: bool = False


# ---------------------------------------------------------------------------
# Saída — espelha o formato openai.types.chat.ChatCompletion
# ---------------------------------------------------------------------------

class OpenAIMessageOut(BaseModel):
    role: Literal["assistant"] = "assistant"
    content: str


class OpenAIChoice(BaseModel):
    index: int = 0
    message: OpenAIMessageOut
    finish_reason: Literal["stop"] = "stop"


class OpenAIUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class OpenAIChatResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex}")
    object: Literal["chat.completion"] = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: list[OpenAIChoice]
    usage: OpenAIUsage = Field(default_factory=OpenAIUsage)
