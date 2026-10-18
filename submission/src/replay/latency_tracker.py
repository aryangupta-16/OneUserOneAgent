"""Track and report per-decision latency."""
from __future__ import annotations

import json
from ..config import MAX_DECISION_LATENCY_S, LATENCY_FAILURE_S


class LatencyTracker:
    """Track decision latencies and generate reports."""

    def __init__(self):
        self.latencies: list[dict] = []

    def record(self, decision_id: str, latency_ms: int, trigger_time: str):
        self.latencies.append({
            "decision_id": decision_id,
            "latency_ms": latency_ms,
            "trigger_time": trigger_time,
            "within_budget": latency_ms / 1000.0 <= MAX_DECISION_LATENCY_S,
            "failure": latency_ms / 1000.0 >= LATENCY_FAILURE_S,
        })

    def report(self) -> dict:
        if not self.latencies:
            return {"total": 0, "within_budget": 0, "failures": 0}
        lats = [l["latency_ms"] for l in self.latencies]
        lats.sort()
        within = sum(1 for l in self.latencies if l["within_budget"])
        failures = sum(1 for l in self.latencies if l["failure"])
        return {
            "total_decisions": len(self.latencies),
            "within_budget": within,
            "budget_violations": len(self.latencies) - within,
            "failures_over_5min": failures,
            "min_ms": lats[0],
            "max_ms": lats[-1],
            "median_ms": lats[len(lats) // 2],
            "p95_ms": lats[int(len(lats) * 0.95)] if lats else 0,
            "p99_ms": lats[int(len(lats) * 0.99)] if lats else 0,
        }

    def save(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.report(), f, indent=2)
