"""Registro centralizado de ferramentas disponíveis ao agente.

Cada ferramenta é um callable assíncrono com a assinatura:
    async def tool_fn(**kwargs) -> str

O registro expõe a lista de ferramentas no formato de schema JSON
usado na instrução de sistema enviada ao modelo.
"""

from __future__ import annotations

import json
from typing import Any, Callable, Coroutine


ToolFn = Callable[..., Coroutine[Any, Any, str]]


class Tool:
    def __init__(
        self,
        name: str,
        description: str,
        parameters: dict,
        fn: ToolFn,
    ):
        self.name = name
        self.description = description
        self.parameters = parameters
        self._fn = fn

    async def call(self, **kwargs: Any) -> str:
        return await self._fn(**kwargs)

    def schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def all_schemas(self) -> list[dict]:
        return [t.schema() for t in self._tools.values()]

    def system_prompt_section(self) -> str:
        """Gera a seção de instrução de sistema que descreve as ferramentas ao modelo."""
        if not self._tools:
            return ""
        schemas_json = json.dumps(self.all_schemas(), ensure_ascii=False, indent=2)
        return (
            "Você tem acesso às seguintes ferramentas. Para usá-las, responda "
            "EXCLUSIVAMENTE com um bloco JSON no formato abaixo, sem texto adicional:\n\n"
            '{"tool": "<nome>", "args": {<argumentos>}}\n\n'
            "Ferramentas disponíveis:\n"
            f"{schemas_json}\n\n"
            "Quando tiver a informação necessária, responda normalmente ao usuário "
            "sem usar o bloco JSON. Nunca invente resultados de ferramentas."
        )
