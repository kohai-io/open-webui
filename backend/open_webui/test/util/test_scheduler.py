import asyncio
from types import SimpleNamespace

from open_webui.utils.scheduler import (
    build_webui_url,
    execute_scheduled_prompt,
    get_webui_base_url,
    send_ntfy_notification,
    truncate_text_for_notification,
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


def test_truncate_text_for_notification():
    short = "hello"
    long = "x" * 600

    assert truncate_text_for_notification(None, max_length=10) == ""
    assert truncate_text_for_notification(short, max_length=10) == short
    assert truncate_text_for_notification(long, max_length=10) == "xxxxxxxxxx..."


def test_send_ntfy_notification_sets_click_header_without_link_in_body(monkeypatch):
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
                "message": "Prompt ran successfully\n\nOutput:\n42",
                "chat_url": "https://owui.example.com/c/chat-123",
                "scheduled_prompts_url": "https://owui.example.com/workspace/scheduled-prompts",
            },
        )
    )

    assert captured["url"] == "https://ntfy.sh/my-topic"
    assert captured["headers"]["Click"] == "https://owui.example.com/c/chat-123"
    assert "Open Chat" in captured["headers"]["Actions"]
    assert "Scheduled Prompts" in captured["headers"]["Actions"]
    assert captured["headers"]["Authorization"] == "Bearer secret-token"
    decoded_body = captured["data"].decode("utf-8")
    assert "Output:" in decoded_body
    assert "https://owui.example.com/c/chat-123" not in decoded_body


def test_execute_scheduled_prompt_filters_prompt_scheduler_and_sets_default_function_calling(
    monkeypatch,
):
    captured = {}

    class _ApiResponse:
        status = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def text(self):
            return ""

        async def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "content": "Your todos are: A, B, C",
                        }
                    }
                ]
            }

    class _DummySession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def post(self, url, headers, json, timeout):
            captured["payload"] = json
            return _ApiResponse()

    monkeypatch.setattr("open_webui.utils.scheduler.aiohttp.ClientSession", _DummySession)
    monkeypatch.setattr("open_webui.utils.scheduler.create_token", lambda **kwargs: "token")
    monkeypatch.setattr(
        "open_webui.utils.scheduler.Users.get_user_by_id",
        lambda _user_id: SimpleNamespace(id="u1", settings=None),
    )
    monkeypatch.setattr(
        "open_webui.utils.scheduler.ScheduledPrompts.update_execution_status",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "open_webui.utils.scheduler.ScheduledPrompts.update_scheduled_prompt_by_id",
        lambda *args, **kwargs: None,
    )

    async def _noop_async(*args, **kwargs):
        return None

    monkeypatch.setattr("open_webui.utils.scheduler.send_user_notification", _noop_async)
    monkeypatch.setattr("open_webui.utils.scheduler.send_ntfy_notification", _noop_async)

    def _insert_new_chat(_user_id, chat_form):
        captured["chat_data"] = chat_form.chat
        return SimpleNamespace(id="chat-1")

    monkeypatch.setattr("open_webui.utils.scheduler.Chats.insert_new_chat", _insert_new_chat)

    app = SimpleNamespace(
        state=SimpleNamespace(
            MODELS={"model-1": {"info": {"meta": {"toolIds": []}}}},
            config=SimpleNamespace(WEBUI_URL=""),
        )
    )

    prompt = SimpleNamespace(
        id="p1",
        name="Todo reminder",
        user_id="u1",
        system_prompt="",
        prompt="What's on my todo list?",
        model_id="model-1",
        tool_ids=["prompt_scheduler", "notes_manager"],
        function_calling_mode="default",
        chat_id=None,
        create_new_chat=True,
        run_once=True,
        cron_expression="* * * * *",
        timezone="UTC",
    )

    result = asyncio.run(execute_scheduled_prompt(app, prompt))

    assert result["success"] is True
    assert captured["payload"]["params"]["function_calling"] == "default"
    assert captured["payload"]["tool_ids"] == ["notes_manager"]
    assert "Use get_note on the relevant note ID" in captured["payload"]["messages"][0]["content"]
    assert captured["chat_data"]["tool_ids"] == ["notes_manager"]


def test_execute_scheduled_prompt_uses_native_mode_when_requested(monkeypatch):
    captured = {}

    class _ApiResponse:
        status = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def text(self):
            return ""

        async def json(self):
            return {"choices": [{"message": {"content": "done"}}]}

    class _DummySession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def post(self, url, headers, json, timeout):
            captured["payload"] = json
            return _ApiResponse()

    monkeypatch.setattr("open_webui.utils.scheduler.aiohttp.ClientSession", _DummySession)
    monkeypatch.setattr("open_webui.utils.scheduler.create_token", lambda **kwargs: "token")
    monkeypatch.setattr(
        "open_webui.utils.scheduler.Users.get_user_by_id",
        lambda _user_id: SimpleNamespace(id="u1", settings=None),
    )
    monkeypatch.setattr(
        "open_webui.utils.scheduler.ScheduledPrompts.update_execution_status",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "open_webui.utils.scheduler.ScheduledPrompts.update_scheduled_prompt_by_id",
        lambda *args, **kwargs: None,
    )

    async def _noop_async(*args, **kwargs):
        return None

    monkeypatch.setattr("open_webui.utils.scheduler.send_user_notification", _noop_async)
    monkeypatch.setattr("open_webui.utils.scheduler.send_ntfy_notification", _noop_async)
    monkeypatch.setattr(
        "open_webui.utils.scheduler.Chats.insert_new_chat",
        lambda _user_id, chat_form: SimpleNamespace(id="chat-1"),
    )

    app = SimpleNamespace(
        state=SimpleNamespace(
            MODELS={"model-1": {"info": {"meta": {"toolIds": []}}}},
            config=SimpleNamespace(WEBUI_URL=""),
        )
    )

    prompt = SimpleNamespace(
        id="p2",
        name="Native reminder",
        user_id="u1",
        system_prompt="",
        prompt="What's on my todo list?",
        model_id="model-1",
        tool_ids=["notes_manager"],
        function_calling_mode="native",
        chat_id=None,
        create_new_chat=True,
        run_once=True,
        cron_expression="* * * * *",
        timezone="UTC",
    )

    asyncio.run(execute_scheduled_prompt(app, prompt))

    assert captured["payload"]["params"]["function_calling"] == "native"


def test_execute_scheduled_prompt_auto_mode_omits_function_calling_param(monkeypatch):
    captured = {}

    class _ApiResponse:
        status = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def text(self):
            return ""

        async def json(self):
            return {"choices": [{"message": {"content": "done"}}]}

    class _DummySession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def post(self, url, headers, json, timeout):
            captured["payload"] = json
            return _ApiResponse()

    monkeypatch.setattr("open_webui.utils.scheduler.aiohttp.ClientSession", _DummySession)
    monkeypatch.setattr("open_webui.utils.scheduler.create_token", lambda **kwargs: "token")
    monkeypatch.setattr(
        "open_webui.utils.scheduler.Users.get_user_by_id",
        lambda _user_id: SimpleNamespace(id="u1", settings=None),
    )
    monkeypatch.setattr(
        "open_webui.utils.scheduler.ScheduledPrompts.update_execution_status",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "open_webui.utils.scheduler.ScheduledPrompts.update_scheduled_prompt_by_id",
        lambda *args, **kwargs: None,
    )

    async def _noop_async(*args, **kwargs):
        return None

    monkeypatch.setattr("open_webui.utils.scheduler.send_user_notification", _noop_async)
    monkeypatch.setattr("open_webui.utils.scheduler.send_ntfy_notification", _noop_async)
    monkeypatch.setattr(
        "open_webui.utils.scheduler.Chats.insert_new_chat",
        lambda _user_id, chat_form: SimpleNamespace(id="chat-1"),
    )

    app = SimpleNamespace(
        state=SimpleNamespace(
            MODELS={"model-1": {"info": {"meta": {"toolIds": []}}}},
            config=SimpleNamespace(WEBUI_URL=""),
        )
    )

    prompt = SimpleNamespace(
        id="p3",
        name="Auto reminder",
        user_id="u1",
        system_prompt="",
        prompt="What's on my todo list?",
        model_id="model-1",
        tool_ids=["notes_manager"],
        function_calling_mode="auto",
        chat_id=None,
        create_new_chat=True,
        run_once=True,
        cron_expression="* * * * *",
        timezone="UTC",
    )

    asyncio.run(execute_scheduled_prompt(app, prompt))

    assert "params" not in captured["payload"]


def test_execute_scheduled_prompt_auto_mode_retries_with_default_when_no_final_text(
    monkeypatch,
):
    captured_payloads = []

    class _ApiResponse:
        def __init__(self, payload):
            self.status = 200
            self._payload = payload

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def text(self):
            return ""

        async def json(self):
            if len(captured_payloads) == 1:
                return {
                    "choices": [
                        {
                            "message": {
                                "content": "",
                                "tool_calls": [{"id": "call_1", "type": "function"}],
                            }
                        }
                    ]
                }
            return {"choices": [{"message": {"content": "Final todo summary"}}]}

    class _DummySession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def post(self, url, headers, json, timeout):
            captured_payloads.append(json)
            return _ApiResponse(json)

    monkeypatch.setattr("open_webui.utils.scheduler.aiohttp.ClientSession", _DummySession)
    monkeypatch.setattr("open_webui.utils.scheduler.create_token", lambda **kwargs: "token")
    monkeypatch.setattr(
        "open_webui.utils.scheduler.Users.get_user_by_id",
        lambda _user_id: SimpleNamespace(id="u1", settings=None),
    )
    monkeypatch.setattr(
        "open_webui.utils.scheduler.ScheduledPrompts.update_execution_status",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "open_webui.utils.scheduler.ScheduledPrompts.update_scheduled_prompt_by_id",
        lambda *args, **kwargs: None,
    )

    async def _noop_async(*args, **kwargs):
        return None

    monkeypatch.setattr("open_webui.utils.scheduler.send_user_notification", _noop_async)
    monkeypatch.setattr("open_webui.utils.scheduler.send_ntfy_notification", _noop_async)
    monkeypatch.setattr(
        "open_webui.utils.scheduler.Chats.insert_new_chat",
        lambda _user_id, chat_form: SimpleNamespace(id="chat-1"),
    )

    app = SimpleNamespace(
        state=SimpleNamespace(
            MODELS={"model-1": {"info": {"meta": {"toolIds": []}}}},
            config=SimpleNamespace(WEBUI_URL=""),
        )
    )

    prompt = SimpleNamespace(
        id="p4",
        name="Auto retry reminder",
        user_id="u1",
        system_prompt="",
        prompt="What's on my todo list?",
        model_id="model-1",
        tool_ids=["notes_manager"],
        function_calling_mode="auto",
        chat_id=None,
        create_new_chat=True,
        run_once=True,
        cron_expression="* * * * *",
        timezone="UTC",
    )

    result = asyncio.run(execute_scheduled_prompt(app, prompt))

    assert result["success"] is True
    assert len(captured_payloads) == 2
    assert "params" not in captured_payloads[0]
    assert captured_payloads[1]["params"]["function_calling"] == "default"


def test_execute_scheduled_prompt_continues_when_model_returns_raw_tool_json(monkeypatch):
    captured_payloads = []

    class _ApiResponse:
        status = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def text(self):
            return ""

        async def json(self):
            if len(captured_payloads) == 1:
                return {
                    "choices": [
                        {
                            "message": {
                                "content": '{"tool":"notes_manager/get_note","params":{"note_id":"n1"}}'
                            }
                        }
                    ]
                }

            return {
                "choices": [
                    {
                        "message": {
                            "content": "Here are your todos: item A, item B",
                        }
                    }
                ]
            }

    class _DummySession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def post(self, url, headers, json, timeout):
            captured_payloads.append(json)
            return _ApiResponse()

    monkeypatch.setattr("open_webui.utils.scheduler.aiohttp.ClientSession", _DummySession)
    monkeypatch.setattr("open_webui.utils.scheduler.create_token", lambda **kwargs: "token")
    monkeypatch.setattr(
        "open_webui.utils.scheduler.Users.get_user_by_id",
        lambda _user_id: SimpleNamespace(id="u1", settings=None),
    )
    monkeypatch.setattr(
        "open_webui.utils.scheduler.ScheduledPrompts.update_execution_status",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "open_webui.utils.scheduler.ScheduledPrompts.update_scheduled_prompt_by_id",
        lambda *args, **kwargs: None,
    )

    async def _noop_async(*args, **kwargs):
        return None

    monkeypatch.setattr("open_webui.utils.scheduler.send_user_notification", _noop_async)
    monkeypatch.setattr("open_webui.utils.scheduler.send_ntfy_notification", _noop_async)
    monkeypatch.setattr(
        "open_webui.utils.scheduler.Chats.insert_new_chat",
        lambda _user_id, chat_form: SimpleNamespace(id="chat-1"),
    )

    app = SimpleNamespace(
        state=SimpleNamespace(
            MODELS={"model-1": {"info": {"meta": {"toolIds": []}}}},
            config=SimpleNamespace(WEBUI_URL=""),
        )
    )

    prompt = SimpleNamespace(
        id="p5",
        name="Tool JSON continuation",
        user_id="u1",
        system_prompt="",
        prompt="What's on my todo list?",
        model_id="model-1",
        tool_ids=["notes_manager"],
        function_calling_mode="default",
        chat_id=None,
        create_new_chat=True,
        run_once=True,
        cron_expression="* * * * *",
        timezone="UTC",
    )

    result = asyncio.run(execute_scheduled_prompt(app, prompt))

    assert result["success"] is True
    assert len(captured_payloads) == 2
    assert captured_payloads[1]["params"]["function_calling"] == "default"
    assert len(captured_payloads[1]["messages"]) == 4
    assert captured_payloads[1]["messages"][-1]["role"] == "user"


def test_execute_scheduled_prompt_forces_generic_continuation_after_malformed_tool_chatter(
    monkeypatch,
):
    captured_payloads = []

    class _ApiResponse:
        status = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def text(self):
            return ""

        async def json(self):
            if len(captured_payloads) == 1:
                return {
                    "choices": [
                        {
                            "message": {
                                "content": "to=notes_manager/get_note part??? Need proper JSON.",
                            }
                        }
                    ],
                }

            return {
                "choices": [
                    {
                        "message": {
                            "content": "Your todo list: 1) Buy milk 2) Call Alex",
                        }
                    }
                ]
            }

    class _DummySession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def post(self, url, headers, json, timeout):
            captured_payloads.append(json)
            return _ApiResponse()

    monkeypatch.setattr("open_webui.utils.scheduler.aiohttp.ClientSession", _DummySession)
    monkeypatch.setattr("open_webui.utils.scheduler.create_token", lambda **kwargs: "token")
    monkeypatch.setattr(
        "open_webui.utils.scheduler.Users.get_user_by_id",
        lambda _user_id: SimpleNamespace(id="u1", settings=None),
    )
    monkeypatch.setattr(
        "open_webui.utils.scheduler.ScheduledPrompts.update_execution_status",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "open_webui.utils.scheduler.ScheduledPrompts.update_scheduled_prompt_by_id",
        lambda *args, **kwargs: None,
    )

    async def _noop_async(*args, **kwargs):
        return None

    monkeypatch.setattr("open_webui.utils.scheduler.send_user_notification", _noop_async)
    monkeypatch.setattr("open_webui.utils.scheduler.send_ntfy_notification", _noop_async)
    monkeypatch.setattr(
        "open_webui.utils.scheduler.Chats.insert_new_chat",
        lambda _user_id, chat_form: SimpleNamespace(id="chat-1"),
    )

    app = SimpleNamespace(
        state=SimpleNamespace(
            MODELS={"model-1": {"info": {"meta": {"toolIds": []}}}},
            config=SimpleNamespace(WEBUI_URL=""),
        )
    )

    prompt = SimpleNamespace(
        id="p6",
        name="Malformed notes chatter",
        user_id="u1",
        system_prompt="",
        prompt="What's on my todo list?",
        model_id="model-1",
        tool_ids=["notes_manager"],
        function_calling_mode="default",
        chat_id=None,
        create_new_chat=True,
        run_once=True,
        cron_expression="* * * * *",
        timezone="UTC",
    )

    result = asyncio.run(execute_scheduled_prompt(app, prompt))

    assert result["success"] is True
    assert len(captured_payloads) == 2
    assert captured_payloads[1]["params"]["function_calling"] == "default"
    assert "Do not output tool-call syntax" in captured_payloads[1]["messages"][-1]["content"]
