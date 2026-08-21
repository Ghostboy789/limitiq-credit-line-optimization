"""Small dependency-free HTTP smoke benchmark for deployed application routes."""

# ruff: noqa: S310

from __future__ import annotations

import argparse
import json
import math
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from urllib.parse import urlparse


def _request_once(url: str, timeout: float) -> tuple[float, bool]:
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:  # nosec B310
            response.read(1)
            success = 200 <= response.status < 400
    except OSError:
        success = False
    return (time.perf_counter() - started) * 1000, success


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    index = max(0, math.ceil(percentile * len(ordered)) - 1)
    return ordered[index]


def run_benchmark(
    url: str, requests: int = 50, concurrency: int = 5, timeout: float = 10
) -> dict[str, Any]:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Benchmark URL must be HTTP(S)")
    if not 1 <= requests <= 1000 or not 1 <= concurrency <= min(100, requests):
        raise ValueError("Requests/concurrency are outside safe benchmark bounds")
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        outcomes = list(pool.map(lambda _: _request_once(url, timeout), range(requests)))
    latencies = [latency for latency, _ in outcomes]
    successes = sum(success for _, success in outcomes)
    return {
        "classification": "Point-in-time HTTP smoke benchmark; not a capacity claim",
        "url": url,
        "requests": requests,
        "concurrency": concurrency,
        "successes": successes,
        "errors": requests - successes,
        "p50_ms": round(_percentile(latencies, 0.50), 2),
        "p95_ms": round(_percentile(latencies, 0.95), 2),
        "max_ms": round(max(latencies), 2),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url")
    parser.add_argument("--requests", type=int, default=50)
    parser.add_argument("--concurrency", type=int, default=5)
    parser.add_argument("--timeout", type=float, default=10)
    args = parser.parse_args()
    result = run_benchmark(args.url, args.requests, args.concurrency, args.timeout)
    print(json.dumps(result, indent=2))
    if result["errors"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
