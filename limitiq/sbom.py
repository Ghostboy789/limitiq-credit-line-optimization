"""Generate a deterministic direct-dependency CycloneDX SBOM."""

from __future__ import annotations

import argparse
import json
import uuid
from pathlib import Path
from typing import Any

from limitiq import __version__
from limitiq.config import ROOT

REQUIREMENTS_PATH = ROOT / "requirements.txt"
NAMESPACE = uuid.UUID("9c07b874-40cb-41e7-9ed1-d674dbc165b0")


def parse_requirements(path: Path = REQUIREMENTS_PATH) -> list[tuple[str, str]]:
    dependencies: list[tuple[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        value = line.strip()
        if not value or value.startswith("#"):
            continue
        if value.count("==") != 1:
            raise ValueError(f"Runtime dependency must be exactly pinned: {value}")
        name, version = value.split("==", 1)
        if not name or not version:
            raise ValueError(f"Invalid runtime dependency: {value}")
        dependencies.append((name, version))
    return dependencies


def build_sbom(path: Path = REQUIREMENTS_PATH) -> dict[str, Any]:
    dependencies = sorted(parse_requirements(path), key=lambda item: item[0].lower())
    identity = "\n".join(f"{name}=={version}" for name, version in dependencies)
    return {
        "$schema": "http://cyclonedx.org/schema/bom-1.6.schema.json",
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "serialNumber": f"urn:uuid:{uuid.uuid5(NAMESPACE, identity)}",
        "version": 1,
        "metadata": {
            "component": {
                "type": "application",
                "bom-ref": f"pkg:pypi/limitiq-credit-line-optimization@{__version__}",
                "name": "limitiq-credit-line-optimization",
                "version": __version__,
                "purl": f"pkg:pypi/limitiq-credit-line-optimization@{__version__}",
            },
            "properties": [
                {
                    "name": "limitiq:inventory-scope",
                    "value": "direct pinned Python runtime dependencies",
                }
            ],
        },
        "components": [
            {
                "type": "library",
                "bom-ref": f"pkg:pypi/{name.lower().replace('_', '-')}@{version}",
                "name": name,
                "version": version,
                "purl": f"pkg:pypi/{name.lower().replace('_', '-')}@{version}",
            }
            for name, version in dependencies
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", type=Path)
    args = parser.parse_args()
    payload = build_sbom()
    text = json.dumps(payload, indent=2) + "\n"
    if args.check:
        if json.loads(args.check.read_text(encoding="utf-8")) != payload:
            raise SystemExit("SBOM does not match pinned runtime requirements")
        return
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8", newline="\n")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
