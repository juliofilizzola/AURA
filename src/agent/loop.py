"""Loop agentic: envia prompt → detecta chamada de ferramenta → executa → repete.

O modelo sinaliza o uso de uma ferramenta respondendo com um bloco JSON:
    {"tool": "<nome>", "args": {<argumentos>}}

O loop repete até:
  - O modelo responder sem um bloco de ferramenta (resposta final).
  - O limite de iterações ser atingido (AURA_MAX_AGENT_LOOPS).
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

from src.agent.tools.registry import ToolRegistry
from src.memory.session_store import SessionStore

if TYPE_CHECKING:
    from src.clients.ollama import OllamaClient
    from src.core.config import Settings

# Detecta blocos JSON de chamada de ferramenta na resposta do modelo
_TOOL_CALL_RE = re.compile(
    r'\{\s*"tool"\s*:\s*"[^"]+"\s*,\s*"args"\s*:\s*\{[^}]*\}\s*\}',
    re.DOTALL,
)


def _extract_tool_call(text: str) -> dict | None:
    """Tenta extrair um bloco de chamada de ferramenta do texto."""
    match = _TOOL_CALL_RE.search(text)
    if not match:
        return None
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return None


class AgentLoop:
    def __init__(
        self,
        ollama: "OllamaClient",
        settings: "Settings",
        registry: ToolRegistry,
        session_store: SessionStore,
    ):
        self._ollama = ollama
        self._settings = settings
        self._registry = registry
        self._session_store = session_store

    async def run(
        self,
        user_message: str,
        session_id: str | None,
    ) -> tuple[str, list[str]]:
        """Executa o loop agentic e retorna (resposta_final, ferramentas_chamadas).

        Args:
            user_message: Mensagem do usuário.
            session_id: ID da sessão para histórico. None = sem memória.

        Returns:
            Tupla (resposta, lista_de_ferramentas_usadas).
        """
        tools_called: list[str] = []

        # --- Carrega histórico da sessão ---
        history = (
            self._session_store.get_history(session_id) if session_id else []
        )

        # --- Prepara system prompt com descrição das ferramentas ---
        tool_section = self._registry.system_prompt_section()
        system_messages: list[dict] = []
        if tool_section:
            system_messages = [{"role": "system", "content": tool_section}]

        # --- Adiciona mensagem do usuário ao histórico temporário ---
        messages = system_messages + history + [
            {"role": "user", "content": user_message}
        ]

        max_loops = self._settings.max_agent_loops
        final_response = ""

        for _ in range(max_loops):
            data = await self._ollama.post(
                "/api/chat",
                {
                    "model": self._settings.model_name,
                    "messages": messages,
                    "stream": False,
                    "options": {"num_predict": 512, "num_ctx": 4096},
                    "keep_alive": "5m",
                },
            )
            response_text = data["message"]["content"]
            if not isinstance(response_text, str):
                raise ValueError("Resposta inválida do modelo.")

            # --- Verifica se o modelo quer chamar uma ferramenta ---
            tool_call = _extract_tool_call(response_text)
            if tool_call:
                tool_name = tool_call.get("tool", "")
                tool_args = tool_call.get("args", {})
                tool = self._registry.get(tool_name)

                if tool:
                    tool_result = await tool.call(**tool_args)
                    tools_called.append(tool_name)

                    # Adiciona o resultado como mensagem de "ferramenta" para o próximo loop
                    messages.append({"role": "assistant", "content": response_text})
                    messages.append({
                        "role": "user",
                        "content": (
                            f'[Resultado da ferramenta "{tool_name}"]:\n{tool_result}\n\n'
                            "Agora responda ao usuário com base nessa informação."
                        ),
                    })
                else:
                    # Ferramenta não encontrada — para o loop
                    final_response = (
                        f"[Erro interno: ferramenta '{tool_name}' não disponível.] "
                        + response_text
                    )
                    break
            else:
                # Resposta final do modelo
                final_response = response_text
                break
        else:
            # Limite de loops atingido
            final_response = (
                "Não consegui completar a tarefa dentro do limite de iterações. "
                "Tente uma solicitação mais simples."
            )

        # --- Persiste no histórico da sessão ---
        if session_id:
            self._session_store.append(session_id, "user", user_message)
            self._session_store.append(session_id, "assistant", final_response)

        return final_response, tools_called
