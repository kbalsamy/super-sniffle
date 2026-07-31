#!/usr/bin/env python3
"""
Universal AI CLI with Token & Cost Tracking
Works with any OpenAI-compatible API + AWS Bedrock
Tracks usage and persists to local JSON file.
"""

import os
import re
import sys
import json
import atexit
import asyncio
import shlex
import argparse
import threading
import subprocess
from typing import Any, Optional

try:
    import readline
except ImportError:  # not available on some platforms (e.g. Windows)
    readline = None

try:
    from contextlib import AsyncExitStack

    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    MCP_AVAILABLE = True
except ImportError:  # 'mcp' package not installed
    MCP_AVAILABLE = False
from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timedelta
from pathlib import Path

from openai import OpenAI
from rich.console import Console, Group
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.live import Live
from rich.table import Table
from rich import box
from rich.spinner import Spinner
from rich.markup import escape


# =============================================================================
# CONTEXT WINDOW DATABASE (max tokens per model)
# =============================================================================

CONTEXT_WINDOWS = {
    # --- Moonshot / Kimi ---
    "kimi-k3": 200_000,
    "kimi-k2-thinking": 200_000,
    "kimi-k2.5": 200_000,
    "kimi-k2.6": 200_000,
    "kimi-k2.7-code": 200_000,

    # --- OpenAI ---
    "gpt-4o": 128_000,
    "gpt-4o-mini": 128_000,
    "gpt-4-turbo": 128_000,
    "o1": 128_000,
    "o1-preview": 128_000,
    "o3-mini": 200_000,

    # --- DeepSeek ---
    "deepseek-chat": 64_000,
    "deepseek-reasoner": 64_000,

    # --- Groq ---
    "llama-3.3-70b-versatile": 8_192,
    "llama-3.1-8b-instant": 8_192,
    "mixtral-8x7b-32768": 32_768,

    # --- AWS Bedrock (Claude) ---
    "anthropic.claude-3-5-sonnet-20241022-v2:0": 200_000,
    "anthropic.claude-3-haiku-20240307-v1:0": 200_000,
    "anthropic.claude-3-opus-20240229-v1:0": 200_000,

    # --- AWS Bedrock (Llama) ---
    "meta.llama3-70b-instruct-v1:0": 8_192,
    "meta.llama3-8b-instruct-v1:0": 8_192,

    # --- AWS Bedrock (Mistral) ---
    "mistral.mistral-large-2402-v1:0": 32_768,

    # --- AWS Bedrock (Amazon Titan) ---
    "amazon.titan-text-express-v1": 8_000,
    "amazon.titan-text-lite-v1": 4_000,

    # --- Qwen ---
    "qwen-max": 32_768,
    "qwen-plus": 32_768,
    "qwen-turbo": 8_192,

    # --- Ollama (Local) ---
    "llama3.2": 8_192,
    "llama3.1": 8_192,
    "mistral": 8_192,
}


# =============================================================================
# PRICING DATABASE (USD per 1M tokens)
# =============================================================================

PRICING = {
    # --- Moonshot / Kimi ---
    "kimi-k3":              {"input": 0.71, "output": 2.94, "provider": "moonshot"},
    "kimi-k2-thinking":     {"input": 0.71, "output": 2.94, "provider": "moonshot"},
    "kimi-k2.5":            {"input": 0.72, "output": 3.60, "provider": "moonshot"},
    "kimi-k2.6":            {"input": 0.72, "output": 3.60, "provider": "moonshot"},
    "kimi-k2.7-code":       {"input": 0.72, "output": 3.60, "provider": "moonshot"},

    # --- OpenAI ---
    "gpt-4o":               {"input": 2.50, "output": 10.00, "provider": "openai"},
    "gpt-4o-mini":          {"input": 0.15, "output": 0.60, "provider": "openai"},
    "gpt-4-turbo":          {"input": 10.00, "output": 30.00, "provider": "openai"},
    "o1":                   {"input": 15.00, "output": 60.00, "provider": "openai"},
    "o3-mini":              {"input": 1.10, "output": 4.40, "provider": "openai"},

    # --- DeepSeek ---
    "deepseek-chat":        {"input": 0.14, "output": 0.28, "provider": "deepseek"},
    "deepseek-reasoner":    {"input": 0.55, "output": 2.19, "provider": "deepseek"},

    # --- Groq ---
    "llama-3.3-70b-versatile":   {"input": 0.59, "output": 0.79, "provider": "groq"},
    "llama-3.1-8b-instant":     {"input": 0.05, "output": 0.08, "provider": "groq"},
    "mixtral-8x7b-32768":       {"input": 0.24, "output": 0.24, "provider": "groq"},

    # --- AWS Bedrock (Claude) ---
    "anthropic.claude-3-5-sonnet-20241022-v2:0": {"input": 3.00, "output": 15.00, "provider": "bedrock"},
    "anthropic.claude-3-haiku-20240307-v1:0":     {"input": 0.25, "output": 1.25, "provider": "bedrock"},
    "anthropic.claude-3-opus-20240229-v1:0":      {"input": 15.00, "output": 75.00, "provider": "bedrock"},

    # --- AWS Bedrock (Llama) ---
    "meta.llama3-70b-instruct-v1:0":  {"input": 0.72, "output": 0.72, "provider": "bedrock"},
    "meta.llama3-8b-instruct-v1:0":   {"input": 0.22, "output": 0.22, "provider": "bedrock"},

    # --- AWS Bedrock (Mistral) ---
    "mistral.mistral-large-2402-v1:0": {"input": 4.00, "output": 12.00, "provider": "bedrock"},

    # --- AWS Bedrock (Amazon Titan) ---
    "amazon.titan-text-express-v1":    {"input": 0.20, "output": 0.60, "provider": "bedrock"},
    "amazon.titan-text-lite-v1":       {"input": 0.15, "output": 0.20, "provider": "bedrock"},

    # --- Qwen ---
    "qwen-max":             {"input": 0.72, "output": 1.44, "provider": "qwen"},
    "qwen-plus":            {"input": 0.36, "output": 0.72, "provider": "qwen"},
    "qwen-turbo":           {"input": 0.072, "output": 0.072, "provider": "qwen"},

    # --- Ollama (Local - free) ---
    "llama3.2":             {"input": 0.0, "output": 0.0, "provider": "ollama"},
    "llama3.1":             {"input": 0.0, "output": 0.0, "provider": "ollama"},
    "mistral":              {"input": 0.0, "output": 0.0, "provider": "ollama"},
}


def get_pricing(model_id: str) -> dict:
    """Get pricing for a model. Falls back to generic lookup or defaults."""
    if not model_id:
        return {"input": 0.0, "output": 0.0, "provider": "unknown"}

    # Exact match
    if model_id in PRICING:
        return PRICING[model_id]

    # Partial match (for Bedrock full ARNs or versioned IDs)
    for key, price in PRICING.items():
        if key in model_id or model_id in key:
            return price

    # Default: unknown pricing
    return {"input": 0.0, "output": 0.0, "provider": "unknown"}


def get_context_window(model_id: str) -> int:
    """Get context window size for a model. Defaults to 8192 if unknown."""
    if not model_id:
        return 8_192

    # Exact match
    if model_id in CONTEXT_WINDOWS:
        return CONTEXT_WINDOWS[model_id]

    # Partial match (for Bedrock full ARNs or versioned IDs)
    for key, window in CONTEXT_WINDOWS.items():
        if key in model_id or model_id in key:
            return window

    # Default context window
    return 8_192


def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token (simplified)."""
    return len(text) // 4


MAX_TOOL_ROUNDS = 8


def _sanitize_tool_name(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "_", name)


# =============================================================================
# MCP (MODEL CONTEXT PROTOCOL) SERVER REGISTRY
# =============================================================================

class MCPManager:
    """Registers stdio MCP servers and exposes their tools for function-calling.

    The MCP client SDK is async-only; the rest of this CLI is synchronous, so
    every registered server is connected on a single dedicated background
    event-loop thread and all calls are bridged onto it with
    run_coroutine_threadsafe.
    """

    def __init__(self, config_file: str, console: Console):
        self.config_file = config_file
        self.console = console
        if os.path.exists(self.config_file):
            self.servers: dict[str, dict] = self._load_config()
        else:
            # First run for this provider: seed the always-on default servers
            # so filesystem access and git code review work without manual
            # /mcp add. Once saved, this file is authoritative — removing a
            # server via /mcp remove keeps it gone on later runs.
            self.servers = self._default_servers()
            self._save_config()

        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._stacks: dict[str, "AsyncExitStack"] = {}
        self.sessions: dict[str, "ClientSession"] = {}
        # prefixed tool name -> (server name, original tool name, input schema)
        self.tools: dict[str, tuple[str, str, dict]] = {}
        self.tool_descriptions: dict[str, str] = {}
        self.errors: dict[str, str] = {}

        if MCP_AVAILABLE and self.servers:
            for name, cfg in list(self.servers.items()):
                self._connect_one(name, cfg)

    # ---- config persistence ----

    @staticmethod
    def _default_servers() -> dict:
        """Always-registered servers: filesystem access to cwd, git code review,
        and desktop-commander (terminal + file editing)."""
        return {
            "fs": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", os.getcwd()],
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

    # ---- background event loop bridging ----

    def _ensure_loop(self):
        if self._loop is None:
            self._loop = asyncio.new_event_loop()
            self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
            self._thread.start()

    def _run(self, coro, timeout: float = 30):
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=timeout)

    # ---- server lifecycle ----

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
            params = StdioServerParameters(
                command=cfg["command"], args=cfg.get("args", []), env=cfg.get("env") or None,
            )
            read, write = await stack.enter_async_context(stdio_client(params))
            session = await stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            result = await session.list_tools()
            return session, result.tools

        try:
            # 90s: first-time `npx` runs have to download/install the package,
            # which for larger servers (e.g. desktop-commander) can take a while.
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
            prefixed = f"{_sanitize_tool_name(name)}__{_sanitize_tool_name(tool.name)}"[:64]
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

    # ---- tool schemas & invocation ----

    def get_tool_schemas(self) -> list[dict]:
        """OpenAI-style function-calling tool definitions."""
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
        """Bedrock Converse API toolConfig, or None if no tools are registered."""
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

    # ---- display helpers ----

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
                escape(prefixed), escape(server), escape(self.tool_descriptions.get(prefixed, "")[:80])
            )
        return table


# =============================================================================
# USAGE TRACKER
# =============================================================================

@dataclass
class SessionUsage:
    """Tracks usage for a single session."""
    provider: str
    model: str
    messages_count: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_input: float = 0.0
    cost_output: float = 0.0
    cost_total: float = 0.0
    start_time: str = field(default_factory=lambda: datetime.now().isoformat())
    end_time: Optional[str] = None


class ContextWindowManager:
    """Manages conversation context to stay within model's token limit."""

    def __init__(self, model: str, reserve_percent: float = 0.15):
        self.model = model
        self.context_limit = get_context_window(model)
        self.reserve_tokens = int(self.context_limit * reserve_percent)
        self.usable_tokens = self.context_limit - self.reserve_tokens

    def estimate_messages_tokens(self, messages: list[dict]) -> int:
        """Estimate total tokens used by messages."""
        total = 0
        for msg in messages:
            # Add overhead for role and formatting (~5 tokens per message)
            total += estimate_tokens(msg.get("content", "")) + 5
        return total

    def should_prune(self, messages: list[dict]) -> bool:
        """Check if messages exceed usable context."""
        return self.estimate_messages_tokens(messages) > self.usable_tokens

    def get_token_usage_percent(self, messages: list[dict]) -> float:
        """Get current token usage as a percentage of usable context."""
        used = self.estimate_messages_tokens(messages)
        return (used / self.usable_tokens) * 100 if self.usable_tokens > 0 else 0

    def prune_messages(self, messages: list[dict], keep_system: bool = True) -> list[dict]:
        """Prune old messages to fit within context, keeping system and latest."""
        if not messages or not self.should_prune(messages):
            return messages

        pruned = []

        # Keep system message if present
        if keep_system and messages and messages[0].get("role") == "system":
            pruned.append(messages[0])

        # Keep the most recent N messages until we fit
        kept_messages = []
        for msg in reversed(messages[1:] if pruned else messages):
            test_list = pruned + [msg] + kept_messages
            if self.estimate_messages_tokens(test_list) <= self.usable_tokens:
                kept_messages.insert(0, msg)
            else:
                break

        return pruned + kept_messages

    def get_status(self, messages: list[dict]) -> dict:
        """Get context usage status."""
        used_tokens = self.estimate_messages_tokens(messages)
        usage_percent = self.get_token_usage_percent(messages)
        return {
            "context_limit": self.context_limit,
            "reserve_tokens": self.reserve_tokens,
            "usable_tokens": self.usable_tokens,
            "used_tokens": used_tokens,
            "remaining_tokens": max(0, self.usable_tokens - used_tokens),
            "usage_percent": usage_percent,
            "needs_pruning": self.should_prune(messages),
        }


class UsageTracker:
    """Persists usage data to local JSON file."""

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or Path.home() / ".ai_cli"
        self.data_dir.mkdir(exist_ok=True)
        self.usage_file = self.data_dir / "usage_history.json"
        self.sessions: list[dict] = self._load()
        self.current_session: Optional[SessionUsage] = None

    def _load(self) -> list[dict]:
        if self.usage_file.exists():
            try:
                with open(self.usage_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return []
        return []

    def _save(self):
        with open(self.usage_file, "w", encoding="utf-8") as f:
            json.dump(self.sessions, f, indent=2, ensure_ascii=False)

    def start_session(self, provider: str, model: str):
        self.current_session = SessionUsage(provider=provider, model=model)

    def record_turn(self, input_tokens: int, output_tokens: int, model: str):
        """Record a single turn's usage."""
        if self.current_session is None:
            return

        pricing = get_pricing(model)

        self.current_session.messages_count += 1
        self.current_session.input_tokens += input_tokens
        self.current_session.output_tokens += output_tokens
        self.current_session.total_tokens += input_tokens + output_tokens

        # Cost = (tokens / 1,000,000) * price_per_1m
        cost_in = (input_tokens / 1_000_000) * pricing["input"]
        cost_out = (output_tokens / 1_000_000) * pricing["output"]

        self.current_session.cost_input += cost_in
        self.current_session.cost_output += cost_out
        self.current_session.cost_total += cost_in + cost_out

    def end_session(self):
        if self.current_session:
            self.current_session.end_time = datetime.now().isoformat()
            self.sessions.append(asdict(self.current_session))
            self._save()

    def get_summary(self) -> Optional[SessionUsage]:
        return self.current_session

    def get_all_time_stats(self) -> dict:
        """Aggregate stats across all sessions."""
        if not self.sessions:
            return {}

        total_input = sum(s["input_tokens"] for s in self.sessions)
        total_output = sum(s["output_tokens"] for s in self.sessions)
        total_cost = sum(s["cost_total"] for s in self.sessions)

        # Group by provider
        by_provider = {}
        for s in self.sessions:
            p = s["provider"]
            if p not in by_provider:
                by_provider[p] = {"sessions": 0, "cost": 0.0, "tokens": 0}
            by_provider[p]["sessions"] += 1
            by_provider[p]["cost"] += s["cost_total"]
            by_provider[p]["tokens"] += s["total_tokens"]

        return {
            "total_sessions": len(self.sessions),
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_tokens": total_input + total_output,
            "total_cost_usd": total_cost,
            "by_provider": by_provider,
        }

    def display_stats(self, console: Console):
        """Display usage statistics in a rich table."""
        stats = self.get_all_time_stats()
        if not stats:
            console.print("[dim]No usage data yet.[/dim]")
            return

        table = Table(
            title="📊 All-Time Usage Statistics",
            box=box.ROUNDED,
            border_style="cyan",
        )
        table.add_column("Metric", style="bold")
        table.add_column("Value", justify="right")

        table.add_row("Total Sessions", str(stats["total_sessions"]))
        table.add_row("Total Input Tokens", f"{stats['total_input_tokens']:,}")
        table.add_row("Total Output Tokens", f"{stats['total_output_tokens']:,}")
        table.add_row("Total Tokens", f"{stats['total_tokens']:,}")
        table.add_row("Total Cost", f"${stats['total_cost_usd']:.6f}")

        console.print(table)

        # Provider breakdown
        if stats["by_provider"]:
            prov_table = Table(
                title="By Provider",
                box=box.SIMPLE,
                border_style="blue",
            )
            prov_table.add_column("Provider", style="bold")
            prov_table.add_column("Sessions", justify="right")
            prov_table.add_column("Tokens", justify="right")
            prov_table.add_column("Cost", justify="right")

            for provider, data in stats["by_provider"].items():
                prov_table.add_row(
                    provider,
                    str(data["sessions"]),
                    f"{data['tokens']:,}",
                    f"${data['cost']:.6f}",
                )

            console.print(prov_table)

    def display_session_summary(self, console: Console):
        """Display current session summary."""
        if not self.current_session:
            return

        s = self.current_session
        table = Table(box=box.SIMPLE, border_style="green", show_header=False)
        table.add_column("", style="dim")
        table.add_column("", justify="right")

        table.add_row("Messages", str(s.messages_count))
        table.add_row("Input Tokens", f"{s.input_tokens:,}")
        table.add_row("Output Tokens", f"{s.output_tokens:,}")
        table.add_row("Total Tokens", f"{s.total_tokens:,}")
        table.add_row("Cost (Input)", f"${s.cost_input:.6f}")
        table.add_row("Cost (Output)", f"${s.cost_output:.6f}")
        table.add_row("[bold]Total Cost[/bold]", f"[bold]${s.cost_total:.6f}[/bold]")

        console.print(
            Panel(table, title="💰 Current Session", border_style="green", expand=False)
        )


# =============================================================================
# PROVIDER CONFIGS
# =============================================================================

@dataclass
class ProviderConfig:
    name: str
    base_url: str
    model: str
    api_key_env: str
    supports_reasoning: bool = False
    reasoning_param: Optional[str] = None
    supports_streaming: bool = True
    system_role: str = "system"
    is_bedrock: bool = False


PROVIDERS = {
    "moonshot": ProviderConfig(
        name="Moonshot (Kimi)",
        base_url="https://api.moonshot.cn/v1",
        model="kimi-k3",
        api_key_env="MOONSHOT_API_KEY",
        supports_reasoning=True,
        reasoning_param="reasoning_effort",
    ),
    "openai": ProviderConfig(
        name="OpenAI",
        base_url="https://api.openai.com/v1",
        model="gpt-4o",
        api_key_env="OPENAI_API_KEY",
        supports_reasoning=True,
        reasoning_param="reasoning_effort",
    ),
    "deepseek": ProviderConfig(
        name="DeepSeek",
        base_url="https://api.deepseek.com/v1",
        model="deepseek-chat",
        api_key_env="DEEPSEEK_API_KEY",
        supports_reasoning=True,
        reasoning_param="reasoning_effort",
    ),
    "groq": ProviderConfig(
        name="Groq",
        base_url="https://api.groq.com/openai/v1",
        model="llama-3.3-70b-versatile",
        api_key_env="GROQ_API_KEY",
    ),
    "ollama": ProviderConfig(
        name="Ollama (Local)",
        base_url="http://localhost:11434/v1",
        model="llama3.2",
        api_key_env="OLLAMA_API_KEY",
    ),
    "qwen": ProviderConfig(
        name="Alibaba Qwen",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        model="qwen-max",
        api_key_env="DASHSCOPE_API_KEY",
    ),
    "bedrock": ProviderConfig(
        name="AWS Bedrock",
        base_url="",  # Not used; boto3 handles it
        model="moonshot.kimi-k2-thinking",
        api_key_env="AWS_ACCESS_KEY_ID",
        is_bedrock=True,
    ),

    "bedrock-mantle": ProviderConfig(
            name="AWS Bedrock",
            base_url="https://bedrock-mantle.us-east-1.api.aws/v1",
            model="moonshot.kimi-k2-thinking",
            api_key_env="AI_API_KEY",            
        ),
    # connect to AWS Bedrock using RestAPI
    "custom": ProviderConfig(
        name="Custom",
        base_url="",
        model="",
        api_key_env="AI_API_KEY"
      
    ),
}


# =============================================================================
# UNIVERSAL AI CLI
# =============================================================================

class UniversalAICli:
    def __init__(
        self,
        provider: str = "custom",
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        reasoning: Optional[str] = None,
        region: str = "ap-south-1",
        profile: Optional[str] = None,
        model_arn: Optional[str] = None,
    ):
        self.config = PROVIDERS.get(provider, PROVIDERS["custom"])
        self.provider_name = provider

        self.model_explicit = bool(model)
        if model:
            self.config.model = model
        if base_url:
            self.config.base_url = base_url

        self.api_key = api_key or os.environ.get(self.config.api_key_env)
        self.reasoning = reasoning
        self.region = region
        self.profile = profile
        self.model_arn = model_arn

        self.console = Console()
        self.messages: list[dict] = []
        self.history_file = os.path.expanduser(f"~/.ai_cli_{provider}_history")
        self.input_history_file = os.path.expanduser(f"~/.ai_cli_{provider}_input_history")
        self._init_input_history()

        # Context window management
        self.context_manager = ContextWindowManager(self.config.model)

        # Token & cost tracking
        self.tracker = UsageTracker()
        self.tracker.start_session(provider, self.config.model)

        # MCP server registry (tool-calling)
        self.mcp_config_file = os.path.expanduser(f"~/.ai_cli_{provider}_mcp_servers.json")
        self.mcp = MCPManager(self.mcp_config_file, self.console)
        atexit.register(self.mcp.shutdown)

        # Initialize client
        if self.config.is_bedrock:
            self._init_bedrock()
        else:
            self._init_openai()

    def _init_input_history(self):
        """Enable up/down-arrow recall of previously typed input, persisted across runs."""
        if readline is None:
            return
        try:
            readline.read_history_file(self.input_history_file)
        except (FileNotFoundError, OSError):
            pass
        readline.set_history_length(1000)
        atexit.register(self._save_input_history)

    def _save_input_history(self):
        if readline is None:
            return
        try:
            readline.write_history_file(self.input_history_file)
        except OSError:
            pass

    def _init_openai(self):
        client_kwargs = {"base_url": self.config.base_url}
        if self.api_key:
            client_kwargs["api_key"] = self.api_key
        else:
            client_kwargs["api_key"] = "dummy"
        self.client = OpenAI(**client_kwargs)
        self.bedrock_client = None

    def _init_bedrock(self):
        import boto3
        from botocore.config import Config

        session_kwargs = {}
        if self.profile:
            session_kwargs["profile_name"] = self.profile

        session = boto3.Session(**session_kwargs)
        self.bedrock_client = session.client(
            "bedrock-runtime",
            region_name=self.region,
            config=Config(retries={"max_attempts": 3}),
        )
        self.client = None

    def _build_request(self, messages: list, stream: bool = True) -> dict:
        payload = {
            "model": self.config.model,
            "messages": messages,
            "stream": stream,
        }
        if (
            self.config.supports_reasoning
            and self.reasoning
            and self.config.reasoning_param
        ):
            payload[self.config.reasoning_param] = self.reasoning
        tools = self.mcp.get_tool_schemas()
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        return payload

    def _execute_tool_call(self, name: str, arguments, is_json_str: bool = True) -> str:
        """Run one tool call through the MCP registry and print a status line."""
        if is_json_str:
            try:
                args = json.loads(arguments) if arguments else {}
            except json.JSONDecodeError:
                args = {}
        else:
            args = arguments or {}

        preview = json.dumps(args, ensure_ascii=False)[:200]
        self.console.print(f"[magenta]🔧 {escape(name)}({escape(preview)})[/magenta]")

        try:
            return self.mcp.call_tool(name, args)
        except Exception as e:
            return f"Error calling tool {name}: {e}"

    def _extract_content(self, delta_or_message) -> tuple[str, Optional[str]]:
        content = getattr(delta_or_message, "content", "") or ""
        reasoning = getattr(delta_or_message, "reasoning_content", None)
        return content, reasoning

    def _extract_usage(self, response) -> tuple[int, int]:
        """Extract token usage from response. Returns (input_tokens, output_tokens)."""
        # OpenAI-style usage
        if hasattr(response, "usage") and response.usage:
            usage = response.usage
            return getattr(usage, "prompt_tokens", 0), getattr(usage, "completion_tokens", 0)

        # Bedrock non-streaming
        if isinstance(response, dict) and "usage" in response:
            u = response["usage"]
            return u.get("inputTokens", 0), u.get("outputTokens", 0)

        return 0, 0

    def _print_banner(self):
        model_name = self.config.model
        if not self.model_explicit and self.model_arn:
            # --model was left at its provider default while --model-arn points
            # elsewhere; that default is misleading, so derive a display/pricing
            # name from the ARN's trailing segment instead
            # (e.g. "us.anthropic.claude-sonnet-4-5-...-v1:0").
            model_name = self.model_arn.rsplit("/", 1)[-1]
        display_model = model_name or "unknown"

        pricing = get_pricing(model_name)
        cost_info = (
            f"${pricing['input']}/1M in, ${pricing['output']}/1M out"
            if pricing["provider"] != "unknown"
            else "Pricing unknown (model not mapped)"
        )

        arn_line = f"[dim]Inference ARN: {escape(self.model_arn)}[/dim]\n" if self.model_arn else ""

        banner = Panel.fit(
            f"[bold cyan]🤖 {self.config.name} CLI[/bold cyan]\n"
            f"[dim]Model: {escape(display_model)}[/dim]\n"
            f"{arn_line}"
            f"[dim]Pricing: {cost_info}[/dim]\n"
            f"[dim]Commands: /clear, /clear-console, /save, /load, /history, /stats, /cost, /aws-cost, /context, /model, /model-arn <arn>, /read <path>, /run <cmd>, /mcp add|remove|list|tools, /quit[/dim]",
            title="Universal AI CLI",
            border_style="cyan",
        )
        self.console.print(banner)

    def _record_usage(self, response, streamed: bool = False):
        """Record token usage from a response object."""
        input_tokens, output_tokens = 0, 0

        if streamed:
            # For streaming, we try to get usage from the final chunk
            # OpenAI: usage is in the last chunk if stream_options.include_usage=True
            # Bedrock: usage is in the final metadata event
            pass  # We'll estimate or get from non-stream if possible
        else:
            input_tokens, output_tokens = self._extract_usage(response)

        if input_tokens or output_tokens:
            self.tracker.record_turn(input_tokens, output_tokens, self.config.model)
            # self.tracker.display_session_summary(self.console)

    def _stream_chat(self, user_input: str) -> str:
        self.messages.append({"role": "user", "content": user_input})

        # Check context usage and warn/prune if needed
        status = self.context_manager.get_status(self.messages)
        if status["usage_percent"] > 80:
            self.console.print(
                f"[yellow]⚠️ Context usage at {status['usage_percent']:.0f}%. "
                f"Remaining: {status['remaining_tokens']:,} tokens[/yellow]"
            )
        if status["needs_pruning"]:
            pruned_count = len(self.messages) - len(self.context_manager.prune_messages(self.messages))
            self.messages = self.context_manager.prune_messages(self.messages)
            self.console.print(
                f"[yellow]📌 Pruned {pruned_count} old messages to fit context window.[/yellow]"
            )

        try:
            if self.config.is_bedrock:
                return self._bedrock_stream_chat(user_input)
            else:
                return self._openai_stream_chat(user_input)
        except Exception as e:
            self.console.print(f"[red]API Error: {escape(str(e))}[/red]")
            self.messages.pop()
            return ""

    def _openai_stream_chat(self, user_input: str) -> str:
        working = list(self.messages)
        total_input_tokens = 0
        total_output_tokens = 0
        final_content = ""

        for round_num in range(MAX_TOOL_ROUNDS):
            request = self._build_request(working, stream=True)
            # Request usage in stream
            request["stream_options"] = {"include_usage": True}

            response = self.client.chat.completions.create(**request)

            full_content = ""
            reasoning_content = ""
            input_tokens = 0
            output_tokens = 0
            tool_calls_acc: dict[int, dict] = {}

            def render():
                parts = []
                if reasoning_content:
                    parts.append(
                        Panel(
                            Markdown(reasoning_content),
                            title="[yellow]Reasoning Process[/yellow]",
                            border_style="yellow",
                            expand=False,
                        )
                    )
                if full_content:
                    parts.append(Markdown(full_content))
                return Group(*parts)
            waiting = Spinner("dots", text=" Waiting for response...")
            with Live(waiting, console=self.console, refresh_per_second=15) as live:
                for chunk in response:
                    # Capture usage from final chunk
                    if hasattr(chunk, "usage") and chunk.usage:
                        input_tokens = getattr(chunk.usage, "prompt_tokens", 0)
                        output_tokens = getattr(chunk.usage, "completion_tokens", 0)

                    if not chunk.choices:
                        continue

                    delta = chunk.choices[0].delta
                    content, reasoning = self._extract_content(delta)

                    if reasoning:
                        reasoning_content += reasoning
                        live.update(render())

                    if content:
                        full_content += content
                        live.update(render())

                    for tc in getattr(delta, "tool_calls", None) or []:
                        entry = tool_calls_acc.setdefault(tc.index, {"id": None, "name": "", "arguments": ""})
                        if tc.id:
                            entry["id"] = tc.id
                        if tc.function:
                            if tc.function.name:
                                entry["name"] += tc.function.name
                            if tc.function.arguments:
                                entry["arguments"] += tc.function.arguments

            self.console.print()
            total_input_tokens += input_tokens
            total_output_tokens += output_tokens

            if tool_calls_acc:
                ordered = [tool_calls_acc[i] for i in sorted(tool_calls_acc)]
                working.append({
                    "role": "assistant",
                    "content": full_content,
                    "tool_calls": [
                        {
                            "id": tc["id"],
                            "type": "function",
                            "function": {"name": tc["name"], "arguments": tc["arguments"]},
                        }
                        for tc in ordered
                    ],
                })
                for tc in ordered:
                    result_text = self._execute_tool_call(tc["name"], tc["arguments"])
                    working.append({"role": "tool", "tool_call_id": tc["id"], "content": result_text})
                continue

            final_content = full_content
            break
        else:
            final_content = "[MCP tool-call loop exceeded max rounds]"

        self.messages.append({"role": "assistant", "content": final_content})

        # Record usage
        if total_input_tokens or total_output_tokens:
            self.tracker.record_turn(total_input_tokens, total_output_tokens, self.config.model)
            # self.tracker.display_session_summary(self.console)

        return final_content

    def _bedrock_msgs_from_history(self) -> tuple[list, Optional[str]]:
        bedrock_msgs = []
        system_text = None
        for msg in self.messages:
            if msg["role"] == "system":
                system_text = msg["content"]
                continue
            bedrock_role = "user" if msg["role"] == "user" else "assistant"
            bedrock_msgs.append({
                "role": bedrock_role,
                "content": [{"text": msg["content"]}],
            })
        return bedrock_msgs, system_text

    def _bedrock_stream_chat(self, user_input: str) -> str:
        """Stream chat using Bedrock ConverseStream API."""
        bedrock_msgs, system_text = self._bedrock_msgs_from_history()
        tool_config = self.mcp.get_bedrock_tool_config()
        total_input_tokens = 0
        total_output_tokens = 0
        final_content = ""

        for round_num in range(MAX_TOOL_ROUNDS):
            kwargs = {
                "modelId": self.model_arn or self.config.model,
                "messages": bedrock_msgs,
            }
            if system_text:
                kwargs["system"] = [{"text": system_text}]
            if tool_config:
                kwargs["toolConfig"] = tool_config

            response = self.bedrock_client.converse_stream(**kwargs)
            stream = response.get("stream")

            full_content = ""
            input_tokens = 0
            output_tokens = 0
            stop_reason = None
            blocks: dict[int, dict] = {}
            waiting = Spinner("dots", text=" Waiting for response...")
            with Live(waiting, console=self.console, refresh_per_second=15) as live:
                for event in stream:
                    if "contentBlockStart" in event:
                        idx = event["contentBlockStart"]["contentBlockIndex"]
                        start = event["contentBlockStart"].get("start", {})
                        if "toolUse" in start:
                            blocks[idx] = {
                                "toolUseId": start["toolUse"]["toolUseId"],
                                "name": start["toolUse"]["name"],
                                "input_json": "",
                            }

                    if "contentBlockDelta" in event:
                        idx = event["contentBlockDelta"]["contentBlockIndex"]
                        delta = event["contentBlockDelta"]["delta"]
                        if "text" in delta:
                            full_content += delta["text"]
                            live.update(Markdown(full_content))
                        elif "toolUse" in delta:
                            entry = blocks.setdefault(idx, {"input_json": ""})
                            entry["input_json"] += delta["toolUse"].get("input", "")

                    if "messageStop" in event:
                        stop_reason = event["messageStop"].get("stopReason")

                    # Capture usage from metadata event
                    if "metadata" in event:
                        usage = event["metadata"].get("usage", {})
                        input_tokens = usage.get("inputTokens", 0)
                        output_tokens = usage.get("outputTokens", 0)

            self.console.print()
            total_input_tokens += input_tokens
            total_output_tokens += output_tokens

            tool_blocks = [b for b in blocks.values() if "toolUseId" in b]
            if stop_reason == "tool_use" and tool_blocks:
                for b in tool_blocks:
                    try:
                        b["input"] = json.loads(b["input_json"]) if b["input_json"] else {}
                    except json.JSONDecodeError:
                        b["input"] = {}

                assistant_content = ([{"text": full_content}] if full_content else []) + [
                    {"toolUse": {"toolUseId": b["toolUseId"], "name": b["name"], "input": b["input"]}}
                    for b in tool_blocks
                ]
                bedrock_msgs.append({"role": "assistant", "content": assistant_content})

                result_content = []
                for b in tool_blocks:
                    result_text = self._execute_tool_call(b["name"], b["input"], is_json_str=False)
                    result_content.append({
                        "toolResult": {"toolUseId": b["toolUseId"], "content": [{"text": result_text}]}
                    })
                bedrock_msgs.append({"role": "user", "content": result_content})
                continue

            final_content = full_content
            break
        else:
            final_content = "[MCP tool-call loop exceeded max rounds]"

        self.messages.append({"role": "assistant", "content": final_content})

        if total_input_tokens or total_output_tokens:
            self.tracker.record_turn(total_input_tokens, total_output_tokens, self.config.model)
            # self.tracker.display_session_summary(self.console)

        return final_content

    def _non_stream_chat(self, user_input: str) -> str:
        self.messages.append({"role": "user", "content": user_input})

        # Check context usage and warn/prune if needed
        status = self.context_manager.get_status(self.messages)
        if status["usage_percent"] > 80:
            self.console.print(
                f"[yellow]⚠️ Context usage at {status['usage_percent']:.0f}%. "
                f"Remaining: {status['remaining_tokens']:,} tokens[/yellow]"
            )
        if status["needs_pruning"]:
            pruned_count = len(self.messages) - len(self.context_manager.prune_messages(self.messages))
            self.messages = self.context_manager.prune_messages(self.messages)
            self.console.print(
                f"[yellow]📌 Pruned {pruned_count} old messages to fit context window.[/yellow]"
            )

        try:
            if self.config.is_bedrock:
                return self._bedrock_non_stream_chat(user_input)
            else:
                return self._openai_non_stream_chat(user_input)
        except Exception as e:
            self.console.print(f"[red]API Error: {escape(str(e))}[/red]")
            self.messages.pop()
            return ""

    def _openai_non_stream_chat(self, user_input: str) -> str:
        working = list(self.messages)
        total_input_tokens = 0
        total_output_tokens = 0
        final_content = ""

        for round_num in range(MAX_TOOL_ROUNDS):
            request = self._build_request(working, stream=False)
            response = self.client.chat.completions.create(**request)

            message = response.choices[0].message
            input_tokens, output_tokens = self._extract_usage(response)
            total_input_tokens += input_tokens
            total_output_tokens += output_tokens

            tool_calls = getattr(message, "tool_calls", None)
            if tool_calls:
                working.append({
                    "role": "assistant",
                    "content": message.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                        }
                        for tc in tool_calls
                    ],
                })
                for tc in tool_calls:
                    result_text = self._execute_tool_call(tc.function.name, tc.function.arguments)
                    working.append({"role": "tool", "tool_call_id": tc.id, "content": result_text})
                continue

            content, reasoning = self._extract_content(message)

            if reasoning:
                self.console.print(
                    Panel(
                        Markdown(reasoning),
                        title="[yellow]Reasoning Process[/yellow]",
                        border_style="yellow",
                        expand=False,
                    )
                )

            self.console.print(Markdown(content))
            self.console.print()
            final_content = content
            break
        else:
            final_content = "[MCP tool-call loop exceeded max rounds]"

        self.messages.append({"role": "assistant", "content": final_content})

        # Record usage
        if total_input_tokens or total_output_tokens:
            self.tracker.record_turn(total_input_tokens, total_output_tokens, self.config.model)
            # self.tracker.display_session_summary(self.console)

        return final_content

    def _bedrock_non_stream_chat(self, user_input: str) -> str:
        """Non-stream chat using Bedrock Converse API."""
        bedrock_msgs, system_text = self._bedrock_msgs_from_history()
        tool_config = self.mcp.get_bedrock_tool_config()
        total_input_tokens = 0
        total_output_tokens = 0
        final_text = ""

        for round_num in range(MAX_TOOL_ROUNDS):
            kwargs = {
                "modelId": self.model_arn or self.config.model,
                "messages": bedrock_msgs,
            }
            if system_text:
                kwargs["system"] = [{"text": system_text}]
            if tool_config:
                kwargs["toolConfig"] = tool_config

            response = self.bedrock_client.converse(**kwargs)

            usage = response.get("usage", {})
            total_input_tokens += usage.get("inputTokens", 0)
            total_output_tokens += usage.get("outputTokens", 0)

            output_message = response["output"]["message"]
            content_blocks = output_message["content"]
            tool_uses = [b["toolUse"] for b in content_blocks if "toolUse" in b]

            if response.get("stopReason") == "tool_use" and tool_uses:
                bedrock_msgs.append(output_message)
                result_content = []
                for tu in tool_uses:
                    result_text = self._execute_tool_call(tu["name"], tu.get("input", {}), is_json_str=False)
                    result_content.append({
                        "toolResult": {"toolUseId": tu["toolUseId"], "content": [{"text": result_text}]}
                    })
                bedrock_msgs.append({"role": "user", "content": result_content})
                continue

            final_text = "\n".join(b["text"] for b in content_blocks if "text" in b)
            self.console.print(Markdown(final_text))
            self.console.print()
            break
        else:
            final_text = "[MCP tool-call loop exceeded max rounds]"

        self.messages.append({"role": "assistant", "content": final_text})

        # Record usage
        if total_input_tokens or total_output_tokens:
            self.tracker.record_turn(total_input_tokens, total_output_tokens, self.config.model)
            # self.tracker.display_session_summary(self.console)

        return final_text

    def _read_file_into_context(self, file_path: str):
        if not file_path:
            self.console.print("[red]Usage: /read <file_path>[/red]")
            return
        path = Path(file_path).expanduser()
        try:
            content = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            self.console.print(f"[red]File not found: {escape(str(path))}[/red]")
            return
        except IsADirectoryError:
            self.console.print(f"[red]Not a file: {escape(str(path))}[/red]")
            return
        except UnicodeDecodeError:
            self.console.print(f"[red]Cannot read binary file: {escape(str(path))}[/red]")
            return
        except Exception as e:
            self.console.print(f"[red]Read failed: {escape(str(e))}[/red]")
            return

        self.messages.append({
            "role": "user",
            "content": f"Contents of {path.name}:\n```\n{content}\n```",
        })
        line_count = content.count("\n") + 1
        self.console.print(
            f"[green]Loaded {path.name} ({line_count} lines) into context.[/green]"
        )

    def _run_shell_command(self, command: str):
        if not command:
            self.console.print("[red]Usage: /run <command>[/red]")
            return
        try:
            result = subprocess.run(shlex.split(command), capture_output=True, text=True, check=True)
            self.console.print(f"[green]Command output:[/green]\n{result.stdout}")
        except subprocess.CalledProcessError as e:
            self.console.print(f"[red]Command failed with error code {e.returncode}:[/red]\n{e.stderr}")
        except Exception as e:
            self.console.print(f"[red]Command failed: {escape(str(e))}[/red]")
            return

        output = ((result.stdout or "") + (result.stderr or "")).strip() or "(no output)"
        truncated = output[:4000]

        self.console.print(
            Panel(
                escape(truncated),
                title=escape(f"$ {command}"),
                border_style="green" if result.returncode == 0 else "red",
            )
        )

        self.messages.append({
            "role": "user",
            "content": (
                f"Ran command `{command}` (exit code {result.returncode}):\n"
                f"```\n{truncated}\n```"
            ),
        })

    def _get_bedrock_unblended_cost_mtd(self) -> dict:
        """Fetch this month's actual AWS Bedrock unblended cost via Cost Explorer.

        Cost Explorer is a global service reachable only from us-east-1, and its
        data typically lags live usage by up to ~24h, so this reflects billed
        cost, not the estimate _record_usage tracks from token counts.
        """
        import boto3

        session_kwargs = {}
        if self.profile:
            session_kwargs["profile_name"] = self.profile
        session = boto3.Session(**session_kwargs)
        ce_client = session.client("ce", region_name="us-east-1")

        today = date.today()
        start = today.replace(day=1)
        end_exclusive = today + timedelta(days=1)

        response = ce_client.get_cost_and_usage(
            TimePeriod={"Start": start.isoformat(), "End": end_exclusive.isoformat()},
            Granularity="MONTHLY",
            Metrics=["UnblendedCost"],
            Filter={"Dimensions": {"Key": "SERVICE", "Values": ["Amazon Bedrock"]}},
        )

        results = response.get("ResultsByTime", [])
        if not results:
            return {"amount": 0.0, "unit": "USD", "start": start.isoformat(), "end": today.isoformat()}
        total = results[0]["Total"]["UnblendedCost"]
        return {
            "amount": float(total["Amount"]),
            "unit": total["Unit"],
            "start": start.isoformat(),
            "end": today.isoformat(),
        }

    def _show_aws_bedrock_cost(self):
        try:
            data = self._get_bedrock_unblended_cost_mtd()
        except Exception as e:
            self.console.print(f"[red]Could not fetch AWS Cost Explorer data: {escape(str(e))}[/red]")
            self.console.print(
                "[dim]Requires AWS credentials with the 'ce:GetCostAndUsage' permission "
                "(this is separate from bedrock:InvokeModel).[/dim]"
            )
            return

        table = Table(box=box.SIMPLE, border_style="green", show_header=False)
        table.add_column("", style="dim")
        table.add_column("", justify="right")
        table.add_row("Period", f"{data['start']} to {data['end']} (month-to-date)")
        table.add_row("Bedrock Unblended Cost", f"${data['amount']:.2f} {data['unit']}")

        self.console.print(
            Panel(table, title="💵 AWS Bedrock Cost (Cost Explorer)", border_style="green", expand=False)
        )
        self.console.print(
            "[dim]Actual billed cost from AWS Cost Explorer (~24h reporting lag); "
            "use /cost for this session's live token-based estimate.[/dim]"
        )

    def _handle_mcp_command(self, args_str: str):
        if not MCP_AVAILABLE:
            self.console.print(
                "[red]MCP support requires the 'mcp' package: pip install mcp[/red]"
            )
            return

        parts = args_str.split(maxsplit=1)
        sub = parts[0].lower() if parts else ""
        rest = parts[1] if len(parts) > 1 else ""

        if sub == "add":
            try:
                tokens = shlex.split(rest)
            except ValueError as e:
                self.console.print(f"[red]Invalid syntax: {escape(str(e))}[/red]")
                return
            if len(tokens) < 2:
                self.console.print("[red]Usage: /mcp add <name> <command> [args...][/red]")
                return
            name, command, *cmd_args = tokens
            if name in self.mcp.servers:
                self.console.print(f"[yellow]Server '{name}' already registered; reconnecting.[/yellow]")
            self.mcp.add_server(name, command, cmd_args)

        elif sub == "remove":
            name = rest.strip()
            if not name:
                self.console.print("[red]Usage: /mcp remove <name>[/red]")
                return
            if self.mcp.remove_server(name):
                self.console.print(f"[green]Removed MCP server '{escape(name)}'.[/green]")
            else:
                self.console.print(f"[red]No such server: {escape(name)}[/red]")

        elif sub in ("list", ""):
            if not self.mcp.servers:
                self.console.print("[yellow]No MCP servers registered. Try: /mcp add <name> <command> [args...][/yellow]")
                return
            self.console.print(Panel(self.mcp.status_table(), title="MCP Servers", border_style="blue"))

        elif sub == "tools":
            if not self.mcp.tools:
                self.console.print("[yellow]No MCP tools available.[/yellow]")
                return
            self.console.print(Panel(self.mcp.tools_table(), title="MCP Tools", border_style="magenta"))

        else:
            self.console.print(
                "[yellow]Usage: /mcp add <name> <command> [args...] | /mcp remove <name> | "
                "/mcp list | /mcp tools[/yellow]"
            )

    def _handle_command(self, cmd: str) -> bool:
        raw_cmd = cmd.strip()
        cmd = raw_cmd.lower()

        if cmd in ("/quit", "/q", "exit"):
            self.tracker.end_session()
            self.console.print("[dim]Goodbye! 👋[/dim]")
            return False

        elif cmd == "/clear":
            self.messages = []
            self.console.print("[green]Conversation history cleared.[/green]")
            return True

        elif cmd == "/clear-console":
            self.console.clear()
            return True

        elif cmd == "/history":
            if not self.messages:
                self.console.print("[yellow]No history yet.[/yellow]")
                return True
            history_text = []
            for m in self.messages:
                role_color = "green" if m["role"] == "user" else "cyan"
                preview = escape(str(m.get("content", ""))[:100])
                history_text.append(
                    f"[{role_color}]{m['role'].upper()}[/]: {preview}..."
                )
            self.console.print(
                Panel(
                    "\n".join(history_text),
                    title="Conversation History",
                    border_style="blue",
                )
            )
            return True

        elif cmd == "/stats":
            self.tracker.display_stats(self.console)
            return True

        elif cmd == "/cost":
            self.tracker.display_session_summary(self.console)
            return True

        elif cmd == "/aws-cost":
            self._show_aws_bedrock_cost()
            return True

        elif cmd == "/context":
            status = self.context_manager.get_status(self.messages)
            table = Table(box=box.SIMPLE, border_style="blue", show_header=False)
            table.add_column("", style="dim")
            table.add_column("", justify="right")

            table.add_row("Model", self.config.model)
            table.add_row("Context Limit", f"{status['context_limit']:,} tokens")
            table.add_row("Reserve", f"{status['reserve_tokens']:,} tokens (15%)")
            table.add_row("Usable", f"{status['usable_tokens']:,} tokens")
            table.add_row("Used", f"{status['used_tokens']:,} tokens")
            table.add_row("Remaining", f"{status['remaining_tokens']:,} tokens")
            table.add_row("Usage", f"{status['usage_percent']:.1f}%")
            table.add_row("Messages", str(len(self.messages)))

            border_color = "red" if status["needs_pruning"] else ("yellow" if status["usage_percent"] > 80 else "green")
            self.console.print(
                Panel(table, title="📊 Context Window Status", border_style=border_color, expand=False)
            )
            return True

        elif cmd == "/save":
            try:
                with open(self.history_file, "w", encoding="utf-8") as f:
                    json.dump(self.messages, f, ensure_ascii=False, indent=2)
                os.chmod(self.history_file, 0o600)
                self.console.print(
                    f"[green]History saved to {self.history_file}[/green]"
                )
            except Exception as e:
                self.console.print(f"[red]Save failed: {escape(str(e))}[/red]")
            return True

        elif cmd == "/load":
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    self.messages = json.load(f)
                self.console.print(
                    f"[green]History loaded from {self.history_file}[/green]"
                )
            except FileNotFoundError:
                self.console.print("[red]No saved history found.[/red]")
            except Exception as e:
                self.console.print(f"[red]Load failed: {escape(str(e))}[/red]")
            return True

        elif cmd.startswith("/model "):
            new_model = raw_cmd[7:].strip()
            if new_model:
                self.config.model = new_model
                self.model_explicit = True
                self.context_manager = ContextWindowManager(new_model)
                self.tracker.current_session.model = new_model
                self.console.print(f"[green]Model switched to: {new_model}[/green]")
            return True

        elif cmd.startswith("/model-arn"):
            new_arn = raw_cmd[len("/model-arn"):].strip()
            if not new_arn or new_arn.lower() == "clear":
                self.model_arn = None
                self.console.print("[green]Inference ARN cleared; using --model.[/green]")
            else:
                if not self.config.is_bedrock:
                    self.console.print(
                        "[yellow]Warning: /model-arn only applies to the Bedrock provider.[/yellow]"
                    )
                self.model_arn = new_arn
                self.console.print(f"[green]Inference ARN set to: {escape(new_arn)}[/green]")
            return True

        elif cmd.startswith("/read "):
            self._read_file_into_context(raw_cmd[6:].strip())
            return True

        elif cmd.startswith("/run "):
            self._run_shell_command(raw_cmd[5:].strip())
            return True

        elif cmd == "/mcp" or cmd.startswith("/mcp "):
            self._handle_mcp_command(raw_cmd[4:].strip())
            return True

        elif cmd.startswith("/"):
            self.console.print(
                "[yellow]Unknown command. Try: /clear, /clear-console, /save, /load, "
                "/history, /stats, /cost, /aws-cost, /context, /model <name>, /model-arn <arn|clear>, "
                "/read <path>, /run <cmd>, /mcp add|remove|list|tools, /quit[/yellow]"
            )
            return True

        return True

    def _set_system_prompt(self, system_prompt: Optional[str]):
        if system_prompt and self.config.system_role:
            self.messages.append({
                "role": self.config.system_role,
                "content": system_prompt,
            })

    def run(self, stream: bool = True, system_prompt: Optional[str] = None):
        self._set_system_prompt(system_prompt)

        self._print_banner()

        while True:
            try:
                user_input = Prompt.ask("[bold green]You[/bold green]")
            except (EOFError, KeyboardInterrupt):
                self.tracker.end_session()
                self.console.print("\n[dim]Goodbye! 👋[/dim]")
                break

            if not user_input.strip():
                continue

            if not self._handle_command(user_input):
                break

            if user_input.strip().startswith("/"):
                continue

            self.console.print(f"[bold cyan]{self.config.model}[/bold cyan]", end=" ")

            if stream:
                self._stream_chat(user_input)
            else:
                self._non_stream_chat(user_input)


def main():
    parser = argparse.ArgumentParser(description="HeyBro")
    parser.add_argument(
        "--provider",
        choices=list(PROVIDERS.keys()),
        default="custom",
        help="API provider (default: custom)",
    )
    parser.add_argument("--model", help="Override default model")
    parser.add_argument(
        "--model-arn",
        help=(
            "Bedrock inference profile / application inference profile ARN to "
            "invoke instead of --model (--model is still used for pricing/display)"
        ),
    )
    parser.add_argument("--base-url", help="Override API base URL")
    parser.add_argument("--api-key", help="API key")
    parser.add_argument(
        "--reasoning",
        choices=["low", "high", "max"],
        help="Reasoning effort (provider-dependent)"
    )
    parser.add_argument("--no-stream", action="store_true", help="Disable streaming")
    parser.add_argument(
        "--system",
        default=(
            "You are a senior code reviewer. Given a diff, file, or snippet, find "
            "concrete issues: bugs, security problems, missed edge cases, unclear "
            "naming. Skip praise and style nitpicks unless asked. For each issue, "
            "give the file/line if known, a one-line description of the problem, "
            "and a concrete fix as a code snippet. Rank issues by severity, most "
            "severe first. Keep prose short; let code do the talking. If the input "
            "isn't code to review, just answer the question concisely."
        ),
        help="System prompt",
    )
    parser.add_argument(
        "--single",
        metavar="PROMPT",
        help="Single prompt mode (use '-' to read the prompt entirely from stdin)",
    )
    parser.add_argument("--region", default="us-east-1", help="AWS region (for Bedrock)")
    parser.add_argument("--profile", help="AWS profile (for Bedrock)")
    args = parser.parse_args()

    stdin_content = None
    if not sys.stdin.isatty():
        stdin_content = sys.stdin.read().strip("\n")

    if args.single == "-":
        if not stdin_content:
            print("Error: --single - requires piped input on stdin")
            sys.exit(1)
        args.single = stdin_content
    elif args.single and stdin_content:
        # Piped input alongside an inline prompt: treat the prompt as
        # instructions and the piped content (e.g. `git diff`) as context.
        args.single = f"{args.single}\n\n{stdin_content}"
    elif not args.single and stdin_content:
        args.single = stdin_content

    try:
        cli = UniversalAICli(
            provider=args.provider,
            model=args.model,
            base_url=args.base_url,
            api_key=args.api_key,
            reasoning=args.reasoning,
            region=args.region,
            profile=args.profile,
            model_arn=args.model_arn,
        )
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    if args.single:
        cli._set_system_prompt(args.system)
        cli._print_banner()
        cli.console.print(f"[bold green]You[/bold green]: {escape(args.single)}")
        cli.console.print(f"[bold cyan]{cli.config.model}[/bold cyan]: ", end="")
        if args.no_stream:
            cli._non_stream_chat(args.single)
        else:
            cli._stream_chat(args.single)
        cli.tracker.end_session()
    else:
        try:
            cli.run(stream=not args.no_stream, system_prompt=args.system)
        finally:
            cli.tracker.end_session()


if __name__ == "__main__":
    main()


