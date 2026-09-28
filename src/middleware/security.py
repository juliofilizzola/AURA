"""Authenticate before reading; bound even chunked request bodies."""

import asyncio
import secrets

from starlette.datastructures import Headers
from starlette.responses import JSONResponse


class LocalSecurityMiddleware:
    def __init__(self, app, settings):
        self.app = app
        self.settings = settings

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = Headers(scope=scope)

        async def reject(status, message):
            await JSONResponse(
                {"detail": message}, status_code=status,
                headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
            )(scope, receive, send)

        # This API accepts local programmatic clients, not browser origins.
        if "origin" in headers or headers.get("sec-fetch-site") == "cross-site":
            await reject(403, "Origem não permitida.")
            return
        host = headers.get("host", "").split(":", 1)[0].lower()
        if host not in {"127.0.0.1", "localhost"}:
            await reject(400, "Host não permitido.")
            return
        expected = f"Bearer {self.settings.api_token}".encode("ascii")
        if not secrets.compare_digest(headers.get("authorization", "").encode("utf-8"), expected):
            await reject(401, "Token de acesso inválido ou ausente.")
            return
        if scope["method"] == "POST" and headers.get("content-type", "").split(";", 1)[0].strip().lower() != "application/json":
            await reject(415, "Use Content-Type: application/json.")
            return
        body = bytearray()
        try:
            async with asyncio.timeout(10):
                while True:
                    event = await receive()
                    if event["type"] == "http.disconnect":
                        return
                    body.extend(event.get("body", b""))
                    if len(body) > self.settings.max_body_bytes:
                        await reject(413, "Solicitação excedeu o limite.")
                        return
                    if not event.get("more_body", False):
                        break
        except TimeoutError:
            await reject(408, "Tempo de envio excedido.")
            return

        delivered = False

        async def bounded_receive():
            nonlocal delivered
            if delivered:
                return await receive()
            delivered = True
            return {"type": "http.request", "body": bytes(body), "more_body": False}

        async def private_send(event):
            if event["type"] == "http.response.start":
                event.setdefault("headers", []).extend([
                    (b"cache-control", b"no-store"),
                    (b"x-content-type-options", b"nosniff"),
                ])
            await send(event)

        await self.app(scope, bounded_receive, private_send)
