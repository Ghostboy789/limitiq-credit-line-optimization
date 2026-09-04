# Security policy

## Supported version

Only the latest tagged release is supported. LimitIQ is an educational system
and must not receive real customer, account, bureau, income or lending data.

## Reporting a vulnerability

Use GitHub's private vulnerability-reporting or Security Advisory workflow for
this repository. Do not open a public issue containing exploit details, secrets
or personal data.

Include the affected commit, route or component, reproduction steps, expected
impact and any safe mitigation. Reports are triaged for input-boundary,
deserialization, file/path, injection, information-disclosure, dependency and
model-artifact risks.

## Existing controls

The release pipeline runs static analysis, dependency and secret scans,
container scanning, a deterministic direct-dependency SBOM, tests and a
container health smoke check. GitHub secret scanning, push protection,
Dependabot security updates and private vulnerability reporting are enabled.
These controls reduce risk; they do not certify the application for production
lending use.

Application resource and input controls are documented in [docs/SECURITY.md](docs/SECURITY.md).
