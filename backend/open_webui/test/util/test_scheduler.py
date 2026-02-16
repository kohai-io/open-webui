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
    assert "Do not include tool-call syntax" in captured_payloads[1]["messages"][-1]["content"]


def test_execute_scheduled_prompt_attaches_note_content_and_preserves_citations(monkeypatch):
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
                "choices": [{"message": {"content": "Here is your todo summary."}}],
                "sources": [
                    {
                        "source": {"name": "notes_manager/get_note"},
                        "document": ["- buy milk\n- call mom"],
                        "metadata": [
                            {
                                "source": "notes_manager/get_note",
                                "parameters": {"note_id": "note-123"},
                            }
                        ],
                    }
                ],
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
        id="p7",
        name="Attach note",
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
    assistant_message = captured["chat_data"]["messages"][1]
    assert assistant_message["content"] == "Here is your todo summary."
    assert assistant_message["note_attachments"][0]["note_id"] == "note-123"
    assert "- buy milk" in assistant_message["note_attachments"][0]["content"]
    assert assistant_message["sources"] == assistant_message["citations"]
    assert assistant_message["sources"][0]["source"]["name"] == "notes_manager/get_note"


def test_execute_scheduled_prompt_uses_continuation_sources_for_note_attachment(monkeypatch):
    captured = {"call_count": 0}

    class _ApiResponse:
        status = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def text(self):
            return ""

        async def json(self):
            captured["call_count"] += 1
            if captured["call_count"] == 1:
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
                "choices": [{"message": {"content": "Final summary after tool call."}}],
                "sources": [
                    {
                        "source": {"name": "notes_manager/get_note"},
                        "document": ["- task from continuation"],
                        "metadata": [
                            {
                                "source": "notes_manager/get_note",
                                "parameters": {"note_id": "cont-note-1"},
                            }
                        ],
                    }
                ],
            }

    class _DummySession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def post(self, url, headers, json, timeout):
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
        id="p8",
        name="Continuation note sources",
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
    assistant_message = captured["chat_data"]["messages"][1]
    assert assistant_message["content"] == "Final summary after tool call."
    assert assistant_message["note_attachments"][0]["note_id"] == "cont-note-1"
    assert "- task from continuation" in assistant_message["note_attachments"][0]["content"]
    assert assistant_message["sources"][0]["source"]["name"] == "notes_manager/get_note"


def test_execute_scheduled_prompt_strips_malformed_tool_chatter_prefix(monkeypatch):
    captured = {"call_count": 0}

    class _ApiResponse:
        status = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def text(self):
            return ""

        async def json(self):
            captured["call_count"] += 1
            if captured["call_count"] == 1:
                return {
                    "choices": [
                        {
                            "message": {
                                "content": "to=notes_manager/get_note commentary Need proper JSON.",
                            }
                        }
                    ]
                }

            return {
                "choices": [
                    {
                        "message": {
                            "content": (
                                "to=notes_manager/get_note commentary foo to=notes_manager/get_note commentary bar\n\n"
                                "Here is your Todo list:\n- Buy groceries\n- Finish report"
                            ),
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
        id="p9",
        name="Strip chatter",
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
    assistant_message = captured["chat_data"]["messages"][1]
    assert "to=notes_manager/get_note" not in assistant_message["content"]
    assert "Here is your Todo list:" in assistant_message["content"]


def test_execute_scheduled_prompt_forces_notes_get_note_after_list_only_sources(monkeypatch):
    captured_payloads = []
    note_id = "0416d5a0-3468-4f0b-a6d6-11900b2439ea"

    class _ApiResponse:
        status = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def text(self):
            return ""

        async def json(self):
            call_idx = len(captured_payloads)
            if call_idx == 1:
                return {
                    "choices": [
                        {
                            "message": {
                                "content": "to=notes_manager/get_note commentary Need proper JSON.",
                            }
                        }
                    ],
                    "sources": [
                        {
                            "source": {"name": "notes_manager/list_my_notes"},
                            "document": [f"| Todo | `{note_id}` | 2026-02-16 |"],
                            "metadata": [{"source": "notes_manager/list_my_notes"}],
                        }
                    ],
                }
            if call_idx == 2:
                return {
                    "choices": [{"message": {"content": "Still working on it..."}}],
                    "sources": [
                        {
                            "source": {"name": "notes_manager/list_my_notes"},
                            "document": [f"| Todo | `{note_id}` | 2026-02-16 |"],
                            "metadata": [{"source": "notes_manager/list_my_notes"}],
                        }
                    ],
                }

            return {
                "choices": [{"message": {"content": "Todo summary from note content."}}],
                "sources": [
                    {
                        "source": {"name": "notes_manager/get_note"},
                        "document": ["- step 1\n- step 2"],
                        "metadata": [
                            {
                                "source": "notes_manager/get_note",
                                "parameters": {"note_id": note_id},
                            }
                        ],
                    }
                ],
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

    def _insert_new_chat(_user_id, chat_form):
        return SimpleNamespace(id="chat-1")

    monkeypatch.setattr("open_webui.utils.scheduler.Chats.insert_new_chat", _insert_new_chat)

    app = SimpleNamespace(
        state=SimpleNamespace(
            MODELS={"model-1": {"info": {"meta": {"toolIds": []}}}},
            config=SimpleNamespace(WEBUI_URL=""),
        )
    )

    prompt = SimpleNamespace(
        id="p10",
        name="Notes follow-up",
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
    assert len(captured_payloads) == 3
    assert (
        "You MUST call get_note with parameter note_id"
        in captured_payloads[2]["messages"][-1]["content"]
    )


def test_execute_scheduled_prompt_retries_when_get_note_uses_title_instead_of_uuid(
    monkeypatch,
):
    captured_payloads = []
    note_id = "0416d5a0-3468-4f0b-a6d6-11900b2439ea"

    class _ApiResponse:
        status = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def text(self):
            return ""

        async def json(self):
            call_idx = len(captured_payloads)
            if call_idx == 1:
                return {
                    "choices": [
                        {
                            "message": {
                                "content": "I found your note but could not read it.",
                            }
                        }
                    ],
                    "sources": [
                        {
                            "source": {"name": "notes_manager/list_my_notes"},
                            "document": [f"| Todo | `{note_id}` | 2026-02-16 |"],
                            "metadata": [{"source": "notes_manager/list_my_notes"}],
                        },
                        {
                            "source": {"name": "notes_manager/get_note"},
                            "document": ["❌ Note not found: Todo"],
                            "metadata": [
                                {
                                    "source": "notes_manager/get_note",
                                    "parameters": {"note_id": "Todo"},
                                }
                            ],
                        },
                    ],
                }

            return {
                "choices": [{"message": {"content": "Todo items: step 1, step 2."}}],
                "sources": [
                    {
                        "source": {"name": "notes_manager/get_note"},
                        "document": ["- step 1\n- step 2"],
                        "metadata": [
                            {
                                "source": "notes_manager/get_note",
                                "parameters": {"note_id": note_id},
                            }
                        ],
                    }
                ],
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
        id="p11",
        name="Retry title-based get_note",
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
    assert (
        "Use the exact UUID from the ID column, not the note title"
        in captured_payloads[1]["messages"][-1]["content"]
    )


def test_execute_scheduled_prompt_note_manager_search_notes_triggers_followup(monkeypatch):
    captured_payloads = []
    note_id = "0fbc657d-fc83-4c0c-94c3-f7585b30c74a"

    class _ApiResponse:
        status = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def text(self):
            return ""

        async def json(self):
            call_idx = len(captured_payloads)
            if call_idx == 1:
                return {
                    "choices": [
                        {
                            "message": {
                                "content": "I found your todo note title but need content access.",
                            }
                        }
                    ],
                    "sources": [
                        {
                            "source": {"name": "note_manager/search_notes"},
                            "document": [
                                "| todo | 📌 title | `0fbc657d-fc83-4c0c-94c3-f7585b30c74a` | 2026-02-16 |"
                            ],
                            "metadata": [{"source": "note_manager/search_notes"}],
                        }
                    ],
                }

            return {
                "choices": [{"message": {"content": "Todo list retrieved."}}],
                "sources": [
                    {
                        "source": {"name": "note_manager/get_note"},
                        "document": ["- step 1\n- step 2"],
                        "metadata": [
                            {
                                "source": "note_manager/get_note",
                                "parameters": {"note_id": note_id},
                            }
                        ],
                    }
                ],
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
        id="p12",
        name="Note manager search follow-up",
        user_id="u1",
        system_prompt="",
        prompt="What's on my todo list?",
        model_id="model-1",
        tool_ids=["note_manager"],
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
    assert "You MUST call get_note with parameter note_id" in captured_payloads[1]["messages"][-1]["content"]
