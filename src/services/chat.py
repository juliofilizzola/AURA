"""Local inference: no tools, file access, history or automatic downloads."""

import asyncio

import httpx

from src.core.config import Settings
from src.core.errors import AppError, BadRequestError
from src.clients.ollama import OllamaClient
from src.schemas.chat import RequestUser, ResponseUser


class ServiceAura:
    def __init__(self, client: httpx.AsyncClient, settings: Settings):
        self.client = client
        self.backend = OllamaClient(client)
        self.settings = settings
        self._busy = False

    async def process_request(self, request: RequestUser) -> ResponseUser:
        if request.model_name not in (None, self.settings.model_name):
            raise BadRequestError("Use o modelo configurado no servidor.")
        # No waiting queue; one generation at a time per process.
        if self._busy:
            raise AppError("IA ocupada. Tente novamente em instantes.", 429)
        self._busy = True
        try:
            async with asyncio.timeout(self.settings.timeout_seconds):
                await self.backend.require_local_model(self.settings.model_name)
                data = await self.backend.post(
                    "/api/chat", {
                        "model": self.settings.model_name,
                        "messages": [{"role": "user", "content": request.msg}],
                        "stream": False,
                        "options": {"num_predict": 512, "num_ctx": 4096},
                        "keep_alive": "5m",
                    },
                )
                content = data["message"]["content"]
                if not isinstance(content, str) or not content.strip():
                    raise ValueError("Invalid response")
                return ResponseUser(result=content)
        except (TimeoutError, httpx.TimeoutException):
            raise AppError("O motor local excedeu o tempo limite.", 504) from None
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise AppError("Modelo local não encontrado. Instale o modelo configurado.") from None
            raise AppError("O motor local não pôde gerar a resposta.", 502) from None
        except httpx.RequestError:
            raise AppError("Ollama indisponível. Verifique o serviço local.") from None
        except (ValueError, KeyError, TypeError):
            raise AppError("Resposta inválida do motor local.", 502) from None
        finally:
            self._busy = False
