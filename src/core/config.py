"""Explicit configuration; no dotenv auto-loading or remote fallback."""

import os
import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    api_token: str = field(repr=False)
    model_name: str = "llama3"
    timeout_seconds: float = 120.0
    max_body_bytes: int = 65536

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

    @classmethod
    def from_env(cls):
        return cls(
            api_token=os.environ.get("AURA_API_TOKEN", ""),
            model_name=os.environ.get("AURA_MODEL", "llama3"),
        )
