import asyncio
import logging
from typing import Optional
from contextlib import AsyncExitStack

import anyio

from mcp import ClientSession
from mcp.client.auth import OAuthClientProvider, TokenStorage
from mcp.client.streamable_http import streamablehttp_client
from mcp.shared.auth import OAuthClientInformationFull, OAuthClientMetadata, OAuthToken
from mcp.shared.exceptions import McpError

log = logging.getLogger(__name__)


class MCPClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = None

    async def connect(self, url: str, headers: Optional[dict] = None):
        async with AsyncExitStack() as exit_stack:
            try:
                log.info(f"Connecting to MCP server at {url}")
                self._streams_context = streamablehttp_client(url, headers=headers)

                log.debug("Establishing transport connection")
                transport = await exit_stack.enter_async_context(self._streams_context)
                read_stream, write_stream, _ = transport

                log.debug("Creating client session")
                self._session_context = ClientSession(
                    read_stream, write_stream
                )  # pylint: disable=W0201

                self.session = await exit_stack.enter_async_context(
                    self._session_context
                )
                
                log.debug("Initializing session (10s timeout)")
                with anyio.fail_after(10):
                    await self.session.initialize()
                
                log.info("MCP session initialized successfully")
                self.exit_stack = exit_stack.pop_all()
            except McpError as e:
                log.error(f"MCP protocol error during connection: {e}")
                await asyncio.shield(self.disconnect())
                raise RuntimeError(
                    f"MCP server rejected connection: {e}. "
                    "This often indicates OAuth authentication issues. "
                    "Check: (1) OAuth client credentials, (2) token validity, "
                    "(3) server endpoint URL, (4) required scopes/permissions."
                ) from e
            except TimeoutError as e:
                log.error("Timeout during MCP session initialization")
                await asyncio.shield(self.disconnect())
                raise RuntimeError(
                    "MCP server initialization timed out after 10 seconds. "
                    "The server may be unreachable or not responding to OAuth flow."
                ) from e
            except Exception as e:
                log.error(f"Unexpected error during MCP connection: {type(e).__name__}: {e}")
                await asyncio.shield(self.disconnect())
                raise

    async def list_tool_specs(self) -> Optional[dict]:
        if not self.session:
            raise RuntimeError("MCP client is not connected.")

        result = await self.session.list_tools()
        tools = result.tools

        tool_specs = []
        for tool in tools:
            name = tool.name
            description = tool.description

            inputSchema = tool.inputSchema

            # TODO: handle outputSchema if needed
            outputSchema = getattr(tool, "outputSchema", None)

            tool_specs.append(
                {"name": name, "description": description, "parameters": inputSchema}
            )

        return tool_specs

    async def call_tool(
        self, function_name: str, function_args: dict
    ) -> Optional[dict]:
        if not self.session:
            raise RuntimeError("MCP client is not connected.")

        result = await self.session.call_tool(function_name, function_args)
        if not result:
            raise Exception("No result returned from MCP tool call.")

        result_dict = result.model_dump(mode="json")
        result_content = result_dict.get("content", {})

        if result.isError:
            raise Exception(result_content)
        else:
            return result_content

    async def list_resources(self, cursor: Optional[str] = None) -> Optional[dict]:
        if not self.session:
            raise RuntimeError("MCP client is not connected.")

        result = await self.session.list_resources(cursor=cursor)
        if not result:
            raise Exception("No result returned from MCP list_resources call.")

        result_dict = result.model_dump()
        resources = result_dict.get("resources", [])

        return resources

    async def read_resource(self, uri: str) -> Optional[dict]:
        if not self.session:
            raise RuntimeError("MCP client is not connected.")

        result = await self.session.read_resource(uri)
        if not result:
            raise Exception("No result returned from MCP read_resource call.")
        result_dict = result.model_dump()

        return result_dict

    async def disconnect(self):
        # Clean up and close the session
        if self.exit_stack is not None:
            await self.exit_stack.aclose()
            self.exit_stack = None

    async def __aenter__(self):
        await self.exit_stack.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.exit_stack.__aexit__(exc_type, exc_value, traceback)
        await self.disconnect()
