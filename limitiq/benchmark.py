"""Small dependency-free HTTP smoke benchmark for deployed application routes."""

# ruff: noqa: S310

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import time
import urllib.request
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from urllib.parse import urljoin, urlparse


def _request_once(target: str | urllib.request.Request, timeout: float) -> tuple[float, bool]:
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(target, timeout=timeout) as response:  # nosec B310
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
    url: str,
    requests: int = 50,
    concurrency: int = 5,
    timeout: float = 10,
    request_factory: Callable[[], str | urllib.request.Request] | None = None,
) -> dict[str, Any]:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Benchmark URL must be HTTP(S)")
    if not 1 <= requests <= 1000 or not 1 <= concurrency <= min(100, requests):
        raise ValueError("Requests/concurrency are outside safe benchmark bounds")
    request_factory = request_factory or (lambda: url)
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        outcomes = list(
            pool.map(lambda _: _request_once(request_factory(), timeout), range(requests))
        )
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


def _batch_request(url: str, rows: int) -> urllib.request.Request:
    if not 1 <= rows <= 5_000:
        raise ValueError("Batch rows must be between 1 and 5,000")
    with urllib.request.urlopen(urljoin(url, "/sample-input.csv"), timeout=10) as response:  # nosec B310
        sample = list(csv.DictReader(io.StringIO(response.read().decode("utf-8"))))
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=list(sample[0]))
    writer.writeheader()
    for index in range(rows):
        row = dict(sample[index % len(sample)])
        row["ACCOUNT_ID"] = f"BENCH-{index:06d}"
        writer.writerow(row)
    boundary = "limitiq-benchmark-boundary"
    body = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="file"; filename="benchmark.csv"\r\n'
        "Content-Type: text/csv\r\n\r\n"
        f"{output.getvalue()}\r\n--{boundary}--\r\n"
    ).encode()
    return urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url")
    parser.add_argument("--requests", type=int, default=50)
    parser.add_argument("--concurrency", type=int, default=5)
    parser.add_argument("--timeout", type=float, default=10)
    parser.add_argument("--batch-rows", type=int)
    args = parser.parse_args()
    factory = (lambda: _batch_request(args.url, args.batch_rows)) if args.batch_rows else None
    result = run_benchmark(
        args.url, args.requests, args.concurrency, args.timeout, request_factory=factory
    )
    print(json.dumps(result, indent=2))
    if result["errors"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
