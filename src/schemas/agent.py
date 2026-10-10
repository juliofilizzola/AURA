"""Schemas Pydantic para as rotas de agente (/api/agent).

Separados dos schemas de chat simples para manter clareza e
permitir evolução independente do contrato de agente.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class AgentRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    msg: str = Field(min_length=1, max_length=8000)
    session_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
        description=(
            "Identificador de sessão para histórico in-memory. "
            "Se omitido, a chamada é stateless (sem memória)."
        ),
    )
    model_name: str | None = Field(default=None, max_length=128)


class AgentResponse(BaseModel):
    result: str
    tools_called: list[str] = Field(default_factory=list)
    session_id: str | None = None
