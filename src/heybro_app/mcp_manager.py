"""Model Context Protocol server registry."""

import asyncio
import json
import os
import re
import threading
from typing import Optional

from rich import box
from rich.console import Console
from rich.markup import escape
from rich.table import Table

try:
    from contextlib import AsyncExitStack

    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False


def sanitize_tool_name(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "_", name)


class MCPManager:
    """Registers stdio MCP servers and exposes their tools for function-calling."""

    def __init__(self, config_file: str, console: Console):
        self.config_file = config_file
        self.console = console
        if os.path.exists(self.config_file):
            self.servers: dict[str, dict] = self._load_config()
        else:
            self.servers = self._default_servers()
            self._save_config()

        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._stacks: dict[str, "AsyncExitStack"] = {}
        self.sessions: dict[str, "ClientSession"] = {}
        self.tools: dict[str, tuple[str, str, dict]] = {}
        self.tool_descriptions: dict[str, str] = {}
        self.errors: dict[str, str] = {}

        if MCP_AVAILABLE and self.servers:
            for name, cfg in list(self.servers.items()):
                self._connect_one(name, cfg)

    @staticmethod
    def _default_servers() -> dict:
        return {
            "fs": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", "${CWD}"],
                "env": {},
            },
            "gcr": {
                "command": "npx",
                "args": ["-y", "git-codereview"],
                "env": {},
            },
            "desktop-commander": {
                "command": "npx",
                "args": ["-y", "@wonderwhy-er/desktop-commander@latest"],
                "env": {},
            },
            "memory": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-memory"],
                "env": {"MEMORY_FILE_PATH": os.path.expanduser("~/.ai_cli_memory.json")},
            },
        }

    def _load_config(self) -> dict:
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def _save_config(self):
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(self.servers, f, indent=2, ensure_ascii=False)
        os.chmod(self.config_file, 0o600)

    def _ensure_loop(self):
        if self._loop is None:
            self._loop = asyncio.new_event_loop()
            self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
            self._thread.start()

    def _run(self, coro, timeout: float = 30):
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=timeout)

    def add_server(self, name: str, command: str, args: list[str], env: Optional[dict] = None):
        if name in self.servers:
            self._disconnect_one(name)
        self.servers[name] = {"command": command, "args": args, "env": env or {}}
        self._save_config()
        if MCP_AVAILABLE:
            self._connect_one(name, self.servers[name])

    def remove_server(self, name: str) -> bool:
        if name not in self.servers:
            return False
        del self.servers[name]
        self._save_config()
        self._disconnect_one(name)
        return True

    def _connect_one(self, name: str, cfg: dict):
        self._ensure_loop()
        stack = AsyncExitStack()

        async def _connect():
            resolved_args = [
                os.getcwd() if arg == "${CWD}" else arg
                for arg in cfg.get("args", [])
            ]
            params = StdioServerParameters(
                command=cfg["command"],
                args=resolved_args,
                env=cfg.get("env") or None,
            )
            read, write = await stack.enter_async_context(stdio_client(params))
            session = await stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            result = await session.list_tools()
            return session, result.tools

        try:
            session, tools = self._run(_connect(), timeout=90)
        except Exception as e:
            message = str(e) or f"{type(e).__name__} (may be a slow first-time npx install; try again)"
            self.errors[name] = message
            self.console.print(f"[red]MCP server '{name}' failed to connect: {escape(message)}[/red]")
            return

        self.errors.pop(name, None)
        self._stacks[name] = stack
        self.sessions[name] = session
        for tool in tools:
            prefixed = f"{sanitize_tool_name(name)}__{sanitize_tool_name(tool.name)}"[:64]
            schema = tool.input_schema or {"type": "object", "properties": {}}
            self.tools[prefixed] = (name, tool.name, schema)
            self.tool_descriptions[prefixed] = tool.description or ""
        self.console.print(f"[green]MCP server '{name}' connected ({len(tools)} tools).[/green]")

    def _disconnect_one(self, name: str):
        self.sessions.pop(name, None)
        for prefixed in [p for p, (s, _, _) in self.tools.items() if s == name]:
            del self.tools[prefixed]
            self.tool_descriptions.pop(prefixed, None)
        stack = self._stacks.pop(name, None)
        if stack is not None and self._loop is not None:
            try:
                self._run(stack.aclose(), timeout=10)
            except Exception:
                pass

    def shutdown(self):
        if self._loop is None:
            return
        for name in list(self._stacks):
            self._disconnect_one(name)
        self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread is not None:
            self._thread.join(timeout=5)

    def get_tool_schemas(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": prefixed,
                    "description": self.tool_descriptions.get(prefixed, ""),
                    "parameters": schema,
                },
            }
            for prefixed, (_, _, schema) in self.tools.items()
        ]

    def get_bedrock_tool_config(self) -> Optional[dict]:
        if not self.tools:
            return None
        return {
            "tools": [
                {
                    "toolSpec": {
                        "name": prefixed,
                        "description": self.tool_descriptions.get(prefixed, ""),
                        "inputSchema": {"json": schema},
                    }
                }
                for prefixed, (_, _, schema) in self.tools.items()
            ]
        }

    def call_tool(self, prefixed_name: str, arguments: dict) -> str:
        if prefixed_name not in self.tools:
            return f"Error: unknown tool '{prefixed_name}'."
        server, tool_name, _ = self.tools[prefixed_name]
        session = self.sessions.get(server)
        if session is None:
            return f"Error: MCP server '{server}' is not connected."

        result = self._run(session.call_tool(tool_name, arguments), timeout=60)
        parts = [getattr(block, "text", "") for block in result.content]
        text_out = "\n".join(p for p in parts if p) or "(tool returned no text content)"
        return f"Tool error: {text_out}" if result.is_error else text_out

    def status_table(self) -> Table:
        table = Table(box=box.SIMPLE, border_style="blue")
        table.add_column("Server")
        table.add_column("Command")
        table.add_column("Status")
        table.add_column("Tools", justify="right")
        for name, cfg in self.servers.items():
            cmd_display = " ".join([cfg["command"], *cfg.get("args", [])])
            if name in self.sessions:
                status = "[green]connected[/green]"
            elif name in self.errors:
                status = f"[red]error: {escape(self.errors[name])}[/red]"
            else:
                status = "[yellow]not connected[/yellow]"
            tool_count = sum(1 for s, _, _ in self.tools.values() if s == name)
            table.add_row(escape(name), escape(cmd_display), status, str(tool_count))
        return table

    def tools_table(self) -> Table:
        table = Table(box=box.SIMPLE, border_style="magenta")
        table.add_column("Tool")
        table.add_column("Server")
        table.add_column("Description")
        for prefixed, (server, _, _) in sorted(self.tools.items()):
            table.add_row(
                escape(prefixed),
                escape(server),
                escape(self.tool_descriptions.get(prefixed, "")[:80]),
            )
        return table