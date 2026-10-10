"""Explicit configuration; carrega .env se presente, sem sobrescrever variáveis já definidas no ambiente."""

import os
import re
from dataclasses import dataclass, field

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    api_token: str = field(repr=False)
    model_name: str = "llama3"
    timeout_seconds: float = 120.0
    max_body_bytes: int = 65536

    # --- Agent settings (opcionais; desabilitados por padrão) ---
    agent_enabled: bool = False
    workspace_dir: str | None = None          # Diretório base para read_file
    allowed_commands: frozenset[str] = field(  # Comandos permitidos para run_shell
        default_factory=frozenset
    )
    session_ttl_minutes: float = 30.0         # TTL de sessões in-memory
    max_agent_loops: int = 5                  # Máximo de iterações por chamada

    def __post_init__(self):
        if len(self.api_token) < 32 or not self.api_token.isascii() or any(
            c.isspace() for c in self.api_token
        ):
            raise ValueError("AURA_API_TOKEN deve conter ao menos 32 caracteres ASCII sem espaços.")
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.:/-]{0,127}", self.model_name):
            raise ValueError("AURA_MODEL inválido.")
        if "cloud" in self.model_name.lower():
            raise ValueError("Modelos cloud não são permitidos.")
        if not 1 <= self.timeout_seconds <= 300:
            raise ValueError("Timeout deve estar entre 1 e 300 segundos.")
        if not 1024 <= self.max_body_bytes <= 65536:
            raise ValueError("Limite de corpo inválido.")
        if not 1 <= self.max_agent_loops <= 20:
            raise ValueError("AURA_MAX_AGENT_LOOPS deve estar entre 1 e 20.")
        if not 1 <= self.session_ttl_minutes <= 1440:
            raise ValueError("AURA_SESSION_TTL_MINUTES deve estar entre 1 e 1440.")

    @classmethod
    def from_env(cls):
        # override=False garante que variáveis já definidas no sistema têm prioridade.
        load_dotenv(override=False)

        # Processa a lista de comandos permitidos
        raw_commands = os.environ.get("AURA_ALLOWED_COMMANDS", "")
        allowed = frozenset(
            c.strip() for c in raw_commands.split(",") if c.strip()
        )

        return cls(
            api_token=os.environ.get("AURA_API_TOKEN", ""),
            model_name=os.environ.get("AURA_MODEL", "llama3"),
            agent_enabled=os.environ.get("AURA_AGENT_ENABLED", "").lower() == "true",
            workspace_dir=os.environ.get("AURA_WORKSPACE_DIR") or None,
            allowed_commands=allowed,
            session_ttl_minutes=float(os.environ.get("AURA_SESSION_TTL_MINUTES", "30")),
            max_agent_loops=int(os.environ.get("AURA_MAX_AGENT_LOOPS", "5")),
        )
