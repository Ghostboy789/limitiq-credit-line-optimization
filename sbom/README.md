# Software bill of materials

`limitiq.cdx.json` is a deterministic CycloneDX 1.6 inventory of direct,
exactly pinned Python runtime dependencies. CI verifies that it matches
`requirements.txt`; `pip-audit` and the container scan provide vulnerability
evidence over the resolved environment and image.

```bash
python -m limitiq.sbom --check sbom/limitiq.cdx.json
```
