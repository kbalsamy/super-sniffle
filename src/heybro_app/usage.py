"""Usage tracking and context-window management."""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .models import estimate_tokens, get_context_window, get_pricing


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
    """Manages conversation context to stay within the model limit."""

    def __init__(self, model: str, reserve_percent: float = 0.15):
        self.model = model
        self.context_limit = get_context_window(model)
        self.reserve_tokens = int(self.context_limit * reserve_percent)
        self.usable_tokens = self.context_limit - self.reserve_tokens

    def estimate_messages_tokens(self, messages: list[dict]) -> int:
        total = 0
        for msg in messages:
            total += estimate_tokens(msg.get("content", "")) + 5
        return total

    def should_prune(self, messages: list[dict]) -> bool:
        return self.estimate_messages_tokens(messages) > self.usable_tokens

    def get_token_usage_percent(self, messages: list[dict]) -> float:
        used = self.estimate_messages_tokens(messages)
        return (used / self.usable_tokens) * 100 if self.usable_tokens > 0 else 0

    def prune_messages(self, messages: list[dict], keep_system: bool = True) -> list[dict]:
        if not messages or not self.should_prune(messages):
            return messages

        pruned = []
        if keep_system and messages and messages[0].get("role") == "system":
            pruned.append(messages[0])

        kept_messages = []
        for msg in reversed(messages[1:] if pruned else messages):
            test_list = pruned + [msg] + kept_messages
            if self.estimate_messages_tokens(test_list) <= self.usable_tokens:
                kept_messages.insert(0, msg)
            else:
                break

        return pruned + kept_messages

    def get_status(self, messages: list[dict]) -> dict:
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
    """Persists usage data to a local JSON file."""

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or Path.home() / ".ai_cli"
        self.data_dir.mkdir(exist_ok=True, parents=True)
        self.usage_file = self.data_dir / "usage_history.json"
        self.sessions: list[dict] = self._load()
        self.current_session: Optional[SessionUsage] = None
        self._recover_incomplete_session()

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

    def _recover_incomplete_session(self) -> None:
        if not self.sessions:
            return

        for i in range(len(self.sessions) - 1, -1, -1):
            sess_dict = self.sessions[i]
            if "end_time" not in sess_dict:
                self.current_session = SessionUsage(**sess_dict)
                del self.sessions[i]
                self._save()
                break

    def start_session(self, provider: str, model: str):
        self.current_session = SessionUsage(provider=provider, model=model)

    def record_turn(self, input_tokens: int, output_tokens: int, model: str):
        if self.current_session is None:
            return

        pricing = get_pricing(model)
        self.current_session.messages_count += 1
        self.current_session.input_tokens += input_tokens
        self.current_session.output_tokens += output_tokens
        self.current_session.total_tokens += input_tokens + output_tokens

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
        if not self.sessions:
            return {}

        total_input = sum(s["input_tokens"] for s in self.sessions)
        total_output = sum(s["output_tokens"] for s in self.sessions)
        total_cost = sum(s["cost_total"] for s in self.sessions)
        by_provider = {}
        for s in self.sessions:
            provider = s["provider"]
            if provider not in by_provider:
                by_provider[provider] = {"sessions": 0, "cost": 0.0, "tokens": 0}
            by_provider[provider]["sessions"] += 1
            by_provider[provider]["cost"] += s["cost_total"]
            by_provider[provider]["tokens"] += s["total_tokens"]

        return {
            "total_sessions": len(self.sessions),
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_tokens": total_input + total_output,
            "total_cost_usd": total_cost,
            "by_provider": by_provider,
        }

    def display_stats(self, console: Console):
        stats = self.get_all_time_stats()
        if not stats:
            console.print("[dim]No usage data yet.[/dim]")
            return

        table = Table(title="All-Time Usage Statistics", box=box.ROUNDED, border_style="cyan")
        table.add_column("Metric", style="bold")
        table.add_column("Value", justify="right")
        table.add_row("Total Sessions", str(stats["total_sessions"]))
        table.add_row("Total Input Tokens", f"{stats['total_input_tokens']:,}")
        table.add_row("Total Output Tokens", f"{stats['total_output_tokens']:,}")
        table.add_row("Total Tokens", f"{stats['total_tokens']:,}")
        table.add_row("Total Cost", f"${stats['total_cost_usd']:.6f}")
        console.print(table)

        if stats["by_provider"]:
            prov_table = Table(title="By Provider", box=box.SIMPLE, border_style="blue")
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
        console.print(Panel(table, title="Current Session", border_style="green", expand=False))

