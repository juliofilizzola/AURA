"""Ferramenta: leitura de arquivo local.

Acesso restrito ao diretório definido em AURA_WORKSPACE_DIR.
Somente extensões seguras são permitidas (texto plano).
"""

from __future__ import annotations

import os
from pathlib import Path

from src.agent.tools.registry import Tool

# Extensões de arquivo permitidas para leitura
_ALLOWED_EXTENSIONS = {
    ".txt", ".md", ".py", ".js", ".ts", ".json", ".yaml", ".yml",
    ".toml", ".cfg", ".ini", ".env", ".sh", ".html", ".css", ".csv",
    ".rst", ".xml", ".sql", ".log",
}

_MAX_FILE_BYTES = 32_768  # 32 KiB


async def _read_file(path: str, workspace_dir: str) -> str:
    workspace = Path(workspace_dir).resolve()
    target = (workspace / path).resolve()

    # Garante que o caminho resolvido está dentro do workspace (path traversal)
    if not str(target).startswith(str(workspace)):
        return "Erro: acesso negado — o caminho está fora do workspace."

    if not target.exists():
        return f"Erro: arquivo não encontrado: {path}"

    if not target.is_file():
        return f"Erro: {path} não é um arquivo."

    if target.suffix.lower() not in _ALLOWED_EXTENSIONS:
        return (
            f"Erro: extensão '{target.suffix}' não permitida. "
            f"Extensões aceitas: {', '.join(sorted(_ALLOWED_EXTENSIONS))}"
        )

    size = target.stat().st_size
    if size > _MAX_FILE_BYTES:
        return f"Erro: arquivo muito grande ({size} bytes; limite: {_MAX_FILE_BYTES})."

    try:
        content = target.read_text(encoding="utf-8", errors="replace")
        return content if content.strip() else "(arquivo vazio)"
    except OSError as exc:
        return f"Erro ao ler arquivo: {exc}"


def make_read_file_tool(workspace_dir: str) -> Tool:
    async def fn(path: str) -> str:
        return await _read_file(path, workspace_dir)

    return Tool(
        name="read_file",
        description=(
            "Lê o conteúdo de um arquivo de texto dentro do workspace local. "
            "Use caminhos relativos ao workspace (ex: 'README.md', 'src/main.py')."
        ),
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Caminho relativo do arquivo dentro do workspace.",
                }
            },
            "required": ["path"],
        },
        fn=fn,
    )
