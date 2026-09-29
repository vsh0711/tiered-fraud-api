from __future__ import annotations

import logging
from collections import defaultdict
from threading import Lock

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

logger = logging.getLogger("fraud_api.metrics")

REQUESTS = Counter("fraud_requests_total", "Total score requests", ["mode", "decision"])
LATENCY = Histogram(
    "fraud_request_latency_ms",
    "End-to-end latency ms",
    ["mode"],
    buckets=(1, 5, 10, 25, 50, 75, 100, 150, 200, 500),
)
TIER_STOPS = Counter("fraud_tier_stop_total", "Last tier executed", ["mode", "tier"])

_lock = Lock()
_latencies: dict[str, list[float]] = defaultdict(list)
_counts: dict[str, int] = defaultdict(int)
_decisions: dict[str, int] = defaultdict(int)
_tier_stops: dict[str, int] = defaultdict(int)


def record(mode: str, decision: str, latency_ms: float, last_tier: str) -> None:
    REQUESTS.labels(mode=mode, decision=decision).inc()
    LATENCY.labels(mode=mode).observe(latency_ms)
    TIER_STOPS.labels(mode=mode, tier=last_tier).inc()
    with _lock:
        _latencies[mode].append(latency_ms)
        _counts[mode] += 1
        _decisions[decision] += 1
        _tier_stops[f"{mode}:{last_tier}"] += 1


def prometheus_metrics() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST


def json_summary() -> dict:
    with _lock:
        out = {
            "requests_total": sum(_counts.values()),
            "by_mode": dict(_counts),
            "by_decision": dict(_decisions),
            "by_tier_stop": dict(_tier_stops),
            "latency_ms_avg": {},
            "latency_ms_p99": {},
        }
        for mode, vals in _latencies.items():
            if not vals:
                continue
            s = sorted(vals)
            out["latency_ms_avg"][mode] = round(sum(s) / len(s), 3)
            idx = max(0, int(0.99 * len(s)) - 1)
            out["latency_ms_p99"][mode] = round(s[idx], 3)
    return out
