"""Bounded transport for the local Ollama API."""

import json

import httpx

from src.core.errors import AppError


class OllamaClient:
    def __init__(self, client: httpx.AsyncClient):
        self.client = client

    async def post(self, path: str, payload: dict) -> dict:
        async with self.client.stream("POST", path, json=payload) as response:
            response.raise_for_status()
            body = bytearray()
            async for chunk in response.aiter_bytes():
                body.extend(chunk)
                if len(body) > 262144:
                    raise AppError("Resposta do motor local excedeu o limite.", 502)
            data = json.loads(body)
            if not isinstance(data, dict):
                raise ValueError("Invalid response")
            return data

    async def require_local_model(self, model: str):
        # Check metadata before sending the prompt, including aliases of cloud models.
        metadata = await self.post("/api/show", {"model": model})
        info = metadata.get("model_info")
        if metadata.get("remote_model") or metadata.get("remote_host"):
            raise AppError("O modelo configurado não é local.")
        count = info.get("general.parameter_count") if isinstance(info, dict) else None
        if not isinstance(count, int) or isinstance(count, bool) or count <= 0:
            raise AppError("Não foi possível confirmar os pesos do modelo local.")
