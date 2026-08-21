from __future__ import annotations

from pathlib import Path

import pytest

from limitiq.sbom import build_sbom, parse_requirements


def test_sbom_matches_pinned_runtime_requirements() -> None:
    payload = build_sbom()
    dependencies = parse_requirements()
    assert payload["bomFormat"] == "CycloneDX"
    assert payload["specVersion"] == "1.6"
    assert len(payload["components"]) == len(dependencies)
    assert all(component["purl"].startswith("pkg:pypi/") for component in payload["components"])


def test_unpinned_requirement_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "requirements.txt"
    path.write_text("fastapi>=1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="exactly pinned"):
        parse_requirements(path)
