from __future__ import annotations

import pytest

from limitiq.benchmark import _batch_request, _percentile, run_benchmark


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


def test_batch_request_factory_builds_bounded_unique_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sample = (
        b"ACCOUNT_ID,LIMIT_BAL,PAY_0,PAY_2,PAY_3,PAY_4,PAY_5,PAY_6,"
        b"BILL_AMT1,BILL_AMT2,BILL_AMT3,BILL_AMT4,BILL_AMT5,BILL_AMT6,"
        b"PAY_AMT1,PAY_AMT2,PAY_AMT3,PAY_AMT4,PAY_AMT5,PAY_AMT6,"
        b"current_limit_inr,current_balance_inr,income_inr,"
        b"total_monthly_obligation_inr,credit_lines,credit_age_months\r\n"
        b"SAMPLE,100000,0,0,0,0,0,0,80000,70000,60000,50000,40000,30000,"
        b"5000,5000,5000,5000,5000,5000,100000,80000,1200000,25000,6,120\r\n"
    )

    class _SampleResponse:
        status = 200

        def __enter__(self) -> _SampleResponse:
            return self

        def __exit__(self, *_: object) -> None:
            return None

        def read(self) -> bytes:
            return sample

    monkeypatch.setattr(
        "limitiq.benchmark.urllib.request.urlopen", lambda *_args, **_kwargs: _SampleResponse()
    )
    request = _batch_request("https://example.com/batch", rows=500)

    assert request.method == "POST"
    assert request.full_url == "https://example.com/batch"
    assert request.data is not None
    body = request.data.decode()
    assert body.count("BENCH-") == 500
    assert "BENCH-000000" in body
    assert "BENCH-000499" in body
    with pytest.raises(ValueError, match="between 1 and 5,000"):
        _batch_request("https://example.com/batch", rows=5_001)
