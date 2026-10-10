"""Ferramenta: execução de comandos shell.

Apenas comandos explicitamente permitidos em AURA_ALLOWED_COMMANDS são aceitos.
Timeout fixo de 10 segundos. Saída truncada a 4 KiB.
"""

from __future__ import annotations

import asyncio
import shlex

from src.agent.tools.registry import Tool

_MAX_OUTPUT_BYTES = 4096
_TIMEOUT_SECONDS = 10


async def _run_shell(command: str, allowed_commands: set[str]) -> str:
    try:
        parts = shlex.split(command)
    except ValueError as exc:
        return f"Erro ao analisar o comando: {exc}"

    if not parts:
        return "Erro: comando vazio."

    base_cmd = parts[0]
    if base_cmd not in allowed_commands:
        allowed_str = ", ".join(sorted(allowed_commands))
        return (
            f"Erro: comando '{base_cmd}' não permitido. "
            f"Comandos aceitos: {allowed_str}"
        )

    try:
        proc = await asyncio.wait_for(
            asyncio.create_subprocess_exec(
                *parts,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            ),
            timeout=_TIMEOUT_SECONDS,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        return f"Erro: comando excedeu o tempo limite de {_TIMEOUT_SECONDS}s."
    except OSError as exc:
        return f"Erro ao executar o comando: {exc}"

    output = stdout.decode("utf-8", errors="replace")
    if len(output) > _MAX_OUTPUT_BYTES:
        output = output[:_MAX_OUTPUT_BYTES] + "\n...(saída truncada)"

    if not output.strip():
        return f"(comando executado sem saída, código de retorno: {proc.returncode})"

    return output


def make_run_shell_tool(allowed_commands: set[str]) -> Tool:
    async def fn(command: str) -> str:
        return await _run_shell(command, allowed_commands)

    return Tool(
        name="run_shell",
        description=(
            "Executa um comando shell e retorna a saída. "
            f"Apenas os seguintes comandos são permitidos: {', '.join(sorted(allowed_commands))}. "
            "Use para listar diretórios, verificar arquivos, etc."
        ),
        parameters={
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Comando a executar (ex: 'ls -la', 'cat arquivo.txt').",
                }
            },
            "required": ["command"],
        },
        fn=fn,
    )
