import argparse
from starlette.applications import Starlette
from starlette.routing import Route

import uvicorn
from mcp.server.sse import SseServerTransport

# Reuse the existing MCP Server instance + tool handlers (already registered via decorators)
from .server import app as mcp_server


def create_asgi_app() -> Starlette:
    """
    Expose the MCP server over HTTP using the SSE transport available in mcp==1.1.0.

    We mount two equivalent endpoint pairs for client compatibility:
    - /sse + /messages
    - /mcp/sse + /mcp/messages
    """

    sse_root = SseServerTransport("/messages")
    sse_mcp = SseServerTransport("/mcp/messages")

    async def handle_sse(request):
        async with sse_root.connect_sse(request.scope, request.receive, request._send) as streams:
            await mcp_server.run(streams[0], streams[1], mcp_server.create_initialization_options())

    async def handle_messages(request):
        await sse_root.handle_post_message(request.scope, request.receive, request._send)

    async def handle_mcp_sse(request):
        async with sse_mcp.connect_sse(request.scope, request.receive, request._send) as streams:
            await mcp_server.run(streams[0], streams[1], mcp_server.create_initialization_options())

    async def handle_mcp_messages(request):
        await sse_mcp.handle_post_message(request.scope, request.receive, request._send)

    return Starlette(
        routes=[
            Route("/sse", endpoint=handle_sse, methods=["GET"]),
            Route("/messages", endpoint=handle_messages, methods=["POST"]),
            Route("/mcp/sse", endpoint=handle_mcp_sse, methods=["GET"]),
            Route("/mcp/messages", endpoint=handle_mcp_messages, methods=["POST"]),
        ],
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run mcp-obsidian over HTTP (SSE transport).")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    uvicorn.run(
        create_asgi_app(),
        host=args.host,
        port=args.port,
        log_level="info",
    )


