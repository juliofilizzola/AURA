from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.core.config import Settings
from src.core.errors import AppError
from src.api.routes.chat import router
from src.middleware.security import LocalSecurityMiddleware
from src.services.chat import ServiceAura


def create_app(settings: Settings | None = None, *, transport=None) -> FastAPI:
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app):
        # Fixed numeric loopback; ignore proxies, OLLAMA_HOST and redirects.
        async with httpx.AsyncClient(
            base_url="http://127.0.0.1:11434",
            trust_env=False, follow_redirects=False,
            timeout=httpx.Timeout(settings.timeout_seconds, connect=3),
            limits=httpx.Limits(max_connections=1), transport=transport,
        ) as client:
            app.state.service = ServiceAura(client, settings)
            yield

    app = FastAPI(title="Aura local", version="2.0.0", lifespan=lifespan,
                  docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(LocalSecurityMiddleware, settings=settings)
    app.include_router(router)

    @app.exception_handler(AppError)
    async def app_error(request: Request, exc: AppError):
        return JSONResponse({"detail": exc.message}, status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        # The default includes rejected input, which may be sensitive.
        return JSONResponse({"detail": "Corpo inválido. Envie msg com 1 a 8000 caracteres."}, status_code=422)

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception):
        return JSONResponse({"detail": "Erro interno."}, status_code=500,
                            headers={"Cache-Control": "no-store"})

    return app
