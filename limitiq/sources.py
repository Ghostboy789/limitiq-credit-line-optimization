"""Verify source provenance and fetch only explicitly open UCI inputs."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from limitiq.config import DATA_DIR, RAW_DIR

MANIFEST_PATH = DATA_DIR / "source_manifest.json"


def load_manifest(path: Path = MANIFEST_PATH) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1 or not isinstance(payload.get("sources"), list):
        raise ValueError("Unsupported source manifest schema")
    ids = [source.get("id") for source in payload["sources"]]
    if any(not value for value in ids) or len(ids) != len(set(ids)):
        raise ValueError("Source manifest IDs must be unique and non-empty")
    return payload


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_sources(
    manifest: dict[str, Any], raw_dir: Path = RAW_DIR, *, open_only: bool = False
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for source in manifest["sources"]:
        if open_only and source["access"] != "automated-open":
            continue
        path = raw_dir / source["raw_file"]
        actual = file_sha256(path) if path.is_file() else None
        results.append(
            {
                "id": source["id"],
                "file": source["raw_file"],
                "access": source["access"],
                "status": (
                    "missing"
                    if actual is None
                    else "verified"
                    if actual == source["sha256"]
                    else "checksum-mismatch"
                ),
                "expected_sha256": source["sha256"],
                "actual_sha256": actual,
            }
        )
    return results


def fetch_open_sources(manifest: dict[str, Any], raw_dir: Path = RAW_DIR) -> None:
    """Fetch only manifest entries carrying explicit open automated access."""
    from limitiq.external import _fetch_uci_zip
    from limitiq.pipeline import download_dataset

    raw_dir.mkdir(parents=True, exist_ok=True)
    for source in manifest["sources"]:
        if source["access"] != "automated-open":
            continue
        destination = raw_dir / source["raw_file"]
        if destination.is_file() and file_sha256(destination) == source["sha256"]:
            continue
        if source["id"] == "taiwan_credit":
            downloaded = download_dataset(force=destination.exists())
            if downloaded.resolve() != destination.resolve():
                raise RuntimeError("Taiwan source downloaded to an unexpected path")
        else:
            _fetch_uci_zip(source["download_url"], source["archive_member"], destination)
        if file_sha256(destination) != source["sha256"]:
            raise RuntimeError(f"Checksum mismatch after fetching {source['id']}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("verify", "fetch-open", "manifest"))
    parser.add_argument("--open-only", action="store_true")
    args = parser.parse_args()
    manifest = load_manifest()
    if args.command == "manifest":
        print(json.dumps(manifest, indent=2))
        return
    if args.command == "fetch-open":
        fetch_open_sources(manifest)
    results = verify_sources(
        manifest,
        open_only=args.open_only or args.command == "fetch-open",
    )
    print(json.dumps(results, indent=2))
    if any(result["status"] != "verified" for result in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
