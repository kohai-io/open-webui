# `functions_tools` v0.10.2 file API compatibility

## Scope

The legacy root repository pinned `functions_tools` at revision `15a73d36764ab82522326ee3ca0f99fe15504731`. The maintained repository is `https://git.theoldschool.house/robert/open-webui-functions-tools.git`; its v0.10.2 compatibility branch is at `196b1a4` (`codex/v0102-file-api-compat`): pipe Files API patch `651c242`, scheduler removal `c077fe5`, and action/tool Files API patch `196b1a4`. This pass covers retained artifacts at the legacy revision that directly call Open WebUI's file model or retrieval `process_file` implementation. The legacy `tools/prompt_scheduler.py` has been removed because upstream Automations, including the `create_automation` tool, replace it.

Open WebUI v0.10.2 changed the relevant file-model operations to async methods. Direct calls to `process_file` also require an explicit async database session. Storage-provider upload and lookup signatures remain compatible, although upload tags must be a mapping rather than a list.

## Patched pipe functions

| Pipe | Version |
| --- | --- |
| `elevenlabs_narrator.py` | `3.1.1` |
| `elevenlabs_podcast.py` | `1.3.1` |
| `elevenlabs_sfx.py` | `1.2.1` |
| `elevenlabs_srt_narrator.py` | `3.5.1` |
| `gemini_video_understanding.py` | `1.1.1` |
| `gpt_image_2_chat.py` | `1.2.1` |
| `nano_banana_otel.py` | `1.3.1` |
| `nano_banana_pro.py` | `4.9.1` |
| `nano_banana_pro_chat.py` | `2.6.1` |
| `runway_inline.py` | `2.1.1` |
| `school-website-audit.py` | `1.8.1` |
| `screen_recording_narrator.py` | `2.87.1` |
| `screen_recording_narrator_conversation.py` | `1.3.3` |
| `user_dashboard.py` | `1.3.1` |
| `veo_inline.py` | `7.1.2` |
| `video_to_sfx.py` | `1.0.1` |
| `video_transcription.py` | `3.9.1` |
| `video_transcription_speechmatics.py` | `3.4.1` |
| `video_transcription_tool_speechmatics.py` | `3.2.1` |

Each version is a patch increment. Existing `required_open_webui_version` metadata on affected pipes is raised to `0.10.2`.

## Patched action and tools

| Artifact | Version |
| --- | --- |
| `actions/gpt_image_2_action.py` | `1.2.1` |
| `tools/ElevenLabsTTS.py` | `0.2.5` |
| `tools/elevenlabs_music.py` | `1.0.1` (first explicit version) |
| `tools/elevenlabs_sfx.py` | `1.0.1` (first explicit version) |
| `tools/user_dashboard_interactive.py` | `2.3.9` |
| `tools/video_transcription_subtitle_tool.py` | `2.4.1` |
| `tools/video_transcription_tool.py` | `3.1.1` |

These artifacts receive the same async Files-model adaptation and `required_open_webui_version: 0.10.2` metadata. The transcription tools also use an explicit async database context for direct retrieval processing. The removed prompt scheduler is not part of this set.

## Compatibility changes

- Await `Files`/`FilesDB` reads, inserts, updates, lists, and deletes.
- Convert synchronous media-resolution helpers and their callers to async where a file lookup occurs.
- Invoke retrieval `process_file` through a small wrapper that creates an explicit `get_async_db_context()` session and passes it as `db`.
- Supply `{}` rather than `[]` for storage tags in the website-audit uploads.
- Preserve v0.10.2's owner-private file behaviour; no legacy file rows, grants, or storage are migrated.

## Verification

- `python -m compileall -q functions_tools/functions` passes.
- AST checks covering the v0.10.2 async `Files` methods and the retrieval wrapper report no un-awaited calls in `functions_tools/functions`, `functions_tools/actions`, or `functions_tools/tools`.
- `git diff --check` passes after generated cache files are removed.

Runtime contract tests still require representative fresh v0.10.2 users, media uploads, and provider credentials. Static Files API compatibility coverage is complete for the currently inventoried functions, actions, and tools.
