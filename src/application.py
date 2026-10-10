from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.core.config import Settings
from src.core.errors import AppError
from src.api.routes.chat import router
from src.api.routes.openai_compat import router as openai_router
from src.api.routes.agent import router as agent_router
from src.middleware.security import LocalSecurityMiddleware
from src.services.chat import ServiceAura


def create_app(settings: Settings | None = None, *, transport=None) -> FastAPI:
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app):
        # URL base do Ollama. Em execução local o padrão é o loopback fixo.
        # Em container (docker-compose), OLLAMA_BASE_URL=http://ollama:11434.
        import os
        ollama_base_url = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        # Fixed loopback by default; ignore proxies and redirects.
        async with httpx.AsyncClient(
            base_url=ollama_base_url,
            trust_env=False, follow_redirects=False,
            timeout=httpx.Timeout(settings.timeout_seconds, connect=3),
            limits=httpx.Limits(max_connections=1), transport=transport,
        ) as client:
            app.state.settings = settings
            app.state.service = ServiceAura(client, settings)

            # --- Inicialização do agente (opcional) ---
            if settings.agent_enabled:
                from src.agent.tools.registry import ToolRegistry
                from src.agent.tools.eval_python import make_eval_python_tool
                from src.agent.tools.read_file import make_read_file_tool
                from src.agent.tools.run_shell import make_run_shell_tool
                from src.agent.loop import AgentLoop
                from src.memory.session_store import SessionStore

                registry = ToolRegistry()

                # eval_python está sempre disponível quando o agente está ativo
                registry.register(make_eval_python_tool())

                # read_file requer AURA_WORKSPACE_DIR
                if settings.workspace_dir:
                    registry.register(make_read_file_tool(settings.workspace_dir))

                # run_shell requer pelo menos um comando em AURA_ALLOWED_COMMANDS
                if settings.allowed_commands:
                    registry.register(make_run_shell_tool(settings.allowed_commands))

                session_store = SessionStore(
                    ttl_minutes=settings.session_ttl_minutes,
                    max_messages=50,
                )

                from src.clients.ollama import OllamaClient
                app.state.agent_service = AgentLoop(
                    ollama=OllamaClient(client),
                    settings=settings,
                    registry=registry,
                    session_store=session_store,
                )
                app.state.session_store = session_store
            else:
                app.state.agent_service = None
                app.state.session_store = None

            yield


    app = FastAPI(title="Aura local", version="2.0.0", lifespan=lifespan,
                  docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(LocalSecurityMiddleware, settings=settings)
    app.include_router(router)
    app.include_router(openai_router)
    app.include_router(agent_router)

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
