"""
AXIOM Token Tracker - Monitors token usage across all verification agents.
"""
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict


class TokenTracker:
    """Tracks token consumption for all AXIOM agents."""

    def __init__(self, daily_limit: int = 82_000_000):
        self.daily_limit = daily_limit
        self._usage: Dict[str, List[dict]] = defaultdict(list)
        self._daily_total = 0
        self._session_start = datetime.now()

    def record_usage(self, agent_name: str, tokens: int, operation: str = "analyze"):
        """Record token usage for an agent."""
        self._usage[agent_name].append({
            "tokens": tokens,
            "operation": operation,
            "timestamp": datetime.now().isoformat(),
        })
        self._daily_total += tokens

    def get_agent_usage(self, agent_name: str) -> int:
        """Get total tokens used by a specific agent."""
        return sum(entry["tokens"] for entry in self._usage.get(agent_name, []))

    def get_daily_total(self) -> int:
        """Get total tokens used today."""
        return self._daily_total

    def get_remaining_budget(self) -> int:
        """Get remaining token budget for today."""
        return max(0, self.daily_limit - self._daily_total)

    def get_usage_summary(self) -> dict:
        """Get comprehensive usage summary."""
        summary = {
            "daily_total": self._daily_total,
            "daily_limit": self.daily_limit,
            "remaining": self.get_remaining_budget(),
            "utilization_pct": round(self._daily_total / self.daily_limit * 100, 4),
            "session_start": self._session_start.isoformat(),
            "agents": {},
        }
        for agent, entries in self._usage.items():
            total = sum(e["tokens"] for e in entries)
            summary["agents"][agent] = {
                "total_tokens": total,
                "call_count": len(entries),
                "avg_tokens": total // max(len(entries), 1),
            }
        return summary

    def estimate_cost(self, agent_name: str, code_length: int) -> int:
        """Estimate token cost for analyzing given code."""
        from core.config import Config
        base = Config.AGENT_TOKEN_ESTIMATES.get(agent_name, 15000)
        code_factor = max(1, code_length // 500)
        return base + (code_factor * 200)

    def can_afford(self, agent_name: str, code_length: int) -> bool:
        """Check if we have budget for an analysis."""
        estimated = self.estimate_cost(agent_name, code_length)
        return self.get_remaining_budget() >= estimated

    def get_rate_stats(self) -> dict:
        """Get tokens-per-minute and projected daily rate."""
        elapsed = (datetime.now() - self._session_start).total_seconds()
        if elapsed < 1:
            return {"tokens_per_minute": 0, "projected_daily": 0}
        tpm = self._daily_total / (elapsed / 60)
        projected = tpm * 60 * 24
        return {
            "tokens_per_minute": round(tpm),
            "projected_daily": round(projected),
            "elapsed_seconds": round(elapsed),
        }
