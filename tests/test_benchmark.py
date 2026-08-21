from __future__ import annotations

import pytest

from limitiq.benchmark import _percentile, run_benchmark


class _Response:
    status = 200

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def read(self, _: int) -> bytes:
        return b"x"


def test_smoke_benchmark_counts_successes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "limitiq.benchmark.urllib.request.urlopen", lambda *_args, **_kwargs: _Response()
    )
    result = run_benchmark("http://127.0.0.1:8000/", requests=4, concurrency=2)
    assert result["successes"] == 4
    assert result["errors"] == 0
    assert result["p95_ms"] >= result["p50_ms"]


def test_benchmark_bounds_and_percentile() -> None:
    assert _percentile([1, 2, 3, 4], 0.95) == 4
    with pytest.raises(ValueError, match="HTTP"):
        run_benchmark("file:///tmp/result", requests=1, concurrency=1)
    with pytest.raises(ValueError, match="bounds"):
        run_benchmark("https://example.com", requests=2, concurrency=3)
