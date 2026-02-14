import asyncio
from types import SimpleNamespace

import pytest

from open_webui.utils.scheduler import (
    build_webui_url,
    get_webui_base_url,
    send_ntfy_notification,
)


class _DummySettings:
    def __init__(self, payload):
        self._payload = payload

    def model_dump(self):
        return self._payload


class _DummyResponse:
    def __init__(self, status=200):
        self.status = status

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def text(self):
        return ""


def _build_app(webui_url):
    return SimpleNamespace(
        state=SimpleNamespace(config=SimpleNamespace(WEBUI_URL=webui_url))
    )


def test_get_webui_base_url_normalizes_trailing_slash():
    app = _build_app("https://owui.example.com/")

    assert get_webui_base_url(app) == "https://owui.example.com"


def test_build_webui_url_supports_relative_path_without_leading_slash():
    app = _build_app("https://owui.example.com")

    assert build_webui_url(app, "workspace/scheduled-prompts") == (
        "https://owui.example.com/workspace/scheduled-prompts"
    )


def test_build_webui_url_returns_none_when_webui_url_missing():
    app = _build_app("")

    assert get_webui_base_url(app) is None
    assert build_webui_url(app, "/c/abc") is None


def test_send_ntfy_notification_sets_click_header_and_body_link(monkeypatch):
    captured = {}

    class _DummySession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def post(self, url, headers, data, timeout):
            captured["url"] = url
            captured["headers"] = headers
            captured["data"] = data
            captured["timeout"] = timeout
            return _DummyResponse(status=200)

    monkeypatch.setattr("open_webui.utils.scheduler.aiohttp.ClientSession", _DummySession)

    user = SimpleNamespace(
        id="u1",
        settings=_DummySettings(
            {
                "ui": {
                    "notifications": {
                        "ntfy": {
                            "enabled": True,
                            "server_url": "https://ntfy.sh",
                            "topic": "my-topic",
                            "token": "secret-token",
                        }
                    }
                }
            }
        ),
    )

    asyncio.run(
        send_ntfy_notification(
            user,
            {
                "status": "success",
                "title": "Scheduled prompt completed",
                "message": "Prompt ran successfully",
                "chat_url": "https://owui.example.com/c/chat-123",
            },
        )
    )

    assert captured["url"] == "https://ntfy.sh/my-topic"
    assert captured["headers"]["Click"] == "https://owui.example.com/c/chat-123"
    assert captured["headers"]["Authorization"] == "Bearer secret-token"
    assert b"Prompt ran successfully" in captured["data"]
    assert b"https://owui.example.com/c/chat-123" in captured["data"]
