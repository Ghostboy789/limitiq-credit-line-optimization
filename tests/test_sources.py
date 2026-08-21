from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

import limitiq.sources as sources
from limitiq.sources import load_manifest, verify_sources


def _manifest(expected: str) -> dict[str, object]:
    return {
        "schema_version": 1,
        "sources": [
            {
                "id": "open",
                "raw_file": "open.csv",
                "access": "automated-open",
                "sha256": expected,
            },
            {
                "id": "manual",
                "raw_file": "manual.csv",
                "access": "manual-terms-review",
                "sha256": "0" * 64,
            },
        ],
    }


def test_source_verification_reports_verified_missing_and_open_filter(tmp_path: Path) -> None:
    payload = b"known source\n"
    (tmp_path / "open.csv").write_bytes(payload)
    manifest = _manifest(hashlib.sha256(payload).hexdigest())

    results = verify_sources(manifest, tmp_path)
    assert [result["status"] for result in results] == ["verified", "missing"]
    assert [result["id"] for result in verify_sources(manifest, tmp_path, open_only=True)] == [
        "open"
    ]


def test_manifest_rejects_duplicate_ids(tmp_path: Path) -> None:
    manifest = _manifest("0" * 64)
    manifest["sources"].append(dict(manifest["sources"][0]))  # type: ignore[index,union-attr]
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="unique"):
        load_manifest(path)


def test_committed_manifest_is_machine_readable_and_explicit_about_access() -> None:
    manifest = load_manifest()
    assert len(manifest["sources"]) == 7
    assert sum(source["access"] == "automated-open" for source in manifest["sources"]) == 3
    assert all(len(source["sha256"]) == 64 for source in manifest["sources"])


def test_fetch_open_cli_verifies_only_automated_sources(monkeypatch, capsys) -> None:
    manifest = _manifest("0" * 64)
    observed: dict[str, bool] = {}
    monkeypatch.setattr(sources, "load_manifest", lambda: manifest)
    monkeypatch.setattr(sources, "fetch_open_sources", lambda _: None)

    def verify(_, raw_dir=sources.RAW_DIR, *, open_only=False):
        observed["open_only"] = open_only
        return [{"id": "open", "status": "verified"}]

    monkeypatch.setattr(sources, "verify_sources", verify)
    monkeypatch.setattr(sys, "argv", ["limitiq.sources", "fetch-open"])

    sources.main()

    assert observed == {"open_only": True}
    assert '"status": "verified"' in capsys.readouterr().out
