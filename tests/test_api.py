import asyncio
import json
import unittest
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

from src.application import create_app
from src.core.config import Settings
from src.core.errors import AppError
from src.schemas.chat import RequestUser
from src.services.chat import ServiceAura
from src.middleware.security import LocalSecurityMiddleware

TOKEN = "test-only-" + "a" * 40
AUTH = {"Authorization": f"Bearer {TOKEN}"}
LOCAL_METADATA = {"model_info": {"general.parameter_count": 8000000000}}


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.response = httpx.Response(200, json={"message": {"content": "Olá!"}})
        self.metadata = LOCAL_METADATA

        def backend(request):
            self.calls.append(request)
            if request.url.path == "/api/show":
                return httpx.Response(200, json=self.metadata)
            return self.response

        self.client = TestClient(
            create_app(Settings(api_token=TOKEN), transport=httpx.MockTransport(backend)),
            base_url="http://127.0.0.1:8000",
        )
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)

    def chat(self, body, **kwargs):
        return self.client.post("/api/chat", json=body, headers=AUTH, **kwargs)

    def test_chat_contract_and_local_destination(self):
        result = self.chat({"msg": "Olá!"})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json(), {"result": "Olá!"})
        self.assertEqual(result.headers["cache-control"], "no-store")
        request = self.calls[-1]
        self.assertEqual(str(request.url), "http://127.0.0.1:11434/api/chat")
        data = json.loads(request.content)
        self.assertEqual(data["options"]["num_predict"], 512)
        self.assertNotIn("authorization", request.headers)

    def test_authentication_before_inference(self):
        for headers in ({}, {"Authorization": "Bearer wrong"}):
            response = self.client.post("/api/chat", json={"msg": "secret"}, headers=headers)
            self.assertEqual(response.status_code, 401)
        self.assertEqual(self.calls, [])

    def test_browser_origin_and_rebinding_rejected(self):
        for header, value, status in (("Origin", "https://evil.example", 403),
                                      ("Host", "evil.example", 400)):
            response = self.client.post("/api/chat", json={"msg": "secret"},
                                        headers={**AUTH, header: value})
            self.assertEqual(response.status_code, status)
        self.assertEqual(self.calls, [])

    def test_validation_does_not_echo_private_input(self):
        for body in ({"msg": " "}, {"msg": "x" * 8001},
                     {"msg": "secret", "extra": "private"}, {"msg": 123}):
            response = self.chat(body)
            self.assertEqual(response.status_code, 422)
            self.assertNotIn("secret", response.text)
            self.assertNotIn("private", response.text)
        self.assertEqual(self.calls, [])

    def test_size_and_content_type(self):
        response = self.client.post("/api/chat", content=b"x" * 65537,
                                    headers={**AUTH, "Content-Type": "application/json"})
        self.assertEqual(response.status_code, 413)
        response = self.client.post("/api/chat", content="secret", headers=AUTH)
        self.assertEqual(response.status_code, 415)
        self.assertEqual(self.calls, [])

    def test_chunked_body_limit(self):
        response = self.client.post("/api/chat", content=iter([b"x" * 40000] * 2),
                                    headers={**AUTH, "Content-Type": "application/json"})
        self.assertEqual(response.status_code, 413)
        self.assertEqual(self.calls, [])

    def test_model_cannot_be_overridden(self):
        self.assertEqual(self.chat({"msg": "hello", "model_name": "other"}).status_code, 400)
        self.assertEqual(self.calls, [])

    def test_cloud_alias_or_unknown_metadata_never_receives_prompt(self):
        for metadata in ({**LOCAL_METADATA, "remote_model": "remote"},
                         {**LOCAL_METADATA, "remote_host": "https://example.com"}, {},
                         {"model_info": {"general.parameter_count": 0}}):
            self.metadata = metadata
            self.calls.clear()
            self.assertEqual(self.chat({"msg": "private prompt"}).status_code, 503)
            self.assertEqual(len(self.calls), 1)
            self.assertEqual(self.calls[0].url.path, "/api/show")
            self.assertNotIn(b"private prompt", self.calls[0].content)

    def test_backend_errors_are_sanitized(self):
        for status, expected in ((404, 503), (500, 502), (302, 502)):
            self.response = httpx.Response(status, text="private backend error",
                                           headers={"Location": "https://example.com"})
            response = self.chat({"msg": "secret"})
            self.assertEqual(response.status_code, expected)
            self.assertNotIn("private", response.text)
            self.assertNotIn("secret", response.text)

    def test_invalid_backend_response(self):
        for content in (b"not json", b'{}', b'{"message":{"content":42}}', b"x" * 262145):
            self.response = httpx.Response(200, content=content)
            self.assertEqual(self.chat({"msg": "hello"}).status_code, 502)

    def test_no_history_between_requests(self):
        self.chat({"msg": "first private prompt"})
        self.chat({"msg": "second prompt"})
        data = json.loads(self.calls[-1].content)
        self.assertEqual(data["messages"], [{"role": "user", "content": "second prompt"}])

    def test_health_requires_auth_and_docs_are_disabled(self):
        self.assertEqual(self.client.get("/api/health").status_code, 401)
        self.assertEqual(self.client.get("/api/health", headers=AUTH).json(), {"status": "ok"})
        self.assertEqual(self.client.get("/docs", headers=AUTH).status_code, 404)


class ConfigurationTests(unittest.TestCase):
    def test_fail_closed_without_token(self):
        with patch.dict("os.environ", {}, clear=True), self.assertRaises(ValueError):
            create_app()

    def test_reject_cloud_models_and_bad_tokens(self):
        for model in ("model:cloud", "https://remote/cloud"):
            with self.assertRaises(ValueError):
                Settings(api_token=TOKEN, model_name=model)
        for token in ("", "short", "ç" * 40, " " * 40):
            with self.assertRaises(ValueError):
                Settings(api_token=token)
        self.assertNotIn(TOKEN, repr(Settings(api_token=TOKEN)))


class ServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_wall_clock_timeout_and_cancellation_release_capacity(self):
        started = asyncio.Event()

        async def backend(request):
            started.set()
            await asyncio.Event().wait()

        async with httpx.AsyncClient(base_url="http://127.0.0.1:11434", transport=httpx.MockTransport(backend)) as client:
            service = ServiceAura(client, Settings(api_token=TOKEN, timeout_seconds=1))
            with self.assertRaises(AppError) as caught:
                await service.process_request(RequestUser(msg="hello"))
            self.assertEqual(caught.exception.status_code, 504)
            self.assertFalse(service._busy)
            started.clear()
            pending = asyncio.create_task(service.process_request(RequestUser(msg="hello")))
            await started.wait()
            pending.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await pending
            self.assertFalse(service._busy)

    async def test_busy_and_recovery(self):
        started, release = asyncio.Event(), asyncio.Event()

        async def backend(request):
            if request.url.path == "/api/show":
                return httpx.Response(200, json=LOCAL_METADATA)
            started.set()
            await release.wait()
            return httpx.Response(200, json={"message": {"content": "ok"}})

        async with httpx.AsyncClient(base_url="http://127.0.0.1:11434", transport=httpx.MockTransport(backend)) as client:
            service = ServiceAura(client, Settings(api_token=TOKEN))
            pending = asyncio.create_task(service.process_request(RequestUser(msg="hello")))
            await started.wait()
            try:
                with self.assertRaises(AppError) as caught:
                    await service.process_request(RequestUser(msg="hello"))
                self.assertEqual(caught.exception.status_code, 429)
            finally:
                release.set()
                await pending
            self.assertEqual((await service.process_request(RequestUser(msg="again"))).result, "ok")

    async def test_connection_and_timeout_errors_release_capacity(self):
        for error, status in ((httpx.ConnectError("secret"), 503),
                              (httpx.ReadTimeout("secret"), 504)):
            def backend(request):
                raise error

            async with httpx.AsyncClient(base_url="http://127.0.0.1:11434", transport=httpx.MockTransport(backend)) as client:
                service = ServiceAura(client, Settings(api_token=TOKEN))
                for _ in range(2):
                    with self.assertRaises(AppError) as caught:
                        await service.process_request(RequestUser(msg="hello"))
                    self.assertEqual(caught.exception.status_code, status)
                    self.assertNotIn("secret", str(caught.exception))


class StreamingBoundaryTests(unittest.IsolatedAsyncioTestCase):
    async def test_multiple_asgi_chunks_stop_before_application(self):
        events = iter([
            {"type": "http.request", "body": b"x" * 40000, "more_body": True},
            {"type": "http.request", "body": b"x" * 40000, "more_body": True},
        ])
        sent = []

        async def receive():
            return next(events)

        async def send(event):
            sent.append(event)

        async def downstream(scope, receive, send):
            self.fail("Oversized body reached the application")

        middleware = LocalSecurityMiddleware(downstream, Settings(api_token=TOKEN))
        await middleware({"type": "http", "method": "POST", "headers": [
            (b"host", b"127.0.0.1"),
            (b"authorization", f"Bearer {TOKEN}".encode()),
            (b"content-type", b"application/json"),
        ]}, receive, send)
        self.assertEqual(sent[0]["status"], 413)


if __name__ == "__main__":
    unittest.main()
