#!/usr/bin/env python3
"""
Universal AI CLI with Token & Cost Tracking
Works with any OpenAI-compatible API + AWS Bedrock
Tracks usage and persists to local JSON file.
"""

import os
import sys
import json
import atexit
import shlex
import argparse
import subprocess
from typing import Optional

try:
    import readline
except ImportError:  # not available on some platforms (e.g. Windows)
    readline = None

from datetime import date, timedelta
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

from heybro_app.mcp_manager import MCP_AVAILABLE, MCPManager
from heybro_app.models import MAX_TOOL_ROUNDS, get_pricing
from heybro_app.providers import PROVIDERS
from heybro_app.usage import ContextWindowManager, UsageTracker


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
        working_dir: Optional[Path] = None,
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
        
        # Set up working directory and file paths
        if working_dir:
            self.working_dir = Path(working_dir).expanduser().resolve()
            self.working_dir.mkdir(parents=True, exist_ok=True)
            self.history_file = str(self.working_dir / f"ai_cli_{provider}_history")
            self.input_history_file = str(self.working_dir / f"ai_cli_{provider}_input_history")
            self.mcp_config_file = str(self.working_dir / f"ai_cli_{provider}_mcp_servers.json")
            self.tracker = UsageTracker(self.working_dir)
        else:
            # Legacy behavior - use home directory
            self.working_dir = None
            self.history_file = os.path.expanduser(f"~/.ai_cli_{provider}_history")
            self.input_history_file = os.path.expanduser(f"~/.ai_cli_{provider}_input_history")
            self.mcp_config_file = os.path.expanduser(f"~/.ai_cli_{provider}_mcp_servers.json")
            self.tracker = UsageTracker()
        
        self._init_input_history()

        # Context window management
        self.context_manager = ContextWindowManager(self.config.model)

        # Token & cost tracking
        self.tracker.start_session(provider, self.config.model)

        # MCP server registry (tool-calling)
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
            # For streaming, we handle usage in the specific streaming methods
            # (_bedrock_stream_chat and _openai_stream_chat)
            return
        else:
            input_tokens, output_tokens = self._extract_usage(response)

        if input_tokens or output_tokens:
            self.tracker.record_turn(input_tokens, output_tokens, self.config.model)
            self._display_token_usage(input_tokens, output_tokens)

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
            self._display_token_usage(total_input_tokens, total_output_tokens)

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
            self._display_token_usage(total_input_tokens, total_output_tokens)

        return final_content

    def _display_token_usage(self, input_tokens: int, output_tokens: int):
        total_tokens = input_tokens + output_tokens
        self.console.print(f"\n[bold blue]Token Usage:[/bold blue] Input: {input_tokens}, Output: {output_tokens}, Total: {total_tokens}")

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
            self._display_token_usage(total_input_tokens, total_output_tokens)

        return final_text

    def _read_file_into_context(self, file_path: str):
        if not file_path:
            self.console.print("[red]Usage: /read <file_path>[/red]")
            return
        
        # If file_path is relative and we have a working directory, resolve relative to working directory
        path = Path(file_path)
        if not path.is_absolute() and self.working_dir:
            path = self.working_dir / path
        
        path = path.expanduser().resolve()
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
            except KeyboardInterrupt:
                self.console.print("\n[yellow]Canceled. Use /quit to exit.[/yellow]")
                continue
            except EOFError:
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
    parser.add_argument(
        "--directory", "-d",
        metavar="PATH",
        help="Working directory for storing history, configs, and data files",
    )
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
            working_dir=args.directory,
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
